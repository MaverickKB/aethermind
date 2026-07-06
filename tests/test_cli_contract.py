"""CLI package contract.

Controlling docs: docs/PRO_SYSTEM_CONTRACT.md lines 21-43, design choice 2 (JSON
default, --human opt-in), build plan Task 3 (unknown commands return structured JSON).
"""

import json

import pytest

from aethermind_pro import cli


def run(args, capsys):
    code = cli.main(args)
    out = capsys.readouterr().out
    return code, out


def test_no_command_is_structured_error(capsys):
    code, out = run([], capsys)
    payload = json.loads(out)
    assert code == 1
    assert payload["ok"] is False
    assert "error" in payload


def test_unknown_command_structured_json_error(capsys):
    code, out = run(["frobnicate"], capsys)
    payload = json.loads(out)
    assert code == 1
    assert payload["ok"] is False
    assert payload["error"]["code"] == "unknown_command"
    assert "next_action" in payload["error"]


def test_json_is_default_output(code_repo, state_dir, capsys):
    code, out = run(["investigate", "--project-root", code_repo, "--state-dir", state_dir], capsys)
    payload = json.loads(out)  # must be valid JSON by default
    assert code == 0
    assert payload["command"] == "investigate"
    assert payload["ok"] is True


def test_human_flag_is_opt_in(code_repo, state_dir, capsys):
    code, out = run(["doctor", "--project-root", code_repo, "--state-dir", state_dir, "--human"], capsys)
    assert code == 0
    # Human output is not raw JSON; it is a readable summary.
    with pytest.raises(json.JSONDecodeError):
        json.loads(out)
    assert "AetherMind Pro doctor" in out


def test_help_lists_commands(capsys):
    code, out = run(["help"], capsys)
    payload = json.loads(out)
    assert code == 0
    for command in ("status", "investigate", "coordinate", "trust", "export", "smoke"):
        assert command in payload["commands"]


def test_status_command_runs(code_repo, state_dir, capsys):
    run(["investigate", "--project-root", code_repo, "--state-dir", state_dir], capsys)
    code, out = run(["status", "--project-root", code_repo, "--state-dir", state_dir], capsys)
    payload = json.loads(out)
    assert code == 0
    assert payload["command"] == "status"
    assert payload["continuity"]["visible_layers"] >= 1


def test_unknown_subcommand_structured_error(capsys):
    code, out = run(["comms", "frobnicate"], capsys)
    payload = json.loads(out)
    assert code == 1
    assert payload["error"]["code"] == "unknown_subcommand"
