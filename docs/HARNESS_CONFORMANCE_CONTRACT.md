# AetherMind Pro Harness Conformance Contract

Status: docs-authority contract. This is not implementation and not plugin/build documentation.

## Decision

All first-class harnesses must be supported and proven. No shortcuts. The product value is all harnesses, any agent.

Required first-class harnesses:

- Hermes;
- Grok Build;
- Codex;
- Claude / Claude Code;
- bring-your-own custom harness;
- future harnesses through the same configurable harness-neutral contract.

## Contract surfaces

AetherMind Pro must define one harness-neutral contract usable across all first-class harnesses. The contract must not privilege one harness architecture.

Minimum surfaces:

- CLI command surface for local operation;
- JSON capsule for machine-readable handoff;
- plaintext handoff for agent/human-compatible orientation;
- configurable bring-your-own harness settings;
- configurable resume-session definitions;
- hook/check-in health expectations where a harness supports them;
- plugin/MCP-mediated access only where needed by a harness, without making MCP or the public plugin the Pro architecture.

## Required conformance dimensions

Every first-class harness must prove it can:

1. discover or be configured for the local Pro coordinator;
2. receive a workspace/project orientation without private Cairn state;
3. read the same harness-neutral continuity posture;
4. write or request continuity through approved local surfaces;
5. receive CORTEX/pressure/verdict/next-action output in the neutral contract;
6. degrade honestly when Pro, substrate, activation, trust review, or continuity freshness is unavailable;
7. avoid hard-coded operator paths, private profiles, and single-harness assumptions;
8. preserve user-owned artifact/uninstall semantics;
9. participate in trust-gated handling of unregistered external/downloaded/public material;
10. pass the same contract tests without relying on source-tree or founder-shell state.

## Gate rules

- Hermes/Codex-only proof is not sufficient.
- A generic fake harness alone is not sufficient.
- All named first-class harnesses must pass before private/invite/external beta or customer-facing harness claims.
- Practical engineering execution may be staged, but the design cannot make later harnesses bolt-ons or optional exceptions.
- Any implementation that hard-codes one harness or treats others as secondary is rejected.

## Deferred details

Exact command names, schema fields, and adapter internals are deferred until functional-product implementation planning. They must be specified before source implementation of harness adapters begins.
