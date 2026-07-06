"""Layer provenance: optional Ed25519 signing of continuity layers.

Who placed this stone, and has it been moved? Signing is *optional* integrity
infrastructure, never a write barrier: unsigned layers are first-class, and
``verify`` simply reports each layer as signed-valid, signed-INVALID, or unsigned.

The signature covers a canonical digest of the layer's load-bearing identity
(``id``, ``ts``, ``author``, ``body``), not the whole record — so appending the
signature fields does not invalidate it, and cosmetic/derived fields are free to
differ. The signed fields map onto the store's record keys as:

    id     <- layer_id
    ts     <- created_at
    author <- author (absent => "")
    body   <- body   (absent => "")

Signatures are persisted as two additive, optional fields on the layer record:

    sig        : hex Ed25519 signature (128 hex chars)
    sig_key_id : short id of the signing public key ("aemk_" + sha256(pubkey)[:16])

These fields are additive only. Old stores that never carried them still parse and
verify (as "unsigned"); parsers that ignore unknown fields are unaffected.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from . import ed25519

# Fields excluded from the signed digest (they are the signature envelope itself).
SIGNATURE_FIELDS = ("sig", "sig_key_id")

# The load-bearing identity that a signature commits to.
SIGNED_KEYS = ("id", "ts", "author", "body")

_SECRET_LEN = 32


def key_id(pubkey: bytes) -> str:
    """Stable short identifier for a public key."""
    return "aemk_" + hashlib.sha256(pubkey).hexdigest()[:16]


def generate_keypair(path: "str | Path") -> Dict[str, Any]:
    """Generate an Ed25519 keypair and write the secret key to ``path``.

    The 32-byte secret seed is written (0600) to ``path``; the public key is written
    alongside as ``<path>.pub`` (hex). Returns the public key hex and its key id.
    Refuses to overwrite an existing secret so a key is never silently clobbered.
    """
    secret_path = Path(path).expanduser()
    if secret_path.exists():
        raise FileExistsError(f"refusing to overwrite existing key: {secret_path}")
    import secrets as _secrets

    secret = _secrets.token_bytes(_SECRET_LEN)
    pubkey = ed25519.public_key(secret)

    secret_path.parent.mkdir(parents=True, exist_ok=True)
    secret_path.write_bytes(secret)
    try:
        secret_path.chmod(0o600)
    except OSError:
        pass
    pub_path = secret_path.with_name(secret_path.name + ".pub")
    pub_path.write_text(pubkey.hex() + "\n", encoding="utf-8")

    return {
        "secret_path": str(secret_path),
        "public_path": str(pub_path),
        "public_key": pubkey.hex(),
        "key_id": key_id(pubkey),
    }


def load_secret(path: "str | Path") -> bytes:
    secret = Path(path).expanduser().read_bytes()
    if len(secret) != _SECRET_LEN:
        raise ValueError(f"secret key must be {_SECRET_LEN} bytes, got {len(secret)}")
    return secret


def canonical_digest(record: Dict[str, Any]) -> bytes:
    """Canonical SHA-256 digest over the signed identity of a layer record."""
    signed = {
        "id": record.get("layer_id") or record.get("id") or "",
        "ts": record.get("created_at") or record.get("ts") or "",
        "author": record.get("author") or "",
        "body": record.get("body") or "",
    }
    message = json.dumps(signed, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(message).digest()


def sign_layer(record: Dict[str, Any], secret: bytes) -> Dict[str, Any]:
    """Return a copy of ``record`` with additive ``sig`` and ``sig_key_id`` fields."""
    pubkey = ed25519.public_key(secret)
    signature = ed25519.sign(secret, canonical_digest(record))
    signed = dict(record)
    signed["sig"] = signature.hex()
    signed["sig_key_id"] = key_id(pubkey)
    return signed


def verify_layer(record: Dict[str, Any], pubkey: bytes) -> bool:
    """Verify a layer's signature against ``pubkey``. Unsigned records return False."""
    sig_hex = record.get("sig")
    if not sig_hex:
        return False
    try:
        signature = bytes.fromhex(sig_hex)
    except (ValueError, TypeError):
        return False
    return ed25519.verify(pubkey, canonical_digest(record), signature)


def layer_status(record: Dict[str, Any], pubkey: Optional[bytes]) -> str:
    """Classify a single layer: unsigned | signed_valid | signed_invalid.

    Without a public key, a present signature can only be reported as
    ``signed_unverified`` (the stone claims provenance we cannot check here).
    """
    if not record.get("sig"):
        return "unsigned"
    if pubkey is None:
        return "signed_unverified"
    return "signed_valid" if verify_layer(record, pubkey) else "signed_invalid"


def _read_layer_lines(store_path: Path) -> Tuple[list, bool]:
    """Read layer records from a ``.aethermind/layers.jsonl`` store."""
    layers_file = store_path / "layers.jsonl"
    if store_path.name != ".aethermind":
        # Accept either the project root or the store dir itself.
        candidate = store_path / ".aethermind" / "layers.jsonl"
        if candidate.exists():
            layers_file = candidate
    records: list = []
    corrupt = False
    if layers_file.exists():
        for line in layers_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                corrupt = True
    return records, corrupt


def _layers_file(store_path: Path) -> Path:
    if store_path.name == ".aethermind":
        return store_path / "layers.jsonl"
    return store_path / ".aethermind" / "layers.jsonl"


def sign_store(store_path: "str | Path", secret: bytes) -> Dict[str, Any]:
    """Sign every currently-unsigned layer in a store, in place.

    Additive only: already-signed layers are left untouched, and only the ``sig`` /
    ``sig_key_id`` fields are added to unsigned ones. Layer order is preserved and no
    load-bearing field is rewritten, so existing parsers keep working.
    """
    path = Path(store_path).expanduser().resolve()
    records, corrupt = _read_layer_lines(path)
    if corrupt:
        return {
            "store": str(path),
            "signed": 0,
            "already_signed": 0,
            "corrupt": True,
            "error": "store has malformed layer lines; refusing to rewrite it",
        }

    pubkey = ed25519.public_key(secret)
    kid = key_id(pubkey)
    signed_now = 0
    already = 0
    out_lines = []
    for record in records:
        if record.get("sig"):
            already += 1
        else:
            record = sign_layer(record, secret)
            signed_now += 1
        out_lines.append(json.dumps(record, sort_keys=True))

    if signed_now:
        layers_file = _layers_file(path)
        layers_file.write_text("\n".join(out_lines) + "\n", encoding="utf-8")

    return {
        "store": str(path),
        "signed": signed_now,
        "already_signed": already,
        "layer_count": len(records),
        "key_id": kid,
        "corrupt": False,
    }


def verify_store(store_path: "str | Path", pubkey: Optional[bytes] = None) -> Dict[str, Any]:
    """Verify every layer in a store and return a per-layer provenance report.

    Unsigned layers are reported, not rejected. A single ``signed_invalid`` layer
    (body moved after signing, or wrong key) sets ``tamper_detected``.
    """
    path = Path(store_path).expanduser().resolve()
    records, corrupt = _read_layer_lines(path)

    per_layer = []
    counts = {"unsigned": 0, "signed_valid": 0, "signed_invalid": 0, "signed_unverified": 0}
    for record in records:
        status = layer_status(record, pubkey)
        counts[status] += 1
        per_layer.append({
            "layer_id": record.get("layer_id") or record.get("id"),
            "status": status,
            "sig_key_id": record.get("sig_key_id"),
        })

    return {
        "store": str(path),
        "layer_count": len(records),
        "corrupt": corrupt,
        "counts": counts,
        "signed_invalid": counts["signed_invalid"] > 0,
        "tamper_detected": counts["signed_invalid"] > 0,
        "layers": per_layer,
    }
