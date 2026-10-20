"""
Test resource for nested classes.
Similar to NestedClasses.dll in C# tests.
"""


class OuterClass:
    """Outer class containing nested classes."""
    
    class InnerClass:
        """Nested inner class."""
        
        def __init__(self, value: int):
            self.value = value
        
        def get_value(self) -> int:
            """Get inner class value."""
            return self.value
    
    class NestedStaticClass:
        """Nested static-like class."""
        
        @staticmethod
        def static_method(value: str) -> str:
            """Static method in nested class."""
            return f"Nested: {value}"
    
    def __init__(self, outer_value: str):
        self.outer_value = outer_value
    
    def create_inner(self, value: int) -> 'OuterClass.InnerClass':
        """Create instance of inner class."""
        return OuterClass.InnerClass(value)
    
    def get_outer_value(self) -> str:
        """Get outer class value."""
        return self.outer_value


class DeepNestedClass:
    """Class with deeply nested classes."""
    
    class Level1:
        """First level nested class."""
        
        class Level2:
            """Second level nested class."""
            
            class Level3:
                """Third level nested class."""
                
                def __init__(self, value: int):
                    self.value = value
                
                def get_value(self) -> int:
                    """Get deeply nested value."""
                    return self.value
