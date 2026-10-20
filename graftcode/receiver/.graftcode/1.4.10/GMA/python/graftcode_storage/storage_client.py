from graftcode_storage.factory.storage_factory import StorageFactory
from graftcode_storage.storage.storage_interface import StorageInterface


class StorageClient:
    def __init__(self) -> None:
        storage_factory = StorageFactory()
        self.storage = storage_factory.create_storage()

    def get_storage(self) -> StorageInterface:
        return self.storage
