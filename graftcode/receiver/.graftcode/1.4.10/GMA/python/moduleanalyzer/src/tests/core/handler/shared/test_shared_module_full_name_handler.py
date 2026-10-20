from unittest.mock import patch

from moduleanalyzer.src.core.handler.shared.shared_module_full_name_handler import (
    SharedModuleFullNameHandler,
)


class SampleClass:
    """Sample class for testing."""

    def method(self):
        pass


class MainModuleClass:
    """Class that appears to be from __main__ module."""

    __module__ = "__main__"


class NonStringModuleClass:
    """Class with non-string __module__ attribute."""

    __module__ = 12345  # Non-string value


def sample_function():
    """Sample function for testing."""
    pass


def main_module_function():
    """Function that appears to be from __main__ module."""
    pass


# Simulate __main__ module function
main_module_function.__module__ = "__main__"


def test_generate_unified_graft_model_class_method():
    """Test with a class method."""
    handler = SharedModuleFullNameHandler()
    result = handler.generate_unified_graft_model(SampleClass().method, None, None)
    assert result == __name__


def test_generate_unified_graft_model_function():
    """Test with a regular function."""
    handler = SharedModuleFullNameHandler()
    result = handler.generate_unified_graft_model(sample_function, None, None)
    assert result == __name__


def test_generate_unified_graft_model_non_callable():
    """Test with non-callable object."""
    handler = SharedModuleFullNameHandler()
    result = handler.generate_unified_graft_model("not_a_callable", None, None)
    assert result == "unnamed module"


def test_generate_unified_graft_model_builtin_function():
    """Test with builtin function."""
    handler = SharedModuleFullNameHandler()
    result = handler.generate_unified_graft_model(len, None, None)
    assert result == "builtins"


def test_generate_unified_graft_model_main_module_class():
    """Test with class from __main__ module (should return unnamed module)."""
    handler = SharedModuleFullNameHandler()
    obj = MainModuleClass()
    result = handler.generate_unified_graft_model(obj, None, None)
    assert result == "unnamed module"


def test_generate_unified_graft_model_main_module_function():
    """Test with function from __main__ module (should return unnamed module)."""
    handler = SharedModuleFullNameHandler()
    result = handler.generate_unified_graft_model(main_module_function, None, None)
    assert result == "unnamed module"


def test_generate_unified_graft_model_non_string_module():
    """Test with object that has non-string __module__ attribute."""
    handler = SharedModuleFullNameHandler()
    obj = NonStringModuleClass()
    result = handler.generate_unified_graft_model(obj, None, None)
    # Should handle non-string module gracefully
    assert isinstance(result, str)


def test_generate_unified_graft_model_module_attribute_exception():
    """Test when accessing __module__ attribute raises exception."""
    handler = SharedModuleFullNameHandler()

    class ExceptionRaisingClass:
        @property
        def __module__(self):
            raise Exception("Access error")

    obj = ExceptionRaisingClass()
    result = handler.generate_unified_graft_model(obj, None, None)
    assert result == "null"


def test_generate_unified_graft_model_inspect_getmodule_exception():
    """Test when inspect.getmodule raises exception."""
    handler = SharedModuleFullNameHandler()

    class TestObject:
        __module__ = None

    obj = TestObject()

    with patch("inspect.getmodule", side_effect=Exception("Inspect error")):
        result = handler.generate_unified_graft_model(obj, None, None)
        assert result == "null"


def test_generate_unified_graft_model_inspect_getmodule_none():
    """Test when inspect.getmodule returns None."""
    handler = SharedModuleFullNameHandler()

    class TestObject:
        __module__ = None

    obj = TestObject()

    with patch("inspect.getmodule", return_value=None):
        result = handler.generate_unified_graft_model(obj, None, None)
        assert result == "unnamed module"


def test_generate_unified_graft_model_inspect_getmodule_no_name():
    """Test when inspect.getmodule returns module without __name__."""
    handler = SharedModuleFullNameHandler()

    class TestObject:
        __module__ = None

    obj = TestObject()

    # Create a module object without __name__
    class ModuleWithoutName:
        pass

    mock_module = ModuleWithoutName()

    with patch("inspect.getmodule", return_value=mock_module):
        result = handler.generate_unified_graft_model(obj, None, None)
        assert result == "unnamed module"


def test_generate_unified_graft_model_inspect_getmodule_main_name():
    """Test when inspect.getmodule returns module with __main__ name."""
    handler = SharedModuleFullNameHandler()

    class TestObject:
        __module__ = None

    obj = TestObject()

    # Create a module object with __main__ as name
    class ModuleWithMainName:
        __name__ = "__main__"

    mock_module = ModuleWithMainName()

    with patch("inspect.getmodule", return_value=mock_module):
        result = handler.generate_unified_graft_model(obj, None, None)
        assert result == "unnamed module"


def test_generate_unified_graft_model_valid_module_name():
    """Test with object having valid module name."""
    handler = SharedModuleFullNameHandler()

    class TestClass:
        pass

    TestClass.__module__ = "my.test.module"
    obj = TestClass()

    result = handler.generate_unified_graft_model(obj, None, None)
    assert result == "my.test.module"


def test_generate_unified_graft_model_module_attribute_access_fails():
    """Test when __module__ attribute access fails but hasattr succeeds."""
    handler = SharedModuleFullNameHandler()

    class ProblematicClass:
        def __getattribute__(self, name):
            if name == "__module__":
                raise AttributeError("Module access failed")
            return super().__getattribute__(name)

    obj = ProblematicClass()
    result = handler.generate_unified_graft_model(obj, None, None)
    # When attribute access fails, it should fall back to inspect.getmodule
    # which will likely succeed and return the current module name
    assert result == "unnamed module"


def test_generate_unified_graft_model_empty_module_string():
    """Test with object having empty string as module name."""
    handler = SharedModuleFullNameHandler()

    class EmptyModuleClass:
        __module__ = ""

    obj = EmptyModuleClass()
    result = handler.generate_unified_graft_model(obj, None, None)
    # Empty string should be returned as is (it's a valid string)
    assert result == ""


def test_generate_unified_graft_model_none_module():
    """Test with object having None as module name."""
    handler = SharedModuleFullNameHandler()

    class NoneModuleClass:
        __module__ = None

    obj = NoneModuleClass()
    result = handler.generate_unified_graft_model(obj, None, None)
    # Should fall back to inspect.getmodule since None is not a string
    assert isinstance(result, str)


def test_generate_unified_graft_model_inspect_fallback_success():
    """Test successful fallback to inspect.getmodule."""
    handler = SharedModuleFullNameHandler()

    class TestObject:
        __module__ = None

    obj = TestObject()

    # Create a module object with a specific name
    class ModuleWithName:
        __name__ = "fallback.module"

    mock_module = ModuleWithName()

    with patch("inspect.getmodule", return_value=mock_module):
        result = handler.generate_unified_graft_model(obj, None, None)
        assert result == "fallback.module"


def test_generate_unified_graft_model_removes_submodule_suffix():
    """Test that submodule suffix is removed when it matches library name pattern."""
    handler = SharedModuleFullNameHandler()

    class TestClass:
        __module__ = "sdncenter_currency_converter.converter"

    # Create a mock parent_command with library_namespace in payload[0] and library name in payload[1]
    class MockParentCommand:
        def __init__(self):
            self.payload = ["", "sdncenter_currency_converter", "0.2.0", "Python 3.8"]

    obj = TestClass()
    parent_command = MockParentCommand()

    result = handler.generate_unified_graft_model(obj, parent_command, None)
    # Should remove ".converter" suffix since "sdncenter_currency_converter" matches library name
    assert result == "sdncenter_currency_converter"


def test_generate_unified_graft_model_keeps_full_name_when_library_name_doesnt_match():
    """Test that full module name is kept when library name doesn't match package."""
    handler = SharedModuleFullNameHandler()

    class TestClass:
        __module__ = "some_other_package.converter"

    # Create a mock parent_command with library_namespace in payload[0] and different library name in payload[1]
    class MockParentCommand:
        def __init__(self):
            self.payload = ["", "sdncenter_currency_converter", "0.2.0", "Python 3.8"]

    obj = TestClass()
    parent_command = MockParentCommand()

    result = handler.generate_unified_graft_model(obj, parent_command, None)
    # Should keep full name since "some_other_package" doesn't match library name
    assert result == "some_other_package.converter"


def test_generate_unified_graft_model_no_dot_in_module_name():
    """Test that module name without dot is returned as-is."""
    handler = SharedModuleFullNameHandler()

    class TestClass:
        __module__ = "simple_module"

    class MockParentCommand:
        def __init__(self):
            self.payload = ["", "simple_module", "1.0.0", "Python 3.8"]

    obj = TestClass()
    parent_command = MockParentCommand()

    result = handler.generate_unified_graft_model(obj, parent_command, None)
    # Should return as-is since there's no submodule
    assert result == "simple_module"
