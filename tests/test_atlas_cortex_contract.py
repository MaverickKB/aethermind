"""Atlas map and host-local CORTEX contract.

Controlling docs: docs/PRO_SYSTEM_CONTRACT.md lines 11-12,
docs/plans/local-coordinator-source-contract-spec.md lines 81-211.
"""

from pathlib import Path

from aethermind_pro import atlas, coordinator, cortex, investigate, primitive_mcp


def test_continuity_missing_then_fresh(code_repo, state_dir):
    missing = atlas.assess_continuity(Path(code_repo))
    assert missing["state"] == "missing"
    investigate.investigate(code_repo, state_dir=state_dir)
    fresh = atlas.assess_continuity(Path(code_repo))
    assert fresh["state"] == "fresh"
    assert fresh["visible_layers"] >= 1


def test_continuity_corrupt_reported(tmp_path):
    primitive_mcp.call("init_store", {"data_root": str(tmp_path)})
    (tmp_path / ".aethermind" / "layers.jsonl").write_text("{not valid json\n", encoding="utf-8")
    assessed = atlas.assess_continuity(tmp_path)
    assert assessed["state"] == "corrupt"


def test_cortex_missing_continuity_is_repair():
    verdict = cortex.coordinate("missing")
    assert verdict["verdict"] == "repair"
    assert "continuity_missing" in verdict["pressure_codes"]
    assert "refresh_continuity" in verdict["repair_lanes"]


def test_cortex_blocks_on_substrate_unavailable():
    verdict = cortex.coordinate("fresh", substrate_state="missing")
    assert verdict["verdict"] == "blocked"
    assert "substrate_unavailable" in verdict["pressure_codes"]


def test_cortex_dangerous_trust_blocks():
    verdict = cortex.coordinate("fresh", trust_state="dangerous")
    assert verdict["verdict"] == "blocked"


def test_map_excludes_private_topology(code_repo, state_dir):
    investigate.investigate(code_repo, state_dir=state_dir)
    result = coordinator.map_command(state_dir=state_dir)
    machine_map = result["map"]
    assert machine_map["host"]["network_context"] == "cairn_disabled"
    assert machine_map["host"]["host_id"].startswith("host-")
    # No raw path in host id.
    assert "/" not in machine_map["host"]["host_id"]


def test_coordinate_command_fresh_continuity_proceeds(code_repo, state_dir):
    investigate.investigate(code_repo, state_dir=state_dir)
    result = coordinator.coordinate(code_repo, state_dir=state_dir)
    assert result["ok"] is True
    # Coordination is unconditional in the source-available build: fresh continuity proceeds.
    assert result["cortex"]["verdict"] == "proceed"
