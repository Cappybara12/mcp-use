from typing import Any, Optional

from graftcode_protocol.enums.runtime_name import RuntimeName
from graftcode_protocol.enums.unified_graft_model_type import UnifiedGraftModelType
from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel

from .shared_type_handler import SharedTypeHandler, TypeWithNullable


class SharedPrimitiveTypeHandler(SharedTypeHandler):
    """
    Handler for primitive types.
    Matches netcore's SharedPrimitiveTypeHandler implementation.

    Structure: TYPE_USAGE → TYPE_USAGE_PRIMITIVE → [IS_NULLABLE, NAMESPACE, TYPENAME, PRIMITIVE_TYPE, ASSEMBLY_NAME, ASSEMBLY_VERSION]
    """

    def generate_unified_graft_model(
        self,
        analyzed_object: Any,
        _parent_command: Optional[UnifiedGraftModel],
        handlers: Any,
    ) -> UnifiedGraftModel:
        """
        Generates a UnifiedGraftModel for primitive types.

        Structure matches C#:
        - TYPE_USAGE wrapper
        - TYPE_USAGE_PRIMITIVE with payload: [IS_NULLABLE, NAMESPACE, TYPENAME, PRIMITIVE_TYPE, ASSEMBLY_NAME, ASSEMBLY_VERSION]

        :param analyzed_object: The object being analyzed.
        :param _parent_command: The parent command related to the object (unused, can be None).
        :param handlers: A collection of handlers that contains current_library_name
                         for external type detection.
        :return: A UnifiedGraftModel instance representing the type of the
                 analyzed object.
        """
        # Get current library name for external type detection
        current_library_name = None
        import_roots: Optional[frozenset[str]] = None
        if handlers and hasattr(handlers, "current_library_name"):
            current_library_name = handlers.current_library_name
        if handlers and hasattr(handlers, "current_library_import_roots"):
            import_roots = handlers.current_library_import_roots

        # Extract type and nullable state from TypeWithNullable wrapper if present
        if isinstance(analyzed_object, TypeWithNullable):
            type_obj = analyzed_object.type
            is_nullable = analyzed_object.is_nullable
        else:
            type_obj = analyzed_object
            is_nullable = self._get_is_nullable(analyzed_object)

        type_name = self.get_type_name(type_obj, current_library_name)
        object_type = self.get_object_type(type_name)
        module_name = self.get_module_name(type_obj, object_type)

        # For external types, type_name contains full module path prefix
        # (e.g. "sdn_test_simple_car.simple_car.SimpleCar"). Split into namespace and clean class name.
        if "." in type_name:
            namespace_from_type = type_name.rsplit(".", 1)[0]
            class_name = type_name.rsplit(".", 1)[1]
        else:
            namespace_from_type = ""
            class_name = type_name

        namespace = (
            namespace_from_type
            if namespace_from_type
            else self._get_namespace(module_name)
        )

        # Create TYPE_USAGE_PRIMITIVE with payload: [IS_NULLABLE, NAMESPACE, TYPENAME, PRIMITIVE_TYPE, ASSEMBLY_NAME, ASSEMBLY_VERSION]
        # Note: TYPE_USAGE wrapper is created by SharedTypeHandler, not here
        primitive_type = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE, []
        )
        primitive_type = primitive_type.add_arg_to_payload(is_nullable.value)
        primitive_type = primitive_type.add_arg_to_payload(namespace)  # NAMESPACE
        primitive_type = primitive_type.add_arg_to_payload(class_name)  # TYPENAME
        primitive_type = primitive_type.add_arg_to_payload(
            object_type
        )  # PRIMITIVE_TYPE
        primitive_type = primitive_type.add_arg_to_payload(
            self._resolve_assembly_name(
                type_obj,
                object_type,
                module_name,
                current_library_name,
                type_name,
                import_roots,
            )
        )  # ASSEMBLY_NAME
        primitive_type = primitive_type.add_arg_to_payload(
            self._get_assembly_version(module_name)
        )  # ASSEMBLY_VERSION

        return primitive_type

    def _get_namespace(self, module_name: str) -> str:
        """Extracts namespace from module path (package path without last component)."""
        if not module_name:
            return ""
        parts = module_name.split(".")
        if len(parts) > 1:
            return ".".join(parts[:-1])  # All but last component
        return ""

    def _get_assembly_version(self, module_name: str) -> str:
        """Gets package version. Returns empty string as version extraction requires package metadata."""
        # Version extraction would require setup.py/pyproject.toml access
        # For now, return empty string to match structure
        return ""
