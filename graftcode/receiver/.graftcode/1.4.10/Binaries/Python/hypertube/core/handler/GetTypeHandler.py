import ast
import os
import sys

from hypertube.core.handler.AbstractHandler import AbstractHandler
from hypertube.core.handler.LoadLibraryHandler import LoadLibraryHandler
from hypertube.core.namespaceCache.NamespaceCache import NamespaceCache
from hypertube.core.typeCache.TypeCache import TypeCache
from hypertube.core.valueTypesParser.ValueTypeParser import ValueTypeParser
from hypertube.utils.LazyModuleLoader import LazyModuleLoader


class GetTypeHandler(AbstractHandler):
    def __init__(self):
        self._required_parameters_count = 1
        self.namespace_cache = NamespaceCache()
        self.type_cache = TypeCache()

    def process(self, command):
        try:
            self.validate(command, self._required_parameters_count, self.__class__.__name__)

            type_to_return = self._get_type_from_payload(command)

            if type_to_return is None:
                raise Exception(f"Type {command.payload[0]} not found")

            caches_are_empty = (
                self.namespace_cache.is_namespace_cache_empty()
                and self.type_cache.is_type_cache_empty()
            )
            is_allowed = (
                ValueTypeParser.is_parsable_value_type(type_to_return)
                or caches_are_empty
                or self.namespace_cache.is_type_allowed(type_to_return)
                or self.type_cache.is_type_allowed(type_to_return)
            )
            if not is_allowed:
                allowed_namespaces = ", ".join(self.namespace_cache.get_cached_namespaces())
                allowed_types = ", ".join(self.type_cache.get_cached_types())
                raise Exception(
                    f"Type {type_to_return.__name__} not allowed. \nAllowed namespaces: {allowed_namespaces}\nAllowed types: {allowed_types}")

            return type_to_return

        except Exception as e:
            exc_type = type(e)
            sys_path = "\n".join(sys.path)
            available_types = "\n".join(self.get_all_available_types())
            new_message = str(e) + "\nMake sure that your python solution is in one of this directories:\n" + sys_path  + "\n\nAvailable user types:\n" + available_types + "\n\n"
            new_exc = exc_type(new_message).with_traceback(e.__traceback__)
            raise new_exc from None

    def _get_type_from_payload(self, command):
        if len(command.payload) == 1:
            type_name = command.payload[0].split(".")
            if len(type_name) == 1:
                module = LazyModuleLoader.get_module(type_name[0])
                if module is None:
                    raise ImportError(f"Module {type_name[0]} not found")
                return module
            else:
                return self._get_type_from_nested_payload(type_name)
        else:
            return self._get_type_from_nested_payload(command.payload)

    def _get_type_from_nested_payload(self, payload):
        module_name = ".".join(payload[:-1])
        class_name = payload[-1]
        loaded_module = LazyModuleLoader.get_module(module_name)
        if loaded_module is None:
            raise ImportError(f"Module {module_name} not found")
        return getattr(loaded_module, class_name)

    def get_all_available_types(self):
        """Get all available types without loading/executing any modules."""
        available_types = set()
        for directory in LoadLibraryHandler.loaded_dir_and_files:
            for root, _, files in os.walk(directory):
                if "Binaries" in root:
                    continue
                for file in files:
                    if file.lower().endswith(".py") and file != "__init__.py":
                        file_path = os.path.join(root, file)
                        module_name = os.path.splitext(file)[0]
                        module_path = os.path.relpath(os.path.join(root, module_name), directory).replace(os.sep, ".")
                        
                        try:
                            # Extract class names using AST without executing code
                            class_names = self._extract_classes_from_file(file_path)
                            for class_name in class_names:
                                qualified_name = f"{module_path}.{class_name}"
                                available_types.add(qualified_name)
                        except Exception:
                            # Skip files that can't be parsed
                            pass
        return sorted(available_types)

    def _extract_classes_from_file(self, file_path):
        """Extract class names from a Python file using AST parsing (no code execution)."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Parse the file into an Abstract Syntax Tree
            tree = ast.parse(content, filename=file_path)
            class_names = []
            
            # Walk through all nodes in the AST
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Only include public classes (not starting with underscore)
                    if not node.name.startswith('_'):
                        class_names.append(node.name)
            
            return class_names
            
        except (SyntaxError, UnicodeDecodeError, FileNotFoundError, OSError):
            # Return empty list if file can't be parsed or read
            return []