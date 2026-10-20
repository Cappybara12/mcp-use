"""
Validates PyPI version strings according to PEP 440 specification.
"""
from dataclasses import dataclass
from .converters.python_version_converter import PythonVersionConverter


@dataclass(frozen=True)
class ValidationResult:
    """
    Represents the result of a version validation.

    Args:
        success: Whether the validation was successful
        error_message: The error message if validation failed
    """
    success: bool
    error_message: str | None = None

    def __str__(self) -> str:
        return "Valid" if self.success else f"Invalid: {self.error_message}"


class VersionValidator:
    """
    Validates PyPI version strings according to PEP 440 specification.
    """

    @staticmethod
    def is_valid(version: str) -> bool:
        """
        Determines whether the specified version string is a valid PyPI version.

        Args:
            version: The version string to validate

        Returns:
            True if the version is valid; otherwise, False
        """
        converter = PythonVersionConverter()
        package_version, _ = converter.try_to_canonical(version)
        return package_version is not None

    @staticmethod
    def validate(version: str) -> ValidationResult:
        """
        Validates a version string and returns a detailed validation result.

        Args:
            version: The version string to validate

        Returns:
            A ValidationResult containing the validation status and error messages
        """
        if not version or not version.strip():
            return ValidationResult(False, "Version string cannot be null or empty.")

        converter = PythonVersionConverter()
        package_version, error = converter.try_to_canonical(version)
        return ValidationResult(package_version is not None, error)
