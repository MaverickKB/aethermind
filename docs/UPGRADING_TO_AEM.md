# Upgrading an existing coordinator store to AEM writes

The AEM compatibility update does not rewrite or delete an existing JSONL
store. The compatibility path is built into normal reads:

1. Existing `layers.jsonl` records remain the first records returned.
2. New continuity appends to `layers.aem`.
3. Later reads return the preserved JSONL prefix followed by the new AEM records.

## Preserve the current store

From each project root whose continuity is not already versioned:

```bash
cp -R .aethermind .aethermind.pre-aem-v0.2
```

Record checksums when the store is especially important:

```bash
shasum -a 256 .aethermind/layers.jsonl 2>/dev/null || true
```

## Update and verify

Update the application checkout, then run:

```bash
aethermind-pro status --project-root . --json
aethermind-pro layers inspect --project-root . --json
```

`legacy_jsonl_layers` reports the preserved legacy count. The first subsequent
write creates or appends `layers.aem`; it does not modify `layers.jsonl` or
`manifest.json`.

## Roll back without losing either generation

```bash
mv .aethermind .aethermind.from-aem-v0.2
mv .aethermind.pre-aem-v0.2 .aethermind
```

The older application then sees the original store exactly as it existed before
the update. Retain `.aethermind.from-aem-v0.2` so every AEM record created after
the update remains available for review and carry-forward.
