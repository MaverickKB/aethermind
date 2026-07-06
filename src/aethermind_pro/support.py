"""Redacted support bundle export.

Derived from docs/PRIVACY_AND_AUDIT.md lines 7-11,
docs/PRO_SYSTEM_CONTRACT.md line 40, and
docs/plans/customer-state-source-contract-spec.md lines 146-178.

Support bundles include only support-safe evidence: component health, redacted
audit tails, root hashes, map summaries, pressure codes, and substrate version. They
exclude raw project content, secrets, private operator paths, arbitrary file contents,
and private topology.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import atlas, config, evidence, responses, substrate
from .audit import AuditLog
from .state import ProState, host_id

EXCLUDED = [
    "raw_project_content",
    "secrets",
    "private_operator_paths",
    "arbitrary_file_contents",
    "private_topology",
    "unredacted_dangerous_prompt_text",
    "generated_pyc_cache_artifacts",
]


def _evidence_block() -> Dict[str, Any]:
    return {
        "proof_surface": "source_tree",
        "observation_mode": "cli_only",
        "tier_eligible": [evidence.TIER_SOURCE_CONTRACT],
        "blockers": list(evidence.STANDARD_BLOCKERS),
    }


def _redact_audit(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Keep only bounded event fields; drop anything not on the allowlist."""
    allowed = ("event_id", "event_name", "created_at",
               "root_id", "verdict_status", "pressure_codes", "component")
    redacted = []
    for event in events:
        redacted.append({k: event.get(k) for k in allowed if k in event})
    return redacted


def support_bundle(output: Optional[str], *, state_dir: "str | Path | None" = None) -> Dict[str, Any]:
    data = ProState(state_dir).load()
    sub = substrate.status()
    audit_tail = _redact_audit(AuditLog(state_dir).tail(limit=50))

    root_hashes = [r.get("root_id") for r in data.get("roots", [])]
    pressure_codes: List[str] = []
    for event in audit_tail:
        pressure_codes.extend(event.get("pressure_codes", []) or [])

    bundle = {
        "support_bundle_version": "aethermind-pro-support-v1",
        "host_id": host_id(),
        "platform": config.current_platform(),
        "distribution": "source-available",
        "component_health": {
            "primitive_substrate": sub["active_source"],
            "atlas": "available",
            "cortex": "available",
            "trust_review": "available",
            "harness_contract": "available",
        },
        "substrate": {"version": sub["version"], "provenance": sub["provenance"]},
        "root_hashes": root_hashes,
        "map_summary": {"configured_roots": len(root_hashes)},
        "pressure_codes": sorted(set(pressure_codes)),
        "audit_tail_redacted": audit_tail,
        "evidence_tier": "source_contract_support_safe",
        "excluded": list(EXCLUDED),
    }

    output_summary: Any
    if output:
        out_path = Path(output).expanduser().resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        output_summary = str(out_path)
    else:
        output_summary = "<in-memory support summary>"

    return responses.ok(
        "support-bundle",
        output=output_summary,
        bundle=bundle,
        excluded=list(EXCLUDED),
        evidence=_evidence_block(),
    )


def _harness_checks(state_dir: "str | Path | None") -> Dict[str, Any]:
    """Summarize harness integration so newly installed harnesses surface here."""
    from . import harnesses as harnesses_mod
    discovered = harnesses_mod.discover(state_dir=state_dir).get("harnesses", [])
    detected = [h["name"] for h in discovered if h.get("detected")]
    integrated = [h["name"] for h in discovered if h.get("integrated")]
    pending = [name for name in detected if name not in integrated]
    summary: Dict[str, Any] = {
        "detected": detected,
        "integrated": integrated,
        "detected_not_integrated": pending,
        "integration_default": "deny_until_approved",
    }
    if pending:
        summary["next_action"] = harnesses_mod.INTEGRATE_HINT.format(name=pending[0])
    else:
        summary["next_action"] = "aethermind-pro harnesses discover --json (re-run after installing a new harness)"
    return summary


def doctor(*, project_root: Optional[str] = None, state_dir: "str | Path | None" = None,
           human: bool = False) -> Dict[str, Any]:
    """`doctor` explains local health without exposing raw customer content."""
    sub = substrate.status()
    checks = {
        "primitive_substrate": sub["active_source"],
        "distribution": "source-available",
        "state_dir_present": True,
        "platform": config.current_platform(),
        "harnesses": _harness_checks(state_dir),
    }
    if project_root:
        from . import roots
        path, err = roots.resolve_root(project_root)
        if err:
            checks["project_root"] = err
        else:
            assert path is not None
            checks["project_root"] = atlas.assess_continuity(path)["state"]

    result = responses.ok("doctor", checks=checks, evidence=_evidence_block())
    if human:
        lines = ["AetherMind Pro doctor", "----------------------"]
        for key, value in checks.items():
            lines.append(f"{key}: {value}")
        lines.append("Limits: source-contract proof only; not artifact/beta/customer/public proof")
        result["human"] = "\n".join(lines)
    return result
