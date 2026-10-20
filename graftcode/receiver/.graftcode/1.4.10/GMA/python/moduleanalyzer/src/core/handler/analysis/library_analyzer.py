import ast
import configparser
import importlib.util
import inspect
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

from graftcode_protocol.enums.runtime_name import RuntimeName
from graftcode_protocol.enums.unified_graft_model_type import UnifiedGraftModelType
from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel
from graftcode_protocol.protocol.serializers.unified_graft_model_serializer import (
    UnifiedGraftModelSerializer,
)
from graftcode_python_logger import GCLoggerFactory, GCLoggerOptions, LogLevel

from moduleanalyzer.src.core.handler.handlers import Handlers
from moduleanalyzer.src.core.handler.interface_analyzer import InterfaceAnalyzer
from moduleanalyzer.src.core.utils.component_info import ComponentInfo
from moduleanalyzer.src.core.utils.type_filter_helper import TypeFilterHelper
from moduleanalyzer.src.core.utils.method_filter_helper import MethodFilterHelper

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
logger.info("GraftCode LibraryAnalyzer module initialized")


class LibraryAnalyzer:
    def _find_first_whl_file(self, directory: str) -> Optional[str]:
        """Find the first .whl file in directory and subdirectories."""
        for _, _, files in os.walk(directory):
            for file in files:
                if file.endswith(".whl"):
                    return file
        return None

    def _extract_library_name_from_whl(self, whl_filename: str) -> str:
        """Extract library name from .whl filename (part before first hyphen)."""
        return os.path.splitext(whl_filename)[0].split("-")[0]

    def _get_search_directory(self, path: str) -> str:
        """Get the directory to search for .whl files based on whether path is file or directory."""
        if os.path.isdir(path):
            return path
        return os.path.dirname(path)

    def add_library_namespace(self, command: UnifiedGraftModel):
        return command.add_arg_to_payload("")

    def add_library_name(
        self,
        command: UnifiedGraftModel,
        py_file_path: str,
    ) -> UnifiedGraftModel:
        """
        Adds the name of the Python wheel (.whl) file (without extension)
        to the command. Only the part before the first hyphen ("-") is used
        as the library name.

        :param command: The command object to which the library name will
                       be added.
        :param py_file_path: The path to the Python file or directory
                            containing .whl files.
        :return: The updated command object with the library name added.
        :raises FileNotFoundError: If no .whl file is found.
        :raises ValueError: If library name cannot be extracted from .whl filename.
        """
        logger.debug("Adding library name")
        try:
            extract_dir = self._get_search_directory(py_file_path)
            whl_file = self._find_first_whl_file(extract_dir)

            if not whl_file:
                raise FileNotFoundError(
                    f"No .whl file found in directory: {extract_dir}. "
                    "A wheel file is required to extract the library name."
                )

            library_name = self._extract_library_name_from_whl(whl_file)
            if not library_name:
                raise ValueError(
                    f"Could not extract library name from .whl file: {whl_file}. "
                    "Expected format: name-version-python-abi-platform.whl"
                )

            logger.debug("Library name added from .whl file: %s", library_name)
            return command.add_arg_to_payload(library_name)

        except (FileNotFoundError, ValueError):
            raise
        except Exception as e:
            logger.error("Failed to add library name: %s", str(e), exc_info=True)
            raise

    def _extract_version_from_whl(self, whl_filename: str) -> Optional[str]:
        """Extract version from .whl filename (part between first and second hyphen)."""
        whl_name_without_extension = os.path.splitext(whl_filename)[0]
        parts = whl_name_without_extension.split("-")
        return parts[1] if len(parts) >= 2 else None

    def _extract_python_version_from_whl(self, whl_filename: str) -> Optional[str]:
        """
        Extract Python version from .whl filename (the 3rd component).

        Wheel format: {name}-{version}-{python}-{abi}-{platform}.whl
        Examples:
            - py3 → "3"
            - py38 → "3.8"
            - py311 → "3.11"
            - cp311 → "3.11"
            - py2.py3 → "3" (takes the highest version)
        """
        whl_name_without_extension = os.path.splitext(whl_filename)[0]
        parts = whl_name_without_extension.split("-")

        if len(parts) < 3:
            return None

        python_tag = parts[2]  # e.g., "py3", "py38", "cp311", "py2.py3"

        # Handle multiple tags like "py2.py3" - take the last one (highest version)
        if "." in python_tag:
            python_tag = python_tag.split(".")[-1]

        # Extract version from tag (py3, py38, py311, cp311, etc.)
        # Remove prefix (py, cp, pp for PyPy, etc.)
        version_str = ""
        for i, char in enumerate(python_tag):
            if char.isdigit():
                version_str = python_tag[i:]
                break

        if not version_str:
            return None

        # Convert "3" → "3", "38" → "3.8", "311" → "3.11"
        if len(version_str) == 1:
            return version_str  # "3"
        elif len(version_str) == 2:
            return f"{version_str[0]}.{version_str[1]}"  # "38" → "3.8"
        else:
            return f"{version_str[0]}.{version_str[1:]}"  # "311" → "3.11"

    def add_python_library_version(self, command, directory) -> str:
        """
        Adds the version from the Python wheel (.whl) file to the command.
        The version is extracted from the filename (part between first and second hyphen).
        For example, from "sdncenter_currency_converter-0.2.0-py3-none-any.whl",
        it will extract "0.2.0" as the version.

        :param command: The command object to which the version will be added.
        :param directory: The path to file or directory where to look for .whl files.
        :return: The updated command object with the version added.
        :raises FileNotFoundError: If no .whl file is found.
        :raises ValueError: If version cannot be extracted from .whl filename.
        """
        logger.debug("Adding Python library version")

        try:
            extract_dir = self._get_search_directory(directory)
            whl_file = self._find_first_whl_file(extract_dir)

            if not whl_file:
                raise FileNotFoundError(
                    f"No .whl file found in directory: {extract_dir}. "
                    "A wheel file is required to extract the library version."
                )

            version = self._extract_version_from_whl(whl_file)
            if not version:
                raise ValueError(
                    f"Could not extract version from .whl file: {whl_file}. "
                    "Expected format: name-version-python-abi-platform.whl"
                )

            logger.debug("Python library version added (from .whl file): %s", version)

        except (FileNotFoundError, ValueError):
            raise
        except Exception as e:
            logger.error(
                "Failed to add Python library version: %s",
                str(e),
                exc_info=True,
            )
            raise

        command = command.add_arg_to_payload(version)
        return command

    def add_python_runtime_version(
        self, command: UnifiedGraftModel, directory: str
    ) -> UnifiedGraftModel:
        """
        Adds the Python version (from .whl file) to the command.

        The version is extracted from the wheel filename's python tag.
        For example, from "sdncenter_currency_converter-0.2.0-py311-none-any.whl",
        it will extract "Python 3.11" as the Python version.

        :param command: The command object to which the Python version will be added.
        :param directory: The path to file or directory where to look for .whl files.
        :return: The updated command object with the Python version added.
        :raises FileNotFoundError: If no .whl file is found.
        :raises ValueError: If Python version cannot be extracted from .whl filename.
        """
        logger.debug("Adding Python version from .whl file")

        try:
            extract_dir = self._get_search_directory(directory)
            whl_file = self._find_first_whl_file(extract_dir)

            if not whl_file:
                raise FileNotFoundError(
                    f"No .whl file found in directory: {extract_dir}. "
                    "A wheel file is required to extract the Python version."
                )

            python_version = self._extract_python_version_from_whl(whl_file)
            if not python_version:
                raise ValueError(
                    f"Could not extract Python version from .whl file: {whl_file}. "
                    "Expected format: name-version-python-abi-platform.whl"
                )

            full_version = f"Python {python_version}"
            logger.debug("Python version added (from .whl file): %s", full_version)
            return command.add_arg_to_payload(full_version)

        except (FileNotFoundError, ValueError):
            raise
        except Exception as e:
            logger.error("Failed to add Python version: %s", str(e), exc_info=True)
            raise

    def _create_base_structured_command(
        self, local_input_path: str
    ) -> UnifiedGraftModel:
        """
        Creates the base structured command with library metadata.

        Extraction strategy:
        1. Try to extract from .whl filename
        2. If that fails, fallback to .dist-info/METADATA file
        3. If both fail, raise appropriate error

        :param local_input_path: The local input path (extracted wheel directory)
        :return: The structured command with metadata
        :raises FileNotFoundError: If no .whl file or .dist-info/METADATA found
        :raises ValueError: If metadata cannot be extracted from any source
        """
        logger.info("Creating base structured command for analyze")

        # Create base structured command
        structured_command = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.LIBRARY, []
        )

        # Strategy 1: Try filename extraction (existing behavior)
        try:
            logger.debug("Attempting metadata extraction from .whl filename")

            structured_command = self.add_library_namespace(structured_command)
            structured_command = self.add_library_name(
                structured_command, local_input_path
            )
            structured_command = self.add_python_library_version(
                structured_command, local_input_path
            )
            structured_command = self.add_python_runtime_version(
                structured_command, local_input_path
            )
            structured_command = structured_command.add_arg_to_payload(
                ComponentInfo.GMA_UGM_VERSION
            )
            logger.debug("GMA UGM version added: %s", ComponentInfo.GMA_UGM_VERSION)
            logger.info("Successfully extracted metadata from .whl filename")
            return structured_command

        except (FileNotFoundError, ValueError) as e:
            logger.warning(
                "Failed to extract metadata from .whl filename: %s. "
                "Attempting fallback to METADATA file.",
                str(e),
            )

        # Strategy 2: Fallback to .dist-info/METADATA
        try:
            logger.debug("Attempting metadata extraction from .dist-info/METADATA file")
            metadata = self._extract_metadata_from_dist_info(local_input_path)

            # Validate required fields (consistent with _create_base_structured_command_local)
            if not metadata["name"]:
                raise ValueError(
                    f"Could not extract package name from METADATA file in: {local_input_path}"
                )
            if not metadata["version"]:
                raise ValueError(
                    f"Could not extract package version from METADATA file in: {local_input_path}"
                )
            if not metadata["python_requires"]:
                raise ValueError(
                    f"Could not extract Python version requirement from METADATA file in: {local_input_path}"
                )
            structured_command = structured_command.add_arg_to_payload("")
            logger.debug("Library namespace added from METADATA: %s", "")

            # Add metadata to command (same format as config file extraction)
            structured_command = structured_command.add_arg_to_payload(metadata["name"])
            logger.debug("Library name added from METADATA: %s", metadata["name"])

            structured_command = structured_command.add_arg_to_payload(
                metadata["version"]
            )
            logger.debug("Library version added from METADATA: %s", metadata["version"])

            python_version = f"Python {metadata['python_requires']}"
            structured_command = structured_command.add_arg_to_payload(python_version)
            logger.debug(
                "Python version requirement added from METADATA: %s", python_version
            )

            structured_command = structured_command.add_arg_to_payload(
                ComponentInfo.GMA_UGM_VERSION
            )
            logger.debug("GMA UGM version added: %s", ComponentInfo.GMA_UGM_VERSION)

            logger.info("Successfully extracted metadata from .dist-info/METADATA file")
            return structured_command

        except (FileNotFoundError, ValueError) as e:
            logger.error(
                "Failed to extract metadata from both .whl filename and METADATA file: %s",
                str(e),
                exc_info=True,
            )
            raise ValueError(
                f"Could not extract library metadata from {local_input_path}. "
                f"Tried: 1) .whl filename, 2) .dist-info/METADATA file. "
                f"Last error: {str(e)}"
            )

    # =========================================================================
    # LOCAL ANALYSIS METHODS (for analyze_local - uses config files, not .whl)
    # =========================================================================

    def _find_config_file(self, directory: str) -> Optional[Tuple[str, str]]:
        """
        Find Python project config file in directory.

        :param directory: Directory to search in
        :return: Tuple of (file_path, file_type) or None if not found
                 file_type is one of: 'pyproject.toml', 'setup.cfg', 'setup.py'
        """
        config_files = ["pyproject.toml", "setup.cfg", "setup.py"]

        for config_file in config_files:
            file_path = os.path.join(directory, config_file)
            if os.path.isfile(file_path):
                logger.debug("Found config file: %s", file_path)
                return (file_path, config_file)

        return None

    def _find_dist_info_directory(self, directory: str) -> Optional[str]:
        """
        Find the first .dist-info directory in the given directory.

        :param directory: Directory to search in
        :return: Path to .dist-info directory or None if not found
        """
        try:
            for item in os.listdir(directory):
                item_path = os.path.join(directory, item)
                if os.path.isdir(item_path) and item.endswith(".dist-info"):
                    logger.debug("Found .dist-info directory: %s", item_path)
                    return item_path
        except Exception as e:
            logger.warning("Error scanning directory %s: %s", directory, str(e))

        return None

    def _extract_metadata_from_dist_info(
        self, directory: str
    ) -> Dict[str, Optional[str]]:
        """
        Extract package metadata from .dist-info/METADATA file.

        Searches for .dist-info directory and parses the METADATA file (RFC 822 format).

        :param directory: Directory containing .dist-info folder (extracted wheel directory)
        :return: Dict with 'name', 'version', 'python_requires' keys
        :raises FileNotFoundError: If no .dist-info directory or METADATA file found
        """
        result: Dict[str, Optional[str]] = {
            "name": None,
            "version": None,
            "python_requires": None,
        }

        # Step 1: Find .dist-info directory
        dist_info_dir = self._find_dist_info_directory(directory)
        if not dist_info_dir:
            raise FileNotFoundError(
                f"No .dist-info directory found in: {directory}. "
                "METADATA file requires a .dist-info directory from an extracted wheel."
            )

        # Step 2: Locate METADATA file
        metadata_path = os.path.join(dist_info_dir, "METADATA")
        if not os.path.isfile(metadata_path):
            raise FileNotFoundError(
                f"METADATA file not found in .dist-info directory: {dist_info_dir}"
            )

        # Step 3: Parse RFC 822 format using email.parser
        try:
            from email.parser import Parser

            with open(metadata_path, "r", encoding="utf-8") as f:
                msg = Parser().parse(f)

            # Extract standard fields
            result["name"] = msg.get("Name")
            result["version"] = msg.get("Version")
            result["python_requires"] = msg.get("Requires-Python")

            logger.debug("Extracted from METADATA file: %s", result)
            return result

        except Exception as e:
            logger.warning(
                "Failed to parse METADATA file %s: %s", metadata_path, str(e)
            )
            return result

    def _extract_metadata_from_config(self, directory: str) -> Dict[str, Optional[str]]:
        """
        Extract package metadata from config files.

        Searches for pyproject.toml, setup.cfg, or setup.py and extracts:
        - name: package name
        - version: package version
        - python_requires: required Python version

        :param directory: Directory containing config files
        :return: Dict with 'name', 'version', 'python_requires' keys
        :raises FileNotFoundError: If no config file is found
        """
        config = self._find_config_file(directory)
        if not config:
            raise FileNotFoundError(
                f"No config file (pyproject.toml, setup.cfg, setup.py) "
                f"found in directory: {directory}"
            )

        file_path, file_type = config

        if file_type == "pyproject.toml":
            return self._extract_from_pyproject_toml(file_path)
        elif file_type == "setup.cfg":
            return self._extract_from_setup_cfg(file_path)
        elif file_type == "setup.py":
            return self._extract_from_setup_py(file_path)

        raise ValueError(f"Unknown config file type: {file_type}")

    def _extract_from_pyproject_toml(self, file_path: str) -> Dict[str, Optional[str]]:
        """
        Extract metadata from pyproject.toml file.

        Supports both [project] table (PEP 621) and [tool.poetry] table.
        """
        result: Dict[str, Optional[str]] = {
            "name": None,
            "version": None,
            "python_requires": None,
        }

        try:
            # Try to use tomllib (Python 3.11+) or tomli
            try:
                import tomllib

                with open(file_path, "rb") as f:
                    data = tomllib.load(f)
            except ImportError:
                try:
                    import tomli

                    with open(file_path, "rb") as f:
                        data = tomli.load(f)
                except ImportError:
                    # Fallback: simple regex parsing for basic cases
                    return self._extract_from_pyproject_toml_regex(file_path)

            # Try [project] table first (PEP 621)
            if "project" in data:
                project = data["project"]
                result["name"] = project.get("name")
                result["version"] = project.get("version")
                result["python_requires"] = project.get("requires-python")

            # Try [tool.poetry] table if project not found
            if not result["name"] and "tool" in data and "poetry" in data["tool"]:
                poetry = data["tool"]["poetry"]
                result["name"] = poetry.get("name")
                result["version"] = poetry.get("version")
                # Poetry uses 'python' key for version constraint
                result["python_requires"] = poetry.get("python")

            logger.debug("Extracted from pyproject.toml: %s", result)
            return result

        except Exception as e:
            logger.warning("Failed to parse pyproject.toml: %s", str(e))
            return result

    def _extract_from_pyproject_toml_regex(
        self, file_path: str
    ) -> Dict[str, Optional[str]]:
        """Fallback regex-based parsing for pyproject.toml."""
        result: Dict[str, Optional[str]] = {
            "name": None,
            "version": None,
            "python_requires": None,
        }

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Simple regex patterns
            name_match = re.search(r'^name\s*=\s*["\']([^"\']+)["\']', content, re.M)
            version_match = re.search(
                r'^version\s*=\s*["\']([^"\']+)["\']', content, re.M
            )
            python_match = re.search(
                r'^requires-python\s*=\s*["\']([^"\']+)["\']', content, re.M
            )

            if name_match:
                result["name"] = name_match.group(1)
            if version_match:
                result["version"] = version_match.group(1)
            if python_match:
                result["python_requires"] = python_match.group(1)

        except Exception as e:
            logger.warning("Failed to parse pyproject.toml with regex: %s", str(e))

        return result

    def _extract_from_setup_cfg(self, file_path: str) -> Dict[str, Optional[str]]:
        """Extract metadata from setup.cfg file."""
        result: Dict[str, Optional[str]] = {
            "name": None,
            "version": None,
            "python_requires": None,
        }

        try:
            config = configparser.ConfigParser()
            config.read(file_path, encoding="utf-8")

            if "metadata" in config:
                result["name"] = config.get("metadata", "name", fallback=None)
                result["version"] = config.get("metadata", "version", fallback=None)

            if "options" in config:
                result["python_requires"] = config.get(
                    "options", "python_requires", fallback=None
                )

            logger.debug("Extracted from setup.cfg: %s", result)

        except Exception as e:
            logger.warning("Failed to parse setup.cfg: %s", str(e))

        return result

    def _extract_from_setup_py(self, file_path: str) -> Dict[str, Optional[str]]:
        """
        Extract metadata from setup.py using AST parsing.

        This method parses setup.py as Python AST and looks for
        setup() or setuptools.setup() calls.
        """
        result: Dict[str, Optional[str]] = {
            "name": None,
            "version": None,
            "python_requires": None,
        }

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    # Check if it's a setup() call
                    func_name = None
                    if isinstance(node.func, ast.Name):
                        func_name = node.func.id
                    elif isinstance(node.func, ast.Attribute):
                        func_name = node.func.attr

                    if func_name == "setup":
                        # Extract keyword arguments
                        for keyword in node.keywords:
                            if keyword.arg == "name" and isinstance(
                                keyword.value, ast.Constant
                            ):
                                result["name"] = keyword.value.value
                            elif keyword.arg == "version" and isinstance(
                                keyword.value, ast.Constant
                            ):
                                result["version"] = keyword.value.value
                            elif keyword.arg == "python_requires" and isinstance(
                                keyword.value, ast.Constant
                            ):
                                result["python_requires"] = keyword.value.value

            logger.debug("Extracted from setup.py: %s", result)

        except Exception as e:
            logger.warning("Failed to parse setup.py: %s", str(e))

        return result

    def _create_base_structured_command_local(
        self, local_input_path: str
    ) -> UnifiedGraftModel:
        """
        Creates the base structured command for local analysis.

        Extraction strategy:
        1. Try config files (pyproject.toml, setup.cfg, setup.py)
        2. If that fails, fallback to .dist-info/METADATA file

        :param local_input_path: The local input path (directory with Python code)
        :return: The structured command with metadata
        :raises FileNotFoundError: If no config file or .dist-info/METADATA found
        :raises ValueError: If required metadata cannot be extracted
        """
        logger.info("Creating base structured command for local analysis")

        metadata: Dict[str, Optional[str]] = None

        # Strategy 1: Try config files first
        try:
            logger.debug("Attempting metadata extraction from config files")
            metadata = self._extract_metadata_from_config(local_input_path)
            logger.info("Successfully extracted metadata from config files")
        except FileNotFoundError as e:
            logger.warning(
                "No config files found: %s. Attempting fallback to .dist-info/METADATA.",
                str(e),
            )

        # Strategy 2: Fallback to .dist-info/METADATA
        if metadata is None:
            try:
                logger.debug(
                    "Attempting metadata extraction from .dist-info/METADATA file"
                )
                metadata = self._extract_metadata_from_dist_info(local_input_path)
                logger.info("Successfully extracted metadata from .dist-info/METADATA")
            except FileNotFoundError as e:
                logger.error(
                    "Failed to extract metadata from both config files and "
                    ".dist-info/METADATA: %s",
                    str(e),
                )
                raise FileNotFoundError(
                    f"No metadata source found in: {local_input_path}. "
                    f"Tried: 1) config files (pyproject.toml, setup.cfg, setup.py), "
                    f"2) .dist-info/METADATA file."
                )

        # Validate required fields
        if not metadata["name"]:
            raise ValueError(
                f"Could not extract package name from metadata sources in: "
                f"{local_input_path}"
            )
        if not metadata["version"]:
            raise ValueError(
                f"Could not extract package version from metadata sources in: "
                f"{local_input_path}"
            )
        if not metadata["python_requires"]:
            raise ValueError(
                f"Could not extract Python version requirement from metadata sources in: "
                f"{local_input_path}"
            )

        # Create base structured command
        structured_command = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.LIBRARY, []
        )

        # Add library namespace
        structured_command = structured_command.add_arg_to_payload("")
        logger.debug("Library namespace added: %s", "")

        # Add library name
        structured_command = structured_command.add_arg_to_payload(metadata["name"])
        logger.debug("Library name added: %s", metadata["name"])

        # Add library version
        structured_command = structured_command.add_arg_to_payload(metadata["version"])
        logger.debug("Library version added: %s", metadata["version"])

        # Add Python version requirement (with "Python " prefix)
        python_version = f"Python {metadata['python_requires']}"
        structured_command = structured_command.add_arg_to_payload(python_version)
        logger.debug("Python version requirement added: %s", python_version)

        # Add GMA UGM version
        structured_command = structured_command.add_arg_to_payload(
            ComponentInfo.GMA_UGM_VERSION
        )
        logger.debug("GMA UGM version added: %s", ComponentInfo.GMA_UGM_VERSION)

        return structured_command

    def _detect_input_type(self, local_input_path: str) -> str:
        """
        Detect whether input is a .whl file or source directory.

        :param local_input_path: Path to analyze
        :return: "whl_file", "source_directory", or "unknown"
        """
        # Check if it's a .whl file
        if os.path.isfile(local_input_path) and local_input_path.endswith(".whl"):
            return "whl_file"

        # Check if it's a directory
        if os.path.isdir(local_input_path):
            # Check if directory contains a .whl file
            whl_file = self._find_first_whl_file(local_input_path)
            if whl_file:
                return "whl_file"

            # Check if it's an extracted wheel directory (has .dist-info)
            dist_info = self._find_dist_info_directory(local_input_path)
            if dist_info:
                return "whl_file"

            # Check if it's a source directory with config files
            config_file = self._find_config_file(local_input_path)
            if config_file:
                return "source_directory"

        return "unknown"

    def _create_base_structured_command_unified(
        self, local_input_path: str
    ) -> UnifiedGraftModel:
        """
        Creates base structured command for local analysis (unified approach).

        Auto-detects input type and uses appropriate extraction strategy:
        - For .whl files: filename → METADATA fallback
        - For source directories: config files (existing behavior)

        :param local_input_path: Path to source directory or .whl file
        :return: Structured command with metadata
        :raises FileNotFoundError: If no metadata source found
        :raises ValueError: If metadata incomplete or invalid
        """
        logger.info("Creating base structured command for local analysis (unified)")

        # Step 1: Detect input type
        input_type = self._detect_input_type(local_input_path)
        logger.debug("Detected input type: %s", input_type)

        # Step 2: Route to appropriate extraction strategy
        if input_type == "whl_file":
            # Use enhanced method (filename → METADATA fallback)
            return self._create_base_structured_command(local_input_path)
        elif input_type == "source_directory":
            # Use existing method for config files
            return self._create_base_structured_command_local(local_input_path)
        else:
            raise ValueError(
                f"Cannot determine input type for: {local_input_path}. "
                f"Expected .whl file or source directory with config files."
            )

    def _serialize_result(self, structured_command: UnifiedGraftModel) -> bytes:
        """
        Serializes the structured command to bytes.

        :param structured_command: The structured command to serialize
        :return: Serialized bytes
        """
        logger.info("Serializing result")
        unified_graft_model_serializer = UnifiedGraftModelSerializer()
        try:
            result = unified_graft_model_serializer.serialize(structured_command)
            logger.info("Result serialized successfully")
            return result
        except Exception as e:
            logger.error(f"Serialization failed: {str(e)}")
            raise

    def _perform_analysis(
        self,
        local_input_path: str,
        structured_command: UnifiedGraftModel,
        type_filter: str = "",
        method_filter: str = "",
    ) -> UnifiedGraftModel:
        """
        Performs the main analysis of classes, functions, and variables.

        :param local_input_path: The local input path
        :param structured_command: The structured command to update
        :param type_filter: Comma-separated wildcard patterns for types to analyze
        :param method_filter: Comma-separated wildcard patterns for methods to analyze
        :return: Updated structured command with analysis results
        """
        # Initialize handlers for analysis
        handlers = Handlers()
        handlers.method_filter = method_filter or ""

        # Set current library name for external type detection
        # payload[1] contains the library name (payload[0] is library_namespace)
        if structured_command.payload and len(structured_command.payload) > 1:
            handlers.current_library_name = structured_command.payload[1]

        # Set current library import roots for assembly name resolution
        handlers.current_library_import_roots = self._collect_import_roots(
            local_input_path
        )

        # Analyze classes
        structured_command = self._analyze_classes(
            local_input_path, handlers, structured_command, type_filter
        )

        # Global functions/variables are module-level symbols that don't belong
        # to any type.  When a type_filter is active the caller only wants
        # specific types, so globals are outside that scope.
        if not type_filter:
            structured_command = self._analyze_global_functions_and_variables(
                local_input_path, handlers, structured_command
            )
        else:
            logger.info(
                "Skipping global functions/variables analysis (type_filter is active)"
            )

        return structured_command

    def _setup_dependency_paths(self, local_input_path: str) -> None:
        """
        Set up sys.path to include all extracted wheel directories for dependency resolution.
        This enables imports between wheels that are extracted in the same parent directory.

        :param local_input_path: The local input path (can be file or directory)
        """
        # Determine the base directory to scan
        if os.path.isfile(local_input_path):
            base_dir = os.path.dirname(local_input_path)
        else:
            base_dir = local_input_path

        # Also check the parent directory for sibling wheels
        parent_dir = os.path.dirname(base_dir)

        directories_to_scan = [base_dir, parent_dir]

        for scan_dir in directories_to_scan:
            if not os.path.exists(scan_dir):
                continue

            # Find and add all directories that look like extracted wheels
            for item in os.listdir(scan_dir):
                item_path = os.path.join(scan_dir, item)
                if os.path.isdir(item_path):
                    # Check if this directory contains a .dist-info subfolder
                    # (indicating it's an extracted wheel)
                    has_dist_info = any(
                        d.endswith(".dist-info")
                        for d in os.listdir(item_path)
                        if os.path.isdir(os.path.join(item_path, d))
                    )
                    if has_dist_info and item_path not in sys.path:
                        sys.path.insert(0, item_path)
                        logger.debug(
                            f"Added to sys.path for dependency resolution: {item_path}"
                        )

    def _analyze_classes(
        self,
        local_input_path: str,
        handlers: "Handlers",
        structured_command: UnifiedGraftModel,
        type_filter: str = "",
    ) -> UnifiedGraftModel:
        """
        Analyzes classes from the input path.

        :param local_input_path: The local input path
        :param handlers: The handlers instance
        :param structured_command: The structured command to update
        :param type_filter: Comma-separated wildcard patterns for types to analyze
        :return: Updated structured command
        """
        logger.info("Analyzing classes")

        # Save original sys.path
        original_sys_path = sys.path.copy()

        try:
            # Set up dependency paths for import resolution
            self._setup_dependency_paths(local_input_path)

            classes_to_analyze = InterfaceAnalyzer.return_classes_from_py(
                local_input_path
            )

            # Filter classes based on type_filter
            if type_filter:
                filtered_classes = []
                for cls in classes_to_analyze:
                    # Get full type name: module.class_name
                    module_name = getattr(cls, "__module__", "")
                    class_name = getattr(cls, "__name__", "")
                    full_type_name = (
                        f"{module_name}.{class_name}" if module_name else class_name
                    )

                    if TypeFilterHelper.matches_filter(full_type_name, type_filter):
                        filtered_classes.append(cls)
                classes_to_analyze = filtered_classes
                logger.info(
                    f"Filtered to {len(classes_to_analyze)} classes matching type_filter: {type_filter}"
                )

            handlers.types_to_analyze.extend(classes_to_analyze)
            logger.info(f"Found {len(classes_to_analyze)} classes to analyze")

            while len(handlers.types_to_analyze) > 0:
                current_class = handlers.types_to_analyze.pop(0)
                structured_command = structured_command.add_arg_to_payload(
                    handlers.analyzer_handler.get(
                        UnifiedGraftModelType.TYPE_DEF
                    ).generate_unified_graft_model(
                        current_class, structured_command, handlers
                    )
                )
        finally:
            # Restore original sys.path
            sys.path = original_sys_path

        return structured_command

    def _analyze_global_functions_and_variables(
        self,
        local_input_path: str,
        handlers: "Handlers",
        structured_command: UnifiedGraftModel,
    ) -> UnifiedGraftModel:
        """
        Analyzes global functions and variables from the input path.

        :param local_input_path: The local input path
        :param handlers: The handlers instance
        :param structured_command: The structured command to update
        :return: Updated structured command
        """
        logger.info("Extracting module members")
        functions, variables = self._extract_global_functions_and_variables(
            local_input_path
        )
        logger.info(
            f"Module members extracted:\n"
            f"  - Functions: {len(functions)}\n"
            f"  - Variables: {len(variables)}"
        )

        # Analyze global functions
        if functions:
            logger.info("Analyzing global functions")
            for func_obj in functions:
                func_name = getattr(func_obj, "__name__", str(func_obj))
                if not MethodFilterHelper.matches_filter(
                    func_name, handlers.method_filter
                ):
                    continue
                function_model = handlers.analyzer_handler.get(
                    UnifiedGraftModelType.GLOBAL_METHOD
                ).generate_unified_graft_model(
                    func_obj,
                    structured_command,
                    handlers,
                )
                structured_command = structured_command.add_arg_to_payload(
                    function_model
                )
            logger.info(f"Analyzed {len(functions)} global functions")

        # Analyze global variables
        if variables:
            logger.info("Analyzing global variables")
            for var_name in variables:
                variable_model = handlers.analyzer_handler.get(
                    UnifiedGraftModelType.GLOBAL_FIELD
                ).generate_unified_graft_model(var_name, structured_command, handlers)
                structured_command = structured_command.add_arg_to_payload(
                    variable_model
                )
            logger.info(f"Analyzed {len(variables)} global variables")

        return structured_command

    def _extract_global_functions_and_variables(
        self, file_path: str
    ) -> Tuple[List[Any], List[str]]:
        """
        Extracts actual function and variable objects from a Python module.

        :param file_path: Path to the Python file or directory
        :return: Tuple of (list of function objects, list of variable names)
        """
        # Handle directory - process all Python files
        if os.path.isdir(file_path):
            return self._extract_from_directory(file_path)

        # Handle single Python file
        if file_path.endswith(".py"):
            return self._extract_from_single_file(file_path)

        logger.warning("Unsupported file type for function extraction: %s", file_path)
        return [], []

    def _extract_from_directory(
        self, directory_path: str
    ) -> Tuple[List[Any], List[str]]:
        """
        Extracts functions and variables from all Python files in a directory.

        :param directory_path: Path to the directory containing Python files
        :return: Tuple of (list of function objects, list of variable names)
        """
        from moduleanalyzer.src.core.handler.interface_analyzer import EXCLUDED_DIRS

        all_functions = []
        all_variables = []

        for root, dirs, files in os.walk(directory_path):
            dirs[:] = [
                d
                for d in dirs
                if not d.endswith(".dist-info") and d not in EXCLUDED_DIRS
            ]
            for file in files:
                if file.endswith(".py"):
                    py_file_path = os.path.join(root, file)
                    functions, variables = self._extract_from_single_file(py_file_path)
                    all_functions.extend(functions)
                    all_variables.extend(variables)

        logger.info(
            "Extracted %d functions and %d variables from directory",
            len(all_functions),
            len(all_variables),
        )
        return all_functions, all_variables

    def _collect_import_roots(self, local_input_path: str) -> frozenset[str]:
        """
        Collect top-level Python import names from classes in the analyzed library.

        Used to resolve ASSEMBLY_NAME when distribution name differs from import root
        (e.g. package 'complex-generics-and-arrays' imported as 'complexGenerics').
        """
        import_roots: set[str] = set()
        try:
            classes = InterfaceAnalyzer.return_classes_from_py(local_input_path)
            for cls in classes:
                module = getattr(cls, "__module__", None)
                if module and module not in ("__main__", "builtins", "typing"):
                    import_roots.add(module.split(".")[0])
        except Exception:
            logger.debug(
                "Could not collect import roots from %s", local_input_path, exc_info=True
            )
        return frozenset(import_roots)

    def _get_package_context(self, file_path: str) -> Tuple[str, str, Optional[str]]:
        """
        Determines the proper package context for a Python file.

        For a file like /path/to/sdn_test_simple_car/__init__.py:
        - package_name = "sdn_test_simple_car"
        - module_name = "sdn_test_simple_car" (for __init__.py) or
                        "sdn_test_simple_car.simple_car" (for simple_car.py)
        - package_path = /path/to/sdn_test_simple_car

        :param file_path: Absolute path to the Python file
        :return: Tuple of (module_name, package_name, package_path)
        """
        file_name = os.path.basename(file_path)
        parent_dir = os.path.dirname(file_path)
        package_name = os.path.basename(parent_dir)

        # Check if parent directory is a Python package (has __init__.py)
        init_path = os.path.join(parent_dir, "__init__.py")
        is_package = os.path.isfile(init_path)

        if is_package:
            if file_name == "__init__.py":
                module_name = package_name
            else:
                base_name = os.path.splitext(file_name)[0]
                module_name = f"{package_name}.{base_name}"
            return module_name, package_name, parent_dir
        else:
            # Not a package, just a standalone file
            module_name = os.path.splitext(file_name)[0]
            return module_name, None, None

    def _setup_package_in_sys_modules(
        self, package_name: str, package_path: str
    ) -> None:
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
        init_path = os.path.join(package_path, "__init__.py")

        # Add the parent directory to sys.path temporarily for imports
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

    def _extract_from_single_file(self, file_path: str) -> Tuple[List[Any], List[str]]:
        """
        Extracts functions and variables from a single Python file.

        :param file_path: Path to the Python file
        :return: Tuple of (list of function objects, list of variable names)
        """
        # Guard sys.path so path mutations here don't leak to callers that do
        # not restore sys.path themselves (e.g. _analyze_global_functions_and_variables).
        original_sys_path = sys.path.copy()
        try:
            module_name, package_name, package_path = self._get_package_context(
                file_path
            )

            # If this file is part of a package, set up the package context first
            # This ensures relative imports work correctly from the start
            if package_name and package_path:
                self._setup_package_in_sys_modules(package_name, package_path)

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

            if spec is None or spec.loader is None:
                logger.warning("Could not load module from %s", file_path)
                return [], []

            module = importlib.util.module_from_spec(spec)
            if package_name:
                module.__package__ = package_name
            sys.modules[module_name] = module

            spec.loader.exec_module(module)

            functions = []
            variables = []

            # Extract functions and variables from the module
            for name, obj in inspect.getmembers(module):
                # Skip private/magic members and imports
                if name.startswith("_"):
                    continue

                # Skip typing module imports (List, Optional, Dict, etc.)
                obj_module = getattr(obj, "__module__", None)
                if obj_module in ("typing", "typing_extensions", "collections.abc"):
                    continue

                # Check if it's a function defined in this module
                if inspect.isfunction(obj):
                    if hasattr(obj, "__module__") and obj.__module__ == module_name:
                        functions.append(obj)
                        logger.debug("Extracted function: %s", name)
                # Check if it's a module-level variable (not a class, module, or function)
                elif not (
                    inspect.isclass(obj)
                    or inspect.ismodule(obj)
                    or inspect.ismethod(obj)
                    or inspect.isbuiltin(obj)
                ):
                    # Additional check: skip special form types from typing
                    obj_type_name = type(obj).__name__
                    if obj_type_name in (
                        "_GenericAlias",
                        "_SpecialForm",
                        "_SpecialGenericAlias",
                    ):
                        continue
                    variables.append(name)
                    logger.debug("Extracted variable: %s", name)

            logger.debug(
                "Extracted %d functions and %d variables from %s",
                len(functions),
                len(variables),
                file_path,
            )
            return functions, variables

        except Exception as e:  # pylint: disable=broad-except
            logger.error(
                "Failed to extract functions and variables from %s: %s",
                file_path,
                str(e),
                exc_info=True,
            )
            return [], []
        finally:
            sys.path = original_sys_path
