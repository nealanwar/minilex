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
        self.seq = []
        self.source = source

    def __repr__(self):
        return f'Sequence: {self.symbols}'


class SymbolSequenceBuilder:
    """
    Transform nested AST of symbols to flat sequence.
    keep_top_level: if non-empty, create sequence of only non-expanded symbols in list, otherwise create sequence of expanded lines containing any symbol at top level 
    """

    def __init__(self, tree_builder, collapse = [], keep_top_level: List[Symbol] = []):
        self.cases = []
        self.seq = []
        self.hold = False
        self.held_stmts = []
        self.source = None
        self.finished = False
        self.tree_builder = tree_builder
        self.collapse_conditionals = collapse
        self.keep_top_level = keep_top_level

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
        for k, v in event.__dict__.items():
            if k == 'name' or k == 'orig_text':
                continue
            self.add(SymbolLine(event.name, k, indent))  # event feature name
            # feature value enterered into sequence recursively
            self.parse_and_add_stmts(v, indent)

    def get_symbols_from_tree(self, node, acc):
        """
        Recursively get symbols from tree.
        """
        if node is None:
            return []
        if isinstance(node, SYM_SEQUENCE):
            [self.get_symbols_from_tree(e, acc) for e in node.symbols]
        else:
            sub_symbols = dict(node.__dict__)
             # to prevent the registering of conditions as actions, do not add a node independently if it is the condition
            # of a condition symbol
            # e.g. if condition is when(gain(health)), do not add gain(health) which will be interpreted as an action
            if isinstance(node, ConditionSymbol):
                del sub_symbols['condition']
            
            [self.get_symbols_from_tree(e, acc) for e in sub_symbols.values() if isinstance(e, Symbol)]
            # to prevent the registering of conditions as actions, do not add a node independently if it is the condition
            # of a condition symbol
            acc.append(node)
        return acc

    def remove_result(self, x):
        del x.result
        return x

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

        # parse and assemble symbol sequence
        if len(self.keep_top_level) > 0:
            sequence.seq = [s for s in self.get_symbols_from_tree(tree.logic, []) if any(isinstance(s, sym) for sym in self.keep_top_level)]
            sequence.seq = [self.remove_result(s) if any(isinstance(s, sym) for sym in self.collapse_conditionals) else s for s in sequence.seq]
        else:
            self.seq = sequence.seq
            self.parse_and_add_stmts(tree.logic, -1)

            # verify flatness of sequence
            assert all(
                all(not isinstance(k, dict) for k in s[1].keys())
                for s in sequence.seq
                if isinstance(s, tuple) and isinstance(s[1], dict)
            ), "nested complex event not permitted in action sequence"

        import json
        with open('./parse/minilex/interpreter/test.json', 'w') as f:
            json.dump(sequence.to_json(), f, indent=2)

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
        
        # clauses and conditions split into labels
        if isinstance(node, ConditionSymbol):
            cond = node.condition
            result = node.result

            # del node.children["condition"]
            # del node.children["result"]

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
        else:
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
