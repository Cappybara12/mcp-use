"""
Test resource for constructors with various scenarios.
Similar to ConstructorTest.dll in C# tests.
"""


class FewConstructorsClass:
    """Class with multiple constructors (simulated with default parameters)."""
    
    def __init__(self, param1: int = 0, param2: str = "", param3: float = 0.0, 
                 param4: bool = False, param5: int = 0, param6: str = ""):
        """Constructor with multiple optional parameters to simulate multiple constructors."""
        self.param1 = param1
        self.param2 = param2
        self.param3 = param3
        self.param4 = param4
        self.param5 = param5
        self.param6 = param6


class NoConstructorsClass:
    """Class with only default constructor."""
    
    def __init__(self):
        """Default constructor."""
        self.value = 0


class PrivateConstructorClass:
    """Class with private constructor (not directly instantiable)."""
    
    def __init__(self):
        """Private constructor - should not be accessible."""
        if type(self) == PrivateConstructorClass:
            raise TypeError("Cannot instantiate PrivateConstructorClass directly")
        self.value = 0
    
    @classmethod
    def create(cls):
        """Factory method to create instance."""
        class _PrivateSubclass(PrivateConstructorClass):
            pass
        return _PrivateSubclass()
