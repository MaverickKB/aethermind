"""Release-honesty gate contract (OSS ladder).

ci-local proves only source-contract health (Tier 1). It must claim exactly that tier,
disclaim the stronger tarball/clean-VM/release rungs, and pass the private-marker gate.
No false green.
"""

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def run_script(name, env=None):
    full_env = dict(os.environ)
    if env:
        full_env.update(env)
    return subprocess.run(
        ["bash", str(SCRIPTS / name)],
        capture_output=True, text=True, env=full_env, cwd=str(ROOT),
    )


def test_ci_local_script_exists():
    assert (SCRIPTS / "ci-local.sh").exists()
    assert (SCRIPTS / "verify_no_legacy_refs.py").exists()


def test_ci_local_proves_source_contract_only():
    result = run_script("ci-local.sh", env={"AETHERMIND_PRO_CI_MODE": "selfcheck"})
    assert result.returncode == 0, result.stderr
    assert "tier_1_source_contract" in result.stdout
    assert "PASS" in result.stdout
    # ci-local must explicitly disclaim stronger readiness (no false green).
    assert "not_shippable" in result.stdout
    assert "not_public_proof" in result.stdout
    assert "not tarball/clean-VM/release proof" in result.stdout


def test_ci_local_does_not_claim_stronger_tiers():
    result = run_script("ci-local.sh", env={"AETHERMIND_PRO_CI_MODE": "selfcheck"})
    combined = result.stdout + result.stderr
    for stronger in ("tier_2_dist_tarball", "tier_3_clean_vm_smoke", "tier_4_tagged_release"):
        assert stronger not in combined


def test_private_marker_gate_passes_on_clean_tree():
    result = subprocess.run(
        ["python3", str(SCRIPTS / "verify_no_legacy_refs.py"), "--root", str(ROOT)],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    assert result.returncode == 0, result.stdout
