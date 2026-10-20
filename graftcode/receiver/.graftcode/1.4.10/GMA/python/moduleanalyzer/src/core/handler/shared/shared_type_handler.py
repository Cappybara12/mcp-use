import types
from typing import Any, Dict, List, Optional, Union, get_args, get_origin

from graftcode_protocol.enums.graft_code_primitive_type import GraftCodePrimitiveType
from graftcode_protocol.enums.is_nullable import IsNullable
from graftcode_protocol.enums.runtime_name import RuntimeName
from graftcode_protocol.enums.unified_graft_model_type import UnifiedGraftModelType
from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel


class TypeWithNullable:
    """
    Wrapper class to preserve nullable state when unwrapping Optional/Union types.
    Matches C# TypeWithNullable utility class.
    """

    def __init__(self, type_obj: Any, is_nullable: IsNullable):
        self.type = type_obj
        self.is_nullable = is_nullable


class SharedTypeHandler:
    def __init__(self) -> None:
        # Mapping Python types to GraftCodePrimitiveType
        self.type_mapping: Dict[str, int] = {
            "NoneType": GraftCodePrimitiveType.VOID.value,
            "str": GraftCodePrimitiveType.STRING.value,
            "int": GraftCodePrimitiveType.INTEGER.value,
            "bool": GraftCodePrimitiveType.BOOLEAN.value,
            "float": GraftCodePrimitiveType.DOUBLE.value,
            "bytes": GraftCodePrimitiveType.GRAFT_MODEL.value,
            "list": GraftCodePrimitiveType.GRAFT_MODEL.value,
            "dict": GraftCodePrimitiveType.GRAFT_MODEL.value,
            "set": GraftCodePrimitiveType.GRAFT_MODEL.value,
            "tuple": GraftCodePrimitiveType.GRAFT_MODEL.value,
            "Any": GraftCodePrimitiveType.UNKNOWN.value,
            "object": GraftCodePrimitiveType.UNKNOWN.value,
        }

    def _get_is_nullable(self, analyzed_object: Any) -> IsNullable:
        """
        Determines if a type is nullable based on the analyzed object.
        A type is nullable if:
        - The analyzed_object is Optional[T] or Union[T, None]
        - The analyzed_object is None or NoneType

        :param analyzed_object: The object being analyzed.
        :return: IsNullable.TRUE if nullable, IsNullable.FALSE otherwise.
        """
        # Check if it's None or NoneType
        if analyzed_object is None or analyzed_object is type(None):
            return IsNullable.TRUE

        # Check for Optional/Union types
        origin = get_origin(analyzed_object)
        if origin is Union:
            args = get_args(analyzed_object)
            # If None is in the union, it's nullable
            if type(None) in args:
                return IsNullable.TRUE

        # Check for Python 3.10+ union syntax (str | None)
        # UnionType is the type used for | syntax in Python 3.10+
        try:
            if (
                isinstance(analyzed_object, types.UnionType)
                or type(analyzed_object).__name__ == "UnionType"
            ):
                args = get_args(analyzed_object)
                if type(None) in args:
                    return IsNullable.TRUE
        except (TypeError, AttributeError):
            # Python < 3.10 or not a union type
            pass

        return IsNullable.FALSE

    @staticmethod
    def _is_list_type(type_obj: Any) -> bool:
        if type_obj is list or type_obj is List:
            return True
        origin = get_origin(type_obj)
        return origin is list or origin is List

    def generate_unified_graft_model(
        self,
        analyzed_object: Any,
        _parent_command: Optional[UnifiedGraftModel],
        handlers: Any,
    ) -> UnifiedGraftModel:
        """
        Generates a UnifiedGraftModel based on the analyzed object type.
        Matches netcore's SharedTypeUsageHandler implementation.

        This handler dispatches to specialized handlers based on the type:
        - TYPE_USAGE_VOID for void types
        - TYPE_USAGE_ARRAY for array types
        - TYPE_USAGE_GENERIC for generic types
        - TYPE_USAGE_GENERIC_ALIAS for generic type parameters
        - TYPE_USAGE_PRIMITIVE for primitive types

        Structure: TYPE_USAGE → [one of: TYPE_USAGE_VOID, TYPE_USAGE_ARRAY, TYPE_USAGE_GENERIC, TYPE_USAGE_GENERIC_ALIAS, TYPE_USAGE_PRIMITIVE]

        :param analyzed_object: The object being analyzed.
        :param _parent_command: The parent command related to the object (unused, can be None).
        :param handlers: A collection of handlers that contains current_library_name
                         for external type detection.
        :return: A UnifiedGraftModel instance representing the type of the
                 analyzed object.
        """
        # Create TYPE_USAGE wrapper (matches C# SharedTypeUsageHandler)
        command = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.TYPE_USAGE, []
        )

        # Generate nested type usage and add to wrapper
        nested_type_usage = self._generate_unified_graft_model_for_type(
            analyzed_object, command, handlers, IsNullable.FALSE
        )

        return command.add_arg_to_payload(nested_type_usage)

    def _generate_unified_graft_model_for_type(
        self,
        analyzed_object_type: Any,
        command: UnifiedGraftModel,
        handlers: Any,
        is_nullable: IsNullable = IsNullable.FALSE,
    ) -> UnifiedGraftModel:
        """
        Generates UnifiedGraftModel for a type, matching C# GenerateUnifiedGraftModelForType.
        Handles nullable unwrapping and delegates to appropriate specialized handlers.

        :param analyzed_object_type: The type being analyzed.
        :param command: The parent command (unused but matches C# signature).
        :param handlers: Collection of handlers.
        :param is_nullable: Current nullable state.
        :return: UnifiedGraftModel for the type (one of: TYPE_USAGE_VOID, TYPE_USAGE_ARRAY, etc.)
        """
        # Check for nullable types first (before generic check, since Optional[T] is generic)
        # Unwrap nullable types to their underlying type and process recursively with isNullable=TRUE
        origin = get_origin(analyzed_object_type)
        if origin is Union:
            args = get_args(analyzed_object_type)
            if type(None) in args:
                # Extract first non-None type
                non_none_types = [arg for arg in args if arg is not type(None)]
                if non_none_types:
                    return self._generate_unified_graft_model_for_type(
                        non_none_types[0], command, handlers, IsNullable.TRUE
                    )
            else:
                # Union without None - unwrap to first type (not generic)
                if args:
                    return self._generate_unified_graft_model_for_type(
                        args[0], command, handlers, is_nullable
                    )

        # Check for Python 3.10+ union syntax (str | None)
        try:
            if (
                isinstance(analyzed_object_type, types.UnionType)
                or type(analyzed_object_type).__name__ == "UnionType"
            ):
                args = get_args(analyzed_object_type)
                if type(None) in args:
                    non_none_types = [arg for arg in args if arg is not type(None)]
                    if non_none_types:
                        return self._generate_unified_graft_model_for_type(
                            non_none_types[0], command, handlers, IsNullable.TRUE
                        )
                else:
                    # Union without None - unwrap to first type
                    if args:
                        return self._generate_unified_graft_model_for_type(
                            args[0], command, handlers, is_nullable
                        )
        except (TypeError, AttributeError):
            # Python < 3.10 or not a union type
            pass

        # Check for delegate/callable types (before void check)
        type_name = self.get_type_name(analyzed_object_type, None)
        if isinstance(type_name, str) and (
            "callable" in type_name.lower()
            or "function" in type_name.lower()
            or "method" in type_name.lower()
        ):
            # Delegate types are handled as primitives with DELEGATE primitive type
            # Preserve nullable state by wrapping if needed
            delegate_obj = (
                TypeWithNullable(analyzed_object_type, is_nullable)
                if is_nullable == IsNullable.TRUE
                else analyzed_object_type
            )
            primitive_handler = handlers.shared_handler.get(
                UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE
            )
            if primitive_handler:
                return primitive_handler.generate_unified_graft_model(
                    delegate_obj, command, handlers
                )

        # Check for void/NoneType
        if (
            analyzed_object_type is None
            or analyzed_object_type is type(None)
            or type_name in ("NoneType", "void")
        ):
            void_handler = handlers.shared_handler.get(
                UnifiedGraftModelType.TYPE_USAGE_VOID
            )
            if void_handler:
                return void_handler.generate_unified_graft_model(
                    analyzed_object_type, command, handlers
                )

        # Check for arrays (List[T] types or runtime list instances)
        # First check if it's a runtime list instance
        if isinstance(analyzed_object_type, list):
            # For runtime instances, infer element type from first element if available
            element_type = (
                type(analyzed_object_type[0]) if analyzed_object_type else Any
            )
            # Create a List[element_type] type annotation for processing
            list_type = List[element_type] if analyzed_object_type else List[Any]
            array_obj = (
                TypeWithNullable(list_type, is_nullable)
                if is_nullable == IsNullable.TRUE
                else list_type
            )
            array_handler = handlers.shared_handler.get(
                UnifiedGraftModelType.TYPE_USAGE_ARRAY
            )
            if array_handler:
                return array_handler.generate_unified_graft_model(
                    array_obj, command, handlers
                )

        # Check for List[T] type annotations
        origin = get_origin(analyzed_object_type)
        if self._is_list_type(analyzed_object_type):
            # Preserve nullable state by wrapping if needed
            array_obj = (
                TypeWithNullable(analyzed_object_type, is_nullable)
                if is_nullable == IsNullable.TRUE
                else analyzed_object_type
            )
            array_handler = handlers.shared_handler.get(
                UnifiedGraftModelType.TYPE_USAGE_ARRAY
            )
            if array_handler:
                return array_handler.generate_unified_graft_model(
                    array_obj, command, handlers
                )

        # Check for generics (but not list/List which are handled as arrays)
        # Dict with type parameters (e.g., Dict[str, int]) should be handled as generic
        # Only exclude bare dict/list types without parameters
        if origin is not None:
            args = get_args(analyzed_object_type)
            # If it has generic arguments and origin is dict, handle as generic
            # Note: get_origin(Dict[str, int]) returns dict, not Dict
            if args and origin is dict:
                generic_obj = (
                    TypeWithNullable(analyzed_object_type, is_nullable)
                    if is_nullable == IsNullable.TRUE
                    else analyzed_object_type
                )
                generic_handler = handlers.shared_handler.get(
                    UnifiedGraftModelType.TYPE_USAGE_GENERIC
                )
                if generic_handler:
                    return generic_handler.generate_unified_graft_model(
                        generic_obj, command, handlers
                    )
            # For other generics (not list/List/dict without args)
            elif origin not in (list, List, dict):
                # Preserve nullable state by wrapping if needed
                generic_obj = (
                    TypeWithNullable(analyzed_object_type, is_nullable)
                    if is_nullable == IsNullable.TRUE
                    else analyzed_object_type
                )
                generic_handler = handlers.shared_handler.get(
                    UnifiedGraftModelType.TYPE_USAGE_GENERIC
                )
                if generic_handler:
                    return generic_handler.generate_unified_graft_model(
                        generic_obj, command, handlers
                    )

        # Check for generic type parameters (single uppercase letters like T, K, V)
        if (
            isinstance(type_name, str)
            and len(type_name) == 1
            and type_name.isupper()
            and type_name not in self.type_mapping
        ):
            # Preserve nullable state by wrapping if needed
            alias_obj = (
                TypeWithNullable(analyzed_object_type, is_nullable)
                if is_nullable == IsNullable.TRUE
                else analyzed_object_type
            )
            alias_handler = handlers.shared_handler.get(
                UnifiedGraftModelType.TYPE_USAGE_GENERIC_ALIAS
            )
            if alias_handler:
                return alias_handler.generate_unified_graft_model(
                    alias_obj, command, handlers
                )

        # Default to primitive handler
        # Preserve nullable state by wrapping if needed
        primitive_obj = (
            TypeWithNullable(analyzed_object_type, is_nullable)
            if is_nullable == IsNullable.TRUE
            else analyzed_object_type
        )
        primitive_handler = handlers.shared_handler.get(
            UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE
        )
        if primitive_handler:
            return primitive_handler.generate_unified_graft_model(
                primitive_obj, command, handlers
            )

        # Fallback: create primitive type usage directly
        primitive_type = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE, []
        )
        current_library_name = None
        import_roots: Optional[frozenset[str]] = None
        if handlers and hasattr(handlers, "current_library_name"):
            current_library_name = handlers.current_library_name
        if handlers and hasattr(handlers, "current_library_import_roots"):
            import_roots = handlers.current_library_import_roots

        fallback_type_obj = (
            analyzed_object_type.type
            if isinstance(analyzed_object_type, TypeWithNullable)
            else analyzed_object_type
        )
        type_name_with_context = self.get_type_name(
            fallback_type_obj, current_library_name
        )
        object_type = self.get_object_type(type_name_with_context)
        module_name = self.get_module_name(fallback_type_obj, object_type)

        primitive_type = primitive_type.add_arg_to_payload(is_nullable.value)
        primitive_type = primitive_type.add_arg_to_payload(
            self._get_namespace(module_name)
        )
        primitive_type = primitive_type.add_arg_to_payload(type_name_with_context)
        primitive_type = primitive_type.add_arg_to_payload(object_type)
        primitive_type = primitive_type.add_arg_to_payload(
            self._resolve_assembly_name(
                fallback_type_obj,
                object_type,
                module_name,
                current_library_name,
                type_name_with_context,
                import_roots,
            )
        )
        primitive_type = primitive_type.add_arg_to_payload(
            self._get_assembly_version(module_name)
        )

        return primitive_type

    def get_type_name(
        self, analyzed_object: Any, current_library_name: Optional[str] = None
    ) -> str:
        """
        Retrieves the name of the type of the analyzed object.

        For external types (from different packages), includes the submodule prefix.
        E.g., SimpleCar from sdn_test_simple_car.simple_car becomes "simple_car.SimpleCar"
        when analyzed from sdn_test_simple_car_repository.

        :param analyzed_object: The object whose type name is being determined.
        :param current_library_name: The name of the library being analyzed (for external type detection).
        :return: The name of the type, or "undefined" if the object is None or "undefined".
        """
        if analyzed_object is None:
            return "undefined"

        # Check for "undefined" string, but avoid comparison with objects that have custom __eq__
        if isinstance(analyzed_object, str) and analyzed_object == "undefined":
            return "undefined"

        # TODO: Temporary solution - for Union/Optional types, extract the first non-None type
        # This should be improved to properly represent Union types in the future
        analyzed_object = self._unwrap_optional_type(analyzed_object)

        # Handle generic types like List[T], Dict[K,V], etc.
        # These have internal names like _GenericAlias that we need to resolve
        origin = get_origin(analyzed_object)
        if origin is not None:
            # It's a generic type - get the origin (e.g., list, dict)
            # and format with the type arguments
            args = get_args(analyzed_object)
            if origin is list or origin is List:
                if args:
                    inner_type = self._get_simple_type_name(
                        args[0], current_library_name
                    )
                    return f"{inner_type}[]"
                return "list"
            elif origin is dict or origin is Dict:
                return "dict"
            # For other generic types, return the origin name
            return getattr(origin, "__name__", str(origin))

        # Get the base type name
        if isinstance(analyzed_object, type):
            type_obj = analyzed_object
            base_name = type_obj.__name__
        else:
            # Python 3.10 typing.Any is _SpecialForm (not a type); type(Any).__name__
            # is "_SpecialForm". Use the form's public name so it maps to UNKNOWN.
            form_name = getattr(analyzed_object, "_name", None)
            if isinstance(form_name, str) and form_name:
                return form_name
            type_obj = type(analyzed_object)
            base_name = type_obj.__name__

        # Check if this is an external type and add submodule prefix if needed
        return self._add_external_type_prefix(type_obj, base_name, current_library_name)

    def _get_simple_type_name(
        self, type_obj: Any, current_library_name: Optional[str] = None
    ) -> str:
        """
        Gets a simple type name from a type object.

        For external types (from different packages), includes the submodule prefix.

        :param type_obj: The type object to get the name from.
        :param current_library_name: The name of the library being analyzed (for external type detection).
        :return: The simple type name, with submodule prefix for external types.
        """
        if isinstance(type_obj, type):
            base_name = type_obj.__name__
            return self._add_external_type_prefix(
                type_obj, base_name, current_library_name
            )
        # Handle nested generics or other cases
        origin = get_origin(type_obj)
        if origin is not None:
            return getattr(origin, "__name__", str(origin))
        form_name = getattr(type_obj, "_name", None)
        if isinstance(form_name, str) and form_name:
            return form_name
        return getattr(type_obj, "__name__", str(type_obj))

    def _add_external_type_prefix(
        self, type_obj: Any, base_name: str, current_library_name: Optional[str]
    ) -> str:
        """
        Adds full module path prefix to type name if it's an external type.

        External type = type from a different package than the one being analyzed.
        E.g., SimpleCar from sdn_test_simple_car.simple_car becomes
        "sdn_test_simple_car.simple_car.SimpleCar" when analyzed from
        sdn_test_simple_car_repository.

        :param type_obj: The type object to check.
        :param base_name: The base type name (e.g., "SimpleCar").
        :param current_library_name: The name of the library being analyzed.
        :return: Type name with full module path prefix for external types, or base_name for local types.
        """
        if not current_library_name:
            return base_name

        # Get the module of the type
        module_name = getattr(type_obj, "__module__", None)
        if not module_name or "." not in module_name:
            return base_name

        # Skip built-in and typing modules
        if module_name in (
            "builtins",
            "typing",
            "typing_extensions",
            "collections.abc",
        ):
            return base_name

        # Split module into parts: e.g., "sdn_test_simple_car.simple_car" -> ["sdn_test_simple_car", "simple_car"]
        parts = module_name.split(".")
        package_name = parts[0]

        # Check if it's an external type (different package than current library)
        if package_name == current_library_name:
            # Local type - no prefix needed
            return base_name

        # External type - add full module path as prefix
        # E.g., "sdn_test_simple_car.simple_car" -> "sdn_test_simple_car.simple_car.SimpleCar"
        # E.g., "pkg.sub1.sub2" -> "pkg.sub1.sub2.ClassName"
        return f"{module_name}.{base_name}"

    def _unwrap_optional_type(self, type_hint: Any) -> Any:
        """
        Unwraps Optional/Union types to get the first non-None type.

        TODO: This is a temporary solution. In the future, Union types should be
        properly represented in the graft model.

        :param type_hint: The type hint to unwrap.
        :return: The first non-None type from a Union, or the original type if not a Union.
        """
        origin = get_origin(type_hint)

        # Handle typing.Union and typing.Optional (which is Union[X, None])
        if origin is Union:
            return self._extract_first_non_none_type(get_args(type_hint), type_hint)

        # Handle Python 3.10+ union syntax (str | None)
        # types.UnionType doesn't have __origin__, check type name instead
        try:
            if (
                isinstance(type_hint, types.UnionType)
                or type(type_hint).__name__ == "UnionType"
            ):
                return self._extract_first_non_none_type(get_args(type_hint), type_hint)
        except (TypeError, AttributeError):
            pass

        return type_hint

    def _extract_first_non_none_type(self, args: tuple, fallback: Any) -> Any:
        """
        Extracts the first non-None type from a tuple of type arguments.

        :param args: Tuple of type arguments from a Union type.
        :param fallback: Value to return if no non-None types found.
        :return: The first non-None type, or fallback if none found.
        """
        non_none_types = [arg for arg in args if arg is not type(None)]
        return non_none_types[0] if non_none_types else fallback

    def get_object_type(self, type_name: str) -> int:
        """
        Maps the given type name to a GraftCodePrimitiveType value.
        Matches netcore's SharedPrimitiveTypeHandler.GetObjectType logic.

        :param type_name: The name of the type to map.
        :return: The corresponding GraftCodePrimitiveType value.
        """
        # Check for delegate types first (matches C# logic)
        if isinstance(type_name, str):
            type_name_lower = type_name.lower()
            if (
                "func" in type_name_lower
                or "action" in type_name_lower
                or "delegate" in type_name_lower
                or "callable" in type_name_lower
            ):
                return GraftCodePrimitiveType.DELEGATE.value

        # Check mapping for known types
        if type_name in self.type_mapping:
            return self.type_mapping[type_name]

        # Default to GRAFT_MODEL (matches C# default)
        return GraftCodePrimitiveType.GRAFT_MODEL.value

    def _strip_submodule_suffix(self, module_name: str) -> str:
        """
        Removes submodule suffix from module name for GCG.NetCore compatibility.
        Only strips when there are exactly 2 parts (package.submodule -> package).
        Deeper paths like 'graftcode_protocol.enums' remain unchanged.

        Example: "sdn_test_simple_car.simple_car" -> "sdn_test_simple_car"
        Example: "graftcode_protocol.enums.runtime_name" -> unchanged

        :param module_name: The module name to process.
        :return: The module name with submodule suffix removed if applicable.
        """
        if module_name and "." in module_name:
            parts = module_name.split(".")
            if len(parts) == 2:
                return parts[0]
        return module_name

    def get_module_name(self, analyzed_object: Any, object_type: int) -> str:
        """
        Retrieves the module name of the analyzed object's type.
        This is equivalent to Assembly.FullName in C#.

        For primitive types (STRING, INTEGER, BOOLEAN, etc.), returns empty string
        since primitives are not framework assemblies and should not be filtered.
        Only complex types (GRAFT_MODEL, UNKNOWN) have their module checked.

        :param analyzed_object: The object whose module name is being determined.
        :param object_type: The GraftCodePrimitiveType value of the object.
        :return: The module name for complex types, or empty string for primitives/unable to determine.
        """
        # Primitive types don't need assembly/module checking - return empty string
        if object_type not in (
            GraftCodePrimitiveType.GRAFT_MODEL.value,
            GraftCodePrimitiveType.UNKNOWN.value,
        ):
            return ""

        if analyzed_object is None:
            return ""

        # Check for "undefined" string, but avoid comparison with objects that have custom __eq__
        if isinstance(analyzed_object, str) and analyzed_object == "undefined":
            return ""

        try:
            # First unwrap Optional/Union types to get the actual type
            unwrapped = self._unwrap_optional_type(analyzed_object)

            # Handle generic types (List[T], Dict[K,V], etc.) - get inner type's module
            origin = get_origin(unwrapped)
            if origin is not None:
                args = get_args(unwrapped)
                if args:
                    # Get the module of the first type argument (e.g., SimpleCar from List[SimpleCar])
                    inner_type = args[0]
                    if isinstance(inner_type, type) and inner_type is not type(None):
                        module = getattr(inner_type, "__module__", None)
                        # For generic inner types, exclude builtins and typing
                        # (we want the actual class module, not builtins for int/str)
                        if module and module not in ("builtins", "typing"):
                            return self._strip_submodule_suffix(module)
                return ""

            # If it's a type object itself
            if isinstance(unwrapped, type):
                module = getattr(unwrapped, "__module__", None)
                # Only exclude typing module, allow builtins for actual type objects
                if module and module != "typing":
                    return self._strip_submodule_suffix(module)
            else:
                # If it's an instance, get its type's module
                obj_type = type(unwrapped)
                module = getattr(obj_type, "__module__", None)
                # Only exclude typing module, allow builtins for instances
                if module and module != "typing":
                    return self._strip_submodule_suffix(module)
        except (AttributeError, TypeError):
            # AttributeError: object lacks __module__ attribute
            # TypeError: type() argument must be a type object
            pass

        return ""

    _FRAMEWORK_MODULES = frozenset(
        {
            "builtins",
            "typing",
            "typing_extensions",
            "collections.abc",
        }
    )

    _FRAMEWORK_MODULE_ROOTS = frozenset(
        {
            "builtins",
            "datetime",
            "pathlib",
            "collections",
            "typing",
            "typing_extensions",
            "abc",
        }
    )

    def _is_framework_module(self, module_name: str) -> bool:
        """Returns True for stdlib/builtin modules that keep import-based assembly names."""
        if not module_name:
            return False
        if module_name in self._FRAMEWORK_MODULES:
            return True
        return module_name.split(".")[0] in self._FRAMEWORK_MODULE_ROOTS

    def _is_local_type(
        self,
        type_obj: Any,
        current_library_name: Optional[str],
        type_name: str,
        import_roots: Optional[frozenset[str]] = None,
    ) -> bool:
        """Returns True when the type belongs to the library being analyzed."""
        if not current_library_name:
            return False
        class_name = (
            type_obj.__name__
            if isinstance(type_obj, type)
            else type(type_obj).__name__
        )
        if type_name == class_name:
            return True

        module = getattr(type_obj, "__module__", None)
        if module and import_roots:
            import_root = module.split(".")[0]
            if import_root in import_roots:
                return True
            if import_root == current_library_name:
                return True

        return False

    def _resolve_assembly_name(
        self,
        type_obj: Any,
        object_type: int,
        module_name: str,
        current_library_name: Optional[str],
        type_name: str,
        import_roots: Optional[frozenset[str]] = None,
    ) -> str:
        """
        Resolves ASSEMBLY_NAME (payload[4]) for TYPE_USAGE_PRIMITIVE complex types.
        Uses distribution package name for local types; import module root for external/stdlib.
        """
        if object_type not in (
            GraftCodePrimitiveType.GRAFT_MODEL.value,
            GraftCodePrimitiveType.UNKNOWN.value,
        ):
            return ""

        if not module_name:
            return ""

        if self._is_framework_module(module_name):
            return self._get_assembly_name(module_name)

        if self._is_local_type(
            type_obj, current_library_name, type_name, import_roots
        ):
            return current_library_name

        return self._get_assembly_name(module_name)

    def _get_namespace(self, module_name: str) -> str:
        """Extracts namespace from module path (package path without last component)."""
        if not module_name:
            return ""
        parts = module_name.split(".")
        if len(parts) > 1:
            return ".".join(parts[:-1])  # All but last component
        return ""

    def _get_assembly_name(self, module_name: str) -> str:
        """Extracts package name from module path (first component)."""
        if not module_name:
            return ""
        parts = module_name.split(".")
        return parts[0] if parts else ""

    def _get_assembly_version(self, module_name: str) -> str:
        """Gets package version. Returns empty string as version extraction requires package metadata."""
        # Version extraction would require setup.py/pyproject.toml access
        # For now, return empty string to match structure
        return ""
