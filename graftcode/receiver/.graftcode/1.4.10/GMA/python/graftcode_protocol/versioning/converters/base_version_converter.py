"""
Interface for platform-specific version converters.

Subclasses must implement ``to_canonical`` and ``from_canonical`` (which raise
on invalid input).  The ``try_*`` variants are provided by the base class and
wrap the raising methods in try/except.
"""
from abc import ABC, abstractmethod
from ...models.package_version import PackageVersion


class BaseVersionConverter(ABC):
    """
    Interface for platform-specific version converters.

    Subclasses implement ``to_canonical`` / ``from_canonical`` with raise-on-error
    semantics.  ``try_to_canonical`` / ``try_from_canonical`` are derived
    automatically — override only when a converter needs custom try-logic.
    """

    @abstractmethod
    def to_canonical(self, version_string: str) -> PackageVersion:
        """
        Converts a platform-specific version string to the canonical PackageVersion format.

        Raises:
            ValueError: If the version string is invalid
        """

    @abstractmethod
    def from_canonical(self, canonical: PackageVersion) -> str:
        """
        Converts a canonical PackageVersion to a platform-specific version string.

        Raises:
            ValueError: If canonical is None or invalid
        """

    def try_to_canonical(self, version_string: str) -> tuple[PackageVersion | None, str | None]:
        """Wraps ``to_canonical`` — returns ``(None, error)`` instead of raising."""
        try:
            return self.to_canonical(version_string), None
        except (ValueError, TypeError) as exc:
            return None, str(exc)

    def try_from_canonical(self, canonical: PackageVersion | None) -> tuple[str | None, str | None]:
        """Wraps ``from_canonical`` — returns ``(None, error)`` instead of raising."""
        try:
            return self.from_canonical(canonical), None
        except (ValueError, TypeError) as exc:
            return None, str(exc)
