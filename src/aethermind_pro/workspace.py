"""Bounded, support-safe workspace inspection.

Derived from the first-ten-minutes contract (see README quickstart) lines 7-14 (works for code repos,
creative writing, research, notes, and general directories) and
docs/plans/source-contract-first-slice-spec.md lines 102-123 (minimum workspace facts,
forbidden default content).

Only bounded, count/label-level facts are produced. No raw file contents, snippets,
secrets, or private paths are ever emitted.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

WORKSPACE_KINDS = (
    "code_repo",
    "creative_writing",
    "research",
    "notes",
    "general",
    "mixed",
    "unknown",
)

_CODE_MARKERS = (
    "pyproject.toml",
    "setup.py",
    "package.json",
    "Cargo.toml",
    "go.mod",
    "pom.xml",
    "build.gradle",
    "Gemfile",
    "composer.json",
    "Makefile",
)
_CODE_EXTS = {".py", ".js", ".ts", ".tsx", ".jsx", ".rs", ".go", ".java", ".rb", ".c", ".cpp", ".h", ".cs"}
_WRITING_EXTS = {".docx", ".odt", ".rtf"}
_RESEARCH_EXTS = {".bib", ".tex", ".ipynb"}
_NOTE_EXTS = {".md", ".markdown", ".txt", ".org"}


def _bucket(count: int) -> str:
    if count == 0:
        return "none"
    if count <= 5:
        return "few"
    if count <= 50:
        return "some"
    return "many"


def inspect_workspace(root: Path, *, max_entries: int = 5000) -> Dict[str, object]:
    """Inspect a root and return a bounded workspace summary.

    Returns a dict with ``kind`` and ``observed_facts`` (bounded strings).
    """
    facts: List[str] = []
    has_git = (root / ".git").exists()
    if has_git:
        facts.append("contains_git_repo")

    present_markers = [m for m in _CODE_MARKERS if (root / m).exists()]
    for marker in present_markers:
        facts.append(f"has_{marker.replace('.', '_').replace('/', '_')}")

    ext_counts: Dict[str, int] = {}
    scanned = 0
    truncated = False
    for path in root.rglob("*"):
        if scanned >= max_entries:
            truncated = True
            break
        # Skip hidden/state directories so private/continuity stores are not summarized.
        parts = path.relative_to(root).parts
        if any(part.startswith(".") for part in parts):
            continue
        if path.is_file():
            scanned += 1
            ext = path.suffix.lower()
            if ext:
                ext_counts[ext] = ext_counts.get(ext, 0) + 1

    code_files = sum(ext_counts.get(e, 0) for e in _CODE_EXTS)
    writing_files = sum(ext_counts.get(e, 0) for e in _WRITING_EXTS)
    research_files = sum(ext_counts.get(e, 0) for e in _RESEARCH_EXTS)
    note_files = sum(ext_counts.get(e, 0) for e in _NOTE_EXTS)

    facts.append(f"code_files:{_bucket(code_files)}")
    facts.append(f"note_or_text_files:{_bucket(note_files)}")
    if writing_files:
        facts.append(f"prose_documents:{_bucket(writing_files)}")
    if research_files:
        facts.append(f"research_files:{_bucket(research_files)}")
    if truncated:
        facts.append("scan_truncated")

    kind = _classify(
        has_git=has_git,
        has_code_marker=bool(present_markers),
        code_files=code_files,
        writing_files=writing_files,
        research_files=research_files,
        note_files=note_files,
    )
    return {"kind": kind, "observed_facts": facts}


def _classify(*, has_git: bool, has_code_marker: bool, code_files: int,
              writing_files: int, research_files: int, note_files: int) -> str:
    signals = {
        "code_repo": (has_git or has_code_marker or code_files > 0),
        "creative_writing": writing_files > 0,
        "research": research_files > 0,
        "notes": note_files > 0,
    }
    active = [name for name, present in signals.items() if present]

    if not active:
        return "unknown"

    # A strong code signal dominates a single competing note signal (code repos
    # frequently include READMEs and notes).
    if signals["code_repo"] and (has_git or has_code_marker or code_files >= 3):
        if len([n for n in active if n != "notes"]) > 1:
            return "mixed"
        return "code_repo"

    if len(active) > 1:
        return "mixed"
    return active[0]
