"""
Test resource for object type static methods and fields.
Similar to TypeObjectStatic.dll in C# tests.
"""


class TypeObjectStaticClassImplementation:
    """Class with static fields and methods returning object type."""
    
    # Static field of type object
    EngineCapacity: object = None
    
    @staticmethod
    def GetEngineCapacity() -> object:
        """Static method returning object type."""
        return TypeObjectStaticClassImplementation.EngineCapacity
    
    @staticmethod
    def GetCarPriceAsString(factor: object) -> object:
        """Static method with object parameter and return type."""
        return str(factor)
    
    def __init__(self):
        """Constructor."""
        pass
