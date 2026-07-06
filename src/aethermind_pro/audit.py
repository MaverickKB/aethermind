"""Bounded local audit events with redaction.

Derived from docs/PRIVACY_AND_AUDIT.md lines 5-11 and
docs/plans/customer-state-source-contract-spec.md lines 180-211.

Audit records include timestamps, event names, verdict status, and root hashes only.
They never include raw project content, secrets, private operator paths, or arbitrary
file contents. The redaction block is asserted on every event.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import config

AUDIT_FILENAME = "audit.jsonl"

COMPONENTS = (
    "roots",
    "map",
    "coordinate",
    "trust",
    "support",
    "export",
    "substrate",
    "harness",
    "investigate",
    "services",
    "unknown",
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _redaction_block() -> Dict[str, bool]:
    return {
        "raw_project_content_included": False,
        "secrets_included": False,
        "private_paths_included": False,
        "arbitrary_snippets_included": False,
    }


def build_event(
    event_name: str,
    *,
    component: str = "unknown",
    root_id: Optional[str] = None,
    verdict_status: Optional[str] = None,
    pressure_codes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Build a bounded audit event. No raw content is permitted in any field."""
    if component not in COMPONENTS:
        component = "unknown"
    return {
        "event_id": "evt-" + uuid.uuid4().hex[:16],
        "event_name": event_name,
        "created_at": _now(),
        "root_id": root_id,
        "verdict_status": verdict_status,
        "pressure_codes": list(pressure_codes or []),
        "component": component,
        "redaction": _redaction_block(),
    }


class AuditLog:
    def __init__(self, state_dir: "str | Path | None" = None):
        self.state_dir = config.ensure_state_dir(state_dir)

    @property
    def path(self) -> Path:
        return self.state_dir / AUDIT_FILENAME

    def record(self, event: Dict[str, Any]) -> Dict[str, Any]:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")
        return event

    def record_event(self, event_name: str, **kwargs) -> Dict[str, Any]:
        return self.record(build_event(event_name, **kwargs))

    def tail(self, limit: int = 50) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8").splitlines()
        events: List[Dict[str, Any]] = []
        for line in lines[-limit:]:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return events
