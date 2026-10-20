from enum import Enum


class RuntimeName(Enum):
    clr = 0
    go = 1
    jvm = 2
    netcore = 3
    perl = 4
    python = 5
    ruby = 6
    nodejs = 7
    cpp = 8
    php = 9
    python27 = 10

    def __str__(self):
        return self.name
