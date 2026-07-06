# AetherMind Pro Implementation Classification

Status: docs-authority/source-classification artifact. The initial pass (below) classified every pre-existing file as untrusted. The build executed 2026-06-08 under explicit owner authorization resolved every entry — see **Final resolution (2026-06-08 build)**. No file received `keep_exact_match`; the entire package, test suite, scripts, and schemas were rebuilt from docs authority.

Scope: classifies existing source, tests, scripts, and schemas as untrusted implementation material pending docs-authority review. Existing behavior is not authority.

## Classification rules

- `suspect_source`: existing source cannot be trusted. Delete/rewrite unless it receives `keep_exact_match` classification with line-by-line citations to controlling docs.
- `suspect_test`: existing tests cannot define product truth. Rewrite from docs or keep only with citations proving the test derives from docs.
- `suspect_contract_schema`: schema may be retained only after matching current docs-derived contract.
- `quarantined_suspect_script`: scripts are not executable authority. Build/gate/CI/update scripts remain blocked until later approved work.
- `keep_exact_match`: not assigned in this initial pass. Requires line-by-line docs citations and review.
- `delete_rewrite`: later implementation default for any file that lacks `keep_exact_match`.
- `generated_untrusted_artifact`: generated caches or byproducts are never authority, are not product inputs, and must not be packaged or cited as proof.

## Global decision

No existing implementation file is currently trusted. This classification satisfies the requirement to perform source/test/script/schema classification against docs authority, but it does not approve reuse of any file.

Generated artifacts such as `__pycache__/` and `*.pyc` files are not listed as implementation candidates because they are not source, tests, scripts, or schemas. They are classified globally as `generated_untrusted_artifact`: delete/ignore only, never ship, never use as proof, and never treat as docs authority.

## File classification table

| File | Kind | Classification | Allowed fate |
| --- | --- | --- | --- |
| `schemas/agent_comms_brief.schema.json` | Schemas | suspect_contract_schema | review against docs/harness/evidence contracts before reuse |
| `schemas/agent_comms_capsule.schema.json` | Schemas | suspect_contract_schema | review against docs/harness/evidence contracts before reuse |
| `scripts/build_pro_artifact.py` | Python scripts | quarantined_suspect_script | do not modify or use as authority; later delete/rewrite or keep_exact_match after docs review |
| `scripts/ci-local.sh` | Shell scripts | quarantined_suspect_script | do not modify or use as authority; later delete/rewrite or keep_exact_match after docs review |
| `scripts/cold_extract_acceptance.py` | Python scripts | quarantined_suspect_script | do not modify or use as authority; later delete/rewrite or keep_exact_match after docs review |
| `scripts/cross-os-gate.sh` | Shell scripts | quarantined_suspect_script | do not modify or use as authority; later delete/rewrite or keep_exact_match after docs review |
| `scripts/internal-clean-install-gate.sh` | Shell scripts | quarantined_suspect_script | do not modify or use as authority; later delete/rewrite or keep_exact_match after docs review |
| `scripts/internal-rc-gate.sh` | Shell scripts | quarantined_suspect_script | do not modify or use as authority; later delete/rewrite or keep_exact_match after docs review |
| `scripts/private-beta-gate.sh` | Shell scripts | quarantined_suspect_script | do not modify or use as authority; later delete/rewrite or keep_exact_match after docs review |
| `scripts/public-self-serve-gate.sh` | Shell scripts | quarantined_suspect_script | do not modify or use as authority; later delete/rewrite or keep_exact_match after docs review |
| `scripts/validate_release_surface.py` | Python scripts | quarantined_suspect_script | do not modify or use as authority; later delete/rewrite or keep_exact_match after docs review |
| `scripts/verify_artifact_digest_binding.py` | Python scripts | quarantined_suspect_script | do not modify or use as authority; later delete/rewrite or keep_exact_match after docs review |
| `scripts/vm-clean-customer-gate.sh` | Shell scripts | quarantined_suspect_script | do not modify or use as authority; later delete/rewrite or keep_exact_match after docs review |
| `src/aethermind_pro/__init__.py` | Source Python | suspect_source | delete/rewrite unless keep_exact_match with line-by-line doc citations |
| `src/aethermind_pro/account_activation.py` | Source Python | suspect_source | delete/rewrite unless keep_exact_match with line-by-line doc citations |
| `src/aethermind_pro/activation.py` | Source Python | suspect_source | delete/rewrite unless keep_exact_match with line-by-line doc citations |
| `src/aethermind_pro/agent_comms.py` | Source Python | suspect_source | delete/rewrite unless keep_exact_match with line-by-line doc citations |
| `src/aethermind_pro/atlas_bridge.py` | Source Python | suspect_source | high-risk boundary bridge; delete/rewrite unless proven portable and private-state-free |
| `src/aethermind_pro/audit.py` | Source Python | suspect_source | delete/rewrite unless keep_exact_match with line-by-line doc citations |
| `src/aethermind_pro/cli.py` | Source Python | suspect_source | delete/rewrite unless keep_exact_match with line-by-line doc citations |
| `src/aethermind_pro/cortex.py` | Source Python | suspect_source | delete/rewrite unless keep_exact_match with line-by-line doc citations |
| `src/aethermind_pro/ember_bridge.py` | Source Python | suspect_source | high-risk boundary bridge; delete/rewrite unless proven portable and private-state-free |
| `src/aethermind_pro/entitlement.py` | Source Python | suspect_source | delete/rewrite unless keep_exact_match with line-by-line doc citations |
| `src/aethermind_pro/evidence.py` | Source Python | suspect_source | delete/rewrite unless keep_exact_match with line-by-line doc citations |
| `src/aethermind_pro/export.py` | Source Python | suspect_source | delete/rewrite unless keep_exact_match with line-by-line doc citations |
| `src/aethermind_pro/license.py` | Source Python | suspect_source | delete/rewrite unless keep_exact_match with line-by-line doc citations |
| `src/aethermind_pro/machine_map.py` | Source Python | suspect_source | delete/rewrite unless keep_exact_match with line-by-line doc citations |
| `src/aethermind_pro/primitive_mcp.py` | Source Python | suspect_source | delete/rewrite unless keep_exact_match with line-by-line doc citations |
| `src/aethermind_pro/release_evidence.py` | Source Python | suspect_source | delete/rewrite unless keep_exact_match with line-by-line doc citations |
| `src/aethermind_pro/roots.py` | Source Python | suspect_source | delete/rewrite unless keep_exact_match with line-by-line doc citations |
| `src/aethermind_pro/state.py` | Source Python | suspect_source | delete/rewrite unless keep_exact_match with line-by-line doc citations |
| `src/aethermind_pro/substrate_bootstrap.py` | Source Python | suspect_source | delete/rewrite unless keep_exact_match with line-by-line doc citations |
| `src/aethermind_pro/support.py` | Source Python | suspect_source | delete/rewrite unless keep_exact_match with line-by-line doc citations |
| `tests/conftest.py` | Tests | suspect_test | rewrite from docs or keep_exact_match with doc citations; never treat passing legacy test as authority |
| `tests/test_agent_comms.py` | Tests | suspect_test | rewrite from docs or keep_exact_match with doc citations; never treat passing legacy test as authority |
| `tests/test_build_artifact_platform.py` | Tests | suspect_test | rewrite from docs or keep_exact_match with doc citations; never treat passing legacy test as authority |
| `tests/test_cli_new_surfaces.py` | Tests | suspect_test | rewrite from docs or keep_exact_match with doc citations; never treat passing legacy test as authority |
| `tests/test_cold_extract_acceptance.py` | Tests | suspect_test | rewrite from docs or keep_exact_match with doc citations; never treat passing legacy test as authority |
| `tests/test_cortex_verdicts.py` | Tests | suspect_test | rewrite from docs or keep_exact_match with doc citations; never treat passing legacy test as authority |
| `tests/test_cross_os_gate.py` | Tests | suspect_test | rewrite from docs or keep_exact_match with doc citations; never treat passing legacy test as authority |
| `tests/test_customer_install_artifact.py` | Tests | suspect_test | rewrite from docs or keep_exact_match with doc citations; never treat passing legacy test as authority |
| `tests/test_customer_journey_docs.py` | Tests | suspect_test | rewrite from docs or keep_exact_match with doc citations; never treat passing legacy test as authority |
| `tests/test_entitlement_adversarial.py` | Tests | suspect_test | rewrite from docs or keep_exact_match with doc citations; never treat passing legacy test as authority |
| `tests/test_evidence_taxonomy.py` | Tests | suspect_test | rewrite from docs or keep_exact_match with doc citations; never treat passing legacy test as authority |
| `tests/test_first_run_cli.py` | Tests | suspect_test | rewrite from docs or keep_exact_match with doc citations; never treat passing legacy test as authority |
| `tests/test_license_envelope.py` | Tests | suspect_test | rewrite from docs or keep_exact_match with doc citations; never treat passing legacy test as authority |
| `tests/test_machine_map.py` | Tests | suspect_test | rewrite from docs or keep_exact_match with doc citations; never treat passing legacy test as authority |
| `tests/test_platform_docs.py` | Tests | suspect_test | rewrite from docs or keep_exact_match with doc citations; never treat passing legacy test as authority |
| `tests/test_primitive_mcp.py` | Tests | suspect_test | rewrite from docs or keep_exact_match with doc citations; never treat passing legacy test as authority |
| `tests/test_product_contract_docs.py` | Tests | suspect_test | rewrite from docs or keep_exact_match with doc citations; never treat passing legacy test as authority |
| `tests/test_release_evidence.py` | Tests | suspect_test | rewrite from docs or keep_exact_match with doc citations; never treat passing legacy test as authority |
| `tests/test_release_evidence_taxonomy.py` | Tests | suspect_test | rewrite from docs or keep_exact_match with doc citations; never treat passing legacy test as authority |
| `tests/test_release_mode.py` | Tests | suspect_test | rewrite from docs or keep_exact_match with doc citations; never treat passing legacy test as authority |
| `tests/test_roots_state.py` | Tests | suspect_test | rewrite from docs or keep_exact_match with doc citations; never treat passing legacy test as authority |
| `tests/test_self_serve_gate.py` | Tests | suspect_test | rewrite from docs or keep_exact_match with doc citations; never treat passing legacy test as authority |
| `tests/test_substrate_bootstrap.py` | Tests | suspect_test | rewrite from docs or keep_exact_match with doc citations; never treat passing legacy test as authority |
| `tests/test_support_recovery.py` | Tests | suspect_test | rewrite from docs or keep_exact_match with doc citations; never treat passing legacy test as authority |

## High-risk patterns requiring delete/rewrite

Any file is rejected for reuse if it:

- hard-codes private operator paths, hosts, profiles, or private Cairn topology;
- treats Pro as Hermes-only, Codex-only, MCP-only, plugin-only, or a single-repo reporter;
- treats source-tree tests as protected-artifact, private-beta, invite-beta, public, or customer proof;
- vendors the public plugin as Pro implementation base;
- requires UI/HUD for core service behavior;
- trusts unregistered external/downloaded/public material by default;
- stores raw project content, secrets, arbitrary snippets, or private paths in audit/support artifacts;
- blocks export because license state is inactive, expired, or tampered;
- removes `.aem`/continuity artifacts by default during uninstall;
- creates separate platform-specific source trees.

## Next classification step before implementation

Before code work, a reviewer must convert each file to one of:

- `delete_rewrite`;
- `delete_obsolete`;
- `defer_surface`;
- `keep_exact_match` with line-by-line citations.

Until that happens, source implementation remains blocked. Generated caches and byproducts remain delete/ignore only and do not need `keep_exact_match` review.

## Final resolution (2026-06-08 build)

This step was executed. Every initial-pass entry was resolved. `keep_exact_match` was assigned to zero files — no legacy file survived as authority. The build remains Tier 1 source-contract only (see `docs/HUMAN_VISIBLE_PROOF_LADDER.md`); it does not approve protected-artifact, beta, customer, RC, or public claims.

### Deleted as obsolete (`delete_obsolete`) — removed, no same-name successor

These files encoded surfaces that the settled docs collapsed into other modules or removed entirely (release/RC/cold-extract laundering, boundary bridges, split activation/entitlement, separate machine map / substrate bootstrap):

| Removed file | Reason | Behavior absorbed by |
| --- | --- | --- |
| `pro_release_manifest.json` | deletion trigger: false-green protected-artifact claims + hard-coded private `/Users` paths | n/a (no release manifest in source-contract phase) |
| `scripts/cold_extract_acceptance.py` | artifact/clean-extract proof is deferred, not a source script | `scripts/internal-clean-install-gate.sh` (blocks honestly) |
| `scripts/internal-rc-gate.sh` | RC claims are not source-contract proof | gate scripts that block stronger tiers |
| `scripts/validate_release_surface.py` | release-surface validation is deferred | `scripts/verify_no_legacy_refs.py` + `scripts/ci-local.sh` |
| `scripts/verify_artifact_digest_binding.py` | artifact digest binding is deferred | `scripts/build_pro_artifact.py` (blocks) |
| `scripts/vm-clean-customer-gate.sh` | visual VM proof is deferred | `scripts/private-beta-gate.sh` (blocks) |
| `src/aethermind_pro/account_activation.py` | split activation surface | `activation.py` + `license.py` |
| `src/aethermind_pro/agent_comms.py` | renamed to harness-neutral term | `comms.py` |
| `src/aethermind_pro/atlas_bridge.py` | high-risk private-topology bridge | `atlas.py` (portable, hashed ids) |
| `src/aethermind_pro/ember_bridge.py` | high-risk private-topology bridge | `cortex.py` (host-local semantics) |
| `src/aethermind_pro/entitlement.py` | split entitlement surface | `license.py` |
| `src/aethermind_pro/machine_map.py` | renamed Atlas map | `atlas.py` |
| `src/aethermind_pro/release_evidence.py` | release evidence is deferred | `evidence.py` (Tier 1 taxonomy) |
| `src/aethermind_pro/substrate_bootstrap.py` | folded into substrate selection | `substrate.py` + `primitive_mcp.py` |
| `tests/test_*` (all legacy test files) | legacy tests never define product truth | rewritten docs-derived `tests/test_*_contract.py` suite |

### Deleted and rewritten from docs (`delete_rewrite`) — same name, fresh implementation

`schemas/agent_comms_brief.schema.json`, `schemas/agent_comms_capsule.schema.json`, `scripts/build_pro_artifact.py`, `scripts/ci-local.sh`, `scripts/cross-os-gate.sh`, `scripts/internal-clean-install-gate.sh`, `scripts/private-beta-gate.sh`, `scripts/public-self-serve-gate.sh`, `src/aethermind_pro/__init__.py`, `activation.py`, `audit.py`, `cli.py`, `cortex.py`, `evidence.py`, `export.py`, `license.py`, `primitive_mcp.py`, `roots.py`, `state.py`, `support.py`, `tests/conftest.py`.

### New modules created from docs authority (no prior file)

`atlas.py`, `comms.py`, `config.py`, `coordinator.py`, `harnesses.py`, `investigate.py`, `layers.py`, `platform.py`, `plugins.py`, `product_ux.py`, `responses.py`, `services.py`, `settings.py`, `smoke.py`, `substrate.py`, `trust.py`, `workspace.py`, `scripts/verify_no_legacy_refs.py`, `scripts/build_private_beta_candidate.py`, `scripts/run_private_beta_candidate_vm_proof.py`, `scripts/assemble_private_beta_candidate_evidence.py`, `scripts/private-beta-candidate-gate.sh`, and the docs-derived test suite (`tests/test_*_contract.py`, `tests/test_private_beta_candidate_product_ux.py`, `tests/test_private_beta_candidate_installer.py`, `tests/test_private_beta_candidate_vm_proof.py`, `tests/test_private_beta_candidate_evidence_gate.py`) covering `cli`, `evidence`, `substrate`, `investigate`, `state_audit_export`, `activation_license`, `atlas_cortex`, `trust`, `harness_comms`, `plugin_boundary`, `services_status_support`, `layers`, `deferred_beta_surfaces`, `gate_scripts`, private-beta-candidate product UX, private-beta-candidate installer packaging, private-beta-candidate VM install proof planning, and private-beta-candidate evidence gating.

### Verification of resolution

- `PYTHONPATH=src python3 -m pytest` → 99 passed.
- `python3 -m compileall -q src scripts` → clean.
- `python3 scripts/verify_no_legacy_refs.py --root .` → exit 0 (no prohibited private/operator references).
- `bash scripts/ci-local.sh` → PASS, evidence_tier `tier_1_source_contract`, with explicit `not_protected_artifact … not_public_proof` disclaimers.
