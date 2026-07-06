"""Primitive write/read smoke path.

Derived from docs/PRO_SYSTEM_CONTRACT.md line 42 (`smoke`) and
docs/plans/install-from-any-state-bootstrap-source-contract-spec.md lines 171-183.

`smoke` exercises the OSS primitive write/read path. It carries source-contract-only
evidence and is never protected-artifact, clean-machine, customer, beta, or public proof.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from . import evidence, primitive_mcp, responses


def _evidence_block() -> Dict[str, Any]:
    return {
        "proof_surface": "source_tree",
        "observation_mode": "cli_only",
        "tier_eligible": [evidence.TIER_SOURCE_CONTRACT],
        "blockers": list(evidence.STANDARD_BLOCKERS),
    }


def smoke(project_root: Optional[str] = None, **_ignored) -> Dict[str, Any]:
    """Run a bounded primitive write/read roundtrip.

    With no project root, a throwaway temp directory is used so no customer root is
    polluted by the smoke check.
    """
    steps = []
    if project_root:
        target = Path(project_root).expanduser().resolve()
        if not target.is_dir():
            return responses.error("smoke", "root_not_found",
                                   "the selected project root does not exist",
                                   "provide an existing directory or omit --project-root")
        return _run(target, steps, cleanup=False)

    tmp = Path(tempfile.mkdtemp(prefix="aethermind-pro-smoke-"))
    try:
        return _run(tmp, steps, cleanup=True)
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


def _run(target: Path, steps, cleanup: bool) -> Dict[str, Any]:
    init_result = primitive_mcp.call("init_store", {"data_root": str(target)})
    steps.append({"step": "init_store", "ok": init_result.get("ok", False)})
    if not init_result.get("ok"):
        return _fail(steps, init_result)

    write_result = primitive_mcp.call(
        "write_layer",
        {"data_root": str(target), "layer": {"kind": "smoke", "source": "aethermind_pro_smoke"}},
    )
    steps.append({"step": "write_layer", "ok": write_result.get("ok", False)})
    if not write_result.get("ok"):
        return _fail(steps, write_result)

    read_result = primitive_mcp.call("read_layers", {"data_root": str(target)})
    roundtrip = bool(read_result.get("ok") and any(
        layer.get("layer_id") == write_result.get("layer_id")
        for layer in read_result.get("layers", [])
    ))
    steps.append({"step": "read_layers", "ok": read_result.get("ok", False), "roundtrip": roundtrip})

    return responses.ok(
        "smoke",
        primitive_write_read_passed=roundtrip,
        used_temp_dir=cleanup,
        steps=steps,
        evidence=_evidence_block(),
    )


def _fail(steps, result: Dict[str, Any]) -> Dict[str, Any]:
    err = result.get("error", {})
    return responses.error("smoke", err.get("code", "internal_error"),
                           err.get("message", "primitive smoke failed"),
                           "inspect the primitive substrate and retry")
