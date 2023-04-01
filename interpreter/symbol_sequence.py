"""
Symbol sequence builder.
"""
from typing import List

from minilex.parser.symbol_tree import SymbolTree
from minilex.parser.symbols import SYM_NO_OP, SYM_SEQUENCE, ConditionSymbol, Symbol


class SymbolLine:
    """
    Line containing symbol information.
    """

    def __init__(self, name, content, indent):
        self.indent = indent
        self.name = name
        self.content = content

    def __repr__(self):
        tab = "".join(self.indent * ["\t"])
        return f"{tab} ({self.name}, {self.content})"


class SymbolLineEnd(SymbolLine):
    """
    Line terminating multi-line symbol.
    """

    def __init__(self, name, indent):
        self.indent = indent
        super().__init__(name, "END", indent)


class ConditionStart(SymbolLine):
    """
    Start of symbol condition.
    """

    def __init__(self, name, indent):
        self.indent = indent
        super().__init__(name, "CONDITION", indent)


class ResultStart(SymbolLine):
    """
    Start of result in symbol.
    """

    def __init__(self, name, indent):
        self.indent = indent
        super().__init__(name, "RESULT", indent)


class SymbolSequence:
    """
    Transform nested AST of symbols to flat sequence.
    """

    def __init__(self, tree: SymbolTree, origin):
        self.text = tree.text
        self.source = tree.source
        self.full = tree
        self.seq: List[SymbolLine] = []
        self.event_origin = origin


class SymbolSequenceBuilder:
    """
    Transform nested AST of symbols to flat sequence.
    """

    def __init__(self):
        self.cases = []
        self.seq = []
        self.hold = False
        self.held_stmts = []
        self.finished = False

    def add_symbol_condition(self, symbol: Symbol, logic):
        """
        Add symbol condition to happen.
        """
        assert not self.finished, "cannot add cases after generating a symbol sequence"
        self.cases.append((symbol, logic))

    def add(self, event_line: SymbolLine):
        """
        Add statement with operator label to event sequence or to held statements set.
        """
        if not self.hold:
            self.seq.append(event_line)
        else:
            self.held_stmts.append(event_line)

    def add_held_statements(self, idx):
        """
        Add stmt(s) to symbol sequence partway through.
        """
        self.seq = self.seq[: idx + 1] + self.held_stmts + self.seq[idx + 1 :]
        self.hold = False
        self.held_stmts = []

    def add_event_params_to_seq(self, event: Symbol, indent):
        """
        Add each param to the sequence.
        """
        for k, v in event.children.items():
            self.add(SymbolLine(event.name, k, indent))  # event feature name
            # feature value enterered into sequence recursively
            self.parse_and_add_stmts(v, indent)

    def __call__(self, tree: SymbolTree, origin):
        """
        Convert a symbol tree to a symbol sequence.
        """
        self.finished = True

        sequence = SymbolSequence(tree, origin)

        # accumulate statements to store somewhere other than end of list
        self.hold = False
        self.held_stmts = []

        # parse and assemble symbol sequence
        self.seq = sequence.seq
        self.parse_and_add_stmts(tree.logic, -1)

        # verify flatness of sequence
        assert all(
            all(not isinstance(k, dict) for k in s[1].keys())
            for s in self.seq
            if isinstance(s, tuple) and isinstance(s[1], dict)
        ), "nested complex event not permitted in action sequence"

        return sequence

    def parse_and_add_stmts(self, node, indent):
        """
        Parse AST of a symbol recursively (depth-first search) and add statements to
        symbol sequence.
        """
        # none string
        if node is None or isinstance(node, SYM_NO_OP):
            return None

        # parse enclosing sequence in order
        if isinstance(node, SYM_SEQUENCE):
            for s in node.events:
                self.parse_and_add_stmts(s, indent + 1)

        # bool or string
        elif isinstance(node, bool) or (isinstance(node, str) and not node.isnumeric()):
            return node

        # numbers
        elif isinstance(node, (int, str)):
            return int(node)

        # clauses and conditions split into labels
        elif isinstance(node, ConditionSymbol):
            cond = node.children.get("condition")
            result = node.children.get("result")

            del node.children["condition"]
            del node.children["result"]

            # add beginning label with other params or label
            # self.add_event_params_to_seq(node)

            self.add(SymbolLine(node.name, node, indent))
            self.add(ConditionStart(node.name, indent))
            if cond is not None:
                self.parse_and_add_stmts(cond, indent + 1)
            self.add(ResultStart(node.name, indent))
            if result is not None:
                self.parse_and_add_stmts(result, indent + 1)

            self.add(SymbolLineEnd(node.name, indent))

        parsed_by_case = False
        for sym, logic in self.cases:
            if isinstance(node, sym):
                parsed_by_case = True
                logic(self, node)

        # non-conditional symbols parsed as self
        if not parsed_by_case and isinstance(node, Symbol):
            self.add(SymbolLine(node.name, node, indent))

        else:
            raise TypeError("invalid symbol entered in ast")

        return None
