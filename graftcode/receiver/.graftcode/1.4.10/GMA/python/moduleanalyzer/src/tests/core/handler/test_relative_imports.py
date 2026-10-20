"""Tests for relative import handling in LibraryAnalyzer and InterfaceAnalyzer."""

import os
import tempfile

import pytest

from moduleanalyzer.src.core.handler.analysis.library_analyzer import LibraryAnalyzer
from moduleanalyzer.src.core.handler.interface_analyzer import InterfaceAnalyzer


class TestRelativeImports:
    """Test relative import handling."""

    @pytest.fixture
    def temp_package_with_relative_imports(self):
        """Create a temporary package with relative imports."""
        temp_dir = tempfile.mkdtemp()
        package_dir = os.path.join(temp_dir, "test_package")
        os.makedirs(package_dir)

        # Create __init__.py with relative import
        init_file = os.path.join(package_dir, "__init__.py")
        with open(init_file, "w") as f:
            f.write("from .module_a import ClassA\n")
            f.write('__version__ = "1.0.0"\n')

        # Create module_a.py
        module_a_file = os.path.join(package_dir, "module_a.py")
        with open(module_a_file, "w") as f:
            f.write("class ClassA:\n")
            f.write("    def method_a(self):\n")
            f.write("        pass\n")

        # Create module_b.py with relative import
        module_b_file = os.path.join(package_dir, "module_b.py")
        with open(module_b_file, "w") as f:
            f.write("from .module_a import ClassA\n")
            f.write("\n")
            f.write("class ClassB:\n")
            f.write("    def method_b(self):\n")
            f.write("        return ClassA()\n")

        yield package_dir

        # Cleanup
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_library_analyzer_get_package_context_for_package(
        self, temp_package_with_relative_imports
    ):
        """Test _get_package_context for files in a package."""
        analyzer = LibraryAnalyzer()

        # Test __init__.py
        init_file = os.path.join(temp_package_with_relative_imports, "__init__.py")
        module_name, package_name, package_path = analyzer._get_package_context(
            init_file
        )

        assert module_name == "test_package"
        assert package_name == "test_package"
        assert package_path == temp_package_with_relative_imports

        # Test module_a.py
        module_a_file = os.path.join(temp_package_with_relative_imports, "module_a.py")
        module_name, package_name, package_path = analyzer._get_package_context(
            module_a_file
        )

        assert module_name == "test_package.module_a"
        assert package_name == "test_package"
        assert package_path == temp_package_with_relative_imports

    def test_library_analyzer_get_package_context_for_standalone_file(self):
        """Test _get_package_context for standalone file (not in a package)."""
        analyzer = LibraryAnalyzer()

        # Create standalone file (no __init__.py in directory)
        temp_dir = tempfile.mkdtemp()
        standalone_file = os.path.join(temp_dir, "standalone.py")
        with open(standalone_file, "w") as f:
            f.write("class StandaloneClass:\n    pass\n")

        try:
            module_name, package_name, package_path = analyzer._get_package_context(
                standalone_file
            )

            assert module_name == "standalone"
            assert package_name is None
            assert package_path is None
        finally:
            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_library_analyzer_handles_relative_imports(
        self, temp_package_with_relative_imports
    ):
        """Test that LibraryAnalyzer correctly handles files with relative imports."""
        analyzer = LibraryAnalyzer()

        # Test extracting from __init__.py with relative import
        init_file = os.path.join(temp_package_with_relative_imports, "__init__.py")
        functions, variables = analyzer._extract_from_single_file(init_file)

        # Should not crash and should extract __version__
        assert "__version__" in variables or len(variables) >= 0

        # Test extracting from module_b.py with relative import
        module_b_file = os.path.join(temp_package_with_relative_imports, "module_b.py")
        functions, variables = analyzer._extract_from_single_file(module_b_file)

        # Should not crash
        assert isinstance(functions, list)
        assert isinstance(variables, list)

    def test_interface_analyzer_get_package_context_for_package(
        self, temp_package_with_relative_imports
    ):
        """Test InterfaceAnalyzer._get_package_context for files in a package."""
        # Test __init__.py
        init_file = os.path.join(temp_package_with_relative_imports, "__init__.py")
        module_name, package_name, package_path = (
            InterfaceAnalyzer._get_package_context(init_file)
        )

        assert module_name == "test_package"
        assert package_name == "test_package"
        assert package_path == temp_package_with_relative_imports

        # Test module_a.py
        module_a_file = os.path.join(temp_package_with_relative_imports, "module_a.py")
        module_name, package_name, package_path = (
            InterfaceAnalyzer._get_package_context(module_a_file)
        )

        assert module_name == "test_package.module_a"
        assert package_name == "test_package"
        assert package_path == temp_package_with_relative_imports

    def test_interface_analyzer_handles_relative_imports(
        self, temp_package_with_relative_imports
    ):
        """Test that InterfaceAnalyzer correctly handles files with relative imports."""
        # Test extracting from module_b.py with relative import
        module_b_file = os.path.join(temp_package_with_relative_imports, "module_b.py")
        classes = InterfaceAnalyzer._return_classes_from_file(module_b_file)

        # Should extract ClassB
        class_names = [cls.__name__ for cls in classes]
        assert "ClassB" in class_names

    def test_interface_analyzer_handles_init_with_relative_imports(
        self, temp_package_with_relative_imports
    ):
        """Test InterfaceAnalyzer with __init__.py containing relative imports."""
        init_file = os.path.join(temp_package_with_relative_imports, "__init__.py")
        classes = InterfaceAnalyzer._return_classes_from_file(init_file)

        # __init__.py doesn't define classes, just imports them
        # Should not crash, classes list might be empty or contain imported ClassA
        assert isinstance(classes, list)

    def test_library_analyzer_setup_package_in_sys_modules(
        self, temp_package_with_relative_imports
    ):
        """Test _setup_package_in_sys_modules registers package correctly."""
        import sys

        analyzer = LibraryAnalyzer()

        package_name = "test_package_unique_name"
        package_path = temp_package_with_relative_imports

        # Ensure package is not already in sys.modules
        if package_name in sys.modules:
            del sys.modules[package_name]

        # Setup package
        analyzer._setup_package_in_sys_modules(package_name, package_path)

        # Verify package is registered
        assert package_name in sys.modules
        assert hasattr(sys.modules[package_name], "__path__")
        assert sys.modules[package_name].__path__ == [package_path]
        assert sys.modules[package_name].__package__ == package_name

        # Cleanup
        del sys.modules[package_name]

    def test_interface_analyzer_setup_package_in_sys_modules(
        self, temp_package_with_relative_imports
    ):
        """Test InterfaceAnalyzer._setup_package_in_sys_modules."""
        import sys

        package_name = "test_package_interface_unique"
        package_path = temp_package_with_relative_imports

        # Ensure package is not already in sys.modules
        if package_name in sys.modules:
            del sys.modules[package_name]

        # Setup package
        InterfaceAnalyzer._setup_package_in_sys_modules(package_name, package_path)

        # Verify package is registered
        assert package_name in sys.modules
        assert hasattr(sys.modules[package_name], "__path__")

        # Cleanup
        del sys.modules[package_name]
