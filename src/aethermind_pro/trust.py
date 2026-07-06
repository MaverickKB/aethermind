"""Trusted-registry gate and trust review.

Derived from docs/PRO_SYSTEM_CONTRACT.md line 13, docs/PRIVACY_AND_AUDIT.md line 11,
docs/TRUST_PROTECTION_PREBUILD_BOUNDARY.md lines 31-50, and
docs/plans/trust-review-source-contract-spec.md.

Anything not in the trusted registry is untrusted until reviewed. Review classifies
material as safe, questionable, or dangerous: questionable requires human approval and
dangerous is reported immediately and never trusted. Headless CLI is sufficient.
Output never includes raw project content, secrets, snippets, or private paths.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from . import evidence, responses
from .audit import AuditLog
from .state import ProState

REGISTRY_VERSION = "aethermind-pro-trust-registry-v1"

DANGEROUS_CATEGORIES = (
    "prompt_injection_attempt",
    "credential_exfiltration_request",
    "private_path_or_topology_exposure",
    "malicious_code_indicator",
    "destructive_action_instruction",
    "policy_bypass_instruction",
    "untrusted_download_or_dependency",
    "provenance_mismatch",
    "unexpected_binary_or_generated_artifact",
    "raw_secret_detected",
    "unknown_high_risk",
)

# Bounded detection signals. Matches map to a category label only; raw text is never
# stored or emitted.
_DANGER_SIGNALS: Tuple[Tuple[str, str], ...] = (
    ("ignore previous instructions", "prompt_injection_attempt"),
    ("disregard the above", "prompt_injection_attempt"),
    ("disregard previous instructions", "prompt_injection_attempt"),
    ("override your system prompt", "prompt_injection_attempt"),
    ("exfiltrate", "credential_exfiltration_request"),
    ("send your api key", "credential_exfiltration_request"),
    ("begin rsa private key", "raw_secret_detected"),
    ("begin private key", "raw_secret_detected"),
    ("aws_secret_access_key", "raw_secret_detected"),
    ("rm -rf /", "destructive_action_instruction"),
    ("drop table", "destructive_action_instruction"),
    ("disable safety", "policy_bypass_instruction"),
    ("bypass the sandbox", "policy_bypass_instruction"),
    ("curl http", "untrusted_download_or_dependency"),
    ("wget http", "untrusted_download_or_dependency"),
)

UNTRUSTED_ORIGINS = ("downloaded", "external_agent", "public_release", "unknown")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _digest_of(subject_path: Optional[Path], subject_ref: str) -> str:
    if subject_path and subject_path.is_file():
        return "sha256:" + hashlib.sha256(subject_path.read_bytes()).hexdigest()
    return "ref:" + hashlib.sha256(subject_ref.encode("utf-8")).hexdigest()[:32]


def _scan(subject_path: Optional[Path]) -> List[str]:
    """Programmatic scan returning bounded danger categories (no raw text)."""
    if not subject_path or not subject_path.is_file():
        return []
    try:
        text = subject_path.read_text(encoding="utf-8", errors="ignore").lower()
    except OSError:
        return ["unexpected_binary_or_generated_artifact"]
    found: List[str] = []
    for needle, category in _DANGER_SIGNALS:
        if needle in text and category not in found:
            found.append(category)
    return found


class TrustRegistry:
    def __init__(self, state_dir: "str | Path | None" = None):
        self.state = ProState(state_dir)

    def find(self, digest: str) -> Optional[Dict[str, Any]]:
        for entry in self.state.load().get("trusted_registry", []):
            if entry.get("subject", {}).get("digest") == digest and entry.get("disposition") == "safe":
                return entry
        return None

    def add(self, entry: Dict[str, Any]) -> None:
        data = self.state.load()
        registry = [
            e for e in data.get("trusted_registry", [])
            if e.get("subject", {}).get("digest") != entry["subject"]["digest"]
        ]
        registry.append(entry)
        data["trusted_registry"] = registry
        self.state.save(data)


def review(
    subject: Optional[str],
    project_root: Optional[str] = None,
    *,
    origin: str = "downloaded",
    state_dir: "str | Path | None" = None,
) -> Dict[str, Any]:
    if not subject:
        return responses.error(
            "trust review",
            "subject_required",
            "trust review requires an explicit --subject",
            "aethermind-pro trust review --subject <path-or-ref> --project-root . --json",
        )

    subject_path: Optional[Path] = None
    candidate = Path(subject).expanduser()
    if candidate.exists():
        subject_path = candidate.resolve()

    digest = _digest_of(subject_path, subject)
    registry = TrustRegistry(state_dir)
    audit = AuditLog(state_dir)

    kind = "file" if subject_path and subject_path.is_file() else "external_material"

    # Already trusted entries pass without re-review.
    if registry.find(digest):
        return _output(audit, subject, digest, kind, "safe", [], state_dir,
                       next_action="material already trusted; you may proceed",
                       origin=origin, register=False)

    categories = _scan(subject_path)
    if categories:
        verdict = "dangerous"
    elif origin in UNTRUSTED_ORIGINS:
        verdict = "questionable"
    else:
        verdict = "safe"

    register = verdict == "safe"
    if register:
        registry.add({
            "registry_version": REGISTRY_VERSION,
            "entry_id": "trust-" + uuid.uuid4().hex[:16],
            "subject": {"kind": kind, "source_ref": _redacted_ref(subject), "digest": digest, "root_id": None},
            "provenance": {"origin": origin, "manifest_ref": None, "reviewed_at": _now(), "reviewer": "programmatic"},
            "disposition": "safe",
            "expires_at": None,
            "notes": "auto-approved by programmatic source-contract review",
        })

    next_action = {
        "safe": "material is safe; you may proceed",
        "questionable": "human approval required: run `aethermind-pro trust approve`",
        "dangerous": "dangerous material reported; do not trust it",
    }[verdict]

    return _output(audit, subject, digest, kind, verdict, categories, state_dir,
                   next_action=next_action, origin=origin, register=False)


def approve(subject_digest: Optional[str], *, state_dir: "str | Path | None" = None) -> Dict[str, Any]:
    if not subject_digest:
        return responses.error(
            "trust approve", "subject_digest_required",
            "trust approve requires --subject-digest",
            "aethermind-pro trust approve --subject-digest <digest> --json",
        )
    registry = TrustRegistry(state_dir)
    audit = AuditLog(state_dir)
    registry.add({
        "registry_version": REGISTRY_VERSION,
        "entry_id": "trust-" + uuid.uuid4().hex[:16],
        "subject": {"kind": "external_material", "source_ref": "human-approved", "digest": subject_digest, "root_id": None},
        "provenance": {"origin": "human_approved", "manifest_ref": None, "reviewed_at": _now(), "reviewer": "human"},
        "disposition": "safe",
        "expires_at": None,
        "notes": "human approved previously questionable material",
    })
    event = audit.record_event("trust_review_completed", component="trust", verdict_status="safe")
    return responses.ok(
        "trust approve",
        subject_digest=subject_digest,
        prior_verdict="questionable",
        approved_by="human-local-operator",
        audit_event_id=event["event_id"],
        next_action="material approved; you may proceed",
    )


def _output(audit: AuditLog, subject: str, digest: str, kind: str, verdict: str,
            categories: List[str], state_dir, *, next_action: str, origin: str,
            register: bool) -> Dict[str, Any]:
    if verdict == "dangerous":
        event_name = "trust_dangerous_reported"
    elif verdict == "questionable":
        event_name = "trust_questionable_pending_human"
    else:
        event_name = "trust_review_completed"
    event = audit.record_event(event_name, component="trust", verdict_status=verdict,
                               pressure_codes=["trust_review"])

    labels = {
        "proof_surface": "source_tree",
        "observation_mode": "cli_only",
        "distribution_mode": "none",
        "tier_eligible": [evidence.TIER_SOURCE_CONTRACT],
        "blockers": list(evidence.STANDARD_BLOCKERS),
    }
    return responses.ok(
        "trust review",
        subject={
            "kind": kind,
            "digest": digest,
            "source_summary": _redacted_ref(subject),
            "root_id": None,
        },
        review={
            "verdict": verdict,
            "pressure_codes": ["trust_review"],
            "evidence_labels": labels,
            "dangerous_content_categories": categories,
            "human_approval_required": verdict == "questionable",
            "audit_event_id": event["event_id"],
        },
        next_action=next_action,
    )


def _redacted_ref(subject: str) -> str:
    """Return a bounded, redacted reference: only the final path component."""
    name = Path(subject).name or subject
    return f"<redacted>/{name}"
