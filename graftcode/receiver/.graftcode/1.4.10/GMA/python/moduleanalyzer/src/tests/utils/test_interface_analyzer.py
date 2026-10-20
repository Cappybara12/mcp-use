import os
import tempfile
import zipfile

import pytest

from moduleanalyzer.src.core.handler.interface_analyzer import InterfaceAnalyzer


def create_temp_py_files(file_names, dir_path):
    """Helper function to create temporary Python files."""
    for file_name in file_names:
        with open(os.path.join(dir_path, file_name), "w") as f:
            f.write("class TestClass:\n    pass\n")


def test_return_classes_from_py_valid_path():
    """Test return_classes_from_py with valid directory path."""
    with tempfile.TemporaryDirectory() as tempdir:
        file_names = ["file1.py", "file2.py"]
        create_temp_py_files(file_names, tempdir)
        classes = InterfaceAnalyzer.return_classes_from_py(tempdir)
        assert len(classes) == 2
        assert classes[0].__name__ == "TestClass"
        assert classes[1].__name__ == "TestClass"


def test_return_classes_from_py_file_not_found():
    """Test return_classes_from_py with non-existent path."""
    with pytest.raises(FileNotFoundError):
        InterfaceAnalyzer.return_classes_from_py("non_existent_path")


def test_return_classes_from_py_no_py_files():
    """Test return_classes_from_py with directory containing no Python files."""
    with tempfile.TemporaryDirectory() as tempdir:
        os.mkdir(os.path.join(tempdir, "subdir"))
        classes = InterfaceAnalyzer.return_classes_from_py(tempdir)
        assert len(classes) == 0


def test_return_classes_from_py_with_multiple_classes():
    """Test return_classes_from_py with multiple classes in one file."""
    with tempfile.TemporaryDirectory() as tempdir:
        file_name = "file1.py"
        with open(os.path.join(tempdir, file_name), "w") as f:
            f.write("class TestClass1:\n    pass\n")
            f.write("class TestClass2:\n    pass\n")
        classes = InterfaceAnalyzer.return_classes_from_py(tempdir)
        assert len(classes) == 2
        assert classes[0].__name__ == "TestClass1"
        assert classes[1].__name__ == "TestClass2"


def test_return_classes_from_py_single_file():
    """Test return_classes_from_py with a single Python file."""
    with tempfile.TemporaryDirectory() as tempdir:
        test_file = os.path.join(tempdir, "test_module.py")
        with open(test_file, "w") as f:
            f.write(
                """
class SingleTestClass:
    def test_method(self):
        return "test"

def some_function():
    return 42
"""
            )
        classes = InterfaceAnalyzer.return_classes_from_py(test_file)
        assert len(classes) == 1
        assert classes[0].__name__ == "SingleTestClass"


def test_return_classes_from_py_zip_file():
    """Test return_classes_from_py with ZIP file containing Python files."""
    with tempfile.TemporaryDirectory() as tempdir:
        # Create a Python file to put in the ZIP
        py_content = """
class ZipTestClass:
    def zip_method(self):
        return "from_zip"
"""
        py_file = os.path.join(tempdir, "module_in_zip.py")
        with open(py_file, "w") as f:
            f.write(py_content)

        # Create ZIP file
        zip_file = os.path.join(tempdir, "test_package.zip")
        with zipfile.ZipFile(zip_file, "w") as zf:
            zf.write(py_file, "module_in_zip.py")

        classes = InterfaceAnalyzer.return_classes_from_py(zip_file)
        assert len(classes) == 1
        assert classes[0].__name__ == "ZipTestClass"


def test_return_classes_from_py_whl_file():
    """Test return_classes_from_py with WHL file containing Python files."""
    with tempfile.TemporaryDirectory() as tempdir:
        # Create a Python file to put in the WHL
        py_content = """
class WhlTestClass:
    def whl_method(self):
        return "from_whl"
"""
        py_file = os.path.join(tempdir, "whl_module.py")
        with open(py_file, "w") as f:
            f.write(py_content)

        # Create WHL file (which is just a ZIP file)
        whl_file = os.path.join(tempdir, "test_package.whl")
        with zipfile.ZipFile(whl_file, "w") as zf:
            zf.write(py_file, "whl_module.py")

        classes = InterfaceAnalyzer.return_classes_from_py(whl_file)
        assert len(classes) == 1
        assert classes[0].__name__ == "WhlTestClass"


def test_extract_wheel_files():
    """Test _extract_wheel_files static method."""
    with tempfile.TemporaryDirectory() as tempdir:
        # Create a Python file to put in the WHL
        py_content = """
class ExtractTestClass:
    pass
"""
        py_file = os.path.join(tempdir, "extract_module.py")
        with open(py_file, "w") as f:
            f.write(py_content)

        # Create WHL file
        whl_file = os.path.join(tempdir, "extract_test.whl")
        with zipfile.ZipFile(whl_file, "w") as zf:
            zf.write(py_file, "extract_module.py")

        # Call _extract_wheel_files
        InterfaceAnalyzer._extract_wheel_files(tempdir)

        # Check that the WHL was extracted and __init__.py files were created
        extract_dir = os.path.join(tempdir, "extract_test")
        assert os.path.exists(extract_dir)
        assert os.path.exists(os.path.join(extract_dir, "extract_module.py"))


def test_return_classes_from_file_not_a_file():
    """Test _return_classes_from_file with directory instead of file."""
    with tempfile.TemporaryDirectory() as tempdir:
        with pytest.raises(NotADirectoryError):
            InterfaceAnalyzer._return_classes_from_file(tempdir)


def test_return_classes_from_file_import_error():
    """Test _return_classes_from_file with file that has import errors."""
    with tempfile.TemporaryDirectory() as tempdir:
        # Create a file with import error
        bad_file = os.path.join(tempdir, "bad_import.py")
        with open(bad_file, "w") as f:
            f.write(
                """
import non_existent_module

class BadImportClass:
    pass
"""
            )

        # Should handle the import error gracefully and return empty list
        classes = InterfaceAnalyzer._return_classes_from_file(bad_file)
        # The method should handle the error and return what it can
        assert isinstance(classes, list)


def test_return_classes_from_file_syntax_error():
    """Test _return_classes_from_file with file that has syntax errors."""
    with tempfile.TemporaryDirectory() as tempdir:
        # Create a file with syntax error
        bad_file = os.path.join(tempdir, "syntax_error.py")
        with open(bad_file, "w") as f:
            f.write(
                """
class SyntaxErrorClass
    pass  # Missing colon
"""
            )

        # Should handle the syntax error gracefully
        classes = InterfaceAnalyzer._return_classes_from_file(bad_file)
        assert isinstance(classes, list)


def test_return_classes_from_file_empty_file():
    """Test _return_classes_from_file with empty Python file."""
    with tempfile.TemporaryDirectory() as tempdir:
        test_file = os.path.join(tempdir, "empty.py")
        with open(test_file, "w") as f:
            f.write("")  # Empty file

        classes = InterfaceAnalyzer._return_classes_from_file(test_file)
        assert len(classes) == 0


def test_return_classes_from_file_package_resolution():
    """Test _return_classes_from_file with package structure."""
    with tempfile.TemporaryDirectory() as tempdir:
        # Create package structure
        package_dir = os.path.join(tempdir, "testpackage")
        os.makedirs(package_dir)

        # Create __init__.py to make it a package
        init_file = os.path.join(package_dir, "__init__.py")
        with open(init_file, "w") as f:
            f.write("")

        # Create module in package
        module_file = os.path.join(package_dir, "testmodule.py")
        with open(module_file, "w") as f:
            f.write(
                """
class PackageTestClass:
    def package_method(self):
        return "from_package"
"""
            )

        classes = InterfaceAnalyzer._return_classes_from_file(module_file)
        assert len(classes) == 1
        assert classes[0].__name__ == "PackageTestClass"


def test_return_classes_from_py_with_invalid_extension():
    """Test return_classes_from_py with file that has non-Python extension."""
    with tempfile.TemporaryDirectory() as tempdir:
        # Create a non-Python file
        temp_file = os.path.join(tempdir, "test.txt")
        with open(temp_file, "w") as f:
            f.write("class Test: pass")

        # Should handle non-Python files gracefully
        # The method checks if path is a file and processes it
        classes = InterfaceAnalyzer.return_classes_from_py(temp_file)
        # Depending on implementation, it might return empty list or try to process it
        assert isinstance(classes, list)


def test_return_classes_from_py_recursive_directory():
    """Test return_classes_from_py with nested directory structure."""
    with tempfile.TemporaryDirectory() as tempdir:
        # Create nested directories with Python files
        subdir1 = os.path.join(tempdir, "subdir1")
        subdir2 = os.path.join(subdir1, "subdir2")
        os.makedirs(subdir2)

        # Create Python files at different levels
        file1 = os.path.join(tempdir, "root_module.py")
        with open(file1, "w") as f:
            f.write("class RootClass:\n    pass\n")

        file2 = os.path.join(subdir1, "sub1_module.py")
        with open(file2, "w") as f:
            f.write("class Sub1Class:\n    pass\n")

        file3 = os.path.join(subdir2, "sub2_module.py")
        with open(file3, "w") as f:
            f.write("class Sub2Class:\n    pass\n")

        classes = InterfaceAnalyzer.return_classes_from_py(tempdir)
        assert len(classes) == 3
        class_names = [cls.__name__ for cls in classes]
        assert "RootClass" in class_names
        assert "Sub1Class" in class_names
        assert "Sub2Class" in class_names


def test_return_classes_from_py_zip_with_wheel_extraction():
    """Test return_classes_from_py with ZIP containing WHL files."""
    with tempfile.TemporaryDirectory() as tempdir:
        # Create a Python file for the WHL
        py_content = """
class WheelInZipClass:
    def method(self):
        return "from_wheel_in_zip"
"""
        py_file = os.path.join(tempdir, "wheel_module.py")
        with open(py_file, "w") as f:
            f.write(py_content)

        # Create WHL file
        whl_file = os.path.join(tempdir, "inner.whl")
        with zipfile.ZipFile(whl_file, "w") as zf:
            zf.write(py_file, "wheel_module.py")

        # Create ZIP file containing the WHL
        zip_file = os.path.join(tempdir, "outer.zip")
        with zipfile.ZipFile(zip_file, "w") as zf:
            zf.write(whl_file, "inner.whl")

        classes = InterfaceAnalyzer.return_classes_from_py(zip_file)
        assert len(classes) == 1
        assert classes[0].__name__ == "WheelInZipClass"


def test_resolve_directory_path_with_file():
    """Test _resolve_directory_path with file path."""
    with tempfile.TemporaryDirectory() as tempdir:
        test_file = os.path.join(tempdir, "test.py")
        with open(test_file, "w") as f:
            f.write("x = 1")

        result = InterfaceAnalyzer._resolve_directory_path(test_file)
        assert result == tempdir


def test_resolve_directory_path_with_directory():
    """Test _resolve_directory_path with directory path."""
    with tempfile.TemporaryDirectory() as tempdir:
        result = InterfaceAnalyzer._resolve_directory_path(tempdir)
        assert result == tempdir


def test_resolve_directory_name_or_file_name_with_file():
    """Test _resolve_directory_name_or_file_name with file path."""
    with tempfile.TemporaryDirectory() as tempdir:
        test_file = os.path.join(tempdir, "mymodule.py")
        with open(test_file, "w") as f:
            f.write("x = 1")

        result = InterfaceAnalyzer._resolve_directory_name_or_file_name(test_file)
        assert result == "mymodule"  # File name without extension


def test_resolve_directory_name_or_file_name_with_directory():
    """Test _resolve_directory_name_or_file_name with directory path."""
    with tempfile.TemporaryDirectory() as tempdir:
        subdir = os.path.join(tempdir, "mypackage")
        os.makedirs(subdir)

        result = InterfaceAnalyzer._resolve_directory_name_or_file_name(subdir)
        assert result == "mypackage"


def test_filter_unique_types():
    """Test _filter_unique_types removes duplicates."""

    class TestClass1:
        pass

    class TestClass2:
        pass

    # Create list with duplicates
    classes = [TestClass1, TestClass2, TestClass1, TestClass2, TestClass1]

    result = InterfaceAnalyzer._filter_unique_types(classes)

    # Should only have 2 unique classes
    assert len(result) == 2
    class_names = [cls.__name__ for cls in result]
    assert "TestClass1" in class_names
    assert "TestClass2" in class_names


def test_handle_archive_file_with_regular_py_file():
    """Test _handle_archive_file returns None for regular .py files."""
    with tempfile.TemporaryDirectory() as tempdir:
        test_file = os.path.join(tempdir, "test.py")
        with open(test_file, "w") as f:
            f.write("x = 1")

        result = InterfaceAnalyzer._handle_archive_file(test_file)
        assert result is None


def test_handle_archive_file_with_zip():
    """Test _handle_archive_file extracts ZIP files."""
    with tempfile.TemporaryDirectory() as tempdir:
        # Create a ZIP file
        zip_path = os.path.join(tempdir, "test.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("module.py", "class Test: pass")

        result = InterfaceAnalyzer._handle_archive_file(zip_path)

        assert result is not None
        assert result == zip_path[:-4]  # Without .zip extension
        assert os.path.exists(result)


def test_handle_archive_file_with_whl():
    """Test _handle_archive_file extracts WHL files."""
    with tempfile.TemporaryDirectory() as tempdir:
        # Create a WHL file
        whl_path = os.path.join(tempdir, "package.whl")
        with zipfile.ZipFile(whl_path, "w") as zf:
            zf.writestr("module.py", "class Test: pass")

        result = InterfaceAnalyzer._handle_archive_file(whl_path)

        assert result is not None
        assert result == whl_path[:-4]  # Without .whl extension
        assert os.path.exists(result)


def test_create_init_files():
    """Test _create_init_files creates __init__.py in directories."""
    with tempfile.TemporaryDirectory() as tempdir:
        # Create nested directories
        subdir1 = os.path.join(tempdir, "pkg1")
        subdir2 = os.path.join(subdir1, "subpkg")
        os.makedirs(subdir2)

        # Create Python files
        with open(os.path.join(subdir1, "mod.py"), "w") as f:
            f.write("x = 1")

        InterfaceAnalyzer._create_init_files(tempdir)

        # Check __init__.py files were created
        assert os.path.exists(os.path.join(subdir1, "__init__.py"))
        assert os.path.exists(os.path.join(subdir2, "__init__.py"))


def test_process_directory_empty():
    """Test _process_directory with empty directory."""
    with tempfile.TemporaryDirectory() as tempdir:
        result = InterfaceAnalyzer._process_directory(tempdir)
        assert result == []


# ------------------------------------------------------------------
# Fix 3: EXCLUDED_DIRS are skipped during class discovery
# ------------------------------------------------------------------


def test_process_directory_skips_excluded_dirs():
    """_process_directory skips __pycache__, tests, generated_output, etc."""
    with tempfile.TemporaryDirectory() as tempdir:
        # Source directory with a real class
        src = os.path.join(tempdir, "src")
        os.makedirs(src)
        with open(os.path.join(src, "real.py"), "w") as f:
            f.write("class RealClass:\n    pass\n")

        # Directories that should be excluded
        for excluded in ("__pycache__", "tests", "generated_output", "test_wheels"):
            edir = os.path.join(tempdir, excluded)
            os.makedirs(edir)
            with open(os.path.join(edir, "hidden.py"), "w") as f:
                f.write("class HiddenClass:\n    pass\n")

        classes = InterfaceAnalyzer._process_directory(tempdir)
        names = [cls.__name__ for cls in classes]

        assert "RealClass" in names
        assert "HiddenClass" not in names


def test_process_directory_skips_test_dir():
    """_process_directory skips 'test/' directories to avoid test-framework deps."""
    with tempfile.TemporaryDirectory() as tempdir:
        with open(os.path.join(tempdir, "app.py"), "w") as f:
            f.write("class AppClass:\n    pass\n")

        test_dir = os.path.join(tempdir, "test")
        os.makedirs(test_dir)
        with open(os.path.join(test_dir, "test_app.py"), "w") as f:
            f.write("class TestAppClass:\n    pass\n")

        classes = InterfaceAnalyzer._process_directory(tempdir)
        names = [cls.__name__ for cls in classes]

        assert "AppClass" in names
        assert "TestAppClass" not in names
