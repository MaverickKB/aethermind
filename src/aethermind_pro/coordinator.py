"""Coordinator command surfaces: `status`, `map`, `coordinate`.

Derived from docs/PRO_SYSTEM_CONTRACT.md lines 23, 28-29 and
docs/plans/source-contract-first-slice-spec.md lines 211-257 (status shape) and
docs/plans/local-coordinator-source-contract-spec.md.

These commands are CLI-complete and never require admin UI / tracker / HUD.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from . import atlas, cortex, evidence, responses, roots, substrate
from .roots import RootsRegistry
from .state import ProState, stable_root_id


def _evidence_block(external: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    active = substrate.select_active(external)["active_source"]
    labels = evidence.source_tree_evidence(substrate_mode=substrate.substrate_mode_label(active))
    return labels


def status(
    project_root: Optional[str] = None,
    *,
    state_dir: "str | Path | None" = None,
    external: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    sub = substrate.status(external=external)
    primitive_component = {
        "external": "available",
        "bundled": "available",
        "external_incompatible": "incompatible",
        "missing": "missing",
    }.get(sub["active_source"], "missing")

    components = {
        "primitive_substrate": primitive_component,
        "pro_state": "available",
        "atlas_map": "available",
        "cortex": "available",
        "distribution": "source-available",
    }

    continuity = {
        "store": "project_local",
        "visible_layers": 0,
        "last_layer_id": None,
        "freshness": "missing",
    }
    root_block: Dict[str, Any] = {"input": project_root, "root_id": None}

    if project_root:
        path, resolve_error = roots.resolve_root(project_root)
        if resolve_error:
            return responses.error(
                "status",
                resolve_error,
                "could not resolve the selected project root",
                "provide an existing directory with --project-root",
            )
        assert path is not None
        root_block["root_id"] = stable_root_id(path)
        assessed = atlas.assess_continuity(path)
        continuity = {
            "store": "project_local",
            "visible_layers": assessed["visible_layers"],
            "last_layer_id": assessed["last_layer_id"],
            "freshness": assessed["state"],
        }

    return responses.ok(
        "status",
        project_root=root_block,
        components=components,
        continuity=continuity,
        evidence=_evidence_block(external),
        next_command="aethermind-pro coordinate --project-root . --json",
    )


def map_command(
    *,
    state_dir: "str | Path | None" = None,
    external: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    data = ProState(state_dir).load()
    cairn_enabled = bool(
        data.get("settings", {}).get("cairn_network_context", {}).get("enabled", False)
    )
    records = RootsRegistry(state_dir).list()
    machine_map = atlas.build_map(records, external=external, cairn_enabled=cairn_enabled)
    return responses.ok("map", map=machine_map, evidence=_evidence_block(external))


def coordinate(
    project_root: Optional[str],
    *,
    state_dir: "str | Path | None" = None,
    external: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    path, resolve_error = roots.resolve_root(project_root)
    if resolve_error:
        return responses.error(
            "coordinate",
            resolve_error,
            "coordinate requires an explicit, existing --project-root",
            "aethermind-pro coordinate --project-root . --json",
        )
    assert path is not None

    sub = substrate.status(path, external=external)
    substrate_component = {
        "external": "available",
        "bundled": "available",
        "external_incompatible": "incompatible",
        "missing": "missing",
    }.get(sub["active_source"], "missing")

    assessed = atlas.assess_continuity(path)
    registry_record = _root_record(state_dir, path)
    trust_state = registry_record.get("trust_state", "trusted") if registry_record else "trusted"
    root_id = stable_root_id(path)

    verdict = cortex.coordinate(
        assessed["state"],
        substrate_state=substrate_component,
        trust_state=trust_state,
        root_id=root_id,
    )

    return responses.ok(
        "coordinate",
        project_root={"input": project_root, "root_id": root_id},
        cortex=verdict,
        cairn_network={
            "note": "actual Cairn-network Ember carries private executive load when available",
            "enabled": False,
            "state": "local_only_or_degraded",
        },
        continuity={
            "store": "project_local",
            "visible_layers": assessed["visible_layers"],
            "last_layer_id": assessed["last_layer_id"],
            "freshness": assessed["state"],
        },
        evidence=_evidence_block(external),
        next_command="aethermind-pro comms brief --project-root . --json",
    )


def _root_record(state_dir, path: Path) -> Optional[Dict[str, Any]]:
    return RootsRegistry(state_dir).get(stable_root_id(path))
