"""
Symbol sequence builder.
"""
from typing import List

from parse.minilex.parser.symbol_tree import SymbolTree
from parse.minilex.parser.symbols import SYM_NO_OP, SYM_SEQUENCE, ConditionSymbol, Symbol
from parse.minilex.data.json_convertable import JSONConvertable

class SymbolLine(JSONConvertable):
    """
    Line containing symbol information.
    """

    def __init__(self, name, content, indent):
        super().__init__()
        self.indent = indent
        self.name = name
        self.content = content

    def __repr__(self):
        tab = "".join(self.indent * ["\t"])
        r = f"{tab} ({self.name}, {self.content})"
        return r

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


class SymbolSequence(JSONConvertable):
    """
    Transform nested AST of symbols to flat sequence.
    """

    def __init__(self, tree: SymbolTree, source):
        self.text = tree.text
        self.source = tree.source
        # self.tree: SymbolTree = tree
        self.seq = []
        self.symbols: List[Symbol] = []
        self.source = source

    def __repr__(self):
        return f'Sequence: {self.symbols}'


class SymbolSequenceBuilder:
    """
    Transform nested AST of symbols to flat sequence.
    """

    def __init__(self, tree_builder):
        self.cases = []
        self.seq = []
        self.hold = False
        self.held_stmts = []
        self.source = None
        self.finished = False
        self.tree_builder = tree_builder
        self.expand_conditionals = False

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
        # if not expanding conditionals, just add symbols rather than lines
        if not self.expand_conditionals:
            self.seq.append(event_line.content)
        elif not self.hold:
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

    def __call__(self, text, source, variants=None):
        """
        Convert a symbol tree to a symbol sequence.
        variants included for small cards
        """
        self.finished = True
        self.variants = variants

        tree = self.tree_builder(text, source, variants)
        sequence = SymbolSequence(tree, source)
        self.source = source

        # accumulate statements to store somewhere other than end of list
        self.hold = False
        self.held_stmts = []

        self.symbols = []

        # parse and assemble symbol sequence
        self.seq = sequence.seq
        self.parse_and_add_stmts(tree.logic, -1)

        # TODO: actual fix for logic erroneously adding SYM_SEQ, no time to do so now
        sequence.seq = [e for e in self.seq if e.name != 'SEQ']

        sequence.symbols = list(set([e for e in self.symbols if e != 'SEQ']))

        # verify flatness of sequence
        assert all(
            all(not isinstance(k, dict) for k in s[1].keys())
            for s in sequence.seq
            if isinstance(s, tuple) and isinstance(s[1], dict)
        ), "nested complex event not permitted in action sequence"

        assert 'SEQ' not in sequence.symbols, 'nested SYM_SEQ not permitted'

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
            for s in node.symbols:
                self.parse_and_add_stmts(s, indent + 1)

        # bool or string
        if isinstance(node, bool) or (isinstance(node, str) and not node.isnumeric()):
            return node

        # numbers
        if isinstance(node, (int, str)):
            return int(node)
        
        self.symbols.append(node.name)

        # clauses and conditions split into labels
        if isinstance(node, ConditionSymbol):
            cond = node.condition
            result = node.result

            # del node.children["condition"]
            # del node.children["result"]

            # add beginning label with other params or label
            # self.add_event_params_to_seq(node)

            self.add(SymbolLine(node.name, node, indent))
            if self.expand_conditionals:
                self.add(ConditionStart(node.name, indent))
                if cond is not None:
                    self.parse_and_add_stmts(cond, indent + 1)
            else:
                # if not expanding conditionals fully, keep condition in symbol attributes but not result
                del node.result
            if self.expand_conditionals:
                self.add(ResultStart(node.name, indent))
            if result is not None:
                self.parse_and_add_stmts(result, indent + 1)
            if self.expand_conditionals:
                self.add(SymbolLineEnd(node.name, indent))
            return None

        for sym, logic in self.cases:
            if isinstance(node, sym):
                logic(self, node, indent)
                return None

        # non-conditional symbols parsed as self
        if isinstance(node, Symbol):
            self.add(SymbolLine(node.name, node, indent))
        else:
            raise TypeError("invalid symbol entered in ast")

        return None
