"""Customer-owned state export.

Export of customer-owned Pro state is always available. It never includes secrets,
raw project content, private operator paths, or active product code.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from . import config, evidence, responses
from .audit import AuditLog
from .state import ProState

EXCLUDED = ["secrets", "raw_project_content", "private_operator_paths", "active_product_code"]


def _evidence_block() -> Dict[str, Any]:
    return {
        "proof_surface": "source_tree",
        "tier_eligible": [evidence.TIER_SOURCE_CONTRACT],
        "blockers": list(evidence.STANDARD_BLOCKERS),
    }


def export_state(output: Optional[str], *, state_dir: "str | Path | None" = None) -> Dict[str, Any]:
    data = ProState(state_dir).load()
    audit_tail = AuditLog(state_dir).tail(limit=50)

    bundle = {
        "export_version": "aethermind-pro-export-v1",
        "settings": data.get("settings", {}),
        "root_registry": [
            {"root_id": r.get("root_id"), "root_kind": r.get("root_kind"),
             "aethermind_store": r.get("aethermind_store"), "last_layer_id": r.get("last_layer_id")}
            for r in data.get("roots", [])
        ],
        "audit_tail_redacted": audit_tail,
        "continuity_manifest": {"roots": len(data.get("roots", []))},
        "customer_owned_artifacts": True,
    }

    output_summary: Any
    if output:
        out_path = Path(output).expanduser().resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        output_summary = str(out_path)
    else:
        output_summary = "<in-memory export summary>"

    return responses.ok(
        "export",
        output=output_summary,
        included={
            "settings": True,
            "root_registry": True,
            "audit_tail_redacted": True,
            "continuity_manifest": True,
            "customer_owned_artifacts": True,
        },
        excluded=list(EXCLUDED),
        always_available=True,
        evidence=_evidence_block(),
    )
