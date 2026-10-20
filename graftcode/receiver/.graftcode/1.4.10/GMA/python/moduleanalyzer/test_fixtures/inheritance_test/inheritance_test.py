from abc import ABC, abstractmethod


class BaseClass:
    def __init__(self) -> None:
        self.base_value = 0


class IMarker(ABC):
    @abstractmethod
    def mark(self) -> None:
        ...


class ChildClass(BaseClass, IMarker):
    def __init__(self) -> None:
        super().__init__()
        self.child_value = 0

    def mark(self) -> None:
        return None
