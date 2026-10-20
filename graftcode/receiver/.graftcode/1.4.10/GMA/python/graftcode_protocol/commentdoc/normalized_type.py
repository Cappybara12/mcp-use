from __future__ import annotations

from enum import Enum
from typing import Optional


class NormalizedType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    UNKNOWN = "unknown"
    VOID = "void"
    DATETIME = "datetime"
    DATE = "date"
    MAP = "map"
    ENUM = "enum"
    ERROR = "error"

    def to_python_type(self) -> str:
        match self:
            case NormalizedType.STRING:
                return "str"
            case NormalizedType.INTEGER:
                return "int"
            case NormalizedType.NUMBER:
                return "float"
            case NormalizedType.BOOLEAN:
                return "bool"
            case NormalizedType.DATETIME:
                return "datetime.datetime"
            case NormalizedType.DATE:
                return "datetime.date"
            case NormalizedType.ARRAY:
                return "list"
            case NormalizedType.MAP:
                return "dict"
            case NormalizedType.OBJECT:
                return "object"
            case NormalizedType.VOID:
                return "None"
            case NormalizedType.UNKNOWN:
                return "Any"
            case NormalizedType.ENUM:
                return "Enum"
            case NormalizedType.ERROR:
                return "Exception"
        return self.value

    @classmethod
    def try_from_wire_value(cls, normalized_type: Optional[str]) -> Optional[NormalizedType]:
        key = (normalized_type or "").strip().lower()
        if not key:
            return None
        try:
            return cls(key)
        except ValueError:
            return None

    @classmethod
    def normalized_to_python_type(
        cls, raw_type: Optional[str], normalized_type: Optional[str]
    ) -> str:
        wire = cls.try_from_wire_value(normalized_type)
        if wire is not None:
            return wire.to_python_type()
        return (raw_type or "").strip()
