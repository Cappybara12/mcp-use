"""Regenerate shared inheritance UGM CSV for Python runtime."""

from __future__ import annotations

import os
from pathlib import Path

from moduleanalyzer.src.core.handler.module_analyzer_local import PythonModuleAnalyzerLocal

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "test_fixtures" / "inheritance_test"
CSV_OUTPUT = (
    Path(__file__).resolve().parents[5]
    / "graftcode-code-generator"
    / "resources"
    / "tests"
    / "by-source"
    / "python"
    / "inheritance_bytes.csv"
)


def main() -> None:
    analyzed_bytes = PythonModuleAnalyzerLocal().analyze_local(str(FIXTURE_DIR))
    CSV_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    CSV_OUTPUT.write_text(
        "\n".join(str(byte) for byte in analyzed_bytes),
        encoding="utf-8",
    )
    print(f"Regenerated {CSV_OUTPUT} ({len(analyzed_bytes)} bytes)")


if __name__ == "__main__":
    main()
