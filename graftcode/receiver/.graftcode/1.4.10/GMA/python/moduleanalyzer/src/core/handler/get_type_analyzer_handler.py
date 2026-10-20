import inspect
from typing import Any

from graftcode_protocol.enums.inheritance_kind import InheritanceKind
from graftcode_protocol.enums.type_kind import TypeKind
from graftcode_protocol.enums.unified_graft_model_type import UnifiedGraftModelType
from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel

from moduleanalyzer.src.core.handler.abstract_handler import AbstractHandler
from moduleanalyzer.src.core.handler.shared.method_dispatch import MethodDispatch
from moduleanalyzer.src.core.handler.shared.shared_comment_doc_handler import (
    SharedCommentDocHandler,
)
from moduleanalyzer.src.core.utils.framework_module_helper import is_framework_module
from moduleanalyzer.src.core.utils.method_filter_helper import MethodFilterHelper


class GetTypeAnalyzerHandler(AbstractHandler):

    def generate_unified_graft_model(
        self,
        analyzed_object: Any,
        parent_command: UnifiedGraftModel,
        handlers: Any,
    ) -> UnifiedGraftModel:
        clazz = analyzed_object

        get_type_command = self.create_unified_graft_model(
            UnifiedGraftModelType.TYPE_DEF
        )
        # Order according to spec: NAMESPACE, TYPENAME, MODULE_FULLNAME, MODULE_HASH, MODIFIER,
        # GENERIC_PARAMETERS, TYPE_DEF (nested), CONSTRUCTOR, FIELD, METHOD, PROPERTY
        get_type_command = self.add_namespace_to_payload(
            get_type_command, clazz, handlers
        )
        get_type_command = self.add_class_name_to_payload(
            get_type_command, clazz, handlers
        )
        get_type_command = self.add_module_full_name_to_payload(
            get_type_command, clazz, handlers, parent_command
        )
        get_type_command = self.add_module_hash_to_payload(
            get_type_command, clazz, handlers
        )
        get_type_command = self.add_modifier_to_payload(
            get_type_command, clazz, handlers
        )
        get_type_command = self.add_generic_parameters_to_payload(
            get_type_command, clazz, handlers
        )
        get_type_command = self.add_type_def_kind_to_payload(get_type_command, clazz)
        get_type_command = self.add_inheritance_to_payload(
            get_type_command, clazz, handlers
        )
        get_type_command = self.add_nested_types_to_payload(
            get_type_command, clazz, handlers, parent_command
        )
        get_type_command = self.add_constructors_to_payload(
            get_type_command, clazz, handlers
        )
        get_type_command = self.add_fields_to_payload(get_type_command, clazz, handlers)
        get_type_command = self.add_methods_to_payload(
            get_type_command, clazz, handlers
        )
        get_type_command = self.add_properties_to_payload(
            get_type_command, clazz, handlers
        )

        return SharedCommentDocHandler.append_to_payload_if_present(
            clazz, get_type_command, handlers
        )

    def add_namespace_to_payload(
        self, command: UnifiedGraftModel, clazz: Any, handlers: Any
    ) -> UnifiedGraftModel:
        return command.add_arg_to_payload(
            handlers.shared_handler.get(
                UnifiedGraftModelType.NAMESPACE
            ).generate_unified_graft_model(clazz.__module__, command, handlers)
        )

    def add_module_full_name_to_payload(
        self,
        command: UnifiedGraftModel,
        clazz: Any,
        handlers: Any,
        library_command: UnifiedGraftModel = None,
    ) -> UnifiedGraftModel:
        context_command = library_command if library_command else command
        return command.add_arg_to_payload(
            handlers.shared_handler.get(
                UnifiedGraftModelType.MODULE_FULL_NAME
            ).generate_unified_graft_model(clazz, context_command, handlers)
        )

    def add_module_hash_to_payload(
        self, command: UnifiedGraftModel, clazz: Any, handlers: Any
    ) -> UnifiedGraftModel:
        return command.add_arg_to_payload(
            handlers.shared_handler.get(
                UnifiedGraftModelType.MODULE_HASH
            ).generate_unified_graft_model(clazz, command, handlers)
        )

    def add_class_name_to_payload(
        self, command: UnifiedGraftModel, clazz: Any, handlers: Any
    ) -> UnifiedGraftModel:
        return command.add_arg_to_payload(
            handlers.shared_handler.get(
                UnifiedGraftModelType.CLASS_NAME
            ).generate_unified_graft_model(clazz.__name__, command, handlers)
        )

    def add_modifier_to_payload(
        self, command: UnifiedGraftModel, clazz: Any, handlers: Any
    ) -> UnifiedGraftModel:
        return command.add_arg_to_payload(
            handlers.shared_handler.get(
                UnifiedGraftModelType.MODIFIER
            ).generate_unified_graft_model(clazz.__name__, command, handlers)
        )

    def add_method_to_payload(
        self,
        get_type_command: UnifiedGraftModel,
        method: Any,
        handlers: Any,
        is_static: bool,
    ) -> UnifiedGraftModel:
        node_type = MethodDispatch.resolve_node_type_for_method(method, is_static)
        return get_type_command.add_arg_to_payload(
            handlers.analyzer_handler.get(node_type).generate_unified_graft_model(
                method, get_type_command, handlers
            )
        )

    def add_instance_method_to_payload(
        self, get_type_command: UnifiedGraftModel, method: Any, handlers: Any
    ) -> UnifiedGraftModel:
        return self.add_method_to_payload(get_type_command, method, handlers, False)

    def add_static_method_to_payload(
        self, get_type_command: UnifiedGraftModel, method: Any, handlers: Any
    ) -> UnifiedGraftModel:
        return self.add_method_to_payload(get_type_command, method, handlers, True)

    def add_constructors_to_payload(
        self, get_type_command: UnifiedGraftModel, clazz: Any, handlers: Any
    ) -> UnifiedGraftModel:
        constructors: list[Any] = []
        for name in dir(clazz):
            if name != "__init__":
                continue
            try:
                method = getattr(clazz, name)
            except (AttributeError, TypeError, ModuleNotFoundError, ImportError):
                continue
            if inspect.isfunction(method):
                constructors.append(method)

        for constructor in constructors:
            if not MethodFilterHelper.matches_filter(
                "__init__",
                handlers.method_filter,
                f"{getattr(clazz, '__module__', '')}.{getattr(clazz, '__name__', '')}",
            ):
                continue
            get_type_command = self.add_constructor_to_payload(
                get_type_command, constructor, handlers
            )
        return get_type_command

    def add_constructor_to_payload(
        self,
        get_type_command: UnifiedGraftModel,
        constructor: Any,
        handlers: Any,
    ) -> UnifiedGraftModel:
        return get_type_command.add_arg_to_payload(
            handlers.analyzer_handler.get(
                UnifiedGraftModelType.CONSTRUCTOR
            ).generate_unified_graft_model(constructor, get_type_command, handlers)
        )

    def add_properties_to_payload(
        self, get_type_command: UnifiedGraftModel, clazz: Any, handlers: Any
    ) -> UnifiedGraftModel:
        """Map @property descriptors to INSTANCE_FIELD payload entries."""
        for name, attr in vars(clazz).items():
            # Skip magic/dunder methods
            if name.startswith("__") and name.endswith("__"):
                continue

            # Skip private/protected properties (single _ prefix)
            if name.startswith("_"):
                continue

            # Check if it's a property descriptor
            if isinstance(attr, property):

                class PropertyAsField:
                    def __init__(self, prop: property, prop_name: str):
                        self.name = prop_name
                        self.fget = getattr(prop, "fget", None)
                        self.fset = getattr(prop, "fset", None)

                get_type_command = self.add_instance_field_to_payload(
                    get_type_command, PropertyAsField(attr, name), handlers
                )
        return get_type_command

    def add_methods_to_payload(
        self, get_type_command: UnifiedGraftModel, clazz: Any, handlers: Any
    ) -> UnifiedGraftModel:
        for name, method in vars(clazz).items():
            # Skip magic/dunder methods - they are handled separately
            # (e.g., __init__ is handled as CONSTRUCTOR)
            if name.startswith("__") and name.endswith("__"):
                continue

            # Private by convention (Python has no protected modifier in UGM)
            if name.startswith("_"):
                continue

            # Skip properties - they are handled separately
            if isinstance(method, property):
                continue

            if callable(method):
                type_full_name = getattr(clazz, "__module__", None)
                if type_full_name:
                    type_full_name = (
                        f"{type_full_name}.{getattr(clazz, '__name__', '')}"
                    )
                if not MethodFilterHelper.matches_filter(
                    name, handlers.method_filter, type_full_name
                ):
                    continue
                if isinstance(method, staticmethod):
                    get_type_command = self.add_static_method_to_payload(
                        get_type_command, method.__func__, handlers
                    )
                else:
                    get_type_command = self.add_instance_method_to_payload(
                        get_type_command, method, handlers
                    )
        return get_type_command

    def add_instance_field_to_payload(
        self, get_type_command: UnifiedGraftModel, field: Any, handlers: Any
    ) -> UnifiedGraftModel:
        return get_type_command.add_arg_to_payload(
            handlers.analyzer_handler.get(
                UnifiedGraftModelType.INSTANCE_FIELD
            ).generate_unified_graft_model(field, get_type_command, handlers)
        )

    def add_static_field_to_payload(
        self, get_type_command: UnifiedGraftModel, field: Any, handlers: Any
    ) -> UnifiedGraftModel:
        return get_type_command.add_arg_to_payload(
            handlers.analyzer_handler.get(
                UnifiedGraftModelType.STATIC_FIELD
            ).generate_unified_graft_model(field, get_type_command, handlers)
        )

    def is_static(self, field_name: str) -> bool:
        try:
            # Store reference to the class being analyzed
            clazz = self.current_class

            # Check if the field exists in the class __dict__ and is a static attribute
            # Use vars() to get the actual descriptor objects (staticmethod, classmethod)
            # rather than getattr() which returns the unwrapped callable
            class_dict = vars(clazz)
            if field_name in class_dict:
                return isinstance(class_dict[field_name], (staticmethod, classmethod))
            return False
        except (AttributeError, TypeError):
            # If there's an error determining if it's static, assume it's not
            return False

    # Save reference to class being analyzed during field processing
    def _is_property_descriptor(self, clazz: Any, field_name: str) -> bool:
        """Check if a field is a @property descriptor in the class hierarchy."""
        for klass in type.mro(clazz) if isinstance(clazz, type) else [clazz]:
            if field_name in vars(klass) and isinstance(
                vars(klass)[field_name], property
            ):
                return True
        return False

    def add_fields_to_payload(
        self, get_type_command: UnifiedGraftModel, clazz: Any, handlers: Any
    ) -> UnifiedGraftModel:
        # Store class reference for use in is_static method
        self.current_class = clazz

        for field_name in dir(clazz):
            if field_name.startswith("_"):
                continue

            try:
                field_value = getattr(clazz, field_name)
            except (AttributeError, TypeError, ModuleNotFoundError, ImportError):
                continue

            if callable(field_value):
                continue

            # Skip properties — they are handled separately by add_properties_to_payload
            if self._is_property_descriptor(clazz, field_name):
                continue

            # Process the field based on whether it's static or instance
            if not self.is_static(field_name):
                get_type_command = self.add_instance_field_to_payload(
                    get_type_command, field_name, handlers
                )
            else:
                get_type_command = self.add_static_field_to_payload(
                    get_type_command, field_name, handlers
                )
        return get_type_command

    def add_generic_parameters_to_payload(
        self, get_type_command: UnifiedGraftModel, clazz: Any, handlers: Any
    ) -> UnifiedGraftModel:
        """Add generic type parameters to the payload."""
        generic_params_handler = handlers.shared_handler.get(
            UnifiedGraftModelType.GENERIC_PARAMETERS
        )
        generic_params = generic_params_handler.generate_unified_graft_model(
            clazz,
            get_type_command,
            handlers,
        )
        get_type_command = get_type_command.add_arg_to_payload(generic_params)
        return get_type_command

    def add_nested_types_to_payload(
        self,
        get_type_command: UnifiedGraftModel,
        clazz: Any,
        handlers: Any,
        parent_command: UnifiedGraftModel,
    ) -> UnifiedGraftModel:
        """Add nested TYPE_DEF (nested classes) to the payload."""
        import inspect

        # Find nested classes - they are attributes of the class
        for name, obj in vars(clazz).items():
            if inspect.isclass(obj):
                # Check if it's a nested class (defined inside this class)
                # Nested classes have __qualname__ that includes parent class name
                if hasattr(obj, "__qualname__") and hasattr(clazz, "__qualname__"):
                    parent_qualname = clazz.__qualname__
                    child_qualname = obj.__qualname__
                    # Check if child is nested in parent (e.g., "OuterClass.NestedClass")
                    if (
                        child_qualname.startswith(parent_qualname + ".")
                        and child_qualname != parent_qualname
                    ):
                        # Generate TYPE_DEF for nested class
                        nested_type = handlers.analyzer_handler.get(
                            UnifiedGraftModelType.TYPE_DEF
                        ).generate_unified_graft_model(obj, parent_command, handlers)
                        get_type_command = get_type_command.add_arg_to_payload(
                            nested_type
                        )
        return get_type_command

    def add_type_def_kind_to_payload(
        self, command: UnifiedGraftModel, clazz: Any
    ) -> UnifiedGraftModel:
        type_kind = self._resolve_type_kind(clazz)
        if type_kind is None:
            return command

        type_def_kind = UnifiedGraftModel(
            command.runtime_name,
            UnifiedGraftModelType.TYPE_DEF_KIND,
            [type_kind.value],
        )
        return command.add_arg_to_payload(type_def_kind)

    @staticmethod
    def _resolve_type_kind(clazz: Any) -> TypeKind | None:
        if not inspect.isclass(clazz):
            return None

        try:
            from abc import ABC
            from typing import Protocol
        except ImportError:
            ABC = None
            Protocol = None

        if Protocol is not None:
            try:
                if issubclass(clazz, Protocol) and clazz is not Protocol:
                    return TypeKind.INTERFACE
            except TypeError:
                pass

        if ABC is not None:
            try:
                if issubclass(clazz, ABC) and clazz is not ABC:
                    abstract_methods = getattr(clazz, "__abstractmethods__", frozenset())
                    if abstract_methods:
                        has_concrete_method = any(
                            not getattr(method, "__isabstractmethod__", False)
                            for name, method in inspect.getmembers(
                                clazz, predicate=inspect.isfunction
                            )
                            if not name.startswith("_")
                        )
                        return (
                            TypeKind.ABSTRACT_CLASS
                            if has_concrete_method
                            else TypeKind.INTERFACE
                        )
            except TypeError:
                pass

        abstract_methods = getattr(clazz, "__abstractmethods__", None)
        if abstract_methods:
            return TypeKind.ABSTRACT_CLASS

        return None

    @staticmethod
    def _should_emit_inheritance_base(base: Any) -> bool:
        if base is object:
            return False
        if not inspect.isclass(base):
            return False
        module = getattr(base, "__module__", "") or ""
        return not is_framework_module(module)

    def add_inheritance_to_payload(
        self, command: UnifiedGraftModel, clazz: Any, handlers: Any
    ) -> UnifiedGraftModel:
        inheritance = UnifiedGraftModel(
            command.runtime_name, UnifiedGraftModelType.TYPE_INHERITANCE, []
        )

        bases = [
            base
            for base in getattr(clazz, "__bases__", ())
            if self._should_emit_inheritance_base(base)
        ]
        for index, base in enumerate(bases):
            kind = (
                InheritanceKind.BASE_CLASS
                if index == 0
                else InheritanceKind.INTERFACE
            )
            inheritance = self.add_inheritance_entry(
                inheritance, base, kind, handlers
            )

        if len(inheritance.payload) == 0:
            return command

        return command.add_arg_to_payload(inheritance)

    def add_inheritance_entry(
        self,
        inheritance: UnifiedGraftModel,
        inherited_type: Any,
        inheritance_kind: InheritanceKind,
        handlers: Any,
    ) -> UnifiedGraftModel:
        type_usage = handlers.shared_handler.get(
            UnifiedGraftModelType.TYPE_USAGE
        ).generate_unified_graft_model(
            inherited_type,
            inheritance,
            handlers,
        )

        entry = UnifiedGraftModel(
            inheritance.runtime_name,
            UnifiedGraftModelType.TYPE_INHERITANCE_ENTRY,
            [inheritance_kind, type_usage],
        )
        return inheritance.add_arg_to_payload(entry)
