"""Host service control: start/stop/restart/status for Pro services.

Derived from docs/PRO_SYSTEM_CONTRACT.md line 32 and
docs/plans/local-coordinator-source-contract-spec.md lines 163-187.

Atlas and host-local Ember/CORTEX services are controllable CLI-complete. Admin UI,
tracker, and HUD are never required for core service function. Service state is local
and bounded; no private LaunchAgents/systemd units are assumed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from . import evidence, responses
from .state import ProState

CORE_SERVICES = ("atlas", "cortex")
HEALTH_STATES = (
    "running", "stopped", "starting", "stopping",
    "degraded", "blocked", "not_installed", "unknown",
)


def _evidence_block() -> Dict[str, Any]:
    return {
        "proof_surface": "source_tree",
        "tier_eligible": [evidence.TIER_SOURCE_CONTRACT],
        "blockers": list(evidence.STANDARD_BLOCKERS),
    }


def _load_services(state_dir) -> Dict[str, str]:
    services = ProState(state_dir).load().get("services", {})
    return {name: services.get(name, "stopped") for name in CORE_SERVICES}


def _save_service(state_dir, name: str, health: str) -> None:
    state = ProState(state_dir)
    data = state.load()
    data.setdefault("services", {})[name] = health
    state.save(data)


def status(*, state_dir: "str | Path | None" = None) -> Dict[str, Any]:
    services = _load_services(state_dir)
    return responses.ok(
        "services status",
        services={
            "atlas": services["atlas"],
            "cortex": services["cortex"],
            "trust_review": "available",
            "harness_contract": "available",
            "tracker": "optional_not_required_for_core",
            "admin_ui": "optional_not_required_for_core",
        },
        ui_required_for_core=False,
        evidence=_evidence_block(),
    )


def control(action: str, name: Optional[str] = None, *,
            state_dir: "str | Path | None" = None) -> Dict[str, Any]:
    if action not in ("start", "stop", "restart"):
        return responses.error("services", "unknown_action",
                               f"unknown services action: {action}",
                               "use start, stop, restart, or status")
    targets = [name] if name else list(CORE_SERVICES)
    for target in targets:
        if target not in CORE_SERVICES:
            return responses.error("services", "unknown_service",
                                   f"unknown service: {target}",
                                   "valid services: " + ", ".join(CORE_SERVICES))
    new_health = "running" if action in ("start", "restart") else "stopped"
    for target in targets:
        _save_service(state_dir, target, new_health)
    return status(state_dir=state_dir)
