"""Tests for PythonModuleAnalyzerLocal."""

import os
import shutil
import tempfile
import zipfile

import pytest

from moduleanalyzer.src.core.handler.module_analyzer_local import (
    PythonModuleAnalyzerLocal,
)


class TestPythonModuleAnalyzerLocal:
    """Tests for PythonModuleAnalyzerLocal class."""

    @pytest.fixture
    def analyzer(self):
        """Create a PythonModuleAnalyzerLocal instance."""
        return PythonModuleAnalyzerLocal()

    @pytest.fixture
    def temp_project_dir(self):
        """Create a temporary project directory with config file."""
        temp_dir = tempfile.mkdtemp()

        # Create pyproject.toml
        with open(os.path.join(temp_dir, "pyproject.toml"), "w") as f:
            f.write(
                """[project]
name = "test-local-project"
version = "1.0.0"
requires-python = ">=3.8"
"""
            )

        # Create Python module
        with open(os.path.join(temp_dir, "__init__.py"), "w") as f:
            f.write("")

        with open(os.path.join(temp_dir, "main.py"), "w") as f:
            f.write(
                """
class TestClass:
    def method(self):
        return "test"

def global_function():
    return "hello"

CONSTANT = 42
"""
            )

        yield temp_dir

        # Cleanup
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_initialization(self, analyzer):
        """Test PythonModuleAnalyzerLocal initialization."""
        assert analyzer.local_temp_dir is not None
        assert analyzer.library_analyzer is not None

    def test_analyze_local_with_directory(self, analyzer, temp_project_dir):
        """Test analyze_local with a directory path."""
        result = analyzer.analyze_local(temp_project_dir)

        assert result is not None
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_analyze_local_with_file(self, analyzer, temp_project_dir):
        """Test analyze_local with a file path."""
        file_path = os.path.join(temp_project_dir, "main.py")
        result = analyzer.analyze_local(file_path)

        assert result is not None
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_analyze_local_raises_without_metadata_source(self, analyzer):
        """Test that analyze_local raises error when no metadata source exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create only Python file, no config, no .dist-info
            with open(os.path.join(temp_dir, "module.py"), "w") as f:
                f.write("x = 1")

            # Now raises FileNotFoundError when no metadata source is found
            with pytest.raises(FileNotFoundError) as exc_info:
                analyzer.analyze_local(temp_dir)

            assert "No metadata source found" in str(exc_info.value)

    def test_analyze_local_raises_without_name(self, analyzer):
        """Test that analyze_local raises error when config has no name."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create pyproject.toml without name
            with open(os.path.join(temp_dir, "pyproject.toml"), "w") as f:
                f.write(
                    """[project]
version = "1.0.0"
requires-python = ">=3.8"
"""
                )

            with open(os.path.join(temp_dir, "module.py"), "w") as f:
                f.write("x = 1")

            with pytest.raises(ValueError) as exc_info:
                analyzer.analyze_local(temp_dir)

            assert "name" in str(exc_info.value).lower()

    def test_analyze_local_raises_without_version(self, analyzer):
        """Test that analyze_local raises error when config has no version."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create pyproject.toml without version
            with open(os.path.join(temp_dir, "pyproject.toml"), "w") as f:
                f.write(
                    """[project]
name = "test-package"
requires-python = ">=3.8"
"""
                )

            with open(os.path.join(temp_dir, "module.py"), "w") as f:
                f.write("x = 1")

            with pytest.raises(ValueError) as exc_info:
                analyzer.analyze_local(temp_dir)

            assert "version" in str(exc_info.value).lower()

    def test_analyze_local_raises_without_python_requires(self, analyzer):
        """Test that analyze_local raises error when config has no python_requires."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create pyproject.toml without requires-python
            with open(os.path.join(temp_dir, "pyproject.toml"), "w") as f:
                f.write(
                    """[project]
name = "test-package"
version = "1.0.0"
"""
                )

            with open(os.path.join(temp_dir, "module.py"), "w") as f:
                f.write("x = 1")

            with pytest.raises(ValueError) as exc_info:
                analyzer.analyze_local(temp_dir)

            assert "python" in str(exc_info.value).lower()

    def test_analyze_local_with_setup_cfg(self, analyzer):
        """Test analyze_local with setup.cfg config file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create setup.cfg
            with open(os.path.join(temp_dir, "setup.cfg"), "w") as f:
                f.write(
                    """[metadata]
name = setupcfg-project
version = 2.0.0

[options]
python_requires = >=3.7
"""
                )

            with open(os.path.join(temp_dir, "__init__.py"), "w") as f:
                f.write("")

            with open(os.path.join(temp_dir, "module.py"), "w") as f:
                f.write("class MyClass: pass")

            result = analyzer.analyze_local(temp_dir)

            assert result is not None
            assert isinstance(result, bytes)

    def test_analyze_local_with_dist_info_metadata(self, analyzer):
        """Test analyze_local with .dist-info/METADATA (no config files).

        This tests the fallback to .dist-info/METADATA when no config files
        are present, simulating a pip-installed package scenario.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create .dist-info directory with METADATA file (no config files)
            dist_info_path = os.path.join(temp_dir, "dist_info_pkg-2.0.0.dist-info")
            os.makedirs(dist_info_path)

            metadata_content = """\
Metadata-Version: 2.1
Name: dist-info-pkg
Version: 2.0.0
Summary: A test package using dist-info metadata
Requires-Python: >=3.8
"""
            with open(os.path.join(dist_info_path, "METADATA"), "w") as f:
                f.write(metadata_content)

            # Create Python module files
            with open(os.path.join(temp_dir, "__init__.py"), "w") as f:
                f.write("")

            with open(os.path.join(temp_dir, "module.py"), "w") as f:
                f.write(
                    """
class DistInfoClass:
    def method(self):
        return "from dist-info package"

def dist_info_function():
    return "hello from dist-info"
"""
                )

            result = analyzer.analyze_local(temp_dir)

            assert result is not None
            assert isinstance(result, bytes)
            assert len(result) > 0

    def test_analyze_local_pip_installed_package_structure(self, analyzer):
        """Test analyze_local with pip-installed package structure.

        This tests the scenario where:
        - Package folder (e.g., pandas/) is in site-packages/
        - .dist-info folder (e.g., pandas-3.0.0.dist-info/) is NEXT TO it, not inside
        - No config files exist inside the package

        The analyzer should:
        1. Find .dist-info in parent directory (site-packages/)
        2. Copy .dist-info to the temporary working directory
        3. Extract metadata from .dist-info/METADATA
        """
        with tempfile.TemporaryDirectory() as site_packages_dir:
            # Simulate site-packages structure:
            # site-packages/
            # ├── my_pip_package-1.2.3.dist-info/
            # │   └── METADATA
            # └── my_pip_package/
            #     ├── __init__.py
            #     └── module.py

            # Create the package directory (like pandas/)
            package_dir = os.path.join(site_packages_dir, "my_pip_package")
            os.makedirs(package_dir)

            # Create Python files inside package
            with open(os.path.join(package_dir, "__init__.py"), "w") as f:
                f.write("")

            with open(os.path.join(package_dir, "module.py"), "w") as f:
                f.write(
                    """
class PipInstalledClass:
    def method(self):
        return "pip installed"

def pip_function():
    return "from pip"
"""
                )

            # Create .dist-info directory NEXT TO package (not inside!)
            dist_info_dir = os.path.join(
                site_packages_dir, "my_pip_package-1.2.3.dist-info"
            )
            os.makedirs(dist_info_dir)

            # Create METADATA file with required fields
            metadata_content = """\
Metadata-Version: 2.1
Name: my-pip-package
Version: 1.2.3
Summary: A pip-installed test package
Requires-Python: >=3.8
"""
            with open(os.path.join(dist_info_dir, "METADATA"), "w") as f:
                f.write(metadata_content)

            # Analyze the package directory (not the .dist-info!)
            result = analyzer.analyze_local(package_dir)

            # Verify analysis succeeded
            assert result is not None
            assert isinstance(result, bytes)
            assert len(result) > 0

    def test_find_dist_info_for_package(self, analyzer):
        """Test _find_dist_info_for_package method directly."""
        with tempfile.TemporaryDirectory() as site_packages_dir:
            # Create .dist-info directory with various naming patterns
            os.makedirs(os.path.join(site_packages_dir, "my_package-1.0.0.dist-info"))
            os.makedirs(
                os.path.join(site_packages_dir, "other-package-2.0.0.dist-info")
            )

            # Test finding with underscore in name
            result = analyzer._find_dist_info_for_package(
                site_packages_dir, "my_package"
            )
            assert result == "my_package-1.0.0.dist-info"

            # Test finding with hyphen in name (normalized)
            result = analyzer._find_dist_info_for_package(
                site_packages_dir, "other_package"
            )
            assert result == "other-package-2.0.0.dist-info"

            # Test not finding non-existent package
            result = analyzer._find_dist_info_for_package(
                site_packages_dir, "nonexistent"
            )
            assert result is None

    def test_dist_info_is_copied_to_workdir(self, analyzer):
        """Test that .dist-info is actually copied to temporary working directory.

        This test verifies the internal mechanism: when analyzing a pip-installed
        package, the .dist-info folder from the parent directory (site-packages)
        must be copied INTO the temporary working directory.
        """
        import unittest.mock as mock

        with tempfile.TemporaryDirectory() as site_packages_dir:
            # Create pip-installed package structure
            package_dir = os.path.join(site_packages_dir, "test_pkg")
            os.makedirs(package_dir)

            with open(os.path.join(package_dir, "__init__.py"), "w") as f:
                f.write("")

            with open(os.path.join(package_dir, "module.py"), "w") as f:
                f.write("class TestClass: pass")

            # Create .dist-info NEXT TO package
            dist_info_dir = os.path.join(site_packages_dir, "test_pkg-1.0.0.dist-info")
            os.makedirs(dist_info_dir)

            metadata_content = """\
Metadata-Version: 2.1
Name: test-pkg
Version: 1.0.0
Requires-Python: >=3.8
"""
            with open(os.path.join(dist_info_dir, "METADATA"), "w") as f:
                f.write(metadata_content)

            # Track calls to FileUtils._copy_directory
            copied_paths = []

            def track_copy(src, dst, logger):
                copied_paths.append((src, dst))
                # Use shutil directly to avoid infinite recursion
                shutil.copytree(src, dst)

            with mock.patch(
                "moduleanalyzer.src.core.handler.module_analyzer_local.FileUtils._copy_directory",
                side_effect=track_copy,
            ):
                result = analyzer.analyze_local(package_dir)

            # Verify .dist-info was copied
            dist_info_copies = [
                (src, dst) for src, dst in copied_paths if ".dist-info" in src
            ]

            assert len(dist_info_copies) >= 1, (
                f".dist-info should be copied to workdir. "
                f"Actual copies: {copied_paths}"
            )

            # Verify the source was the .dist-info from site-packages
            src_path, dst_path = dist_info_copies[0]
            assert "test_pkg-1.0.0.dist-info" in src_path
            assert "test_pkg-1.0.0.dist-info" in dst_path

            # Verify analysis succeeded
            assert result is not None
            assert isinstance(result, bytes)

    @pytest.mark.skip(reason="setup.py conflicts with pytest")
    def test_analyze_local_with_setup_py(self, analyzer):
        """Test analyze_local with setup.py config file.

        Note: This test is skipped because when _perform_analysis imports
        Python modules using importlib, setup.py may also get executed,
        which conflicts with pytest's command line arguments.

        The setup.py metadata extraction itself works correctly (tested
        in test_library_analyzer.py using AST parsing only).
        """
        pass

    def test_analyze_local_with_zip_containing_config_files(self, analyzer):
        """Test analyze_local with a .zip file containing pyproject.toml.

        Scenario: Package downloaded as .zip with config files inside.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create the package structure to be zipped
            package_content_dir = os.path.join(temp_dir, "zip_package")
            os.makedirs(package_content_dir)

            # Create pyproject.toml
            with open(os.path.join(package_content_dir, "pyproject.toml"), "w") as f:
                f.write(
                    """\
[project]
name = "zip-test-package"
version = "1.0.0"
requires-python = ">=3.8"
"""
                )

            # Create Python module
            with open(os.path.join(package_content_dir, "__init__.py"), "w") as f:
                f.write("")

            with open(os.path.join(package_content_dir, "module.py"), "w") as f:
                f.write(
                    """\
class ZipClass:
    def method(self):
        return "from zip"
"""
                )

            # Create the .zip file
            zip_path = os.path.join(temp_dir, "test_package.zip")
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for root, _, files in os.walk(package_content_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, package_content_dir)
                        zf.write(file_path, arcname)

            # Analyze the .zip file
            result = analyzer.analyze_local(zip_path)

            assert result is not None
            assert isinstance(result, bytes)
            assert len(result) > 0

    def test_analyze_local_with_zip_containing_whl(self, analyzer):
        """Test analyze_local with a .zip file containing a .whl file inside.

        Scenario: Package downloaded as .zip with .whl inside (common for distribution).
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            # First create a .whl file structure
            whl_content_dir = os.path.join(temp_dir, "whl_content")
            os.makedirs(whl_content_dir)

            # Create package folder inside whl
            pkg_dir = os.path.join(whl_content_dir, "whl_test_pkg")
            os.makedirs(pkg_dir)

            with open(os.path.join(pkg_dir, "__init__.py"), "w") as f:
                f.write("")

            with open(os.path.join(pkg_dir, "module.py"), "w") as f:
                f.write(
                    """\
class WhlTestClass:
    def method(self):
        return "from whl in zip"
"""
                )

            # Create .dist-info folder
            dist_info_dir = os.path.join(
                whl_content_dir, "whl_test_pkg-2.0.0.dist-info"
            )
            os.makedirs(dist_info_dir)

            metadata_content = """\
Metadata-Version: 2.1
Name: whl-test-pkg
Version: 2.0.0
Requires-Python: >=3.9
"""
            with open(os.path.join(dist_info_dir, "METADATA"), "w") as f:
                f.write(metadata_content)

            # Create WHEEL file (required for valid wheel)
            with open(os.path.join(dist_info_dir, "WHEEL"), "w") as f:
                f.write("Wheel-Version: 1.0\n")

            # Create RECORD file (required for valid wheel)
            with open(os.path.join(dist_info_dir, "RECORD"), "w") as f:
                f.write("")

            # Create the .whl file (which is just a zip)
            whl_path = os.path.join(temp_dir, "whl_test_pkg-2.0.0-py3-none-any.whl")
            with zipfile.ZipFile(whl_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for root, _, files in os.walk(whl_content_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, whl_content_dir)
                        zf.write(file_path, arcname)

            # Now create a .zip containing the .whl
            zip_path = os.path.join(temp_dir, "package_with_whl.zip")
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.write(whl_path, os.path.basename(whl_path))

            # Analyze the .zip file containing .whl
            result = analyzer.analyze_local(zip_path)

            assert result is not None
            assert isinstance(result, bytes)
            assert len(result) > 0

    def test_analyze_local_with_zip_containing_dist_info(self, analyzer):
        """Test analyze_local with a .zip file containing .dist-info folder.

        Scenario: Extracted wheel packaged as .zip (has .dist-info but no config files).
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create structure like an extracted wheel
            extracted_whl_dir = os.path.join(temp_dir, "extracted_whl")
            os.makedirs(extracted_whl_dir)

            # Create package folder
            pkg_dir = os.path.join(extracted_whl_dir, "dist_info_pkg")
            os.makedirs(pkg_dir)

            with open(os.path.join(pkg_dir, "__init__.py"), "w") as f:
                f.write("")

            with open(os.path.join(pkg_dir, "module.py"), "w") as f:
                f.write("class DistInfoClass: pass")

            # Create .dist-info folder NEXT TO package (like in extracted whl)
            dist_info_dir = os.path.join(
                extracted_whl_dir, "dist_info_pkg-3.0.0.dist-info"
            )
            os.makedirs(dist_info_dir)

            metadata_content = """\
Metadata-Version: 2.1
Name: dist-info-pkg
Version: 3.0.0
Requires-Python: >=3.8
"""
            with open(os.path.join(dist_info_dir, "METADATA"), "w") as f:
                f.write(metadata_content)

            # Create the .zip file containing the extracted whl structure
            zip_path = os.path.join(temp_dir, "extracted_wheel.zip")
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for root, dirs, files in os.walk(extracted_whl_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, extracted_whl_dir)
                        zf.write(file_path, arcname)

            # Analyze the .zip file
            result = analyzer.analyze_local(zip_path)

            assert result is not None
            assert isinstance(result, bytes)
            assert len(result) > 0

    def test_analyze_local_src_layout_config_in_parent(self, analyzer):
        """Test analyze_local with config in parent of --modules target.

        Scenario: User runs `gg --modules ./python_pkg/src`
            python_pkg/
                pyproject.toml      <- config is here (parent of src/)
                src/                <- --modules points here
                    __init__.py
                    module.py

        GMA should find pyproject.toml one level up from the module path.
        """
        with tempfile.TemporaryDirectory() as project_root:
            with open(os.path.join(project_root, "pyproject.toml"), "w") as f:
                f.write(
                    """\
[project]
name = "src-layout-package"
version = "1.0.0"
requires-python = ">=3.9"
"""
                )

            src_dir = os.path.join(project_root, "src")
            os.makedirs(src_dir)

            with open(os.path.join(src_dir, "__init__.py"), "w") as f:
                f.write("")

            with open(os.path.join(src_dir, "module.py"), "w") as f:
                f.write(
                    """\
class SrcLayoutClass:
    def method(self):
        return "from src layout"
"""
                )

            result = analyzer.analyze_local(src_dir)

            assert result is not None
            assert isinstance(result, bytes)
            assert len(result) > 0

    # ------------------------------------------------------------------
    # Fix 1: best-effort copy (permission errors don't crash analysis)
    # ------------------------------------------------------------------
    def test_analyze_local_survives_permission_denied_file(self, analyzer):
        """Copy directory skips files that can't be read (permission error)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with open(os.path.join(temp_dir, "pyproject.toml"), "w") as f:
                f.write(
                    '[project]\nname = "perm-test"\n'
                    'version = "1.0.0"\nrequires-python = ">=3.8"\n'
                )
            with open(os.path.join(temp_dir, "__init__.py"), "w") as f:
                f.write("")
            with open(os.path.join(temp_dir, "module.py"), "w") as f:
                f.write("class OkClass:\n    pass\n")

            # Create a file that cannot be read
            locked = os.path.join(temp_dir, "locked.whl")
            with open(locked, "w") as f:
                f.write("fake wheel")
            os.chmod(locked, 0o000)

            try:
                result = analyzer.analyze_local(temp_dir)
                assert isinstance(result, bytes)
                assert len(result) > 0
            finally:
                os.chmod(locked, 0o644)

    # ------------------------------------------------------------------
    # Fix 2: ancestor config search
    # ------------------------------------------------------------------
    def test_find_config_in_ancestors_finds_pyproject(self):
        """_find_config_in_ancestors walks up and finds pyproject.toml."""
        with tempfile.TemporaryDirectory() as root:
            # root/pyproject.toml
            cfg = os.path.join(root, "pyproject.toml")
            with open(cfg, "w") as f:
                f.write("[project]\nname = 'x'\n")

            # root/a/b/c  (3 levels deep)
            deep = os.path.join(root, "a", "b", "c")
            os.makedirs(deep)

            found = PythonModuleAnalyzerLocal._find_config_in_ancestors(deep)
            assert found is not None
            assert os.path.basename(found) == "pyproject.toml"
            assert os.path.normcase(found) == os.path.normcase(cfg)

    def test_find_config_in_ancestors_respects_max_depth(self):
        """_find_config_in_ancestors stops at max_depth."""
        with tempfile.TemporaryDirectory() as root:
            cfg = os.path.join(root, "pyproject.toml")
            with open(cfg, "w") as f:
                f.write("[project]\n")

            deep = os.path.join(root, "a", "b", "c", "d", "e", "f")
            os.makedirs(deep)

            # max_depth=2 should NOT reach root from f/
            assert PythonModuleAnalyzerLocal._find_config_in_ancestors(
                deep, max_depth=2
            ) is None

    def test_find_config_in_ancestors_returns_none_when_absent(self):
        """_find_config_in_ancestors returns None when no config exists."""
        with tempfile.TemporaryDirectory() as root:
            deep = os.path.join(root, "a", "b")
            os.makedirs(deep)

            assert PythonModuleAnalyzerLocal._find_config_in_ancestors(deep) is None

    def test_analyze_local_deep_subpackage_finds_ancestor_config(self, analyzer):
        """analyze_local on a deep subpackage finds pyproject.toml in ancestor."""
        with tempfile.TemporaryDirectory() as root:
            with open(os.path.join(root, "pyproject.toml"), "w") as f:
                f.write(
                    '[project]\nname = "deep-pkg"\n'
                    'version = "1.0.0"\nrequires-python = ">=3.8"\n'
                )
            sub = os.path.join(root, "pkg", "sub")
            os.makedirs(sub)
            with open(os.path.join(sub, "__init__.py"), "w") as f:
                f.write("")
            with open(os.path.join(sub, "module.py"), "w") as f:
                f.write("class DeepClass:\n    pass\n")

            result = analyzer.analyze_local(sub)
            assert isinstance(result, bytes)
            assert len(result) > 0

    # ------------------------------------------------------------------
    # Fix 4: globals skipped when type_filter is active
    # ------------------------------------------------------------------
    def test_analyze_local_type_filter_skips_globals(self, analyzer):
        """When type_filter is active, global functions/vars are not in result."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with open(os.path.join(temp_dir, "pyproject.toml"), "w") as f:
                f.write(
                    '[project]\nname = "globals-test"\n'
                    'version = "1.0.0"\nrequires-python = ">=3.8"\n'
                )
            with open(os.path.join(temp_dir, "__init__.py"), "w") as f:
                f.write("")
            with open(os.path.join(temp_dir, "module.py"), "w") as f:
                f.write(
                    "class TargetClass:\n    pass\n\n"
                    "def global_func():\n    return 1\n\n"
                    "GLOBAL_VAR = 42\n"
                )

            result_filtered = analyzer.analyze_local(temp_dir, "*TargetClass*")
            result_all = analyzer.analyze_local(temp_dir, "")

            # Filtered result should be smaller (no globals)
            assert len(result_filtered) < len(result_all)

    def test_local_temp_dir_creation(self):
        """Test that local_temp_dir is created inside a 'gma-python' subdirectory."""
        custom_temp = os.path.join(tempfile.gettempdir(), "test_analyzer_temp_12345")
        expected_dir = os.path.join(custom_temp, "gma-python")

        try:
            os.environ["LOCAL_TEMP_DIR"] = custom_temp

            if os.path.exists(custom_temp):
                shutil.rmtree(custom_temp)

            analyzer = PythonModuleAnalyzerLocal()

            assert analyzer.local_temp_dir == expected_dir
            assert os.path.exists(expected_dir)

        finally:
            del os.environ["LOCAL_TEMP_DIR"]
            if os.path.exists(custom_temp):
                shutil.rmtree(custom_temp, ignore_errors=True)
