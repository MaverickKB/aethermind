# AetherMind — product definition

Status: source-available, pre-release. This repo is the coordinator, delicensed for
public release — not the primitive spec root and not a private operator deployment.

## Product promise

AetherMind is a local continuity layer that improves agent accuracy, reduces
hallucinations and token churn, and orients models from any supported harness so agents
do not wake up alone and cold. It is local-first: no accounts, no telemetry, no
call-home.

What you get:

- the AetherMind primitive contract and validators as the substrate baseline;
- a local-machine coordinator stack with Atlas host mapping and Ember/CORTEX pressure,
  verdict, and repair semantics;
- configurable harness-neutral adapters so Hermes, Grok Build, Codex, Claude/Claude
  Code, bring-your-own harnesses, and future local agent harnesses share the same
  host-local continuity posture;
- plugin install/discovery support for harnesses that need the reference AetherMind
  plugin, without making the plugin the coordinator's implementation base;
- a complete CLI/service control path, with an optional web/admin UI (never required
  for core) for settings, data ownership, layer inspection, service control, log views,
  trust review, and harness health;
- optional Ed25519 layer provenance (`keygen` / `sign` / `verify`);
- fully user-owned local state and configuration; export is always available.

What is out of scope:

- private operator identity, LAN behavior, routes, local endpoints, side projects
  (home automation, kiosk, companion, embedded), or household-specific abilities;
- any hosted service, telemetry, accounts, or monetization machinery (removed in
  Phase 0, not deferred).

## Capabilities

| Capability | Included |
| --- | --- |
| Continuity primitive | The `.aem` contract, validators, and reference adapter as the substrate baseline |
| AetherMind stores | Project-local `.aem` contract; dense continuity discipline |
| Reference AetherMind plugin | Installed, detected, or fetched when a harness needs it; not vendored as coordinator source |
| Configurable harness contract | Universal local contract with configurable harness settings and custom resume-session definitions; tracker/HUD is a separate optional overlay |
| Full Ember executive layer | Not packaged; the coordinator ships host-local Ember/CORTEX coordination semantics only |
| Atlas-class orientation | Host-local Atlas profile, catalog, briefing, and index for user-selected roots |
| Optional admin interface | Optional web/admin interface for visual settings, service control, logs, data control, root grouping, layer inspection, import/locate/refresh scans, trust review, and layer management — never required for core |
| Harness coordination | Shared CLI/JSON/plaintext/MCP-compatible handoff surfaces for Hermes, Grok Build, Codex, Claude/Claude Code, and future harnesses |
| Layer provenance | Optional Ed25519 signing and verification |
| Packaging | Source-available; distribution artifacts follow the OSS release ladder (`docs/RELEASE_CHECKLIST.md`) |

## Local coordinator scope

The Pro local coordinator is a customer-local system. It must be configurable without hard-coded operator paths, private endpoints, or identity assumptions.

Required coordinator functions for a future locked candidate. This is preliminary architecture mapping, not a current RC plan, and it should be treated as provisional until serious critical review:

1. Inspect a customer-selected project root.
2. Use AetherMind continuity records as dense continuity substrate, not as a broad memory log.
3. Build an Atlas host profile over allowed local roots.
4. Apply host-local Ember/CORTEX pressure, verdict, and repair-lane checks before mutation, release, or completion claims; do not pretend this is Ken's private full Ember deployment.
5. Enforce license activation through an initial authority call, then preserve permanent offline local use once activated.
6. Produce bounded audit artifacts that are safe for customer support review.
7. Provide configurable harness-neutral local handoff capsules and status surfaces for Hermes, Grok Build, Codex, Claude/Claude Code, bring-your-own harnesses, and future harnesses; prove all listed first-class harnesses before external/private-or-invite beta proof.
8. Keep Atlas/Ember host services functional without any UI process active; CLI control must remain a complete operating path.
9. Provide tracker/HUD visibility as a beta people-use surface after functional tests pass, while keeping it separate from core service function during lower-level iteration.
10. Install, discover, or fetch the public AetherMind plugin when a supported harness needs it.
11. Run Ember-managed trust gates before anything not in the trusted registry is trusted. CLI output must be sufficient for headless operation and classify reviewed material as safe, questionable with human approval, or dangerous with immediate human report; admin UI should make review visual, verbose, and inspectable outside any active work session after the CLI path is locked.
12. Offer admin UI control before invite/external beta over settings, roots, grouped layers, layer actions, imports, locate/refresh scans, host service start/stop/restart, logs, and data ownership for users who prefer visual administration over CLI operation.
13. Keep Cairn-network context disabled by default and expose it only through manually gated advanced settings for auto-detection or manual central-core configuration.
14. Fail closed for license enforcement and fail honestly/degraded for continuity freshness.

## Non-loss invariants

- One primitive and protocol across every deployment of AetherMind.
- The coordinator coordinates the installed local machine; it does not sell private operator infrastructure, package a private Ember deployment, or become a fork of the reference plugin.
- Contracts and audit interfaces stay explicit and inspectable.
- UI and tracker surfaces must never be core service dependencies; core control stays on the CLI.
- No artifact may require a specific operator's home directory, private LAN hosts, or private profile state. The private-marker gate (`scripts/verify_no_legacy_refs.py`) enforces this.
