"""Explicit-root primitive MCP / substrate adapter.

Derived from docs/AETHERMIND_PRIMITIVE_MCP.md lines 5-33.

Every tool takes an explicit ``data_root``; there is no hidden cwd assumption.
Write tools are policy controlled. Policy violations map to the bounded error
vocabulary that Pro maps into CORTEX pressure codes.

This module ships a bundled, data-local primitive store (``.aethermind/`` beside the
selected root) so first standalone value works without an external install. It must
not create a hidden parallel AetherMind: the store stays at the data-local location
defined by the OSS primitive contract.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import aem_codec

STORE_DIRNAME = ".aethermind"
LAYERS_FILE = "layers.aem"
LEGACY_LAYERS_FILE = "layers.jsonl"

BUNDLED_VERSION = "aethermind-bundled-0.2.0"
COMPATIBILITY_RANGE = ">=0.1.0,<0.3.0"

POLICY_ERRORS = (
    "data_root_required",
    "root_denied_by_policy",
    "root_not_allowed_by_policy",
    "mcp_write_tools_disabled",
    "mcp_init_disabled",
    "uninitialized_data_root",
)

READ_SAFE_TOOLS = ("status", "read_layers")
WRITE_TOOLS = ("init_store", "write_layer")


class PrimitivePolicy:
    """Bounded write/init policy by allowed/denied roots."""

    def __init__(
        self,
        allowed_roots: Optional[List[str]] = None,
        denied_roots: Optional[List[str]] = None,
        write_enabled: bool = True,
        init_enabled: bool = True,
    ):
        self.allowed_roots = [str(Path(r).expanduser().resolve()) for r in allowed_roots] if allowed_roots else None
        self.denied_roots = [str(Path(r).expanduser().resolve()) for r in (denied_roots or [])]
        self.write_enabled = write_enabled
        self.init_enabled = init_enabled

    def check_root(self, data_root: Path) -> Optional[str]:
        resolved = str(data_root)
        if resolved in self.denied_roots:
            return "root_denied_by_policy"
        if self.allowed_roots is not None and resolved not in self.allowed_roots:
            return "root_not_allowed_by_policy"
        return None


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ok(**fields: Any) -> Dict[str, Any]:
    result = {"ok": True}
    result.update(fields)
    return result


def _error(code: str, message: str) -> Dict[str, Any]:
    return {"ok": False, "error": {"code": code, "message": message}}


def _store_dir(data_root: Path) -> Path:
    return data_root / STORE_DIRNAME


def _is_initialized(data_root: Path) -> bool:
    return _store_dir(data_root).is_dir()


def call(tool: str, params: Dict[str, Any], policy: Optional[PrimitivePolicy] = None) -> Dict[str, Any]:
    """Dispatch a primitive MCP tool call with explicit-root policy enforcement."""
    policy = policy or PrimitivePolicy()
    data_root_raw = params.get("data_root") or params.get("root")
    if not data_root_raw:
        return _error("data_root_required", "data_root is required; no cwd assumption is made")
    data_root = Path(data_root_raw).expanduser().resolve()

    policy_error = policy.check_root(data_root)
    if policy_error:
        return _error(policy_error, f"root rejected by policy: {policy_error}")

    if tool == "status":
        return _status(data_root)
    if tool == "read_layers":
        return _read_layers(data_root)
    if tool == "init_store":
        if not policy.init_enabled:
            return _error("mcp_init_disabled", "init tools are disabled by policy")
        return _init_store(data_root)
    if tool == "write_layer":
        if not policy.write_enabled:
            return _error("mcp_write_tools_disabled", "write tools are disabled by policy")
        return _write_layer(data_root, params.get("layer") or {})
    return _error("unknown_tool", f"unknown primitive tool: {tool}")


def _status(data_root: Path) -> Dict[str, Any]:
    initialized = _is_initialized(data_root)
    read = _read_layers(data_root) if initialized else {"layers": [], "corrupt": False}
    legacy_count = sum(1 for item in read.get("layers", []) if item.get("store_format") == "legacy-jsonl")
    aem_count = len(read.get("layers", [])) - legacy_count
    return _ok(
        initialized=initialized,
        store="project_local",
        provenance="bundled",
        version=BUNDLED_VERSION,
        compatibility_range=COMPATIBILITY_RANGE,
        format="aem-light-v1",
        visible_layers=len(read.get("layers", [])),
        aem_layers=aem_count,
        legacy_jsonl_layers=legacy_count,
        legacy_jsonl_preserved=(_store_dir(data_root) / LEGACY_LAYERS_FILE).exists(),
        corrupt=bool(read.get("corrupt")),
    )


def _init_store(data_root: Path) -> Dict[str, Any]:
    store = _store_dir(data_root)
    created = not store.exists()
    store.mkdir(parents=True, exist_ok=True)
    return _ok(
        store="project_local",
        format="aem-light-v1",
        created=created,
        already_present=not created,
        legacy_jsonl_preserved=(store / LEGACY_LAYERS_FILE).exists(),
    )


_SEMANTIC_TYPE = re.compile(r"^[a-z][a-z0-9-]{0,63}$")
_RFC3339 = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d{1,9})?)?(?:Z|[+-]\d{2}:\d{2})$"
)


def _semantic_type(layer: Dict[str, Any]) -> str:
    value = str(layer.get("type") or layer.get("kind") or "discovery").lower()
    value = re.sub(r"[^a-z0-9-]+", "-", value).strip("-")
    return value if _SEMANTIC_TYPE.fullmatch(value) else "discovery"


def _layer_body(layer: Dict[str, Any]) -> str:
    body = layer.get("body")
    if isinstance(body, str) and body.strip():
        return body
    facts = layer.get("observed_facts")
    if facts:
        return "Workspace observation: " + json.dumps(
            facts, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
    kind = str(layer.get("kind") or "continuity")
    source = str(layer.get("source") or "aethermind-pro")
    return "%s recorded by %s" % (kind.replace("_", " "), source)


def canonicalize_layer(layer: Dict[str, Any]) -> Dict[str, Any]:
    timestamp = layer.get("created_at") or layer.get("ts") or _now()
    if not isinstance(timestamp, str) or not _RFC3339.fullmatch(timestamp):
        timestamp = _now()
    layer_id = layer.get("layer_id") or layer.get("id") or ("aem-pro-" + uuid.uuid4().hex[:16])
    markers = layer.get("markers")
    if not isinstance(markers, list) or not all(isinstance(item, str) for item in markers):
        markers = []
    confidence = layer.get("conf", 1.0)
    if isinstance(confidence, bool):
        raise ValueError("conf must be numeric, not boolean")
    record: Dict[str, Any] = {
        "id": str(layer_id),
        "ts": timestamp,
        "author": str(layer.get("author") or "aethermind-pro"),
        "type": _semantic_type(layer),
        "body": _layer_body(layer),
        "ctx": str(layer.get("ctx") or "aethermind-pro/%s" % _semantic_type(layer)),
        "conf": float(confidence),
        "markers": markers,
        "primitive": str(layer.get("primitive") or "layer"),
        "x_pro_payload": json.dumps(layer, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
    }
    aliases = {
        "kind": layer.get("kind"),
        "label": layer.get("workspace_kind"),
        "content_id": layer.get("root_id"),
        "source_tool": layer.get("source"),
        "sig": layer.get("sig"),
        "sig_key_id": layer.get("sig_key_id"),
    }
    for key, value in aliases.items():
        if isinstance(value, str) and value:
            record[key] = value
    return record


def _write_layer(data_root: Path, layer: Dict[str, Any]) -> Dict[str, Any]:
    if not _is_initialized(data_root):
        return _error("uninitialized_data_root", "store is not initialized; call init_store first")
    try:
        record = canonicalize_layer(layer)
        receipt = aem_codec.append_layer(_store_dir(data_root) / LAYERS_FILE, record)
    except (OSError, TypeError, ValueError, aem_codec.AEMError) as exc:
        return _error("aem_write_failed", str(exc))
    return _ok(
        layer_id=receipt["layer_id"],
        id=receipt["layer_id"],
        store="project_local",
        format="aem-light-v1",
        record_hash=receipt["record_hash"],
        legacy_jsonl_preserved=(_store_dir(data_root) / LEGACY_LAYERS_FILE).exists(),
    )


PROTOCOL_VERSION = "2025-06-18"

_ROOT_SCHEMA = {
    "type": "object",
    "properties": {"data_root": {"type": "string", "description": "explicit project/data root; no cwd assumption"}},
    "required": ["data_root"],
}

TOOL_DEFS = [
    {"name": "status", "description": "Report primitive store state for an explicit data_root.",
     "inputSchema": _ROOT_SCHEMA},
    {"name": "read_layers", "description": "Read continuity layers from the data_root store.",
     "inputSchema": _ROOT_SCHEMA},
    {"name": "init_store", "description": "Initialize the project-local .aethermind store at data_root.",
     "inputSchema": _ROOT_SCHEMA},
    {"name": "write_layer", "description": "Append one continuity layer (durable decision/correction/friction) to the data_root store.",
     "inputSchema": {
         "type": "object",
         "properties": {
             "data_root": {"type": "string"},
             "layer": {"type": "object", "description": "layer record fields (type, body, ctx, ...)"},
         },
         "required": ["data_root", "layer"],
     }},
]


def serve(stdin=None, stdout=None) -> int:
    """Serve the primitive tools over MCP stdio (newline-delimited JSON-RPC 2.0).

    One implementation covers every MCP-capable harness; policy enforcement and
    the explicit-root rule are identical to direct CLI calls.
    """
    import sys

    stdin = stdin if stdin is not None else sys.stdin
    stdout = stdout if stdout is not None else sys.stdout

    def respond(payload: Dict[str, Any]) -> None:
        stdout.write(json.dumps(payload, sort_keys=True) + "\n")
        stdout.flush()

    for raw in stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            message = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(message, dict) or "id" not in message:
            continue  # notifications need no response
        msg_id = message["id"]
        method = message.get("method")
        params = message.get("params") or {}
        if method == "initialize":
            result: Dict[str, Any] = {
                "protocolVersion": params.get("protocolVersion", PROTOCOL_VERSION),
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "aethermind-pro-primitive", "version": BUNDLED_VERSION},
            }
        elif method == "tools/list":
            result = {"tools": TOOL_DEFS}
        elif method == "tools/call":
            outcome = call(params.get("name", ""), params.get("arguments") or {})
            result = {
                "content": [{"type": "text", "text": json.dumps(outcome, sort_keys=True)}],
                "isError": outcome.get("ok") is not True,
            }
        elif method == "ping":
            result = {}
        else:
            respond({"jsonrpc": "2.0", "id": msg_id,
                     "error": {"code": -32601, "message": f"method not found: {method}"}})
            continue
        respond({"jsonrpc": "2.0", "id": msg_id, "result": result})
    return 0


def _read_layers(data_root: Path) -> Dict[str, Any]:
    if not _is_initialized(data_root):
        return _error("uninitialized_data_root", "store is not initialized")
    layers: List[Dict[str, Any]] = []
    corrupt = False
    legacy_path = _store_dir(data_root) / LEGACY_LAYERS_FILE
    if legacy_path.exists():
        try:
            legacy_lines = legacy_path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError):
            legacy_lines = []
            corrupt = True
        for line in legacy_lines:
            line = line.strip()
            if not line:
                continue
            try:
                legacy = json.loads(line)
                if not isinstance(legacy, dict):
                    raise ValueError("legacy layer must be an object")
                legacy["store_format"] = "legacy-jsonl"
                layers.append(legacy)
            except (json.JSONDecodeError, ValueError):
                corrupt = True
    report = aem_codec.read_report(_store_dir(data_root) / LAYERS_FILE)
    corrupt = corrupt or bool(report["issues"])
    for record in report["layers"]:
        restored: Dict[str, Any] = {}
        payload = record.get("x_pro_payload")
        if isinstance(payload, str):
            try:
                decoded = json.loads(payload)
                if isinstance(decoded, dict):
                    restored.update(decoded)
            except json.JSONDecodeError:
                corrupt = True
        restored.update({
            "layer_id": record["id"],
            "id": record["id"],
            "created_at": record["ts"],
            "ts": record["ts"],
            "author": record["author"],
            "type": record["type"],
            "body": record["body"],
            "ctx": record["ctx"],
            "conf": record["conf"],
            "markers": record["markers"],
            "primitive": record.get("primitive", "layer"),
            "kind": record.get("kind", restored.get("kind", record["type"])),
            "store_format": "aem-light-v1",
        })
        for field in ("sig", "sig_key_id", "label", "content_id", "source_tool"):
            if field in record:
                restored[field] = record[field]
        if record.get("label") and "workspace_kind" not in restored:
            restored["workspace_kind"] = record["label"]
        layers.append(restored)
    return _ok(
        layers=layers,
        count=len(layers),
        corrupt=corrupt,
        issues=report["issues"],
        legacy_jsonl_preserved=legacy_path.exists(),
    )
