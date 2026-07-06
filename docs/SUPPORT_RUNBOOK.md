# AetherMind Pro Support Runbook

Collect support-safe evidence only.

1. Run `status --json` for component and distribution health.
2. Run `map --json` to refresh the Atlas machine map.
3. Run `coordinate --json` to collect CORTEX pressure and verdicts.
4. Run `audit tail --json` to inspect bounded audit events.
5. Run `support-bundle --output support.json --json` to collect redacted diagnostics.
6. Run `export --output export.json --json` if customer-owned state must be recovered.

Support bundles include hashes and summaries, not project contents or private operator paths.
