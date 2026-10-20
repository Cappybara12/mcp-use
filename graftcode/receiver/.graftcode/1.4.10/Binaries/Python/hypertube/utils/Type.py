from enum import Enum


class Type(Enum):
    Command = 0
    HypertubeString = 1
    HypertubeInteger = 2
    HypertubeBoolean = 3
    HypertubeFloat = 4
    HypertubeByte = 5
    HypertubeChar = 6
    HypertubeLongLong = 7
    HypertubeDouble = 8
    HypertubeUnsignedLongLong = 9
    HypertubeUnsignedInteger = 10
    HypertubeNoneType = 11
    HypertubeUndefinedType = 12
    HypertubeVoidType = 13
