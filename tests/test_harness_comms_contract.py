"""Harness-neutral comms and harness config contract.

Controlling docs: docs/HARNESS_CONFORMANCE_CONTRACT.md,
docs/plans/harness-neutral-source-contract-spec.md,
docs/plans/harness-discovery-bootstrap-source-contract-spec.md,
docs/plans/source-contract-test-spec.md required test group 7.
"""

import json
import os
from pathlib import Path

from aethermind_pro import cli, comms, harnesses, investigate


SCHEMA_DIR = Path(__file__).resolve().parents[1] / "schemas"


def test_capsule_has_required_neutral_fields(code_repo, state_dir):
    investigate.investigate(code_repo, state_dir=state_dir)
    capsule = comms.build_capsule(code_repo, state_dir=state_dir, harness_target="codex")
    for key in ("schema_version", "capsule_id", "project", "continuity", "cortex",
                "trust", "harness", "evidence", "redaction"):
        assert key in capsule
    assert capsule["schema_version"] == "aethermind-pro-handoff-v1"
    assert capsule["harness"]["target"] == "codex"


def test_plaintext_carries_equivalent_orientation(code_repo, state_dir):
    investigate.investigate(code_repo, state_dir=state_dir)
    result = comms.brief(code_repo, state_dir=state_dir)
    text = result["plaintext"]
    assert "AetherMind Pro handoff" in text
    assert "CORTEX verdict" in text
    assert "source-contract proof only" in text


def test_capsule_matches_schema_required_keys(code_repo, state_dir):
    investigate.investigate(code_repo, state_dir=state_dir)
    capsule = comms.build_capsule(code_repo, state_dir=state_dir)
    schema = json.loads((SCHEMA_DIR / "agent_comms_capsule.schema.json").read_text())
    for required in schema["required"]:
        assert required in capsule


def test_all_first_class_harnesses_listed(state_dir):
    result = harnesses.list_harnesses(state_dir=state_dir)
    names = {h["name"] for h in result["harnesses"]}
    for harness in ("hermes", "grok_build", "codex", "claude_code"):
        assert harness in names


def test_byo_custom_harness_is_data_driven(state_dir):
    cfg = {"kind": "custom", "enabled": True, "command": ["my-agent", "run"],
           "handoff_input": "stdin", "handoff_output": "stdout"}
    result = harnesses.configure("my-agent", cfg, state_dir=state_dir)
    assert result["ok"] is True
    assert result["config"]["command"] == ["my-agent", "run"]
    listed = harnesses.list_harnesses(state_dir=state_dir)
    assert any(h["name"] == "my-agent" for h in listed["harnesses"])


def test_harness_check_degrades_honestly(state_dir):
    result = harnesses.check("grok_build", state_dir=state_dir)
    assert result["ok"] is True
    # Not configured: must report degradation honestly, not pretend success.
    codes = {d["code"] for d in result["degradation"]}
    assert codes  # at least one honest degradation
    assert result["depth_tier_proven"] <= 2


def test_discover_carries_all_harnesses_blocker(state_dir):
    result = harnesses.discover(state_dir=state_dir)
    assert "not_all_harnesses_proven" in result["evidence"]["blockers"]
    names = {h["name"] for h in result["harnesses"]}
    assert {"hermes", "grok_build", "codex", "claude_code"}.issubset(names)


def test_unknown_openclaw_like_harness_discovered_as_future_candidate(tmp_path, monkeypatch, state_dir):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    candidate = bin_dir / "openclaw"
    candidate.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    candidate.chmod(0o755)
    monkeypatch.setenv("PATH", str(bin_dir) + os.pathsep + os.environ.get("PATH", ""))

    result = harnesses.discover(state_dir=state_dir)

    found = next(h for h in result["harnesses"] if h["name"] == "openclaw")
    assert found["classification"] == "future_unknown"
    assert found["detected"] is True
    assert found["trusted"] is False
    assert found["trust_review"] == "required"
    assert found["depth"]["current_tier"] == 1
    assert found["next_action"] == "aethermind-pro harnesses bootstrap plan --name openclaw --json"


def test_harness_bootstrap_plan_generates_default_deny_prompts_without_writes(state_dir):
    result = harnesses.bootstrap_plan("codex", state_dir=state_dir)

    assert result["ok"] is True
    assert result["command"] == "harnesses bootstrap plan"
    assert result["harness"]["name"] == "codex"
    assert result["created_surfaces"] == []
    assert result["prompts"]
    for prompt in result["prompts"]:
        assert prompt["approval"]["default"] == "deny"
        assert "approve_once" in prompt["approval"]["accepted_values"]
        assert prompt["proposed_change"]["required_for_first_value"] is False
        assert prompt["proposed_change"]["required_for_harness_depth"] is True
        assert prompt["proposed_change"]["trust_review"] in {"not_required", "required"}
        assert prompt["explanation"]["rollback"]
        assert prompt["explanation"]["uninstall_behavior"] in {"removed_by_default", "offer_removal"}
    assert "not_all_harnesses_proven" in result["evidence"]["blockers"]


def test_cli_routes_harnesses_bootstrap_plan(capsys, state_dir):
    code = cli.main(["harnesses", "bootstrap", "plan", "--name", "codex", "--state-dir", state_dir, "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert payload["ok"] is True
    assert payload["command"] == "harnesses bootstrap plan"
    assert payload["harness"]["name"] == "codex"
    assert payload["prompts"]


def test_harness_bootstrap_plan_does_not_overclaim_detection_for_arbitrary_custom(state_dir):
    result = harnesses.bootstrap_plan("definitely-not-installed-pass7", state_dir=state_dir)

    assert result["ok"] is True
    assert result["harness"]["classification"] == "custom"
    assert result["harness"]["detected"] is False
    assert {p["harness"]["detected"] for p in result["prompts"]} == {False}
    assert {p["proposed_change"]["trust_review"] for p in result["prompts"]} == {"required"}


def test_harness_bootstrap_prompts_include_external_surface_ownership_preview(state_dir):
    result = harnesses.bootstrap_plan("codex", state_dir=state_dir)

    surface_prompts = [p for p in result["prompts"] if p["proposed_change"]["kind"] != "manual_instruction_only"]
    assert surface_prompts
    for prompt in surface_prompts:
        record = prompt["ownership_preview"]
        assert record["surface_id"].startswith("preview-codex-")
        assert record["harness"] == "codex"
        assert record["surface_kind"] in {"handoff_file", "custom_config"}
        assert record["target"] == prompt["proposed_change"]["target"]
        assert record["created_by"] == "aethermind_pro"
        assert record["created_at"] is None
        assert record["approval_id"] == prompt["prompt_id"]
        assert record["trust_event_id"] is None
        assert record["rollback"] in {"remove", "restore_previous"}
        assert record["default_uninstall"] in {"remove", "offer_removal"}

    manual_prompt = next(p for p in result["prompts"] if p["proposed_change"]["kind"] == "manual_instruction_only")
    assert "ownership_preview" not in manual_prompt
    assert manual_prompt["explanation"]["rollback"] == "not_applicable"
