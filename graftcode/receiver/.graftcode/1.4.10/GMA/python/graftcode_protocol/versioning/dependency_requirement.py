"""
Dependency requirement model with version constraint support.

Represents a package requirement as specified in requirements.txt or
pyproject.toml, along with the currently installed version (if any).
"""

from dataclasses import dataclass, field

from .version_constraint import VersionConstraint


@dataclass
class DependencyRequirement:
    """
    A parsed dependency requirement with constraint and installed version.

    The `required` field is a PEP 440 specifier set (constraint expression),
    while `installed` is a concrete version string.

    Attributes:
        package_name: The name of the package.
        required: Version constraint (PEP 440 specifier set), or None.
        installed: Concrete installed version string, or None.
        extras: List of extras requested (e.g., ["security", "socks"]).
        environment_marker: PEP 508 environment marker, or None.

    Examples:
        >>> req = DependencyRequirement(
        ...     package_name="requests",
        ...     required=VersionConstraint(">=2.0,<3.0"),
        ...     installed="2.28.1"
        ... )
        >>> req.is_satisfied
        True

        >>> req = DependencyRequirement(
        ...     package_name="numpy",
        ...     required=VersionConstraint(">=2.0"),
        ...     installed="1.24.0"
        ... )
        >>> req.is_satisfied
        False
    """

    package_name: str
    required: VersionConstraint | None = None
    installed: str | None = None
    extras: list[str] = field(default_factory=list)
    environment_marker: str | None = None

    @property
    def is_satisfied(self) -> bool:
        """
        Check if the installed version satisfies the requirement.

        Returns:
            True if:
            - installed is set AND (required is None OR installed matches)
            False if:
            - installed is None (package not installed)
            - installed doesn't match required constraint
        """
        if self.installed is None:
            return False
        if self.required is None or self.required.is_empty():
            return True
        try:
            return self.required.contains(self.installed)
        except ValueError:
            return False

    @property
    def is_installed(self) -> bool:
        """Check if the package is installed."""
        return self.installed is not None

    def to_requirement_string(self) -> str:
        """
        Convert back to a PEP 508 requirement string.

        Returns:
            A string like "requests[security]>=2.0,<3.0; python_version>='3.6'"
        """
        parts = [self.package_name]

        if self.extras:
            parts.append(f"[{','.join(self.extras)}]")

        if self.required and not self.required.is_empty():
            parts.append(str(self.required))

        result = "".join(parts)

        if self.environment_marker:
            result += f"; {self.environment_marker}"

        return result

    def __str__(self) -> str:
        """Return a human-readable representation."""
        status = "satisfied" if self.is_satisfied else "NOT satisfied"
        installed_str = self.installed or "not installed"
        required_str = str(self.required) if self.required else "any"
        return (
            f"{self.package_name} "
            f"(required: {required_str}, installed: {installed_str}) "
            f"[{status}]"
        )
