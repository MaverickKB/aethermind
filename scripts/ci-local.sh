#!/usr/bin/env bash
# Source-contract health gate (Tier 1 of the OSS release-honesty ladder).
#
# ci-local proves ONLY that the source tree compiles, carries no private markers, and
# passes its tests. It is the first rung; it must never claim the built-tarball,
# clean-VM, or tagged-release rungs (those are Phase 4 machinery). No false green.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "AetherMind ci-local: source-contract health only (Tier 1)"

python3 -m compileall -q src scripts

# Private-marker gate: fail if any operator literal or private host/path leaks into
# source/test/script/schema files. This is the permanent regression gate for the
# public repo (see CONTRIBUTING.md).
python3 scripts/verify_no_legacy_refs.py --root .

# selfcheck mode skips pytest so this gate can be exercised from within the test suite
# without recursing into itself.
if [ "${AETHERMIND_PRO_CI_MODE:-full}" != "selfcheck" ]; then
  if python3 -c 'import pytest' >/dev/null 2>&1; then
    PYTHONPATH=src python3 -m pytest -q
  elif command -v uv >/dev/null 2>&1; then
    PYTHONPATH=src uv run --no-project --with pytest python -m pytest -q
  else
    echo "ci-local: pytest unavailable and uv not found; install test extra or run with uv" >&2
    exit 1
  fi
fi

echo "evidence_tier: tier_1_source_contract"
echo "blocks: not_dist_tarball not_clean_vm_smoke not_tagged_release not_shippable not_public_proof"
echo "ci-local: PASS (source contract only; not tarball/clean-VM/release proof)"
