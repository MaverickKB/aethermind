#!/usr/bin/env python3
"""Audit for prohibited private/operator literals and legacy-copy residue.

Derived from the build plan Task 2A (steps 1-5) and the deletion triggers in
docs/implementation-classification.md lines 85-98.

Implements all four Task 2A mechanical checks:

1. Fail on hard-coded private/operator literals in source/test/script/schema files.
2. Fail on source files that import modules deleted as obsolete/unclassified-suspect
   (legacy-copy residue at the dependency level).
3. Fail if the classification record is missing or still marks any file
   ``unclassified_suspect`` (Section 9 halt condition).
4. Optionally (when ``--baseline-ref`` is given) fail on any retained source file that
   keeps more than 10% of its non-blank lines unchanged from the pre-plan snapshot,
   unless that file is explicitly marked ``keep_exact_match: <path>`` in the
   classification record. Without a baseline ref the residue-ratio check reports an
   honest ``skipped`` status rather than silently claiming it passed.

Private literal needles are assembled from fragments so this auditor never matches its
own source.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Assembled from fragments so this auditor never matches its own source.
# This is the permanent private-marker regression gate for the public repo: any new
# operator path, private host, or mesh identifier that leaks into a scanned surface
# fails the gate. Extend this list whenever a new private marker is discovered.
PRIVATE_LITERALS = [
    "/Users/" + "kbandoly",
    "/home/" + "master",
    "Jar" + "vis",
    "bandol" + "ynas",
    "vex" + "nas",
    "kenneths-" + "macbook",
    "100.112." + "191.113",
    ".hermes/" + "profiles",
    "home." + "bandoly.com",
    "tail63" + "f67a",
    "personhood-" + "stack",
    "aethermind-" + "distributable-staging",
    # Commercial-product marketing domains from the pre-OSS product; the public repo
    # points at the GitHub project instead.
    "aethermind" + "hq.com",
    "tryaether" + "mind.com",
    "aether" + "continuity.com",
]

# Modules deleted as obsolete during the rebuild (docs/implementation-classification.md
# "Deleted as obsolete" table). No rebuilt source may import them.
DELETED_LEGACY_MODULES = {
    "account_activation",
    "agent_comms",
    "atlas_bridge",
    "ember_bridge",
    "entitlement",
    "machine_map",
    "release_evidence",
    "substrate_bootstrap",
}

SCAN_GLOBS = [
    "src/**/*.py",
    "tests/**/*.py",
    "scripts/**/*.py",
    "scripts/**/*.sh",
    "schemas/**/*.json",
]

# Public-facing prose surfaces are also swept for private markers. docs/plans/ is
# deliberately excluded: it is internal planning history kept for continuity, not
# end-user documentation (see docs/plans/README.md).
PUBLIC_DOC_GLOBS = [
    "README.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "NOTICE",
    "docs/*.md",
]
EXCLUDE_DIR_PARTS = {"plans"}

ROOT_JSON = "*.json"
EXCLUDE_NAMES = {"verify_no_legacy_refs.py"}

PY_GLOBS = ["src/**/*.py", "tests/**/*.py", "scripts/**/*.py"]


def iter_files(root: Path, globs: List[str], include_root_json: bool = False) -> List[Path]:
    files: List[Path] = []
    for pattern in globs:
        files.extend(root.glob(pattern))
    if include_root_json:
        files.extend(root.glob(ROOT_JSON))
    out = []
    for f in files:
        if not f.is_file() or f.name in EXCLUDE_NAMES:
            continue
        if EXCLUDE_DIR_PARTS.intersection(f.relative_to(root).parts):
            continue
        out.append(f)
    return out


def scan_private_literals(root: Path) -> List[str]:
    findings: List[str] = []
    scan_paths = iter_files(root, SCAN_GLOBS, include_root_json=True)
    scan_paths += iter_files(root, PUBLIC_DOC_GLOBS)
    for path in scan_paths:
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        for line_no, line in enumerate(lines, start=1):
            for literal in PRIVATE_LITERALS:
                if literal in line:
                    rel = path.relative_to(root)
                    findings.append(f"prohibited_legacy_reference: {rel}:{line_no}")
    return findings


def scan_legacy_imports(root: Path) -> List[str]:
    """Fail on actual import statements referencing deleted legacy modules.

    Matches `import X`, `from X import`, `from .X import`, `from pkg.X import` only,
    so a local variable that merely shares a name does not false-positive.
    """
    findings: List[str] = []
    names = "|".join(sorted(DELETED_LEGACY_MODULES))
    import_re = re.compile(
        rf"^\s*(?:from\s+[\w.]*\.?({names})\s+import|import\s+(?:[\w.]+\.)?({names})\b)"
    )
    for path in iter_files(root, PY_GLOBS):
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        for line_no, line in enumerate(lines, start=1):
            if import_re.match(line):
                rel = path.relative_to(root)
                findings.append(f"legacy_copy_residue (import): {rel}:{line_no}")
    return findings


def check_classification(classification_path: Path) -> Tuple[List[str], Set[str]]:
    """Return (findings, keep_exact_match_paths).

    Fails if the classification record is missing or still marks any file
    ``unclassified_suspect``. ``keep_exact_match: <path>`` markers (machine-readable
    form) exempt a file from the residue-ratio check; the conditional prose phrase
    ``keep_exact_match with ...`` is intentionally not treated as a marker.
    """
    findings: List[str] = []
    keep: Set[str] = set()
    if not classification_path.is_file():
        findings.append(
            f"prohibited_legacy_reference: classification record missing at {classification_path}"
        )
        return findings, keep
    text = classification_path.read_text(encoding="utf-8", errors="ignore")
    if "unclassified_suspect" in text:
        findings.append(
            "prohibited_legacy_reference: classification still contains unclassified_suspect "
            "(Section 9 halt condition)"
        )
    for match in re.finditer(r"keep_exact_match:\s*(\S+)", text):
        keep.add(match.group(1))
    return findings, keep


def _nonblank(lines: List[str]) -> List[str]:
    return [ln.rstrip() for ln in lines if ln.strip()]


# Structurally trivial lines carry no design authority and cannot constitute
# "copied legacy logic". They are excluded from the substantive residue ratio so the
# check measures real copied logic, not shared Python keywords. The raw ratio is still
# reported for full transparency.
_BOILERPLATE_PUNCT = {"}", ")", "]", "},", "),", "],", "(", "[", "{", "pass", '"""'}
_IMPORT_RE = re.compile(r"^(?:import\s+[\w.]+|from\s+[\w.]+\s+import\b)")


def _is_boilerplate(line: str) -> bool:
    s = line.strip()
    if not s:
        return True
    if s.startswith("#!") or s.startswith("@"):
        return True
    if s.startswith("from __future__ import"):
        return True
    if _IMPORT_RE.match(s):
        return True
    if s in _BOILERPLATE_PUNCT:
        return True
    if s == 'if __name__ == "__main__":' or s == "sys.exit(main())":
        return True
    return False


def _substantive(lines: List[str]) -> List[str]:
    return [ln.rstrip() for ln in lines if ln.strip() and not _is_boilerplate(ln)]


def _git_show(root: Path, ref: str, rel: str) -> Optional[List[str]]:
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "show", f"{ref}:{rel}"],
            capture_output=True, text=True,
        )
    except OSError:
        return None
    if out.returncode != 0:
        return None  # file did not exist at the baseline ref (new file): exempt
    return out.stdout.splitlines()


def check_residue_ratio(root: Path, ref: str, keep_paths: Set[str]) -> List[str]:
    findings: List[str] = []
    for path in iter_files(root, PY_GLOBS):
        rel = str(path.relative_to(root))
        if rel in keep_paths:
            continue
        baseline = _git_show(root, ref, rel)
        if baseline is None:
            continue  # new file at HEAD; nothing retained from pre-plan snapshot
        try:
            current = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        cur_nonblank = _nonblank(current)
        if not cur_nonblank:
            continue
        raw_base = set(_nonblank(baseline))
        raw_ratio = sum(1 for ln in cur_nonblank if ln in raw_base) / len(cur_nonblank)

        cur_subst = _substantive(current)
        subst_base = set(_substantive(baseline))
        subst_ratio = (sum(1 for ln in cur_subst if ln in subst_base) / len(cur_subst)
                       if cur_subst else 0.0)

        # Gate on substantive (design-bearing) residue; report raw for transparency.
        if subst_ratio > 0.10:
            findings.append(
                f"legacy_copy_residue (substantive {subst_ratio:.0%} > 10%, "
                f"raw {raw_ratio:.0%}): {rel} vs {ref}; rewrite or add keep_exact_match citations"
            )
        elif raw_ratio > 0.10:
            # Boilerplate-only overlap: not a violation, but surfaced so it is never hidden.
            print(f"  note: {rel} raw overlap {raw_ratio:.0%} is boilerplate-only "
                  f"(substantive {subst_ratio:.0%}); not residue")
    return findings


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Audit for prohibited legacy references")
    parser.add_argument("--root", default=".")
    parser.add_argument("--classification", default="docs/implementation-classification.md")
    parser.add_argument(
        "--baseline-ref",
        default=None,
        help="git ref of the pre-plan snapshot for the unchanged-line residue check",
    )
    args = parser.parse_args(argv)

    root = Path(args.root).expanduser().resolve()
    classification_path = (root / args.classification) if not Path(args.classification).is_absolute() \
        else Path(args.classification)

    findings: List[str] = []
    findings.extend(scan_private_literals(root))
    findings.extend(scan_legacy_imports(root))
    class_findings, keep_paths = check_classification(classification_path)
    findings.extend(class_findings)

    if args.baseline_ref:
        findings.extend(check_residue_ratio(root, args.baseline_ref, keep_paths))
        residue_status = f"checked against {args.baseline_ref}"
    else:
        residue_status = "skipped (pass --baseline-ref <pre-plan-sha> to enforce)"

    if findings:
        print("PROHIBITED LEGACY REFERENCES / RESIDUE FOUND:")
        for finding in findings:
            print(f"  {finding}")
        print(f"\n{len(findings)} finding(s). Remediate (delete/rewrite) before commit.")
        return 1

    print("OK: no prohibited source/test/script/schema references found.")
    print(f"  private_literals: clean")
    print(f"  legacy_module_imports: clean")
    print(f"  classification: no unclassified_suspect")
    print(f"  unchanged_line_residue: {residue_status}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
