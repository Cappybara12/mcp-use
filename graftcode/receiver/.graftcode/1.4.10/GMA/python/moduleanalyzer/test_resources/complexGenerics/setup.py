"""Setup file for complex generics test package."""

from setuptools import find_packages, setup

if __name__ == "__main__":
    setup(
        name="complex-generics-and-arrays",
        version="1.0.0",
        description="Test package with complex generics and arrays for module analyzer testing",
        author="Test Author",
        python_requires=">=3.7",
        packages=find_packages(),
        py_modules=["examples"],
    )
