"""
Converts between Maven version strings and the canonical PackageVersion format.
"""
import re
from .base_version_converter import BaseVersionConverter
from ...models.package_version import PackageVersion


class MavenVersionConverter(BaseVersionConverter):
    """
    Converts between Maven version strings and the canonical PackageVersion format.
    Maven format examples: 1.2.3, 1.2.3-beta-1, 1.2.3-SNAPSHOT
    Note: Maven uses dash-separated prerelease identifiers instead of dot-separated.
    """

    # Maven version pattern: Major.Minor.Patch[-Qualifier.Number]
    VERSION_PATTERN = re.compile(
        r'^(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)'
        r'(?:-(?P<prerelease>[A-Za-z0-9]+)(?:\.(?P<number>\d+))?)?$',
        re.IGNORECASE
    )

    SNAPSHOT_LABEL = "snapshot"

    def to_canonical(self, version_string: str) -> PackageVersion:
        """
        Converts a Maven version string to the canonical PackageVersion format.
        Supports formats: 1.2.3, 1.2.3-beta.1, 1.2.3-SNAPSHOT

        Raises:
            ValueError: If version_string is empty or does not match Maven format.
        """
        if not version_string or not version_string.strip():
            raise ValueError("Version string cannot be null or empty.")

        version_string = version_string.strip()
        match = self.VERSION_PATTERN.match(version_string)
        if not match:
            raise ValueError(
                f"Version string '{version_string}' does not match Maven format."
            )

        major = int(match.group('major'))
        minor = int(match.group('minor'))
        patch = int(match.group('patch'))

        prerelease_label = None
        prerelease_number = None

        if match.group('prerelease'):
            prerelease_label = match.group('prerelease').lower()

            if prerelease_label != self.SNAPSHOT_LABEL and match.group('number'):
                prerelease_number = int(match.group('number'))

        return PackageVersion(
            major, minor, patch,
            prerelease_label, prerelease_number, None
        )

    def from_canonical(self, canonical: PackageVersion) -> str:
        """
        Converts a canonical PackageVersion to a Maven version string.
        Produces format: 1.2.3 or 1.2.3-beta-1 or 1.2.3-SNAPSHOT
        """
        if canonical is None:
            raise ValueError("Canonical version cannot be None.")

        version = f"{canonical.major}.{canonical.minor}.{canonical.patch}"

        if canonical.prerelease_label:
            # Use lowercase for labels (snapshot, not SNAPSHOT)
            maven_label = canonical.prerelease_label.lower()

            version += f"-{maven_label}"

            # Add prerelease number with dot separator (e.g., beta.1)
            if canonical.prerelease_number is not None:
                version += f".{canonical.prerelease_number}"

        # Note: Maven versions don't typically include build metadata
        # If build metadata is present, it will be ignored

        return version

