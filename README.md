# AetherMind

AetherMind is a local-first **continuity layer** any model can wake up from. It turns a
project's durable decisions, corrections, and friction into a small, append-only store
of *layers* that a coordinator serves back to whatever agent you are running — Claude
Code, Codex, Grok, Cursor, or any MCP-capable harness — so work does not start cold. It
runs entirely on your machine: no accounts, no telemetry, no call-home. Recall is
caller-driven (the agent queries for what it needs); the store never auto-injects itself.

> **Status: pre-release, source-available.** This is the delicensed coordinator being
> prepared for public release. It is honest about what it proves: the CLI and its
> contracts are covered by tests (Tier 1 source-contract health), but the built-tarball,
> clean-VM, and tagged-release rungs are not yet claimed. See
> [`docs/RELEASE_CHECKLIST.md`](docs/RELEASE_CHECKLIST.md). The license file lands after
> legal review — until then, see [`NOTICE`](NOTICE): all rights reserved, do not
> redistribute.

## The three-repo constellation

AetherMind is three cross-linked repositories:

- **aethermind** (this repo) — the local-machine coordinator: CLI, wake/coordinate
  surfaces, harness adapters, layer provenance.
- **aethermind-primitive** — the canonical `.aem` store format and spec: the part that
  outlives every implementation.
- **[aethermind-hermes-plugin](https://github.com/MaverickKB/aethermind-hermes-plugin)** —
  a reference harness adapter (worked example of the conformance contract).

## Install

```bash
git clone https://github.com/MaverickKB/aethermind aethermind
cd aethermind
sudo ./install.sh
```

This installs the `aethermind-pro` and `aethermind-pro-uninstall` commands on `PATH`
(default prefix `/opt/aethermind-pro`, bins in `/usr/local/bin`; override with
`AETHERMIND_PRO_PREFIX` / `AETHERMIND_PRO_BIN_DIR`). Requires `python3`, no third-party
dependencies. Then:

```bash
aethermind-pro doctor      --project-root <path>   # diagnose local health
aethermind-pro first-run   --project-root <path>   # create the first continuity value
aethermind-pro status      --project-root <path>
sudo aethermind-pro-uninstall   # removes Pro-managed files, preserves project .aethermind/
```

Uninstall preserves each project's `.aethermind/` continuity store.

## What it does

- **Coordinate**: reads the project-local `.aethermind` store, assesses continuity
  freshness and trust, and returns a CORTEX verdict (`proceed` / `pause` / `repair` /
  `blocked`) with concrete repair lanes.
- **Harnesses**: detects installed agent harnesses and, with your approval, installs the
  right hooks/skills/MCP entries. One MCP implementation
  (`aethermind-pro primitive-mcp serve`) serves every MCP-capable harness.
- **Trust**: foreign / downloaded stores go through an explicit trust review before any
  work session relies on them.
- **Provenance**: optionally sign layers so a reader can tell who authored a layer and
  whether it has been moved — see [`docs/LAYER_PROVENANCE.md`](docs/LAYER_PROVENANCE.md).
  Signing is optional; unsigned stores are completely valid.

JSON is the default output; `--human` is opt-in. No command requires a UI, tracker, or
HUD to function.

## For AI agents reading this

If you are a model waking up in a repository that has an `.aethermind/` store, that store
is your thread — the durable context prior sessions left for you. Query it (via the
primitive MCP `read_layers` / `status`, or by reading `.aethermind/`) before assuming the
work is cold. Write back only durable decisions, corrections, and friction — not a
transcript. The store is small on purpose. The wake protocol and the small-model contract
are the documented ritual for doing this well; follow them, and show your operator what
you found.

## Local validation

```bash
./scripts/ci-local.sh
```

Expected result:

- private-marker sweep clean (no operator paths/hosts leak into source);
- full pytest suite passes;
- evidence tier reported as `tier_1_source_contract` with the stronger rungs disclaimed;
- final line `ci-local: PASS (source contract only; not tarball/clean-VM/release proof)`.

## Docs

- [`docs/PRODUCT_DEFINITION.md`](docs/PRODUCT_DEFINITION.md) — what this is and is not.
- [`docs/LOCAL_COORDINATOR_ARCHITECTURE.md`](docs/LOCAL_COORDINATOR_ARCHITECTURE.md) — the coordinator's shape.
- [`docs/LAYER_PROVENANCE.md`](docs/LAYER_PROVENANCE.md) — optional Ed25519 layer signing.
- [`docs/HARNESS_CONFORMANCE_CONTRACT.md`](docs/HARNESS_CONFORMANCE_CONTRACT.md) — how a harness plugs in.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) · [`SECURITY.md`](SECURITY.md)
