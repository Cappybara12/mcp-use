"""
Test resource for parameter arrays (*args).
Similar to ParamArrayTest.dll in C# tests.
"""

from typing import List


class ParamArrayTestClass:
    """Class demonstrating *args parameter handling."""
    
    @staticmethod
    def method_with_args(*args: int) -> int:
        """Method with *args parameter."""
        return sum(args)
    
    @staticmethod
    def method_with_args_and_kwargs(*args: str, **kwargs: int) -> dict:
        """Method with both *args and **kwargs."""
        return {
            "args": list(args),
            "kwargs": kwargs
        }
    
    def instance_method_with_args(self, prefix: str, *args: int) -> List[str]:
        """Instance method with *args."""
        return [f"{prefix}{arg}" for arg in args]
    
    @staticmethod
    def method_with_typed_args(*args: str) -> List[str]:
        """Method with typed *args."""
        return list(args)
    
    @staticmethod
    def method_with_mixed_params(required: int, optional: str = "default", *args: float) -> float:
        """Method with mixed parameter types including *args."""
        result = float(required)
        if args:
            result += sum(args)
        return result
