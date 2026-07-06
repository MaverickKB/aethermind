"""Customer-selected, host-visible root configuration.

Derived from docs/PRO_SYSTEM_CONTRACT.md line 27 (`roots`) and
docs/plans/local-coordinator-source-contract-spec.md lines 54-79.

Roots are explicit and policy-bound. Hidden cwd / private profile assumptions are
rejected. Support/audit contexts use root hashes, never raw paths.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import workspace
from .state import ProState, stable_root_id

PATH_POLICIES = ("explicit_user_selected", "denied", "removed", "unknown")
STORE_STATES = ("present", "created", "missing", "blocked", "corrupt", "unknown")
TRUST_STATES = ("trusted", "review_required", "questionable", "dangerous", "unknown")


def resolve_root(project_root: Optional[str]) -> Tuple[Optional[Path], Optional[str]]:
    """Resolve an explicit project root.

    Returns (path, error_code). ``error_code`` is one of:
    ``project_root_required``, ``root_not_found``.
    """
    if not project_root:
        return None, "project_root_required"
    path = Path(project_root).expanduser()
    try:
        path = path.resolve()
    except OSError:
        return None, "root_not_found"
    if not path.exists() or not path.is_dir():
        return None, "root_not_found"
    return path, None


def build_root_record(path: Path, *, store_state: str = "unknown",
                      trust_state: str = "unknown",
                      last_layer_id: Optional[str] = None,
                      last_seen_at: Optional[str] = None) -> Dict:
    summary = workspace.inspect_workspace(path)
    return {
        "root_id": stable_root_id(path),
        "display_name": path.name or str(path),
        "path_policy": "explicit_user_selected",
        "root_kind": summary["kind"],
        "aethermind_store": store_state,
        "trust_state": trust_state,
        "last_seen_at": last_seen_at,
        "last_layer_id": last_layer_id,
    }


class RootsRegistry:
    def __init__(self, state_dir: "str | Path | None" = None):
        self.state = ProState(state_dir)

    def list(self) -> List[Dict]:
        return list(self.state.load().get("roots", []))

    def add(self, record: Dict) -> Dict:
        data = self.state.load()
        roots = [r for r in data.get("roots", []) if r.get("root_id") != record["root_id"]]
        roots.append(record)
        data["roots"] = roots
        self.state.save(data)
        return record

    def remove(self, root_id: str) -> bool:
        data = self.state.load()
        before = data.get("roots", [])
        after = [r for r in before if r.get("root_id") != root_id]
        data["roots"] = after
        self.state.save(data)
        return len(after) != len(before)

    def get(self, root_id: str) -> Optional[Dict]:
        for record in self.list():
            if record.get("root_id") == root_id:
                return record
        return None
