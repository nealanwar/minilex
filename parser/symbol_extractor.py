"""
Builder for ASTs from text.
"""
import re
from typing import List


class _SymbolCriteria:
    """
    Criteria for lexing a symbol.
    """

    def __init__(
        self,
        symbol,
        regex: str,
        exclude_regex: List[str],
        symbol_args: List[int],
        custom_make_function,
    ):
        self.symbol_class = symbol
        self.regex = regex
        self.exclude_regex = exclude_regex
        self.args = symbol_args
        self.custom_make_function = custom_make_function


class SymbolExtractor:
    """
    Generate an abstract syntax tree.
    """

    def __init__(self):
        self.symbols: List[_SymbolCriteria] = []
        self.finished = False
        self.default_symbol = None

    def add_terminal_symbol(self, symbol, regex: str, exclude_regex: List[str] = None):
        """
        Add symbol with no args.
        """
        self.add_symbol(symbol, regex, [], [], exclude_regex)

    def add_symbol(
        self,
        symbol,
        regex: str,
        symbol_args: List[int],
        exclude_regex: List[str] = None,
        custom_make_function = None,
    ):
        """
        Add arbitrary symbol, arguments are groups found by regex search if it succeeds.
        """
        assert not self.finished, "cannot add symbols after generating an ast"
        if exclude_regex is None:
            exclude_regex = []
        self.symbols.append(
            _SymbolCriteria(
                symbol, regex, exclude_regex, symbol_args, custom_make_function
            )
        )

    def add_default_symbol(self, symbol):
        """
        Add default symbol that will be returned if no other case matches.
        """
        self.default_symbol = symbol

    def __call__(self, string: str):
        """
        Generate an AST of symbols corresponding to some plain text.
        """

        # after calling for the first time, cannot add more symbols
        self.finished = True

        if string is None:
            return None
        string = string.strip().lower()

        if len(string) == 0:
            return None

        for sym in self.symbols:
            inc_r = re.search(sym.regex, string)
            exc_r = [re.search(e, string) for e in sym.exclude_regex]

            if inc_r is not None and all(e is None for e in exc_r):
                if 'gain this card' in sym.regex:
                    daf = 3
                # final arg always original tex
                group_args = [self(inc_r.group(d)) for d in sym.args]
                # if custom make function is provided, use that to instantiate class
                if sym.custom_make_function is not None:
                    return sym.custom_make_function(self.__call__, inc_r, string)
                # otherwise just feed in regex groups and string
                return sym.symbol_class(*group_args, string)

        return self.default_symbol(string)
