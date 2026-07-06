# Contributing to AetherMind

Thanks for looking. A few things make this repo easy to work in.

## Status and license

AetherMind is **pre-release and source-available**. The LICENSE file lands after legal
review (planned BUSL-1.1 with a 3-year Apache-2.0 change date — see [`NOTICE`](NOTICE)).
Until then the code is readable but not redistributable. By contributing you agree your
contribution may be released under that pending license.

## Public surfaces vs. internal history

Two kinds of content live here, and they are treated differently:

- **Public surfaces** — everything under `src/`, `tests/`, `scripts/`, top-level docs
  under `docs/`, and the root `README.md` / `CONTRIBUTING.md` / `SECURITY.md`. These
  must stay clean of any private markers (see below) and describe the product honestly.
- **Internal planning history** — `docs/plans/` (private archive, not published). These are the dated
  planning and council records kept **for continuity, not as end-user documentation**.
  They may reference superseded designs (including the commercial apparatus removed in
  Phase 0) and are deliberately exempt from the private-marker sweep. Do not "fix" the
  history to match the present; it is a record.

## Running the tests

The project has **no third-party runtime dependencies**; tests use `pytest`.

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[test]"
PYTHONPATH=src pytest -q
```

Or run the full source-contract gate, which also runs the private-marker sweep:

```bash
./scripts/ci-local.sh
```

Expected tail: `ci-local: PASS (source contract only; not tarball/clean-VM/release proof)`.

## The private-marker gate

`scripts/verify_no_legacy_refs.py` is the **permanent regression gate** for the public
repo. It fails if any operator path, private host, or mesh identifier leaks into a
scanned surface (`src/`, `tests/`, `scripts/`, and public docs — internal planning history is
excluded). `tests/test_private_markers.py` asserts both that the tree is clean and that
the gate actually catches a planted marker.

If you discover a new private marker, add it to `PRIVATE_LITERALS` in the gate (using
the fragment-concatenation form so the gate never matches its own source) and to
`SENTINEL_MARKERS` in the sentinel test. Never commit a real private path — hash it, or
use a synthetic value under `tests/`.

## Style and scope

- **Minimum viable, surgical changes.** No speculative features; don't "improve" code
  the change doesn't touch.
- **No false green.** Evidence labels (`src/aethermind_pro/evidence.py`) block claiming
  a release rung you have not actually proven. Keep that discipline.
- **JSON first.** CLI output is JSON by default; `--human` is opt-in. No command may
  require a UI, tracker, or HUD to function.
- **Signing is optional.** Layer provenance is optional infrastructure and must never
  become a write barrier.

## Related repositories

- [`aethermind-primitive`](https://github.com/MaverickKB) — the canonical `.aem` format and spec.
- [`aethermind-hermes-plugin`](https://github.com/MaverickKB/aethermind-hermes-plugin) — the reference harness adapter.
