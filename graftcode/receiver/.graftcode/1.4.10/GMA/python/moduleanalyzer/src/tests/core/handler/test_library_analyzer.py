"""Tests for LibraryAnalyzer - metadata extraction from .whl and config files."""

import os
import shutil
import tempfile

import pytest

from moduleanalyzer.src.core.handler.analysis.library_analyzer import LibraryAnalyzer

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def library_analyzer() -> LibraryAnalyzer:
    """Create a LibraryAnalyzer instance."""
    return LibraryAnalyzer()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def pyproject_toml_dir(temp_dir):
    """Create a directory with pyproject.toml."""
    content = """[project]
name = "my-test-package"
version = "1.2.3"
requires-python = ">=3.8"
"""
    with open(os.path.join(temp_dir, "pyproject.toml"), "w") as f:
        f.write(content)

    # Create a Python file
    with open(os.path.join(temp_dir, "main.py"), "w") as f:
        f.write("def hello(): pass\n")

    return temp_dir


@pytest.fixture
def pyproject_toml_poetry_dir(temp_dir):
    """Create a directory with pyproject.toml using Poetry format."""
    content = """[tool.poetry]
name = "poetry-package"
version = "4.5.6"
python = "^3.9"
"""
    with open(os.path.join(temp_dir, "pyproject.toml"), "w") as f:
        f.write(content)

    return temp_dir


@pytest.fixture
def setup_cfg_dir(temp_dir):
    """Create a directory with setup.cfg."""
    content = """[metadata]
name = setupcfg-package
version = 2.0.0

[options]
python_requires = >=3.7
"""
    with open(os.path.join(temp_dir, "setup.cfg"), "w") as f:
        f.write(content)

    return temp_dir


@pytest.fixture
def setup_py_dir(temp_dir):
    """Create a directory with setup.py."""
    content = """from setuptools import setup

setup(
    name="setuppy-package",
    version="3.3.3",
    python_requires=">=3.10",
)
"""
    with open(os.path.join(temp_dir, "setup.py"), "w") as f:
        f.write(content)

    return temp_dir


@pytest.fixture
def whl_file_dir(temp_dir):
    """Create a directory with a mock .whl file."""
    whl_filename = "my_package-1.0.0-py311-none-any.whl"
    whl_path = os.path.join(temp_dir, whl_filename)
    # Create empty file to simulate .whl
    with open(whl_path, "w") as f:
        f.write("")
    return temp_dir


@pytest.fixture
def whl_file_cp_dir(temp_dir):
    """Create a directory with a CPython .whl file."""
    whl_filename = "another_package-2.5.0-cp39-cp39-win_amd64.whl"
    whl_path = os.path.join(temp_dir, whl_filename)
    with open(whl_path, "w") as f:
        f.write("")
    return temp_dir


@pytest.fixture
def no_config_dir(temp_dir):
    """Create a directory without any config files."""
    with open(os.path.join(temp_dir, "module.py"), "w") as f:
        f.write("x = 1\n")
    return temp_dir


@pytest.fixture
def dist_info_dir(temp_dir):
    """Create a directory with .dist-info/METADATA (no config files)."""
    # Create a Python module file
    with open(os.path.join(temp_dir, "module.py"), "w") as f:
        f.write("x = 1\n")

    # Create .dist-info directory with METADATA file
    dist_info_path = os.path.join(temp_dir, "dist_info_package-1.5.0.dist-info")
    os.makedirs(dist_info_path)

    metadata_content = """\
Metadata-Version: 2.1
Name: dist-info-package
Version: 1.5.0
Summary: A test package with dist-info
Requires-Python: >=3.9
"""
    with open(os.path.join(dist_info_path, "METADATA"), "w") as f:
        f.write(metadata_content)

    return temp_dir


# =============================================================================
# Tests for .whl file extraction
# =============================================================================


class TestWhlExtraction:
    """Tests for .whl file metadata extraction."""

    def test_find_first_whl_file(self, library_analyzer, whl_file_dir):
        """Test finding .whl file in directory."""
        result = library_analyzer._find_first_whl_file(whl_file_dir)
        assert result == "my_package-1.0.0-py311-none-any.whl"

    def test_find_first_whl_file_not_found(self, library_analyzer, no_config_dir):
        """Test when no .whl file exists."""
        result = library_analyzer._find_first_whl_file(no_config_dir)
        assert result is None

    def test_extract_library_name_from_whl(self, library_analyzer):
        """Test extracting library name from .whl filename."""
        assert (
            library_analyzer._extract_library_name_from_whl(
                "my_package-1.0.0-py3-none-any.whl"
            )
            == "my_package"
        )

    def test_extract_library_name_from_whl_with_underscore(self, library_analyzer):
        """Test extracting library name with underscores."""
        assert (
            library_analyzer._extract_library_name_from_whl(
                "sdncenter_currency_converter-0.3.7-py3-none-any.whl"
            )
            == "sdncenter_currency_converter"
        )

    def test_extract_version_from_whl(self, library_analyzer):
        """Test extracting version from .whl filename."""
        assert (
            library_analyzer._extract_version_from_whl(
                "my_package-1.0.0-py3-none-any.whl"
            )
            == "1.0.0"
        )

    def test_extract_version_from_whl_complex(self, library_analyzer):
        """Test extracting complex version from .whl filename."""
        assert (
            library_analyzer._extract_version_from_whl(
                "package-2.5.10-cp39-cp39-win_amd64.whl"
            )
            == "2.5.10"
        )

    def test_extract_python_version_from_whl_py3(self, library_analyzer):
        """Test extracting Python version 'py3'."""
        result = library_analyzer._extract_python_version_from_whl(
            "package-1.0.0-py3-none-any.whl"
        )
        assert result == "3"

    def test_extract_python_version_from_whl_py38(self, library_analyzer):
        """Test extracting Python version 'py38'."""
        result = library_analyzer._extract_python_version_from_whl(
            "package-1.0.0-py38-none-any.whl"
        )
        assert result == "3.8"

    def test_extract_python_version_from_whl_py311(self, library_analyzer):
        """Test extracting Python version 'py311'."""
        result = library_analyzer._extract_python_version_from_whl(
            "package-1.0.0-py311-none-any.whl"
        )
        assert result == "3.11"

    def test_extract_python_version_from_whl_cp39(self, library_analyzer):
        """Test extracting Python version 'cp39' (CPython)."""
        result = library_analyzer._extract_python_version_from_whl(
            "package-1.0.0-cp39-cp39-win_amd64.whl"
        )
        assert result == "3.9"

    def test_extract_python_version_from_whl_cp311(self, library_analyzer):
        """Test extracting Python version 'cp311' (CPython)."""
        result = library_analyzer._extract_python_version_from_whl(
            "package-1.0.0-cp311-cp311-manylinux1_x86_64.whl"
        )
        assert result == "3.11"

    def test_extract_python_version_from_whl_py2_py3(self, library_analyzer):
        """Test extracting Python version from universal wheel 'py2.py3'."""
        result = library_analyzer._extract_python_version_from_whl(
            "package-1.0.0-py2.py3-none-any.whl"
        )
        assert result == "3"  # Takes the last (highest) version


# =============================================================================
# Tests for config file extraction
# =============================================================================


class TestConfigFileExtraction:
    """Tests for config file metadata extraction."""

    def test_find_config_file_pyproject(self, library_analyzer, pyproject_toml_dir):
        """Test finding pyproject.toml."""
        result = library_analyzer._find_config_file(pyproject_toml_dir)
        assert result is not None
        assert result[1] == "pyproject.toml"

    def test_find_config_file_setup_cfg(self, library_analyzer, setup_cfg_dir):
        """Test finding setup.cfg."""
        result = library_analyzer._find_config_file(setup_cfg_dir)
        assert result is not None
        assert result[1] == "setup.cfg"

    def test_find_config_file_setup_py(self, library_analyzer, setup_py_dir):
        """Test finding setup.py."""
        result = library_analyzer._find_config_file(setup_py_dir)
        assert result is not None
        assert result[1] == "setup.py"

    def test_find_config_file_not_found(self, library_analyzer, no_config_dir):
        """Test when no config file exists."""
        result = library_analyzer._find_config_file(no_config_dir)
        assert result is None

    def test_extract_from_pyproject_toml(self, library_analyzer, pyproject_toml_dir):
        """Test extracting metadata from pyproject.toml."""
        metadata = library_analyzer._extract_metadata_from_config(pyproject_toml_dir)

        assert metadata["name"] == "my-test-package"
        assert metadata["version"] == "1.2.3"
        assert metadata["python_requires"] == ">=3.8"

    def test_extract_from_pyproject_toml_poetry(
        self, library_analyzer, pyproject_toml_poetry_dir
    ):
        """Test extracting metadata from pyproject.toml with Poetry format."""
        metadata = library_analyzer._extract_metadata_from_config(
            pyproject_toml_poetry_dir
        )

        assert metadata["name"] == "poetry-package"
        assert metadata["version"] == "4.5.6"
        assert metadata["python_requires"] == "^3.9"

    def test_extract_from_setup_cfg(self, library_analyzer, setup_cfg_dir):
        """Test extracting metadata from setup.cfg."""
        metadata = library_analyzer._extract_metadata_from_config(setup_cfg_dir)

        assert metadata["name"] == "setupcfg-package"
        assert metadata["version"] == "2.0.0"
        assert metadata["python_requires"] == ">=3.7"

    def test_extract_from_setup_py(self, library_analyzer, setup_py_dir):
        """Test extracting metadata from setup.py."""
        metadata = library_analyzer._extract_metadata_from_config(setup_py_dir)

        assert metadata["name"] == "setuppy-package"
        assert metadata["version"] == "3.3.3"
        assert metadata["python_requires"] == ">=3.10"

    def test_extract_metadata_no_config_file(self, library_analyzer, no_config_dir):
        """Test that FileNotFoundError is raised when no config file exists."""
        with pytest.raises(FileNotFoundError) as exc_info:
            library_analyzer._extract_metadata_from_config(no_config_dir)

        assert "No config file" in str(exc_info.value)


# =============================================================================
# Tests for error handling (no fallbacks)
# =============================================================================


class TestNoFallbacks:
    """Tests to ensure no default fallback values are used."""

    def test_add_library_name_raises_without_whl(self, library_analyzer, no_config_dir):
        """Test that add_library_name raises FileNotFoundError without .whl."""
        from graftcode_protocol.enums.runtime_name import RuntimeName
        from graftcode_protocol.enums.unified_graft_model_type import (
            UnifiedGraftModelType,
        )
        from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel

        command = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.LIBRARY, []
        )

        with pytest.raises(FileNotFoundError) as exc_info:
            library_analyzer.add_library_name(command, no_config_dir)

        assert "No .whl file found" in str(exc_info.value)

    def test_add_python_library_version_raises_without_whl(
        self, library_analyzer, no_config_dir
    ):
        """Test that add_python_library_version raises FileNotFoundError without .whl."""
        from graftcode_protocol.enums.runtime_name import RuntimeName
        from graftcode_protocol.enums.unified_graft_model_type import (
            UnifiedGraftModelType,
        )
        from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel

        command = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.LIBRARY, []
        )

        with pytest.raises(FileNotFoundError) as exc_info:
            library_analyzer.add_python_library_version(command, no_config_dir)

        assert "No .whl file found" in str(exc_info.value)

    def test_add_python_runtime_version_raises_without_whl(
        self, library_analyzer, no_config_dir
    ):
        """Test that add_python_runtime_version raises FileNotFoundError without .whl."""
        from graftcode_protocol.enums.runtime_name import RuntimeName
        from graftcode_protocol.enums.unified_graft_model_type import (
            UnifiedGraftModelType,
        )
        from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel

        command = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.LIBRARY, []
        )

        with pytest.raises(FileNotFoundError) as exc_info:
            library_analyzer.add_python_runtime_version(command, no_config_dir)

        assert "No .whl file found" in str(exc_info.value)

    def test_create_base_structured_command_raises_without_metadata_source(
        self, library_analyzer, no_config_dir
    ):
        """Test that _create_base_structured_command raises without any metadata source."""
        with pytest.raises(ValueError) as exc_info:
            library_analyzer._create_base_structured_command(no_config_dir)

        assert "Could not extract library metadata" in str(exc_info.value)


# =============================================================================
# Tests for local analysis (_create_base_structured_command_local)
# =============================================================================


class TestLocalAnalysis:
    """Tests for local analysis using config files."""

    def test_create_base_structured_command_local_pyproject(
        self, library_analyzer, pyproject_toml_dir
    ):
        """Test creating structured command from pyproject.toml."""
        result = library_analyzer._create_base_structured_command_local(
            pyproject_toml_dir
        )

        assert result.payload[1] == "my-test-package"
        assert result.payload[2] == "1.2.3"
        assert result.payload[3] == "Python >=3.8"

    def test_create_base_structured_command_local_setup_cfg(
        self, library_analyzer, setup_cfg_dir
    ):
        """Test creating structured command from setup.cfg."""
        result = library_analyzer._create_base_structured_command_local(setup_cfg_dir)

        assert result.payload[1] == "setupcfg-package"
        assert result.payload[2] == "2.0.0"
        assert result.payload[3] == "Python >=3.7"

    def test_create_base_structured_command_local_setup_py(
        self, library_analyzer, setup_py_dir
    ):
        """Test creating structured command from setup.py."""
        result = library_analyzer._create_base_structured_command_local(setup_py_dir)

        assert result.payload[1] == "setuppy-package"
        assert result.payload[2] == "3.3.3"
        assert result.payload[3] == "Python >=3.10"

    def test_create_base_structured_command_local_raises_without_metadata_source(
        self, library_analyzer, no_config_dir
    ):
        """Test that _create_base_structured_command_local raises without any metadata source."""
        with pytest.raises(FileNotFoundError) as exc_info:
            library_analyzer._create_base_structured_command_local(no_config_dir)

        assert "No metadata source found" in str(exc_info.value)

    def test_create_base_structured_command_local_with_dist_info_fallback(
        self, library_analyzer, dist_info_dir
    ):
        """Test that _create_base_structured_command_local uses .dist-info/METADATA as fallback."""
        result = library_analyzer._create_base_structured_command_local(dist_info_dir)

        # Verify metadata was extracted from .dist-info/METADATA
        assert result.payload[1] == "dist-info-package"
        assert result.payload[2] == "1.5.0"
        assert result.payload[3] == "Python >=3.9"


# =============================================================================
# Tests with real test resources
# =============================================================================


class TestWithRealResources:
    """Tests using actual test resource directories."""

    @pytest.mark.skipif(
        not os.path.exists(
            "moduleanalyzer/test_resources/local_project_pyproject/pyproject.toml"
        ),
        reason="Test resource not available",
    )
    def test_real_pyproject_toml(self, library_analyzer):
        """Test with real pyproject.toml test resource."""
        path = "moduleanalyzer/test_resources/local_project_pyproject"
        metadata = library_analyzer._extract_metadata_from_config(path)

        assert metadata["name"] == "test-pyproject-package"
        assert metadata["version"] == "2.1.0"
        assert metadata["python_requires"] == ">=3.8"

    @pytest.mark.skipif(
        not os.path.exists(
            "moduleanalyzer/test_resources/local_project_setup_cfg/setup.cfg"
        ),
        reason="Test resource not available",
    )
    def test_real_setup_cfg(self, library_analyzer):
        """Test with real setup.cfg test resource."""
        path = "moduleanalyzer/test_resources/local_project_setup_cfg"
        metadata = library_analyzer._extract_metadata_from_config(path)

        assert metadata["name"] == "test-setupcfg-package"
        assert metadata["version"] == "1.5.3"
        assert metadata["python_requires"] == ">=3.7"

    @pytest.mark.skipif(
        not os.path.exists(
            "moduleanalyzer/test_resources/local_project_setup_py/setup.py"
        ),
        reason="Test resource not available",
    )
    def test_real_setup_py(self, library_analyzer):
        """Test with real setup.py test resource."""
        path = "moduleanalyzer/test_resources/local_project_setup_py"
        metadata = library_analyzer._extract_metadata_from_config(path)

        assert metadata["name"] == "test-setuppy-package"
        assert metadata["version"] == "3.0.0"
        assert metadata["python_requires"] == ">=3.9"


# =============================================================================
# Additional edge case tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_extract_library_name_from_whl_simple(self, library_analyzer):
        """Test extracting library name from simple .whl filename without version."""
        result = library_analyzer._extract_library_name_from_whl("invalid.whl")
        # Simple filenames without dash return the name before .whl
        assert result == "invalid"

    def test_extract_version_from_whl_invalid(self, library_analyzer):
        """Test extracting version from invalid .whl filename."""
        result = library_analyzer._extract_version_from_whl("invalid.whl")
        assert result is None

    def test_extract_python_version_from_whl_invalid(self, library_analyzer):
        """Test extracting Python version from invalid .whl filename."""
        result = library_analyzer._extract_python_version_from_whl("invalid.whl")
        assert result is None

    def test_extract_python_version_from_whl_no_digits(self, library_analyzer):
        """Test extracting Python version when no digits in tag."""
        result = library_analyzer._extract_python_version_from_whl(
            "package-1.0.0-abc-none-any.whl"
        )
        assert result is None

    def test_get_search_directory_with_file(self, library_analyzer, temp_dir):
        """Test _get_search_directory when given a file path."""
        file_path = os.path.join(temp_dir, "test.py")
        with open(file_path, "w") as f:
            f.write("x = 1")

        result = library_analyzer._get_search_directory(file_path)
        assert result == temp_dir

    def test_get_search_directory_with_directory(self, library_analyzer, temp_dir):
        """Test _get_search_directory when given a directory path."""
        result = library_analyzer._get_search_directory(temp_dir)
        assert result == temp_dir

    def test_find_config_file_priority(self, library_analyzer, temp_dir):
        """Test that pyproject.toml has priority over setup.cfg and setup.py."""
        # Create all three config files
        with open(os.path.join(temp_dir, "pyproject.toml"), "w") as f:
            f.write('[project]\nname = "from-pyproject"\n')
        with open(os.path.join(temp_dir, "setup.cfg"), "w") as f:
            f.write("[metadata]\nname = from-setup-cfg\n")
        with open(os.path.join(temp_dir, "setup.py"), "w") as f:
            f.write('setup(name="from-setup-py")\n')

        result = library_analyzer._find_config_file(temp_dir)
        assert result is not None
        assert result[1] == "pyproject.toml"

    def test_extract_from_setup_py_with_variables(self, library_analyzer, temp_dir):
        """Test setup.py parsing with variable assignments."""
        content = """from setuptools import setup

NAME = "var-package"
VERSION = "1.0.0"

setup(
    name=NAME,
    version=VERSION,
)
"""
        with open(os.path.join(temp_dir, "setup.py"), "w") as f:
            f.write(content)

        metadata = library_analyzer._extract_metadata_from_config(temp_dir)
        # Should still work or return None values (not crash)
        assert metadata is not None

    def test_extract_from_empty_pyproject_toml(self, library_analyzer, temp_dir):
        """Test parsing empty pyproject.toml."""
        with open(os.path.join(temp_dir, "pyproject.toml"), "w") as f:
            f.write("")

        metadata = library_analyzer._extract_metadata_from_config(temp_dir)
        assert metadata["name"] is None
        assert metadata["version"] is None
        assert metadata["python_requires"] is None

    def test_extract_from_malformed_setup_cfg(self, library_analyzer, temp_dir):
        """Test parsing malformed setup.cfg."""
        with open(os.path.join(temp_dir, "setup.cfg"), "w") as f:
            f.write("not valid ini format {{{")

        # Should not crash, just return None values
        metadata = library_analyzer._extract_metadata_from_config(temp_dir)
        assert metadata is not None


class TestWhlWithDirectory:
    """Tests for .whl file handling with directories."""

    def test_add_library_name_with_whl(self, library_analyzer, whl_file_dir):
        """Test add_library_name when .whl file exists."""
        from graftcode_protocol.enums.runtime_name import RuntimeName
        from graftcode_protocol.enums.unified_graft_model_type import (
            UnifiedGraftModelType,
        )
        from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel

        command = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.LIBRARY, []
        )

        result = library_analyzer.add_library_name(command, whl_file_dir)
        assert result.payload[0] == "my_package"

    def test_add_python_library_version_with_whl(self, library_analyzer, whl_file_dir):
        """Test add_python_library_version when .whl file exists."""
        from graftcode_protocol.enums.runtime_name import RuntimeName
        from graftcode_protocol.enums.unified_graft_model_type import (
            UnifiedGraftModelType,
        )
        from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel

        command = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.LIBRARY, []
        )

        result = library_analyzer.add_python_library_version(command, whl_file_dir)
        assert result.payload[0] == "1.0.0"

    def test_add_python_runtime_version_with_whl(self, library_analyzer, whl_file_dir):
        """Test add_python_runtime_version when .whl file exists."""
        from graftcode_protocol.enums.runtime_name import RuntimeName
        from graftcode_protocol.enums.unified_graft_model_type import (
            UnifiedGraftModelType,
        )
        from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel

        command = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.LIBRARY, []
        )

        result = library_analyzer.add_python_runtime_version(command, whl_file_dir)
        assert result.payload[0] == "Python 3.11"

    def test_create_base_structured_command_with_whl(
        self, library_analyzer, whl_file_dir
    ):
        """Test _create_base_structured_command with .whl file."""
        # Create a Python file in the directory
        with open(os.path.join(whl_file_dir, "main.py"), "w") as f:
            f.write("def hello(): pass\n")

        result = library_analyzer._create_base_structured_command(whl_file_dir)

        assert result.payload[1] == "my_package"
        assert result.payload[2] == "1.0.0"
        assert result.payload[3] == "Python 3.11"
