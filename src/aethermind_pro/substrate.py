"""Substrate ownership and active-primitive selection.

Derived from docs/SUBSTRATE_OWNERSHIP.md lines 9-37 and
docs/AETHERMIND_PRIMITIVE_MCP.md.

Precedence:
1. A compatible user-managed external primitive wins.
2. An incompatible external primitive blocks unless the user explicitly selects bundled.
3. The bundled compatible primitive is used when no external install exists.
4. Pro never silently overwrites/downgrades/hides/replaces a user-managed install.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from . import primitive_mcp

ACTIVE_SOURCES = ("external", "bundled", "external_incompatible", "missing")


def select_active(
    external: Optional[Dict[str, Any]] = None,
    *,
    user_selected_bundled: bool = False,
) -> Dict[str, Any]:
    """Resolve which substrate is active under precedence rules.

    ``external`` (when present) describes a detected user-managed primitive:
    ``{"version": str, "compatible": bool, "source_ref": str}``.
    """
    if external is None:
        return {
            "active_source": "bundled",
            "version": primitive_mcp.BUNDLED_VERSION,
            "compatibility_range": primitive_mcp.COMPATIBILITY_RANGE,
            "source_ref": "bundled",
            "provenance": "bundled",
            "selection_reason": "no_external_install",
            "mutates_user_install": False,
        }

    if external.get("compatible"):
        return {
            "active_source": "external",
            "version": external.get("version", "unknown"),
            "compatibility_range": primitive_mcp.COMPATIBILITY_RANGE,
            "source_ref": external.get("source_ref", "user_managed"),
            "provenance": "user_managed",
            "selection_reason": "compatible_user_managed_install",
            "mutates_user_install": False,
        }

    # Incompatible external install: block unless the user explicitly chose bundled.
    if user_selected_bundled:
        return {
            "active_source": "bundled",
            "version": primitive_mcp.BUNDLED_VERSION,
            "compatibility_range": primitive_mcp.COMPATIBILITY_RANGE,
            "source_ref": "bundled",
            "provenance": "bundled",
            "selection_reason": "user_selected_bundled_after_incompatible_external",
            "mutates_user_install": False,
        }

    return {
        "active_source": "external_incompatible",
        "version": external.get("version", "unknown"),
        "compatibility_range": primitive_mcp.COMPATIBILITY_RANGE,
        "source_ref": external.get("source_ref", "user_managed"),
        "provenance": "user_managed",
        "selection_reason": "external_install_incompatible_blocked",
        "mutates_user_install": False,
    }


def status(
    data_root: "str | Path | None" = None,
    *,
    external: Optional[Dict[str, Any]] = None,
    user_selected_bundled: bool = False,
) -> Dict[str, Any]:
    """Build the `substrate status --json` payload (docs/SUBSTRATE_OWNERSHIP.md lines 24-34)."""
    active = select_active(external, user_selected_bundled=user_selected_bundled)

    has_visible_layers = False
    store_initialized = False
    if data_root is not None:
        store_status = primitive_mcp.call("status", {"data_root": str(data_root)})
        if store_status.get("ok"):
            store_initialized = bool(store_status.get("initialized"))
            has_visible_layers = (store_status.get("visible_layers") or 0) > 0

    return {
        "active_source": active["active_source"],
        "version": active["version"],
        "compatibility_range": active["compatibility_range"],
        "source_ref": active["source_ref"],
        "provenance": active["provenance"],
        "selection_reason": active["selection_reason"],
        "network_required": False,
        "mutates_store": active["active_source"] in ("external", "bundled"),
        "mutates_user_install": active["mutates_user_install"],
        "store_initialized": store_initialized,
        "has_visible_layers": has_visible_layers,
    }


def substrate_mode_label(active_source: str) -> str:
    """Map an active source to the evidence taxonomy ``substrate_mode`` label."""
    return {
        "external": "preinstalled_compatible",
        "external_incompatible": "preinstalled_incompatible",
        "bundled": "bundled_bootstrap",
        "missing": "missing_blocked",
    }.get(active_source, "missing_blocked")
