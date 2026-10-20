"""
Tests for utils InterfaceAnalyzer.
"""

import os
import shutil
import tempfile
import zipfile

import pytest

from moduleanalyzer.src.utils.interface_analyzer import InterfaceAnalyzer


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_directory = tempfile.mkdtemp()
    yield temp_directory
    shutil.rmtree(temp_directory, ignore_errors=True)


def test_return_classes_from_py_file_not_found(temp_dir):
    """Test return_classes_from_py with non-existent file."""
    non_existent_path = os.path.join(temp_dir, "non_existent.py")

    with pytest.raises(FileNotFoundError) as exc_info:
        InterfaceAnalyzer.return_classes_from_py(non_existent_path)

    assert "File or directory does not exist" in str(exc_info.value)


def test_return_classes_from_py_single_file(temp_dir):
    """Test return_classes_from_py with single Python file."""
    # Create a test Python file with classes
    test_file = os.path.join(temp_dir, "test_module.py")
    with open(test_file, "w") as f:
        f.write(
            """
class TestClass1:
    pass

class TestClass2:
    def method1(self):
        pass

def some_function():
    pass

TEST_CONSTANT = "value"
"""
        )

    # Execute
    classes = InterfaceAnalyzer.return_classes_from_py(test_file)

    # Verify
    assert len(classes) == 2
    class_names = [cls.__name__ for cls in classes]
    assert "TestClass1" in class_names
    assert "TestClass2" in class_names


def test_return_classes_from_py_directory(temp_dir):
    """Test return_classes_from_py with directory containing Python files."""
    # Create multiple Python files with classes
    file1 = os.path.join(temp_dir, "module1.py")
    with open(file1, "w") as f:
        f.write(
            """
class Module1Class:
    pass
"""
        )

    file2 = os.path.join(temp_dir, "module2.py")
    with open(file2, "w") as f:
        f.write(
            """
class Module2Class:
    pass

class AnotherClass:
    pass
"""
        )

    # Create a non-Python file (should be ignored)
    non_py_file = os.path.join(temp_dir, "readme.txt")
    with open(non_py_file, "w") as f:
        f.write("This is not a Python file")

    # Execute
    classes = InterfaceAnalyzer.return_classes_from_py(temp_dir)

    # Verify
    assert len(classes) == 3
    class_names = [cls.__name__ for cls in classes]
    assert "Module1Class" in class_names
    assert "Module2Class" in class_names
    assert "AnotherClass" in class_names


def test_return_classes_from_py_zip_file(temp_dir):
    """Test return_classes_from_py with ZIP file."""
    # Create a Python file
    py_file = os.path.join(temp_dir, "test_module.py")
    with open(py_file, "w") as f:
        f.write(
            """
class ZipTestClass:
    pass
"""
        )

    # Create a ZIP file containing the Python file
    zip_file = os.path.join(temp_dir, "test_package.zip")
    with zipfile.ZipFile(zip_file, "w") as zf:
        zf.write(py_file, "test_module.py")

    # Execute
    classes = InterfaceAnalyzer.return_classes_from_py(zip_file)

    # Verify
    assert len(classes) == 1
    assert classes[0].__name__ == "ZipTestClass"


def test_return_classes_from_py_empty_directory(temp_dir):
    """Test return_classes_from_py with empty directory."""
    empty_dir = os.path.join(temp_dir, "empty")
    os.makedirs(empty_dir)

    # Execute
    classes = InterfaceAnalyzer.return_classes_from_py(empty_dir)

    # Verify
    assert len(classes) == 0


def test_return_classes_from_py_directory_no_classes(temp_dir):
    """Test return_classes_from_py with directory containing Python files but no classes."""
    # Create a Python file without classes
    test_file = os.path.join(temp_dir, "no_classes.py")
    with open(test_file, "w") as f:
        f.write(
            """
def function1():
    pass

def function2():
    return "hello"

CONSTANT = 42
"""
        )

    # Execute
    classes = InterfaceAnalyzer.return_classes_from_py(temp_dir)

    # Verify
    assert len(classes) == 0


def test_return_classes_from_file_directory_instead_of_file(temp_dir):
    """Test _return_classes_from_file with directory instead of file."""
    test_dir = os.path.join(temp_dir, "test_dir")
    os.makedirs(test_dir)

    with pytest.raises(NotADirectoryError) as exc_info:
        InterfaceAnalyzer._return_classes_from_file(test_dir)

    assert "Expected a file but found a directory" in str(exc_info.value)


def test_return_classes_from_file_with_syntax_error(temp_dir):
    """Test _return_classes_from_file with Python file containing syntax error."""
    # Create a Python file with syntax error
    test_file = os.path.join(temp_dir, "syntax_error.py")
    with open(test_file, "w") as f:
        f.write(
            """
class InvalidSyntax
    pass  # Missing colon
"""
        )

    # Execute and expect it to raise an exception
    with pytest.raises(SyntaxError):
        InterfaceAnalyzer._return_classes_from_file(test_file)


def test_return_classes_from_file_with_import_error(temp_dir):
    """Test _return_classes_from_file with Python file that has import issues."""
    # Create a Python file with import error
    test_file = os.path.join(temp_dir, "import_error.py")
    with open(test_file, "w") as f:
        f.write(
            """
import non_existent_module

class TestClass:
    pass
"""
        )

    # Execute and expect it to raise an exception
    with pytest.raises(ModuleNotFoundError):
        InterfaceAnalyzer._return_classes_from_file(test_file)


def test_return_classes_from_py_nested_directories(temp_dir):
    """Test return_classes_from_py with nested directory structure."""
    # Create nested directory structure
    subdir = os.path.join(temp_dir, "subdir")
    os.makedirs(subdir)

    # Create files in both root and subdirectory
    root_file = os.path.join(temp_dir, "root_module.py")
    with open(root_file, "w") as f:
        f.write(
            """
class RootClass:
    pass
"""
        )

    sub_file = os.path.join(subdir, "sub_module.py")
    with open(sub_file, "w") as f:
        f.write(
            """
class SubClass:
    pass
"""
        )

    # Execute
    classes = InterfaceAnalyzer.return_classes_from_py(temp_dir)

    # Verify
    assert len(classes) == 2
    class_names = [cls.__name__ for cls in classes]
    assert "RootClass" in class_names
    assert "SubClass" in class_names


def test_return_classes_from_py_with_inheritance(temp_dir):
    """Test return_classes_from_py with classes that have inheritance."""
    test_file = os.path.join(temp_dir, "inheritance.py")
    with open(test_file, "w") as f:
        f.write(
            """
class BaseClass:
    pass

class DerivedClass(BaseClass):
    pass

class MultipleInheritance(BaseClass):
    pass
"""
        )

    # Execute
    classes = InterfaceAnalyzer.return_classes_from_py(test_file)

    # Verify
    assert len(classes) == 3
    class_names = [cls.__name__ for cls in classes]
    assert "BaseClass" in class_names
    assert "DerivedClass" in class_names
    assert "MultipleInheritance" in class_names


def test_return_classes_from_py_with_inner_classes(temp_dir):
    """Test return_classes_from_py with inner/nested classes."""
    test_file = os.path.join(temp_dir, "nested_classes.py")
    with open(test_file, "w") as f:
        f.write(
            """
class OuterClass:
    class InnerClass:
        pass
    def method(self):
        class LocalClass:
            pass
        return LocalClass

class StandaloneClass:
    pass
"""
        )

    # Execute
    classes = InterfaceAnalyzer.return_classes_from_py(test_file)

    # Verify - should find outer and standalone classes
    # Inner classes might not be detected depending on implementation
    assert len(classes) >= 2
    class_names = [cls.__name__ for cls in classes]
    assert "OuterClass" in class_names
    assert "StandaloneClass" in class_names


def test_return_classes_from_py_nonexistent_path():
    """Test return_classes_from_py when path doesn't exist."""
    nonexistent_path = "/fake/nonexistent/path/to/file.py"

    with pytest.raises(FileNotFoundError, match="File or directory does not exist"):
        InterfaceAnalyzer.return_classes_from_py(nonexistent_path)
