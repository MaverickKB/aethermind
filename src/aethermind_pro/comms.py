"""Harness-neutral Agent Comms capsules.

Derived from docs/PRO_SYSTEM_CONTRACT.md line 30 and
docs/plans/harness-neutral-source-contract-spec.md lines 85-160.

Equivalent orientation is exposed through CLI JSON, a JSON capsule, and a plaintext
handoff. No surface defines separate product truth. Output excludes secrets, raw
project content, and private operator paths.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import atlas, cortex, evidence, responses, roots, substrate, workspace
from .state import stable_root_id

SCHEMA_VERSION = "aethermind-pro-handoff-v1"
HARNESS_TARGETS = ("hermes", "grok_build", "codex", "claude_code", "cursor", "custom", "future")
COMMS_DIRNAME = "comms"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_capsule(
    project_root: str,
    *,
    state_dir: "str | Path | None" = None,
    external: Optional[Dict[str, Any]] = None,
    harness_target: str = "custom",
) -> Dict[str, Any]:
    path, resolve_error = roots.resolve_root(project_root)
    if resolve_error:
        raise ValueError(resolve_error)
    assert path is not None
    if harness_target not in HARNESS_TARGETS:
        harness_target = "custom"

    summary = workspace.inspect_workspace(path)
    assessed = atlas.assess_continuity(path)
    sub = substrate.status(path, external=external)
    substrate_component = "available" if sub["active_source"] in ("external", "bundled") else "missing"
    verdict = cortex.coordinate(assessed["state"], substrate_state=substrate_component)

    return {
        "schema_version": SCHEMA_VERSION,
        "capsule_id": "capsule-" + uuid.uuid4().hex[:16],
        "created_at": _now(),
        "project": {
            "root_id": stable_root_id(path),
            "display_name": path.name or str(path),
            "workspace_kind": summary["kind"],
        },
        "continuity": {
            "store": "project_local",
            "freshness": assessed["state"],
            "last_layer_id": assessed["last_layer_id"],
            "summary": f"{assessed['visible_layers']} visible layer(s)",
        },
        "cortex": {
            "verdict": verdict["verdict"],
            "pressure_codes": verdict["pressure_codes"],
            "repair_lanes": verdict["repair_lanes"],
            "next_actions": verdict["next_actions"],
        },
        "trust": {"required": False, "verdict": "not_required", "audit_event_id": None},
        "harness": {
            "target": harness_target,
            "capabilities_required": ["read_orientation", "write_or_request_continuity", "resume_session_optional"],
            "capabilities_available": ["read_orientation"],
            "unsupported": [],
        },
        "evidence": {
            "proof_surface": "source_tree",
            "observation_mode": "cli_only",
            "distribution_mode": "none",
            "tier_eligible": [evidence.TIER_SOURCE_CONTRACT],
            "blockers": list(evidence.STANDARD_BLOCKERS),
        },
        "redaction": {
            "raw_project_content_included": False,
            "private_paths_included": False,
            "secrets_included": False,
        },
    }


def plaintext(capsule: Dict[str, Any]) -> str:
    """Render the equivalent plaintext handoff (docs harness-neutral spec lines 145-157)."""
    project = capsule.get("project", {})
    continuity = capsule.get("continuity", {})
    cortex_block = capsule.get("cortex", {})
    trust = capsule.get("trust", {})
    actions: List[str] = cortex_block.get("next_actions", []) or []
    lines = [
        "AetherMind Pro handoff",
        f"Project: {project.get('display_name') or project.get('root_id')}",
        f"Workspace: {project.get('workspace_kind', 'unknown')}",
        f"Continuity: {continuity.get('freshness', 'unknown')}"
        + (f" + {continuity.get('last_layer_id')}" if continuity.get("last_layer_id") else ""),
        f"CORTEX verdict: {cortex_block.get('verdict', 'unknown')}",
        f"Pressure: {', '.join(cortex_block.get('pressure_codes', [])) or 'none'}",
        f"Trust: {trust.get('verdict', 'not_required')}",
        "Next actions:",
    ]
    for i, action in enumerate(actions, start=1):
        lines.append(f"{i}. {action}")
    lines.append("Evidence tier: tier_1_source_contract; " + ", ".join(evidence.STANDARD_BLOCKERS))
    lines.append("Limits: source-contract proof only; not artifact/beta/customer/public proof")
    return "\n".join(lines)


def brief(project_root: str, *, state_dir: "str | Path | None" = None,
          external: Optional[Dict[str, Any]] = None, harness_target: str = "custom") -> Dict[str, Any]:
    try:
        capsule = build_capsule(project_root, state_dir=state_dir, external=external, harness_target=harness_target)
    except ValueError as exc:
        return responses.error("comms brief", str(exc),
                               "comms brief requires an explicit, existing --project-root",
                               "aethermind-pro comms brief --project-root . --json")
    return responses.ok("comms brief", capsule=capsule, plaintext=plaintext(capsule),
                        evidence=capsule["evidence"])


def write(project_root: str, capsule: Optional[Dict[str, Any]] = None, *,
          state_dir: "str | Path | None" = None,
          external: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    from . import config

    if capsule is None:
        try:
            capsule = build_capsule(project_root, state_dir=state_dir, external=external)
        except ValueError as exc:
            return responses.error("comms write", str(exc),
                                   "comms write requires an explicit, existing --project-root",
                                   "aethermind-pro comms write --project-root . --json")
    comms_dir = config.ensure_state_dir(state_dir) / COMMS_DIRNAME
    comms_dir.mkdir(parents=True, exist_ok=True)
    capsule_path = comms_dir / f"{capsule['capsule_id']}.json"
    capsule_path.write_text(json.dumps(capsule, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return responses.ok("comms write", capsule_id=capsule["capsule_id"],
                        stored=True, evidence=capsule["evidence"])


def read(project_root: Optional[str] = None, *, state_dir: "str | Path | None" = None) -> Dict[str, Any]:
    from . import config

    comms_dir = config.ensure_state_dir(state_dir) / COMMS_DIRNAME
    if not comms_dir.exists():
        return responses.ok("comms read", capsules=[], count=0,
                            evidence=evidence.source_tree_evidence())
    capsules: List[Dict[str, Any]] = []
    for capsule_file in sorted(comms_dir.glob("*.json")):
        try:
            capsules.append(json.loads(capsule_file.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    return responses.ok("comms read", capsules=capsules, count=len(capsules),
                        evidence=evidence.source_tree_evidence())
