# Release checklist

The OSS release-honesty ladder. Each rung must actually be proven before it is
claimed — no false green (`src/aethermind_pro/evidence.py`). Rungs above Tier 1 are
built in Phase 4 (`build_oss_distribution.py` / `verify_oss_distribution.py`).

## Tier 1 — source contract (proven now)

- [ ] `./scripts/ci-local.sh` passes (compiles, private-marker sweep clean, full pytest).
- [ ] Private-marker gate clean: `python3 scripts/verify_no_legacy_refs.py --root .`
      reports `private_literals: clean`.
- [ ] No operator paths, private hosts, or mesh identifiers outside `docs/plans/`.
- [ ] Git status clean before tagging.

## Scope gate

- [ ] Product surface matches `docs/PRODUCT_DEFINITION.md`.
- [ ] No side projects (home automation, kiosk, companion, embedded) or operator-specific
      identity in the tree.
- [ ] No private continuity store shipped (`.aethermind/` is gitignored; ship fixtures
      under `tests/` only).
- [ ] No commercial-enforcement remnants (activation, license gates, call-home,
      obfuscation build).

## Tier 2 — distribution tarball (Phase 4)

- [ ] A built sdist/wheel/tarball reproduces deterministically.
- [ ] SHA-256 manifest generated for the artifact.
- [ ] The artifact's own checks pass off the built tarball, not the source tree.

## Tier 3 — clean-VM smoke (Phase 4)

- [ ] The distribution installs and runs on a clean machine (no preinstalled/operator state).
- [ ] `doctor` / `first-run` / `status` succeed natively, observed end to end.

## Tier 4 — tagged release (Phase 4)

- [ ] Tagged release with the published checksum manifest.
- [ ] `LICENSE` present (BUSL-1.1, after legal review) — see `NOTICE`.
- [ ] Cross-links to `aethermind-primitive` and `aethermind-hermes-plugin` current.
- [ ] Remaining blockers documented honestly.
