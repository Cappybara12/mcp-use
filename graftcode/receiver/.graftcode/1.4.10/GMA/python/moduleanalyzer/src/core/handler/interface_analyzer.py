import importlib
import importlib.util
import inspect
import os
import sys
from typing import List, Optional, Tuple, Type
import zipfile

# Constants
INIT_PY_FILE = "__init__.py"

# Directories skipped during analysis – they contain non-source artefacts
# (caches, test fixtures, build outputs) that cause spurious import errors.
EXCLUDED_DIRS = frozenset(
    {
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".tox",
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "generated_output",
        "test_wheels",
        "test_resources",
        "test",
        "tests",
    }
)


class InterfaceAnalyzer:
    @staticmethod
    def return_classes_from_py(path: str) -> List[Type]:
        """
        Returns a list of classes found in Python files. If a directory is provided,
        it will search recursively for Python files and return the classes found in those files.

        :param path: Path to a Python file or directory.
        :return: List of classes found in the specified Python files.
        :raises FileNotFoundError: If the file or directory does not exist.
        :raises NotADirectoryError: If a directory is provided but a file was expected.
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"File or directory does not exist: {path}")

        if os.path.isfile(path):
            extracted_path = InterfaceAnalyzer._handle_archive_file(path)
            if extracted_path is None:  # Single Python file - use original path
                return InterfaceAnalyzer._return_classes_from_file(path)
            path = extracted_path  # Use extracted directory path

        if os.path.isdir(path):
            return InterfaceAnalyzer._process_directory(path)

        raise NotADirectoryError(f"Expected a file or directory but found: {path}")

    @staticmethod
    def _handle_archive_file(path: str) -> str | None:
        """
        Handles zip and whl file extraction.

        :param path: Path to the archive file.
        :return: Extracted directory path, or None if it's a regular Python file.
        """
        if path.endswith(".zip"):
            extract_dir = path[:-4]  # Remove the .zip extension
            with zipfile.ZipFile(path, "r") as zip_ref:
                zip_ref.extractall(extract_dir)
            # Scan extracted dir for .whl files and extract them
            InterfaceAnalyzer._extract_wheel_files(extract_dir)
            return extract_dir
        elif path.endswith(".whl"):
            extract_dir = path[:-4]  # Remove the .whl extension
            with zipfile.ZipFile(path, "r") as zip_ref:
                zip_ref.extractall(extract_dir)
            return extract_dir
        else:
            # Regular Python file - return None to indicate it should be processed directly
            return None

    @staticmethod
    def _process_directory(path: str) -> List[Type]:
        """
        Process all Python files in a directory recursively.
        Skips directories that appear to be extracted dependency wheels
        (sibling directories with .dist-info folders).

        :param path: Directory path to process.
        :return: List of classes found in all Python files.
        """
        classes = []

        for root, dirs, files in os.walk(path):
            # Skip .dist-info directories and known non-source directories
            dirs[:] = [
                d
                for d in dirs
                if not d.endswith(".dist-info") and d not in EXCLUDED_DIRS
            ]

            # Skip sibling wheel directories (directories at parent level that are
            # extracted dependency wheels - they have their own .dist-info)
            if root != path:
                # Check if this is a sibling extracted wheel directory
                parent_of_root = os.path.dirname(root)
                if parent_of_root == os.path.dirname(path):
                    # This is a sibling directory - check if it's an extracted wheel
                    has_dist_info = any(
                        d.endswith(".dist-info")
                        for d in os.listdir(root)
                        if os.path.isdir(os.path.join(root, d))
                    )
                    if has_dist_info:
                        continue

            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    classes.extend(
                        InterfaceAnalyzer._return_classes_from_file(file_path)
                    )

        return InterfaceAnalyzer._filter_unique_types(classes)

    @staticmethod
    def _filter_unique_types(classes: List[Type]) -> List[Type]:
        """
        Remove duplicate class types from a list based on module and class name.

        Args:
            classes (List[Type]): List of class types to filter.

        Returns:
            List[Type]: List containing only unique class types, preserving the last occurrence.
        """
        unique_classes = {(cls.__module__, cls.__name__): cls for cls in classes}
        return list(unique_classes.values())

    @staticmethod
    def _extract_wheel_files(directory: str) -> None:
        """
        Recursively scans a directory for .whl files and extracts them.

        :param directory: Directory to scan for .whl files.
        """
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith(".whl"):
                    whl_path = os.path.join(root, file)
                    InterfaceAnalyzer._extract_single_wheel(whl_path)

    @staticmethod
    def _extract_single_wheel(whl_path: str) -> None:
        """
        Extracts a single wheel file and creates necessary __init__.py files.

        :param whl_path: Path to the .whl file to extract.
        """
        extract_dir = whl_path[:-4]  # Remove the .whl extension
        with zipfile.ZipFile(whl_path, "r") as zip_ref:
            zip_ref.extractall(extract_dir)

        InterfaceAnalyzer._create_init_files(extract_dir)

    @staticmethod
    def _create_init_files(extract_dir: str) -> None:
        """
        Create __init__.py files in all directories within the extracted directory.

        :param extract_dir: Directory where __init__.py files should be created.
        """
        for root_dir, dirs, _ in os.walk(extract_dir):
            # Create an __init__.py file in this directory
            InterfaceAnalyzer._create_init_file_if_missing(root_dir)

            # Create __init__.py files in subdirectories
            for dir_name in dirs:
                subdir_path = os.path.join(root_dir, dir_name)
                InterfaceAnalyzer._create_init_file_if_missing(subdir_path)

    @staticmethod
    def _create_init_file_if_missing(directory: str) -> None:
        """
        Create an __init__.py file in the specified directory if it doesn't exist.

        :param directory: Directory where the __init__.py file should be created.
        """
        init_path = os.path.join(directory, INIT_PY_FILE)
        if not os.path.exists(init_path):
            os.makedirs(directory, exist_ok=True)
            with open(init_path, "w", encoding="utf-8") as init_file:
                init_file.write("# Package initialization file\n")

    @staticmethod
    def _get_package_context(
        file_path: str,
    ) -> Tuple[str, Optional[str], Optional[str]]:
        """
        Determines the proper package context for a Python file.

        For a file like /path/to/sdn_test_simple_car/__init__.py:
        - module_name = "sdn_test_simple_car" (for __init__.py) or
                        "sdn_test_simple_car.simple_car" (for simple_car.py)
        - package_name = "sdn_test_simple_car"
        - package_path = /path/to/sdn_test_simple_car

        :param file_path: Absolute path to the Python file
        :return: Tuple of (module_name, package_name, package_path)
        """
        file_name = os.path.basename(file_path)
        parent_dir = os.path.dirname(file_path)
        package_name = os.path.basename(parent_dir)

        # Check if parent directory is a Python package (has __init__.py)
        init_path = os.path.join(parent_dir, INIT_PY_FILE)
        is_package = os.path.isfile(init_path)

        if is_package:
            if file_name == INIT_PY_FILE:
                module_name = package_name
            else:
                base_name = os.path.splitext(file_name)[0]
                module_name = f"{package_name}.{base_name}"
            return module_name, package_name, parent_dir
        else:
            # Not a package, just a standalone file
            module_name = os.path.splitext(file_name)[0]
            return module_name, None, None

    @staticmethod
    def _setup_package_in_sys_modules(package_name: str, package_path: str) -> None:
        """
        Sets up a package in sys.modules so that relative imports work.

        Re-registers the package if the cached entry points at a different
        directory. This is important when the analyser is invoked multiple
        times in the same process with different sources that happen to
        share a top-level name (commonly ``src``): the first analysis would
        otherwise poison ``sys.modules`` for every subsequent one, so its
        sibling files could not be located for relative imports.

        :param package_name: Name of the package (e.g., "sdn_test_simple_car")
        :param package_path: Path to the package directory
        """
        existing = sys.modules.get(package_name)
        if existing is not None and getattr(existing, "__path__", None) == [
            package_path
        ]:
            return

        # Create a module spec for the package
        init_path = os.path.join(package_path, INIT_PY_FILE)

        # Add the parent directory to sys.path for imports
        parent_of_package = os.path.dirname(package_path)
        if parent_of_package not in sys.path:
            sys.path.insert(0, parent_of_package)

        # Create and register the package module
        package_spec = importlib.util.spec_from_file_location(
            package_name,
            init_path,
            submodule_search_locations=[package_path],
        )
        if package_spec and package_spec.loader:
            package_module = importlib.util.module_from_spec(package_spec)
            package_module.__path__ = [package_path]
            package_module.__package__ = package_name
            sys.modules[package_name] = package_module

    @staticmethod
    def _return_classes_from_file(file_path: str) -> List[Type]:
        """
        Helper method to return classes from a single Python file.

        :param file_path: Path to the Python file.
        :return: List of classes found in the Python file.
        :raises FileNotFoundError: If the file does not exist.
        :raises NotADirectoryError: If a directory is provided instead of a file.
        """
        if not os.path.isfile(file_path):
            raise NotADirectoryError(
                f"Expected a file but found a directory: {file_path}"
            )

        # Get package context for proper relative import handling
        module_name, package_name, package_path = (
            InterfaceAnalyzer._get_package_context(file_path)
        )

        # Add the parent directories to sys.path temporarily
        original_sys_path = sys.path.copy()

        classes = []
        try:
            # If this file is part of a package, set up the package context first
            # This ensures relative imports work correctly from the start
            if package_name and package_path:
                InterfaceAnalyzer._setup_package_in_sys_modules(
                    package_name, package_path
                )
                # Add parent of package to sys.path so the package itself is
                # importable, and the package directory itself so *bare
                # sibling imports* written by the user (e.g. ``from
                # price_calculator import X`` instead of the Python-3-strict
                # ``from .price_calculator import X``) still resolve. This
                # mirrors the standalone branch below and is required for
                # flat-layout projects that were promoted to packages by
                # ``_create_init_files`` in ``analyze_local``.
                parent_of_package = os.path.dirname(package_path)
                if parent_of_package not in sys.path:
                    sys.path.insert(0, parent_of_package)
                if package_path not in sys.path:
                    sys.path.insert(0, package_path)

                # Create spec with submodule_search_locations for proper package support
                spec = importlib.util.spec_from_file_location(
                    module_name,
                    file_path,
                    submodule_search_locations=[package_path],
                )
            else:
                # Standalone file (no __init__.py in parent directory). Ensure
                # the file's directory is on sys.path so sibling file-to-file
                # imports can be resolved in a flat layout, e.g.
                #
                #     src/
                #       billing_service.py  -> from price_calculator import X
                #       price_calculator.py -> class X: ...
                #
                # Without this, Python cannot find the sibling module unless
                # it happens to already be in sys.modules, which is
                # order-dependent when os.walk traverses the directory.
                file_dir = os.path.dirname(file_path)
                if file_dir and file_dir not in sys.path:
                    sys.path.insert(0, file_dir)
                spec = importlib.util.spec_from_file_location(module_name, file_path)

            if spec is None or getattr(spec, "loader", None) is None:
                # Could not create a loader for this file; skip safely
                print(
                    f"Warning: Unable to create import spec/loader for {file_path}; skipping."
                )
                return classes

            module = importlib.util.module_from_spec(spec)
            if package_name:
                module.__package__ = package_name
            sys.modules[module_name] = module

            try:
                spec.loader.exec_module(module)
                for name, obj in inspect.getmembers(module):
                    if name.startswith("_"):
                        continue
                    if inspect.isclass(obj):
                        # Only include classes that are defined in this module,
                        # not imported from other modules (like dependencies)
                        if hasattr(obj, "__module__") and obj.__module__ == module_name:
                            classes.append(obj)
            except ImportError as ie:
                # Log import errors but continue processing other files
                print(f"ImportError when loading {file_path}: {str(ie)}")
            except Exception as e:
                # Catch other exceptions (e.g., pytest Skipped) to avoid crashing the analyzer
                e_type = type(e).__name__
                print(f"Error when loading {file_path}: {e_type}: {str(e)}")
        finally:
            # Restore the original sys.path
            sys.path = original_sys_path

        return classes

    @staticmethod
    def _resolve_directory_path(path: str) -> str:
        """
        Returns the directory based on the given filesystem path.
        - If the path points to a directory, returns it as-is.
        - If it points to a file, returns the directory containing that file.
        - Raises FileNotFoundError if the path does not exist.
        """
        try:
            abs_path = os.path.abspath(path)
        except Exception as e:
            raise ValueError(f"Failed to process path '{path}': {e}")

        if not os.path.exists(abs_path):
            raise FileNotFoundError(f"File or directory does not exist: {abs_path}")

        if os.path.isdir(abs_path):
            return abs_path
        elif os.path.isfile(abs_path):
            return os.path.dirname(abs_path)
        else:
            raise ValueError(f"Unsupported path type: {abs_path}")

    @staticmethod
    def _resolve_directory_name_or_file_name(path: str) -> str:
        """
        Resolve the name of a directory or a file (without extension) from a given path.

        - If the path points to a directory, returns the directory name.
        - If the path points to a file, returns the file name without its extension.
        - Raises a ValueError if the path does not refer to an existing file or directory.

        Args:
            path (str): Absolute or relative filesystem path.

        Returns:
            str: Directory name or file name without extension.

        Raises:
            ValueError: If the provided path is neither a valid file nor directory.
            OSError: If an unexpected filesystem error occurs during path resolution.
        """
        if os.path.isdir(path):
            return os.path.basename(os.path.normpath(path))
        elif os.path.isfile(path):
            return os.path.splitext(os.path.basename(path))[0]
        else:
            raise ValueError(f"Unsupported file/directory path type: {path}")
