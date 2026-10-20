"""
Mix: some methods return ONLY primitives (via custom generics/arrays),
others return mixed primitives + a concrete class (UserId).
No framework generics; primitives + arrays are OK.
"""

from typing import Generic, TypeVar, List, Optional, Tuple

T = TypeVar('T')
TOk = TypeVar('TOk')
TErr = TypeVar('TErr')
L = TypeVar('L')
R = TypeVar('R')

# ---- concrete class to mix with primitives ----
class UserId:
    def __init__(self, value: int):
        self.value = value
    
    def __str__(self) -> str:
        return f"UserId({self.value})"

# ---- custom generic building blocks ----
class Arr(Generic[T]):
    def __init__(self, items: List[T]):
        self.items = items
    
    @property
    def length(self) -> int:
        return len(self.items)

class Option(Generic[T]):
    def __init__(self, has_value: bool, value: Optional[T] = None):
        self.has_value = has_value
        self.value = value
    
    @classmethod
    def some(cls, value: T) -> 'Option[T]':
        return cls(True, value)
    
    @classmethod
    def none(cls) -> 'Option[T]':
        return cls(False)

class Result(Generic[TOk, TErr]):
    def __init__(self, is_ok: bool, ok: Optional[TOk] = None, err: Optional[TErr] = None):
        self.is_ok = is_ok
        self.ok = ok
        self.err = err
    
    @classmethod
    def ok_value(cls, value: TOk) -> 'Result[TOk, TErr]':
        return cls(True, ok=value)
    
    @classmethod
    def err_value(cls, error: TErr) -> 'Result[TOk, TErr]':
        return cls(False, err=error)

class Either(Generic[L, R]):
    def __init__(self, is_left: bool, left: Optional[L] = None, right: Optional[R] = None):
        self.is_left = is_left
        self.left = left
        self.right = right
    
    @classmethod
    def from_left(cls, value: L) -> 'Either[L, R]':
        return cls(True, left=value)
    
    @classmethod
    def from_right(cls, value: R) -> 'Either[L, R]':
        return cls(False, right=value)

class Page(Generic[T]):
    def __init__(self, items: Arr[T], next_cursor: str):
        self.items = items
        self.next_cursor = next_cursor

class Examples:
    # ---------------------------
    # LEVELS: primitives only
    # ---------------------------
    
    # P0 (base)
    @staticmethod
    def P0_GetIntArraySimple() -> List[int]:
        """Returns a simple int array."""
        return []
    
    @staticmethod
    def P0_GetIntJaggedSimple() -> List[List[int]]:
        """Returns a jagged int array (list of lists)."""
        return []
    
    @staticmethod
    def P0_GetIntGridSimple() -> List[List[int]]:
        """Returns a 2D int grid (list of lists)."""
        return []
    
    @staticmethod
    def P0_GetOptionalInt() -> Option[int]:
        """Returns an optional int."""
        return Option[int].none()
    
    @staticmethod
    def P0_GetIntPage() -> Page[int]:
        """Returns an int page."""
        return Page[int](Arr[int]([]), "")
    
    @staticmethod
    def P0_GetIntArray() -> Arr[int]:
        """Returns an int array wrapper."""
        return Arr[int]([])
    
    @staticmethod
    def P0_GetNullableInt() -> Optional[int]:
        """Returns a nullable int."""
        return None
    
    @staticmethod
    def P0_GetIntResult() -> Result[int, str]:
        """Returns an int result."""
        return Result[int, str].err_value("error")
    
    # P1 (simple): Arr[Result[Option[int], str]]
    @staticmethod
    def P1_FetchIds() -> Arr[Result[Option[int], str]]:
        return Arr[Result[Option[int], str]]([])
    
    # P2: List[List[Result[Either[int, str], str]]]
    @staticmethod
    def P2_ParseGrid() -> List[List[Result[Either[int, str], str]]]:
        return []
    
    # P3: List[List[Either[Option[int], Result[str, int]]]]
    @staticmethod
    def P3_BuildJagged() -> List[List[Either[Option[int], Result[str, int]]]]:
        return []
    
    # P4 (mixed dims): Arr[List[List[Option[Result[int, str]]]]]
    @staticmethod
    def P4_LoadMatrixCells() -> Arr[List[List[Option[Result[int, str]]]]]:
        return Arr[List[List[Option[Result[int, str]]]]]([])
    
    # P5 (bigger): List[List[List[List[Option[Result[Page[Either[str, int]], Either[Option[int], str]]]]]]]
    @staticmethod
    def P5_VolumesJagged() -> List[List[List[List[Option[Result[Page[Either[str, int]], Either[Option[int], str]]]]]]]:
        return []
    
    # ---------------------------
    # LEVELS: mixed primitives + UserId
    # ---------------------------
    
    # M1 (simple mix): Arr[Result[UserId, str]]
    @staticmethod
    def M1_LoadUsers() -> Arr[Result[UserId, str]]:
        return Arr[Result[UserId, str]]([])
    
    # M2: List[List[Option[UserId]]]
    @staticmethod
    def M2_UserGrid() -> List[List[Option[UserId]]]:
        return []
    
    # M3: List[List[Result[Option[UserId], Either[int, str]]]]
    @staticmethod
    def M3_JaggedUserResults() -> List[List[Result[Option[UserId], Either[int, str]]]]:
        return []
    
    # M4 (dims + wrapper + mix): Arr[List[List[List[Result[UserId, str]]]]]
    @staticmethod
    def M4_MixedUserMatrices() -> Arr[List[List[List[Result[UserId, str]]]]]:
        return Arr[List[List[List[Result[UserId, str]]]]]([])
    
    # M5 (deep mix):
    # Arr[
    #   Result[
    #     List[List[Arr[Option[Either[UserId, int]]]]],
    #     Page[Result[str, UserId]]
    #   ]
    # ]
    @staticmethod
    def M5_DeepUserBeast() -> Arr[Result[List[List[Arr[Option[Either[UserId, int]]]]], Page[Result[str, UserId]]]]:
        return Arr[Result[List[List[Arr[Option[Either[UserId, int]]]]], Page[Result[str, UserId]]]]([])
