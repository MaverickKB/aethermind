# AetherMind Pro System Contract

AetherMind Pro is the single installed, local machine-aware coordinator above the AetherMind primitive. It is source-available and local-first: no accounts, no telemetry, no call-home.

## Boundary

- **OSS AetherMind primitive:** data-local `.aethermind/` layers beside the relevant data/source being worked. For code work this is often a project checkout, but repo-local is an example, not the architecture.
- **AetherMind primitive MCP / public plugin:** neutral substrate adapters over the same primitive. They expose explicit-root tools for status, init, read, write, validation, and export with policy controls. MCP and harness plugins are substrate/harness surfaces, not the Pro architecture.
- **AetherMind Pro:** machine-aware coordination across user-selected host-visible roots from one installed local machine. It is not merely a layer counter, not merely a single-repo reporter, not a distributed network, and not a private Cairn deployment package.
- **Cairn network boundary:** when a customer/operator is inside the Cairn network, Pro may use Cairn-visible services as optional upstream context. Pro remains local-machine authoritative for its own installed state and must degrade honestly when the Cairn network or actual Ember is unavailable.
- **Atlas role:** keep the local machine map: roots, continuity stores, manifests, workspace state, component health, stale/missing/corrupt continuity, mounted/remote/container metadata, and safe local topology signals.
- **Ember/CORTEX role:** Pro ships host-local Ember/CORTEX coordination semantics as services that run with or without an admin UI active: salience hints, pressure codes, gate levels, verdicts, repair lanes, and recommended next actions over the Atlas map. It is not a full private Ember deployment. A full Cairn-network Ember, where one exists, remains a separate executive service.
- **Trust-gate role:** Ember owns trust gating for anything not in the trusted registry, including downloaded, externally created, or public-untrusted code and continuity input and prompt-injection-like dangerous content. Before trust is granted, Pro must expose an inspectable review outside any active work session. The scan may be programmatic, agentic, or both. Headless/CLI operation must remain sufficient. Minimum CLI proof is verdict, pressure codes, evidence labels, redacted source/path summary, dangerous-content finding categories, and audit event ID. Review outcomes classify material as safe, questionable, or dangerous: safe may proceed, questionable requires human approval, and dangerous is reported to a human immediately. The optional admin UI should make the review visual, verbose, and clearer after the CLI path is locked.
- **Harness role:** Pro bolts onto local agent harnesses instead of becoming one. Hermes, Grok Build, Codex, Claude/Claude Code, custom bring-your-own harnesses, and future harnesses should be able to use the same local-machine posture through a configurable universal contract: documented CLI, JSON, plaintext, MCP-compatible, or plugin-mediated surfaces plus configurable resume-session definitions. Before any external/private-or-invite beta proof, all listed first-class harnesses must be proven unless Ken materially changes this requirement.
- **Tracker/HUD role:** Pro will need tracker/HUD visibility for beta people-use surfaces, including last check-in and manual-intervention status, but tracker/HUD should be developed after functional tests pass because it is easy to break during iteration. Tracker/HUD is not required for lower-level functional iteration and is not required for Pro services to function.
- **Admin interface role:** Pro must provide a CLI-complete control path first. A minimal web/admin UI is required before invite/external beta and should be planned near beta shipping after functional tests pass. Private beta means in-house only; invite/external beta is a different posture. The admin UI can inspect settings and data, show logs, start/stop/restart AetherMind Pro host services such as Ember/Atlas, view layers grouped by repo root or directory group, run import/locate/refresh scans, and mark individual lines/layers as hidden, archived, quarantined, or stale when they believe performance or knowledge quality is affected.
- **Plugin role:** When Hermes or another harness needs the public AetherMind plugin, Pro should detect an installed compatible plugin or fetch/install it from the public GitHub release path. The plugin is not vendored as Pro's source base.
- **Cairn network role:** Cairn-network context is disabled by default. Advanced settings may manually enable auto-detection or explicit central Cairn core configuration.
- **Provenance role:** layers may optionally be signed (Ed25519) so a reader can tell who authored a layer and whether it has been moved. Signing is optional infrastructure, never a write barrier; unsigned stores are fully valid. See `docs/LAYER_PROVENANCE.md`.

## Shipped command contract

- `status`: report component, substrate, and distribution health.
- `substrate status`: report active primitive substrate source, version, provenance, compatibility range, and layer visibility.
- `primitive-mcp call`: local proof surface for the policy-aware AetherMind primitive MCP tool architecture.
- `keygen` / `sign` / `verify`: generate a provenance keypair, sign a store's unsigned layers, and report per-layer signature status.
- `roots`: configure, list, and remove user-selected host-visible roots.
- `map`: build or refresh the Atlas-style machine map over configured roots.
- `coordinate`: use the Atlas map plus host-local Ember/CORTEX semantics to produce local orientation, verdict, and next actions; include the boundary that actual Cairn-network Ember carries private executive load when available.
- `comms`: write/read/brief harness-neutral Agent Comms capsules through CLI/JSON/plaintext for Hermes, Grok Build, Codex, Claude/Claude Code, and future harnesses.
- `harnesses`: configure built-in and custom harness adapters, including resume-session definitions, check-in behavior, and hook health expectations.
- `services`: start, stop, restart, and report AetherMind Pro host services, including Atlas and host-local Ember/CORTEX services.
- `tracker`: optionally display active registered systems, last check-ins, and manual-intervention flags without making the HUD a runtime requirement.
- `trust`: run Ember-managed trust review for downloaded, externally created, or public-untrusted code/continuity before it is trusted; CLI/headless review is required, visual admin review is optional after the CLI path is locked.
- `layers`: browse roots and directory groups, inspect layers/lines, and mark entries as hidden, archived, quarantined, or stale under user authority through CLI and optional admin UI paths. Legacy hard labels such as superseded, ignored, or deleted are not preferred customer terms.
- `settings`: control local data settings, advanced harness behavior, and disabled-by-default Cairn-network context.
- `admin-ui`: optionally launch a local web/admin interface for settings, service control, log views, layer inspection, trust review, and data management.
- `plugins`: detect, verify, install, or repair public AetherMind harness plugins when a harness requires plugin-mediated access.
- `audit`: inspect bounded local audit events.
- `support-bundle`: export redacted support context without project content.
- `export`: export user-owned Pro state (always available).
- `smoke`: exercise the primitive write/read path for source-contract proof.

## Release proof invariant

Release readiness climbs the OSS ladder (`docs/RELEASE_CHECKLIST.md`): source contract
→ built distribution tarball → clean-VM smoke → tagged release. A clean-VM proof must
run from the built distribution on a clean machine — no source tree, private paths, or
operator shell knowledge — and exercise substrate bootstrap, plugin install/discovery
where required, roots, map, coordinate, cross-harness comms across all listed
first-class harnesses, trust review, CLI data controls, host-service control, audit,
support-bundle, export, and disabled-by-default Cairn-network behavior. If the admin UI
or tracker/HUD ship in a build, the proof must also show they can be launched, report
honestly, and be absent/inactive without breaking core services.
