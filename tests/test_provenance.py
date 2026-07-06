"""Layer provenance contract: keygen, sign, verify, tamper, and old-store compat.

Signing is optional integrity infrastructure, never a write barrier. Unsigned layers
are first-class; verification reports each layer as signed-valid, signed-INVALID, or
unsigned.
"""

import json
from pathlib import Path

import pytest

from aethermind_pro import cli, ed25519, provenance


def _make_store(root: Path, records):
    """Write a minimal .aethermind/layers.jsonl store (as the primitive does)."""
    store = root / ".aethermind"
    store.mkdir(parents=True, exist_ok=True)
    (store / "manifest.json").write_text(
        json.dumps({"store_version": "aethermind-store-v1"}) + "\n", encoding="utf-8")
    lines = [json.dumps(r, sort_keys=True) for r in records]
    (store / "layers.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return store


def test_keypair_roundtrip(tmp_path):
    info = provenance.generate_keypair(tmp_path / "prov.key")
    assert info["key_id"].startswith("aemk_")
    secret = provenance.load_secret(info["secret_path"])
    assert len(secret) == 32
    # The derived public key matches the written .pub and the reported hex.
    pub = ed25519.public_key(secret)
    assert pub.hex() == info["public_key"]
    assert Path(info["public_path"]).read_text().strip() == info["public_key"]


def test_keygen_refuses_to_overwrite(tmp_path):
    provenance.generate_keypair(tmp_path / "prov.key")
    with pytest.raises(FileExistsError):
        provenance.generate_keypair(tmp_path / "prov.key")


def test_sign_and_verify_layer(tmp_path):
    info = provenance.generate_keypair(tmp_path / "k")
    secret = provenance.load_secret(info["secret_path"])
    pub = ed25519.public_key(secret)
    record = {"layer_id": "layer-1", "created_at": "2026-07-05T00:00:00Z",
              "author": "cairn", "body": "who placed this stone"}
    signed = provenance.sign_layer(record, secret)
    assert signed["sig_key_id"] == info["key_id"]
    assert provenance.verify_layer(signed, pub) is True
    assert provenance.layer_status(signed, pub) == "signed_valid"


def test_tamper_detection_body_moved(tmp_path):
    info = provenance.generate_keypair(tmp_path / "k")
    secret = provenance.load_secret(info["secret_path"])
    pub = ed25519.public_key(secret)
    record = {"layer_id": "layer-1", "created_at": "2026-07-05T00:00:00Z",
              "author": "cairn", "body": "original"}
    signed = provenance.sign_layer(record, secret)
    # Move the stone: mutate the signed body but keep the old signature.
    signed["body"] = "the stone has been moved"
    assert provenance.verify_layer(signed, pub) is False
    assert provenance.layer_status(signed, pub) == "signed_invalid"


def test_wrong_key_is_invalid(tmp_path):
    info = provenance.generate_keypair(tmp_path / "k")
    secret = provenance.load_secret(info["secret_path"])
    record = {"layer_id": "l", "created_at": "t", "author": "a", "body": "b"}
    signed = provenance.sign_layer(record, secret)
    other = ed25519.public_key(bytes(range(32)))
    assert provenance.verify_layer(signed, other) is False


def test_verify_store_reports_mixed(tmp_path):
    info = provenance.generate_keypair(tmp_path / "k")
    secret = provenance.load_secret(info["secret_path"])
    pub = ed25519.public_key(secret)
    signed = provenance.sign_layer(
        {"layer_id": "a", "created_at": "t1", "author": "x", "body": "one"}, secret)
    unsigned = {"layer_id": "b", "created_at": "t2", "author": "x", "body": "two"}
    tampered = provenance.sign_layer(
        {"layer_id": "c", "created_at": "t3", "author": "x", "body": "three"}, secret)
    tampered["body"] = "moved"
    _make_store(tmp_path, [signed, unsigned, tampered])

    report = provenance.verify_store(tmp_path, pub)
    assert report["layer_count"] == 3
    assert report["counts"]["signed_valid"] == 1
    assert report["counts"]["unsigned"] == 1
    assert report["counts"]["signed_invalid"] == 1
    assert report["tamper_detected"] is True


def test_verify_store_without_pubkey_is_unverified(tmp_path):
    info = provenance.generate_keypair(tmp_path / "k")
    secret = provenance.load_secret(info["secret_path"])
    signed = provenance.sign_layer(
        {"layer_id": "a", "created_at": "t", "author": "x", "body": "b"}, secret)
    _make_store(tmp_path, [signed])
    report = provenance.verify_store(tmp_path, None)
    assert report["counts"]["signed_unverified"] == 1
    assert report["tamper_detected"] is False


def test_old_store_without_sig_fields_still_parses(tmp_path):
    """Compat: a store written before signing existed carries no sig fields.

    It must parse cleanly and verify as entirely unsigned (never rejected)."""
    legacy = [
        {"layer_id": "old-1", "created_at": "2026-01-01T00:00:00Z",
         "kind": "workspace_observation", "body": "pre-provenance layer"},
        {"layer_id": "old-2", "created_at": "2026-01-02T00:00:00Z", "body": "another"},
    ]
    _make_store(tmp_path, legacy)
    report = provenance.verify_store(tmp_path, None)
    assert report["corrupt"] is False
    assert report["layer_count"] == 2
    assert report["counts"]["unsigned"] == 2
    assert report["tamper_detected"] is False


def test_sign_store_is_additive_only(tmp_path):
    """Signing adds only sig / sig_key_id and preserves load-bearing fields + order."""
    info = provenance.generate_keypair(tmp_path / "k")
    secret = provenance.load_secret(info["secret_path"])
    legacy = [
        {"layer_id": "old-1", "created_at": "t1", "body": "one", "kind": "obs"},
        {"layer_id": "old-2", "created_at": "t2", "body": "two", "kind": "obs"},
    ]
    _make_store(tmp_path, legacy)
    result = provenance.sign_store(tmp_path, secret)
    assert result["signed"] == 2

    records, corrupt = provenance._read_layer_lines(tmp_path)
    assert corrupt is False
    assert [r["layer_id"] for r in records] == ["old-1", "old-2"]
    for original, now in zip(legacy, records):
        # Every original field is preserved untouched.
        for key, value in original.items():
            assert now[key] == value
        # Only the two signature fields were added.
        assert set(now) - set(original) == {"sig", "sig_key_id"}

    # Re-signing is idempotent: already-signed layers are left alone.
    again = provenance.sign_store(tmp_path, secret)
    assert again["signed"] == 0
    assert again["already_signed"] == 2


# --- CLI integration ---

def _run(args, capsys):
    code = cli.main(args)
    out = capsys.readouterr().out
    return code, json.loads(out)


def test_cli_keygen_sign_verify_flow(tmp_path, capsys):
    key = tmp_path / "prov.key"
    proj = tmp_path / "proj"
    proj.mkdir()
    _make_store(proj, [{"layer_id": "l1", "created_at": "t", "author": "a", "body": "b"}])

    code, keyout = _run(["keygen", "--out", str(key), "--json"], capsys)
    assert code == 0 and keyout["ok"] is True
    pub = keyout["public_key"]

    code, before = _run(["verify", "--project-root", str(proj), "--pubkey", pub, "--json"], capsys)
    assert code == 0
    assert before["counts"]["unsigned"] == 1

    code, signed = _run(["sign", "--project-root", str(proj), "--key", str(key), "--json"], capsys)
    assert code == 0 and signed["signed"] == 1

    code, after = _run(["verify", "--project-root", str(proj), "--pubkey", pub, "--json"], capsys)
    assert code == 0
    assert after["counts"]["signed_valid"] == 1
    assert after["tamper_detected"] is False


def test_cli_verify_requires_project_root(capsys):
    code, payload = _run(["verify", "--json"], capsys)
    assert code == 1
    assert payload["ok"] is False
    assert payload["error"]["code"] == "project_root_required"


def test_cli_sign_requires_key(tmp_path, capsys):
    proj = tmp_path / "proj"
    proj.mkdir()
    code, payload = _run(["sign", "--project-root", str(proj), "--json"], capsys)
    assert code == 1
    assert payload["error"]["code"] == "key_required"


def test_investigate_opt_in_signing(code_repo, state_dir, tmp_path, capsys):
    key = tmp_path / "prov.key"
    _run(["keygen", "--out", str(key), "--json"], capsys)
    _run(["settings", "set", "provenance.sign_new_layers", "true",
          "--state-dir", state_dir, "--json"], capsys)
    _run(["settings", "set", "provenance.key_path", str(key),
          "--state-dir", state_dir, "--json"], capsys)

    code, payload = _run(["investigate", "--project-root", code_repo,
                          "--state-dir", state_dir, "--json"], capsys)
    assert code == 0
    assert payload["layer"]["provenance"]["signing"] == "signed"

    pub = (key.with_name(key.name + ".pub")).read_text().strip()
    code, report = _run(["verify", "--project-root", code_repo, "--pubkey", pub, "--json"], capsys)
    assert report["counts"]["signed_valid"] >= 1


def test_investigate_signing_off_by_default(code_repo, state_dir, capsys):
    code, payload = _run(["investigate", "--project-root", code_repo,
                          "--state-dir", state_dir, "--json"], capsys)
    assert code == 0
    # Signing is opt-in: the write succeeds and the layer is unsigned by default.
    assert payload["layer"]["provenance"]["signing"] == "disabled"


def test_investigate_signing_enabled_without_key_still_writes(code_repo, state_dir, capsys):
    _run(["settings", "set", "provenance.sign_new_layers", "true",
          "--state-dir", state_dir, "--json"], capsys)
    code, payload = _run(["investigate", "--project-root", code_repo,
                          "--state-dir", state_dir, "--json"], capsys)
    # Never a write barrier: no key configured => layer still created, just unsigned.
    assert code == 0
    assert payload["layer"]["created"] is True
    assert payload["layer"]["provenance"]["signing"] == "enabled_but_no_key"
