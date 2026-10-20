"""
Version conversion system for multi-platform package managers.
"""
from ..models.package_version import PackageVersion
from ..enums.package_manager import PackageManager
from .version_converter import VersionConverter
from .version_parser import VersionParser
from .version_validator import VersionValidator
from .dependency_requirement import DependencyRequirement
from .version_constraint import VersionConstraint
from .requirement_parser import (
    parse_requirement,
    try_parse_requirement,
    parse_requirement_line,
    normalize_package_name,
    extract_package_name_from_requirement,
    extract_specifier_from_requirement,
)

__all__ = [
    'PackageVersion',
    'PackageManager',
    'VersionConverter',
    'VersionParser',
    'VersionValidator',
    'DependencyRequirement',
    'VersionConstraint',
    'parse_requirement',
    'try_parse_requirement',
    'parse_requirement_line',
    'normalize_package_name',
    'extract_package_name_from_requirement',
    'extract_specifier_from_requirement',
]
