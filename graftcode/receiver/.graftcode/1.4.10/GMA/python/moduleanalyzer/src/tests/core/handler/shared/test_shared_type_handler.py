from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional, Union

from graftcode_protocol.enums.graft_code_primitive_type import GraftCodePrimitiveType
from graftcode_protocol.enums.is_nullable import IsNullable
from graftcode_protocol.enums.runtime_name import RuntimeName
from graftcode_protocol.enums.unified_graft_model_type import UnifiedGraftModelType
from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel

from moduleanalyzer.src.core.handler.handlers import Handlers
from moduleanalyzer.src.core.handler.shared.shared_type_handler import SharedTypeHandler


def test_generate_unified_graft_model_str():
    handler = SharedTypeHandler()
    analyzed_object = "test_string"
    parent_command = None
    handlers = Handlers()

    result = handler.generate_unified_graft_model(
        analyzed_object, parent_command, handlers
    )

    assert result.runtime_name == RuntimeName.Python
    assert result.graft_model_type == UnifiedGraftModelType.TYPE_USAGE


def test_generate_unified_graft_model_int():
    handler = SharedTypeHandler()
    analyzed_object = 123
    parent_command = None
    handlers = Handlers()

    result = handler.generate_unified_graft_model(
        analyzed_object, parent_command, handlers
    )

    assert result.runtime_name == RuntimeName.Python
    assert result.graft_model_type == UnifiedGraftModelType.TYPE_USAGE


def test_generate_unified_graft_model_bool():
    handler = SharedTypeHandler()
    analyzed_object = True
    parent_command = None
    handlers = Handlers()

    result = handler.generate_unified_graft_model(
        analyzed_object, parent_command, handlers
    )

    assert result.runtime_name == RuntimeName.Python
    assert result.graft_model_type == UnifiedGraftModelType.TYPE_USAGE


def test_get_object_type_str():
    handler = SharedTypeHandler()
    assert handler.get_object_type("str") == GraftCodePrimitiveType.STRING.value


def test_get_object_type_int():
    handler = SharedTypeHandler()
    assert handler.get_object_type("int") == GraftCodePrimitiveType.INTEGER.value


def test_get_object_type_bool():
    handler = SharedTypeHandler()
    assert handler.get_object_type("bool") == GraftCodePrimitiveType.BOOLEAN.value


def test_get_object_type_unknown():
    handler = SharedTypeHandler()
    assert (
        handler.get_object_type("unknown_type")
        == GraftCodePrimitiveType.GRAFT_MODEL.value
    )


def test_get_object_type_none():
    handler = SharedTypeHandler()
    assert handler.get_object_type("None") == GraftCodePrimitiveType.GRAFT_MODEL.value


def test_get_object_type_list():
    handler = SharedTypeHandler()
    assert handler.get_object_type("list") == GraftCodePrimitiveType.GRAFT_MODEL.value


def test_get_object_type_any():
    handler = SharedTypeHandler()
    assert handler.get_object_type("Any") == GraftCodePrimitiveType.UNKNOWN.value


def test_get_object_type_dict():
    handler = SharedTypeHandler()
    assert handler.get_object_type("dict") == GraftCodePrimitiveType.GRAFT_MODEL.value


def test_get_object_type_set():
    handler = SharedTypeHandler()
    assert handler.get_object_type("set") == GraftCodePrimitiveType.GRAFT_MODEL.value


def test_get_object_type_tuple():
    handler = SharedTypeHandler()
    assert handler.get_object_type("tuple") == GraftCodePrimitiveType.GRAFT_MODEL.value


# Additional tests for missing type mappings
def test_get_object_type_nonetype():
    handler = SharedTypeHandler()
    assert handler.get_object_type("NoneType") == GraftCodePrimitiveType.VOID.value


def test_get_object_type_float():
    handler = SharedTypeHandler()
    assert handler.get_object_type("float") == GraftCodePrimitiveType.DOUBLE.value


def test_get_object_type_bytes():
    handler = SharedTypeHandler()
    assert handler.get_object_type("bytes") == GraftCodePrimitiveType.GRAFT_MODEL.value


def test_get_object_type_object():
    handler = SharedTypeHandler()
    assert handler.get_object_type("object") == GraftCodePrimitiveType.UNKNOWN.value


# Tests for generate_unified_graft_model with different object types
def test_generate_unified_graft_model_float():
    handler = SharedTypeHandler()
    analyzed_object = 3.14
    parent_command = None
    handlers = Handlers()

    result = handler.generate_unified_graft_model(
        analyzed_object, parent_command, handlers
    )

    # Verify TYPE_USAGE wrapper structure
    assert result.runtime_name == RuntimeName.Python
    assert result.graft_model_type == UnifiedGraftModelType.TYPE_USAGE
    assert len(result.payload) == 1

    # Verify nested TYPE_USAGE_PRIMITIVE
    nested = result.payload[0]
    assert isinstance(nested, UnifiedGraftModel)
    assert nested.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE
    assert nested.payload[0] == IsNullable.FALSE.value
    assert nested.payload[1] == ""  # NAMESPACE
    assert nested.payload[2] == "float"  # TYPENAME
    assert nested.payload[3] == GraftCodePrimitiveType.DOUBLE.value  # PRIMITIVE_TYPE
    assert nested.payload[4] == ""  # ASSEMBLY_NAME
    assert nested.payload[5] == ""  # ASSEMBLY_VERSION


def test_generate_unified_graft_model_bytes():
    handler = SharedTypeHandler()
    analyzed_object = b"test_bytes"
    parent_command = None
    handlers = Handlers()

    result = handler.generate_unified_graft_model(
        analyzed_object, parent_command, handlers
    )

    # Verify TYPE_USAGE wrapper structure
    assert result.runtime_name == RuntimeName.Python
    assert result.graft_model_type == UnifiedGraftModelType.TYPE_USAGE
    assert len(result.payload) == 1

    # Verify nested TYPE_USAGE_PRIMITIVE
    nested = result.payload[0]
    assert isinstance(nested, UnifiedGraftModel)
    assert nested.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE
    assert nested.payload[0] == IsNullable.FALSE.value
    assert nested.payload[1] == ""  # NAMESPACE
    assert nested.payload[2] == "bytes"  # TYPENAME
    assert (
        nested.payload[3] == GraftCodePrimitiveType.GRAFT_MODEL.value
    )  # PRIMITIVE_TYPE
    assert nested.payload[4] == "builtins"  # ASSEMBLY_NAME
    assert nested.payload[5] == ""  # ASSEMBLY_VERSION


def test_generate_unified_graft_model_list():
    handler = SharedTypeHandler()
    analyzed_object = [1, 2, 3]
    parent_command = None
    handlers = Handlers()

    result = handler.generate_unified_graft_model(
        analyzed_object, parent_command, handlers
    )

    # Verify TYPE_USAGE wrapper structure
    assert result.runtime_name == RuntimeName.Python
    assert result.graft_model_type == UnifiedGraftModelType.TYPE_USAGE
    assert len(result.payload) == 1

    # Lists are handled as arrays (List[T]) or primitives depending on type detection
    # For runtime instances, it may be treated as primitive GRAFT_MODEL
    nested = result.payload[0]
    assert isinstance(nested, UnifiedGraftModel)
    # Could be TYPE_USAGE_PRIMITIVE or TYPE_USAGE_ARRAY depending on implementation
    assert nested.graft_model_type in (
        UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE,
        UnifiedGraftModelType.TYPE_USAGE_ARRAY,
    )


def test_generate_unified_graft_model_dict():
    handler = SharedTypeHandler()
    analyzed_object = {"key": "value"}
    parent_command = None
    handlers = Handlers()

    result = handler.generate_unified_graft_model(
        analyzed_object, parent_command, handlers
    )

    # Verify nested structure (matches C# structure)
    assert result.runtime_name == RuntimeName.Python
    assert result.graft_model_type == UnifiedGraftModelType.TYPE_USAGE
    assert len(result.payload) == 1
    nested = result.payload[0]
    assert isinstance(nested, UnifiedGraftModel)
    assert nested.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE
    assert nested.payload[0] == IsNullable.FALSE.value
    assert nested.payload[1] == ""  # NAMESPACE
    assert nested.payload[2] == "dict"  # TYPENAME
    assert (
        nested.payload[3] == GraftCodePrimitiveType.GRAFT_MODEL.value
    )  # PRIMITIVE_TYPE
    assert nested.payload[4] == "builtins"  # ASSEMBLY_NAME


def test_generate_unified_graft_model_set():
    handler = SharedTypeHandler()
    analyzed_object = {1, 2, 3}
    parent_command = None
    handlers = Handlers()

    result = handler.generate_unified_graft_model(
        analyzed_object, parent_command, handlers
    )

    # Verify nested structure (matches C# structure)
    assert result.runtime_name == RuntimeName.Python
    assert result.graft_model_type == UnifiedGraftModelType.TYPE_USAGE
    assert len(result.payload) == 1
    nested = result.payload[0]
    assert isinstance(nested, UnifiedGraftModel)
    assert nested.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE
    assert nested.payload[0] == IsNullable.FALSE.value
    assert nested.payload[2] == "set"  # TYPENAME
    assert (
        nested.payload[3] == GraftCodePrimitiveType.GRAFT_MODEL.value
    )  # PRIMITIVE_TYPE
    assert nested.payload[4] == "builtins"  # ASSEMBLY_NAME


def test_generate_unified_graft_model_tuple():
    handler = SharedTypeHandler()
    analyzed_object = (1, 2, 3)
    parent_command = None
    handlers = Handlers()

    result = handler.generate_unified_graft_model(
        analyzed_object, parent_command, handlers
    )

    # Verify nested structure (matches C# structure)
    assert result.runtime_name == RuntimeName.Python
    assert result.graft_model_type == UnifiedGraftModelType.TYPE_USAGE
    assert len(result.payload) == 1
    nested = result.payload[0]
    assert isinstance(nested, UnifiedGraftModel)
    assert nested.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE
    assert nested.payload[0] == IsNullable.FALSE.value
    assert nested.payload[2] == "tuple"  # TYPENAME
    assert (
        nested.payload[3] == GraftCodePrimitiveType.GRAFT_MODEL.value
    )  # PRIMITIVE_TYPE
    assert nested.payload[4] == "builtins"  # ASSEMBLY_NAME


def test_generate_unified_graft_model_none():
    handler = SharedTypeHandler()
    analyzed_object = None
    parent_command = None
    handlers = Handlers()

    result = handler.generate_unified_graft_model(
        analyzed_object, parent_command, handlers
    )

    # Verify nested structure (matches C# structure)
    # None should be handled as void or primitive depending on implementation
    assert result.runtime_name == RuntimeName.Python
    assert result.graft_model_type == UnifiedGraftModelType.TYPE_USAGE
    assert len(result.payload) == 1
    nested = result.payload[0]
    assert isinstance(nested, UnifiedGraftModel)
    # Could be TYPE_USAGE_VOID or TYPE_USAGE_PRIMITIVE depending on implementation
    assert nested.graft_model_type in (
        UnifiedGraftModelType.TYPE_USAGE_VOID,
        UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE,
    )


def test_generate_unified_graft_model_undefined_string():
    handler = SharedTypeHandler()
    analyzed_object = "undefined"
    parent_command = None
    handlers = Handlers()

    result = handler.generate_unified_graft_model(
        analyzed_object, parent_command, handlers
    )

    # Verify nested structure (matches C# structure)
    assert result.runtime_name == RuntimeName.Python
    assert result.graft_model_type == UnifiedGraftModelType.TYPE_USAGE
    assert len(result.payload) == 1
    nested = result.payload[0]
    assert isinstance(nested, UnifiedGraftModel)
    assert nested.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE
    assert (
        nested.payload[0] == IsNullable.FALSE.value
    )  # String "undefined" is not nullable
    assert nested.payload[2] == "undefined"  # TYPENAME
    assert (
        nested.payload[3] == GraftCodePrimitiveType.GRAFT_MODEL.value
    )  # PRIMITIVE_TYPE
    assert nested.payload[4] == ""  # ASSEMBLY_NAME (empty for "undefined")


def test_generate_unified_graft_model_custom_class():
    handler = SharedTypeHandler()

    class CustomClass:
        pass

    analyzed_object = CustomClass()
    parent_command = None
    handlers = Handlers()

    result = handler.generate_unified_graft_model(
        analyzed_object, parent_command, handlers
    )

    # Verify nested structure (matches C# structure)
    assert result.runtime_name == RuntimeName.Python
    assert result.graft_model_type == UnifiedGraftModelType.TYPE_USAGE
    assert len(result.payload) == 1
    nested = result.payload[0]
    assert isinstance(nested, UnifiedGraftModel)
    assert nested.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE
    assert nested.payload[0] == IsNullable.FALSE.value
    assert nested.payload[2] == "CustomClass"  # TYPENAME
    assert (
        nested.payload[3] == GraftCodePrimitiveType.GRAFT_MODEL.value
    )  # PRIMITIVE_TYPE
    assert (
        nested.payload[4] == __name__.split(".")[0] if "." in __name__ else __name__
    )  # ASSEMBLY_NAME


def test_generate_unified_graft_model_type_object():
    handler = SharedTypeHandler()
    analyzed_object = str  # Pass the type itself, not an instance
    parent_command = None
    handlers = Handlers()

    result = handler.generate_unified_graft_model(
        analyzed_object, parent_command, handlers
    )

    # Verify nested structure (matches C# structure)
    assert result.runtime_name == RuntimeName.Python
    assert result.graft_model_type == UnifiedGraftModelType.TYPE_USAGE
    assert len(result.payload) == 1
    nested = result.payload[0]
    assert isinstance(nested, UnifiedGraftModel)
    assert nested.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE
    assert nested.payload[0] == IsNullable.FALSE.value
    assert nested.payload[2] == "str"  # TYPENAME
    assert nested.payload[3] == GraftCodePrimitiveType.STRING.value  # PRIMITIVE_TYPE
    assert nested.payload[4] == ""  # ASSEMBLY_NAME (primitives don't have module name)


# Tests for get_type_name method edge cases
def test_get_type_name_any():
    handler = SharedTypeHandler()
    assert handler.get_type_name(Any) == "Any"


def test_get_type_name_special_form_uses_public_name():
    class FakeForm:
        _name = "Any"

    handler = SharedTypeHandler()
    assert handler.get_type_name(FakeForm()) == "Any"


def test_get_type_name_none():
    handler = SharedTypeHandler()
    result = handler.get_type_name(None)
    assert result == "undefined"


def test_get_type_name_undefined_string():
    handler = SharedTypeHandler()
    result = handler.get_type_name("undefined")
    assert result == "undefined"


def test_get_type_name_regular_object():
    handler = SharedTypeHandler()
    result = handler.get_type_name("test_string")
    assert result == "str"


def test_get_type_name_type_object():
    handler = SharedTypeHandler()
    result = handler.get_type_name(int)
    assert result == "int"


def test_get_type_name_custom_class():
    handler = SharedTypeHandler()

    class TestClass:
        pass

    result = handler.get_type_name(TestClass())
    assert result == "TestClass"


def test_get_type_name_custom_type():
    handler = SharedTypeHandler()

    class TestClass:
        pass

    result = handler.get_type_name(TestClass)
    assert result == "TestClass"


# Test to ensure type_mapping completeness
def test_type_mapping_length():
    """
    Test to ensure the type_mapping dictionary contains exactly the expected number of entries.
    If this test fails, it means someone added/removed a type mapping without updating the tests.
    Update this test count and add corresponding test cases when adding new type mappings.
    """
    handler = SharedTypeHandler()
    expected_mapping_count = (
        12  # NoneType, str, int, bool, float, bytes, list, dict, set, tuple, Any, object
    )
    actual_mapping_count = len(handler.type_mapping)

    assert actual_mapping_count == expected_mapping_count, (
        f"type_mapping contains {actual_mapping_count} entries, expected {expected_mapping_count}. "
        f"If you added/removed type mappings, update this test and add corresponding test cases. "
        f"Current mappings: {list(handler.type_mapping.keys())}"
    )


# Tests for get_module_name method
def test_get_module_name_builtin_primitive_type():
    """Primitive types (STRING, INTEGER, etc.) return empty string."""
    handler = SharedTypeHandler()
    result = handler.get_module_name(str, GraftCodePrimitiveType.STRING.value)
    assert result == ""


def test_get_module_name_builtin_primitive_instance():
    """Primitive type instances return empty string."""
    handler = SharedTypeHandler()
    result = handler.get_module_name("test_string", GraftCodePrimitiveType.STRING.value)
    assert result == ""


def test_get_module_name_builtin_int():
    """Integer primitive returns empty string."""
    handler = SharedTypeHandler()
    result = handler.get_module_name(123, GraftCodePrimitiveType.INTEGER.value)
    assert result == ""


def test_get_module_name_none():
    handler = SharedTypeHandler()
    result = handler.get_module_name(None, GraftCodePrimitiveType.GRAFT_MODEL.value)
    assert result == ""


def test_get_module_name_undefined_string():
    handler = SharedTypeHandler()
    result = handler.get_module_name("undefined", GraftCodePrimitiveType.STRING.value)
    assert result == ""


def test_get_module_name_custom_class():
    """Custom classes are GRAFT_MODEL type and return their module name."""
    handler = SharedTypeHandler()

    class TestClass:
        pass

    result = handler.get_module_name(
        TestClass(), GraftCodePrimitiveType.GRAFT_MODEL.value
    )
    assert result == __name__


def test_get_module_name_custom_type():
    """Custom class types are GRAFT_MODEL and return their module name."""
    handler = SharedTypeHandler()

    class TestClass:
        pass

    result = handler.get_module_name(
        TestClass, GraftCodePrimitiveType.GRAFT_MODEL.value
    )
    assert result == __name__


# Tests for external framework types (graftcode-python-protocol)
def test_get_module_name_graftcode_protocol_enum():
    """Test module name extraction from graftcode-python-protocol enum types."""
    handler = SharedTypeHandler()
    result = handler.get_module_name(
        RuntimeName, GraftCodePrimitiveType.GRAFT_MODEL.value
    )
    assert result == "graftcode_protocol.enums.runtime_name"


def test_get_module_name_graftcode_protocol_enum_instance():
    """Test module name extraction from graftcode-python-protocol enum instance."""
    handler = SharedTypeHandler()
    result = handler.get_module_name(
        RuntimeName.Python, GraftCodePrimitiveType.GRAFT_MODEL.value
    )
    assert result == "graftcode_protocol.enums.runtime_name"


def test_get_module_name_graftcode_protocol_class():
    """Test module name extraction from graftcode-python-protocol class."""
    handler = SharedTypeHandler()
    result = handler.get_module_name(
        UnifiedGraftModel, GraftCodePrimitiveType.GRAFT_MODEL.value
    )
    assert result == "graftcode_protocol.models.unified_graft_model"


def test_get_module_name_graftcode_protocol_instance():
    """Test module name extraction from graftcode-python-protocol instance."""
    handler = SharedTypeHandler()
    model = UnifiedGraftModel(RuntimeName.Python, UnifiedGraftModelType.TYPE_USAGE, [])
    result = handler.get_module_name(model, GraftCodePrimitiveType.GRAFT_MODEL.value)
    assert result == "graftcode_protocol.models.unified_graft_model"


def test_generate_unified_graft_model_graftcode_enum_type():
    """Test full payload generation with graftcode-python-protocol enum type."""
    handler = SharedTypeHandler()
    analyzed_object = RuntimeName  # Pass the enum class itself
    parent_command = None
    handlers = Handlers()

    result = handler.generate_unified_graft_model(
        analyzed_object, parent_command, handlers
    )

    # Verify nested structure (matches C# structure)
    assert result.runtime_name == RuntimeName.Python
    assert result.graft_model_type == UnifiedGraftModelType.TYPE_USAGE
    assert len(result.payload) == 1
    nested = result.payload[0]
    assert isinstance(nested, UnifiedGraftModel)
    assert nested.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE
    assert nested.payload[2] == "RuntimeName"  # TYPENAME
    assert (
        nested.payload[3] == GraftCodePrimitiveType.GRAFT_MODEL.value
    )  # PRIMITIVE_TYPE
    # ASSEMBLY_NAME is the first component of the module path (e.g., "graftcode_protocol")
    assert nested.payload[4] == "graftcode_protocol"  # ASSEMBLY_NAME


def test_generate_unified_graft_model_graftcode_enum_instance():
    """Test full payload generation with graftcode-python-protocol enum instance."""
    handler = SharedTypeHandler()
    analyzed_object = RuntimeName.Python  # Pass an enum value
    parent_command = None
    handlers = Handlers()

    result = handler.generate_unified_graft_model(
        analyzed_object, parent_command, handlers
    )

    # Verify nested structure (matches C# structure)
    assert result.runtime_name == RuntimeName.Python
    assert result.graft_model_type == UnifiedGraftModelType.TYPE_USAGE
    assert len(result.payload) == 1
    nested = result.payload[0]
    assert isinstance(nested, UnifiedGraftModel)
    assert nested.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE
    assert nested.payload[2] == "RuntimeName"  # TYPENAME
    assert (
        nested.payload[3] == GraftCodePrimitiveType.GRAFT_MODEL.value
    )  # PRIMITIVE_TYPE
    # ASSEMBLY_NAME is the first component of the module path (e.g., "graftcode_protocol")
    assert nested.payload[4] == "graftcode_protocol"  # ASSEMBLY_NAME


def test_generate_unified_graft_model_graftcode_class():
    """Test full payload generation with graftcode-python-protocol class type."""
    handler = SharedTypeHandler()
    analyzed_object = UnifiedGraftModel
    parent_command = None
    handlers = Handlers()

    result = handler.generate_unified_graft_model(
        analyzed_object, parent_command, handlers
    )

    # Verify nested structure (matches C# structure)
    assert result.runtime_name == RuntimeName.Python
    assert result.graft_model_type == UnifiedGraftModelType.TYPE_USAGE
    assert len(result.payload) == 1
    nested = result.payload[0]
    assert isinstance(nested, UnifiedGraftModel)
    assert nested.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE
    assert nested.payload[0] == IsNullable.FALSE.value
    assert nested.payload[2] == "UnifiedGraftModel"  # TYPENAME
    assert (
        nested.payload[3] == GraftCodePrimitiveType.GRAFT_MODEL.value
    )  # PRIMITIVE_TYPE
    # ASSEMBLY_NAME is the first component of the module path (e.g., "graftcode_protocol")
    assert nested.payload[4] == "graftcode_protocol"  # ASSEMBLY_NAME


def test_generate_unified_graft_model_graftcode_instance():
    """Test full payload generation with graftcode-python-protocol instance."""
    handler = SharedTypeHandler()
    model = UnifiedGraftModel(RuntimeName.Python, UnifiedGraftModelType.TYPE_USAGE, [])
    parent_command = None
    handlers = Handlers()

    result = handler.generate_unified_graft_model(model, parent_command, handlers)

    # Verify nested structure (matches C# structure)
    assert result.runtime_name == RuntimeName.Python
    assert result.graft_model_type == UnifiedGraftModelType.TYPE_USAGE
    assert len(result.payload) == 1
    nested = result.payload[0]
    assert isinstance(nested, UnifiedGraftModel)
    assert nested.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE
    assert nested.payload[0] == IsNullable.FALSE.value
    assert nested.payload[2] == "UnifiedGraftModel"  # TYPENAME
    assert (
        nested.payload[3] == GraftCodePrimitiveType.GRAFT_MODEL.value
    )  # PRIMITIVE_TYPE
    # ASSEMBLY_NAME is the first component of the module path (e.g., "graftcode_protocol")
    assert nested.payload[4] == "graftcode_protocol"  # ASSEMBLY_NAME


# Comprehensive tests showing primitive vs complex type module name behavior
def test_primitive_types_return_empty_module_name():
    """Verify that primitive types (STRING, INTEGER, BOOLEAN, etc.) return empty module name."""
    handler = SharedTypeHandler()
    parent_command = None
    handlers = Handlers()

    # Test string primitive
    result_str = handler.generate_unified_graft_model("hello", parent_command, handlers)
    nested_str = result_str.payload[0]
    assert nested_str.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE
    assert (
        nested_str.payload[3] == GraftCodePrimitiveType.STRING.value
    )  # PRIMITIVE_TYPE
    assert nested_str.payload[4] == ""  # ASSEMBLY_NAME (empty for primitives)

    # Test integer primitive
    result_int = handler.generate_unified_graft_model(42, parent_command, handlers)
    nested_int = result_int.payload[0]
    assert nested_int.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE
    assert (
        nested_int.payload[3] == GraftCodePrimitiveType.INTEGER.value
    )  # PRIMITIVE_TYPE
    assert nested_int.payload[4] == ""  # ASSEMBLY_NAME (empty for primitives)

    # Test boolean primitive
    result_bool = handler.generate_unified_graft_model(True, parent_command, handlers)
    nested_bool = result_bool.payload[0]
    assert nested_bool.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE
    assert (
        nested_bool.payload[3] == GraftCodePrimitiveType.BOOLEAN.value
    )  # PRIMITIVE_TYPE
    assert nested_bool.payload[4] == ""  # ASSEMBLY_NAME (empty for primitives)

    # Test float primitive
    result_float = handler.generate_unified_graft_model(3.14, parent_command, handlers)
    nested_float = result_float.payload[0]
    assert nested_float.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE
    assert (
        nested_float.payload[3] == GraftCodePrimitiveType.DOUBLE.value
    )  # PRIMITIVE_TYPE
    assert nested_float.payload[4] == ""  # ASSEMBLY_NAME (empty for primitives)


def test_complex_types_return_module_name():
    """Verify that complex types (GRAFT_MODEL, UNKNOWN) return module name for framework filtering."""
    handler = SharedTypeHandler()
    parent_command = None
    handlers = Handlers()

    # Test list (complex type) - should be TYPE_USAGE_ARRAY
    result_list = handler.generate_unified_graft_model(
        [1, 2, 3], parent_command, handlers
    )
    nested_list = result_list.payload[0]
    assert nested_list.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_ARRAY
    # For arrays, the element type is nested inside

    # Test dict (complex type)
    result_dict = handler.generate_unified_graft_model(
        {"key": "value"}, parent_command, handlers
    )
    nested_dict = result_dict.payload[0]
    assert isinstance(nested_dict, UnifiedGraftModel)
    assert nested_dict.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE
    assert nested_dict.payload[0] == IsNullable.FALSE.value
    assert (
        nested_dict.payload[3] == GraftCodePrimitiveType.GRAFT_MODEL.value
    )  # PRIMITIVE_TYPE
    assert nested_dict.payload[4] == "builtins"  # ASSEMBLY_NAME

    # Test custom class (complex type)
    class CustomClass:
        pass

    result_custom = handler.generate_unified_graft_model(
        CustomClass(), parent_command, handlers
    )
    nested_custom = result_custom.payload[0]
    assert isinstance(nested_custom, UnifiedGraftModel)
    assert nested_custom.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE
    assert nested_custom.payload[0] == IsNullable.FALSE.value
    assert nested_custom.payload[3] == GraftCodePrimitiveType.GRAFT_MODEL.value
    # Module name should be the first component of __name__ after stripping submodule suffix
    expected_module = __name__.split(".")[0] if "." in __name__ else __name__
    assert nested_custom.payload[4] == expected_module  # ASSEMBLY_NAME (import root, no library context)

    # Test object type (UNKNOWN)
    result_object = handler.generate_unified_graft_model(
        object(), parent_command, handlers
    )
    nested_object = result_object.payload[0]
    assert isinstance(nested_object, UnifiedGraftModel)
    assert nested_object.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE
    assert nested_object.payload[0] == IsNullable.FALSE.value
    assert (
        nested_object.payload[3] == GraftCodePrimitiveType.UNKNOWN.value
    )  # PRIMITIVE_TYPE
    assert (
        nested_object.payload[4] == "builtins"
    )  # ASSEMBLY_NAME (UNKNOWN types also get module name)


def test_generate_unified_graft_model_local_type_uses_distribution_package_name():
    """Local complex types use LIBRARY package name, not Python import module root."""
    handler = SharedTypeHandler()

    class ExamplesClass:
        pass

    ExamplesClass.__module__ = "complexGenerics.examples"

    class MockHandlers:
        current_library_name = "complex-generics-and-arrays"
        current_library_import_roots = frozenset({"complexGenerics"})

        def __init__(self):
            self.shared_handler = Handlers().shared_handler

    result = handler.generate_unified_graft_model(ExamplesClass, None, MockHandlers())

    nested = result.payload[0]
    assert isinstance(nested, UnifiedGraftModel)
    assert nested.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE
    assert nested.payload[2] == "ExamplesClass"
    assert nested.payload[4] == "complex-generics-and-arrays"


# Tests for standard library modules
def test_get_module_name_datetime_instance():
    """Test module name extraction from datetime instance."""
    handler = SharedTypeHandler()

    obj = datetime.now()
    result = handler.get_module_name(obj, GraftCodePrimitiveType.GRAFT_MODEL.value)
    assert result == "datetime"


def test_get_module_name_datetime_type():
    """Test module name extraction from datetime type."""
    handler = SharedTypeHandler()

    result = handler.get_module_name(datetime, GraftCodePrimitiveType.GRAFT_MODEL.value)
    assert result == "datetime"


def test_get_module_name_pathlib_path_instance():
    """Test module name extraction from pathlib.Path instance."""
    handler = SharedTypeHandler()

    obj = Path("/tmp")
    result = handler.get_module_name(obj, GraftCodePrimitiveType.GRAFT_MODEL.value)
    assert result == "pathlib"


def test_get_module_name_pathlib_path_type():
    """Test module name extraction from pathlib.Path type."""
    handler = SharedTypeHandler()

    result = handler.get_module_name(Path, GraftCodePrimitiveType.GRAFT_MODEL.value)
    assert result == "pathlib"


def test_get_module_name_collections_deque_instance():
    """Test module name extraction from collections.deque instance."""
    handler = SharedTypeHandler()

    obj = deque([1, 2, 3])
    result = handler.get_module_name(obj, GraftCodePrimitiveType.GRAFT_MODEL.value)
    assert result == "collections"


def test_get_module_name_collections_deque_type():
    """Test module name extraction from collections.deque type."""
    handler = SharedTypeHandler()

    result = handler.get_module_name(deque, GraftCodePrimitiveType.GRAFT_MODEL.value)
    assert result == "collections"


def test_get_module_name_collections_defaultdict():
    """Test module name extraction from collections.defaultdict."""
    handler = SharedTypeHandler()

    obj = defaultdict(int)
    result = handler.get_module_name(obj, GraftCodePrimitiveType.GRAFT_MODEL.value)
    assert result == "collections"


def test_get_module_name_builtin_exception_instance():
    """Test module name extraction from built-in exception instance."""
    handler = SharedTypeHandler()

    obj = ValueError("test error")
    result = handler.get_module_name(obj, GraftCodePrimitiveType.GRAFT_MODEL.value)
    assert result == "builtins"


def test_get_module_name_builtin_exception_type():
    """Test module name extraction from built-in exception type."""
    handler = SharedTypeHandler()

    result = handler.get_module_name(
        ValueError, GraftCodePrimitiveType.GRAFT_MODEL.value
    )
    assert result == "builtins"


def test_get_module_name_custom_exception():
    """Test module name extraction from custom exception."""
    handler = SharedTypeHandler()

    class CustomError(Exception):
        pass

    obj = CustomError("test")
    result = handler.get_module_name(obj, GraftCodePrimitiveType.GRAFT_MODEL.value)
    assert result == __name__


# Tests for third-party library (pytest)
def test_get_module_name_pytest_fixture_instance():
    """Test module name extraction from pytest FixtureDef type.

    Note: For modules with exactly 2 parts (package.submodule), we strip
    to just the package name for GCG.NetCore compatibility.
    """
    handler = SharedTypeHandler()
    from _pytest.fixtures import FixtureDef

    result = handler.get_module_name(
        FixtureDef, GraftCodePrimitiveType.GRAFT_MODEL.value
    )
    # _pytest.fixtures has 2 parts, so it's stripped to _pytest
    assert result == "_pytest"


def test_get_module_name_pytest_config_type():
    """Test module name extraction from pytest Config type.

    Note: For modules with exactly 2 parts (package.submodule), we strip
    to just the package name for GCG.NetCore compatibility.
    """
    handler = SharedTypeHandler()
    from _pytest.config import Config

    result = handler.get_module_name(Config, GraftCodePrimitiveType.GRAFT_MODEL.value)
    # _pytest.config has 2 parts, so it's stripped to _pytest
    assert result == "_pytest"


# Integration tests with standard library types
def test_generate_unified_graft_model_datetime():
    """Test full payload generation with datetime instance."""
    handler = SharedTypeHandler()

    analyzed_object = datetime.now()
    parent_command = None
    handlers = Handlers()

    result = handler.generate_unified_graft_model(
        analyzed_object, parent_command, handlers
    )

    # Verify nested structure (matches C# structure)
    assert result.runtime_name == RuntimeName.Python
    assert result.graft_model_type == UnifiedGraftModelType.TYPE_USAGE
    assert len(result.payload) == 1
    nested = result.payload[0]
    assert isinstance(nested, UnifiedGraftModel)
    assert nested.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE
    assert nested.payload[2] == "datetime"  # TYPENAME
    assert (
        nested.payload[3] == GraftCodePrimitiveType.GRAFT_MODEL.value
    )  # PRIMITIVE_TYPE
    assert nested.payload[4] == "datetime"  # ASSEMBLY_NAME


def test_generate_unified_graft_model_pathlib():
    """Test full payload generation with pathlib.Path instance."""
    handler = SharedTypeHandler()

    analyzed_object = Path("/tmp/test")
    parent_command = None
    handlers = Handlers()

    result = handler.generate_unified_graft_model(
        analyzed_object, parent_command, handlers
    )

    # Verify nested structure (matches C# structure)
    assert result.runtime_name == RuntimeName.Python
    assert result.graft_model_type == UnifiedGraftModelType.TYPE_USAGE
    assert len(result.payload) == 1
    nested = result.payload[0]
    assert isinstance(nested, UnifiedGraftModel)
    assert nested.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE
    assert nested.payload[0] == IsNullable.FALSE.value
    assert nested.payload[2] in ["PosixPath", "WindowsPath"]  # TYPENAME (depends on OS)
    assert (
        nested.payload[3] == GraftCodePrimitiveType.GRAFT_MODEL.value
    )  # PRIMITIVE_TYPE
    assert nested.payload[4] == "pathlib"  # ASSEMBLY_NAME


def test_generate_unified_graft_model_collections_deque():
    """Test full payload generation with collections.deque instance."""
    handler = SharedTypeHandler()

    analyzed_object = deque([1, 2, 3])
    parent_command = None
    handlers = Handlers()

    result = handler.generate_unified_graft_model(
        analyzed_object, parent_command, handlers
    )

    # Verify nested structure (matches C# structure)
    assert result.runtime_name == RuntimeName.Python
    assert result.graft_model_type == UnifiedGraftModelType.TYPE_USAGE
    assert len(result.payload) == 1
    nested = result.payload[0]
    assert isinstance(nested, UnifiedGraftModel)
    assert nested.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE
    assert nested.payload[2] == "deque"  # TYPENAME
    assert (
        nested.payload[3] == GraftCodePrimitiveType.GRAFT_MODEL.value
    )  # PRIMITIVE_TYPE
    assert nested.payload[4] == "collections"  # ASSEMBLY_NAME


def test_generate_unified_graft_model_exception():
    """Test full payload generation with built-in exception."""
    handler = SharedTypeHandler()

    analyzed_object = ValueError("test error")
    parent_command = None
    handlers = Handlers()

    result = handler.generate_unified_graft_model(
        analyzed_object, parent_command, handlers
    )

    # Verify nested structure (matches C# structure)
    assert result.runtime_name == RuntimeName.Python
    assert result.graft_model_type == UnifiedGraftModelType.TYPE_USAGE
    assert len(result.payload) == 1
    nested = result.payload[0]
    assert isinstance(nested, UnifiedGraftModel)
    assert nested.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE
    assert nested.payload[0] == IsNullable.FALSE.value
    assert nested.payload[2] == "ValueError"  # TYPENAME
    assert (
        nested.payload[3] == GraftCodePrimitiveType.GRAFT_MODEL.value
    )  # PRIMITIVE_TYPE
    assert nested.payload[4] == "builtins"  # ASSEMBLY_NAME


# Tests for Optional/Union type unwrapping (temporary solution)
def test_get_type_name_optional_str():
    """Test that Optional[str] unwraps to 'str'."""
    handler = SharedTypeHandler()
    result = handler.get_type_name(Optional[str])
    assert result == "str"


def test_get_type_name_optional_int():
    """Test that Optional[int] unwraps to 'int'."""
    handler = SharedTypeHandler()
    result = handler.get_type_name(Optional[int])
    assert result == "int"


def test_get_type_name_union_str_none():
    """Test that Union[str, None] unwraps to 'str'."""
    handler = SharedTypeHandler()
    result = handler.get_type_name(Union[str, None])
    assert result == "str"


def test_get_type_name_union_int_none():
    """Test that Union[int, None] unwraps to 'int'."""
    handler = SharedTypeHandler()
    result = handler.get_type_name(Union[int, None])
    assert result == "int"


def test_get_type_name_python310_union_syntax():
    """Test that str | None (Python 3.10+ syntax) unwraps to 'str'."""
    handler = SharedTypeHandler()
    # Using eval to avoid syntax error on older Python versions
    union_type = str | None
    result = handler.get_type_name(union_type)
    assert result == "str"


def test_get_type_name_union_with_multiple_types():
    """Test Union with multiple non-None types returns first type."""
    handler = SharedTypeHandler()
    result = handler.get_type_name(Union[str, int, None])
    assert result == "str"


def test_get_type_name_optional_custom_class():
    """Test that Optional[CustomClass] unwraps to 'CustomClass'."""
    handler = SharedTypeHandler()

    class CustomClass:
        pass

    result = handler.get_type_name(Optional[CustomClass])
    assert result == "CustomClass"


def test_generate_unified_graft_model_optional_str():
    """Test full payload generation with Optional[str]."""
    handler = SharedTypeHandler()

    handlers = Handlers()
    result = handler.generate_unified_graft_model(Optional[str], None, handlers)

    # Verify nested structure (matches C# structure)
    assert result.runtime_name == RuntimeName.Python
    assert result.graft_model_type == UnifiedGraftModelType.TYPE_USAGE
    assert len(result.payload) == 1
    nested = result.payload[0]
    assert isinstance(nested, UnifiedGraftModel)
    assert nested.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE
    assert nested.payload[0] == IsNullable.TRUE.value  # Optional makes it nullable
    assert nested.payload[2] == "str"  # TYPENAME
    assert nested.payload[3] == GraftCodePrimitiveType.STRING.value  # PRIMITIVE_TYPE


def test_generate_unified_graft_model_union_int_none():
    """Test full payload generation with Union[int, None]."""
    handler = SharedTypeHandler()
    handlers = Handlers()

    result = handler.generate_unified_graft_model(Union[int, None], None, handlers)

    # Verify TYPE_USAGE wrapper structure
    assert result.runtime_name == RuntimeName.Python
    assert result.graft_model_type == UnifiedGraftModelType.TYPE_USAGE
    assert len(result.payload) == 1

    # Verify nested TYPE_USAGE_PRIMITIVE with nullable=True
    nested = result.payload[0]
    assert isinstance(nested, UnifiedGraftModel)
    assert nested.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE
    assert nested.payload[0] == IsNullable.TRUE.value  # Union[int, None] is nullable
    assert nested.payload[2] == "int"  # TYPENAME
    assert nested.payload[3] == GraftCodePrimitiveType.INTEGER.value


def test_get_is_nullable_none():
    """Unit test for _get_is_nullable with None."""
    handler = SharedTypeHandler()
    assert handler._get_is_nullable(None) == IsNullable.TRUE


def test_get_is_nullable_none_type():
    """Unit test for _get_is_nullable with type(None)."""
    handler = SharedTypeHandler()
    assert handler._get_is_nullable(type(None)) == IsNullable.TRUE


def test_get_is_nullable_optional():
    """Unit test for _get_is_nullable with Optional[str]."""
    handler = SharedTypeHandler()
    assert handler._get_is_nullable(Optional[str]) == IsNullable.TRUE


def test_get_is_nullable_union_with_none():
    """Unit test for _get_is_nullable with Union[int, None]."""
    handler = SharedTypeHandler()
    assert handler._get_is_nullable(Union[int, None]) == IsNullable.TRUE


def test_get_is_nullable_union_without_none():
    """Unit test for _get_is_nullable with Union[int, str] (no None)."""
    handler = SharedTypeHandler()
    assert handler._get_is_nullable(Union[int, str]) == IsNullable.FALSE


def test_get_is_nullable_regular_type():
    """Unit test for _get_is_nullable with regular type."""
    handler = SharedTypeHandler()
    assert handler._get_is_nullable(str) == IsNullable.FALSE
    assert handler._get_is_nullable(int) == IsNullable.FALSE
    assert handler._get_is_nullable(bool) == IsNullable.FALSE


def test_get_is_nullable_python310_union_syntax():
    """Unit test for _get_is_nullable with Python 3.10+ union syntax."""
    handler = SharedTypeHandler()
    # Note: This test may not work in Python < 3.10
    try:
        # Python 3.10+ union syntax: str | None
        union_type = str | None
        assert handler._get_is_nullable(union_type) == IsNullable.TRUE
    except TypeError:
        # Python < 3.10 doesn't support | syntax
        pass


# Tests for complex type structures with IsNullable
def test_generate_unified_graft_model_list_with_is_nullable():
    """Test list type with IsNullable."""
    handler = SharedTypeHandler()
    handlers = Handlers()
    result = handler.generate_unified_graft_model([1, 2, 3], None, handlers)

    # Verify nested structure
    assert result.graft_model_type == UnifiedGraftModelType.TYPE_USAGE
    nested = result.payload[0]
    assert nested.graft_model_type in (
        UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE,
        UnifiedGraftModelType.TYPE_USAGE_ARRAY,
    )


def test_generate_unified_graft_model_dict_with_is_nullable():
    """Test dict type with IsNullable."""
    handler = SharedTypeHandler()
    handlers = Handlers()
    result = handler.generate_unified_graft_model({"key": "value"}, None, handlers)

    # Verify nested structure
    assert result.graft_model_type == UnifiedGraftModelType.TYPE_USAGE
    nested = result.payload[0]
    assert nested.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE
    assert nested.payload[0] == IsNullable.FALSE.value
    assert nested.payload[2] == "dict"


def test_generate_unified_graft_model_tuple_with_is_nullable():
    """Test tuple type with IsNullable."""
    handler = SharedTypeHandler()
    handlers = Handlers()
    result = handler.generate_unified_graft_model((1, 2, 3), None, handlers)

    # Verify nested structure
    assert result.graft_model_type == UnifiedGraftModelType.TYPE_USAGE
    nested = result.payload[0]
    assert nested.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE
    assert nested.payload[0] == IsNullable.FALSE.value
    assert nested.payload[2] == "tuple"


def test_generate_unified_graft_model_set_with_is_nullable():
    """Test set type with IsNullable."""
    handler = SharedTypeHandler()
    handlers = Handlers()
    result = handler.generate_unified_graft_model({1, 2, 3}, None, handlers)

    # Verify nested structure (matches C# structure)
    assert result.graft_model_type == UnifiedGraftModelType.TYPE_USAGE
    assert len(result.payload) == 1
    nested = result.payload[0]
    assert isinstance(nested, UnifiedGraftModel)
    assert nested.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE
    assert nested.payload[0] == IsNullable.FALSE.value
    assert nested.payload[2] == "set"  # TYPENAME
    assert (
        nested.payload[3] == GraftCodePrimitiveType.GRAFT_MODEL.value
    )  # PRIMITIVE_TYPE


def test_generate_unified_graft_model_optional_list():
    """Test Optional[List[str]] with IsNullable."""
    handler = SharedTypeHandler()
    handlers = Handlers()
    result = handler.generate_unified_graft_model(Optional[List[str]], None, handlers)

    # Verify nested structure - should be TYPE_USAGE_ARRAY with nullable=True
    assert result.graft_model_type == UnifiedGraftModelType.TYPE_USAGE
    nested = result.payload[0]
    assert nested.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_ARRAY
    assert nested.payload[0] == IsNullable.TRUE.value  # Optional makes it nullable


def test_generate_unified_graft_model_union_list_none():
    """Test Union[List[str], None] with IsNullable."""
    handler = SharedTypeHandler()
    handlers = Handlers()
    result = handler.generate_unified_graft_model(
        Union[List[str], None], None, handlers
    )

    # Verify nested structure - should be TYPE_USAGE_ARRAY with nullable=True
    assert result.graft_model_type == UnifiedGraftModelType.TYPE_USAGE
    nested = result.payload[0]
    assert nested.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_ARRAY
    assert (
        nested.payload[0] == IsNullable.TRUE.value
    )  # Union with None makes it nullable


def test_generate_unified_graft_model_nested_optional():
    """Test nested Optional types."""
    handler = SharedTypeHandler()
    # Optional[Optional[str]] should still be nullable
    handlers = Handlers()
    result = handler.generate_unified_graft_model(
        Optional[Optional[str]], None, handlers
    )

    # Verify nested structure
    assert result.graft_model_type == UnifiedGraftModelType.TYPE_USAGE
    nested = result.payload[0]
    assert isinstance(nested, UnifiedGraftModel)
    assert nested.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE
    assert nested.payload[0] == IsNullable.TRUE.value
    assert nested.payload[2] == "str"
    assert nested.payload[3] == GraftCodePrimitiveType.STRING.value


def test_generate_unified_graft_model_union_multiple_types():
    """Test Union with multiple types including None."""
    handler = SharedTypeHandler()
    handlers = Handlers()
    result = handler.generate_unified_graft_model(Union[str, int, None], None, handlers)

    # Verify nested structure
    assert result.graft_model_type == UnifiedGraftModelType.TYPE_USAGE
    nested = result.payload[0]
    assert nested.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE
    assert nested.payload[0] == IsNullable.TRUE.value  # Contains None
    assert nested.payload[2] == "str"  # First non-None type
    assert nested.payload[3] == GraftCodePrimitiveType.STRING.value


def test_generate_unified_graft_model_union_without_none():
    """Test Union without None should be non-nullable."""
    handler = SharedTypeHandler()
    handlers = Handlers()
    result = handler.generate_unified_graft_model(Union[str, int], None, handlers)

    # Verify nested structure (matches C# structure)
    assert result.graft_model_type == UnifiedGraftModelType.TYPE_USAGE
    nested = result.payload[0]
    assert isinstance(nested, UnifiedGraftModel)
    assert nested.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE
    assert nested.payload[0] == IsNullable.FALSE.value  # No None in union
    assert nested.payload[2] == "str"  # TYPENAME (first type in union)
    assert nested.payload[3] == GraftCodePrimitiveType.STRING.value  # PRIMITIVE_TYPE


def test_unwrap_optional_type_non_union():
    """Test that non-Union types are returned unchanged."""
    handler = SharedTypeHandler()

    # Regular types should pass through unchanged
    assert handler._unwrap_optional_type(str) is str
    assert handler._unwrap_optional_type(int) is int
    assert handler._unwrap_optional_type(list) is list


# Tests for external type prefix functionality
def test_add_external_type_prefix_no_library_name():
    """Test that no prefix is added when current_library_name is None."""
    handler = SharedTypeHandler()

    class ExternalClass:
        pass

    result = handler._add_external_type_prefix(ExternalClass, "ExternalClass", None)
    assert result == "ExternalClass"


def test_add_external_type_prefix_same_package():
    """Test that no prefix is added for types from the same package."""
    handler = SharedTypeHandler()

    # Create a mock class with __module__ set to the same package
    class LocalClass:
        pass

    LocalClass.__module__ = "my_package.my_module"

    result = handler._add_external_type_prefix(LocalClass, "LocalClass", "my_package")
    assert result == "LocalClass"


def test_add_external_type_prefix_different_package():
    """Test that full module path prefix is added for types from a different package."""
    handler = SharedTypeHandler()

    # Create a mock class with __module__ set to a different package
    class ExternalClass:
        pass

    ExternalClass.__module__ = "external_package.submodule"

    result = handler._add_external_type_prefix(
        ExternalClass, "ExternalClass", "my_package"
    )
    assert result == "external_package.submodule.ExternalClass"


def test_add_external_type_prefix_deep_module_path():
    """Test that full module path is added for deep module hierarchies."""
    handler = SharedTypeHandler()

    class DeepClass:
        pass

    DeepClass.__module__ = "external_package.sub1.sub2.sub3"

    result = handler._add_external_type_prefix(DeepClass, "DeepClass", "my_package")
    assert result == "external_package.sub1.sub2.sub3.DeepClass"


def test_add_external_type_prefix_builtin_skipped():
    """Test that builtin types don't get prefix."""
    handler = SharedTypeHandler()

    result = handler._add_external_type_prefix(str, "str", "my_package")
    assert result == "str"


def test_add_external_type_prefix_single_part_module():
    """Test handling of types with single-part module name (no dot)."""
    handler = SharedTypeHandler()

    # Types from modules without submodules (e.g., builtins) should not get prefix
    # Since str.__module__ is 'builtins' (no dot), no prefix is added
    result = handler._add_external_type_prefix(int, "int", "my_package")
    assert result == "int"


def test_get_type_name_with_external_type():
    """Test get_type_name returns full module path prefixed name for external types."""
    handler = SharedTypeHandler()

    class ExternalClass:
        pass

    ExternalClass.__module__ = "external_package.submodule"

    result = handler.get_type_name(ExternalClass, "my_package")
    assert result == "external_package.submodule.ExternalClass"


def test_get_type_name_with_local_type():
    """Test get_type_name returns simple name for local types."""
    handler = SharedTypeHandler()

    class LocalClass:
        pass

    LocalClass.__module__ = "my_package.my_module"

    result = handler.get_type_name(LocalClass, "my_package")
    assert result == "LocalClass"


def test_get_type_name_without_library_context():
    """Test get_type_name returns simple name when no library context provided."""
    handler = SharedTypeHandler()

    class SomeClass:
        pass

    SomeClass.__module__ = "some_package.some_module"

    result = handler.get_type_name(SomeClass)  # No current_library_name
    assert result == "SomeClass"


def test_generate_unified_graft_model_external_type_with_handlers():
    """Test full payload generation with external type and handlers context."""
    handler = SharedTypeHandler()

    class ExternalClass:
        pass

    ExternalClass.__module__ = "external_package.submodule"

    # Create mock handlers with current_library_name
    class MockHandlers:
        current_library_name = "my_package"

        def __init__(self):
            self.shared_handler = Handlers().shared_handler

    result = handler.generate_unified_graft_model(ExternalClass, None, MockHandlers())

    # Verify nested structure (matches C# structure)
    assert result.graft_model_type == UnifiedGraftModelType.TYPE_USAGE
    nested = result.payload[0]
    assert isinstance(nested, UnifiedGraftModel)
    assert nested.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE
    assert (
        nested.payload[1] == "external_package.submodule"
    )  # NAMESPACE (full module path for external type)
    assert nested.payload[2] == "ExternalClass"  # TYPENAME (class name only)
    assert (
        nested.payload[4] == "external_package"
    )  # ASSEMBLY_NAME (external import root)


def test_generate_unified_graft_model_local_type_with_handlers():
    """Test full payload generation with local type and handlers context."""
    handler = SharedTypeHandler()

    class LocalClass:
        pass

    LocalClass.__module__ = "my_package.my_module"

    # Create mock handlers with current_library_name
    class MockHandlers:
        current_library_name = "my_package"

        def __init__(self):
            self.shared_handler = Handlers().shared_handler

    result = handler.generate_unified_graft_model(LocalClass, None, MockHandlers())

    # Verify nested structure (matches C# structure)
    assert result.graft_model_type == UnifiedGraftModelType.TYPE_USAGE
    nested = result.payload[0]
    assert isinstance(nested, UnifiedGraftModel)
    assert nested.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE
    assert nested.payload[0] == IsNullable.FALSE.value
    assert nested.payload[2] == "LocalClass"  # TYPENAME (local type, no prefix)
    assert (
        nested.payload[4] == "my_package"
    )  # ASSEMBLY_NAME (package name from library context)
