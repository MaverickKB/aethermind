"""Public AetherMind harness plugin dependency handling.

Derived from docs/SUBSTRATE_OWNERSHIP.md lines 17-23,
docs/AETHERMIND_PRIMITIVE_MCP.md, and docs/LOCAL_COORDINATOR_ARCHITECTURE.md.

The public plugin is a harness dependency/input, never Pro's implementation base.
Pro detects a compatible installed plugin, repairs/upgrades only with explicit
approval, and may fetch/install from the public GitHub release path when needed and
missing. Pro host-local state stays separate from plugin-owned harness files.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

from . import evidence, responses

PUBLIC_PLUGIN_SOURCE = "https://github.com/MaverickKB/aethermind-hermes-plugin"
PUBLIC_PLUGIN_REPO = "MaverickKB/aethermind-hermes-plugin"
COMPATIBILITY_RANGE = ">=0.1.0,<0.2.0"
PLUGIN_NAME = "aethermind"
HERMES_INSTALL_COMMAND = f"hermes plugins install {PUBLIC_PLUGIN_REPO} --enable"


def _home() -> Path:
    return Path(os.environ.get("HOME", str(Path.home())))


def _version_tuple(version: str) -> Optional[tuple]:
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)", version or "")
    return tuple(int(part) for part in match.groups()) if match else None


def _compatible(version: str) -> bool:
    parsed = _version_tuple(version)
    return parsed is not None and (0, 1, 0) <= parsed < (0, 2, 0)


def probe_installed(*, home: "str | Path | None" = None) -> Optional[Dict[str, Any]]:
    """Read the installed Hermes plugin manifest from the documented plugin dir."""
    root = Path(home) if home else _home()
    manifest = root / ".hermes" / "plugins" / PLUGIN_NAME / "plugin.yaml"
    if not manifest.is_file():
        return None
    version = "unknown"
    for line in manifest.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^version:\s*[\"']?(\S+?)[\"']?\s*$", line.strip())
        if match:
            version = match.group(1)
            break
    return {"version": version, "compatible": _compatible(version),
            "path": str(manifest.parent)}


def install_via_hermes_cli(*, timeout: int = 300) -> Dict[str, Any]:
    """Install the published plugin through Hermes's own plugin manager."""
    if not shutil.which("hermes"):
        return {"ok": False, "reason": "hermes_cli_missing"}
    try:
        result = subprocess.run(
            ["hermes", "plugins", "install", PUBLIC_PLUGIN_REPO, "--enable"],
            text=True, capture_output=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "reason": "install_timeout"}
    if result.returncode != 0:
        return {"ok": False, "reason": "install_failed",
                "detail": (result.stderr or result.stdout).strip()[-400:]}
    return {"ok": True}


def remove_via_hermes_cli(*, timeout: int = 120) -> Dict[str, Any]:
    if not shutil.which("hermes"):
        return {"ok": False, "reason": "hermes_cli_missing"}
    try:
        result = subprocess.run(["hermes", "plugins", "remove", PLUGIN_NAME],
                                text=True, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"ok": False, "reason": "remove_timeout"}
    if result.returncode != 0:
        return {"ok": False, "reason": "remove_failed",
                "detail": (result.stderr or result.stdout).strip()[-400:]}
    return {"ok": True}


def _evidence_block() -> Dict[str, Any]:
    return {
        "proof_surface": "source_tree",
        "tier_eligible": [evidence.TIER_SOURCE_CONTRACT],
        "blockers": list(evidence.STANDARD_BLOCKERS),
    }


def detect(*, installed: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Report public-plugin presence.

    ``installed`` (when supplied) describes a detected plugin:
    ``{"version": str, "compatible": bool, "path": str}``. With no detection signal,
    the plugin is honestly reported absent. Pro state is always separate from the
    plugin's harness files.
    """
    if installed is None:
        plugin = {
            "present": False,
            "state": "absent",
            "version": None,
            "compatible": None,
        }
    else:
        compatible = bool(installed.get("compatible"))
        plugin = {
            "present": True,
            "state": "compatible" if compatible else "incompatible",
            "version": installed.get("version", "unknown"),
            "compatible": compatible,
        }
    return responses.ok(
        "plugins detect",
        plugin=plugin,
        source=PUBLIC_PLUGIN_SOURCE,
        compatibility_range=COMPATIBILITY_RANGE,
        vendored_as_pro_source=False,
        pro_state_separate_from_plugin=True,
        evidence=_evidence_block(),
    )


def install(*, approve: bool = False, network_available: bool = False,
            installed: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Plan/perform a plugin install. Fetch is allowed only when needed and missing."""
    detection = detect(installed=installed)["plugin"]
    if detection["present"] and detection["state"] == "compatible":
        return responses.ok("plugins install", action="use_existing_compatible",
                            plugin=detection, evidence=_evidence_block())
    if not approve:
        return responses.ok("plugins install", action="needs_approval",
                            requires_user_approval=True, source=PUBLIC_PLUGIN_SOURCE,
                            next_action="re-run with explicit approval to fetch/install",
                            evidence=_evidence_block())
    if not network_available:
        return responses.ok("plugins install", action="degraded_network_unavailable",
                            network_required=True, source=PUBLIC_PLUGIN_SOURCE,
                            next_action="enable network access to fetch the public plugin",
                            evidence=_evidence_block())
    # Network fetch implementation is deferred (docs build-blocker decisions): report honestly.
    return responses.ok("plugins install", action="fetch_deferred",
                        source=PUBLIC_PLUGIN_SOURCE,
                        next_action="public plugin fetch implementation is deferred to a later gate",
                        evidence=_evidence_block())


def repair(*, approve: bool = False, installed: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Repair/upgrade an incompatible plugin, only with explicit approval."""
    detection = detect(installed=installed)["plugin"]
    if not detection["present"]:
        return responses.ok("plugins repair", action="nothing_to_repair",
                            plugin=detection, evidence=_evidence_block())
    if not approve:
        return responses.ok("plugins repair", action="needs_approval",
                            requires_user_approval=True,
                            next_action="re-run with explicit approval to repair/upgrade",
                            evidence=_evidence_block())
    return responses.ok("plugins repair", action="repair_deferred",
                        next_action="plugin repair implementation is deferred to a later gate",
                        evidence=_evidence_block())
