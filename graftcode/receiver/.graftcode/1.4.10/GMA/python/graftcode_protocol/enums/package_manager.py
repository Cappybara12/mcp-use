"""
Enum representing different package managers and their version format conventions.
"""
from enum import Enum


class PackageManager(Enum):
    """
    Represents different package managers and their version format conventions.
    """
    
    # NuGet package manager (.NET) - uses SemVer 2.0 format: 1.2.3-beta.1+build
    NUGET = "nuget"
    
    # Python package manager (pip/PyPI) - uses PEP 440 format: 1.2.3b1, 1.2.3.post1
    PYTHON = "python"
    
    # npm package manager (Node.js) - uses SemVer 2.0 format: 1.2.3-beta.1
    NPM = "npm"
    
    # Maven package manager (Java) - uses format: 1.2.3-beta-1
    MAVEN = "maven"
    
    # RubyGems package manager - uses format: 1.2.3.pre.1
    RUBYGEMS = "rubygems"
    
    # Canonical format used for inter-service communication - uses SemVer 2.0 format
    CANONICAL = "canonical"
