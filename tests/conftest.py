"""Shared fixtures for docs-derived source-contract tests.

All fixtures use synthetic temp directories only (docs/plans/source-contract-test-spec.md
lines 250-270). No real operator paths, secrets, or existing repo continuity are used.
"""

import pathlib
import sys

import pytest

SRC = pathlib.Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture
def state_dir(tmp_path):
    return str(tmp_path / "pro-state")


@pytest.fixture
def code_repo(tmp_path):
    root = tmp_path / "synthetic-repo"
    root.mkdir()
    (root / "pyproject.toml").write_text("[project]\nname = 'synthetic'\n", encoding="utf-8")
    (root / "main.py").write_text("def run():\n    return 1\n", encoding="utf-8")
    (root / "lib.py").write_text("X = 2\n", encoding="utf-8")
    (root / ".git").mkdir()
    return str(root)


@pytest.fixture
def writing_dir(tmp_path):
    root = tmp_path / "synthetic-novel"
    root.mkdir()
    (root / "chapter-1.docx").write_bytes(b"PK\x03\x04 synthetic")
    (root / "chapter-2.docx").write_bytes(b"PK\x03\x04 synthetic")
    (root / "outline.rtf").write_text("synthetic outline\n", encoding="utf-8")
    return str(root)


@pytest.fixture
def notes_dir(tmp_path):
    root = tmp_path / "synthetic-notes"
    root.mkdir()
    for i in range(4):
        (root / f"note-{i}.md").write_text(f"# note {i}\n", encoding="utf-8")
    return str(root)
