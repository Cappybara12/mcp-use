"""Tests for framework module detection used in inheritance filtering."""

from __future__ import annotations

from abc import ABC

from moduleanalyzer.src.core.utils.framework_module_helper import is_framework_module


def test_is_framework_module_detects_abc_and_typing_modules() -> None:
    assert is_framework_module("abc") is True
    assert is_framework_module("typing") is True
    assert is_framework_module("typing_extensions") is True
    assert is_framework_module("collections.abc") is True


def test_is_framework_module_allows_user_package_modules() -> None:
    assert is_framework_module("inheritance_test.inheritance_test") is False
    assert is_framework_module("my_package.submodule") is False


def test_abc_class_is_framework_module() -> None:
    assert is_framework_module(ABC.__module__) is True
