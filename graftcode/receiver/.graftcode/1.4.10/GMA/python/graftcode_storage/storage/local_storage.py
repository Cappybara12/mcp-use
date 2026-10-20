import os
import shutil
import tempfile
from graftcode_storage.storage.storage_interface import StorageInterface
from graftcode_storage.utils.validation import throw_if_null_or_empty_or_whitespace


class LocalStorage(StorageInterface):
    """
    LocalStorage provides a filesystem-based implementation of StorageInterface.
    It stores blobs in a temporary directory on the local machine.
    """
    
    STORAGE_DIR_NAME = "graftcode.local.storage"

    def __init__(self):
        """
        Initializes LocalStorage with a base temporary directory.
        """
        self._base_directory = os.path.join(
            tempfile.gettempdir(),
            self.STORAGE_DIR_NAME
        )

    def upload_blob(self, source_file_path: str, storage_container_name: str, storage_blob_path: str) -> str:
        """
        Copies a local file into the local storage directory.

        :param source_file_path: Path to the local source file.
        :param storage_container_name: Virtual container name under local storage.
        :param storage_blob_path: Virtual blob path under local storage.
        :return: The storage blob path of the stored blob.
        :raises ValueError: If parameters are null, empty, or whitespace.
        :raises FileNotFoundError: If source file is not found locally.
        :raises OSError: If write operation fails.
        """
        throw_if_null_or_empty_or_whitespace(source_file_path, "source_file_path")
        throw_if_null_or_empty_or_whitespace(storage_container_name, "storage_container_name")
        throw_if_null_or_empty_or_whitespace(storage_blob_path, "storage_blob_path")

        local_blob_path = self._generate_local_blob_path(storage_container_name, storage_blob_path)
        
        try:
            os.makedirs(os.path.dirname(local_blob_path), exist_ok=True)
            shutil.copy2(source_file_path, local_blob_path)
        except FileNotFoundError as e:
            raise FileNotFoundError(
                f"Source file not found – {source_file_path}"
            ) from e
        except OSError as e:
            raise OSError(
                f"Failed to write local blob – {local_blob_path}"
            ) from e

        return storage_blob_path

    def download_blob(self, destination_path: str, storage_container_name: str, storage_blob_path: str) -> None:
        """
        Copies a blob from local storage directory to a given destination.

        :param destination_path: Local file path to copy the blob to.
        :param storage_container_name: Virtual container name under local storage.
        :param storage_blob_path: Virtual blob path under local storage.
        :raises ValueError: If parameters are null, empty, or whitespace.
        :raises FileNotFoundError: If the blob does not exist in local storage.
        :raises OSError: If write operation fails.
        """
        throw_if_null_or_empty_or_whitespace(destination_path, "destination_path")
        throw_if_null_or_empty_or_whitespace(storage_container_name, "storage_container_name")
        throw_if_null_or_empty_or_whitespace(storage_blob_path, "storage_blob_path")

        local_blob_path = self._generate_local_blob_path(storage_container_name, storage_blob_path)
        
        try:
            os.makedirs(os.path.dirname(destination_path), exist_ok=True)
            shutil.copy2(local_blob_path, destination_path)
        except FileNotFoundError as e:
            raise FileNotFoundError(
                f"Source file not found – {local_blob_path}"
            ) from e
        except OSError as e:
            raise OSError(
                f"Failed to write local blob – {destination_path}"
            ) from e

    def delete_blob(self, storage_container_name: str, storage_blob_path: str) -> None:
        """
        Deletes a blob from the local storage directory.

        :param storage_container_name: Virtual container name under local storage.
        :param storage_blob_path: Virtual blob path of the blob.
        :raises ValueError: If storage_container_name or storage_blob_path is null, empty, or whitespace.
        """
        throw_if_null_or_empty_or_whitespace(storage_container_name, "storage_container_name")
        throw_if_null_or_empty_or_whitespace(storage_blob_path, "storage_blob_path")

        local_blob_path = self._generate_local_blob_path(storage_container_name, storage_blob_path)
        
        try:
            if os.path.exists(local_blob_path):
                os.remove(local_blob_path)
        except OSError:
            pass

    def blob_exists(self, storage_container_name: str, storage_blob_path: str) -> bool:
        """
        Checks if a blob exists in local storage directory.

        :param storage_container_name: Virtual container name under local storage.
        :param storage_blob_path: Virtual blob path to check.
        :return: True if the file exists locally, False otherwise.
        :raises ValueError: If storage_container_name or storage_blob_path is null, empty, or whitespace.
        :raises OSError: If filesystem check fails.
        """
        throw_if_null_or_empty_or_whitespace(storage_container_name, "storage_container_name")
        throw_if_null_or_empty_or_whitespace(storage_blob_path, "storage_blob_path")

        local_blob_path = self._generate_local_blob_path(storage_container_name, storage_blob_path)
    
        try:
            return os.path.exists(local_blob_path)
        except OSError as e:
            raise OSError(
                f"Failed to check local blob existence – {local_blob_path}"
            ) from e

    def _generate_local_blob_path(self, storage_container_name: str, storage_blob_path: str) -> str:
        """
        Constructs the full local filesystem path for a given virtual blob path.

        :param storage_container_name: Virtual container name under local storage.
        :param storage_blob_path: Virtual blob path under local storage.
        :return: Full filesystem path in the base directory.
        :raises ValueError: If storage_container_name or storage_blob_path is null, empty, or whitespace.
        """
        throw_if_null_or_empty_or_whitespace(storage_container_name, "storage_container_name")
        throw_if_null_or_empty_or_whitespace(storage_blob_path, "storage_blob_path")
        return os.path.join(
            self._base_directory,
            storage_container_name,
            storage_blob_path
        )
