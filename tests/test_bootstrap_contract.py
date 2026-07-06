"""Install-from-any-state bootstrap source contract.

Controlling docs: docs/plans/install-from-any-state-bootstrap-source-contract-spec.md.
These tests support only Tier 1 source-contract health.
"""

import json
from pathlib import Path

from aethermind_pro import cli


def run_cli(args, capsys):
    code = cli.main(args)
    out = capsys.readouterr().out
    return code, json.loads(out)


def test_bootstrap_status_reports_first_value_independent_of_harness(capsys, state_dir):
    code, payload = run_cli(["bootstrap", "status", "--state-dir", state_dir, "--json"], capsys)

    assert code == 0
    assert payload["ok"] is True
    assert payload["command"] == "bootstrap status"
    assert payload["first_value"]["possible_now"] is True
    assert payload["first_value"]["requires_harness"] is False
    assert payload["first_value"]["requires_network"] is False
    assert payload["first_value"]["requires_prior_aethermind_state"] is False
    assert payload["first_value"]["next_command"] == "aethermind-pro investigate --project-root . --json"
    assert payload["evidence"]["tier_eligible"] == ["tier_1_source_contract"]
    assert "not_shippable" in payload["evidence"]["blockers"]


def test_bootstrap_plan_is_consent_oriented_and_defers_harness_writes(capsys, code_repo, state_dir):
    code, payload = run_cli([
        "bootstrap", "plan", "--project-root", code_repo, "--state-dir", state_dir, "--json"
    ], capsys)

    assert code == 0
    assert payload["ok"] is True
    assert payload["command"] == "bootstrap plan"
    assert payload["actions"]
    kinds = {action["kind"] for action in payload["actions"]}
    assert "run_harness_discovery" in kinds
    assert "defer_harness_bootstrap" in kinds
    assert all("owner" in action for action in payload["actions"])
    assert "write_harness_hooks_without_approval" in payload["forbidden_actions"]
    assert "claim_install_ready_from_source_tree" in payload["forbidden_actions"]
    assert payload["evidence"]["tier_eligible"] == ["tier_1_source_contract"]


def test_bootstrap_preserves_compatible_user_managed_primitive(capsys, code_repo, state_dir):
    write_state(state_dir, {"primitive": {"external": {
        "version": "0.1.5", "compatible": True, "source_ref": "user_managed"
    }}})

    code, payload = run_cli([
        "bootstrap", "plan", "--project-root", code_repo, "--state-dir", state_dir, "--json"
    ], capsys)

    assert code == 0
    assert payload["components"]["primitive"] == "user_managed_compatible"
    assert payload["bootstrap_state"] == "previous_pro_install"
    kinds = {action["kind"] for action in payload["actions"]}
    assert "preserve_user_primitive" in kinds
    assert "select_bundled_primitive" not in kinds


def test_bootstrap_blocks_incompatible_user_primitive_without_silent_bundled_selection(
    capsys, code_repo, state_dir
):
    write_state(state_dir, {"primitive": {"external": {
        "version": "0.0.1", "compatible": False, "source_ref": "user_managed"
    }}})

    code, payload = run_cli(["bootstrap", "status", "--state-dir", state_dir, "--json"], capsys)

    assert code == 0
    assert payload["components"]["primitive"] == "user_managed_incompatible"
    assert payload["bootstrap_state"] == "pro_absent_primitive_incompatible"
    assert payload["first_value"]["possible_now"] is False
    assert any(d["code"] == "incompatible_user_primitive" for d in payload["degradation"])

    code, plan = run_cli([
        "bootstrap", "plan", "--project-root", code_repo, "--state-dir", state_dir, "--json"
    ], capsys)
    assert code == 0
    kinds = {action["kind"] for action in plan["actions"]}
    assert "report_incompatible_primitive" in kinds
    assert "select_bundled_primitive" not in kinds


def test_bootstrap_does_not_treat_string_false_compatibility_as_compatible(capsys, state_dir):
    write_state(state_dir, {"primitive": {"external": {
        "version": "0.0.1", "compatible": "false", "source_ref": "user_managed"
    }}})

    code, payload = run_cli(["bootstrap", "status", "--state-dir", state_dir, "--json"], capsys)

    assert code == 0
    assert payload["components"]["primitive"] == "user_managed_incompatible"
    assert payload["first_value"]["possible_now"] is False


def test_bootstrap_reports_malformed_pro_state_as_partial_broken(capsys, state_dir):
    path = Path(state_dir)
    path.mkdir(parents=True, exist_ok=True)
    (path / "pro_state.json").write_text("{not json", encoding="utf-8")

    code, payload = run_cli(["bootstrap", "status", "--state-dir", state_dir, "--json"], capsys)

    assert code == 0
    assert payload["components"]["pro_state"] == "corrupt"
    assert payload["bootstrap_state"] == "partial_broken_pro_install"
    assert payload["first_value"]["possible_now"] is False
    assert any(d["code"] == "corrupt_pro_state" for d in payload["degradation"])


def write_state(state_dir, updates):
    path = Path(state_dir)
    path.mkdir(parents=True, exist_ok=True)
    data = {
        "state_version": "aethermind-pro-state-v1",
        "settings": {},
        "roots": [],
        "harnesses": {},
        "trusted_registry": [],
        "services": {},
    }
    data.update(updates)
    (path / "pro_state.json").write_text(json.dumps(data), encoding="utf-8")
