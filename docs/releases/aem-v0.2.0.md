# AEM v0.2.0 compatibility update

This update aligns the source-available coordinator's bundled continuity
substrate with the public AetherMind 0.2 primitive and Hermes adapter.

## Highlights

- Canonical `.aem` writes replace new JSONL continuity writes.
- Existing JSONL layers remain readable and unchanged.
- Existing AEM stores are visible without conversion.
- The public Hermes plugin 0.2 generation is accepted as compatible.
- Primitive MCP names and higher-level coordinator commands remain stable.
- Preservation and rollback directions cover stores that contain either or both
  continuity generations.

## Existing installations

No destructive migration runs during startup, status, read, or write. Preserve
the store before updating, verify the reported legacy count, and keep the
post-update AEM store if rolling the application back. Full directions are in
[`UPGRADING_TO_AEM.md`](../UPGRADING_TO_AEM.md).

## Release boundary

This is the AEM compatibility generation for the source tree. The package keeps
its existing pre-release version and evidence classification. CI redesign,
update discovery, and an automated updater belong to the later update project.
