"""
Types of symbols lexer can convert text to.
"""
from minilex.data.json_convertable import JSONConvertable

class Symbol(JSONConvertable):
    """
    Symbol representing lexed text.
    """

    def __init__(self, name, text=None):
        self.name = name
        self.orig_text = text
        self.children = dict(self.__dict__)
        del self.children["name"]
        del self.children["orig_text"]
        assert isinstance(self.name, str), "event name must be str"

    def __repr__(self):
        self_dict = dict(self.__dict__)
        del self_dict["name"]
        del self_dict["orig_text"]
        return (
            f"{self.name}: {self_dict}"
            if len(self_dict) > 0
            else f"{self.name}"
        )

    def to_json(self):
        """
        Convert symbol to docstring.
        """

        def jsonify(obj):
            if isinstance(obj, Symbol):
                return obj.to_json()
            if isinstance(obj, list):
                arr = [jsonify(e) for e in obj]
                return arr[0] if len(arr) == 1 else arr
            return str(obj)

        children = self.__dict__
        if 'children' in children:
            del children['children']
        if children is None:
            return self.name
        if isinstance(children, dict):
            return {self.name: {k: jsonify(e) for k, e in children.items()}}
        return {self.name: jsonify(children)}


class ConditionSymbol(Symbol):
    """
    Symbol representing condition or control structure.
    """

    def __init__(self, name, condition=None, result=None, text=None):
        self.condition = condition
        self.result = result
        super().__init__(name, text=text)


class SYM_NO_OP(Symbol):
    """
    Symbol representing no-op.
    """

    def __init__(self):
        super().__init__("NO_OP")


class SYM_SEQUENCE(Symbol):
    """
    Symbol containing sequence of symbols.
    """

    def __init__(self, symbols):
        self.symbols = symbols
        super().__init__("SEQ")
