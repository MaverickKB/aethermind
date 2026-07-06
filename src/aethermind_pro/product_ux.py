"""Product-facing first-run and uninstall surfaces.

These commands give a new user their first local continuity value and an honest
uninstall plan. First local value never requires activation, a network, or a
harness; the store is created locally and stays customer-owned.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from . import evidence, harnesses, investigate, responses, roots
from .state import ProState


def first_run(project_root: Optional[str], *, state_dir: "str | Path | None" = None) -> Dict[str, Any]:
    """Create the first local continuity value with no activation or network."""
    result = investigate.investigate(project_root, state_dir=state_dir, operator_type="internal_agent")
    if not result.get("ok"):
        result["command"] = "first-run"
        return result

    layer = result.get("layer", {})
    return responses.ok(
        "first-run",
        project_root=result.get("project_root"),
        workspace_summary=result.get("workspace_summary"),
        first_value={
            "created": bool(layer.get("created")),
            "layer_id": layer.get("layer_id"),
            "store": layer.get("store", "project_local"),
            "requires_activation": False,
            "requires_network": False,
            "requires_harness": False,
        },
        distribution="source-available",
        harnesses=harness_offers(state_dir=state_dir),
        next_commands={
            "status": "aethermind-pro status --project-root . --json",
            "doctor": "aethermind-pro doctor --project-root . --json",
            "support_bundle": "aethermind-pro support-bundle --output /tmp/aethermind-pro-support.json --json",
            "export": "aethermind-pro export --output /tmp/aethermind-pro-export.json --json",
        },
        evidence=_source_evidence(),
    )


def uninstall_plan(project_root: Optional[str], *, state_dir: "str | Path | None" = None) -> Dict[str, Any]:
    """Report uninstall ownership without deleting user continuity by default."""
    resolved = None
    continuity_present = False
    if project_root:
        resolved, err = roots.resolve_root(project_root)
        if err:
            resolved = None
        if resolved is not None:
            continuity_present = (resolved / ".aethermind").exists()

    state = ProState(state_dir).load()
    pro_managed_surfaces = _pro_managed_surfaces(state)
    return responses.ok(
        "uninstall plan",
        project_root={
            "input": project_root,
            "resolved": str(resolved) if resolved else None,
            "continuity_present": continuity_present,
        },
        pro_managed_surfaces=pro_managed_surfaces,
        default_behavior={
            "remove_pro_managed_controls": True,
            "preserve_user_continuity": True,
            "preserve_project_files": True,
            "preserve_user_owned_harness_config": True,
        },
        destructive_options={
            "purge_user_continuity": "available_only_with_explicit_confirm",
            "purge_state_dir": "available_only_with_explicit_confirm",
        },
        requires_confirm_for_purge=True,
        next_action="run installer-provided uninstall command; add explicit purge flags only if you want continuity removed",
        evidence=_source_evidence(),
    )


def harness_offers(*, state_dir: "str | Path | None" = None) -> Dict[str, Any]:
    """Discover harnesses on this machine and offer consent-gated integration.

    Re-run on every first-run/doctor call so harnesses installed later are
    offered too. Never writes anything; integration stays default-deny.
    """
    discovered = harnesses.discover(state_dir=state_dir).get("harnesses", [])
    detected = [
        {
            "name": h["name"],
            "classification": h["classification"],
            "integrated": h.get("integrated", False),
            "next_action": h["next_action"],
        }
        for h in discovered if h.get("detected")
    ]
    return {
        "detected": detected,
        "integrated_count": sum(1 for h in detected if h["integrated"]),
        "integration_default": "deny_until_approved",
        "rerun_after_adding_harness": "aethermind-pro harnesses discover --json",
    }


def _pro_managed_surfaces(state: Dict[str, Any]) -> Dict[str, Any]:
    configured = state.get("harnesses", {}) if isinstance(state, dict) else {}
    if not isinstance(configured, dict):
        configured = {}
    managed = []
    for name, cfg in sorted(configured.items()):
        if isinstance(cfg, dict) and cfg.get("owner") == "aethermind_pro":
            managed.append({"kind": "harness_config", "name": name, "default_uninstall": "remove"})
    surfaces = state.get("pro_managed_surfaces", []) if isinstance(state, dict) else []
    for record in surfaces:
        if isinstance(record, dict):
            managed.append(dict(record))
    return {
        "count": len(managed),
        "items": managed,
        "remove_command": "aethermind-pro harnesses bootstrap remove --all --json",
        "state_dir": "preserve_by_default",
        "project_continuity": "preserve_by_default",
    }


def _source_evidence() -> Dict[str, Any]:
    return {
        "proof_surface": "source_tree",
        "observation_mode": "cli_only",
        "tier_eligible": [evidence.TIER_SOURCE_CONTRACT],
        "blockers": list(evidence.STANDARD_BLOCKERS),
    }
