import json
from pathlib import Path

import pytest

from aethermind_pro import aem_codec, primitive_mcp, provenance


def canonical_layer(layer_id="0001", body="canonical AEM"):
    return {
        "id": layer_id,
        "ts": "2026-08-22T00:00:00Z",
        "author": "fixture",
        "type": "decision",
        "body": body,
        "ctx": "test/compatibility",
        "conf": 1.0,
        "markers": ["compatibility"],
        "primitive": "layer",
    }


def test_codec_roundtrip_and_duplicate_rejection(tmp_path):
    path = tmp_path / "layers.aem"
    first = canonical_layer()
    receipt = aem_codec.append_layer(path, first)
    assert receipt["layer_id"] == "0001"
    assert aem_codec.read_report(path)["layers"] == [first]
    with pytest.raises(aem_codec.AEMError, match="duplicate"):
        aem_codec.append_layer(path, first)


def test_bundled_substrate_writes_only_aem(tmp_path):
    primitive_mcp.call("init_store", {"data_root": str(tmp_path)})
    result = primitive_mcp.call(
        "write_layer",
        {"data_root": str(tmp_path), "layer": {"kind": "workspace_observation"}},
    )
    assert result["ok"] is True
    store = tmp_path / ".aethermind"
    assert (store / "layers.aem").is_file()
    assert not (store / "layers.jsonl").exists()
    assert not (store / "manifest.json").exists()


def test_legacy_jsonl_remains_byte_identical_and_visible(tmp_path):
    store = tmp_path / ".aethermind"
    store.mkdir()
    legacy = {"layer_id": "legacy-1", "created_at": "2026-01-01T00:00:00Z", "kind": "decision"}
    legacy_path = store / "layers.jsonl"
    legacy_path.write_text(json.dumps(legacy, sort_keys=True) + "\n", encoding="utf-8")
    before = legacy_path.read_bytes()

    primitive_mcp.call("write_layer", {"data_root": str(tmp_path), "layer": {"kind": "discovery"}})
    read = primitive_mcp.call("read_layers", {"data_root": str(tmp_path)})

    assert legacy_path.read_bytes() == before
    assert [item["layer_id"] for item in read["layers"]][:1] == ["legacy-1"]
    assert read["count"] == 2
    assert read["legacy_jsonl_preserved"] is True


def test_existing_canonical_aem_is_visible_without_rewrite(tmp_path):
    store = tmp_path / ".aethermind"
    store.mkdir()
    path = store / "layers.aem"
    path.write_text(aem_codec.serialize_layer(canonical_layer()), encoding="utf-8")
    before = path.read_bytes()
    status = primitive_mcp.call("status", {"data_root": str(tmp_path)})
    read = primitive_mcp.call("read_layers", {"data_root": str(tmp_path)})
    assert status["visible_layers"] == 1
    assert read["layers"][0]["body"] == "canonical AEM"
    assert path.read_bytes() == before


def test_sign_store_refuses_to_rewrite_existing_aem(tmp_path):
    store = tmp_path / ".aethermind"
    store.mkdir()
    (store / "layers.aem").write_text(
        aem_codec.serialize_layer(canonical_layer()), encoding="utf-8"
    )
    secret = bytes(range(32))
    before = (store / "layers.aem").read_bytes()
    result = provenance.sign_store(tmp_path, secret)
    assert result["append_only_refusal"] is True
    assert (store / "layers.aem").read_bytes() == before
