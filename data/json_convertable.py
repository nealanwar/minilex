"""
Abstract base for JSON-convertable objects implementing to_json().
"""
from enum import Enum

class JSONConvertable:
    """
    Abstract base for JSON-convertable objects implementing to_json().
    """
    def __json_val(self, v):
        return [self.__json_val(e) for e in v] if isinstance(v, list) else \
            {k: self.__json_val(e) for k, e in v.items()} if isinstance(v, dict) else \
                  v.value if isinstance(v, Enum) else \
            v.to_json() if not isinstance(v, (int, str, float)) and v is not None else v

    def __repr__(self):
        return self.to_json()

    def to_json(self):
        """
        Convert to json.
        """
        return {
            k: self.__json_val(v)
            for k, v in self.__dict__.items()
        }
