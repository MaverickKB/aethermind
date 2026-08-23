"""Dependency-free reader and append-only writer for the public AEM subset.

The bundled coordinator supports Python 3.9, so this module deliberately avoids
``tomllib`` while accepting the scalar and string-list syntax emitted by the
public AetherMind primitive. Records are parsed independently so one damaged
record is reported without hiding the healthy records around it.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import fcntl
except ImportError:  # pragma: no cover, Windows uses the guarded fallback
    fcntl = None


class AEMError(ValueError):
    """Raised when an AEM record cannot be parsed or validated."""


REQUIRED_FIELDS = ("id", "ts", "author", "type", "body", "ctx", "conf", "markers")
FIELD_ORDER = REQUIRED_FIELDS + (
    "primitive",
    "thread_key",
    "supersedes",
    "rollback_of",
    "corrects",
    "prev_hash",
    "archived_to",
    "evidence",
    "recurrence_of",
    "verification",
    "next",
    "artifact",
    "artifact_ref",
    "anchor",
    "ref",
    "kind",
    "label",
    "host",
    "repo_root",
    "content_id",
    "source_tool",
    "store_kind",
    "sig",
    "sig_key_id",
    "x_pro_payload",
)
STRING_LIST_FIELDS = {
    "markers", "supersedes", "rollback_of", "corrects", "evidence",
    "recurrence_of", "verification", "next",
}
_KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_TYPE = re.compile(r"^[a-z][a-z0-9-]{0,63}$")
_HEADER = re.compile(r"(?m)^\s*\[\[(?:layer|layers)\]\]\s*(?:#.*)?$")


def _strip_comment(value: str) -> str:
    quoted = False
    escaped = False
    depth = 0
    for index, char in enumerate(value):
        if escaped:
            escaped = False
            continue
        if char == "\\" and quoted:
            escaped = True
            continue
        if char == '"':
            quoted = not quoted
            continue
        if not quoted:
            if char == "[":
                depth += 1
            elif char == "]":
                depth -= 1
            elif char == "#" and depth == 0:
                return value[:index].rstrip()
    return value.strip()


def _parse_value(encoded: str) -> Any:
    encoded = _strip_comment(encoded)
    if not encoded:
        raise AEMError("empty value")
    try:
        value = json.loads(encoded)
    except json.JSONDecodeError as exc:
        raise AEMError("unsupported AEM value") from exc
    if isinstance(value, dict) or value is None:
        raise AEMError("AEM values must be scalar or string arrays")
    if isinstance(value, list) and not all(isinstance(item, str) for item in value):
        raise AEMError("AEM arrays must contain strings")
    if isinstance(value, float) and not math.isfinite(value):
        raise AEMError("AEM numbers must be finite")
    return value


def validate_layer(layer: Dict[str, Any], seen_ids: Optional[set] = None) -> None:
    for field in REQUIRED_FIELDS:
        if field not in layer:
            raise AEMError("missing required field: %s" % field)
    for field in ("id", "ts", "author", "type", "body", "ctx"):
        if not isinstance(layer[field], str) or not layer[field]:
            raise AEMError("%s must be a non-empty string" % field)
    if not _TYPE.fullmatch(layer["type"]):
        raise AEMError("type must be a lowercase semantic token")
    if isinstance(layer["conf"], bool) or not isinstance(layer["conf"], (int, float)):
        raise AEMError("conf must be numeric")
    if not 0.0 <= float(layer["conf"]) <= 1.0:
        raise AEMError("conf must be between 0.0 and 1.0")
    layer["conf"] = float(layer["conf"])
    for field in STRING_LIST_FIELDS:
        if field in layer and (
            not isinstance(layer[field], list)
            or not all(isinstance(item, str) for item in layer[field])
        ):
            raise AEMError("%s must be a string array" % field)
    primitive = layer.setdefault("primitive", "layer")
    if not isinstance(primitive, str) or not primitive:
        raise AEMError("primitive must be a non-empty string")
    for key, value in layer.items():
        if not _KEY.fullmatch(key):
            raise AEMError("invalid field name: %s" % key)
        if isinstance(value, (dict, tuple, set)) or value is None:
            raise AEMError("unsupported field value: %s" % key)
        if isinstance(value, list) and not all(isinstance(item, str) for item in value):
            raise AEMError("%s must be a string array" % key)
    if seen_ids is not None:
        if layer["id"] in seen_ids:
            raise AEMError("duplicate layer id: %s" % layer["id"])
        seen_ids.add(layer["id"])


def parse_record(text: str) -> Dict[str, Any]:
    layer: Dict[str, Any] = {}
    header_seen = False
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if _HEADER.fullmatch(line):
            if header_seen:
                raise AEMError("record contains multiple headers")
            header_seen = True
            continue
        if not header_seen or "=" not in line:
            raise AEMError("invalid AEM line %d" % number)
        key, encoded = (part.strip() for part in line.split("=", 1))
        if not _KEY.fullmatch(key):
            raise AEMError("invalid field name at line %d" % number)
        if key in layer:
            raise AEMError("duplicate key at line %d: %s" % (number, key))
        layer[key] = _parse_value(encoded)
    if not header_seen:
        raise AEMError("missing [[layer]] header")
    validate_layer(layer)
    return layer


def split_records(text: str) -> List[str]:
    matches = list(_HEADER.finditer(text))
    if not matches:
        return [] if not text.strip() else [text]
    records = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        records.append(text[match.start():end])
    return records


def parse_layers(text: str) -> List[Dict[str, Any]]:
    records = split_records(text)
    layers: List[Dict[str, Any]] = []
    seen_ids: set = set()
    for record in records:
        layer = parse_record(record)
        validate_layer(layer, seen_ids)
        layers.append(layer)
    return layers


def read_report(path: Path) -> Dict[str, Any]:
    report: Dict[str, Any] = {"layers": [], "issues": []}
    if not path.exists():
        return report
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        report["issues"].append(str(exc))
        return report
    seen_ids: set = set()
    for index, record in enumerate(split_records(text), 1):
        try:
            layer = parse_record(record)
            validate_layer(layer, seen_ids)
            report["layers"].append(layer)
        except AEMError as exc:
            report["issues"].append("record %d: %s" % (index, exc))
    return report


def _encode(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        if not math.isfinite(value):
            raise AEMError("AEM numbers must be finite")
        return repr(value)
    if isinstance(value, int):
        return str(value)
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def serialize_layer(layer: Dict[str, Any]) -> str:
    record = dict(layer)
    validate_layer(record)
    ordered = [field for field in FIELD_ORDER if field in record]
    ordered.extend(sorted(field for field in record if field not in FIELD_ORDER))
    lines = ["[[layer]]"]
    lines.extend("%s = %s" % (field, _encode(record[field])) for field in ordered)
    return "\n".join(lines) + "\n\n"


def canonical_layer_hash(layer: Dict[str, Any]) -> str:
    return hashlib.sha256(serialize_layer(layer).encode("utf-8")).hexdigest()


def append_layer(path: Path, layer: Dict[str, Any]) -> Dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise AEMError("refusing to append through a symlinked AEM ledger")
    encoded = serialize_layer(layer).encode("utf-8")
    with path.open("a+b") as handle:
        if fcntl is not None:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            handle.seek(0)
            existing = handle.read().decode("utf-8")
            report_layers = parse_layers(existing) if existing.strip() else []
            ids = {item["id"] for item in report_layers}
            if layer["id"] in ids:
                raise AEMError("duplicate layer id: %s" % layer["id"])
            handle.seek(0, os.SEEK_END)
            if handle.write(encoded) != len(encoded):
                raise OSError("short write while appending AEM record")
            handle.flush()
            os.fsync(handle.fileno())
        finally:
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    return {
        "layer_id": layer["id"],
        "record_hash": hashlib.sha256(encoded).hexdigest(),
        "bytes_appended": len(encoded),
    }
