"""First-ten-minutes `investigate` command.

Derived from the first-ten-minutes contract (see README quickstart) lines 5-14 and
docs/plans/source-contract-first-slice-spec.md lines 65-173.

`investigate --project-root <root>` inspects a real workspace without Hermes, Codex,
MCP, skills, or prior AetherMind state, creates at least one project-local AetherMind
layer from observed facts, and returns layer id, workspace summary, and next command.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from . import evidence, primitive_mcp, provenance, responses, roots, substrate, workspace
from .audit import AuditLog
from .roots import RootsRegistry
from .state import ProState, stable_root_id

NEXT_COMMAND = "aethermind-pro status --project-root . --json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def investigate(
    project_root: Optional[str],
    *,
    no_write: bool = False,
    state_dir: "str | Path | None" = None,
    policy: Optional[primitive_mcp.PrimitivePolicy] = None,
    external: Optional[Dict[str, Any]] = None,
    operator_type: str = "internal_agent",
) -> Dict[str, Any]:
    path, resolve_error = roots.resolve_root(project_root)
    if resolve_error == "project_root_required":
        return responses.error(
            "investigate",
            "project_root_required",
            "investigate requires an explicit --project-root; no cwd is assumed",
            "aethermind-pro investigate --project-root . --json",
        )
    if resolve_error == "root_not_found":
        return responses.error(
            "investigate",
            "root_not_found",
            "the selected project root does not exist or is not a directory",
            "select an existing project directory with --project-root",
        )
    assert path is not None

    # Substrate selection (degrade honestly if the substrate is missing/blocked).
    sub = substrate.status(path, external=external)
    if sub["active_source"] == "missing":
        return responses.error(
            "investigate",
            "substrate_missing",
            "no compatible AetherMind primitive substrate is available",
            "install a compatible primitive or enable the bundled substrate",
        )
    if sub["active_source"] == "external_incompatible":
        return responses.error(
            "investigate",
            "substrate_incompatible",
            "the user-managed primitive is incompatible; not overwriting it",
            "select the bundled substrate explicitly or repair the external primitive",
        )

    summary = workspace.inspect_workspace(path)
    audit = AuditLog(state_dir)

    layer_block: Dict[str, Any]
    store_state: str
    degradation = []

    if no_write:
        store_status = primitive_mcp.call("status", {"data_root": str(path)}, policy)
        store_state = "already_present" if store_status.get("initialized") else "missing"
        layer_block = {"created": False, "layer_id": None, "store": "project_local"}
        degradation.append(
            {"code": "no_write", "message": "dry inspection only; layer not created",
             "next_action": "re-run without --no-write to create first-value continuity"}
        )
    else:
        init_result = primitive_mcp.call("init_store", {"data_root": str(path)}, policy)
        if not init_result.get("ok"):
            return _primitive_error("investigate", init_result)
        already = init_result.get("already_present", False)
        layer = {
            "kind": "workspace_observation",
            "source": "aethermind_pro_investigate",
            "created_at": _now(),
            "workspace_kind": summary["kind"],
            "observed_facts": summary["observed_facts"],
            "root_id": stable_root_id(path),
        }
        layer, provenance_result = _prepare_provenance(layer, state_dir)
        write_result = primitive_mcp.call("write_layer", {"data_root": str(path), "layer": layer}, policy)
        if not write_result.get("ok"):
            return _primitive_error("investigate", write_result)
        store_state = "already_present" if already else "created"
        layer_block = {"created": True, "layer_id": write_result["layer_id"], "store": "project_local"}
        layer_block["provenance"] = provenance_result
        audit.record_event("workspace_investigated", component="investigate",
                            root_id=stable_root_id(path), verdict_status="proceed")
        _register_root(state_dir, path, store_state, write_result["layer_id"])

    labels = evidence.source_tree_evidence(
        operator_type=operator_type,
        substrate_mode=substrate.substrate_mode_label(sub["active_source"]),
    )

    return responses.ok(
        "investigate",
        project_root={
            "input": project_root,
            "resolved": str(path),
            "root_id": stable_root_id(path),
        },
        workspace_summary={
            "kind": summary["kind"],
            "observed_facts": summary["observed_facts"],
            "aethermind_store": store_state,
        },
        layer=layer_block,
        evidence=labels,
        degradation=degradation,
        next_command=NEXT_COMMAND,
    )


def _prepare_provenance(layer: Dict[str, Any], state_dir):
    """Optionally sign the complete AEM record before its single append.

    Enabled only when the ``provenance.sign_new_layers`` setting is true and a
    readable secret key is configured at ``provenance.key_path``. Any failure leaves
    the new layer unsigned rather than blocking the write.
    """
    settings = ProState(state_dir).load().get("settings", {}).get("provenance", {})
    if not settings.get("sign_new_layers"):
        return layer, {"signing": "disabled"}
    key_path = settings.get("key_path")
    if not key_path:
        return layer, {"signing": "enabled_but_no_key",
                       "note": "set provenance.key_path to a secret key from `keygen`"}
    try:
        secret = provenance.load_secret(key_path)
        canonical = primitive_mcp.canonicalize_layer(layer)
        signed = provenance.sign_layer(canonical, secret)
    except (OSError, ValueError):
        return layer, {"signing": "enabled_but_key_unreadable",
                       "note": "provenance.key_path is not a readable 32-byte key; layer left unsigned"}
    return signed, {"signing": "signed", "key_id": signed.get("sig_key_id"), "signed": 1}


def _register_root(state_dir, path: Path, store_state: str, layer_id: str) -> None:
    registry = RootsRegistry(state_dir)
    record = roots.build_root_record(
        path,
        store_state="present" if store_state == "already_present" else "created",
        trust_state="trusted",
        last_layer_id=layer_id,
        last_seen_at=_now(),
    )
    registry.add(record)


def _primitive_error(command: str, result: Dict[str, Any]) -> Dict[str, Any]:
    err = result.get("error", {})
    code = err.get("code", "internal_error")
    return responses.error(
        command,
        code,
        err.get("message", "primitive substrate error"),
        "resolve the substrate policy issue and retry",
    )
