"""Host-local Ember/CORTEX pressure/verdict/repair semantics.

Derived from docs/PRO_SYSTEM_CONTRACT.md line 12 (Ember/CORTEX role) and
docs/plans/local-coordinator-source-contract-spec.md lines 135-162.

This is portable pressure/verdict/repair logic only. It does not package a private
Ember deployment and degrades honestly when an actual Cairn-network Ember is absent.
It never blocks export of customer-owned state.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

VERDICTS = ("proceed", "pause", "repair", "blocked", "unknown")
REPAIR_LANES = (
    "refresh_continuity",
    "review_trust",
    "fix_substrate",
    "configure_root",
    "check_harness",
    "unknown",
)


def coordinate(
    continuity_state: str,
    *,
    substrate_state: str = "available",
    trust_state: str = "trusted",
    map_id: Optional[str] = None,
    root_id: Optional[str] = None,
    trust_event_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Produce a CORTEX verdict over a root's coordinated state."""
    pressure_codes: List[str] = []
    repair_lanes: List[str] = []
    next_actions: List[str] = []
    verdict = "proceed"

    if substrate_state in ("missing", "incompatible", "blocked"):
        verdict = "blocked"
        pressure_codes.append("substrate_unavailable")
        repair_lanes.append("fix_substrate")
        next_actions.append("resolve the primitive substrate before coordinating")

    if trust_state in ("review_required", "questionable"):
        verdict = _escalate(verdict, "pause")
        pressure_codes.append("trust_review_pending")
        repair_lanes.append("review_trust")
        next_actions.append("complete trust review before relying on this material")
    elif trust_state == "dangerous":
        verdict = "blocked"
        pressure_codes.append("dangerous_material_detected")
        repair_lanes.append("review_trust")
        next_actions.append("dangerous material reported; do not trust it")

    if continuity_state == "missing":
        verdict = _escalate(verdict, "repair")
        pressure_codes.append("continuity_missing")
        repair_lanes.append("refresh_continuity")
        next_actions.append("run investigate to create first continuity value")
    elif continuity_state == "stale":
        verdict = _escalate(verdict, "pause")
        pressure_codes.append("continuity_stale")
        repair_lanes.append("refresh_continuity")
        next_actions.append("refresh continuity before strong coordination claims")
    elif continuity_state == "corrupt":
        verdict = _escalate(verdict, "repair")
        pressure_codes.append("continuity_corrupt")
        repair_lanes.append("refresh_continuity")
        next_actions.append("continuity store is corrupt; re-initialize after review")
    elif continuity_state == "unknown":
        verdict = _escalate(verdict, "pause")
        pressure_codes.append("continuity_unknown")

    if not next_actions:
        next_actions.append("continuity is fresh; proceed")

    return {
        "verdict": verdict,
        "pressure_codes": pressure_codes,
        "repair_lanes": repair_lanes,
        "next_actions": next_actions,
        "basis": {
            "map_id": map_id,
            "root_id": root_id,
            "trust_event_id": trust_event_id,
        },
    }


_ORDER = {"proceed": 0, "pause": 1, "repair": 2, "blocked": 3, "unknown": 1}


def _escalate(current: str, candidate: str) -> str:
    """Raise the verdict to the more severe of the two (blocked > repair > pause > proceed)."""
    if _ORDER.get(candidate, 0) > _ORDER.get(current, 0):
        return candidate
    return current
