import logging
import os
import shutil
import zipfile
from typing import Union


class PackageExtractor:
    """
    Utility class for extracting ZIP and wheel package files.
    """

    @staticmethod
    def is_zip_file(file_path: Union[str, os.PathLike]) -> bool:
        """
        Checks if the given file is a ZIP file based on its header.

        :param file_path: The path to the file to check.
        :return: True if the file is a ZIP file, False otherwise.
        """
        if not os.path.isfile(file_path):
            return False
        with open(file_path, "rb") as file:
            header = file.read(4)
        return header == b"PK\x03\x04"

    @staticmethod
    def extract_zip(zip_path: str, extract_to: str = None) -> str:
        """
        Extracts a ZIP file to a directory.

        :param zip_path: Path to the ZIP file
        :param extract_to: Directory to extract to. If None, extracts to directory
                          with same name as ZIP (without .zip extension)
        :return: Path to the extracted directory
        """
        if extract_to is None:
            extract_to = zip_path[:-4] if zip_path.endswith(".zip") else zip_path + "_extracted"

        if not os.path.exists(extract_to):
            os.makedirs(extract_to)

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_to)

        # Also extract any .whl files found in the extracted directory
        PackageExtractor._extract_wheel_files(extract_to)

        return extract_to

    @staticmethod
    def process_file(file_path: str, extract_to: str) -> str:
        """
        Processes the file based on its type. If the file is a ZIP file,
        it extracts it to the specified directory.

        :param file_path: Path to the file to process
        :param extract_to: Directory to extract the file to if it is a ZIP
        :return: Path to the extracted directory
        :raises ValueError: If the file is not a ZIP file.
        """
        if not PackageExtractor.is_zip_file(file_path):
            raise ValueError(
                f"The file {file_path} is not a ZIP file and cannot be "
                f"processed as one."
            )
        return PackageExtractor.extract_zip(file_path, extract_to)

    @staticmethod
    def _extract_wheel_files(directory: str) -> None:
        """
        Recursively scans a directory for .whl files and extracts them.

        :param directory: Directory to scan for .whl files.
        """
        whl_files = PackageExtractor._find_wheel_files(directory)
        for whl_path in whl_files:
            PackageExtractor._extract_single_wheel_file(whl_path)

    @staticmethod
    def _find_wheel_files(directory: str) -> list:
        """
        Find all .whl files in a directory recursively.

        :param directory: Directory to scan for .whl files.
        :return: List of paths to .whl files.
        """
        whl_files = []
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith(".whl"):
                    whl_files.append(os.path.join(root, file))
        return whl_files

    @staticmethod
    def _extract_single_wheel_file(whl_path: str) -> None:
        """
        Extract a single .whl file and create necessary __init__.py files.

        :param whl_path: Path to the .whl file to extract.
        """
        extract_dir = whl_path[:-4]  # Remove the .whl extension
        with zipfile.ZipFile(whl_path, "r") as zip_ref:
            zip_ref.extractall(extract_dir)

        PackageExtractor._create_init_files(extract_dir)

    @staticmethod
    def _create_init_files(extract_dir: str) -> None:
        """
        Create __init__.py files in all directories to make package imports work.

        :param extract_dir: Directory to scan and create __init__.py files in.
        """
        for root_dir, dirs, _ in os.walk(extract_dir):
            for dir_name in dirs:
                PackageExtractor._create_init_file_if_needed(root_dir, dir_name)

    @staticmethod
    def _create_init_file_if_needed(root_dir: str, dir_name: str) -> None:
        """
        Create an __init__.py file in a directory if it doesn't exist.

        :param root_dir: Parent directory path.
        :param dir_name: Directory name to create __init__.py in.
        """
        init_path = os.path.join(root_dir, dir_name, "__init__.py")
        if not os.path.exists(init_path):
            # Create an empty __init__.py file
            with open(init_path, "w", encoding="utf-8"):
                pass  # File is intentionally left empty


class FileUtils:
    @staticmethod
    def _cleanup_directory(directory_path: str, logger: logging.Logger) -> None:
        """
        Remove all files and subdirectories inside the specified directory.

        This method iterates over the contents of the given directory and deletes
        all files and subdirectories recursively. The directory itself is not removed.
        Any errors encountered during the cleanup are logged as warnings.

        Args:
            directory_path (str): Absolute or relative path to the directory to clean.
            logger (logging.Logger): Logger instance used for informational and warning messages.

        Raises:
            OSError: If a filesystem-related error occurs during deletion.
            Exception: For any unexpected runtime error during cleanup.
        """
        logger.info(f"Cleaning up temporary directory: {directory_path}")
        try:
            for item in os.listdir(directory_path):
                item_path = os.path.join(directory_path, item)
                if os.path.isfile(item_path):
                    os.unlink(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
            logger.debug("Temporary directory cleaned successfully")
        except Exception as cleanup_error:
            logger.warning(f"Failed to clean temporary directory: {str(cleanup_error)}")

    @staticmethod
    def _copy_directory(
        source_directory_path: str,
        destination_directory_path: str,
        logger: logging.Logger,
    ) -> None:
        """
        Best-effort recursive copy of a source directory.

        Individual files that cannot be copied (e.g. locked
        .whl files) are skipped with a warning instead of
        aborting the whole operation.
        """
        logger.info(
            "Copy directory: %s to %s",
            source_directory_path,
            destination_directory_path,
        )

        skipped: list[str] = []

        def _safe_copy2(src: str, dst: str) -> None:
            try:
                shutil.copy2(src, dst)
            except (PermissionError, OSError) as exc:
                skipped.append(src)
                logger.warning(
                    "Skipped file (permission/OS error): "
                    "%s — %s",
                    src,
                    exc,
                )

        try:
            shutil.copytree(
                source_directory_path,
                destination_directory_path,
                dirs_exist_ok=True,
                copy_function=_safe_copy2,
            )
        except Exception as copy_error:
            logger.warning(
                "Failed to copy directory %s to %s: %s",
                source_directory_path,
                destination_directory_path,
                copy_error,
            )
            raise

        if skipped:
            logger.warning(
                "Best-effort copy: %d file(s) skipped",
                len(skipped),
            )