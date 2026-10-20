import importlib
import importlib.util
import sys
from typing import Optional, Any


class LazyModuleLoader:
    """Centralized module loader that only executes code when actually needed."""
    _loaded_specs = {}

    @classmethod
    def register_module_path(cls, module_name: str, file_path: str):
        """Register a module for lazy loading without executing it."""
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        cls._loaded_specs[module_name] = spec

    @classmethod
    def get_module(cls, module_name: str) -> Optional[Any]:
        """Get module, loading it only if necessary."""
        # Check if already loaded
        if module_name in sys.modules:
            return sys.modules[module_name]

        # Check if we have a spec for lazy loading
        if module_name in cls._loaded_specs:
            spec = cls._loaded_specs[module_name]
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)  # Execute only when needed
            sys.modules[module_name] = module
            return module

        # Try standard import as fallback
        return importlib.import_module(module_name)

    @classmethod
    def is_module_available(cls, module_name: str) -> bool:
        """Check if module is available without loading it."""
        return (module_name in sys.modules or
                module_name in cls._loaded_specs or
                importlib.util.find_spec(module_name) is not None)

    @classmethod
    def safe_getattr(cls, obj, name):
        """Get an attribute without invoking property getters.

        Class and static methods are still bound, so calls such as
        datetime.fromisoformat receive the type instead of the raw descriptor.
        """
        try:
            value = object.__getattribute__(obj, name)
        except AttributeError:
            try:
                return getattr(obj, name)
            except Exception:
                raise AttributeError(f"Attribute {name} not found in {obj}") from None

        if isinstance(value, property):
            return value

        value_type_name = type(value).__name__
        if isinstance(value, (classmethod, staticmethod)) or value_type_name in (
            "classmethod_descriptor",
            "staticmethod",
        ):
            return getattr(obj, name)

        return value
