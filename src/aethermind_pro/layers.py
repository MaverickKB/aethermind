"""Layer inspection and soft user actions.

Derived from docs/PRO_SYSTEM_CONTRACT.md line 35, docs/PRIVACY_AND_AUDIT.md line 9, and
docs/plans/local-coordinator-source-contract-spec.md.

Users browse roots/groups, inspect layers without raw content leakage, and mark
entries hidden/archived/quarantined/stale. Marks are stored in Pro state, never by
rewriting the append-only `.aem` primitive store. Destructive removal requires an
explicit human choice and is never the default.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from . import atlas, evidence, primitive_mcp, responses, roots
from .roots import RootsRegistry
from .state import ProState, stable_root_id

# Preferred customer marks. Legacy hard labels (deleted/ignored/superseded) are avoided.
MARKS = ("hidden", "archived", "quarantined", "stale")
MARKS_KEY = "layer_marks"


def _evidence_block() -> Dict[str, Any]:
    return {
        "proof_surface": "source_tree",
        "tier_eligible": [evidence.TIER_SOURCE_CONTRACT],
        "blockers": list(evidence.STANDARD_BLOCKERS),
    }


def _marks(state_dir) -> Dict[str, str]:
    return ProState(state_dir).load().get(MARKS_KEY, {})


def browse(*, state_dir: "str | Path | None" = None) -> Dict[str, Any]:
    records = RootsRegistry(state_dir).list()
    groups: Dict[str, List[str]] = {}
    for record in records:
        groups.setdefault(record.get("root_kind", "unknown"), []).append(record.get("root_id"))
    return responses.ok(
        "layers browse",
        roots=[{"root_id": r.get("root_id"), "display_name": r.get("display_name"),
                "root_kind": r.get("root_kind")} for r in records],
        directory_groups=groups,
        evidence=_evidence_block(),
    )


def inspect(project_root: Optional[str], *, state_dir: "str | Path | None" = None) -> Dict[str, Any]:
    path, err = roots.resolve_root(project_root)
    if err:
        return responses.error("layers inspect", err,
                               "layers inspect requires an explicit, existing --project-root",
                               "aethermind-pro layers inspect --project-root . --json")
    assert path is not None
    root_id = stable_root_id(path)
    read = primitive_mcp.call("read_layers", {"data_root": str(path)})
    marks = _marks(state_dir)
    layers_out: List[Dict[str, Any]] = []
    if read.get("ok"):
        for layer in read.get("layers", []):
            layer_id = layer.get("layer_id")
            layers_out.append({
                "layer_id": layer_id,
                "kind": layer.get("kind", "unknown"),
                "created_at": layer.get("created_at"),
                "workspace_kind": layer.get("workspace_kind"),
                "mark": marks.get(f"{root_id}:{layer_id}", "none"),
            })
    return responses.ok(
        "layers inspect",
        project_root={"input": project_root, "root_id": root_id},
        layers=layers_out,
        count=len(layers_out),
        raw_content_included=False,
        evidence=_evidence_block(),
    )


def mark(project_root: Optional[str], layer_id: Optional[str], mark_value: Optional[str], *,
         state_dir: "str | Path | None" = None) -> Dict[str, Any]:
    if not layer_id or not mark_value:
        return responses.error("layers mark", "layer_and_mark_required",
                               "layers mark requires --layer-id and --mark",
                               "marks: " + ", ".join(MARKS))
    if mark_value not in MARKS:
        return responses.error("layers mark", "invalid_mark",
                               f"invalid mark: {mark_value}",
                               "valid marks: " + ", ".join(MARKS))
    path, err = roots.resolve_root(project_root)
    if err:
        return responses.error("layers mark", err,
                               "layers mark requires an explicit, existing --project-root",
                               "aethermind-pro layers mark --project-root . --layer-id <id> --mark <mark>")
    assert path is not None
    root_id = stable_root_id(path)
    state = ProState(state_dir)
    data = state.load()
    data.setdefault(MARKS_KEY, {})[f"{root_id}:{layer_id}"] = mark_value
    state.save(data)
    return responses.ok("layers mark", layer_id=layer_id, mark=mark_value,
                        store_rewritten=False, evidence=_evidence_block())


def remove(project_root: Optional[str], layer_id: Optional[str], *, confirm: bool = False,
           state_dir: "str | Path | None" = None) -> Dict[str, Any]:
    """Destructive removal is gated. It is never the default and never silently
    rewrites the append-only `.aem` store."""
    if not confirm:
        return responses.ok(
            "layers remove",
            performed=False,
            requires_explicit_confirmation=True,
            message="destructive removal requires an explicit human choice; "
                    "consider marking hidden/archived/quarantined instead",
            next_action="re-run with explicit --confirm to record a removal intent",
            evidence=_evidence_block(),
        )
    # Even when confirmed, record a soft quarantine intent rather than rewriting the
    # append-only primitive store. A true purge is a separate explicit operation with
    # honest limits.
    soft = mark(project_root, layer_id, "quarantined", state_dir=state_dir)
    if not soft.get("ok"):
        return soft
    return responses.ok(
        "layers remove",
        performed=True,
        method="soft_quarantine",
        store_rewritten=False,
        message="recorded a quarantine intent; the append-only store was not rewritten",
        purge_limits="a full purge has honest limits and is a separate explicit operation",
        evidence=_evidence_block(),
    )
