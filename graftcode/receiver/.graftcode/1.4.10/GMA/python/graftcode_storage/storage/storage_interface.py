from abc import ABC, abstractmethod


class StorageInterface(ABC):
    """
    StorageInterface defines the operations for blob storage implementations.
    Implementations should support uploading, downloading, deleting blobs,
    and checking their existence.
    """

    @abstractmethod
    def upload_blob(self, source_file_path: str, storage_container_name: str, storage_blob_path: str) -> str:
        """
        Uploads a local file to the storage as a blob.

        :param source_file_path: Path to the local source file.
        :param storage_container_name: Name of the storage container.
        :param storage_blob_path: Target blob path in the storage.
        :return: The storage path of the uploaded blob.
        :raises ValueError: If source_file_path, storage_container_name, or storage_blob_path is null, empty, or whitespace.
        :raises OSError: If the local file cannot be read or the blob cannot be written.
        :raises Exception: Storage-specific errors such as network or authentication failures.
        """
        ...

    @abstractmethod
    def download_blob(self, destination_path: str, storage_container_name: str, storage_blob_path: str) -> None:
        """
        Downloads a blob from the storage to a local file.

        :param destination_path: Local file path where the blob will be saved.
        :param storage_container_name: Name of the storage container.
        :param storage_blob_path: Blob path in the storage.
        :raises ValueError: If destination_path, storage_container_name, or storage_blob_path is null, empty, or whitespace.
        :raises FileNotFoundError: If the source blob does not exist locally or remotely.
        :raises OSError: If the blob cannot be read or the local file cannot be written.
        :raises Exception: Storage-specific errors such as network or authentication failures.
        """
        ...

    @abstractmethod
    def delete_blob(self, storage_container_name: str, storage_blob_path: str) -> None:
        """
        Deletes a blob from the storage.

        :param storage_container_name: Name of the storage container.
        :param storage_blob_path: Blob path in the storage to delete.
        :raises ValueError: If storage_container_name or storage_blob_path is null, empty, or whitespace.
        :raises Exception: Storage-specific errors such as network or authentication failures.
        """
        ...

    @abstractmethod
    def blob_exists(self, storage_container_name: str, storage_blob_path: str) -> bool:
        """
        Checks whether a blob exists in the storage.

        :param storage_container_name: Name of the storage container.
        :param storage_blob_path: Blob path in the storage.
        :return: True if the blob exists, False otherwise.
        :raises ValueError: If storage_container_name or storage_blob_path is null, empty, or whitespace.
        :raises Exception: Storage-specific errors such as network or authentication failures.
        """
        ...
