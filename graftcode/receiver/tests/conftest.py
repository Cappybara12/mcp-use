import os
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@pytest.fixture()
def service(tmp_path, monkeypatch):
    """Receiver in demo mode against a throwaway copy of the sample data."""
    monkeypatch.setenv("WAYZYY_WRITER_DIR", str(tmp_path / "no-writer"))
    monkeypatch.setenv("WAYZYY_SCANNER_DIR", str(tmp_path / "no-scanner"))
    data = tmp_path / "sample_data"
    shutil.copytree(ROOT / "sample_data", data)
    monkeypatch.setenv("WAYZYY_DRAFTS_DIR", str(data / "drafts"))
    monkeypatch.setenv("WAYZYY_REVIEW_DIR", str(data / "review"))
    for mod in [m for m in sys.modules if m.startswith("article_receiver")]:
        del sys.modules[mod]
    from article_receiver.service import ArticlePipelineService
    return ArticlePipelineService()


@pytest.fixture()
def service_with_config(tmp_path, monkeypatch):
    """Factory: build a demo-mode receiver using a given PIPELINE_CONFIG file."""

    def make(config_path):
        monkeypatch.setenv("WAYZYY_WRITER_DIR", str(tmp_path / "no-writer"))
        monkeypatch.setenv("WAYZYY_SCANNER_DIR", str(tmp_path / "no-scanner"))
        monkeypatch.delenv("WAYZYY_DRAFTS_DIR", raising=False)
        monkeypatch.delenv("WAYZYY_REVIEW_DIR", raising=False)
        # Work on a throwaway copy of the sample data the config would use, so tests
        # never write into the repository.
        import yaml
        cfg = yaml.safe_load(Path(config_path).read_text(encoding="utf-8")) if Path(config_path).is_file() else {}
        if not isinstance(cfg, dict):
            cfg = {}  # invalid configs are rejected by the receiver itself
        source = (Path(config_path).parent / cfg["data_dir"]) if cfg and cfg.get("data_dir") else ROOT / "sample_data"
        data = tmp_path / "data"
        shutil.copytree(source, data)
        monkeypatch.setenv("WAYZYY_SAMPLE_DIR", str(data))
        monkeypatch.setenv("PIPELINE_CONFIG", str(config_path))
        for mod in [m for m in sys.modules if m.startswith("article_receiver")]:
            del sys.modules[mod]
        from article_receiver.service import ArticlePipelineService
        return ArticlePipelineService()

    return make
