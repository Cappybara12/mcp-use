"""
Factory class that provides version conversion between different package managers and the canonical format.
The canonical format uses SemVer 2.0 and can be passed between services as a string.
"""
from ..models.package_version import PackageVersion
from ..enums.package_manager import PackageManager
from .converters import (
    BaseVersionConverter,
    NuGetVersionConverter,
    PythonVersionConverter,
    NpmVersionConverter,
    MavenVersionConverter
)


class VersionConverter:
    """
    Factory class that provides version conversion between different package managers and the canonical format.
    The canonical format uses SemVer 2.0 and can be passed between services as a string.
    """

    _converters: dict[PackageManager, BaseVersionConverter] = {
        PackageManager.NUGET: NuGetVersionConverter(),
        PackageManager.PYTHON: PythonVersionConverter(),
        PackageManager.NPM: NpmVersionConverter(),
        PackageManager.MAVEN: MavenVersionConverter(),
        PackageManager.RUBYGEMS: NuGetVersionConverter(),  # RubyGems uses SemVer-like format
        PackageManager.CANONICAL: NuGetVersionConverter()  # Canonical uses SemVer 2.0
    }

    @staticmethod
    def get_converter(package_manager: PackageManager) -> BaseVersionConverter:
        """
        Gets the appropriate converter for the specified package manager.

        Args:
            package_manager: The package manager type

        Returns:
            The version converter for the specified package manager

        Raises:
            NotImplementedError: If the package manager is not supported
        """
        if package_manager not in VersionConverter._converters:
            raise NotImplementedError(f"Package manager '{package_manager}' is not supported.")

        return VersionConverter._converters[package_manager]

    @staticmethod
    def to_canonical(version_string: str, package_manager: PackageManager) -> PackageVersion:
        """
        Converts a platform-specific version string to the canonical PackageVersion format.

        Args:
            version_string: The platform-specific version string
            package_manager: The source package manager type

        Returns:
            A PackageVersion object representing the canonical format
        """
        converter = VersionConverter.get_converter(package_manager)
        return converter.to_canonical(version_string)

    @staticmethod
    def try_to_canonical(
        version_string: str,
        package_manager: PackageManager
    ) -> tuple[PackageVersion | None, str | None]:
        """
        Tries to convert a platform-specific version string to the canonical PackageVersion format.

        Args:
            version_string: The platform-specific version string
            package_manager: The source package manager type

        Returns:
            A tuple of (PackageVersion, error_message)
            If successful, error_message is None
            If failed, PackageVersion is None
        """
        try:
            converter = VersionConverter.get_converter(package_manager)
            return converter.try_to_canonical(version_string)
        except Exception as e:
            return None, str(e)

    @staticmethod
    def from_canonical(canonical: PackageVersion, package_manager: PackageManager) -> str:
        """
        Converts a canonical PackageVersion to a platform-specific version string.

        Args:
            canonical: The canonical PackageVersion
            package_manager: The target package manager type

        Returns:
            A platform-specific version string
        """
        converter = VersionConverter.get_converter(package_manager)
        return converter.from_canonical(canonical)

    @staticmethod
    def try_from_canonical(
        canonical: PackageVersion | None,
        package_manager: PackageManager
    ) -> tuple[str | None, str | None]:
        """
        Tries to convert a canonical PackageVersion to a platform-specific version string.

        Args:
            canonical: The canonical PackageVersion
            package_manager: The target package manager type

        Returns:
            A tuple of (version_string, error_message)
            If successful, error_message is None
            If failed, version_string is None
        """
        try:
            converter = VersionConverter.get_converter(package_manager)
            return converter.try_from_canonical(canonical)
        except Exception as e:
            return None, str(e)

    @staticmethod
    def to_canonical_string(canonical: PackageVersion) -> str:
        """
        Converts a canonical PackageVersion to a canonical string representation.
        This string can be passed between services and parsed back using PackageVersion.parse().

        Args:
            canonical: The canonical PackageVersion

        Returns:
            A canonical version string in SemVer 2.0 format
        """
        if canonical is None:
            raise ValueError("Canonical version cannot be None.")

        return str(canonical)

    @staticmethod
    def from_canonical_string(canonical_string: str) -> PackageVersion:
        """
        Parses a canonical version string (from another service) to a PackageVersion.

        Args:
            canonical_string: The canonical version string in SemVer 2.0 format

        Returns:
            A PackageVersion object
        """
        return PackageVersion.parse(canonical_string)

    @staticmethod
    def try_from_canonical_string(canonical_string: str) -> tuple[PackageVersion | None, str | None]:
        """
        Tries to parse a canonical version string (from another service) to a PackageVersion.

        Args:
            canonical_string: The canonical version string in SemVer 2.0 format

        Returns:
            A tuple of (PackageVersion, error_message)
            If successful, error_message is None
            If failed, PackageVersion is None
        """
        return PackageVersion.try_parse(canonical_string)
