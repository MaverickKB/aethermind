"""Substrate ownership and primitive MCP contract.

Controlling docs: docs/SUBSTRATE_OWNERSHIP.md lines 9-37,
docs/AETHERMIND_PRIMITIVE_MCP.md lines 5-33.
"""

from aethermind_pro import primitive_mcp, substrate


def test_no_external_uses_bundled():
    active = substrate.select_active(None)
    assert active["active_source"] == "bundled"
    assert active["mutates_user_install"] is False


def test_compatible_external_wins():
    active = substrate.select_active({"version": "0.1.5", "compatible": True, "source_ref": "user"})
    assert active["active_source"] == "external"
    assert active["mutates_user_install"] is False


def test_incompatible_external_blocks_unless_user_selects_bundled():
    incompatible = {"version": "0.9.0", "compatible": False, "source_ref": "user"}
    blocked = substrate.select_active(incompatible)
    assert blocked["active_source"] == "external_incompatible"
    chosen = substrate.select_active(incompatible, user_selected_bundled=True)
    assert chosen["active_source"] == "bundled"


def test_status_contract_fields(tmp_path):
    status = substrate.status(str(tmp_path))
    for key in ("active_source", "version", "compatibility_range", "source_ref",
                "provenance", "network_required", "mutates_store", "has_visible_layers"):
        assert key in status
    assert status["network_required"] is False


def test_primitive_requires_explicit_root():
    result = primitive_mcp.call("status", {})
    assert result["ok"] is False
    assert result["error"]["code"] == "data_root_required"


def test_primitive_write_requires_init(tmp_path):
    result = primitive_mcp.call("write_layer", {"data_root": str(tmp_path), "layer": {}})
    assert result["ok"] is False
    assert result["error"]["code"] == "uninitialized_data_root"


def test_primitive_write_disabled_by_policy(tmp_path):
    primitive_mcp.call("init_store", {"data_root": str(tmp_path)})
    policy = primitive_mcp.PrimitivePolicy(write_enabled=False)
    result = primitive_mcp.call("write_layer", {"data_root": str(tmp_path), "layer": {}}, policy)
    assert result["ok"] is False
    assert result["error"]["code"] == "mcp_write_tools_disabled"


def test_primitive_root_denied_by_policy(tmp_path):
    policy = primitive_mcp.PrimitivePolicy(denied_roots=[str(tmp_path)])
    result = primitive_mcp.call("status", {"data_root": str(tmp_path)}, policy)
    assert result["ok"] is False
    assert result["error"]["code"] == "root_denied_by_policy"


def test_primitive_roundtrip(tmp_path):
    primitive_mcp.call("init_store", {"data_root": str(tmp_path)})
    write = primitive_mcp.call("write_layer", {"data_root": str(tmp_path), "layer": {"kind": "t"}})
    assert write["ok"] is True
    read = primitive_mcp.call("read_layers", {"data_root": str(tmp_path)})
    assert read["ok"] is True
    assert read["count"] == 1
    assert read["layers"][0]["layer_id"] == write["layer_id"]
