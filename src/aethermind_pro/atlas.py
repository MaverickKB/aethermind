"""Atlas-style local machine map core.

Derived from docs/PRO_SYSTEM_CONTRACT.md line 11 (Atlas role) and
docs/plans/local-coordinator-source-contract-spec.md lines 81-133.

The map is local, bounded, and support-safe. It never contains raw project content,
secrets, private operator paths, or private Cairn topology.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import config, evidence, primitive_mcp, substrate
from .state import host_id

# Layers older than this are reported stale rather than fresh.
STALE_AFTER_SECONDS = 30 * 24 * 60 * 60

CONTINUITY_STATES = ("fresh", "stale", "missing", "corrupt", "blocked", "unknown")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_str() -> str:
    return _now().strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_ts(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def assess_continuity(root_path: Path) -> Dict[str, Any]:
    """Classify continuity for a root: state, visible layer count, last layer id."""
    status = primitive_mcp.call("status", {"data_root": str(root_path)})
    if not status.get("ok") or not status.get("initialized"):
        return {"state": "missing", "visible_layers": 0, "last_layer_id": None}

    read = primitive_mcp.call("read_layers", {"data_root": str(root_path)})
    if not read.get("ok"):
        return {"state": "blocked", "visible_layers": 0, "last_layer_id": None}
    if read.get("corrupt"):
        return {"state": "corrupt", "visible_layers": read.get("count", 0), "last_layer_id": None}

    layers: List[Dict[str, Any]] = read.get("layers", [])
    if not layers:
        return {"state": "missing", "visible_layers": 0, "last_layer_id": None}

    last = layers[-1]
    last_ts = _parse_ts(last.get("created_at"))
    if last_ts is None:
        state = "unknown"
    elif (_now() - last_ts).total_seconds() > STALE_AFTER_SECONDS:
        state = "stale"
    else:
        state = "fresh"
    return {"state": state, "visible_layers": len(layers), "last_layer_id": last.get("layer_id")}


def build_map(
    root_records: List[Dict[str, Any]],
    *,
    external: Optional[Dict[str, Any]] = None,
    cairn_enabled: bool = False,
) -> Dict[str, Any]:
    """Build the bounded Atlas machine map over configured roots."""
    sub = substrate.status(external=external)
    primitive_state = {
        "external": "available",
        "bundled": "available",
        "external_incompatible": "incompatible",
        "missing": "missing",
    }.get(sub["active_source"], "missing")

    counts = {"fresh": 0, "stale": 0, "missing": 0, "corrupt": 0, "unknown": 0}
    roots_out: List[Dict[str, Any]] = []
    for record in root_records:
        roots_out.append(record)
        state = record.get("aethermind_store", "unknown")
        # Normalize root-record store labels into continuity counts.
        if state in ("present", "created"):
            counts["fresh"] += 1
        elif state == "corrupt":
            counts["corrupt"] += 1
        elif state in ("missing", "blocked"):
            counts["missing"] += 1
        else:
            counts["unknown"] += 1

    return {
        "map_id": "map-" + uuid.uuid4().hex[:16],
        "created_at": _now_str(),
        "host": {
            "host_id": host_id(),
            "platform": config.current_platform(),
            "platform_mode": "native",
            "network_context": "cairn_enabled_manual" if cairn_enabled else "cairn_disabled",
        },
        "roots": roots_out,
        "components": {
            "primitive_substrate": primitive_state,
            "atlas": "available",
            "cortex": "available",
            "trust_review": "available",
            "harness_contract": "available",
        },
        "continuity": counts,
        "evidence": {
            "proof_surface": "source_tree",
            "tier_eligible": [evidence.TIER_SOURCE_CONTRACT],
            "blockers": list(evidence.STANDARD_BLOCKERS),
        },
    }
