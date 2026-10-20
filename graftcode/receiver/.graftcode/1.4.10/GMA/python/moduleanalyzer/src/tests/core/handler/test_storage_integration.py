"""
Simple integration tests for PythonModuleAnalyzer storage behavior.
"""

import os
import tempfile
from unittest.mock import patch

import pytest

from moduleanalyzer.src.core.handler.module_analyzer import PythonModuleAnalyzer


class StorageWithDownload:
    """Storage class that tracks download_blob calls."""

    def __init__(self):
        self.download_blob_called = False
        self.download_blob_call_count = 0

    def download_blob(self, local_path, container_name, blob_name):
        """Track download_blob method calls."""
        self.download_blob_called = True
        self.download_blob_call_count += 1


def test_local_storage_no_download_call():
    """
    Core test: LOCAL storage should never call download_blob.
    """
    # Create a real test file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write('def test_func(): return "test"')
        test_file = f.name

    try:
        # Create test storage to track download_blob calls
        storage = StorageWithDownload()

        with patch.dict(os.environ, {"STORAGE_TYPE": "LOCAL"}), patch(
            "moduleanalyzer.src.core.handler.module_analyzer.StorageClient"
        ) as mock_client:

            mock_client.return_value.get_storage.return_value = storage

            analyzer = PythonModuleAnalyzer()

            # This should work without calling download_blob
            try:
                analyzer.analyze("dummy", test_file)
            except Exception:
                # We expect other errors (missing deps), but not
                # AttributeError about download_blob
                pass

            # The key assertion: download_blob should never be called
            assert not storage.download_blob_called
            assert storage.download_blob_call_count == 0

    finally:
        # Cleanup
        if os.path.exists(test_file):
            os.unlink(test_file)


def test_azure_storage_calls_download():
    """
    Verification test: AZURE storage should call download_blob.
    """
    storage = StorageWithDownload()

    with patch.dict(os.environ, {"STORAGE_TYPE": "AZURE"}), patch(
        "moduleanalyzer.src.core.handler.module_analyzer.StorageClient"
    ) as mock_client:

        mock_client.return_value.get_storage.return_value = storage

        analyzer = PythonModuleAnalyzer()

        try:
            analyzer.analyze("test_container", "test_file.py")
        except Exception:
            # We expect errors, but download_blob should be called first
            pass

        # The key assertion: download_blob should be called for AZURE
        assert storage.download_blob_called
        assert storage.download_blob_call_count == 1


def test_local_storage_file_not_found():
    """
    Test that LOCAL storage with nonexistent file raises FileNotFoundError.
    """
    storage = StorageWithDownload()

    with patch.dict(os.environ, {"STORAGE_TYPE": "LOCAL"}), patch(
        "moduleanalyzer.src.core.handler.module_analyzer.StorageClient"
    ) as mock_client:

        mock_client.return_value.get_storage.return_value = storage

        analyzer = PythonModuleAnalyzer()

        # Should raise FileNotFoundError, not AttributeError
        with pytest.raises(FileNotFoundError):
            analyzer.analyze("dummy", "nonexistent_file.py")

        # download_blob should never be called
        assert not storage.download_blob_called
        assert storage.download_blob_call_count == 0
