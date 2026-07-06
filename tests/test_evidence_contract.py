"""Evidence taxonomy contract (OSS release-honesty ladder).

These tests prove false-green promotion is impossible by schema. They support only
Tier 1 source-contract health and assert source-tree evidence cannot satisfy the
distribution-artifact, clean-VM, or tagged-release gates.
"""

import pytest

from aethermind_pro import evidence


def test_required_labels_present():
    labels = evidence.source_tree_evidence()
    for key in evidence.REQUIRED_LABEL_KEYS:
        assert key in labels
    assert labels["proof_surface"] == "source_tree"
    assert labels["observation_mode"] == "cli_only"
    assert labels["distribution_mode"] == "none"
    assert labels["tier_eligible"] == [evidence.TIER_SOURCE_CONTRACT]


def test_blockers_cover_all_stronger_claims():
    labels = evidence.source_tree_evidence()
    for blocker in (
        "not_dist_tarball", "not_clean_vm_smoke", "not_tagged_release",
        "not_shippable", "not_public_proof",
    ):
        assert blocker in labels["blockers"]


def test_tier_eligible_has_no_stronger_tier():
    labels = evidence.source_tree_evidence()
    assert not evidence.STRONGER_TIERS.intersection(labels["tier_eligible"])


def test_promotion_to_stronger_tier_fails_by_schema():
    with pytest.raises(evidence.EvidenceError):
        evidence.source_tree_evidence(tier_eligible=["tier_1_source_contract", "tagged_release"])


def test_invalid_label_value_rejected():
    with pytest.raises(evidence.EvidenceError):
        evidence.validate_evidence({
            **evidence.source_tree_evidence(),
            "proof_surface": "made_up",
        })


def test_source_tree_not_eligible_for_any_strong_gate():
    labels = evidence.source_tree_evidence()
    assert evidence.dist_tarball_eligible(labels) is False
    assert evidence.clean_vm_smoke_eligible(labels) is False
    assert evidence.tagged_release_eligible(labels) is False


def test_clean_vm_smoke_requires_native_clean_machine_observed():
    strong = {
        "proof_surface": "clean_machine",
        "platform_mode": "native",
        "network_mode": "offline",
        "substrate_mode": "preinstalled_compatible",
        "operator_type": "internal_agent",
        "observation_mode": "visual_keyboard_mouse",
        "distribution_mode": "dist_tarball",
        "tier_eligible": [],
        "blockers": [],
    }
    assert evidence.clean_vm_smoke_eligible(strong) is True
    # Drop to source-tree observation only: no longer eligible.
    strong["proof_surface"] = "source_tree"
    assert evidence.clean_vm_smoke_eligible(strong) is False


def test_tagged_release_requires_release_distribution():
    near_release = {
        "proof_surface": "clean_machine",
        "platform_mode": "native",
        "network_mode": "online",
        "substrate_mode": "preinstalled_compatible",
        "operator_type": "user",
        "observation_mode": "automated_ci",
        "distribution_mode": "dist_tarball",
        "tier_eligible": [],
        "blockers": [],
    }
    # A dist tarball on a clean machine is a smoke proof, not yet a tagged release.
    assert evidence.clean_vm_smoke_eligible(near_release) is True
    assert evidence.tagged_release_eligible(near_release) is False
    near_release["distribution_mode"] = "tagged_release"
    assert evidence.tagged_release_eligible(near_release) is True
