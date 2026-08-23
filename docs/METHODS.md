# Bundled primitive methods

The coordinator exposes one explicit-root primitive adapter directly and through
`aethermind-pro primitive-mcp serve`. Every method requires `data_root`; none
assumes the process working directory.

## `status`

Reports initialization, bundled version, compatibility range, store format,
visible layer count, canonical AEM count, legacy JSONL count, and corruption
state. It does not create a store.

## `read_layers`

Returns existing legacy JSONL records followed by canonical AEM records. Legacy
response names remain available for existing coordinator consumers. The method
does not rewrite either ledger.

## `init_store`

Explicitly creates the project-local `.aethermind/` directory. It preserves any
existing store and reports whether the directory was newly created.

## `write_layer`

Appends one canonical record to `.aethermind/layers.aem`. Existing callers may
continue supplying the established `layer` object. The adapter maps its fields to
the canonical AEM spine and returns both `id` and the existing `layer_id` alias.
It never appends to `layers.jsonl`.

## CLI example

```bash
aethermind-pro primitive-mcp call \
  --tool write_layer \
  --data-root . \
  --layer '{"kind":"decision","body":"Keep continuity in the AEM ledger"}'
```

The coordinator's higher-level commands, including `investigate`, `status`,
`map`, `coordinate`, `layers inspect`, `doctor`, and `smoke`, continue to use
this adapter without changing their command names.
