from abc import ABC, abstractmethod

from graftcode_storage.storage.storage_interface import StorageInterface


class StorageFactoryInterface(ABC):

    @abstractmethod
    def create_storage(self) -> StorageInterface:
        pass
