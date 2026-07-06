"""Permanent private-marker regression gate.

The public repo must never leak an operator path, private host, or mesh identifier
into a scanned surface. This sentinel replaces the marker check that used to live in
test_human_visible_vm_evidence.py; the actual sweep is scripts/verify_no_legacy_refs.py.

Two guarantees:
1. The current tree is clean (the sweep passes).
2. The sweep actually catches a planted marker (it is not silently a no-op).
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "scripts" / "verify_no_legacy_refs.py"

# Assembled from fragments so this file is not itself a finding.
SENTINEL_MARKERS = [
    "/Users/" + "kbandoly",
    "bandol" + "ynas",
    "home." + "bandoly.com",
    "tail63" + "f67a",
    "/home/" + "master",
    "aethermind" + "hq.com",
]


def _run_gate(root):
    return subprocess.run(
        [sys.executable, str(GATE), "--root", str(root)],
        capture_output=True, text=True, cwd=str(ROOT),
    )


def test_tracked_tree_is_clean():
    result = _run_gate(ROOT)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "private_literals: clean" in result.stdout


def test_gate_catches_planted_marker(tmp_path):
    # A minimal fake tree with the classification record the gate expects.
    (tmp_path / "src").mkdir()
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "implementation-classification.md").write_text(
        "all files classified; none unclassified.\n", encoding="utf-8")
    leak = SENTINEL_MARKERS[0]
    (tmp_path / "src" / "leak.py").write_text(f'HOST = "{leak}"\n', encoding="utf-8")

    result = _run_gate(tmp_path)
    assert result.returncode != 0
    assert "prohibited_legacy_reference" in result.stdout
    assert "src/leak.py" in result.stdout


def test_every_named_marker_is_caught(tmp_path):
    """Every private marker the Phase 0 plan named must trip the gate when planted."""
    for i, marker in enumerate(SENTINEL_MARKERS):
        sub = tmp_path / f"tree{i}"
        (sub / "src").mkdir(parents=True)
        (sub / "docs").mkdir()
        (sub / "docs" / "implementation-classification.md").write_text(
            "all files classified.\n", encoding="utf-8")
        (sub / "src" / "leak.py").write_text(f'X = "{marker}"\n', encoding="utf-8")
        result = _run_gate(sub)
        assert result.returncode != 0, f"gate missed planted marker: {marker}"
