"""Services, status, doctor, and support bundle contract.

Controlling docs: docs/PRO_SYSTEM_CONTRACT.md lines 23, 32, 40,
docs/PRIVACY_AND_AUDIT.md lines 3-12,
docs/plans/customer-state-source-contract-spec.md lines 146-178.
"""

import json

from aethermind_pro import coordinator, investigate, services, support


def test_services_status_ui_not_required(state_dir):
    result = services.status(state_dir=state_dir)
    assert result["ok"] is True
    assert result["ui_required_for_core"] is False
    assert result["services"]["atlas"] in services.HEALTH_STATES
    assert result["services"]["tracker"] == "optional_not_required_for_core"


def test_services_control_start_stop(state_dir):
    started = services.control("start", "atlas", state_dir=state_dir)
    assert started["services"]["atlas"] == "running"
    stopped = services.control("stop", "atlas", state_dir=state_dir)
    assert stopped["services"]["atlas"] == "stopped"


def test_services_unknown_service(state_dir):
    result = services.control("start", "made_up", state_dir=state_dir)
    assert result["ok"] is False
    assert result["error"]["code"] == "unknown_service"


def test_status_reports_components_and_distribution(code_repo, state_dir):
    investigate.investigate(code_repo, state_dir=state_dir)
    result = coordinator.status(code_repo, state_dir=state_dir)
    comp = result["components"]
    for key in ("primitive_substrate", "pro_state", "atlas_map", "cortex", "distribution"):
        assert key in comp
    assert comp["distribution"] == "source-available"
    assert result["continuity"]["freshness"] == "fresh"


def test_support_bundle_redacts_and_excludes(code_repo, state_dir, tmp_path):
    investigate.investigate(code_repo, state_dir=state_dir)
    out = tmp_path / "support.json"
    result = support.support_bundle(str(out), state_dir=state_dir)
    assert result["ok"] is True
    for excluded in ("raw_project_content", "secrets", "private_operator_paths"):
        assert excluded in result["excluded"]
    bundle = json.loads(out.read_text())
    # Only hashed root ids appear, never raw paths.
    for root_hash in bundle["root_hashes"]:
        assert root_hash is None or root_hash.startswith("root-")


def test_doctor_human_has_no_raw_content(code_repo, state_dir):
    result = support.doctor(project_root=code_repo, state_dir=state_dir, human=True)
    assert result["ok"] is True
    assert "AetherMind Pro doctor" in result["human"]
    assert code_repo not in result["human"]
