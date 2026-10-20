import os

from graftcode_storage.utils.consts import (
    AZURE_STORAGE_TOKEN,
    AZURE_STORAGE_URL,
    DEFAULT_STORAGE_TYPE,
    STORAGE_TYPE_KEY,
)

class EnvironmentConfig:
    @staticmethod
    def get_storage_type() -> str:
        storage_type = os.getenv(STORAGE_TYPE_KEY)
        if not storage_type or not storage_type.strip():
            return DEFAULT_STORAGE_TYPE
        return storage_type

    @staticmethod
    def get_azure_storage_url() -> str:
        return EnvironmentConfig._get_value_for_key_or_throw(
            AZURE_STORAGE_URL
        )

    @staticmethod
    def get_azure_storage_token() -> str:
        return EnvironmentConfig._get_value_for_key_or_throw(
            AZURE_STORAGE_TOKEN
        )

    @staticmethod
    def _get_value_for_key_or_throw(key: str) -> str:
        value = os.getenv(key)
        if not value:
            raise ValueError(f"{key} environment variable is not set")
        return value
