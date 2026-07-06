"""Evidence taxonomy (OSS release-honesty ladder).

The taxonomy makes false-green promotion impossible by schema, not by convention:
``validate_evidence`` rejects any label set that claims a tier its surfaces cannot
support, and the gate predicates below refuse source-tree evidence for the stronger
distribution-artifact, clean-VM, and tagged-release gates.

The ladder is re-aimed at open-source reality (there is no license, no protected
binary, no call-home):

    tier_1_source_contract  -> tests pass against the source tree
    tier_2_dist_tarball     -> a built sdist/wheel/tarball reproduces + passes its checks
    tier_3_clean_vm_smoke   -> the distribution installs and runs on a clean machine
    tier_4_tagged_release   -> a signed, tagged release with a published checksum manifest

Building tiers 2-4 is Phase 4 work (build_oss_distribution.py /
verify_oss_distribution.py). This module only lets tier 1 be *claimed* and blocks the
rest honestly until that machinery exists.
"""

from __future__ import annotations

from typing import Dict, List

# --- Allowed label vocabularies ---

PROOF_SURFACES = ("source_tree", "dist_tarball", "clean_machine")
PLATFORM_MODES = ("simulated", "native")
NETWORK_MODES = ("offline", "online")
SUBSTRATE_MODES = (
    "preinstalled_compatible",
    "preinstalled_incompatible",
    "bundled_bootstrap",
    "missing_blocked",
)
OPERATOR_TYPES = ("maintainer", "internal_agent", "contributor", "user")
OBSERVATION_MODES = ("cli_only", "visual_keyboard_mouse", "automated_ci")
DISTRIBUTION_MODES = ("none", "dist_tarball", "tagged_release")

REQUIRED_LABEL_KEYS = (
    "proof_surface",
    "platform_mode",
    "network_mode",
    "substrate_mode",
    "operator_type",
    "tier_eligible",
    "observation_mode",
    "distribution_mode",
)

# Tier this source-contract implementation may claim.
TIER_SOURCE_CONTRACT = "tier_1_source_contract"

# Tiers that source-tree evidence may NEVER claim.
STRONGER_TIERS = frozenset(
    {
        "tier_2_dist_tarball",
        "tier_3_clean_vm_smoke",
        "tier_4_tagged_release",
        "dist_tarball",
        "clean_machine",
        "clean_vm",
        "released",
        "tagged_release",
        "shippable",
        "public",
    }
)

# Standard machine-readable blockers that keep source-tree proof from being read
# as anything stronger.
STANDARD_BLOCKERS: List[str] = [
    "not_dist_tarball",
    "not_clean_vm_smoke",
    "not_tagged_release",
    "not_shippable",
    "not_public_proof",
]


class EvidenceError(ValueError):
    """Raised when an evidence label set would allow false-green promotion."""


def source_tree_evidence(operator_type: str = "internal_agent", **overrides) -> Dict:
    """Return the canonical source-tree, CLI-only, no-distribution evidence block.

    This is the only evidence posture this implementation phase is allowed to emit;
    the distribution/clean-VM/release tiers are Phase 4 work.
    """
    labels: Dict = {
        "proof_surface": "source_tree",
        "platform_mode": "native",
        "network_mode": "offline",
        "substrate_mode": "bundled_bootstrap",
        "operator_type": operator_type,
        "observation_mode": "cli_only",
        "distribution_mode": "none",
        "tier_eligible": [TIER_SOURCE_CONTRACT],
        "blockers": list(STANDARD_BLOCKERS),
    }
    labels.update(overrides)
    validate_evidence(labels)
    return labels


def error_evidence() -> Dict:
    """Evidence block for bounded error responses: claims nothing."""
    return {
        "proof_surface": "source_tree",
        "tier_eligible": [],
        "blockers": ["source_contract_not_satisfied"],
    }


def validate_evidence(labels: Dict) -> None:
    """Reject label sets that claim a tier their surfaces cannot support."""
    for key in REQUIRED_LABEL_KEYS:
        if key not in labels:
            raise EvidenceError(f"missing required evidence label: {key}")

    _check_value("proof_surface", labels["proof_surface"], PROOF_SURFACES)
    _check_value("platform_mode", labels["platform_mode"], PLATFORM_MODES)
    _check_value("network_mode", labels["network_mode"], NETWORK_MODES)
    _check_value("substrate_mode", labels["substrate_mode"], SUBSTRATE_MODES)
    _check_value("operator_type", labels["operator_type"], OPERATOR_TYPES)
    _check_value("observation_mode", labels["observation_mode"], OBSERVATION_MODES)
    _check_value("distribution_mode", labels["distribution_mode"], DISTRIBUTION_MODES)

    tiers = labels.get("tier_eligible") or []
    if not isinstance(tiers, list):
        raise EvidenceError("tier_eligible must be a list")

    # False-green prevention by schema: source-tree evidence may never claim a
    # stronger (built-artifact / clean-VM / released) tier.
    if labels["proof_surface"] == "source_tree":
        forbidden = STRONGER_TIERS.intersection(tiers)
        if forbidden:
            raise EvidenceError(
                "source-tree evidence cannot claim stronger tiers: "
                + ", ".join(sorted(forbidden))
            )


def _check_value(key: str, value, allowed) -> None:
    if value not in allowed:
        raise EvidenceError(f"invalid {key}: {value!r} (allowed: {', '.join(allowed)})")


# --- Gate eligibility predicates ---


def dist_tarball_eligible(labels: Dict) -> bool:
    """A built distribution tarball must prove itself off the source tree."""
    if labels.get("proof_surface") not in ("dist_tarball", "clean_machine"):
        return False
    if labels.get("distribution_mode") not in ("dist_tarball", "tagged_release"):
        return False
    return True


def clean_vm_smoke_eligible(labels: Dict) -> bool:
    """A clean-VM smoke proof requires the distribution to install and run natively
    on a fresh machine, observed end to end."""
    if labels.get("proof_surface") != "clean_machine":
        return False
    if labels.get("platform_mode") != "native":
        return False
    if labels.get("substrate_mode") == "bundled_bootstrap":
        return False
    if labels.get("observation_mode") not in ("visual_keyboard_mouse", "automated_ci"):
        return False
    return True


def tagged_release_eligible(labels: Dict) -> bool:
    """A tagged release additionally requires clean-VM proof and a published,
    checksum-manifested tarball under a release tag."""
    if not clean_vm_smoke_eligible(labels):
        return False
    return labels.get("distribution_mode") == "tagged_release"
