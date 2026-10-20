import os
from azure.core.exceptions import ResourceNotFoundError, AzureError
from azure.storage.blob import BlobServiceClient
from graftcode_storage.storage.storage_interface import StorageInterface
from graftcode_storage.utils.validation import throw_if_null_or_empty_or_whitespace

class AzureBlobStorage(StorageInterface):
    """
    AzureBlobStorage provides an implementation of StorageInterface using
    Azure Blob Storage service. It supports uploading, downloading,
    deleting blobs, and checking their existence in an Azure Storage account.
    """
    
    def __init__(
            self, 
            azure_storage_url: str,
            azure_storage_token: str
        ):
        """
        Initializes AzureBlobStorage with connection details.

        :param azure_storage_url: URL of the Azure Blob service endpoint.
        :param azure_storage_token: Authentication token or credential.
        :raises ValueError: If any parameter is null, empty, or whitespace.
        :raises AzureError: If client initialization fails.
        """
        throw_if_null_or_empty_or_whitespace(azure_storage_url, "azure_storage_url")
        throw_if_null_or_empty_or_whitespace(azure_storage_token, "azure_storage_token")
        
        try:
            self._blob_service_client = BlobServiceClient(
            account_url=azure_storage_url,
            credential=azure_storage_token
        )
        except AzureError as e:
            raise AzureError(
                f"Failed to create BlobServiceClient for {azure_storage_url}"
            ) from e

    def upload_blob(self, source_file_path: str, storage_container_name: str, storage_blob_path: str) -> str:
        """
        Uploads a local file to Azure Blob Storage.

        :param source_file_path: Path to the local source file.
        :param storage_container_name: Name of the Azure storage container.
        :param storage_blob_path: Target blob path in Azure Storage.
        :return: The storage path of the uploaded blob.
        :raises ValueError: If parameters are null, empty, or whitespace.
        :raises OSError: If source file is not found locally.
        :raises ResourceNotFoundError: If specified container does not exist.
        :raises AzureError: For upload failures or authentication errors.
        """
        throw_if_null_or_empty_or_whitespace(source_file_path, "source_file_path")
        throw_if_null_or_empty_or_whitespace(storage_container_name, "storage_container_name")
        throw_if_null_or_empty_or_whitespace(storage_blob_path, "storage_blob_path")
        if not os.path.exists(source_file_path):
            raise OSError(f"File not found {source_file_path}")
        
        try:
            container_client = self._blob_service_client.get_container_client(
                storage_container_name
            )
            blob_client = container_client.get_blob_client(storage_blob_path)

            with open(source_file_path, "rb") as data:
                blob_client.upload_blob(data, overwrite=True)
        except ResourceNotFoundError as e:
            raise ResourceNotFoundError(
                f"Blob not found - container:{storage_container_name} - path:{storage_blob_path}"
            ) from e
        except AzureError as e:
            raise AzureError(
                f"Failed to upload blob - container:{storage_container_name} - path:{storage_blob_path}"
            ) from e
            
        return storage_blob_path

    def download_blob(self, destination_path: str, storage_container_name: str, storage_blob_path: str) -> None:
        """
        Downloads a blob from Azure Storage to a local file.

        :param destination_path: Local file path to write the downloaded blob.
        :param storage_container_name: Name of the Azure storage container.
        :param storage_blob_path: Source blob path in Azure Storage.
        :raises ValueError: If parameters are null, empty, or whitespace.
        :raises ResourceNotFoundError: If the blob does not exist.
        :raises AzureError: For download failures or authentication errors.
        :raises OSError: If local write operation fails.
        """
        throw_if_null_or_empty_or_whitespace(destination_path, "destination_path")
        throw_if_null_or_empty_or_whitespace(storage_container_name, "storage_container_name")
        throw_if_null_or_empty_or_whitespace(storage_blob_path, "storage_blob_path")
        
        try:
            container_client = self._blob_service_client.get_container_client(
                storage_container_name
            )
            blob_client = container_client.get_blob_client(storage_blob_path)
            os.makedirs(os.path.dirname(destination_path), exist_ok=True)
            stream = blob_client.download_blob()
            with open(destination_path, "wb") as file:
                file.write(stream.readall())
        except ResourceNotFoundError as e:
            raise ResourceNotFoundError(
                f"Blob not found - container:{storage_container_name} - path:{storage_blob_path}"
            ) from e
        except AzureError as e:
            raise AzureError(
                f"Failed to download blob - container:{storage_container_name} - path:{storage_blob_path}"
            ) from e

    def delete_blob(self, storage_container_name: str, storage_blob_path: str) -> None:
        """
        Deletes a blob from Azure Storage.

        :param storage_container_name: Name of the Azure storage container.
        :param storage_blob_path: Path of the blob to delete.
        :raises ValueError: If storage_container_name or storage_blob_path is null, empty, or whitespace.
        :raises AzureError: For deletion failures or authentication errors.
        """
        throw_if_null_or_empty_or_whitespace(storage_container_name, "storage_container_name")
        throw_if_null_or_empty_or_whitespace(storage_blob_path, "storage_blob_path")
        
        try:
            container_client = self._blob_service_client.get_container_client(
                storage_container_name
            )
            blob_client = container_client.get_blob_client(storage_blob_path)
            blob_client.delete_blob()
        except ResourceNotFoundError:
            pass
        except AzureError as e:
            raise AzureError(
                f"Failed to delete blob - container:{storage_container_name} - path:{storage_blob_path}"
            ) from e

    def blob_exists(self, storage_container_name: str, storage_blob_path: str) -> bool:
        """
        Checks if a blob exists in Azure Storage.

        :param storage_container_name: Name of the Azure storage container.
        :param storage_blob_path: Path to check existence.
        :return: True if the blob exists, False otherwise.
        :raises ValueError: If storage_container_name or storage_blob_path is null, empty, or whitespace.
        :raises AzureError: For existence check failures or authentication errors.
        """
        throw_if_null_or_empty_or_whitespace(storage_container_name, "storage_container_name")
        throw_if_null_or_empty_or_whitespace(storage_blob_path, "storage_blob_path")
        
        try:
            container_client = self._blob_service_client.get_container_client(
                storage_container_name
            )
            blob_client = container_client.get_blob_client(storage_blob_path)
        except AzureError as e:
            raise AzureError(
                f"Failed to check blob existence - container:{storage_container_name} - path:{storage_blob_path}"
            ) from e
        return blob_client.exists()
