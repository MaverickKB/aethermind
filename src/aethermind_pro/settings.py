"""Local data settings, advanced harness behavior, and disabled-by-default Cairn context.

Derived from docs/PRO_SYSTEM_CONTRACT.md line 36 and
docs/plans/local-coordinator-source-contract-spec.md lines 189-211.

Cairn-network context is disabled by default and can only be enabled through an
explicit advanced setting. Product behavior never requires Cairn network availability.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from . import evidence, responses
from .state import ProState

ADVANCED_KEYS = (
    "cairn-network.enabled",
    "cairn-network.auto_detection",
    "provenance.sign_new_layers",
    "provenance.key_path",
)


def _evidence_block() -> Dict[str, Any]:
    return {
        "proof_surface": "source_tree",
        "tier_eligible": [evidence.TIER_SOURCE_CONTRACT],
        "blockers": list(evidence.STANDARD_BLOCKERS),
    }


def show(*, state_dir: "str | Path | None" = None) -> Dict[str, Any]:
    data = ProState(state_dir).load()
    return responses.ok("settings show", settings=data.get("settings", {}),
                        evidence=_evidence_block())


def set_value(key: Optional[str], value: Optional[str], *,
              state_dir: "str | Path | None" = None) -> Dict[str, Any]:
    if not key:
        return responses.error("settings set", "key_required",
                               "settings set requires a key and value",
                               "advanced keys: " + ", ".join(ADVANCED_KEYS))
    state = ProState(state_dir)
    data = state.load()
    settings = data.setdefault("settings", {})
    cairn = settings.setdefault("cairn_network_context",
                                {"enabled": False, "mode": "disabled_by_default",
                                 "configured_core": None, "auto_detection": False})

    provenance = settings.setdefault("provenance",
                                     {"sign_new_layers": False, "key_path": None})

    bool_value = str(value).lower() in ("1", "true", "yes", "on")
    stored_value: Any = bool_value
    if key == "cairn-network.enabled":
        cairn["enabled"] = bool_value
        cairn["mode"] = "manually_enabled" if bool_value else "disabled_by_default"
    elif key == "cairn-network.auto_detection":
        cairn["auto_detection"] = bool_value
    elif key == "provenance.sign_new_layers":
        provenance["sign_new_layers"] = bool_value
    elif key == "provenance.key_path":
        # A path value, not a boolean; empty/none clears it.
        stored_value = None if value is None or str(value).lower() in ("", "none") else str(value)
        provenance["key_path"] = stored_value
    else:
        return responses.error("settings set", "unknown_key",
                               f"unknown or unsupported setting key: {key}",
                               "advanced keys: " + ", ".join(ADVANCED_KEYS))
    state.save(data)
    return responses.ok("settings set", key=key, value=stored_value,
                        settings=settings, evidence=_evidence_block())
