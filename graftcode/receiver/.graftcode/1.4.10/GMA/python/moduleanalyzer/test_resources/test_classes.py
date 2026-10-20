"""
Real Python classes for testing module analyzer functionality.
Similar to TestClass.js in Node.js tests.
"""

import asyncio
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Protocol, Union


class SampleClass:
    """
    Main test class with various Python features for comprehensive testing.
    """

    # Class variables
    static_value: int = 42
    _protected_static: str = "protected"
    __private_static: float = 3.14

    def __init__(self, public_value: int, private_value: str = "default"):
        """Constructor with typed parameters."""
        self.public_value = public_value
        self._protected_value = private_value
        self.__private_value = "secret"

    # Instance methods
    def multiply_two_numbers(self, a: int, b: int) -> int:
        """Instance method with type hints."""
        return a * b

    def get_1d_array(self) -> List[str]:
        """Method returning a list."""
        return ["one", "two", "three", "four", "five"]

    def get_2d_array(self) -> List[List[str]]:
        """Method returning nested lists."""
        return [
            ["S00", "S01"],
            ["S10", "S11"],
        ]

    def add_array_elements_and_multiply(
        self, my_array: List[int], my_value: int
    ) -> int:
        """Method with complex parameter types."""
        return sum(my_array) * my_value

    # Static methods
    @staticmethod
    def multiply_by_two(a: int) -> int:
        """Static method with type hints."""
        return 2 * a

    @staticmethod
    def divide_by(x: float, y: float) -> float:
        """Static method that may raise exceptions."""
        return SampleClass.divide_by_second(x, y)

    @staticmethod
    def divide_by_second(x: float, y: float) -> float:
        """Intermediate static method."""
        return SampleClass.divide_by_third(x, y)

    @staticmethod
    def divide_by_third(x: float, y: float) -> float:
        """Final static method with exception handling."""
        if y == 0:
            raise ValueError("ZeroDivisionException")
        return x / y

    # Class methods
    @classmethod
    def create_with_defaults(cls) -> "SampleClass":
        """Class method factory."""
        return cls(100, "factory_created")

    # Property methods
    @property
    def computed_value(self) -> int:
        """Property getter."""
        return self.public_value * 2

    @computed_value.setter
    def computed_value(self, value: int) -> None:
        """Property setter."""
        self.public_value = value // 2

    # Private methods
    def _protected_method(self, data: str) -> str:
        """Protected method."""
        return f"protected: {data}"

    def __private_method(self, data: str) -> str:
        """Private method."""
        return f"private: {data}"


class SampleBClass:
    """
    Secondary test class for inheritance and composition testing.
    """

    def __init__(self):
        self.animals: List[str] = []

    def add_animal(self, animal: str) -> List[str]:
        """Add an animal to the list."""
        self.animals = [*self.animals, animal]
        return self.animals

    def delete_animal(self, animal: str) -> List[str]:
        """Remove an animal from the list."""
        self.animals = [a for a in self.animals if a != animal]
        return self.animals

    def get_animals(self) -> List[str]:
        """Get all animals."""
        return self.animals.copy()


class GenericSampleClass:
    """Test class with generic types and advanced Python features."""

    def __init__(self, data: Dict[str, Union[int, str]]):
        self.data = data

    def process_data(
        self, callback: callable, optional_param: Optional[str] = None, *args, **kwargs
    ) -> Dict[str, any]:
        """Method with complex signature including *args and **kwargs."""
        result = callback(self.data, *args, **kwargs)
        if optional_param:
            result["optional"] = optional_param
        return result

    async def async_operation(self, delay: float = 1.0) -> str:
        """Async method for testing async handling."""
        await asyncio.sleep(delay)
        return "async_complete"


class InheritanceSampleClass(SampleClass):
    """Test inheritance scenarios."""

    def __init__(self, public_value: int, extra_param: str):
        super().__init__(public_value)
        self.extra_param = extra_param

    def multiply_two_numbers(self, a: int, b: int) -> int:
        """Override parent method."""
        return super().multiply_two_numbers(a, b) + 1

    def child_specific_method(self, param: bool) -> str:
        """Method specific to child class."""
        return f"child method: {param}"


# Global functions for testing
def sample_global_function() -> str:
    """Global function with no parameters."""
    return "test_function_result"


async def async_global_function(param: str) -> str:
    """Async global function."""
    await asyncio.sleep(0.1)
    return f"async: {param}"


def function_with_complex_params(
    required_param: str,
    optional_param: Optional[int] = None,
    *args: str,
    **kwargs: Union[int, str],
) -> Dict[str, any]:
    """Function with complex parameter signature."""
    return {
        "required": required_param,
        "optional": optional_param,
        "args": args,
        "kwargs": kwargs,
    }


def function_with_union_types(param: Union[int, str, List[int]]) -> Union[str, int]:
    """Function with union types."""
    if isinstance(param, str):
        return len(param)
    elif isinstance(param, list):
        return sum(param)
    return str(param)


# Global variables for testing
MY_GLOBAL_CONSTANT: str = "GLOBAL_VALUE"
my_global_variable: int = 42
my_global_list: List[str] = ["item1", "item2", "item3"]
my_global_dict: Dict[str, int] = {"key1": 1, "key2": 2}


# Exception classes
class CustomTestException(Exception):
    """Custom exception for testing."""

    pass


class CustomTestExceptionWithParams(Exception):
    """Custom exception with parameters."""

    def __init__(self, message: str, error_code: int):
        super().__init__(message)
        self.error_code = error_code


# Dataclass for modern Python features
@dataclass
class SampleDataClass:
    """Dataclass for testing modern Python features."""

    name: str
    value: int = 0
    tags: List[str] = field(default_factory=list)

    def process(self) -> str:
        """Method in dataclass."""
        return f"{self.name}: {self.value}"


# Enum for testing
class SampleEnum(Enum):
    """Enum for testing."""

    OPTION_A = auto()
    OPTION_B = auto()
    OPTION_C = "custom_value"


# Protocol for testing (Python 3.8+)
class SampleProtocol(Protocol):
    """Protocol for testing structural typing."""

    def required_method(self, param: str) -> int:
        """Required method in protocol."""
        ...
