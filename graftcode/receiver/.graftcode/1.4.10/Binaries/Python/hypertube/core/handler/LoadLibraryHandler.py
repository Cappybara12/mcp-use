import os
import sys
import py_compile
from argparse import ArgumentError

from hypertube.core.handler.AbstractHandler import AbstractHandler
from hypertube.utils.LazyModuleLoader import LazyModuleLoader


class LoadLibraryHandler(AbstractHandler):
    # Track loaded directories/files by absolute path
    loaded_dir_and_files = set()

    def __init__(self):
        self._required_parameters_count = 1

    def process(self, command):
        try:
            try:
                self.validate(command, self._required_parameters_count, "LoadLibrary")
            except ValueError as exc:
                raise Exception("LoadLibrary payload parameters mismatch") from exc

            dir_or_file_to_load = command.payload[0]

            if not isinstance(dir_or_file_to_load, str) or not dir_or_file_to_load:
                raise Exception("Library path is required and must be a non-empty string")

            # ------------------------------------------------------------------
            # Normalize file extension:
            # - If no extension is provided and "<path>.py" exists, use that.
            # ------------------------------------------------------------------
            normalized_path = dir_or_file_to_load
            root, ext = os.path.splitext(normalized_path)
            if ext == "":
                candidate = normalized_path + ".py"
                if os.path.isfile(candidate):
                    normalized_path = candidate

            # Use absolute path for de-duplication
            absolute_path = os.path.abspath(normalized_path)

            # Ensure path exists
            if not os.path.exists(absolute_path):
                raise Exception(f"{dir_or_file_to_load} does not exist")

            # ------------------------------------------------------------------
            # Load only once (by absolute path)
            # ------------------------------------------------------------------
            if absolute_path in LoadLibraryHandler.loaded_dir_and_files:
                return 0

            if os.path.isdir(absolute_path):
                self._validate_directory_syntax(absolute_path)

                # Add directory to sys.path only if not already present
                if absolute_path not in sys.path:
                    sys.path.append(absolute_path)

            elif os.path.isfile(absolute_path) and absolute_path.endswith(".py"):
                self._validate_python_file_syntax(absolute_path)

                module_name = os.path.splitext(os.path.basename(absolute_path))[0]
                LazyModuleLoader.register_module_path(module_name, absolute_path)
            else:
                raise Exception(f"{dir_or_file_to_load} is not a valid directory or .py file")

            # Mark as loaded
            LoadLibraryHandler.loaded_dir_and_files.add(absolute_path)

            return 0

        except Exception as e:
            new_exc = ArgumentError(None, str(e)).with_traceback(e.__traceback__)
            raise new_exc from None

    @staticmethod
    def get_loaded_directories():
        # Return a list for external callers
        return list(LoadLibraryHandler.loaded_dir_and_files)

    @staticmethod
    def _validate_directory_syntax(directory_path):
        for root, dirs, files in os.walk(directory_path):
            dirs.sort()
            for file_name in sorted(files):
                if file_name.endswith(".py"):
                    file_path = os.path.join(root, file_name)
                    LoadLibraryHandler._validate_python_file_syntax(file_path)

    @staticmethod
    def _validate_python_file_syntax(file_path):
        try:
            py_compile.compile(file_path, doraise=True)
        except py_compile.PyCompileError as exc:
            error_message = getattr(exc, "msg", str(exc))
            raise Exception(f"Python syntax error in file {file_path}: {error_message}") from exc
