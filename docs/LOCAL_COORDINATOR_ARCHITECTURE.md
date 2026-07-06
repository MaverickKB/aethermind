# Local coordinator architecture

Status: private Pro architecture skeleton.

## Role

The local coordinator runs on the user's local machine. Cairn-network visibility is disabled by default and may be enabled only through advanced settings for auto-detection or explicit central Cairn core configuration. The coordinator is not a full private Ember deployment and must not try to package one.

It coordinates local continuity for user-selected workspaces across the installed host. Its Ember role is host-local CORTEX pressure/verdict/repair semantics over an Atlas host profile. Atlas and host-local Ember/CORTEX services must run with or without any UI process active. A full Cairn-network Ember, where one exists, remains a separate private executive service. The coordinator imposes no deployment identity, private routes, or home-lab services.

Pro should bolt onto the public AetherMind plugin rather than build from a vendored plugin copy. When Hermes or another harness needs plugin-mediated access, Pro detects an installed compatible plugin or fetches/installs it from the public GitHub release path. The Pro artifact remains the local-machine coordinator above that substrate.

## Components

```text
customer project roots
        |
        v
AetherMind primitive store(s)  <---->  OSS primitive / public plugin / primitive MCP
        |
        v
Atlas host profile + briefing catalog
        |
        v
Host-local Ember/CORTEX coordinator
        |
        +--> pressure/verdict API
        +--> trusted-registry gate and trust review through CLI/headless path first, optional visual admin path later
        +--> project registration contract API
        +--> configurable harness-neutral capsules for Hermes / Grok Build / Codex / Claude / custom harnesses
        +--> optional tracker/HUD for people-use surfaces (never required for core)
        +--> optional web/admin UI (never required for core)
        +--> bounded audit artifacts
        +--> optional layer provenance (Ed25519 signing)
```

## Upstream source lineage

| Source | Role | Release treatment |
| --- | --- | --- |
| The AetherMind primitive (the `.aem` store format and its released package) | Primitive package baseline for the coordinator | Depend on the released artifact/tag, never a private checkout path |
| [`aethermind-hermes-plugin`](https://github.com/MaverickKB/aethermind-hermes-plugin) | Reference harness plugin when a harness needs plugin-mediated primitive access | Detect/install/fetch as a dependency; do not vendor it as coordinator source |
| Ember (host-local CORTEX pressure/verdict/repair semantics) | Source of the portable pressure/verdict/repair logic only | Package only the portable logic; a full private Ember deployment and its executive service stay out |
| Atlas (local orientation/catalog mechanisms) | Local orientation/catalog mechanisms | Split the portable library/CLI from any generated/private inventory cards |

## Host-local coordinator split required before binary build

The Pro Ember/CORTEX coordinator should contain only:

- local continuity pressure/verdict logic;
- local repair-lane suggestion logic;
- resolver interfaces that accept explicit customer config;
- audit/event schemas needed by Pro support surfaces;
- optional Cairn-network/actual-Ember handoff metadata;
- tests and fixtures that do not contain private operator state.

Full Ember deploy / local-private material must stay out of the coordinator:

- private LaunchAgents/systemd units tied to a specific operator's machines;
- excluded side projects (home automation, kiosk, companion, embedded) or operator-specific routes;
- private ledger files and existing Cairn continuity stores;
- hard-coded operator/host paths;
- profile-specific harness/Cairn assumptions.

Atlas portable core should contain only:

- project scanning/indexing;
- card/trail/briefing data model;
- local SQLite/file-backed store;
- CLI/API entry points;
- tests/fixtures with synthetic paths.

Harness adapters should contain only:

- CLI/JSON/plaintext/MCP-compatible contracts usable by Hermes, Grok Build, Codex, Claude/Claude Code, and future harnesses;
- configurable settings for bring-your-own harnesses, including custom resume-session definitions;
- plugin install/discovery/repair logic for harnesses that need the public AetherMind plugin;
- tracker/HUD integration for active registered systems, last check-in, and manual-intervention flags, gated until functional tests pass;
- conformance tests that prove all listed first-class harnesses exchange local handoff capsules without importing Pro internals before external/private-or-invite beta proof.

The admin UI is a late surface, planned near beta shipping after the CLI path is locked and functional tests pass. Private beta means in-house only; invite/external beta is a different posture and requires the web UI. The UI should expose the same control surfaces that remain available through CLI/service commands:

- settings for local data, harnesses, plugin behavior, and advanced disabled-by-default Cairn-network context;
- host service start, stop, restart, and health views for AetherMind Pro services such as Atlas and host-local Ember/CORTEX;
- log views for users who prefer visual inspection over CLI logs;
- root and directory-group views over Atlas-organized layers;
- layer and line-level management actions: hide, archive, quarantine, mark stale, and additional management actions as designed;
- import, locate, refresh, and trust-review scans;
- clear visual trust gates for anything not in the trusted registry, including downloaded, external, or public-untrusted code and continuity before any active work session relies on it.

The admin UI is not part of the required execution path for lower-level functional iteration. It may be a local web interface and exists for users who want visual, transparent administration instead of CLI-only control after the CLI path is proven. Core services, CLI controls, harness comms, trust gating, and coordination must continue to function when the UI is closed or never launched. Tracker/HUD must not become a dependency for service function, but beta people-use claims require all beta pieces that are in scope for the claimed beta posture.

Atlas private/generated material must stay out of the coordinator:

- generated cards for a specific operator's mesh;
- private wiki/routing files;
- local MCP preset cards that embed operator topology.

## Future candidate acceptance

This architecture should be treated as untrustworthy until serious critical review. A future locked release is not complete until it has:

1. A product definition and boundary.
2. A manifest listing exactly which host-local Ember/CORTEX, Atlas, and harness-adapter modules are included, proving no full private Ember deployment is packaged.
3. A release-surface scanner proving no private paths or out-of-scope terms ship (`scripts/verify_no_legacy_refs.py`).
4. A built-distribution smoke test that runs from an extracted tarball on a clean machine, not from a source checkout (the Phase 4 OSS ladder: dist tarball → clean-VM smoke → tagged release).

## Current state

This is a source-available product surface. It ships host-local pressure/verdict behavior only, not any full private Ember deployment. The next implementation step is to keep the plugin-as-dependency boundary explicit while improving the local-machine Atlas/Ember coordinator, CLI/service controls, optional admin UI, optional tracker/HUD, and conformance paths for Hermes, Grok Build, Codex, Claude/Claude Code, and custom harnesses.
