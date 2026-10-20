"""
Converts between npm (Node.js) version strings and the canonical PackageVersion format.
"""
from .base_version_converter import BaseVersionConverter
from ...models.package_version import PackageVersion


class NpmVersionConverter(BaseVersionConverter):
    """
    Converts between npm (Node.js) version strings and the canonical PackageVersion format.
    npm follows SemVer 2.0, so conversion is direct.
    Format: 1.2.3-beta.1+build
    """

    def to_canonical(self, version_string: str) -> PackageVersion:
        """
        Converts an npm version string to the canonical PackageVersion format.
        npm follows SemVer 2.0, so parsing delegates to PackageVersion.parse.
        """
        return PackageVersion.parse(version_string)

    def from_canonical(self, canonical: PackageVersion) -> str:
        """
        Converts a canonical PackageVersion to an npm version string.
        npm uses SemVer 2.0 format, which is exactly what str(PackageVersion) provides.
        """
        if canonical is None:
            raise ValueError("Canonical version cannot be None.")
        return str(canonical)
