# Layer provenance (optional Ed25519 signing)

*Who placed this stone, and has it been moved?*

Layer provenance lets an author sign continuity layers so a later reader can tell
whether a layer is authentic and unmodified. It is **optional integrity
infrastructure, never a write barrier**: unsigned layers are first-class, and
verification simply *reports* each layer's status. Nothing about signing gates a
write, and a store with zero signatures is a completely valid store.

## What is signed

A signature commits to a layer's load-bearing identity, not its whole record:

| Signed field | Source record key | Fallback |
| --- | --- | --- |
| `id` | `layer_id` (or `id`) | `""` |
| `ts` | `created_at` (or `ts`) | `""` |
| `author` | `author` | `""` |
| `body` | `body` | `""` |

The digest is `SHA-256` over the canonical JSON of `{id, ts, author, body}`
(`sort_keys=True`, compact separators). The Ed25519 signature (RFC 8032) is computed
over that digest. Because only the identity is signed, appending the signature fields
does not invalidate the signature, and cosmetic or derived fields may differ freely.

## How it is stored (additive fields only)

Two optional fields are added to the layer record:

| Field | Meaning |
| --- | --- |
| `sig` | hex-encoded Ed25519 signature (128 hex chars) |
| `sig_key_id` | short id of the signing public key: `aemk_` + `sha256(pubkey)[:16]` |

These fields are **additive**. A store written before provenance existed carries
neither field; it parses cleanly and verifies as entirely `unsigned`. Any parser that
ignores unknown fields is unaffected. Signing an existing store rewrites only the
signature fields of previously-unsigned layers — load-bearing fields and layer order
are preserved — so old readers keep working.

## Verification report

`verify` (and `provenance.verify_store`) returns a per-layer status:

| Status | Meaning |
| --- | --- |
| `unsigned` | no `sig` field — normal, not an error |
| `signed_valid` | signature checks out against the supplied public key |
| `signed_invalid` | signature present but does not verify (body moved, or wrong key) — tamper |
| `signed_unverified` | signature present but no public key was supplied to check it |

A single `signed_invalid` layer sets `tamper_detected: true` on the store report.

## CLI

```bash
aethermind-pro keygen --out <secret-key-path>        # writes <path> (0600) + <path>.pub
aethermind-pro sign   --project-root . --key <path>  # sign currently-unsigned layers
aethermind-pro verify --project-root . --pubkey <hex-or-omit>
```

Opt-in signing of new layers is controlled by two settings; when enabled without a
readable key, the write still succeeds and the layer is simply left unsigned:

```bash
aethermind-pro settings set provenance.sign_new_layers true
aethermind-pro settings set provenance.key_path <secret-key-path>
```

## Security notes

- The secret key never leaves the machine and is never written into a store; only the
  public key id (`sig_key_id`) is persisted alongside the signature.
- Provenance answers "was this layer authored by the holder of key K and unchanged
  since?" It does **not** encrypt layers, gate reads, or phone home.
- Trust in a public key is out of band (share the `.pub` / `key_id` yourself); the
  store does not vouch for which key is legitimate.
