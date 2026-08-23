# Substrate Ownership

AetherMind Pro is a one-stop product, but the OSS AetherMind primitive remains the data-local substrate. The root primitive is intended to remain an open-source proof free for use. Pro must not create a hidden parallel AetherMind.

Pro may advance the OSS primitive and free plugins for performance, reliability, and features, but customer installs must detect existing primitive/plugin versions and adapt without silently introducing version conflicts.

The public AetherMind plugin is an installable harness adapter over that substrate. Pro should install, discover, fetch, or repair it when a harness needs plugin-mediated access; Pro must not vendor the plugin as its implementation base.

## Active substrate precedence

1. Use a compatible user-managed external AetherMind primitive when present.
2. Block an incompatible external primitive unless the user explicitly selects the bundled substrate.
3. Use the bundled compatible primitive when no external install exists.
4. Never silently overwrite, downgrade, hide, or replace a user-managed install.
5. Report upgrade/adaptation decisions clearly when Pro can use a newer primitive or plugin capability.

## Harness plugin precedence

1. Use a compatible installed public AetherMind plugin when the harness already has one.
2. Repair or upgrade an incompatible plugin only with explicit user/operator approval.
3. Fetch/install the plugin from the public GitHub release path when it is needed and missing.
4. Keep Pro's host-local Atlas/Ember state separate from plugin-owned harness files.

## Status contract

`aethermind-pro substrate status --json` reports:

- active source: external, bundled, external_incompatible, or missing;
- version and compatibility range;
- source ref and manifest provenance;
- whether network access is required;
- whether this substrate will mutate `.aethermind/` stores;
- whether the selected data/source root already has visible layers.

## Data compatibility

Bundled-substrate writes remain readable by the accepted OSS compatibility range. A later standalone OSS install must be able to read and write the same data-local `.aethermind/` store without migration loss.

The AEM compatibility update preserves earlier coordinator stores in place.
Existing JSONL records remain readable, while all new continuity appends to the
canonical AEM ledger. Operators retain both representations during rollback so
neither the legacy prefix nor newer AEM records are lost.
