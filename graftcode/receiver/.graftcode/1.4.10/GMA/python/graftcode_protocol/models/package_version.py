"""
Canonical package version model following SemVer 2.0 format with extensions.
This model preserves the original format as much as possible for traceability.

Extended fields support:
- epoch: Python PEP 440 epoch (e.g., "1!" in "1!2.0.0")
- local_version: Python PEP 440 local version identifier (e.g., "+ubuntu1")
- platform: RubyGems platform-specific identifier (e.g., "-java")
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class PackageVersion:
    """
    Represents a canonical package version following SemVer 2.0 format with extensions.

    Args:
        major: Major version number
        minor: Minor version number
        patch: Patch version number
        prerelease_label: Pre-release label (e.g., "alpha", "beta", "rc", "a", "b")
        prerelease_number: Pre-release number (e.g., 1 in "beta.1")
        build_metadata: Build metadata (everything after '+' in SemVer 2.0)
        epoch: Python PEP 440 epoch number
        local_version: Python PEP 440 local version identifier
        platform: RubyGems platform-specific identifier
    """
    major: int
    minor: int
    patch: int
    prerelease_label: str | None = None
    prerelease_number: int | None = None
    build_metadata: str | None = None
    epoch: int | None = None
    local_version: str | None = None
    platform: str | None = None

    def __str__(self) -> str:
        """
        Returns the canonical SemVer 2.0 string representation of the version.
        """
        version = f"{self.major}.{self.minor}.{self.patch}"

        if self.prerelease_label:
            version += f"-{self.prerelease_label}"
            if self.prerelease_number is not None:
                version += f".{self.prerelease_number}"

        if self.build_metadata:
            version += f"+{self.build_metadata}"

        return version


    @property
    def is_prerelease(self) -> bool:
        """Determines whether this version is a pre-release version."""
        return self.prerelease_label is not None

    @property
    def is_stable(self) -> bool:
        """Determines whether this version is a stable release."""
        return self.prerelease_label is None

    @staticmethod
    def parse(version: str) -> 'PackageVersion':
        """
        Parses a canonical SemVer 2.0 string into a PackageVersion instance.

        Args:
            version: The version string to parse (e.g., "1.2.3", "1.0.0-beta.1", "2.1.0+build.123")

        Returns:
            A new PackageVersion instance

        Raises:
            ValueError: If the version string is not in a valid format
        """
        result, error = PackageVersion.try_parse(version)
        if result is None:
            raise ValueError(
                f"Invalid version format: '{version}'. "
                f"Expected SemVer 2.0 format (e.g., '1.2.3', '1.0.0-beta.1', '2.1.0+build.123'). "
                f"Error: {error}"
            )
        return result

    @staticmethod
    def try_parse(version: str) -> tuple['PackageVersion | None', str | None]:
        """
        Tries to parse a canonical SemVer 2.0 string into a PackageVersion instance.

        Returns:
            A tuple of (PackageVersion, error_message).
            If successful, error_message is None; if failed, PackageVersion is None.
        """
        if not version or not version.strip():
            return None, "Version string cannot be null or empty."

        try:
            build_metadata_parts = version.split('+', 1)
            main_version = build_metadata_parts[0]
            build_metadata = build_metadata_parts[1] if len(build_metadata_parts) > 1 else None

            prerelease_parts = main_version.split('-', 1)
            core_version = prerelease_parts[0]
            prerelease_info = prerelease_parts[1] if len(prerelease_parts) > 1 else None

            major, minor, patch = PackageVersion._parse_core_version(core_version)
            prerelease_label, prerelease_number = PackageVersion._parse_prerelease_info(prerelease_info)

            return PackageVersion(
                major, minor, patch,
                prerelease_label, prerelease_number, build_metadata
            ), None
        except ValueError as exc:
            return None, str(exc)

    @staticmethod
    def _parse_core_version(core_version: str) -> tuple[int, int, int]:
        """
        Parses 'X.Y.Z' into (major, minor, patch).

        Raises:
            ValueError: If the format is invalid.
        """
        parts = core_version.split('.')
        if len(parts) != 3:
            raise ValueError("Version must have exactly 3 parts (major.minor.patch).")

        try:
            major, minor, patch = map(int, parts)
        except ValueError:
            raise ValueError(f"Non-integer components in '{core_version}'.")

        if not all(v >= 0 for v in (major, minor, patch)):
            raise ValueError(f"Negative version numbers in '{core_version}'.")

        return major, minor, patch

    @staticmethod
    def _parse_prerelease_info(prerelease_info: str | None) -> tuple[str | None, int | None]:
        """
        Parses prerelease information.

        Returns:
            Tuple of (prerelease_label, prerelease_number)
        """
        if not prerelease_info:
            return None, None

        prerelease_segments = prerelease_info.split('.')
        prerelease_label = prerelease_segments[0]
        prerelease_number = None

        if len(prerelease_segments) > 1:
            # Try to parse the last segment as a number
            try:
                prerelease_number = int(prerelease_segments[-1])

                # If there are more than 2 segments, reconstruct the label
                if len(prerelease_segments) > 2:
                    prerelease_label = '.'.join(prerelease_segments[:-1])

            except ValueError:
                # Not a number, so the entire thing is the label
                prerelease_label = prerelease_info

        return prerelease_label, prerelease_number
