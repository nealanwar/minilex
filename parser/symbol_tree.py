"""
Abstract syntax tree.
"""
import re

from parse.minilex.parser.symbol_extractor import SymbolExtractor


class SymbolTree:
    """
    AST of symbols.
    """

    def __init__(self, text, source, logic):
        self.text = text
        self.source = source
        self.logic = logic

    def __repr__(self):
        return f"{self.logic}"

    def to_json(self):
        """
        Convert symbol tree to json.
        """
        return {
            "text": self.text,
            "source": str(self.source),
            "logic": self.logic.to_json(),
        }


class SymbolTreeBuilder:
    """
    Creator of AST of symbols based on tree builder.
    """

    def __init__(self, symbol_extractor: SymbolExtractor):
        self.symbol_extractor = symbol_extractor

        self.source_cases = []
        self.regex_cases = []
        self.default_case = None
        self.finished = False

    def __on_add_case(self):
        assert not self.finished, "cannot add cases after generating a symbol tree"

    def add_regex_case(self, regex, logic_creator):
        """
        Add tree parsing case for text matching particular regex.
        """
        self.__on_add_case()
        self.regex_cases.append((regex, logic_creator))

    def add_source_case(self, source, logic_creator):
        """
        Add tree parsing case for particular source.
        """
        self.__on_add_case()
        self.source_cases.append((source, logic_creator))

    def add_default_case(self, logic_creator):
        """
        Add default text parsing case, this logic will be
        used to parse text that does not match any other case.
        """
        self.__on_add_case()
        self.default_case = logic_creator

    def __call__(self, text, source):
        """
        Parse some piece of text from a given source.
        """
        # after calling for the first time, cannot add more symbols
        self.finished = True

        # parse null event
        if (
            text is None
            or isinstance(text, bool)
            or len(text) == 0
            or (
                all(isinstance(e, str) for e in text)
                and re.search(r"^n\s?/\s?a$", (" ".join(text)).lower().strip())
                is not None
            )
        ):
            return SymbolTree(text, source, None)

        # parse source cases
        for src, logic_creator in self.source_cases:
            if source == src:
                return SymbolTree(
                    text, source, logic_creator(self.symbol_extractor, text)
                )

        # get first str line
        # i = 0
        # while not isinstance(text[i], str) and i < len(text):
        #     i += 1

        # parse regex cases
        for regex, logic_creator in self.regex_cases:
            r = re.search(regex, text[0].lower().strip())
            if r is not None:
                return SymbolTree(
                    text, source, logic_creator(self.symbol_extractor, text, r)
                )

        # parse default
        return SymbolTree(text, source, self.default_case(self.symbol_extractor, text))
