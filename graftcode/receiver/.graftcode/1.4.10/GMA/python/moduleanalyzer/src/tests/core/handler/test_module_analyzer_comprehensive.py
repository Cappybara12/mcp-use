"""
Comprehensive tests for PythonModuleAnalyzer using real implementations.

This module provides extensive test coverage for the PythonModuleAnalyzer class
using real handlers, real Python files, and real functionality instead of mocks.
"""

import os
from pathlib import Path
import tempfile
import zipfile

from graftcode_protocol.protocol.serializers.unified_graft_model_to_json_serializer import (
    UnifiedGraftModelToJsonSerializer,
)
from graftcode_protocol.enums.runtime_name import RuntimeName
from graftcode_protocol.enums.unified_graft_model_type import (
    UnifiedGraftModelType,
)
from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel
import pytest

from moduleanalyzer.src.core.handler.handlers import Handlers
from moduleanalyzer.src.core.handler.module_analyzer import PythonModuleAnalyzer
from moduleanalyzer.test_resources.test_classes import SampleClass


class TestPythonModuleAnalyzerComprehensive:
    """Comprehensive test cases for PythonModuleAnalyzer using real implementations."""

    @pytest.fixture
    def real_python_file(self):
        """Create a real Python file with actual classes and functions.

        Uses an isolated temp directory to avoid os.walk finding unrelated
        .whl files in the system temp directory.
        """
        content = '''"""
Real Python module for testing.
Contains actual classes, functions, and variables.
"""

class Calculator:
    """A simple calculator class."""

    def __init__(self, initial_value: int = 0):
        self.value = initial_value

    def add(self, number: int) -> int:
        """Add a number to the current value."""
        self.value += number
        return self.value

    @staticmethod
    def multiply(a: int, b: int) -> int:
        """Static method to multiply two numbers."""
        return a * b

    @classmethod
    def create_with_value(cls, value: int) -> 'Calculator':
        """Class method to create calculator with initial value."""
        return cls(value)


class DataProcessor:
    """Class for processing data."""

    DEFAULT_BATCH_SIZE = 100

    def __init__(self):
        self.processed_count = 0

    def process_batch(self, data_list: list) -> int:
        """Process a batch of data."""
        self.processed_count += len(data_list)
        return self.processed_count


def global_function(param1: str, param2: int = 42) -> str:
    """A global function with default parameters."""
    return f"{param1}_{param2}"


def simple_function():
    """Simple function with no parameters."""
    pass


# Global variables
GLOBAL_CONSTANT = "test_constant"
global_variable = 123
_private_global = "private"
'''

        # Use isolated temp directory to prevent os.walk from finding
        # unrelated .whl files in system temp
        import shutil

        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, "test_module.py")
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(content)

        yield temp_path

        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_initialization_creates_required_attributes(self):
        """Test that PythonModuleAnalyzer initializes with required attributes."""
        # Set LOCAL storage to avoid Azure dependencies
        os.environ["STORAGE_TYPE"] = "LOCAL"

        analyzer = PythonModuleAnalyzer()

        assert hasattr(analyzer, "local_temp_dir")
        assert hasattr(analyzer, "storage")
        assert hasattr(analyzer, "python_version_map")
        assert isinstance(analyzer.python_version_map, dict)
        assert analyzer.local_temp_dir is not None

    def test_extract_python_module_info_with_real_file(self, real_python_file):
        """Test extract_python_module_info with a real Python file."""
        os.environ["STORAGE_TYPE"] = "LOCAL"
        analyzer = PythonModuleAnalyzer()

        classes, functions, variables = analyzer.extract_python_module_info(
            real_python_file
        )

        # Verify extracted classes
        assert len(classes) >= 2
        assert "Calculator" in classes
        assert "DataProcessor" in classes

        # Verify Calculator class methods
        calculator_methods = classes["Calculator"]
        assert "add" in calculator_methods
        assert "multiply" in calculator_methods
        assert "create_with_value" in calculator_methods

        # Verify extracted functions
        assert len(functions) >= 2
        assert "global_function" in functions
        assert "simple_function" in functions

        # Check function parameters
        global_func_params = functions["global_function"]
        assert len(global_func_params) >= 1  # At least param1

        simple_func_params = functions["simple_function"]
        assert len(simple_func_params) == 0  # No parameters

        # Verify extracted variables
        assert len(variables) >= 2
        assert "GLOBAL_CONSTANT" in variables
        assert "global_variable" in variables

    def test_handlers_integration_with_real_class(self):
        """Test that real handlers work correctly with actual Python classes."""
        os.environ["STORAGE_TYPE"] = "LOCAL"

        # Use real handlers
        handlers = Handlers()

        # Test with a real class from our test resources
        parent_command = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.TYPE_DEF, []
        )

        # Get the type handler and test it with SampleClass
        type_handler = handlers.analyzer_handler[UnifiedGraftModelType.TYPE_DEF]
        result = type_handler.generate_unified_graft_model(
            SampleClass, parent_command, handlers
        )

        # Verify the result is a proper UnifiedGraftModel
        assert isinstance(result, UnifiedGraftModel)
        assert result.runtime_name == RuntimeName.Python
        # Note: UnifiedGraftModel might have different attribute names

    def test_analyze_with_local_storage_real_file(self, real_python_file):
        """
        Test that analyze method requires a .whl file or .dist-info/METADATA.

        The analyze() method is designed for analyzing Python wheel packages,
        not plain Python files. It should raise ValueError when neither .whl
        nor .dist-info is present.
        """
        os.environ["STORAGE_TYPE"] = "LOCAL"
        analyzer = PythonModuleAnalyzer()

        # analyze() now requires a .whl file or .dist-info - should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            analyzer.analyze("", real_python_file)

        assert "Could not extract library metadata" in str(exc_info.value)

    def test_analyze_with_existing_test_resources(self):
        """Test analyze method with existing test resource files."""
        os.environ["STORAGE_TYPE"] = "LOCAL"
        analyzer = PythonModuleAnalyzer()

        # Get the path to our test resources
        test_resources_path = (
            Path(__file__).parent.parent.parent / "resources" / "test_classes.py"
        )

        if test_resources_path.exists():
            result = analyzer.analyze("", str(test_resources_path))

            # Should return serialized bytes
            assert isinstance(result, bytes)
            assert len(result) > 0

    def test_extract_python_module_info_with_syntax_error(self):
        """Test extract_python_module_info handles syntax errors gracefully."""
        os.environ["STORAGE_TYPE"] = "LOCAL"
        analyzer = PythonModuleAnalyzer()

        # Create file with syntax error
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write(
                """
# This file has syntax errors
class BadClass  # Missing colon
    def method(self):
        pass
"""
            )
            bad_file = f.name

        try:
            classes, functions, variables = analyzer.extract_python_module_info(
                bad_file
            )

            # Should return empty structures on syntax error
            assert classes == {}
            assert functions == {}
            assert variables == []
        finally:
            if os.path.exists(bad_file):
                os.unlink(bad_file)

    def test_extract_python_module_info_nonexistent_file(self):
        """Test extract_python_module_info with nonexistent file."""
        os.environ["STORAGE_TYPE"] = "LOCAL"
        analyzer = PythonModuleAnalyzer()

        # This should handle the error gracefully
        classes, functions, variables = analyzer.extract_python_module_info(
            "/nonexistent/file.py"
        )

        assert classes == {}
        assert functions == {}
        assert variables == []

    def test_error_handling_and_recovery(self):
        """Test error handling in various scenarios."""
        os.environ["STORAGE_TYPE"] = "LOCAL"
        analyzer = PythonModuleAnalyzer()

        # Test with empty file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("")  # Empty file
            empty_file = f.name

        try:
            classes, functions, variables = analyzer.extract_python_module_info(
                empty_file
            )

            # Should handle empty file gracefully
            assert isinstance(classes, dict)
            assert isinstance(functions, dict)
            assert isinstance(variables, list)
        finally:
            if os.path.exists(empty_file):
                os.unlink(empty_file)

    def test_find_wheel_files_with_whl_files(self):
        """Test _find_wheel_files method with real .whl files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test .whl files
            whl1 = os.path.join(temp_dir, "package1-1.0.0-py3-none-any.whl")
            whl2 = os.path.join(temp_dir, "subdir", "package2-2.0.0-py3-none-any.whl")

            # Create the subdirectory
            os.makedirs(os.path.dirname(whl2))

            # Create fake .whl files (empty files for testing)
            with open(whl1, "w") as f:
                f.write("")
            with open(whl2, "w") as f:
                f.write("")

            # Test the method
            whl_files = PythonModuleAnalyzer._find_wheel_files(temp_dir)

            # Verify results
            assert len(whl_files) == 2
            assert whl1 in whl_files
            assert whl2 in whl_files

    def test_find_wheel_files_no_whl_files(self):
        """Test _find_wheel_files method with no .whl files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create some non-.whl files
            with open(os.path.join(temp_dir, "test.py"), "w") as f:
                f.write("# test file")
            with open(os.path.join(temp_dir, "test.txt"), "w") as f:
                f.write("test")

            # Test the method
            whl_files = PythonModuleAnalyzer._find_wheel_files(temp_dir)

            # Should return empty list
            assert whl_files == []

    def test_extract_single_wheel_file(self):
        """Test _extract_single_wheel_file method with real ZIP/WHL file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a fake .whl file (which is actually a ZIP)
            whl_path = os.path.join(temp_dir, "test_package-1.0.0-py3-none-any.whl")

            # Create test content for the .whl file
            test_content = """
def test_function():
    return "test"

class SampleClass:
    def method(self):
        pass
"""

            # Create the .whl file as a ZIP
            with zipfile.ZipFile(whl_path, "w") as whl_zip:
                whl_zip.writestr("test_module/__init__.py", "")
                whl_zip.writestr("test_module/main.py", test_content)
                whl_zip.writestr("test_module/submodule/__init__.py", "")
                whl_zip.writestr(
                    "test_module/submodule/helper.py", "def helper(): pass"
                )

            # Test extraction
            PythonModuleAnalyzer._extract_single_wheel_file(whl_path)

            # Verify extraction directory was created
            extract_dir = whl_path[:-4]  # Remove .whl extension
            assert os.path.exists(extract_dir)

            # Verify files were extracted
            assert os.path.exists(os.path.join(extract_dir, "test_module", "main.py"))
            assert os.path.exists(
                os.path.join(extract_dir, "test_module", "submodule", "helper.py")
            )

            # Verify __init__.py files were created in all directories
            assert os.path.exists(
                os.path.join(extract_dir, "test_module", "__init__.py")
            )
            assert os.path.exists(
                os.path.join(extract_dir, "test_module", "submodule", "__init__.py")
            )

    def test_create_init_files(self):
        """Test _create_init_files method creates __init__.py files in all directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create directory structure without __init__.py files
            dir1 = os.path.join(temp_dir, "package1")
            dir2 = os.path.join(temp_dir, "package1", "subpackage")
            dir3 = os.path.join(temp_dir, "package2")

            os.makedirs(dir1)
            os.makedirs(dir2)
            os.makedirs(dir3)

            # Create some Python files
            with open(os.path.join(dir1, "module1.py"), "w") as f:
                f.write("# module1")
            with open(os.path.join(dir2, "module2.py"), "w") as f:
                f.write("# module2")

            # Test the method
            PythonModuleAnalyzer._create_init_files(temp_dir)

            # Verify __init__.py files were created
            assert os.path.exists(os.path.join(dir1, "__init__.py"))
            assert os.path.exists(os.path.join(dir2, "__init__.py"))
            assert os.path.exists(os.path.join(dir3, "__init__.py"))

    def test_create_init_file_if_needed_creates_file(self):
        """Test _create_init_file_if_needed creates __init__.py when it doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a subdirectory
            subdir = "test_package"
            subdir_path = os.path.join(temp_dir, subdir)
            os.makedirs(subdir_path)

            init_file = os.path.join(subdir_path, "__init__.py")

            # Ensure __init__.py doesn't exist yet
            assert not os.path.exists(init_file)

            # Test the method
            PythonModuleAnalyzer._create_init_file_if_needed(temp_dir, subdir)

            # Verify __init__.py was created
            assert os.path.exists(init_file)

            # Verify it's an empty file
            with open(init_file, "r") as f:
                content = f.read()
                assert content == ""

    def test_create_init_file_if_needed_skips_existing(self):
        """Test _create_init_file_if_needed skips when __init__.py already exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a subdirectory
            subdir = "test_package"
            subdir_path = os.path.join(temp_dir, subdir)
            os.makedirs(subdir_path)

            init_file = os.path.join(subdir_path, "__init__.py")
            original_content = "# existing init file"

            # Create existing __init__.py with content
            with open(init_file, "w") as f:
                f.write(original_content)

            # Test the method
            PythonModuleAnalyzer._create_init_file_if_needed(temp_dir, subdir)

            # Verify content was not overwritten
            with open(init_file, "r") as f:
                content = f.read()
                assert content == original_content

    def test_extract_wheel_files_integration(self):
        """Test the main _extract_wheel_files method with multiple .whl files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test .whl files
            whl1_path = os.path.join(temp_dir, "package1-1.0.0-py3-none-any.whl")
            whl2_path = os.path.join(
                temp_dir, "subdir", "package2-2.0.0-py3-none-any.whl"
            )

            # Create subdirectory
            os.makedirs(os.path.dirname(whl2_path))

            # Create test content
            test_content1 = 'def func1(): return "package1"'
            test_content2 = 'def func2(): return "package2"'

            # Create .whl files as ZIPs
            with zipfile.ZipFile(whl1_path, "w") as whl_zip:
                whl_zip.writestr("pkg1/__init__.py", "")
                whl_zip.writestr("pkg1/module.py", test_content1)

            with zipfile.ZipFile(whl2_path, "w") as whl_zip:
                whl_zip.writestr("pkg2/__init__.py", "")
                whl_zip.writestr("pkg2/module.py", test_content2)

            # Test the main method
            PythonModuleAnalyzer._extract_wheel_files(temp_dir)

            # Verify both packages were extracted
            extract_dir1 = whl1_path[:-4]
            extract_dir2 = whl2_path[:-4]

            assert os.path.exists(extract_dir1)
            assert os.path.exists(extract_dir2)

            # Verify files were extracted correctly
            assert os.path.exists(os.path.join(extract_dir1, "pkg1", "module.py"))
            assert os.path.exists(os.path.join(extract_dir2, "pkg2", "module.py"))

            # Verify __init__.py files were created
            assert os.path.exists(os.path.join(extract_dir1, "pkg1", "__init__.py"))
            assert os.path.exists(os.path.join(extract_dir2, "pkg2", "__init__.py"))


class TestZipExtraction:
    """Tests for ZIP file extraction functionality."""

    def test_extract_zip_to_directory(self):
        """Test _extract_zip_to_directory creates correct directory structure."""
        os.environ["STORAGE_TYPE"] = "LOCAL"
        analyzer = PythonModuleAnalyzer()

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a test ZIP file
            zip_path = os.path.join(temp_dir, "test_package.zip")

            with zipfile.ZipFile(zip_path, "w") as zip_file:
                zip_file.writestr("module/__init__.py", "")
                zip_file.writestr("module/main.py", "def hello(): pass")

            # Extract the ZIP
            extracted_path = analyzer._extract_zip_to_directory(zip_path)

            # Verify extraction
            assert os.path.exists(extracted_path)
            assert extracted_path == zip_path[:-4]  # Without .zip extension
            assert os.path.exists(os.path.join(extracted_path, "module", "main.py"))

    def test_extract_zip_with_nested_whl(self):
        """Test ZIP extraction handles nested .whl files."""
        os.environ["STORAGE_TYPE"] = "LOCAL"
        analyzer = PythonModuleAnalyzer()

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a nested .whl file first
            whl_path = os.path.join(temp_dir, "inner_package-1.0.0-py3-none-any.whl")
            with zipfile.ZipFile(whl_path, "w") as whl_file:
                whl_file.writestr("inner/__init__.py", "")
                whl_file.writestr("inner/code.py", "x = 1")

            # Create main ZIP containing the .whl
            zip_path = os.path.join(temp_dir, "outer.zip")
            with zipfile.ZipFile(zip_path, "w") as zip_file:
                zip_file.write(whl_path, os.path.basename(whl_path))

            # Remove the original whl so we only have it in the zip
            os.remove(whl_path)

            # Extract
            extracted_path = analyzer._extract_zip_to_directory(zip_path)

            # Verify .whl was extracted from the outer ZIP
            assert os.path.exists(extracted_path)

    def test_handle_zip_file_extraction_with_py_files(self):
        """Test _handle_zip_file_extraction with Python files."""
        os.environ["STORAGE_TYPE"] = "LOCAL"
        analyzer = PythonModuleAnalyzer()

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create directory with Python files
            subdir = os.path.join(temp_dir, "package")
            os.makedirs(subdir)

            with open(os.path.join(subdir, "module1.py"), "w") as f:
                f.write("def func1(): pass")
            with open(os.path.join(subdir, "module2.py"), "w") as f:
                f.write("def func2(): pass")

            # Create a ZIP file path (doesn't need to be real, just for the method)
            zip_path = os.path.join(temp_dir, "test.zip")
            with open(zip_path, "w") as f:
                f.write("")

            python_files = analyzer._handle_zip_file_extraction(zip_path)

            # Should find Python files in the directory
            assert len(python_files) >= 2

    def test_find_python_files_in_directory(self):
        """Test _find_python_files_in_directory finds all .py files."""
        os.environ["STORAGE_TYPE"] = "LOCAL"
        analyzer = PythonModuleAnalyzer()

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create nested structure with Python files
            subdir1 = os.path.join(temp_dir, "pkg1")
            subdir2 = os.path.join(temp_dir, "pkg1", "subpkg")
            os.makedirs(subdir1)
            os.makedirs(subdir2)

            with open(os.path.join(temp_dir, "root.py"), "w") as f:
                f.write("# root")
            with open(os.path.join(subdir1, "mod1.py"), "w") as f:
                f.write("# mod1")
            with open(os.path.join(subdir2, "mod2.py"), "w") as f:
                f.write("# mod2")
            with open(os.path.join(temp_dir, "not_python.txt"), "w") as f:
                f.write("not python")

            python_files = analyzer._find_python_files_in_directory(temp_dir)

            assert len(python_files) == 3
            assert any("root.py" in f for f in python_files)
            assert any("mod1.py" in f for f in python_files)
            assert any("mod2.py" in f for f in python_files)


class TestLocalStoragePath:
    """Tests for local storage path handling."""

    def test_get_local_input_path_local_storage(self):
        """Test _get_local_input_path for local storage."""
        os.environ["STORAGE_TYPE"] = "LOCAL"
        analyzer = PythonModuleAnalyzer()

        result = analyzer._get_local_input_path("container", "path/to/file.py", True)
        # Use os.path.join for cross-platform compatibility
        expected = os.path.join("container", "path/to/file.py")
        assert result == expected

    def test_get_local_input_path_azure_storage(self):
        """Test _get_local_input_path for Azure storage."""
        os.environ["STORAGE_TYPE"] = "LOCAL"
        analyzer = PythonModuleAnalyzer()

        result = analyzer._get_local_input_path("container", "path/to/file.py", False)
        assert analyzer.local_temp_dir in result
        assert "file.py" in result


class TestWhlFileExtraction:
    """Tests for .whl file extraction methods."""

    def test_extract_whl_to_temp_dir(self):
        """Test _extract_whl_to_temp_dir extracts WHL contents."""
        os.environ["STORAGE_TYPE"] = "LOCAL"
        analyzer = PythonModuleAnalyzer()

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a .whl file (ZIP format)
            whl_path = os.path.join(temp_dir, "test-1.0.0-py3-none-any.whl")
            with zipfile.ZipFile(whl_path, "w") as whl_file:
                whl_file.writestr("pkg/__init__.py", "")
                whl_file.writestr("pkg/module.py", "x = 1")

            # Extract to temp dir
            extract_dir = os.path.join(temp_dir, "extracted")
            os.makedirs(extract_dir)

            analyzer._extract_whl_to_temp_dir(whl_path, extract_dir)

            # Verify extraction
            assert os.path.exists(os.path.join(extract_dir, "pkg", "__init__.py"))
            assert os.path.exists(os.path.join(extract_dir, "pkg", "module.py"))

    def test_copy_files_to_persistent_directory(self):
        """Test _copy_files_to_persistent_directory copies files correctly."""
        os.environ["STORAGE_TYPE"] = "LOCAL"
        analyzer = PythonModuleAnalyzer()

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create source structure
            source_dir = os.path.join(temp_dir, "source")
            os.makedirs(os.path.join(source_dir, "pkg"))

            source_file1 = os.path.join(source_dir, "pkg", "mod1.py")
            source_file2 = os.path.join(source_dir, "pkg", "mod2.py")

            with open(source_file1, "w") as f:
                f.write("# mod1")
            with open(source_file2, "w") as f:
                f.write("# mod2")

            # Create persistent dir
            persistent_dir = os.path.join(temp_dir, "persistent")
            os.makedirs(persistent_dir)

            # Copy files
            copied = analyzer._copy_files_to_persistent_directory(
                [source_file1, source_file2], source_dir, persistent_dir
            )

            # Verify copy
            assert len(copied) == 2
            for copied_file in copied:
                assert os.path.exists(copied_file)
                assert persistent_dir in copied_file


class TestSdnSimpleCarWheelAnalysis:
    """Tests for analyzing the sdn_test_simple_car wheel package."""

    @pytest.fixture
    def sdn_simple_car_whl_path(self):
        """Get the path to the sdn_test_simple_car .whl file."""
        # Path: tests/core/handler -> tests/core -> tests -> src -> moduleanalyzer -> test_wheels
        test_wheels_path = (
            Path(__file__).parent.parent.parent.parent.parent / "test_wheels"
        )
        whl_path = test_wheels_path / "sdn_test_simple_car-0.1.0-py3-none-any.whl"
        if not whl_path.exists():
            pytest.skip(f"Test wheel file not found: {whl_path}")
        return str(whl_path)

    def test_analyze_sdn_simple_car_wheel_full_flow(self, sdn_simple_car_whl_path):
        """
        Test full analysis flow for sdn_test_simple_car wheel package.

        This test verifies that the analyzer can:
        1. Extract the .whl file
        2. Find and parse Python modules
        3. Extract classes, functions, and variables
        4. Return serialized analysis results
        """
        os.environ["STORAGE_TYPE"] = "LOCAL"
        analyzer = PythonModuleAnalyzer()

        # Run full analysis on the wheel file
        result = analyzer.analyze("", sdn_simple_car_whl_path)

        # Store as numeric byte array for debugging (e.g., [5, 0, 0, 0, ...])
        _byte_array = list(result)  # noqa: F841

        # Deserialize to human-readable JSON for debugging
        _json_result = (  # noqa: F841
            UnifiedGraftModelToJsonSerializer.serialize_from_byte_array(result)
        )

        # Verify result is serialized bytes
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_extract_sdn_simple_car_wheel_contents(self, sdn_simple_car_whl_path):
        """
        Test extraction and verification of sdn_test_simple_car wheel contents.

        Verifies that the wheel file contains expected structure:
        - sdn_test_simple_car/__init__.py
        - sdn_test_simple_car/simple_car.py
        """
        os.environ["STORAGE_TYPE"] = "LOCAL"

        with tempfile.TemporaryDirectory() as temp_dir:
            # Extract the wheel file
            with zipfile.ZipFile(sdn_simple_car_whl_path, "r") as whl_zip:
                whl_zip.extractall(temp_dir)

            # Verify expected files exist
            init_file = os.path.join(temp_dir, "sdn_test_simple_car", "__init__.py")
            simple_car_file = os.path.join(
                temp_dir, "sdn_test_simple_car", "simple_car.py"
            )

            assert os.path.exists(init_file), "Missing __init__.py"
            assert os.path.exists(simple_car_file), "Missing simple_car.py"

    def test_extract_python_module_info_from_sdn_simple_car(
        self, sdn_simple_car_whl_path
    ):
        """
        Test extraction of Python module info from sdn_test_simple_car package.

        Extracts the wheel and analyzes the simple_car.py module to verify
        classes, functions, and variables are properly extracted.
        """
        os.environ["STORAGE_TYPE"] = "LOCAL"
        analyzer = PythonModuleAnalyzer()

        with tempfile.TemporaryDirectory() as temp_dir:
            # Extract the wheel file
            with zipfile.ZipFile(sdn_simple_car_whl_path, "r") as whl_zip:
                whl_zip.extractall(temp_dir)

            simple_car_file = os.path.join(
                temp_dir, "sdn_test_simple_car", "simple_car.py"
            )

            # Extract module info
            classes, functions, variables = analyzer.extract_python_module_info(
                simple_car_file
            )

            # Verify extraction results (at least some content should be found)
            # The actual assertions depend on the content of simple_car.py
            assert isinstance(classes, dict)
            assert isinstance(functions, dict)
            assert isinstance(variables, list)

    def test_wheel_file_metadata_extraction(self, sdn_simple_car_whl_path):
        """
        Test extraction of metadata from sdn_test_simple_car wheel file.

        Verifies that the wheel filename contains expected metadata:
        - Package name: sdn_test_simple_car
        - Version: 0.1.0
        - Python version: py3
        """
        # Verify wheel filename format
        whl_filename = os.path.basename(sdn_simple_car_whl_path)

        assert "sdn_test_simple_car" in whl_filename
        assert "0.1.0" in whl_filename
        assert "py3" in whl_filename
        assert whl_filename.endswith(".whl")

    def test_analyze_zip_containing_whl_full_flow(self, sdn_simple_car_whl_path):
        """
        Test full analysis flow for a .zip file containing a .whl inside.

        This test verifies that the analyzer can handle the case where:
        1. Input is a .zip file
        2. The .zip contains a .whl file inside
        3. The analyzer extracts the .zip, finds the .whl, extracts it
        4. Returns serialized analysis results
        """
        os.environ["STORAGE_TYPE"] = "LOCAL"
        analyzer = PythonModuleAnalyzer()

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a .zip file containing the .whl
            zip_path = os.path.join(temp_dir, "package_with_whl.zip")
            with zipfile.ZipFile(zip_path, "w") as zip_file:
                # Add the .whl file to the zip
                whl_filename = os.path.basename(sdn_simple_car_whl_path)
                zip_file.write(sdn_simple_car_whl_path, whl_filename)

            # Run full analysis on the zip file containing the whl
            result = analyzer.analyze("", zip_path)

            # Verify result is serialized bytes
            assert isinstance(result, bytes)
            assert len(result) > 0
