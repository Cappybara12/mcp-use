"""
Test resource for nullable/optional types.
Similar to NullableTest.dll in C# tests.
"""

from typing import Optional, Union


class NullableTestClass:
    """Class demonstrating nullable/optional type handling."""
    
    def __init__(self):
        self.nullable_int: Optional[int] = None
        self.nullable_str: Optional[str] = None
        self.nullable_bool: Optional[bool] = None
    
    def get_nullable_int(self) -> Optional[int]:
        """Returns nullable int."""
        return self.nullable_int
    
    def set_nullable_int(self, value: Optional[int]) -> None:
        """Sets nullable int."""
        self.nullable_int = value
    
    def get_nullable_str(self) -> Optional[str]:
        """Returns nullable string."""
        return self.nullable_str
    
    def get_nullable_bool(self) -> Optional[bool]:
        """Returns nullable bool."""
        return self.nullable_bool
    
    def process_nullable(self, value: Optional[int]) -> Optional[str]:
        """Processes nullable value."""
        if value is None:
            return None
        return str(value)
    
    def union_with_none(self, value: Union[int, None]) -> Union[str, None]:
        """Union type with None."""
        if value is None:
            return None
        return str(value)
