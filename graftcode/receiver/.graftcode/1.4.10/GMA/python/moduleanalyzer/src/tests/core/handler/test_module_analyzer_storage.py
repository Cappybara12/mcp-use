"""
Tests for PythonModuleAnalyzer storage logic.

This module tests the STORAGE_TYPE=LOCAL vs AZURE behavior to ensure
download_blob is not called when using local storage.
"""

import os
import shutil
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from moduleanalyzer.src.core.handler.module_analyzer import PythonModuleAnalyzer


class StorageWithDownload:
    """Test storage class with download_blob method for AZURE simulation."""

    def __init__(self):
        self.download_blob_called = False
        self.download_blob_call_count = 0
        self.download_blob_args = None

    def download_blob(self, local_path, container_name, blob_name):
        """Mock download_blob method."""
        self.download_blob_called = True
        self.download_blob_call_count += 1
        self.download_blob_args = (local_path, container_name, blob_name)

    def reset_mock(self):
        """Reset tracking variables."""
        self.download_blob_called = False
        self.download_blob_call_count = 0
        self.download_blob_args = None


@pytest.fixture
def mock_storage():
    """Create a test storage instance with download_blob method."""
    return StorageWithDownload()


@pytest.fixture
def mock_storage_client(mock_storage):
    """Mock StorageClient that returns our test storage."""
    with patch(
        "moduleanalyzer.src.core.handler.module_analyzer.StorageClient"
    ) as mock_client:
        mock_client.return_value.get_storage.return_value = mock_storage
        yield mock_client, mock_storage


@pytest.fixture
def temp_test_file():
    """Create a temporary test Python file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(
            """
class TestClass:
    def test_method(self):
        return "test"

def global_function():
    return "global"

global_variable = "test_value"
"""
        )
        temp_path = f.name

    yield temp_path

    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def temp_directory_with_file():
    """Create a temporary directory with a test Python file."""
    temp_dir = tempfile.mkdtemp()
    test_file_path = os.path.join(temp_dir, "test_module.py")

    with open(test_file_path, "w") as f:
        f.write(
            """
class TestClass:
    def test_method(self):
        return "test"

def global_function():
    return "global"

global_variable = "test_value"
"""
        )

    yield temp_dir, "test_module.py"

    # Cleanup
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


def test_local_storage_absolute_path_no_download(mock_storage_client, temp_test_file):
    """
    Test LOCAL storage with absolute path - no download_blob call.
    """
    mock_client, mock_storage = mock_storage_client

    with patch.dict(os.environ, {"STORAGE_TYPE": "LOCAL"}):
        analyzer = PythonModuleAnalyzer()

        # Use absolute path - analyzer should process without calling download_blob
        try:
            analyzer.analyze("dummy_container", temp_test_file)
        except Exception:
            # We might get errors from analysis, but that's ok
            pass

        # Verify download_blob was NOT called
        assert not mock_storage.download_blob_called
        assert mock_storage.download_blob_call_count == 0


def test_local_storage_relative_path_no_download(
    mock_storage_client, temp_directory_with_file
):
    """
    Test LOCAL storage with relative path - no download_blob call.
    """
    mock_client, mock_storage = mock_storage_client
    temp_dir, filename = temp_directory_with_file

    with patch.dict(os.environ, {"STORAGE_TYPE": "LOCAL"}):
        analyzer = PythonModuleAnalyzer()

        # Replace library_analyzer with a mock after instantiation
        mock_lib = MagicMock()
        mock_lib._create_base_structured_command.return_value = MagicMock()
        mock_lib._perform_analysis.return_value = MagicMock()
        mock_lib._serialize_result.return_value = b"test_serialized_data"
        analyzer.library_analyzer = mock_lib

        # Use relative path
        analyzer.analyze(temp_dir, filename)

        # Verify download_blob was NOT called
        assert not mock_storage.download_blob_called
        assert mock_storage.download_blob_call_count == 0


def test_azure_storage_download_is_called(mock_storage_client, temp_test_file):
    """
    Test AZURE storage - download_blob IS called.
    """
    mock_client, mock_storage = mock_storage_client

    with patch.dict(os.environ, {"STORAGE_TYPE": "AZURE"}):
        analyzer = PythonModuleAnalyzer()

        # Replace library_analyzer with a mock after instantiation
        mock_lib = MagicMock()
        mock_lib._create_base_structured_command.return_value = MagicMock()
        mock_lib._perform_analysis.return_value = MagicMock()
        mock_lib._serialize_result.return_value = b"test_serialized_data"
        analyzer.library_analyzer = mock_lib

        analyzer.analyze("test_container", "test_file.py")

        # Verify download_blob WAS called
        assert mock_storage.download_blob_called
        assert mock_storage.download_blob_call_count == 1

        # Verify the call arguments (order: local_path, container_name, blob_name)
        assert analyzer.local_temp_dir in mock_storage.download_blob_args[0]
        assert mock_storage.download_blob_args[1] == "test_container"
        assert mock_storage.download_blob_args[2] == "test_file.py"


def test_default_storage_type_is_azure(mock_storage_client):
    """
    Test that when STORAGE_TYPE is not set, defaults to AZURE.
    """
    mock_client, mock_storage = mock_storage_client

    # Ensure STORAGE_TYPE is not set
    env_copy = os.environ.copy()
    if "STORAGE_TYPE" in env_copy:
        del env_copy["STORAGE_TYPE"]

    with patch.dict(os.environ, env_copy, clear=True):
        analyzer = PythonModuleAnalyzer()

        # Replace library_analyzer with a mock after instantiation
        mock_lib = MagicMock()
        mock_lib._create_base_structured_command.return_value = MagicMock()
        mock_lib._perform_analysis.return_value = MagicMock()
        mock_lib._serialize_result.return_value = b"test_serialized_data"
        analyzer.library_analyzer = mock_lib

        analyzer.analyze("test_container", "test_file.py")

        # Verify download_blob WAS called (default AZURE behavior)
        assert mock_storage.download_blob_called
        assert mock_storage.download_blob_call_count == 1


def test_local_storage_file_not_found_raises_error(mock_storage_client):
    """
    Test LOCAL storage with nonexistent file raises FileNotFoundError.
    """
    mock_client, mock_storage = mock_storage_client

    with patch.dict(os.environ, {"STORAGE_TYPE": "LOCAL"}):
        analyzer = PythonModuleAnalyzer()

        with pytest.raises(FileNotFoundError, match="Local file not found"):
            analyzer.analyze("dummy_container", "nonexistent_file.py")

        # Verify download_blob was NOT called
        assert not mock_storage.download_blob_called


def test_storage_type_case_insensitive(mock_storage_client):
    """
    Test that STORAGE_TYPE is case insensitive.
    """
    mock_client, mock_storage = mock_storage_client
    test_cases = ["local", "LOCAL", "Local", "LocAL"]

    for storage_type in test_cases:
        with patch.dict(os.environ, {"STORAGE_TYPE": storage_type}), patch(
            "os.path.exists", return_value=True
        ):
            analyzer = PythonModuleAnalyzer()

            # Replace library_analyzer with a mock after instantiation
            mock_lib = MagicMock()
            mock_lib._create_base_structured_command.return_value = MagicMock()
            mock_lib._perform_analysis.return_value = MagicMock()
            mock_lib._serialize_result.return_value = b"test_serialized_data"
            analyzer.library_analyzer = mock_lib

            analyzer.analyze("dummy_container", "test_file.py")

            # Verify download_blob was NOT called
            assert not mock_storage.download_blob_called

            # Reset mock for next iteration
            mock_storage.reset_mock()
