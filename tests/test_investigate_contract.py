"""First-value `investigate` contract.

Controlling docs: docs/FIRST_TEN_MINUTES_CONTRACT.md lines 5-14,
docs/plans/source-contract-first-slice-spec.md lines 65-173,
docs/plans/source-contract-test-spec.md required test group 1 and group 3.

These tests support only Tier 1 source-contract health.
"""

from aethermind_pro import investigate


def test_code_repo_first_value(code_repo, state_dir):
    result = investigate.investigate(code_repo, state_dir=state_dir)
    assert result["ok"] is True
    assert result["command"] == "investigate"
    assert result["layer"]["created"] is True
    assert result["layer"]["layer_id"]
    assert result["workspace_summary"]["kind"] == "code_repo"
    assert result["workspace_summary"]["aethermind_store"] == "created"
    assert result["next_command"] == "aethermind-pro status --project-root . --json"
    assert result["evidence"]["tier_eligible"] == ["tier_1_source_contract"]


def test_creative_writing_needs_no_vcs(writing_dir, state_dir):
    result = investigate.investigate(writing_dir, state_dir=state_dir)
    assert result["ok"] is True
    assert result["workspace_summary"]["kind"] in ("creative_writing", "mixed")
    assert result["layer"]["created"] is True


def test_notes_directory(notes_dir, state_dir):
    result = investigate.investigate(notes_dir, state_dir=state_dir)
    assert result["ok"] is True
    assert result["workspace_summary"]["kind"] in ("notes", "mixed")


def test_no_write_does_not_claim_layer(code_repo, state_dir):
    result = investigate.investigate(code_repo, no_write=True, state_dir=state_dir)
    assert result["ok"] is True
    assert result["layer"]["created"] is False
    assert result["layer"]["layer_id"] is None
    assert any(d["code"] == "no_write" for d in result["degradation"])


def test_missing_project_root_errors():
    result = investigate.investigate(None)
    assert result["ok"] is False
    assert result["error"]["code"] == "project_root_required"
    assert result["evidence"]["tier_eligible"] == []


def test_nonexistent_root_errors(tmp_path, state_dir):
    missing = str(tmp_path / "does-not-exist")
    result = investigate.investigate(missing, state_dir=state_dir)
    assert result["ok"] is False
    assert result["error"]["code"] == "root_not_found"


def test_works_without_optional_integrations(code_repo, state_dir):
    # No Hermes/Codex/MCP/plugin/prior state configured; first value must still work.
    result = investigate.investigate(code_repo, state_dir=state_dir)
    assert result["ok"] is True
    assert result["layer"]["created"] is True


def test_resolved_root_and_root_id_present(code_repo, state_dir):
    result = investigate.investigate(code_repo, state_dir=state_dir)
    assert result["project_root"]["root_id"].startswith("root-")
    assert result["project_root"]["resolved"]
