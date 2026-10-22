"""Regression tests: draft filenames must never reach files outside the drafts folder."""
import json
import os
from pathlib import Path

import pytest


@pytest.fixture()
def drafts_dir():
    return Path(os.environ["WAYZYY_DRAFTS_DIR"])


@pytest.fixture()
def outside(tmp_path):
    """A file outside the drafts folder that must never be read or modified."""
    f = tmp_path / "outside.txt"
    f.write_text("SECRET", encoding="utf-8")
    return f


READERS = ["get_draft", "run_style_check"]


@pytest.mark.parametrize("reader", READERS)
def test_absolute_path_is_rejected(service, outside, reader):
    with pytest.raises(ValueError):
        getattr(service, reader)(str(outside))


@pytest.mark.parametrize("reader", READERS)
@pytest.mark.parametrize("name", ["../outside.txt", "../../outside.txt", "..", ".", "a/../../outside.txt", "sub/dir.md"])
def test_traversal_names_are_rejected(service, reader, name):
    with pytest.raises(ValueError):
        getattr(service, reader)(name)


@pytest.mark.parametrize("bad", ["", "   ", None, "bad\x00name.md", "back\\slash.md"])
def test_malformed_names_are_rejected(service, bad):
    with pytest.raises(ValueError):
        service.get_draft(bad)


@pytest.mark.parametrize("reader", READERS)
def test_symlink_to_outside_file_cannot_be_read(service, drafts_dir, outside, reader):
    (drafts_dir / "link.md").symlink_to(outside)
    with pytest.raises(ValueError):
        getattr(service, reader)("link.md")
    # a fuzzy name that would match the link is not a way around it either
    with pytest.raises(ValueError):
        getattr(service, reader)("link")


def test_symlink_to_outside_file_cannot_be_overwritten(service, drafts_dir, outside):
    (drafts_dir / "link.md").symlink_to(outside)
    with pytest.raises(ValueError):
        service.save_draft("link.md", "OVERWRITTEN")
    assert outside.read_text(encoding="utf-8") == "SECRET"


def test_symlinked_directory_cannot_expose_outside_files(service, drafts_dir, tmp_path):
    outside_dir = tmp_path / "outside_dir"
    outside_dir.mkdir()
    (outside_dir / "secret.md").write_text("SECRET", encoding="utf-8")
    (drafts_dir / "dirlink").symlink_to(outside_dir)
    with pytest.raises(ValueError):
        service.get_draft("dirlink/secret.md")
    with pytest.raises(ValueError):
        service.get_draft("secret.md")  # fuzzy search must not descend into the link


def test_symlink_that_stays_inside_the_folder_is_allowed(service, drafts_dir):
    (drafts_dir / "alias.md").symlink_to(drafts_dir / "2026-01-01_sample-assagao-cafe-guide.md")
    assert "Assagao" in json.loads(service.get_draft("alias.md"))["content"]


def test_glob_characters_are_not_wildcards(service):
    for pattern in ["*", "?", "[a-z]*", "*.md"]:
        with pytest.raises(ValueError):
            service.get_draft(pattern)


@pytest.mark.parametrize("name", ["notes.txt", "noextension", "x.md.txt"])
def test_save_requires_a_markdown_name(service, name):
    with pytest.raises(ValueError):
        service.save_draft(name, "x")


def test_save_writes_inside_the_drafts_folder(service, drafts_dir):
    service.save_draft("ok.md", "hello")
    assert (drafts_dir / "ok.md").read_text(encoding="utf-8") == "hello"


def test_write_article_with_hostile_topic_stays_inside(service, drafts_dir, tmp_path):
    result = json.loads(service.write_article("../../../etc/passwd"))
    assert Path(result["saved_to"]).resolve().parent == drafts_dir.resolve()
    assert not (tmp_path / "etc").exists()
