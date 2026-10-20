import ast
from collections import deque
import os
import shutil
import tempfile
from typing import Dict, List, Optional, Tuple
import zipfile

from graftcode_python_logger import GCLoggerFactory, GCLoggerOptions, LogLevel
from graftcode_storage.storage_client import StorageClient

from moduleanalyzer.src.core.handler.analysis.library_analyzer import LibraryAnalyzer
from moduleanalyzer.src.core.utils.component_info import ComponentInfo
from moduleanalyzer.src.core.utils.file_utils import FileUtils, PackageExtractor

# Initialize logger with correct pattern
logger_options = GCLoggerOptions(
    service_name=os.getenv("SERVICE_NAME", ComponentInfo.SERVICE_NAME),
    app_service_name=os.getenv("WEBSITE_SITE_NAME", ComponentInfo.SERVICE_NAME),
    minimum_log_level=LogLevel.INFO,
    use_app_insights_from_env=True,
    app_insights_env_var=ComponentInfo.APPLICATIONINSIGHTS_CONNECTION_STRING_KEY,
    include_source_context=True,
    include_exception_stack_trace=True,
)

factory = GCLoggerFactory.initialize(logger_options)
logger = factory.get_logger(__name__)

# Log module initialization
logger.info("GraftCode Module Analyzer module initialized")


class PythonModuleAnalyzer:
    """
    A class for analyzing Python modules, handling file storage, and generating serialized data.
    """

    def __init__(self) -> None:
        """
        Initializes the PythonModuleAnalyzer instance by
        setting up storage, and configuring the local temporary directory.
        """
        logger.info("Initializing PythonModuleAnalyzer")

        storage_client = StorageClient()
        self.storage = storage_client.get_storage()
        logger.debug("Storage client initialized")

        # Use a dedicated subdirectory to avoid nuking shared /tmp contents
        # (e.g. OpenCensus exporter storage) during cleanup.
        base_temp = os.getenv("LOCAL_TEMP_DIR", "/tmp")
        self.local_temp_dir = os.path.join(base_temp, "gma-python")
        os.makedirs(self.local_temp_dir, exist_ok=True)

        self.python_version_map = {
            "2.7": "Python 2.7",
            "3.6": "Python 3.6",
            "3.7": "Python 3.7",
            "3.8": "Python 3.8",
            "3.9": "Python 3.9",
            "3.10": "Python 3.10",
            "3.11": "Python 3.11",
        }

        self.library_analyzer = LibraryAnalyzer()

    def _get_local_input_path(
        self, container_name: str, input_blob_name: str, is_local_storage: bool
    ) -> str:
        """
        Determines the local input path based on storage type and input format.

        :param container_name: The container name
        :param input_blob_name: The input blob name
        :param is_local_storage: Whether using local storage
        :return: The local input path
        """
        if is_local_storage:
            if os.path.isabs(input_blob_name) or input_blob_name.startswith("/"):
                local_input_path = input_blob_name
                logger.info(f"Using absolute local path: {local_input_path}")
            else:
                local_input_path = os.path.join(container_name, input_blob_name)
                logger.info(f"Local storage detected, using path: {local_input_path}")
        else:
            if os.path.isabs(input_blob_name) or input_blob_name.startswith("/"):
                local_input_path = os.path.join(
                    self.local_temp_dir, os.path.basename(input_blob_name)
                )
            else:
                local_input_path = os.path.join(self.local_temp_dir, input_blob_name)

        return local_input_path

    def _download_or_verify_file(
        self,
        container_name: str,
        input_blob_name: str,
        local_input_path: str,
        is_local_storage: bool,
    ) -> None:
        """
        Downloads the file from storage or verifies local file exists.

        :param container_name: The container name
        :param input_blob_name: The input blob name
        :param local_input_path: The local input path
        :param is_local_storage: Whether using local storage
        """
        if not is_local_storage:
            logger.info("Downloading file from storage")
            self.storage.download_blob(
                local_input_path, container_name, input_blob_name
            )
            logger.info(
                "File downloaded successfully",
                extra={"custom_dimensions": {"local_path": local_input_path}},
            )
        else:
            if not os.path.exists(local_input_path):
                raise FileNotFoundError(f"Local file not found: {local_input_path}")
            logger.info(
                "Using local file",
                extra={"custom_dimensions": {"local_path": local_input_path}},
            )

    def _process_zip_file_if_needed(self, local_input_path: str) -> None:
        """
        Processes the file if it is a ZIP file.

        :param local_input_path: The local input path
        """
        if PackageExtractor.is_zip_file(local_input_path):
            logger.info("Processing ZIP file")
            PackageExtractor.process_file(local_input_path, self.local_temp_dir)
            logger.info("ZIP file processed successfully")

    def analyze(
        self,
        container_name: str,
        input_blob_name: str,
        trace_id: str = "",
        parent_trace_id: str = "",
    ) -> bytes:
        """
        Analyzes a Python module by downloading it from storage, processing it, and
        returning the serialized output as bytes.

        :param container_name: The name of the container or directory in the storage service.
        :param input_blob_name: The name of the file in the container or directory to analyze.
        :param trace_id: Trace ID for cross-service correlation.
        :param parent_trace_id: Parent trace ID for cross-service correlation.
        :return: A bytes object containing the serialized output.
        :raises IOError: If file operations or serialization fails.
        """
        with GCLoggerFactory.track_operation(
            logger,
            "PythonModuleAnalyzer.analyze",
            properties={
                "container_name": container_name,
                "input_blob_name": input_blob_name,
            },
            operation_id=trace_id or None,
            parent_span_id=parent_trace_id or None,
        ):
            logger.info(
                f"Starting Python module analysis for container={container_name}, blob={input_blob_name}",
                extra={
                    "custom_dimensions": {
                        "container_name": container_name,
                        "input_blob_name": input_blob_name,
                    }
                },
            )

            local_input_path = self._prepare_input_file(container_name, input_blob_name)

            try:
                structured_command = (
                    self.library_analyzer._create_base_structured_command(
                        local_input_path
                    )
                )
                structured_command = self.library_analyzer._perform_analysis(
                    local_input_path, structured_command
                )
                result = self.library_analyzer._serialize_result(structured_command)
                logger.info("Python module analysis completed successfully")
                return result

            except Exception as e:
                logger.error(f"Analyze failed: {str(e)}", exc_info=True)
                raise
            finally:
                FileUtils._cleanup_directory(self.local_temp_dir, logger)

    def _prepare_input_file(self, container_name: str, input_blob_name: str) -> str:
        """
        Prepares the input file by determining storage type and handling file download/verification.

        :param container_name: The container name
        :param input_blob_name: The input blob name
        :return: The local input path (extracted directory for ZIP files, or original path for .py files)
        """
        # Check storage type and get local input path
        storage_type = os.getenv("STORAGE_TYPE", "AZURE").upper()
        is_local_storage = storage_type == "LOCAL"
        local_input_path = self._get_local_input_path(
            container_name, input_blob_name, is_local_storage
        )

        # Download or verify file
        self._download_or_verify_file(
            container_name, input_blob_name, local_input_path, is_local_storage
        )

        # Process ZIP file if needed and return extracted directory path
        if PackageExtractor.is_zip_file(local_input_path):
            extracted_path = self._extract_zip_to_directory(local_input_path)
            logger.info("Using extracted directory: %s", extracted_path)
            return extracted_path

        return local_input_path

    def _extract_zip_to_directory(self, zip_path: str) -> str:
        """
        Extracts a ZIP file to a directory with the same name (without .zip extension).

        :param zip_path: Path to the ZIP file
        :return: Path to the extracted directory
        """
        # Extract to directory with same name as ZIP (without .zip extension)
        extract_dir = zip_path[:-4]

        logger.info("Extracting ZIP file to: %s", extract_dir)
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_dir)

        # If the original file is a .whl, copy it to the extracted directory
        # so that metadata extraction (_create_base_structured_command) can find it
        if zip_path.endswith(".whl"):
            dest_whl = os.path.join(extract_dir, os.path.basename(zip_path))
            shutil.copy(zip_path, dest_whl)
            logger.debug("Copied .whl file to extracted directory: %s", dest_whl)

            # Extract sibling wheel files for dependency resolution
            sibling_dirs = self._extract_sibling_wheel_files(zip_path)
            if sibling_dirs:
                logger.info(
                    f"Extracted {len(sibling_dirs)} sibling wheel(s) for dependency resolution"
                )

        # Also extract any .whl files found in the extracted directory
        self._extract_wheel_files(extract_dir)

        return extract_dir

    def _handle_zip_file_extraction(self, file_path: str) -> List[str]:
        """
        Handles extraction of ZIP files and returns list of Python files.

        :param file_path: Path to the ZIP file
        :return: List of Python file paths
        """
        extract_dir = os.path.dirname(file_path)
        python_files = []
        whl_files = []

        # First look for Python files and WHL files
        for root, _, files in os.walk(extract_dir):
            for file in files:
                if file.endswith(".py"):
                    python_files.append(os.path.join(root, file))
                elif file.endswith(".whl"):
                    whl_files.append(os.path.join(root, file))

        logger.info(
            f"Found {len(python_files)} Python files and {len(whl_files)} WHL files in the extracted directory"
        )

        # If no Python files found but WHL files exist, try to extract them
        if not python_files and whl_files:
            python_files = self._extract_whl_files(whl_files, extract_dir)

        return python_files

    def _extract_whl_files(self, whl_files: List[str], extract_dir: str) -> List[str]:
        """
        Extracts Python files from WHL files.

        :param whl_files: List of WHL file paths
        :param extract_dir: Base extraction directory
        :return: List of extracted Python file paths
        """
        python_files = []

        # Create a persistent directory to store the extracted Python files
        whl_extract_persistent_dir = os.path.join(
            self.local_temp_dir, "whl_extracted_" + os.path.basename(extract_dir)
        )

        # Create the persistent directory if it doesn't exist
        if not os.path.exists(whl_extract_persistent_dir):
            os.makedirs(whl_extract_persistent_dir)
            logger.debug(f"Created persistent directory: {whl_extract_persistent_dir}")
        else:
            logger.debug(
                f"Using existing persistent directory: {whl_extract_persistent_dir}"
            )

        # Process each WHL file (which is essentially a ZIP file)
        for whl_file in whl_files:
            try:
                python_files.extend(
                    self._extract_single_whl_file(whl_file, whl_extract_persistent_dir)
                )
            except Exception as whl_error:
                logger.error(f"Error extracting WHL file {whl_file}: {str(whl_error)}")

        return python_files

    def _extract_single_whl_file(self, whl_file: str, persistent_dir: str) -> List[str]:
        """
        Extracts Python files from a single WHL file.

        :param whl_file: Path to the WHL file
        :param persistent_dir: Persistent directory to store extracted files
        :return: List of extracted Python file paths
        """
        with tempfile.TemporaryDirectory() as whl_extract_dir:
            self._extract_whl_to_temp_dir(whl_file, whl_extract_dir)
            temp_python_files = self._find_python_files_in_directory(whl_extract_dir)
            return self._copy_files_to_persistent_directory(
                temp_python_files, whl_extract_dir, persistent_dir
            )

    def _extract_whl_to_temp_dir(self, whl_file: str, extract_dir: str) -> None:
        """
        Extracts WHL file contents to a temporary directory.

        :param whl_file: Path to the WHL file
        :param extract_dir: Directory to extract to
        """
        with zipfile.ZipFile(whl_file, "r") as whl_zip:
            whl_zip.extractall(extract_dir)

    def _find_python_files_in_directory(self, directory: str) -> List[str]:
        """
        Finds all Python files in a directory recursively.

        :param directory: Directory to search in
        :return: List of Python file paths
        """
        python_files = []
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith(".py"):
                    python_files.append(os.path.join(root, file))
        return python_files

    def _copy_files_to_persistent_directory(
        self, source_files: List[str], source_base_dir: str, persistent_dir: str
    ) -> List[str]:
        """
        Copies files from temporary directory to persistent directory.

        :param source_files: List of source file paths
        :param source_base_dir: Base directory for calculating relative paths
        :param persistent_dir: Target persistent directory
        :return: List of copied file paths
        """
        copied_files = []
        for source_file in source_files:
            persistent_path = self._create_persistent_file_path(
                source_file, source_base_dir, persistent_dir
            )
            self._ensure_directory_exists(os.path.dirname(persistent_path))
            shutil.copy2(source_file, persistent_path)
            copied_files.append(persistent_path)
        return copied_files

    def _create_persistent_file_path(
        self, source_file: str, source_base_dir: str, persistent_dir: str
    ) -> str:
        """
        Creates the target path for a file in the persistent directory.

        :param source_file: Source file path
        :param source_base_dir: Base directory for relative path calculation
        :param persistent_dir: Target persistent directory
        :return: Target file path
        """
        rel_path = os.path.relpath(source_file, source_base_dir)
        return os.path.join(persistent_dir, rel_path)

    def _ensure_directory_exists(self, directory_path: str) -> None:
        """
        Ensures a directory exists, creating it if necessary.

        :param directory_path: Directory path to create
        """
        os.makedirs(directory_path, exist_ok=True)

    def _read_file_with_encoding_fallback(self, file_path: str) -> str:
        """
        Reads a file with UTF-8 encoding, falling back to other encodings if needed.

        :param file_path: Path to the file to read
        :return: File content as string
        :raises FileNotFoundError: If file doesn't exist
        :raises IsADirectoryError: If path is a directory
        """
        # Try UTF-8 first
        try:
            return self._read_file_with_encoding(file_path, "utf-8")
        except UnicodeDecodeError as ude:
            logger.warning(
                f"UTF-8 decode error in {file_path}: {str(ude)}. Trying with different encodings."
            )
            return self._try_alternative_encodings(file_path, ude)

    def _read_file_with_encoding(self, file_path: str, encoding: str) -> str:
        """
        Reads a file with the specified encoding.

        :param file_path: Path to the file to read
        :param encoding: Encoding to use
        :return: File content as string
        :raises UnicodeDecodeError: If encoding fails
        """
        with open(file_path, "r", encoding=encoding) as file:
            return file.read()

    def _try_alternative_encodings(
        self, file_path: str, original_error: UnicodeDecodeError
    ) -> str:
        """
        Tries alternative encodings to read a file.

        :param file_path: Path to the file to read
        :param original_error: The original UnicodeDecodeError from UTF-8 attempt
        :return: File content as string
        :raises UnicodeDecodeError: If all encodings fail
        """
        encodings = ["latin-1", "cp1252", "iso-8859-1"]
        for encoding in encodings:
            try:
                logger.debug(f"Trying to read file with {encoding} encoding")
                content = self._read_file_with_encoding(file_path, encoding)
                logger.debug(f"File successfully read with {encoding} encoding")
                return content
            except UnicodeDecodeError:
                continue

        # If all encodings fail
        logger.error("Failed to decode file with all attempted encodings")
        raise original_error

    def _extract_ast_info_from_source(
        self, source: str, file_path: str
    ) -> Tuple[Dict[str, Dict[str, List[str]]], Dict[str, List[str]], List[str]]:
        """
        Extracts classes, functions, and variables from Python source code.

        :param source: Python source code
        :param file_path: File path for error reporting
        :return: Tuple of (classes, functions, variables)
        """
        tree = self._parse_ast_safely(source, file_path)
        if tree is None:
            return {}, {}, []

        classes = {}
        functions = {}
        variables = []

        for node in tree.body:
            self._process_ast_node(node, classes, functions, variables)

        logger.info(
            f"Module info extracted - Classes: {len(classes)}, Functions: {len(functions)}, Variables: {len(variables)}"
        )
        return classes, functions, variables

    def _parse_ast_safely(self, source: str, file_path: str) -> Optional[ast.AST]:
        """
        Safely parses Python source code into an AST.

        :param source: Python source code
        :param file_path: File path for error reporting
        :return: AST node or None if parsing fails
        """
        try:
            tree = ast.parse(source, filename=file_path)
            logger.debug("AST parsed successfully")
            return tree
        except SyntaxError as se:
            logger.error(f"Python syntax error in {file_path}: {str(se)}")
            return None

    def _process_ast_node(
        self,
        node: ast.AST,
        classes: Dict[str, Dict[str, List[str]]],
        functions: Dict[str, List[str]],
        variables: List[str],
    ) -> None:
        """
        Processes a single AST node and updates the appropriate collections.

        :param node: AST node to process
        :param classes: Dictionary to store class information
        :param functions: Dictionary to store function information
        :param variables: List to store variable names
        """
        if isinstance(node, ast.ClassDef):
            self._process_class_node(node, classes)
        elif isinstance(node, ast.FunctionDef):
            self._process_function_node(node, functions)
        elif isinstance(node, ast.Assign):
            self._process_assignment_node(node, variables)

    def _process_class_node(
        self, node: ast.ClassDef, classes: Dict[str, Dict[str, List[str]]]
    ) -> None:
        """
        Processes a class definition node.

        :param node: Class definition AST node
        :param classes: Dictionary to store class information
        """
        logger.debug(f"Processing class: {node.name}")
        methods = self._extract_methods_from_class(node)
        classes[node.name] = methods
        logger.debug(f"Processed class {node.name} with {len(methods)} methods")

    def _extract_methods_from_class(
        self, class_node: ast.ClassDef
    ) -> Dict[str, List[str]]:
        """
        Extracts methods from a class definition.

        :param class_node: Class definition AST node
        :return: Dictionary mapping method names to parameter lists
        """
        methods = {}
        for method in class_node.body:
            if isinstance(method, ast.FunctionDef):
                params = [arg.arg for arg in method.args.args]
                methods[method.name] = params
                logger.debug(
                    f"Found method in class {class_node.name}: {method.name} with {len(params)} parameters"
                )
        return methods

    def _process_function_node(
        self, node: ast.FunctionDef, functions: Dict[str, List[str]]
    ) -> None:
        """
        Processes a function definition node.

        :param node: Function definition AST node
        :param functions: Dictionary to store function information
        """
        logger.debug(f"Processing global function: {node.name}")
        params = [arg.arg for arg in node.args.args]
        functions[node.name] = params
        logger.debug(
            f"Processed global function {node.name} with {len(params)} parameters"
        )

    def _process_assignment_node(self, node: ast.Assign, variables: List[str]) -> None:
        """
        Processes an assignment node to extract variable names.

        :param node: Assignment AST node
        :param variables: List to store variable names
        """
        for target in node.targets:
            if isinstance(target, ast.Name):
                variables.append(target.id)
                logger.debug(f"Found global variable: {target.id}")

    def _process_multiple_python_files(
        self, python_files: List[str]
    ) -> Tuple[Dict[str, Dict[str, List[str]]], Dict[str, List[str]], List[str]]:
        """
        Processes multiple Python files and aggregates their info.

        :param python_files: List of Python file paths
        :return: Tuple of (classes, functions, variables) aggregated from all files
        """
        all_classes = {}
        all_functions = {}
        all_variables = []

        for file_path in python_files:
            try:
                source = self._read_file_with_encoding_fallback(file_path)
                file_classes, file_functions, file_variables = (
                    self._extract_ast_info_from_source(source, file_path)
                )

                # Merge the file's info into the overall collections
                all_classes.update(file_classes)
                all_functions.update(file_functions)
                all_variables.extend(file_variables)

                logger.info(
                    f"Extracted from {file_path} - Classes: {len(file_classes)}, Functions: {len(file_functions)}, Variables: {len(file_variables)}"
                )

            except (IsADirectoryError, FileNotFoundError) as e:
                logger.error(f"Error accessing file {file_path}: {str(e)}")
                continue
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {str(e)}")
                continue

        logger.info(
            f"All files processed - Classes: {len(all_classes)}, Functions: {len(all_functions)}, Variables: {len(all_variables)}"
        )
        return all_classes, all_functions, all_variables

    def extract_python_module_info(
        self, file_path: str
    ) -> Tuple[Dict[str, Dict[str, List[str]]], Dict[str, List[str]], List[str]]:
        """
        Extracts information about classes, their methods, global functions,
        and variables from a Python file.
        """
        logger.info(f"Extracting Python module info from: {file_path}")
        try:
            return self._extract_module_info_by_file_type(file_path)
        except Exception as e:
            logger.error(
                f"Failed to extract Python module info: {str(e)}", exc_info=True
            )
            raise e

    def _extract_module_info_by_file_type(
        self, file_path: str
    ) -> Tuple[Dict[str, Dict[str, List[str]]], Dict[str, List[str]], List[str]]:
        """
        Extracts module info based on file type (ZIP or single Python file).

        :param file_path: Path to the file to analyze
        :return: Tuple of (classes, functions, variables)
        """
        if file_path.endswith(".zip"):
            return self._extract_from_zip_file(file_path)
        else:
            return self._extract_from_single_file(file_path)

    def _extract_from_zip_file(
        self, file_path: str
    ) -> Tuple[Dict[str, Dict[str, List[str]]], Dict[str, List[str]], List[str]]:
        """
        Extracts module info from a ZIP file.

        :param file_path: Path to the ZIP file
        :return: Tuple of (classes, functions, variables)
        """
        python_files = self._handle_zip_file_extraction(file_path)

        if not python_files:
            logger.warning(
                "No Python files found in the extracted directory or WHL files"
            )
            return {}, {}, []

        return self._process_multiple_python_files(python_files)

    def _extract_from_single_file(
        self, file_path: str
    ) -> Tuple[Dict[str, Dict[str, List[str]]], Dict[str, List[str]], List[str]]:
        """
        Extracts module info from a single Python file.

        :param file_path: Path to the Python file
        :return: Tuple of (classes, functions, variables)
        """
        try:
            source = self._read_file_with_encoding_fallback(file_path)
            return self._extract_ast_info_from_source(source, file_path)
        except (IsADirectoryError, FileNotFoundError) as e:
            logger.error(f"Error accessing file {file_path}: {str(e)}")
            return {}, {}, []

    def return_classes_from_py(self, directory: str) -> deque:
        """
        Returns a deque of Python file paths within a specified directory.

        :param directory: The directory to search for Python files.
        :return: A deque of paths to Python files found within the directory.
        """
        logger.debug("Returning classes from Python files")
        try:
            files = deque()
            for root, _, files_in_dir in os.walk(directory):
                for file in files_in_dir:
                    if file.endswith(".py"):
                        files.append(os.path.join(root, file))
            logger.debug(f"Found {len(files)} Python files")
            return files
        except Exception as e:
            logger.error(
                f"Failed to return classes from Python files: {str(e)}",
                exc_info=True,
            )
            raise e

    @staticmethod
    def _extract_wheel_files(directory: str) -> None:
        """
        Recursively scans a directory for .whl files and extracts them.

        :param directory: Directory to scan for .whl files.
        """
        whl_files = PythonModuleAnalyzer._find_wheel_files(directory)
        for whl_path in whl_files:
            PythonModuleAnalyzer._extract_single_wheel_file(whl_path)

    @staticmethod
    def _extract_sibling_wheel_files(wheel_path: str) -> List[str]:
        """
        Extract all sibling .whl files from the same directory as the main wheel.
        This enables dependency resolution when multiple wheels are in the same directory.

        :param wheel_path: Path to the main .whl file being analyzed.
        :return: List of extracted directory paths for sibling wheels.
        """
        parent_dir = os.path.dirname(wheel_path)
        extracted_dirs = []
        main_wheel_name = os.path.basename(wheel_path)

        try:
            for file in os.listdir(parent_dir):
                if file.endswith(".whl") and file != main_wheel_name:
                    sibling_whl = os.path.join(parent_dir, file)
                    extract_dir = sibling_whl[:-4]  # Remove .whl extension

                    if not os.path.exists(extract_dir):
                        logger.info(f"Extracting dependency wheel: {sibling_whl}")
                        with zipfile.ZipFile(sibling_whl, "r") as zip_ref:
                            zip_ref.extractall(extract_dir)
                        PythonModuleAnalyzer._create_init_files(extract_dir)

                    extracted_dirs.append(extract_dir)
        except Exception as e:
            logger.warning(f"Failed to extract sibling wheel files: {str(e)}")

        return extracted_dirs

    @staticmethod
    def _find_wheel_files(directory: str) -> List[str]:
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

        PythonModuleAnalyzer._create_init_files(extract_dir)

    @staticmethod
    def _create_init_files(extract_dir: str) -> None:
        """
        Create __init__.py files in all directories to make package imports work.

        :param extract_dir: Directory to scan and create __init__.py files in.
        """
        for root_dir, dirs, _ in os.walk(extract_dir):
            for dir_name in dirs:
                PythonModuleAnalyzer._create_init_file_if_needed(root_dir, dir_name)

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
