"""Customer-owned local Pro state.

Derived from docs/PRO_SYSTEM_CONTRACT.md (state is customer-owned and exportable),
docs/PRIVACY_AND_AUDIT.md (no upload by default), and
docs/plans/local-coordinator-source-contract-spec.md (root records, disabled-by-default
Cairn-network context).

State is a single JSON document under the resolved state directory. It holds only
bounded, support-safe metadata: settings, the root registry, harness configs, and the
trusted registry. It never stores raw project content.
"""

from __future__ import annotations

import hashlib
import json
import platform
from pathlib import Path
from typing import Any, Dict

from . import config

STATE_FILENAME = "pro_state.json"
STATE_VERSION = "aethermind-pro-state-v1"


def default_state() -> Dict[str, Any]:
    return {
        "state_version": STATE_VERSION,
        "settings": {
            "cairn_network_context": {
                "enabled": False,
                "mode": "disabled_by_default",
                "configured_core": None,
                "auto_detection": False,
            }
        },
        "roots": [],
        "harnesses": {},
        "trusted_registry": [],
        "services": {},
    }


class ProState:
    """Read/modify/write the customer-owned Pro state document."""

    def __init__(self, state_dir: "str | Path | None" = None):
        self.state_dir = config.ensure_state_dir(state_dir)

    @property
    def path(self) -> Path:
        return self.state_dir / STATE_FILENAME

    def load(self) -> Dict[str, Any]:
        if not self.path.exists():
            return default_state()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            # Corrupt local state must not be treated as fresh; return a fresh skeleton
            # so the caller can degrade honestly rather than crash.
            return default_state()
        if not isinstance(data, dict):
            return default_state()
        # Merge missing top-level keys so older states stay readable.
        merged = default_state()
        merged.update(data)
        return merged

    def save(self, data: Dict[str, Any]) -> None:
        self.path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def stable_root_id(path: "str | Path") -> str:
    """Stable, non-reversible identifier for a root path.

    Used in support/audit contexts so private paths are never emitted
    (docs/PRIVACY_AND_AUDIT.md line 5)."""
    resolved = str(Path(path).expanduser().resolve())
    digest = hashlib.sha256(resolved.encode("utf-8")).hexdigest()
    return "root-" + digest[:16]


def host_id() -> str:
    """Stable local host identifier that does not expose a private hostname."""
    raw = platform.node() or "unknown-host"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return "host-" + digest[:16]
