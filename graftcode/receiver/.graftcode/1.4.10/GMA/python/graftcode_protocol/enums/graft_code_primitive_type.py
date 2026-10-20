from enum import IntEnum


class GraftCodePrimitiveType(IntEnum):
    GRAFT_MODEL = 0
    STRING = 1
    INTEGER = 2
    BOOLEAN = 3
    FLOAT = 4
    BYTE = 5
    CHAR = 6
    LONG = 7
    DOUBLE = 8
    UNSIGNED_LONG_LONG = 9
    UNSIGNED_INTEGER = 10
    NULL = 11
    UNDEFINED = 12
    DELEGATE = 13
    UNKNOWN = 14
    VOID = 15
