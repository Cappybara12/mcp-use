"""
Parses PyPI version strings according to PEP 440 specification.
This class is now a wrapper around PythonVersionConverter for backward compatibility.
Consider using PackageVersion.parse() or VersionConverter directly for new code.
"""
from ..models.package_version import PackageVersion
from .converters.python_version_converter import PythonVersionConverter


class VersionParser:
    """
    Parses PyPI version strings according to PEP 440 specification.
    This class is now a wrapper around PythonVersionConverter for backward compatibility.
    Consider using PackageVersion.parse() or VersionConverter directly for new code.
    """

    _converter = PythonVersionConverter()

    @staticmethod
    def parse(version: str) -> PackageVersion:
        """
        Parses a PyPI version string into a PackageVersion object.

        Args:
            version: The version string to parse

        Returns:
            A PackageVersion object

        Raises:
            ValueError: If the version string is invalid
        """
        return VersionParser._converter.to_canonical(version)

    @staticmethod
    def try_parse(version: str) -> tuple[PackageVersion | None, str | None]:
        """
        Tries to parse a PyPI version string into a PackageVersion object.

        Args:
            version: The version string to parse

        Returns:
            A tuple of (PackageVersion, error_message)
            If successful, error_message is None
            If failed, PackageVersion is None
        """
        return VersionParser._converter.try_to_canonical(version)
