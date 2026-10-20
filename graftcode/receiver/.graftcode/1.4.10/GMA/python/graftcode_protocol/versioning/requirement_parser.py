"""
PEP 508 requirement string parser.

Parses dependency requirement strings like:
- 'requests>=2.0,<3.0'
- 'requests[security]>=2.0,<3.0; python_version>="3.6"'
- 'numpy~=1.20'

Uses the `packaging` library for standards-compliant parsing.
"""

import logging
import re

from packaging.requirements import InvalidRequirement, Requirement

from .dependency_requirement import DependencyRequirement
from .version_constraint import VersionConstraint

logger = logging.getLogger(__name__)


def parse_requirement(req_string: str) -> DependencyRequirement:
    """
    Parse a PEP 508 requirement string into a DependencyRequirement.

    Args:
        req_string: A requirement string like
            "requests[security]>=2.0,<3.0; python_version>='3.6'"

    Returns:
        DependencyRequirement with parsed components.

    Raises:
        ValueError: If the requirement string is invalid.

    Examples:
        >>> req = parse_requirement("requests>=2.0,<3.0")
        >>> req.package_name
        'requests'
        >>> req.required.raw
        '>=2.0,<3.0'

        >>> req = parse_requirement("numpy[dev]~=1.20; python_version>='3.8'")
        >>> req.extras
        ['dev']
    """
    if not req_string or not req_string.strip():
        raise ValueError("Requirement string cannot be empty")

    try:
        req = Requirement(req_string)

        specifier_str = str(req.specifier) if req.specifier else ""
        version_constraint = VersionConstraint(specifier_str) if specifier_str else None

        return DependencyRequirement(
            package_name=req.name,
            required=version_constraint,
            extras=sorted(req.extras),
            environment_marker=str(req.marker) if req.marker else None,
        )
    except InvalidRequirement as e:
        raise ValueError(f"Invalid requirement string '{req_string}': {e}") from e


def try_parse_requirement(
    req_string: str,
) -> tuple[DependencyRequirement | None, str | None]:
    """
    Try to parse a PEP 508 requirement string, returning error.

    Args:
        req_string: A requirement string to parse.

    Returns:
        Tuple of (DependencyRequirement, None) on success,
        or (None, error_message) on failure.

    Examples:
        >>> req, error = try_parse_requirement("requests>=2.0")
        >>> req.package_name
        'requests'
        >>> error is None
        True

        >>> req, error = try_parse_requirement("invalid[")
        >>> req is None
        True
        >>> "Invalid" in error
        True
    """
    try:
        return parse_requirement(req_string), None
    except ValueError as e:
        return None, str(e)


def parse_requirement_line(line: str) -> DependencyRequirement | None:
    """
    Parse a single line from a requirements file.

    Handles:
    - Comments (lines starting with #)
    - Inline comments
    - Blank lines
    - Options (-r, -e, --index-url, etc.)

    Args:
        line: A single line from requirements.txt

    Returns:
        DependencyRequirement if the line contains a valid requirement,
        None otherwise.
    """
    line = line.strip()

    if not line:
        return None

    if line.startswith("#"):
        return None

    if line.startswith("-"):
        return None

    if "#" in line:
        line = line.split("#")[0].strip()

    if not line:
        return None

    req, error = try_parse_requirement(line)
    if error:
        logger.warning("Could not parse requirement line: %r - %s", line, error)
        return None

    return req


def normalize_package_name(name: str) -> str:
    """
    Normalize package name according to PEP 503.

    Converts to lowercase and replaces underscores/dots with hyphens.

    Args:
        name: Package name to normalize.

    Returns:
        Normalized package name.

    Examples:
        >>> normalize_package_name("My_Package.Name")
        'my-package-name'
    """
    return re.sub(r"[-_.]+", "-", name).lower()


def extract_package_name_from_requirement(req_string: str) -> str:
    """
    Extract just the package name from a requirement string.

    This is a lightweight alternative to full parsing when only
    the name is needed.

    Args:
        req_string: A requirement string like "requests[security]>=2.0,<3.0"

    Returns:
        Normalized package name.

    Examples:
        >>> extract_package_name_from_requirement("requests[security]>=2.0")
        'requests'
        >>> extract_package_name_from_requirement("My_Package>=1.0")
        'my-package'
    """
    if "[" in req_string:
        req_string = re.sub(r"\[.*?\]", "", req_string)

    if ";" in req_string:
        req_string = req_string.split(";")[0]

    name = re.split(r"[<>=!~@]", req_string)[0].strip()

    return normalize_package_name(name)


def extract_specifier_from_requirement(req_string: str) -> str:
    """
    Extract the version specifier from a requirement string.

    Args:
        req_string: A requirement string like "requests>=2.0,<3.0"

    Returns:
        Version specifier string, or empty string if none.

    Examples:
        >>> extract_specifier_from_requirement("requests>=2.0,<3.0")
        '>=2.0,<3.0'
        >>> extract_specifier_from_requirement("requests")
        ''
    """
    try:
        req = Requirement(req_string)
        return str(req.specifier) if req.specifier else ""
    except InvalidRequirement:
        match = re.search(r"([<>=!~]+[^;\[]+)", req_string)
        return match.group(1).strip() if match else ""
