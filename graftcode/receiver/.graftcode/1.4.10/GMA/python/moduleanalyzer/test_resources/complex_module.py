"""
Complex Python module for advanced testing scenarios.
Tests decorators, context managers, generators, and more.
"""

import asyncio
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, ContextManager, Generator, Iterator


# Decorator functions
def timing_decorator(func: Callable) -> Callable:
    """Decorator for timing function execution."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        # Simulate timing
        result = func(*args, **kwargs)
        return result

    return wrapper


def retry_decorator(max_retries: int = 3):
    """Parameterized decorator for retrying operations."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise e
            return None

        return wrapper

    return decorator


class ComplexClass:
    """Complex class with advanced Python features."""

    def __init__(self, initial_data: list):
        self._data = initial_data

    @timing_decorator
    def process_data(self, multiplier: int) -> list:
        """Method with decorator."""
        return [x * multiplier for x in self._data]

    @retry_decorator(max_retries=5)
    def unreliable_operation(self, fail_rate: float = 0.5) -> str:
        """Method that might fail, with retry decorator."""
        import random

        if random.random() < fail_rate:
            raise RuntimeError("Operation failed")
        return "Success"

    def __iter__(self) -> Iterator[Any]:
        """Make class iterable."""
        return iter(self._data)

    def __len__(self) -> int:
        """Length support."""
        return len(self._data)

    def __getitem__(self, index: int) -> Any:
        """Index access."""
        return self._data[index]

    def __setitem__(self, index: int, value: Any) -> None:
        """Index assignment."""
        self._data[index] = value

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self._data.clear()
        return False

    @property
    def data_size(self) -> int:
        """Property getter."""
        return len(self._data)

    @data_size.setter
    def data_size(self, value: int) -> None:
        """Property setter - resize data."""
        if value > len(self._data):
            self._data.extend([0] * (value - len(self._data)))
        else:
            self._data = self._data[:value]


class MetaTestClass(type):
    """Metaclass for testing metaclass analysis."""

    def __new__(cls, name, bases, attrs):
        # Add a method to all classes created with this metaclass
        attrs["meta_method"] = lambda self: f"Created by {cls.__name__}"
        return super().__new__(cls, name, bases, attrs)


class ClassWithMeta(metaclass=MetaTestClass):
    """Class using custom metaclass."""

    def __init__(self, value: str):
        self.value = value


# Generator functions
def simple_generator(n: int) -> Generator[int, None, None]:
    """Simple generator function."""
    for i in range(n):
        yield i


def fibonacci_generator(limit: int) -> Generator[int, None, None]:
    """Fibonacci sequence generator."""
    a, b = 0, 1
    while a < limit:
        yield a
        a, b = b, a + b


# Context manager functions
@contextmanager
def temporary_value(obj: Any, attr: str, temp_value: Any) -> ContextManager[None]:
    """Context manager for temporarily changing an attribute."""
    original_value = getattr(obj, attr)
    setattr(obj, attr, temp_value)
    try:
        yield
    finally:
        setattr(obj, attr, original_value)


# Async functions
async def async_data_processor(data: list, delay: float = 0.1) -> list:
    """Async function for processing data."""
    result = []
    for item in data:
        await asyncio.sleep(delay)
        result.append(item * 2)
    return result


async def async_generator_function(n: int) -> Generator[int, None, None]:
    """Async generator function."""
    for i in range(n):
        await asyncio.sleep(0.01)
        yield i


# Functions with complex signatures
def function_with_all_param_types(
    positional_only: str,
    /,  # Python 3.8+ positional-only separator
    regular_param: int,
    default_param: str = "default",
    *args: Any,
    keyword_only: bool,
    keyword_with_default: float = 1.0,
    **kwargs: Any,
) -> dict:
    """Function demonstrating all parameter types."""
    return {
        "positional_only": positional_only,
        "regular_param": regular_param,
        "default_param": default_param,
        "args": args,
        "keyword_only": keyword_only,
        "keyword_with_default": keyword_with_default,
        "kwargs": kwargs,
    }


# Functions that were previously lambda assignments
def lambda_function(x, y):
    return x + y


def complex_lambda(data):
    return [item for item in data if isinstance(item, (int, float))]


# Nested functions
def outer_function(multiplier: int):
    """Function containing nested function."""

    def inner_function(value: int) -> int:
        """Nested function."""
        return value * multiplier

    return inner_function


# Exception handling functions
def function_with_exception_handling(risky_operation: bool = False) -> str:
    """Function demonstrating exception handling."""
    try:
        if risky_operation:
            raise ValueError("Risky operation failed")
        return "Success"
    except ValueError as e:
        return f"Caught ValueError: {e}"
    except Exception as e:
        return f"Caught unexpected error: {e}"
    finally:
        # Cleanup code
        pass


# Global variables with complex types
COMPLEX_GLOBAL_DATA = {
    "nested_dict": {"level_2": {"level_3": "deep_value"}},
    "list_of_dicts": [{"id": 1, "name": "item1"}, {"id": 2, "name": "item2"}],
}


def complex_global_function():
    return "complex_lambda_result"
