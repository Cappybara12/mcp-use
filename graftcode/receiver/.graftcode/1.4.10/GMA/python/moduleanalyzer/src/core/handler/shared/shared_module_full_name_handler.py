import inspect
from typing import Any

from moduleanalyzer.src.core.handler.abstract_handler import AbstractHandler


class SharedModuleFullNameHandler(AbstractHandler):
    """
    Handler responsible for generating the full module name of the analyzed
    object. Prioritizes the __module__ attribute for reliability with
    uninstalled code.
    """

    def generate_unified_graft_model(
        self, analyzed_object: Any, parent_command: Any, handlers: Any
    ) -> str:
        """
        Generates the unified graft model by returning the full module name
        of the analyzed object.

        :param analyzed_object: The object being analyzed.
        :param parent_command: The parent command (unused in this specific
                              logic).
        :param handlers: Handlers collection (unused in this specific logic).
        :return: The full module name string, or a fallback like
                "unnamed module".
        """
        module_name = None

        # Try the __module__ attribute first
        try:
            if hasattr(analyzed_object, "__module__") and isinstance(
                analyzed_object.__module__, str
            ):
                module_name = analyzed_object.__module__
                # Avoid returning '__main__' as it's often not the desired
                # canonical module name
                if module_name == "__main__":
                    # Treat __main__ as unknown for module name purposes
                    module_name = None
        except Exception:
            # Ensure it's None if attribute access failed
            module_name = "null"

        # Fallback to inspect.getmodule if __module__ didn't work or wasn't
        # present
        if module_name is None:
            try:
                module = inspect.getmodule(analyzed_object)
                if module and hasattr(module, "__name__"):
                    module_name = module.__name__
                    if module_name == "__main__":
                        # Also treat __main__ from getmodule as unknown
                        module_name = None
            except Exception:
                # inspect.getmodule can fail in various ways
                module_name = "null"

        # Final fallback value if no name could be determined
        if module_name is None:
            # Consider logging this situation
            return "unnamed module"  # Or another appropriate placeholder

        # TODO: VERIFICATION NEEDED - Removing submodule suffix from module name
        # This is a temporary fix to prevent double package names in C# GCG.NetCore
        # Example: "sdncenter_currency_converter.converter" -> "sdncenter_currency_converter"
        # The parent_command contains library name in Payload[0], and we're checking if
        # the module name has a redundant submodule suffix that matches the last component.
        #
        # Original behavior (commented out for now, but kept for reference):
        # - Full module name was returned: "package.submodule"
        # - This caused C# to generate: "graft.pypi.package.submodule"
        #
        # New behavior:
        # - Extract package name only if module has format "package.submodule"
        # - Check if library name from Payload[0] matches the package part
        # - Return package name only to avoid redundancy
        #
        # This needs verification because:
        # 1. We might be losing important submodule information
        # 2. Need to ensure this works for all package structures (single module, nested modules, etc.)
        # 3. Need to verify C# side expectations match this change
        if module_name and "." in module_name and parent_command:
            try:
                # Try to get library name from parent_command.Payload[1]
                # (Payload[0] is library_namespace)
                if (
                    hasattr(parent_command, "payload")
                    and len(parent_command.payload) > 1
                ):
                    library_name = parent_command.payload[1]
                    if isinstance(library_name, str):
                        # If module_name is "package.submodule" and library_name matches "package",
                        # return only the package part
                        parts = module_name.split(".")
                        if len(parts) >= 2 and parts[0] == library_name:
                            module_name = parts[0]  # Return package name only
            except Exception:
                # If any error occurs during extraction, keep the original module_name
                pass

        return module_name
