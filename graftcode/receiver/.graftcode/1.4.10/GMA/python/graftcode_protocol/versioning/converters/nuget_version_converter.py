"""
Converts between NuGet version strings and the canonical PackageVersion format.
"""
from .base_version_converter import BaseVersionConverter
from ...models.package_version import PackageVersion


class NuGetVersionConverter(BaseVersionConverter):
    """
    Converts between NuGet version strings and the canonical PackageVersion format.
    NuGet follows SemVer 2.0, so conversion is mostly direct.
    Format: 1.2.3-beta.1+build
    """

    def to_canonical(self, version_string: str) -> PackageVersion:
        """
        Converts a NuGet version string to the canonical PackageVersion format.
        NuGet follows SemVer 2.0, so parsing delegates to PackageVersion.parse.
        """
        return PackageVersion.parse(version_string)

    def from_canonical(self, canonical: PackageVersion) -> str:
        """
        Converts a canonical PackageVersion to a NuGet version string.
        NuGet uses SemVer 2.0 format, which is exactly what str(PackageVersion) provides.
        """
        if canonical is None:
            raise ValueError("Canonical version cannot be None.")
        return str(canonical)
