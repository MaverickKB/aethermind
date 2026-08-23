# Change log

## AEM v0.2.0 compatibility update

### Store format

- New bundled-substrate continuity records append to `layers.aem`.
- Existing `layers.jsonl` records remain readable and byte-for-byte unchanged.
- Unified reads return the legacy JSONL prefix followed by canonical AEM records.
- Existing AEM stores are detected and read without rewriting them.

### Compatibility

- The bundled primitive identifies as `aethermind-bundled-0.2.0`.
- Public primitive and Hermes plugin versions from 0.1 through 0.2 are accepted.
- Existing primitive MCP tool names and explicit-root arguments remain unchanged.
- Layer response aliases such as `layer_id`, `created_at`, and `kind` remain available.

### Documentation

- Added a current method reference.
- Added preservation, update, and rollback directions for legacy stores.
- Corrected the public primitive repository link.
