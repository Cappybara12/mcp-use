from graftcode_storage.config.environment_config import EnvironmentConfig
from graftcode_storage.storage.azure_blob_storage import AzureBlobStorage
from graftcode_storage.storage.local_storage import LocalStorage
from graftcode_storage.storage.storage_interface import StorageInterface
from graftcode_storage.utils.consts import AZURE, LOCAL


class StorageFactory:
    def create_storage(self) -> StorageInterface:
        storage_type_str = EnvironmentConfig.get_storage_type()

        if storage_type_str.upper() == AZURE:
            azure_storage_url = EnvironmentConfig.get_azure_storage_url()
            azure_storage_token = EnvironmentConfig.get_azure_storage_token()
            return AzureBlobStorage(azure_storage_url, azure_storage_token)
        elif storage_type_str.upper() == LOCAL:
            return LocalStorage()
        else:
            raise ValueError(f"Unsupported storage type: {storage_type_str}")
