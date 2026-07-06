# AetherMind Pro Privacy and Audit

AetherMind Pro reads customer-selected root metadata, continuity-store presence, layer counts, manifest presence, repo status, and component health. It does not upload data by default.

Audit records include timestamps, event names, verdict status, and hashes of root paths. They do not include raw project content, secrets, private operator paths, or arbitrary file contents.

Support bundles include redacted audit tails, root hashes, map summaries, pressure codes, and component health for customer-controlled support.

User data controls are a product surface, not only a support surface. Users should be able to inspect settings, roots, grouped layers, and local Pro state through CLI/service commands. A later optional web/admin UI should provide the same controls for users who prefer visual administration. Through Ember/Atlas, users should be able to view layers by repo root or directory group and mark individual lines or layers as hidden, archived, quarantined, or stale when they decide a layer is outdated, harmful to performance, or poisoned knowledge. Legacy hard labels such as superseded, ignored, or deleted are not preferred customer terms.

Trust review is explicit. Ember-managed trust gates for anything not in the trusted registry, including downloaded, externally created, or public-untrusted code and continuity, must run outside active work sessions before the material is trusted. The scan looks for dangerous content such as prompt injections. Headless/CLI review must be sufficient for service function and must produce at least a verdict, pressure codes, evidence labels, redacted source/path summary, dangerous-content finding categories, and audit event ID. Review outcomes classify material as safe, questionable, or dangerous: questionable requires human approval, and dangerous is immediately reported to a human. The web/admin UI should make the review visual, verbose, and clear after the CLI path is locked. Audit records should capture trust decisions without storing raw project content.
