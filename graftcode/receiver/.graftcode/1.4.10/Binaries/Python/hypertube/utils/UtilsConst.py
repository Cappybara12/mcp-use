import os
from pathlib import Path

class UtilsConst:
    _working_directory = str(Path().absolute()) + "/"
    _config_source = ""
    _license_key = "License key not set"

    @staticmethod
    def set_working_directory(path: str) -> None:
        path = path.replace("\\", "/")
        if not path.endswith("/"):
            path = path + "/"

        if not os.path.exists(path):
            os.makedirs(path)
            os.chmod(path, 0o700)

        UtilsConst._working_directory = path

    @staticmethod
    def get_working_directory() -> str:
        return UtilsConst._working_directory

    @staticmethod
    def set_config_source(value: str) -> None:
        UtilsConst._config_source = value

    @staticmethod
    def get_config_source() -> str:
        return UtilsConst._config_source

    @staticmethod
    def set_license_key(value: str) -> None:
        if not value or value == "" or value == "your-license-key":
            return

        UtilsConst._license_key = value

    @staticmethod
    def get_license_key() -> str:
        return UtilsConst._license_key