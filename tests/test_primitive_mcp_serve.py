"""Primitive MCP stdio serve contract.

`aethermind-pro primitive-mcp serve` must speak MCP over stdio (newline-delimited
JSON-RPC 2.0): initialize, tools/list, tools/call. This is the universal native
tool surface for every MCP-capable harness (Grok Build, Codex, Claude Code,
Hermes, future) from one implementation.
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def rpc(id_, method, params=None):
    msg = {"jsonrpc": "2.0", "id": id_, "method": method}
    if params is not None:
        msg["params"] = params
    return json.dumps(msg)


def run_serve(lines):
    proc = subprocess.run(
        [sys.executable, "-m", "aethermind_pro.cli", "primitive-mcp", "serve"],
        input="\n".join(lines) + "\n",
        text=True,
        capture_output=True,
        cwd=ROOT,
        env={"PYTHONPATH": str(ROOT / "src"), "PATH": "/usr/bin:/bin", "HOME": "/tmp"},
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    return [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]


def test_serve_initialize_list_and_call(tmp_path):
    data_root = tmp_path / "proj"
    data_root.mkdir()
    responses = run_serve([
        rpc(1, "initialize", {"protocolVersion": "2025-06-18",
                              "capabilities": {}, "clientInfo": {"name": "test", "version": "0"}}),
        json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}),
        rpc(2, "tools/list"),
        rpc(3, "tools/call", {"name": "init_store", "arguments": {"data_root": str(data_root)}}),
        rpc(4, "tools/call", {"name": "status", "arguments": {"data_root": str(data_root)}}),
    ])

    by_id = {r["id"]: r for r in responses}
    init = by_id[1]["result"]
    assert init["serverInfo"]["name"] == "aethermind-pro-primitive"
    assert "tools" in init["capabilities"]

    tools = {t["name"] for t in by_id[2]["result"]["tools"]}
    assert {"status", "read_layers", "init_store", "write_layer"} <= tools
    for tool in by_id[2]["result"]["tools"]:
        assert tool["inputSchema"]["type"] == "object"

    call_result = by_id[3]["result"]
    assert call_result["isError"] is False
    payload = json.loads(call_result["content"][0]["text"])
    assert payload["ok"] is True

    status_payload = json.loads(by_id[4]["result"]["content"][0]["text"])
    assert status_payload["initialized"] is True


def test_serve_reports_tool_errors_without_crashing(tmp_path):
    responses = run_serve([
        rpc(1, "initialize", {"protocolVersion": "2025-06-18"}),
        rpc(2, "tools/call", {"name": "status", "arguments": {}}),
        rpc(3, "nonexistent/method"),
    ])
    by_id = {r["id"]: r for r in responses}
    # Missing data_root is a tool-level error, not a protocol crash.
    assert by_id[2]["result"]["isError"] is True
    assert by_id[3]["error"]["code"] == -32601
