"""
Comprehensive functional tests for nested TYPE_USAGE structure.

Tests verify that TYPE_USAGE is only the top-level entry point,
and nested structures contain specific types directly without TYPE_USAGE wrappers.
"""
from typing import Dict, List, Optional, Union

from graftcode_protocol.enums.graft_code_primitive_type import (
    GraftCodePrimitiveType,
)
from graftcode_protocol.enums.is_nullable import IsNullable
from graftcode_protocol.enums.runtime_name import RuntimeName
from graftcode_protocol.enums.unified_graft_model_type import (
    UnifiedGraftModelType,
)
from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel

from moduleanalyzer.src.core.handler.handlers import Handlers
from moduleanalyzer.src.core.handler.shared.shared_type_handler import SharedTypeHandler


def assert_type_usage_structure(result: UnifiedGraftModel, expected_nested_type: UnifiedGraftModelType):
    """
    Helper to assert TYPE_USAGE wrapper structure.
    
    Args:
        result: The UnifiedGraftModel result from handler
        expected_nested_type: The expected nested type (e.g., TYPE_USAGE_PRIMITIVE)
    """
    # Top level should be TYPE_USAGE
    assert result.runtime_name == RuntimeName.Python
    assert result.graft_model_type == UnifiedGraftModelType.TYPE_USAGE
    assert len(result.payload) == 1, "TYPE_USAGE should contain exactly one nested type"
    
    # Nested type should be the specific type (not wrapped in TYPE_USAGE)
    nested_type = result.payload[0]
    assert isinstance(nested_type, UnifiedGraftModel)
    assert nested_type.graft_model_type == expected_nested_type
    assert nested_type.runtime_name == RuntimeName.Python
    
    return nested_type


def test_primitive_type_structure():
    """Test that primitive types have correct nested structure."""
    handler = SharedTypeHandler()
    handlers = Handlers()
    
    result = handler.generate_unified_graft_model("test_string", None, handlers)
    
    # Verify TYPE_USAGE wrapper
    nested = assert_type_usage_structure(result, UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE)
    
    # Verify PRIMITIVE_TYPE_USAGE payload: [IS_NULLABLE, NAMESPACE, TYPENAME, PRIMITIVE_TYPE, ASSEMBLY_NAME, ASSEMBLY_VERSION]
    assert nested.payload[0] == IsNullable.FALSE.value
    assert nested.payload[1] == ""  # NAMESPACE
    assert nested.payload[2] == "str"  # TYPENAME
    assert nested.payload[3] == GraftCodePrimitiveType.STRING.value  # PRIMITIVE_TYPE
    assert nested.payload[4] == ""  # ASSEMBLY_NAME
    assert nested.payload[5] == ""  # ASSEMBLY_VERSION


def test_array_type_structure():
    """Test that array types have correct nested structure."""
    handler = SharedTypeHandler()
    handlers = Handlers()
    
    result = handler.generate_unified_graft_model(List[int], None, handlers)
    
    # Verify TYPE_USAGE wrapper
    nested = assert_type_usage_structure(result, UnifiedGraftModelType.TYPE_USAGE_ARRAY)
    
    # Verify ARRAY_TYPE_USAGE payload: [IS_NULLABLE, ARRAY_DIMENSION, <nested type>]
    assert nested.payload[0] == IsNullable.FALSE.value
    assert nested.payload[1] == 1  # ARRAY_DIMENSION
    assert isinstance(nested.payload[2], UnifiedGraftModel)
    
    # Element type should be TYPE_USAGE_PRIMITIVE (NOT wrapped in TYPE_USAGE)
    element_type = nested.payload[2]
    assert element_type.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE
    assert element_type.payload[2] == "int"
    assert element_type.payload[3] == GraftCodePrimitiveType.INTEGER.value


def test_untyped_list_structure():
    """Test that an untyped list is represented as an array of unknown elements."""
    handler = SharedTypeHandler()
    handlers = Handlers()

    result = handler.generate_unified_graft_model(list, None, handlers)

    nested = assert_type_usage_structure(
        result, UnifiedGraftModelType.TYPE_USAGE_ARRAY
    )
    assert nested.payload[0] == IsNullable.FALSE.value
    assert nested.payload[1] == 1

    element_type = nested.payload[2]
    assert (
        element_type.graft_model_type
        == UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE
    )
    # Element primitive: [IS_NULLABLE, NAMESPACE, TYPENAME, PRIMITIVE_TYPE, ASSEMBLY_NAME, ASSEMBLY_VERSION]
    assert element_type.payload[2] == "Any"
    assert element_type.payload[3] == GraftCodePrimitiveType.UNKNOWN.value
    assert element_type.payload[4] == ""


def test_untyped_typing_list_structure():
    """Untyped typing.List is an array of unknown elements, same as list."""
    handler = SharedTypeHandler()
    handlers = Handlers()

    result = handler.generate_unified_graft_model(List, None, handlers)

    nested = assert_type_usage_structure(
        result, UnifiedGraftModelType.TYPE_USAGE_ARRAY
    )
    element_type = nested.payload[2]
    assert element_type.payload[2] == "Any"
    assert element_type.payload[3] == GraftCodePrimitiveType.UNKNOWN.value
    assert element_type.payload[4] == ""


def test_nested_array_structure():
    """Test nested arrays (List[List[int]])."""
    handler = SharedTypeHandler()
    handlers = Handlers()
    
    result = handler.generate_unified_graft_model(List[List[int]], None, handlers)
    
    nested = assert_type_usage_structure(result, UnifiedGraftModelType.TYPE_USAGE_ARRAY)
    
    # Outer array
    assert nested.payload[0] == IsNullable.FALSE.value
    assert nested.payload[1] == 2  # ARRAY_DIMENSION (nested lists)
    
    # Inner array type (should be TYPE_USAGE_ARRAY directly, not wrapped)
    inner_array = nested.payload[2]
    assert inner_array.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_ARRAY
    assert inner_array.payload[1] == 1  # Inner dimension
    
    # Element type should be primitive
    element_type = inner_array.payload[2]
    assert element_type.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE
    assert element_type.payload[2] == "int"


def test_generic_type_structure():
    """Test that generic types have correct nested structure."""
    handler = SharedTypeHandler()
    handlers = Handlers()
    
    result = handler.generate_unified_graft_model(Dict[str, int], None, handlers)
    
    nested = assert_type_usage_structure(result, UnifiedGraftModelType.TYPE_USAGE_GENERIC)
    
    # Verify GENERIC_TYPE_USAGE payload: [IS_NULLABLE, <nested type> (generic type), <nested type>[] (generic arguments)]
    assert nested.payload[0] == IsNullable.FALSE.value
    
    # Generic type itself (dict) should be TYPE_USAGE_PRIMITIVE (not wrapped)
    generic_type = nested.payload[1]
    assert generic_type.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE
    assert generic_type.payload[2] == "dict"
    
    # Generic arguments should be nested types directly (not wrapped)
    key_type = nested.payload[2]
    value_type = nested.payload[3]
    
    assert key_type.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE
    assert key_type.payload[2] == "str"
    
    assert value_type.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE
    assert value_type.payload[2] == "int"


def test_complex_generic_structure():
    """Test complex generic with nested generics."""
    handler = SharedTypeHandler()
    handlers = Handlers()
    
    # Dict[str, List[int]]
    result = handler.generate_unified_graft_model(Dict[str, List[int]], None, handlers)
    
    nested = assert_type_usage_structure(result, UnifiedGraftModelType.TYPE_USAGE_GENERIC)
    
    # Key type: str (primitive)
    key_type = nested.payload[2]
    assert key_type.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE
    assert key_type.payload[2] == "str"
    
    # Value type: List[int] (array, not wrapped in TYPE_USAGE)
    value_type = nested.payload[3]
    assert value_type.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_ARRAY
    assert value_type.payload[1] == 1
    
    # Element type of array should be primitive
    element_type = value_type.payload[2]
    assert element_type.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE
    assert element_type.payload[2] == "int"


def test_optional_primitive_structure():
    """Test Optional[str] preserves nullable state."""
    handler = SharedTypeHandler()
    handlers = Handlers()
    
    result = handler.generate_unified_graft_model(Optional[str], None, handlers)
    
    nested = assert_type_usage_structure(result, UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE)
    
    # Should be nullable
    assert nested.payload[0] == IsNullable.TRUE.value
    assert nested.payload[2] == "str"
    assert nested.payload[3] == GraftCodePrimitiveType.STRING.value


def test_optional_array_structure():
    """Test Optional[List[int]] preserves nullable state."""
    handler = SharedTypeHandler()
    handlers = Handlers()
    
    result = handler.generate_unified_graft_model(Optional[List[int]], None, handlers)
    
    nested = assert_type_usage_structure(result, UnifiedGraftModelType.TYPE_USAGE_ARRAY)
    
    # Array itself should be nullable
    assert nested.payload[0] == IsNullable.TRUE.value
    assert nested.payload[1] == 1
    
    # Element type should not be nullable (unless explicitly Optional)
    element_type = nested.payload[2]
    assert element_type.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE
    assert element_type.payload[0] == IsNullable.FALSE.value


def test_void_type_structure():
    """Test void type structure."""
    handler = SharedTypeHandler()
    handlers = Handlers()
    
    result = handler.generate_unified_graft_model(type(None), None, handlers)
    
    nested = assert_type_usage_structure(result, UnifiedGraftModelType.TYPE_USAGE_VOID)
    
    # VOID_TYPE_USAGE has empty payload
    assert len(nested.payload) == 0


def test_complex_nested_structure():
    """
    Test a very complex nested structure:
    Dict[str, Optional[List[Dict[int, str]]]]
    
    Structure should be:
    TYPE_USAGE
      └── TYPE_USAGE_GENERIC (Dict)
          ├── TYPE_USAGE_PRIMITIVE (dict)
          ├── TYPE_USAGE_PRIMITIVE (str) - key
          └── TYPE_USAGE_GENERIC (Optional[List[...]])
              ├── TYPE_USAGE_PRIMITIVE (Optional/Union)
              └── TYPE_USAGE_ARRAY (List)
                  ├── TYPE_USAGE_ARRAY payload
                  └── TYPE_USAGE_GENERIC (Dict)
                      ├── TYPE_USAGE_PRIMITIVE (dict)
                      ├── TYPE_USAGE_PRIMITIVE (int) - key
                      └── TYPE_USAGE_PRIMITIVE (str) - value
    """
    handler = SharedTypeHandler()
    handlers = Handlers()
    
    # Create complex type: Dict[str, Optional[List[Dict[int, str]]]]
    complex_type = Dict[str, Optional[List[Dict[int, str]]]]
    result = handler.generate_unified_graft_model(complex_type, None, handlers)
    
    # Top level: TYPE_USAGE wrapper
    nested = assert_type_usage_structure(result, UnifiedGraftModelType.TYPE_USAGE_GENERIC)
    
    # Dict generic type
    assert nested.payload[0] == IsNullable.FALSE.value
    
    # Dict type itself
    dict_type = nested.payload[1]
    assert dict_type.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE
    assert dict_type.payload[2] == "dict"
    
    # Key type: str
    key_type = nested.payload[2]
    assert key_type.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE
    assert key_type.payload[2] == "str"
    
    # Value type: Optional[List[Dict[int, str]]]
    # This should be handled as a generic (Optional/Union) or array depending on implementation
    value_type = nested.payload[3]
    
    # The value type should be either TYPE_USAGE_ARRAY (if Optional is unwrapped) 
    # or TYPE_USAGE_GENERIC (if Optional is preserved)
    # Based on our implementation, Optional[List[...]] unwraps to List[...] with nullable=True
    assert value_type.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_ARRAY
    assert value_type.payload[0] == IsNullable.TRUE.value  # Optional makes it nullable
    
    # List element type: Dict[int, str]
    list_element = value_type.payload[2]
    assert list_element.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_GENERIC
    
    # Dict[int, str] structure
    inner_dict_type = list_element.payload[1]
    assert inner_dict_type.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE
    assert inner_dict_type.payload[2] == "dict"
    
    # Key: int
    inner_key = list_element.payload[2]
    assert inner_key.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE
    assert inner_key.payload[2] == "int"
    
    # Value: str
    inner_value = list_element.payload[3]
    assert inner_value.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE
    assert inner_value.payload[2] == "str"


def test_no_nested_type_usage_wrappers():
    """
    Verify that nested types are NOT wrapped in TYPE_USAGE.
    Only the top-level entry point should be TYPE_USAGE.
    """
    handler = SharedTypeHandler()
    handlers = Handlers()
    
    result = handler.generate_unified_graft_model(Dict[str, List[int]], None, handlers)
    
    # Top level is TYPE_USAGE
    assert result.graft_model_type == UnifiedGraftModelType.TYPE_USAGE
    
    # Nested generic
    nested_generic = result.payload[0]
    assert nested_generic.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_GENERIC
    
    # Generic arguments should NOT be TYPE_USAGE
    key_type = nested_generic.payload[2]
    assert key_type.graft_model_type != UnifiedGraftModelType.TYPE_USAGE
    assert key_type.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE
    
    value_type = nested_generic.payload[3]
    assert value_type.graft_model_type != UnifiedGraftModelType.TYPE_USAGE
    assert value_type.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_ARRAY
    
    # Array element should NOT be TYPE_USAGE
    element_type = value_type.payload[2]
    assert element_type.graft_model_type != UnifiedGraftModelType.TYPE_USAGE
    assert element_type.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE


def test_expected_unified_graft_model_structure():
    """
    Comprehensive test that writes and asserts the expected UnifiedGraftModel structure
    for a complex type: Dict[str, Optional[List[int]]]
    """
    handler = SharedTypeHandler()
    handlers = Handlers()
    
    complex_type = Dict[str, Optional[List[int]]]
    result = handler.generate_unified_graft_model(complex_type, None, handlers)
    
    # Expected structure:
    # TYPE_USAGE
    #   └── TYPE_USAGE_GENERIC
    #       ├── IS_NULLABLE (FALSE)
    #       ├── TYPE_USAGE_PRIMITIVE (dict) - generic type itself
    #       ├── TYPE_USAGE_PRIMITIVE (str) - key type
    #       └── TYPE_USAGE_ARRAY (List[int]) - value type
    #           ├── IS_NULLABLE (TRUE) - from Optional
    #           ├── ARRAY_DIMENSION (1)
    #           └── TYPE_USAGE_PRIMITIVE (int) - element type
    
    # Top level
    assert result.graft_model_type == UnifiedGraftModelType.TYPE_USAGE
    assert len(result.payload) == 1
    
    # Generic type
    generic = result.payload[0]
    assert generic.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_GENERIC
    assert generic.payload[0] == IsNullable.FALSE.value
    
    # Dict type itself
    dict_type = generic.payload[1]
    assert dict_type.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE
    assert dict_type.payload[2] == "dict"
    
    # Key: str
    key = generic.payload[2]
    assert key.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE
    assert key.payload[2] == "str"
    assert key.payload[3] == GraftCodePrimitiveType.STRING.value
    
    # Value: Optional[List[int]] -> List[int] with nullable=True
    value = generic.payload[3]
    assert value.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_ARRAY
    assert value.payload[0] == IsNullable.TRUE.value  # Optional makes it nullable
    assert value.payload[1] == 1  # Array dimension
    
    # Element: int
    element = value.payload[2]
    assert element.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE
    assert element.payload[2] == "int"
    assert element.payload[3] == GraftCodePrimitiveType.INTEGER.value
    
    # Verify no TYPE_USAGE wrappers in nested structures
    assert dict_type.graft_model_type != UnifiedGraftModelType.TYPE_USAGE
    assert key.graft_model_type != UnifiedGraftModelType.TYPE_USAGE
    assert value.graft_model_type != UnifiedGraftModelType.TYPE_USAGE
    assert element.graft_model_type != UnifiedGraftModelType.TYPE_USAGE
