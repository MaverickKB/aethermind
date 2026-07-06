"""Install-from-any-state bootstrap contract.

Derived from docs/plans/install-from-any-state-bootstrap-source-contract-spec.md.
This module reports and plans only Tier 1 source-contract bootstrap behavior; it
must not claim installer, artifact, beta, customer, RC, shippable, or public proof.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from . import evidence, responses, roots, substrate
from .state import stable_root_id


def status(state_dir: Optional[str] = None) -> Dict[str, Any]:
    """Return bootstrap posture for the local source-contract coordinator."""
    pro_state = _pro_state_status(state_dir)
    primitive = _primitive_status(None, state_dir)
    primitive_state = _primitive_state(primitive)
    bootstrap_state = _bootstrap_state(pro_state, primitive_state)
    first_value_possible = (
        primitive_state != "user_managed_incompatible"
        and pro_state not in {"broken", "corrupt", "partial"}
    )
    return responses.ok(
        "bootstrap status",
        bootstrap_state=bootstrap_state,
        components={
            "pro_coordinator": "installed",
            "primitive": primitive_state,
            "pro_state": pro_state,
            "harness_discovery": "available",
        },
        first_value={
            "possible_now": first_value_possible,
            "requires_harness": False,
            "requires_network": False,
            "requires_prior_aethermind_state": False,
            "next_command": "aethermind-pro investigate --project-root . --json",
        },
        evidence=_bootstrap_evidence(primitive),
        degradation=_degradation(pro_state, primitive_state),
    )


def plan(project_root: Optional[str], state_dir: Optional[str] = None) -> Dict[str, Any]:
    """Return a consent-oriented bootstrap plan for the selected root."""
    resolved, err = roots.resolve_root(project_root)
    if err:
        return responses.error(
            "bootstrap plan",
            err,
            "bootstrap plan requires an explicit, existing --project-root",
            "aethermind-pro bootstrap plan --project-root . --json",
        )
    assert resolved is not None
    pro_state = _pro_state_status(state_dir)
    primitive = _primitive_status(resolved, state_dir)
    primitive_state = _primitive_state(primitive)
    actions = _actions_for_primitive(primitive_state)
    actions.extend(_coordinator_and_harness_actions())
    return responses.ok(
        "bootstrap plan",
        components={
            "pro_coordinator": "installed",
            "primitive": primitive_state,
            "pro_state": pro_state,
            "harness_discovery": "available",
        },
        project_root={
            "input": str(project_root),
            "resolved": str(resolved),
            "root_id": stable_root_id(resolved),
        },
        bootstrap_state=_bootstrap_state(pro_state, primitive_state),
        actions=actions,
        forbidden_actions=[
            "write_harness_hooks_without_approval",
            "overwrite_user_managed_primitive_without_approval",
            "read_raw_project_content_by_default",
            "use_private_founder_paths",
            "claim_install_ready_from_source_tree",
        ],
        evidence=_bootstrap_evidence(primitive),
        degradation=_degradation(pro_state, primitive_state),
    )


def apply(project_root: Optional[str], state_dir: Optional[str] = None) -> Dict[str, Any]:
    """Plan-level apply surface: first value is performed by investigate, not installer proof."""
    planned = plan(project_root, state_dir=state_dir)
    if not planned.get("ok"):
        planned["command"] = "bootstrap apply"
        return planned
    return responses.ok(
        "bootstrap apply",
        applied=False,
        reason="source_contract_planning_surface_only",
        next_command="aethermind-pro investigate --project-root . --json",
        actions=planned["actions"],
        evidence=planned["evidence"],
        degradation=[
            {
                "code": "apply_deferred_to_investigate",
                "message": "minimal safe bootstrap occurs through first-value investigate in this Tier 1 source contract",
                "next_action": "aethermind-pro investigate --project-root . --json",
            }
        ] + planned.get("degradation", []),
    )


def _pro_state_status(state_dir: Optional[str]) -> str:
    if not state_dir:
        return "missing"
    path = Path(state_dir).expanduser()
    if not path.exists():
        return "missing"
    if not path.is_dir():
        return "broken"
    state_file = path / "pro_state.json"
    if not state_file.exists():
        return "missing"
    try:
        data = json.loads(state_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "corrupt"
    if not isinstance(data, dict):
        return "corrupt"
    if data.get("state_version") != "aethermind-pro-state-v1":
        return "partial"
    return "available"


def _primitive_status(data_root: Optional[Path], state_dir: Optional[str]) -> Dict[str, Any]:
    return substrate.status(data_root, external=_external_primitive_from_state(state_dir))


def _external_primitive_from_state(state_dir: Optional[str]) -> Optional[Dict[str, Any]]:
    if not state_dir:
        return None
    state_path = Path(state_dir).expanduser() / "pro_state.json"
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    primitive = data.get("primitive")
    if not isinstance(primitive, dict):
        return None
    external = primitive.get("external")
    if not isinstance(external, dict):
        return None
    compatible = external.get("compatible")
    return {
        "version": str(external.get("version", "unknown")),
        "compatible": compatible is True,
        "source_ref": str(external.get("source_ref", "user_managed")),
    }


def _primitive_state(primitive_status: Dict[str, Any]) -> str:
    active = str(primitive_status.get("active_source", "unknown"))
    return {
        "external": "user_managed_compatible",
        "external_incompatible": "user_managed_incompatible",
        "bundled": "bundled_available",
        "missing": "missing",
    }.get(active, "unknown")


def _bootstrap_state(pro_state: str, primitive_state: str) -> str:
    if pro_state in {"partial", "broken", "corrupt"}:
        return "partial_broken_pro_install"
    if primitive_state == "user_managed_compatible" and pro_state == "missing":
        return "pro_absent_primitive_present"
    if primitive_state == "user_managed_incompatible":
        return "pro_absent_primitive_incompatible"
    if pro_state == "available":
        return "previous_pro_install"
    if primitive_state == "bundled_available":
        return "clean_machine_blank"
    return "unknown"


def _actions_for_primitive(primitive_state: str) -> list[Dict[str, Any]]:
    if primitive_state == "user_managed_compatible":
        return [{
            "action_id": "preserve-user-primitive",
            "kind": "preserve_user_primitive",
            "required_for_first_value": True,
            "requires_user_approval": False,
            "target": "user_managed_primitive",
            "owner": "user_owned",
            "rollback": "preserve_user_owned_state",
            "network_required": False,
            "trust_review": "not_required",
        }]
    if primitive_state == "user_managed_incompatible":
        return [{
            "action_id": "report-incompatible-primitive",
            "kind": "report_incompatible_primitive",
            "required_for_first_value": True,
            "requires_user_approval": True,
            "target": "user_managed_primitive",
            "owner": "user_owned",
            "rollback": "manual_review_required",
            "network_required": False,
            "trust_review": "required",
        }]
    return [{
        "action_id": "select-bundled-primitive",
        "kind": "select_bundled_primitive",
        "required_for_first_value": True,
        "requires_user_approval": False,
        "target": "project_local_aethermind_store",
        "owner": "user_owned",
        "rollback": "preserve_user_owned_state",
        "network_required": False,
        "trust_review": "not_required",
    }]


def _coordinator_and_harness_actions() -> list[Dict[str, Any]]:
    return [
        {
            "action_id": "create-pro-state",
            "kind": "create_pro_state",
            "required_for_first_value": True,
            "requires_user_approval": False,
            "target": "pro_state_directory",
            "owner": "pro_managed",
            "rollback": "delete_pro_managed_state",
            "network_required": False,
            "trust_review": "not_required",
        },
        {
            "action_id": "run-harness-discovery",
            "kind": "run_harness_discovery",
            "required_for_first_value": False,
            "requires_user_approval": False,
            "target": "local_harness_discovery",
            "owner": "pro_managed",
            "rollback": "not_applicable",
            "network_required": False,
            "trust_review": "not_required",
        },
        {
            "action_id": "defer-harness-bootstrap",
            "kind": "defer_harness_bootstrap",
            "required_for_first_value": False,
            "requires_user_approval": True,
            "target": "external_harness_control_surfaces",
            "owner": "external_harness",
            "rollback": "manual_review_required",
            "network_required": False,
            "trust_review": "required",
        },
    ]


def _primitive_degradation(primitive_state: str) -> list[Dict[str, str]]:
    if primitive_state != "user_managed_incompatible":
        return []
    return [{
        "code": "incompatible_user_primitive",
        "message": "user-managed primitive is incompatible; Pro will not overwrite or bypass it silently",
        "next_action": "approve bundled primitive selection or repair the user-managed primitive",
    }]


def _degradation(pro_state: str, primitive_state: str) -> list[Dict[str, str]]:
    degradation = []
    if pro_state in {"broken", "corrupt", "partial"}:
        degradation.append({
            "code": "corrupt_pro_state" if pro_state == "corrupt" else "partial_broken_pro_state",
            "message": "Pro state is not a valid complete source-contract state document",
            "next_action": "run bootstrap plan and repair Pro-managed state before claiming first-value readiness",
        })
    degradation.extend(_primitive_degradation(primitive_state))
    return degradation


def _bootstrap_evidence(primitive_status: Dict[str, Any]) -> Dict[str, Any]:
    return evidence.source_tree_evidence(
        substrate_mode=substrate.substrate_mode_label(str(primitive_status.get("active_source", "missing")))
    )
