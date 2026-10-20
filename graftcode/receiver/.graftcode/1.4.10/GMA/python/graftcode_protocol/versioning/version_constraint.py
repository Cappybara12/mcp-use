"""
PEP 440 version constraint (specifier set) handling.

Provides the VersionConstraint class for parsing and evaluating
version specifiers like ">=1.0,<2.0" or "~=1.4".
"""

from dataclasses import dataclass
from typing import Iterable, Iterator

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version


@dataclass
class VersionConstraint:
    """
    PEP 440 version constraint (specifier set).

    Wraps a specifier string like ">=1.0,<2.0" or "~=1.4" and provides
    methods to check if versions satisfy the constraint.

    Attributes:
        raw: The original specifier string.

    Examples:
        >>> constraint = VersionConstraint(">=1.0,<2.0")
        >>> constraint.contains("1.5.0")
        True
        >>> constraint.contains("2.1.0")
        False

        >>> constraint = VersionConstraint("~=1.4")
        >>> constraint.contains("1.5")
        True
        >>> constraint.contains("2.0")
        False
    """

    raw: str  # Original specifier string, e.g., ">=1.0,<2.0"

    def __post_init__(self) -> None:
        """Parse the raw specifier string into a SpecifierSet."""
        try:
            object.__setattr__(
                self,
                "_specifier_set",
                SpecifierSet(self.raw) if self.raw else SpecifierSet(),
            )
        except InvalidSpecifier as e:
            raise ValueError(f"Invalid version specifier '{self.raw}': {e}") from e

    @property
    def specifier_set(self) -> SpecifierSet:
        """Get the underlying SpecifierSet object."""
        return self._specifier_set

    def contains(self, version: str, prereleases: bool | None = None) -> bool:
        """
        Check if a version satisfies this constraint.

        Args:
            version: Version string to check (e.g., "1.5.0").
            prereleases: Whether to include pre-releases. None = auto-detect.

        Returns:
            True if the version satisfies the constraint.

        Raises:
            ValueError: If the version string is invalid.
        """
        try:
            ver = Version(version)
            return self._specifier_set.contains(ver, prereleases=prereleases)
        except InvalidVersion as e:
            raise ValueError(f"Invalid version '{version}': {e}") from e

    def filter(
        self, versions: Iterable[str], prereleases: bool | None = None
    ) -> Iterator[str]:
        """
        Filter versions that satisfy this constraint.

        Args:
            versions: Iterable of version strings to filter.
            prereleases: Whether to include pre-releases. None = auto-detect.

        Yields:
            Version strings that satisfy the constraint.
        """
        return self._specifier_set.filter(versions, prereleases=prereleases)

    def select_best_match(
        self, versions: Iterable[str], prereleases: bool | None = None
    ) -> str | None:
        """
        Select the best (highest) matching version from a list.

        Args:
            versions: Iterable of version strings to choose from.
            prereleases: Whether to include pre-releases. None = auto-detect.

        Returns:
            The highest version that satisfies the constraint, or None.
        """
        matching = list(self.filter(versions, prereleases=prereleases))
        if not matching:
            return None
        return str(max(Version(v) for v in matching))

    def is_empty(self) -> bool:
        """Check if this constraint matches any version (empty specifier)."""
        return not self.raw or self.raw.strip() == ""

    def __str__(self) -> str:
        """Return the raw specifier string."""
        return self.raw

    def __repr__(self) -> str:
        """Return a detailed representation."""
        return f"VersionConstraint('{self.raw}')"
