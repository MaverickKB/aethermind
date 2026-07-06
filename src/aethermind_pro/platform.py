"""Platform support/status and optional UI surfaces.

Platform status reports where the source-available build is known to run. `tracker`
and `admin-ui` are optional visual surfaces; core commands never require them, so they
report as available-but-not-required.
"""

from __future__ import annotations

from typing import Any, Dict

from . import config, evidence, responses


def _evidence_block() -> Dict[str, Any]:
    return {
        "proof_surface": "source_tree",
        "tier_eligible": [evidence.TIER_SOURCE_CONTRACT],
        "blockers": list(evidence.STANDARD_BLOCKERS),
    }


def platform_status() -> Dict[str, Any]:
    current = config.current_platform()
    # macOS and Linux are primary; Windows is a later target.
    return responses.ok(
        "platform status",
        current_platform=current,
        primary_targets=["macos", "linux"],
        later_targets=["windows"],
        evidence=_evidence_block(),
    )


def tracker() -> Dict[str, Any]:
    return responses.ok(
        "tracker",
        status="optional_not_required_for_core",
        required_for_core=False,
        message="tracker/HUD is an optional visual surface; the CLI is complete without it",
        evidence=_evidence_block(),
    )


def admin_ui() -> Dict[str, Any]:
    return responses.ok(
        "admin-ui",
        status="optional_not_required_for_core",
        required_for_core=False,
        message="a web/admin UI is an optional visual surface; core control stays on the CLI",
        evidence=_evidence_block(),
    )
