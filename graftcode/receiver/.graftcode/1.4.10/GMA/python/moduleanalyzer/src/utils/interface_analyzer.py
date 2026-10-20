import importlib
import importlib.util
import inspect
import os
from typing import List, Type
import zipfile


class InterfaceAnalyzer:
    @staticmethod
    def return_classes_from_py(path: str) -> List[Type]:
        """
        Returns a list of classes found in Python files. If a directory is
        provided, it will search recursively for Python files and return the
        classes found in those files.

        :param path: Path to a Python file or directory.
        :return: List of classes found in the specified Python files.
        :raises FileNotFoundError: If the file or directory does not exist.
        :raises NotADirectoryError: If a directory is provided but a file was
                                   expected.
        """
        InterfaceAnalyzer._validate_path_exists(path)
        if os.path.isfile(path):
            return InterfaceAnalyzer._handle_file_path(path)
        elif os.path.isdir(path):
            return InterfaceAnalyzer._extract_classes_from_directory(path)
        else:
            raise NotADirectoryError(f"Expected a file or directory but found: {path}")

    @staticmethod
    def _validate_path_exists(path: str) -> None:
        """
        Validates that the given path exists.

        :param path: Path to validate
        :raises FileNotFoundError: If the file or directory does not exist
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"File or directory does not exist: {path}")

    @staticmethod
    def _handle_file_path(path: str) -> List[Type]:
        """
        Handles a file path, processing ZIP files or regular Python files.

        :param path: File path to handle
        :return: List of classes found
        """
        if path.endswith(".zip"):
            extracted_path = InterfaceAnalyzer._extract_zip_file(path)
            return InterfaceAnalyzer._extract_classes_from_directory(extracted_path)
        else:
            return InterfaceAnalyzer._return_classes_from_file(path)

    @staticmethod
    def _extract_zip_file(path: str) -> str:
        """
        Extracts a ZIP file and returns the extraction directory.

        :param path: Path to the ZIP file
        :return: Path to the extraction directory
        """
        extract_dir = path[:-4]  # Remove the .zip extension
        with zipfile.ZipFile(path, "r") as zip_ref:
            zip_ref.extractall(extract_dir)
        return extract_dir

    @staticmethod
    def _extract_classes_from_directory(path: str) -> List[Type]:
        """
        Extracts classes from all Python files in a directory.

        :param path: Directory path to search
        :return: List of classes found
        """
        classes = []
        for root, _, files in os.walk(path):
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    classes.extend(
                        InterfaceAnalyzer._return_classes_from_file(file_path)
                    )
        return classes

    @staticmethod
    def _return_classes_from_file(file_path: str) -> List[Type]:
        """
        Helper method to return classes from a single Python file.

        :param file_path: Path to the Python file.
        :return: List of classes found in the Python file.
        :raises FileNotFoundError: If the file does not exist.
        :raises NotADirectoryError: If a directory is provided instead of a
                                   file.
        """
        if not os.path.isfile(file_path):
            raise NotADirectoryError(
                f"Expected a file but found a directory: {file_path}"
            )

        classes = []
        spec = importlib.util.spec_from_file_location(
            os.path.basename(file_path)[:-3], file_path
        )
        foo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(foo)
        for _, obj in inspect.getmembers(foo):
            if inspect.isclass(obj):
                classes.append(obj)

        return classes
