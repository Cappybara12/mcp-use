"""Setup file for test package."""

from setuptools import find_packages, setup

if __name__ == "__main__":
    setup(
        name="test-setuppy-package",
        version="3.0.0",
        description="A test package for setup.py parsing",
        author="Test Author",
        python_requires=">=3.9",
        packages=find_packages(),
    )
