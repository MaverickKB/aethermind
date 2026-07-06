# Security

## Threat model

AetherMind is **local-first**. After the Phase 0 delicensing surgery there is **no
call-home of any kind**: no activation, no telemetry, no license server, no accounts.
The coordinator reads and writes only local files you point it at, and it makes no
network requests as part of its normal operation.

What that means for the threat model:

- **No central authority.** There is no server that can be compromised to affect your
  install, revoke it, or exfiltrate your data. The trust boundary is your machine.
- **Explicit roots only.** Every command that touches a store takes an explicit
  `--project-root` / `data_root`; there is no hidden current-directory assumption and
  no implicit traversal.
- **Bounded audit and support surfaces.** Audit events and support bundles carry only
  hashed root ids, component health, and bounded event metadata — never raw project
  content, secrets, or private paths. Root paths are hashed (`root-…`); the hostname is
  hashed (`host-…`).
- **Customer-owned state.** Your `.aethermind/` store and Pro state are yours; `export`
  is always available and uninstall preserves your continuity store.

## Trust gate for foreign stores

A continuity store you did not create — downloaded, shared, or public — is untrusted
input. It can contain prompt-injection-style content aimed at whatever agent reads it.
Before any work session relies on foreign material, run an explicit trust review:

```bash
aethermind-pro trust review --subject <path> --origin downloaded --json
```

Review outcomes classify material as **safe**, **questionable** (requires human
approval), or **dangerous** (reported to a human immediately, not trusted). Headless
CLI review is sufficient; it produces a verdict, pressure codes, a redacted
source/path summary, dangerous-content finding categories, and an audit event id.

## Layer provenance

Optional Ed25519 signing (`aethermind-pro keygen` / `sign` / `verify`, see
[`docs/LAYER_PROVENANCE.md`](docs/LAYER_PROVENANCE.md)) lets a reader tell whether a
layer was authored by the holder of a given key and has not been modified. Provenance
answers authenticity and tamper-evidence; it does **not** encrypt layers, gate reads,
or phone home. Trust in a public key is established out of band.

## What is explicitly out of scope

- Encryption at rest of the store (it is plain, human-readable local data by design).
- Protecting against an attacker who already has code execution and full control of
  your machine.
- Any DRM / anti-tamper of the coordinator itself (the commercial-protection apparatus
  was removed in Phase 0).

## Reporting a vulnerability

Please report security issues privately rather than opening a public issue. Open a
GitHub security advisory on the repository
(<https://github.com/MaverickKB/aethermind/security/advisories>) with a description,
reproduction steps, and impact. You will get an acknowledgement; please allow
reasonable time for a fix before any public disclosure.
