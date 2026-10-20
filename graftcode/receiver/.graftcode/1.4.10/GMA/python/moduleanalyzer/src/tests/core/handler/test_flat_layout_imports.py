"""Regression tests for flat-layout Python projects (no ``__init__.py``).

Reproduces the following scenario:

    <root>/src/
        billing_service.py   # imports sibling ``price_calculator``
        price_calculator.py  # only imports stdlib

Without the fix, :meth:`InterfaceAnalyzer._return_classes_from_file` (and its
``LibraryAnalyzer`` counterpart) took the "standalone file" branch for every
file in ``src/`` because no ``__init__.py`` was present, but never added the
containing directory to ``sys.path``. As a result:

* ``price_calculator.py`` loaded fine (stdlib-only imports).
* ``billing_service.py`` raised ``ModuleNotFoundError`` on
  ``from price_calculator import EnergyPriceCalculator`` and was silently
  dropped, because the import happens *before* the class body is executed.

The fix adds the file's directory to ``sys.path`` in the standalone branch
and guards ``sys.path`` with a save/restore pattern so the mutation doesn't
leak to callers.
"""

import os
import shutil
import sys
import tempfile
from textwrap import dedent
from typing import Iterator, Tuple

import pytest

from moduleanalyzer.src.core.handler.analysis.library_analyzer import LibraryAnalyzer
from moduleanalyzer.src.core.handler.interface_analyzer import InterfaceAnalyzer
from moduleanalyzer.src.core.handler.module_analyzer_local import (
    PythonModuleAnalyzerLocal,
)

# Name of the package init file used by `_create_init_files` in the workdir
# copy. Referenced by tests that assert the user's source tree is unchanged.
INIT_PY_FILE = "__init__.py"

# Module names dynamically registered in sys.modules by the analyzers during
# these tests. They must be cleaned up between tests so the test run does not
# pollute (or get polluted by) sibling test modules.
_BILLING_MODULES = ("price_calculator", "billing_service")
_REPORT_MODULES = ("math_utils", "a_report")


def _cleanup_sys_modules(names: Tuple[str, ...]) -> None:
    for name in names:
        sys.modules.pop(name, None)


@pytest.fixture
def flat_billing_project() -> Iterator[Tuple[str, str, str]]:
    """Flat ``src/`` layout reproducing the original user-reported scenario.

    :yields: Tuple ``(src_dir, billing_path, price_path)``.
    """
    _cleanup_sys_modules(_BILLING_MODULES)
    tmp = tempfile.mkdtemp(prefix="gma_flat_layout_")
    src = os.path.join(tmp, "src")
    os.makedirs(src)

    price_path = os.path.join(src, "price_calculator.py")
    with open(price_path, "w", encoding="utf-8") as f:
        f.write(
            dedent(
                """
                import random


                class EnergyPriceCalculator:
                    @staticmethod
                    def get_price() -> int:
                        return random.randint(100, 104)
                """
            ).lstrip()
        )

    billing_path = os.path.join(src, "billing_service.py")
    with open(billing_path, "w", encoding="utf-8") as f:
        f.write(
            dedent(
                """
                from price_calculator import EnergyPriceCalculator


                class BillingService:
                    @staticmethod
                    def calculate_bill(kwh_used: int) -> int:
                        price = EnergyPriceCalculator.get_price()
                        return kwh_used * price
                """
            ).lstrip()
        )

    try:
        yield src, billing_path, price_path
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        _cleanup_sys_modules(_BILLING_MODULES)


@pytest.fixture
def flat_report_project() -> Iterator[Tuple[str, str, str]]:
    """Flat layout variant exercising global functions/variables, not classes.

    Filenames are chosen so the *importing* file (``a_report.py``) is walked
    **before** the imported one (``math_utils.py``) in alphabetical order.
    This guarantees the analyzer cannot accidentally succeed via a
    pre-populated ``sys.modules`` cache from an earlier file in the walk.

    :yields: Tuple ``(src_dir, report_path, math_utils_path)``.
    """
    _cleanup_sys_modules(_REPORT_MODULES)
    tmp = tempfile.mkdtemp(prefix="gma_flat_globals_")
    src = os.path.join(tmp, "src")
    os.makedirs(src)

    math_path = os.path.join(src, "math_utils.py")
    with open(math_path, "w", encoding="utf-8") as f:
        f.write(
            dedent(
                """
                PI = 3.14


                def multiplier(x: int) -> int:
                    return x * 2
                """
            ).lstrip()
        )

    report_path = os.path.join(src, "a_report.py")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(
            dedent(
                """
                from math_utils import multiplier


                TITLE = "Report"


                def format_report(x: int) -> str:
                    return f"{TITLE}: {multiplier(x)}"
                """
            ).lstrip()
        )

    try:
        yield src, report_path, math_path
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        _cleanup_sys_modules(_REPORT_MODULES)


class TestInterfaceAnalyzerFlatLayout:
    """InterfaceAnalyzer must discover every class in a flat sibling-import layout."""

    def test_directory_scan_discovers_both_classes(self, flat_billing_project):
        """Regression: both classes must be returned.

        Previously ``BillingService`` was dropped due to
        ``ModuleNotFoundError: No module named 'price_calculator'`` raised
        inside ``billing_service.py`` during ``exec_module``.
        """
        src, _billing, _price = flat_billing_project

        classes = InterfaceAnalyzer.return_classes_from_py(src)
        names = {cls.__name__ for cls in classes}

        assert (
            "EnergyPriceCalculator" in names
        ), f"EnergyPriceCalculator (stdlib-only) missing from {names}"
        assert "BillingService" in names, (
            f"BillingService missing from {names}; this is the regression "
            "the fix addresses."
        )

    def test_single_file_with_sibling_import_returns_class(self, flat_billing_project):
        """Loading the importing file alone must also work."""
        _src, billing_path, _price = flat_billing_project

        classes = InterfaceAnalyzer._return_classes_from_file(billing_path)
        names = [cls.__name__ for cls in classes]

        assert names == ["BillingService"]

    def test_sys_path_is_restored(self, flat_billing_project):
        """``sys.path`` must not leak the project dir after analysis."""
        src, _billing, _price = flat_billing_project
        snapshot = list(sys.path)

        InterfaceAnalyzer.return_classes_from_py(src)

        assert sys.path == snapshot, (
            "sys.path leaked after flat-layout analysis: "
            f"{set(sys.path) - set(snapshot)!r}"
        )


class TestLibraryAnalyzerFlatLayout:
    """LibraryAnalyzer must extract globals from flat-layout sibling-import files."""

    @pytest.fixture
    def analyzer(self) -> LibraryAnalyzer:
        return LibraryAnalyzer()

    def test_extract_from_single_file_handles_sibling_import(
        self, analyzer, flat_report_project
    ):
        """Globals of the importing file must be extracted, not lost to ImportError."""
        _src, report_path, _math_path = flat_report_project

        functions, variables = analyzer._extract_from_single_file(report_path)
        function_names = {fn.__name__ for fn in functions}

        assert "format_report" in function_names, (
            f"format_report missing from {function_names}; "
            "sibling import likely failed."
        )
        assert (
            "TITLE" in variables
        ), f"TITLE missing from {variables}; sibling import likely failed."

    def test_extract_from_directory_handles_sibling_imports(
        self, analyzer, flat_report_project
    ):
        """Directory-level extraction aggregates globals from both files."""
        src, _report, _math = flat_report_project

        functions, variables = analyzer._extract_from_directory(src)
        function_names = {fn.__name__ for fn in functions}

        assert {
            "multiplier",
            "format_report",
        } <= function_names, (
            f"Expected multiplier and format_report in {function_names}"
        )
        assert {"PI", "TITLE"} <= set(
            variables
        ), f"Expected PI and TITLE in {variables}"

    def test_sys_path_is_restored(self, analyzer, flat_report_project):
        """``sys.path`` must be restored after single-file extraction."""
        _src, report_path, _math_path = flat_report_project
        snapshot = list(sys.path)

        analyzer._extract_from_single_file(report_path)

        assert sys.path == snapshot, (
            "sys.path leaked after flat-layout extraction: "
            f"{set(sys.path) - set(snapshot)!r}"
        )


# ---------------------------------------------------------------------------
# End-to-end: PythonModuleAnalyzerLocal.analyze_local on flat projects
# ---------------------------------------------------------------------------
#
# `analyze_local` copies the user's source into a disposable workdir before
# analysing it. The fix adds an `_create_init_files` pass on that copy so
# Python treats the flat layout as a package, which is the only way to make
# *relative* imports (`from .x import Y`) resolve:
#
#     user's src/                  workdir copy/           `__module__`
#     --------------               ---------------         ------------
#     src/billing.py   ── copy ──▶ src/billing.py    ─┐
#     src/price.py                 src/price.py       │─▶ `src.billing`
#                                  src/__init__.py <── synthesized
#                                                      `src.price`
#
# The original `src/` tree is never touched, which we verify below.


_RELATIVE_MODULES = (
    "price_calculator",
    "billing_service",
    "src.price_calculator",
    "src.billing_service",
)


def _make_flat_project(tmp: str, billing_import: str) -> str:
    """Write a minimal flat-layout project with a configurable import style.

    :param tmp: Existing temp directory to populate.
    :param billing_import: Exact import statement placed at the top of
        ``billing_service.py`` (e.g. ``from price_calculator import X`` or
        ``from .price_calculator import X``).
    :return: Absolute path to the ``src/`` directory ready for
        :meth:`PythonModuleAnalyzerLocal.analyze_local`.
    """
    src = os.path.join(tmp, "src")
    os.makedirs(src)

    with open(os.path.join(src, "pyproject.toml"), "w", encoding="utf-8") as f:
        f.write(
            dedent(
                """
                [project]
                name = "flat-demo"
                version = "0.0.1"
                requires-python = ">=3.8"
                """
            ).lstrip()
        )

    with open(os.path.join(src, "price_calculator.py"), "w", encoding="utf-8") as f:
        f.write(
            dedent(
                """
                import random


                class EnergyPriceCalculator:
                    @staticmethod
                    def get_price() -> int:
                        return random.randint(100, 104)
                """
            ).lstrip()
        )

    with open(os.path.join(src, "billing_service.py"), "w", encoding="utf-8") as f:
        f.write(
            dedent(
                f"""
                {billing_import}


                class BillingService:
                    @staticmethod
                    def calculate_bill(kwh_used: int) -> int:
                        price = EnergyPriceCalculator.get_price()
                        return kwh_used * price
                """
            ).lstrip()
        )

    return src


@pytest.fixture
def flat_absolute_sibling_project() -> Iterator[str]:
    """Flat layout with the *bare absolute* sibling import pattern.

    Reproduces the original user-reported scenario verbatim:

        src/
            billing_service.py   # from price_calculator import ...
            price_calculator.py

    Python 3 treats ``from price_calculator import X`` as an absolute
    import; once ``_create_init_files`` promotes ``src/`` to a package,
    resolution must still succeed so the analyser can pull
    ``BillingService`` into the UGM.
    """
    _cleanup_sys_modules(_RELATIVE_MODULES)
    tmp = tempfile.mkdtemp(prefix="gma_flat_absolute_")
    try:
        yield _make_flat_project(
            tmp, "from price_calculator import EnergyPriceCalculator"
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        _cleanup_sys_modules(_RELATIVE_MODULES)


@pytest.fixture
def flat_relative_import_project() -> Iterator[str]:
    """Flat layout using explicit relative imports (``from .x import Y``)."""
    _cleanup_sys_modules(_RELATIVE_MODULES)
    tmp = tempfile.mkdtemp(prefix="gma_flat_relative_")
    try:
        yield _make_flat_project(
            tmp, "from .price_calculator import EnergyPriceCalculator"
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        _cleanup_sys_modules(_RELATIVE_MODULES)


class TestAnalyzeLocalFlatAbsoluteSiblingImport:
    """End-to-end: the original user-reported scenario.

    Flat ``src/`` with ``billing_service.py`` doing
    ``from price_calculator import EnergyPriceCalculator`` (no leading dot).

    After ``analyze_local`` promotes the flat layout to a package via
    ``_create_init_files``, Python 3 would normally reject this bare
    absolute sibling import. The fix adds ``package_path`` itself to
    ``sys.path`` (not only ``parent_of_package``) so such imports keep
    resolving, matching the standalone-branch behaviour pre-auto-init.
    """

    @pytest.fixture
    def analyzer(self) -> PythonModuleAnalyzerLocal:
        return PythonModuleAnalyzerLocal()

    def test_analyze_local_discovers_both_classes(
        self, analyzer, flat_absolute_sibling_project
    ):
        """Both ``BillingService`` and ``EnergyPriceCalculator`` must be in the UGM."""
        src = flat_absolute_sibling_project

        result = analyzer.analyze_local(src)

        assert isinstance(result, bytes) and len(result) > 0
        assert (
            b"EnergyPriceCalculator" in result
        ), "EnergyPriceCalculator is stdlib-only and should always be found."
        assert b"BillingService" in result, (
            "BillingService missing from UGM payload; bare sibling import "
            "failed after flat layout was promoted to a package."
        )


class TestAnalyzeLocalFlatRelativeImports:
    """End-to-end: ``analyze_local`` must handle flat layouts with ``.`` imports.

    Without auto-init in the workdir copy, Python raises
    ``ImportError: attempted relative import with no known parent package``
    inside ``billing_service.py`` during ``exec_module``, silently dropping
    ``BillingService``. The fix synthesises ``__init__.py`` files in the
    workdir copy so the layout is seen as a real package.
    """

    @pytest.fixture
    def analyzer(self) -> PythonModuleAnalyzerLocal:
        return PythonModuleAnalyzerLocal()

    def test_analyze_local_discovers_both_classes(
        self, analyzer, flat_relative_import_project
    ):
        """Result payload must contain both class names."""
        src = flat_relative_import_project

        result = analyzer.analyze_local(src)

        assert isinstance(result, bytes) and len(result) > 0

        # Class names appear in the serialized UGM (protobuf encodes strings
        # as UTF-8 length-prefixed fields; substring match is sufficient to
        # prove the class was loaded and registered).
        assert (
            b"EnergyPriceCalculator" in result
        ), "EnergyPriceCalculator is stdlib-only and should always be found."
        assert b"BillingService" in result, (
            "BillingService missing from UGM payload; relative import likely "
            "failed inside the workdir copy."
        )

    def test_analyze_local_does_not_modify_user_source(
        self, analyzer, flat_relative_import_project
    ):
        """Auto-init must happen in the workdir copy, never in user's tree.

        Guards against a regression where ``_create_init_files`` would be
        pointed at the user's path instead of ``workdir_module_path``.
        """
        src = flat_relative_import_project
        original_entries = set(os.listdir(src))

        analyzer.analyze_local(src)

        after_entries = set(os.listdir(src))
        assert after_entries == original_entries, (
            f"User's source was modified: added={after_entries - original_entries!r}, "
            f"removed={original_entries - after_entries!r}"
        )
        assert not os.path.exists(os.path.join(src, INIT_PY_FILE)), (
            "An __init__.py was created in the user's source directory; "
            "auto-init must be confined to the disposable workdir copy."
        )

    def test_analyze_local_reanalysis_same_basename_still_works(
        self, analyzer, flat_relative_import_project
    ):
        """Back-to-back analyses of different ``src/`` trees must both succeed.

        Long-lived services may analyse many projects in the same process.
        Because ``_create_init_files`` turns every flat layout into a
        package named after its directory (commonly ``src``), the first
        analysis registers a ``src`` package in ``sys.modules``. Without
        path-aware re-registration in ``_setup_package_in_sys_modules``,
        the second analysis would reuse that stale entry and fail to
        resolve ``from .sibling import X`` against the new source tree.
        """
        first_src = flat_relative_import_project

        first_result = analyzer.analyze_local(first_src)
        assert b"BillingService" in first_result

        second_tmp = tempfile.mkdtemp(prefix="gma_flat_relative_second_")
        try:
            second_src = os.path.join(second_tmp, "src")
            os.makedirs(second_src)

            with open(
                os.path.join(second_src, "pyproject.toml"), "w", encoding="utf-8"
            ) as f:
                f.write(
                    dedent(
                        """
                        [project]
                        name = "flat-relative-demo-2"
                        version = "0.0.2"
                        requires-python = ">=3.8"
                        """
                    ).lstrip()
                )
            with open(
                os.path.join(second_src, "greeter.py"), "w", encoding="utf-8"
            ) as f:
                f.write('GREETING = "hi"\n')
            with open(os.path.join(second_src, "api.py"), "w", encoding="utf-8") as f:
                f.write(
                    dedent(
                        """
                        from .greeter import GREETING


                        class PublicAPI:
                            @staticmethod
                            def hello() -> str:
                                return GREETING
                        """
                    ).lstrip()
                )

            second_result = analyzer.analyze_local(second_src)

            assert b"PublicAPI" in second_result, (
                "Second analysis silently lost PublicAPI; sys.modules['src'] "
                "cached from the first run likely blocked package re-registration."
            )
        finally:
            shutil.rmtree(second_tmp, ignore_errors=True)
            sys.modules.pop("src.api", None)
            sys.modules.pop("src.greeter", None)
            sys.modules.pop("src", None)
