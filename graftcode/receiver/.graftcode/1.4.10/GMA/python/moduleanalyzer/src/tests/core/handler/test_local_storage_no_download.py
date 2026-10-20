"""
Regression test for storage bug fix.

Tests that STORAGE_TYPE=LOCAL does not call download_blob method,
which was causing AttributeError.
"""

import os
import tempfile
from unittest.mock import patch

import pytest

from moduleanalyzer.src.core.handler.module_analyzer import PythonModuleAnalyzer


def test_local_storage_no_download_blob_attribute_error():
    """
    Regression test: LOCAL storage should not cause AttributeError
    about missing download_blob method.
    """
    # Create test file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("def test(): pass")
        test_file = f.name

    try:
        # Create a storage object without download_blob method
        class LocalStorageWithoutDownload:
            """Simulates local storage that doesn't have download_blob method."""

            pass

        local_storage = LocalStorageWithoutDownload()

        with patch.dict(os.environ, {"STORAGE_TYPE": "LOCAL"}):
            with patch(
                "moduleanalyzer.src.core.handler.module_analyzer.StorageClient"
            ) as mock_client:
                mock_client.return_value.get_storage.return_value = local_storage

                analyzer = PythonModuleAnalyzer()

                # This should NOT raise AttributeError about download_blob
                try:
                    analyzer.analyze("dummy", test_file)
                except AttributeError as e:
                    if "download_blob" in str(e):
                        pytest.fail(f"Bug not fixed! Still calling: {e}")
                except Exception:
                    # Other exceptions are OK (e.g., analysis errors)
                    pass

    finally:
        if os.path.exists(test_file):
            os.unlink(test_file)


def test_azure_storage_calls_download_blob():
    """Verify AZURE storage still works (calls download_blob)."""

    class AzureStorageWithDownload:
        """Simulates Azure storage with download_blob method."""

        def __init__(self):
            self.download_blob_called = False
            self.download_blob_args = None

        def download_blob(self, local_path, container_name, blob_name):
            """Mock download_blob method."""
            self.download_blob_called = True
            self.download_blob_args = (local_path, container_name, blob_name)

    azure_storage = AzureStorageWithDownload()

    with patch.dict(os.environ, {"STORAGE_TYPE": "AZURE"}):
        with patch(
            "moduleanalyzer.src.core.handler.module_analyzer.StorageClient"
        ) as mock_client:
            mock_client.return_value.get_storage.return_value = azure_storage

            analyzer = PythonModuleAnalyzer()

            try:
                analyzer.analyze("container", "file.py")
            except Exception:
                # Expected to fail since file doesn't exist, but we just want to verify download_blob was called
                pass

            # Verify download_blob was called for AZURE
            assert (
                azure_storage.download_blob_called
            ), "download_blob should be called for AZURE storage"
            expected_path = os.path.join(analyzer.local_temp_dir, "file.py")
            assert azure_storage.download_blob_args == (
                expected_path,
                "container",
                "file.py",
            )
