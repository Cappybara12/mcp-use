import os
import shutil
import tempfile

from graftcode_python_logger import GCLoggerFactory, GCLoggerOptions, LogLevel

from moduleanalyzer.src.core.handler.analysis.library_analyzer import LibraryAnalyzer
from moduleanalyzer.src.core.handler.interface_analyzer import InterfaceAnalyzer
from graftcode_protocol.protocol.serializers.dependency_tree_to_json_serializer import (
    DependencyTreeToJsonSerializer,
)
from graftcode_protocol.protocol.serializers.hosted_library_statistics_to_json_serializer import (
    HostedLibraryStatisticsToJsonSerializer,
)
from moduleanalyzer.src.core.statistics.ugm_hosted_library_statistics_builder import (
    UgmHostedLibraryStatisticsBuilder,
)
from moduleanalyzer.src.core.dependency.local_dependency_tree_builder import (
    build_dependency_tree_from_path,
)
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
logger.info("GraftCode Module Analyzer Local module initialized")


class PythonModuleAnalyzerLocal:
    def __init__(self) -> None:
        """
        Initializes the PythonModuleAnalyzerLocal instance by
        configuring the local temporary directory.
        """
        logger.info("Initializing PythonModuleAnalyzerLocal")

        # Use a dedicated subdirectory to avoid nuking shared /tmp contents
        # (e.g. OpenCensus exporter storage) during cleanup.
        base_temp = os.getenv("LOCAL_TEMP_DIR", "/tmp")
        self.local_temp_dir = os.path.join(base_temp, "gma-python")
        os.makedirs(self.local_temp_dir, exist_ok=True)

        self.library_analyzer = LibraryAnalyzer()

    def _find_dist_info_for_package(self, parent_dir: str, package_name: str) -> str:
        """
        Find the .dist-info directory for a package in the parent directory.

        Handles different naming conventions:
        - package_name → package-name.dist-info
        - package_name → package_name.dist-info
        - package_name → package_name-version.dist-info

        :param parent_dir: Parent directory to search (e.g., site-packages)
        :param package_name: Name of the package (e.g., "sdn_test_simple_car")
        :return: Name of .dist-info directory if found, None otherwise
        """
        if not os.path.isdir(parent_dir):
            return None

        # Normalize package name (replace _ with -)
        normalized_name = package_name.replace("_", "-")

        try:
            for item in os.listdir(parent_dir):
                if not item.endswith(".dist-info"):
                    continue

                # Check if it matches the package name
                # Handle: package-name-version.dist-info or package-name.dist-info
                item_lower = item.lower()
                if item_lower.startswith(normalized_name.lower() + "-"):
                    logger.debug(f"Found matching .dist-info: {item}")
                    return item

                # Also check original package name with underscores
                if item_lower.startswith(package_name.lower() + "-"):
                    logger.debug(f"Found matching .dist-info: {item}")
                    return item

        except Exception as e:
            logger.warning(f"Error searching for .dist-info in {parent_dir}: {str(e)}")

        return None

    @staticmethod
    def _find_config_in_ancestors(start_path: str, max_depth: int = 5) -> str | None:
        """
        Walk up the directory tree from *start_path* looking for the nearest
        Python project config file (pyproject.toml, setup.cfg, setup.py).

        :param start_path: File or directory to start searching from.
        :param max_depth: Maximum number of parent levels to traverse.
        :return: Absolute path to the config file, or ``None``.
        """
        config_names = ("pyproject.toml", "setup.cfg", "setup.py")
        current = os.path.abspath(start_path)
        if os.path.isfile(current):
            current = os.path.dirname(current)

        for _ in range(max_depth):
            parent = os.path.dirname(current)
            if parent == current:
                break
            current = parent
            for cfg_name in config_names:
                candidate = os.path.join(current, cfg_name)
                if os.path.isfile(candidate):
                    return candidate
        return None

    def _extract_zip_for_local_analysis(self, zip_path: str) -> str:
        """
        Extract .zip file for local analysis.

        This method extracts:
        1. The main .zip archive
        2. Any .whl files found inside (recursively)
        3. Creates Python package structure (__init__.py files)

        :param zip_path: Path to .zip file
        :return: Path to extracted directory
        :raises ValueError: If extraction fails
        """
        try:
            # Use PackageExtractor to handle extraction
            extracted_dir = PackageExtractor.extract_zip(zip_path)
            logger.info(f"Successfully extracted .zip to: {extracted_dir}")
            return extracted_dir

        except Exception as e:
            logger.error(
                f"Failed to extract .zip file {zip_path}: {str(e)}", exc_info=True
            )
            raise ValueError(
                f"Could not extract .zip file: {zip_path}. Error: {str(e)}"
            )

    def analyze_local(
        self,
        source_path: str,
        type_filter: str = "",
        method_filter: str = "",
        trace_id: str = "",
        parent_trace_id: str = "",
    ) -> bytes:
        """
        Analyzes a Python module/directory from local sourcePath

        :param source_path: Path of module to analyze - directory path or fileInDirectory path.
        :param type_filter: Comma-separated wildcard patterns for types to analyze
                          (e.g., "my_namespace.*, *Service, Test*").
                          Empty string means analyze all types.
        :param method_filter: Comma-separated wildcard patterns for methods to analyze
                          (e.g., "get_*, *Async").
                          Empty string means analyze all methods.
        :param trace_id: Trace ID for cross-service correlation.
        :param parent_trace_id: Parent trace ID for cross-service correlation.
        :return: A bytes object containing the serialized output.
        :raises IOError: If file operations or serialization fails.
        """
        with GCLoggerFactory.track_operation(
            logger,
            "PythonModuleAnalyzer.analyze_local",
            properties={
                "source_path": source_path,
            },
            operation_id=trace_id or None,
            parent_span_id=parent_trace_id or None,
        ):
            logger.info(
                f"Starting Python module analysis local for path={source_path}",
                extra={
                    "custom_dimensions": {
                        "source_path": source_path,
                    }
                },
            )

            # Handle .zip file extraction (but NOT .whl files)
            # .whl files are also ZIP format, but should be handled by existing logic
            working_source_path = source_path
            temp_extract_dir = None

            if (
                os.path.isfile(source_path)
                and source_path.endswith(".zip")
                and PackageExtractor.is_zip_file(source_path)
            ):
                logger.info(f"Detected .zip file, extracting: {source_path}")
                temp_extract_dir = self._extract_zip_for_local_analysis(source_path)
                working_source_path = temp_extract_dir
                logger.info(f"Extracted to: {working_source_path}")

            source_module_path = InterfaceAnalyzer._resolve_directory_path(
                working_source_path
            )
            source_module_name = InterfaceAnalyzer._resolve_directory_name_or_file_name(
                working_source_path
            )
            workdir_root = tempfile.mkdtemp()
            workdir_module_path = os.path.join(workdir_root, source_module_name)

            FileUtils._copy_directory(source_module_path, workdir_module_path, logger)

            # Auto-generate `__init__.py` in the throwaway workdir copy so that
            # flat-layout Python projects (no `__init__.py` in user's source)
            # are analysed as proper packages. This lets Python resolve both
            # absolute sibling imports (`from price_calculator import X`) and
            # relative imports (`from .price_calculator import X`) uniformly.
            # The user's original source tree is never touched because the
            # init files are created in the *copy* under `workdir_root`.
            InterfaceAnalyzer._create_init_files(workdir_module_path)

            parent_dir = os.path.dirname(source_module_path)

            # For pip-installed packages, copy .dist-info from parent directory
            # into the workdir so metadata extraction can find it
            dist_info_name = self._find_dist_info_for_package(
                parent_dir, source_module_name
            )
            if dist_info_name:
                source_dist_info = os.path.join(parent_dir, dist_info_name)
                workdir_dist_info = os.path.join(workdir_module_path, dist_info_name)
                logger.info(
                    f"Found .dist-info directory, copying to module: {source_dist_info}"
                )
                FileUtils._copy_directory(source_dist_info, workdir_dist_info, logger)

            # For src-layout packages, copy config file from parent directory
            # into the workdir (mirrors the .dist-info parent lookup above)
            config_files = ["pyproject.toml", "setup.cfg", "setup.py"]
            has_config_in_workdir = any(
                os.path.exists(os.path.join(workdir_module_path, cfg))
                for cfg in config_files
            )
            if not has_config_in_workdir and os.path.isdir(parent_dir):
                for cfg in config_files:
                    parent_cfg = os.path.join(parent_dir, cfg)
                    if os.path.isfile(parent_cfg):
                        dest_cfg = os.path.join(workdir_module_path, cfg)
                        shutil.copy2(parent_cfg, dest_cfg)
                        logger.info(
                            f"Found config file in parent directory, "
                            f"copying to workdir: {parent_cfg}"
                        )
                        has_config_in_workdir = True
                        break

            # If still no config, walk up the ancestor directories from the
            # *original* source path (handles deep package structures where
            # pyproject.toml is several levels above the analysed subpackage).
            if not has_config_in_workdir:
                ancestor_cfg = self._find_config_in_ancestors(source_module_path)
                if ancestor_cfg:
                    cfg_name = os.path.basename(ancestor_cfg)
                    dest_cfg = os.path.join(workdir_module_path, cfg_name)
                    shutil.copy2(ancestor_cfg, dest_cfg)
                    logger.info(
                        "Found config file in ancestor directory, "
                        f"copying to workdir: {ancestor_cfg}"
                    )

            try:
                # Determine which method to use based on available files
                has_config = any(
                    os.path.exists(os.path.join(workdir_module_path, config))
                    for config in config_files
                )

                # Check for .whl file - either in workdir_root or in parent of source_module_path
                # (for extracted .zip → .whl case)
                parent_has_whl = False

                # Check in workdir_root (temp directory parent)
                if workdir_root and os.path.exists(workdir_root):
                    parent_has_whl = any(
                        f.endswith(".whl") for f in os.listdir(workdir_root)
                    )

                # Also check in the parent of source_module_path (where .whl was extracted from)
                if not parent_has_whl and source_module_path:
                    source_parent = os.path.dirname(source_module_path)
                    if source_parent and os.path.exists(source_parent):
                        parent_has_whl = any(
                            f.endswith(".whl") for f in os.listdir(source_parent)
                        )

                if has_config:
                    # Use local method for directories with config files
                    logger.debug(
                        "Using _create_base_structured_command_local (config files found)"
                    )
                    structured_command = (
                        self.library_analyzer._create_base_structured_command_local(
                            workdir_module_path
                        )
                    )
                elif parent_has_whl:
                    # Use regular method for extracted .whl (looks for .whl in parent)
                    logger.debug(
                        "Using _create_base_structured_command (.whl file found)"
                    )
                    structured_command = (
                        self.library_analyzer._create_base_structured_command(
                            workdir_module_path
                        )
                    )
                else:
                    # Fallback to local method, will raise appropriate error
                    logger.debug(
                        "Using _create_base_structured_command_local (fallback)"
                    )
                    structured_command = (
                        self.library_analyzer._create_base_structured_command_local(
                            workdir_module_path
                        )
                    )

                structured_command = self.library_analyzer._perform_analysis(
                    workdir_module_path, structured_command, type_filter, method_filter
                )
                result = self.library_analyzer._serialize_result(structured_command)
                logger.info("Python module analysis completed successfully")
                return result

            except (OSError, IOError, ValueError) as e:
                logger.error(
                    f"Analyze failed (expected error): {str(e)}", exc_info=True
                )
                raise
            except Exception as e:
                logger.error(
                    f"Analyze failed (unexpected error): {str(e)}", exc_info=True
                )
                raise
            finally:
                FileUtils._cleanup_directory(self.local_temp_dir, logger)

                # Cleanup extracted .zip directories
                if temp_extract_dir and os.path.exists(temp_extract_dir):
                    try:
                        shutil.rmtree(temp_extract_dir)
                        logger.debug(
                            f"Cleaned up extracted .zip directory: {temp_extract_dir}"
                        )
                    except Exception as e:
                        logger.warning(f"Failed to cleanup .zip extraction: {str(e)}")

    def get_dependency_tree_local(
        self, source_path: str, trace_id: str = "", parent_trace_id: str = ""
    ) -> str:
        with GCLoggerFactory.track_operation(
            logger,
            "PythonModuleAnalyzer.get_dependency_tree_local",
            properties={"source_path": source_path},
            operation_id=trace_id or None,
            parent_span_id=parent_trace_id or None,
        ):
            tree = build_dependency_tree_from_path(source_path)
            return DependencyTreeToJsonSerializer.serialize(tree)

    def get_hosted_library_statistics_local(self, analyzed_package: bytes) -> str:
        statistics = UgmHostedLibraryStatisticsBuilder.build(analyzed_package)
        return HostedLibraryStatisticsToJsonSerializer.serialize(statistics)
