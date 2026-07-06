"""Built-in and custom harness configuration, discovery, and conformance checks.

Derived from docs/HARNESS_CONFORMANCE_CONTRACT.md,
docs/plans/harness-neutral-source-contract-spec.md (config model), and
docs/plans/harness-discovery-bootstrap-source-contract-spec.md (depth tiers, discovery,
check output).

All first-class harnesses are in scope. No harness is privileged. BYO custom harnesses
are data-driven and require no source change. Everything degrades honestly.
"""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from . import evidence, responses
from .state import ProState

FIRST_CLASS = ("hermes", "grok_build", "codex", "claude_code", "cursor")
ALL_KINDS = ("hermes", "grok_build", "codex", "claude_code", "cursor", "custom", "future")

# Harness discovery blocks always carry the all-harness blocker too.
DISCOVERY_BLOCKERS = ["not_all_harnesses_proven"] + list(evidence.STANDARD_BLOCKERS)

# Bounded, non-private executable hints used only for best-effort local detection.
_DETECTION_HINTS = {
    "hermes": ["hermes"],
    "grok_build": ["grok-build", "grok"],
    "codex": ["codex"],
    "claude_code": ["claude", "claude-code"],
    "cursor": ["cursor", "cursor-agent"],
}

# Bounded user-config-directory hints: documented harness config surfaces only,
# never private session internals.
_CONFIG_SURFACE_HINTS = {
    "hermes": [".hermes"],
    "grok_build": [".grok"],
    "codex": [".codex"],
    "claude_code": [".claude"],
    "cursor": [".cursor"],
}

# Bounded future-candidate hints. This is not arbitrary PATH scraping: candidates
# remain untrusted and unsupported until the user approves/configures them.
_FUTURE_CANDIDATE_HINTS = {
    "openclaw": ["openclaw"],
}

# Pro-managed integration surfaces per first-class harness, all verified against
# the harness's own documentation or live install:
# - Claude Code: skills at ~/.claude/skills/<name>/SKILL.md.
# - Codex: skills at ~/.codex/skills/ and [mcp_servers.*] stdio entries in
#   ~/.codex/config.toml (both verified against the live local install).
# - Grok Build: skills, hooks (*.json), and [mcp_servers.*] config.toml entries,
#   all documented in the bundled user guide (08-skills, 10-hooks, 07-mcp-servers).
# - Hermes: the published plugin via Hermes's own plugin manager (handled in
#   _apply_hermes) plus a Pro handoff file.
_INTEGRATION_SURFACES = {
    "hermes": {"surface_kind": "handoff_file", "relpath": ".hermes/aethermind-pro/HANDOFF.md", "depth_tier": 2},
}

_HARNESS_SURFACES = {
    "claude_code": [
        {"surface_kind": "skill", "writer": "skill", "relpath": ".claude/skills/aethermind-pro/SKILL.md", "depth_tier": 4},
    ],
    "codex": [
        {"surface_kind": "skill", "writer": "skill", "relpath": ".codex/skills/aethermind-pro/SKILL.md", "depth_tier": 4},
        {"surface_kind": "mcp_config", "writer": "toml_mcp", "relpath": ".codex/config.toml", "depth_tier": 4},
    ],
    "grok_build": [
        {"surface_kind": "skill", "writer": "skill", "relpath": ".grok/skills/aethermind-pro/SKILL.md", "depth_tier": 4},
        {"surface_kind": "hook", "writer": "hook_file", "relpath": ".grok/hooks/aethermind-pro.json", "depth_tier": 4},
        {"surface_kind": "mcp_config", "writer": "toml_mcp", "relpath": ".grok/config.toml", "depth_tier": 4},
    ],
    # Cursor surfaces verified from the live local install: skills directory,
    # mcpServers map in mcp.json, and versioned hooks.json with camelCase events.
    "cursor": [
        {"surface_kind": "skill", "writer": "skill", "relpath": ".cursor/skills/aethermind-pro/SKILL.md", "depth_tier": 4},
        {"surface_kind": "mcp_config", "writer": "json_mcp", "relpath": ".cursor/mcp.json", "depth_tier": 4},
        {"surface_kind": "hook", "writer": "cursor_hooks", "relpath": ".cursor/hooks.json", "depth_tier": 4},
    ],
}

MCP_SERVER_NAME = "aethermind_pro"
_TOML_MARK_BEGIN = "# >>> aethermind-pro managed mcp server (do not edit) >>>"
_TOML_MARK_END = "# <<< aethermind-pro managed mcp server <<<"

INTEGRATE_HINT = "aethermind-pro harnesses bootstrap apply --name {name} --approve --json"
REMOVE_HINT = "aethermind-pro harnesses bootstrap remove --name {name} --json"


def _evidence_block() -> Dict[str, Any]:
    return {
        "proof_surface": "source_tree",
        "tier_eligible": [evidence.TIER_SOURCE_CONTRACT],
        "blockers": list(DISCOVERY_BLOCKERS),
    }


def default_config(name: str, kind: str) -> Dict[str, Any]:
    return {
        "name": name,
        "kind": kind if kind in ALL_KINDS else "custom",
        "enabled": False,
        "command": [],
        "working_directory_policy": "required_root_argument",
        "handoff_input": "manual",
        "handoff_output": "manual",
        "resume_session": {"supported": False, "definition": None},
        "check_in": {"supported": False, "interval_seconds": None, "health_expectation": None},
        "plugin": {"required": False, "name": None, "install_policy": "detect_only"},
    }


def list_harnesses(*, state_dir: "str | Path | None" = None) -> Dict[str, Any]:
    configured = ProState(state_dir).load().get("harnesses", {})
    harnesses: List[Dict[str, Any]] = []
    for kind in FIRST_CLASS:
        cfg = configured.get(kind) or default_config(kind, kind)
        harnesses.append({"name": kind, "kind": kind, "classification": "first_class_known",
                          "enabled": cfg.get("enabled", False)})
    for name, cfg in configured.items():
        if name in FIRST_CLASS:
            continue
        harnesses.append({"name": name, "kind": cfg.get("kind", "custom"),
                          "classification": "custom", "enabled": cfg.get("enabled", False)})
    return responses.ok("harnesses list", harnesses=harnesses, evidence=_evidence_block())


def configure(name: Optional[str], config: Optional[Dict[str, Any]], *,
              state_dir: "str | Path | None" = None) -> Dict[str, Any]:
    if not name:
        return responses.error("harnesses configure", "name_required",
                               "harnesses configure requires --name",
                               "aethermind-pro harnesses configure --name <name> --config <json> --json")
    config = config or {}
    kind = config.get("kind", name if name in ALL_KINDS else "custom")
    merged = default_config(name, kind)
    merged.update({k: v for k, v in config.items() if k in merged})
    merged["name"] = name

    state = ProState(state_dir)
    data = state.load()
    data.setdefault("harnesses", {})[name] = merged
    state.save(data)
    return responses.ok("harnesses configure", name=name, config=merged, evidence=_evidence_block())


def bootstrap_plan(name: Optional[str], *, state_dir: "str | Path | None" = None) -> Dict[str, Any]:
    """Return default-deny prompts for harness integration surfaces.

    Planning only: no skills, hooks, MCP/plugin config, or workspace files are
    written here. Every prompt requires explicit user approval before apply.
    """
    if not name:
        return responses.error("harnesses bootstrap plan", "name_required",
                               "harnesses bootstrap plan requires --name",
                               "aethermind-pro harnesses bootstrap plan --name codex --json")
    configured = ProState(state_dir).load().get("harnesses", {})
    cfg = configured.get(name)
    classification = _classification_for(name, cfg)
    detected = _is_detected(name, cfg)
    return responses.ok(
        "harnesses bootstrap plan",
        harness={
            "name": name,
            "classification": classification,
            "configured": bool(cfg),
            "detected": detected,
            "current_depth_tier": 2 if cfg and cfg.get("enabled") else 1,
            "target_depth_tier": 4,
        },
        prompts=_bootstrap_prompts(name, classification, detected),
        created_surfaces=[],
        evidence=_evidence_block(),
    )


def bootstrap_apply(name: Optional[str], *, approve: bool = False,
                    approval_id: Optional[str] = None,
                    state_dir: "str | Path | None" = None) -> Dict[str, Any]:
    """Write the Pro-managed integration surface for a detected harness.

    Default is deny: nothing is written without an explicit approval action.
    First-class harnesses get a skill (Claude Code, Codex) or configured handoff
    file (Hermes, Grok Build). Unknown/custom candidates require trust review
    and are never written here.
    """
    command = "harnesses bootstrap apply"
    if not name:
        return responses.error(command, "name_required",
                               "harnesses bootstrap apply requires --name",
                               INTEGRATE_HINT.format(name="claude_code"))

    if name not in _HARNESS_SURFACES and name != "hermes":
        return responses.ok(
            command,
            action="trust_review_required",
            nothing_written=True,
            harness={"name": name, "classification": _classification_for(name)},
            next_action=(f"aethermind-pro trust review --subject {name} --json, then "
                         f"aethermind-pro harnesses configure --name {name} --json"),
            manual_steps=[
                "run trust review on the candidate harness",
                "configure it as a BYO/custom harness with your own handoff surface",
            ],
            evidence=_evidence_block(),
        )

    if not approve and not approval_id:
        return responses.ok(
            command,
            action="denied_default_no_approval",
            nothing_written=True,
            harness={"name": name, "detected": _is_detected(name)},
            approval={"default": "deny", "how_to_approve": INTEGRATE_HINT.format(name=name)},
            evidence=_evidence_block(),
        )

    detected, basis = _detect(name)
    if not detected:
        return responses.error(command, "harness_missing",
                               f"{name} was not detected on this machine",
                               "install the harness, then re-run: "
                               + INTEGRATE_HINT.format(name=name))

    if name == "hermes":
        return _apply_hermes(command, basis, approval_id, state_dir)

    now = datetime.now(timezone.utc).isoformat()
    approval = approval_id or f"cli-approve-{name}"
    records: List[Dict[str, Any]] = []
    for surface in _HARNESS_SURFACES[name]:
        target = _home() / surface["relpath"]
        writer = surface.get("writer", "skill")
        shared_file = writer in ("toml_mcp", "json_mcp", "cursor_hooks")
        record = {
            "surface_id": f"surface-{name}-{surface['surface_kind']}",
            "harness": name,
            "surface_kind": surface["surface_kind"],
            "writer": writer,
            "target": str(target),
            "created_by": "aethermind_pro",
            "created_at": now,
            "approval_id": approval,
            "trust_event_id": None,
            "rollback": "restore_previous" if shared_file else "remove",
            "default_uninstall": "remove",
        }
        target.parent.mkdir(parents=True, exist_ok=True)
        if writer == "toml_mcp":
            _upsert_toml_mcp_block(target)
        elif writer == "json_mcp":
            _upsert_json_mcp(target)
        elif writer == "cursor_hooks":
            _upsert_cursor_hooks(target)
        elif writer == "hook_file":
            target.write_text(_hook_content(name), encoding="utf-8")
        else:
            target.write_text(_surface_content(name, surface, record), encoding="utf-8")
        records.append(record)

    state = ProState(state_dir)
    data = state.load()
    surfaces = [s for s in data.get("pro_managed_surfaces", [])
                if s.get("harness") != name]
    surfaces.extend(records)
    data["pro_managed_surfaces"] = surfaces
    cfg = data.setdefault("harnesses", {}).get(name) or default_config(name, name)
    cfg["enabled"] = True
    data["harnesses"][name] = cfg
    state.save(data)

    return responses.ok(
        command,
        action="integrated",
        harness={"name": name, "detected": True, "detection_basis": basis},
        created_surfaces=records,
        depth_tier_now=max(s["depth_tier"] for s in _HARNESS_SURFACES[name]),
        rollback=REMOVE_HINT.format(name=name),
        uninstall_behavior="removed_by_default",
        evidence=_evidence_block(),
    )


def _mcp_command() -> str:
    return shutil.which("aethermind-pro") or "aethermind-pro"


def _toml_mcp_block() -> str:
    return (
        f"{_TOML_MARK_BEGIN}\n"
        f"[mcp_servers.{MCP_SERVER_NAME}]\n"
        f'command = "{_mcp_command()}"\n'
        f'args = ["primitive-mcp", "serve"]\n'
        f"{_TOML_MARK_END}\n"
    )


def _strip_toml_mcp_block(content: str) -> str:
    if _TOML_MARK_BEGIN not in content:
        return content
    lines = content.splitlines(keepends=True)
    out: List[str] = []
    skipping = False
    for line in lines:
        if line.rstrip("\n") == _TOML_MARK_BEGIN:
            skipping = True
            continue
        if skipping:
            if line.rstrip("\n") == _TOML_MARK_END:
                skipping = False
            continue
        out.append(line)
    return "".join(out)


def _upsert_toml_mcp_block(config_path: Path) -> None:
    existing = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    stripped = _strip_toml_mcp_block(existing)
    if stripped and not stripped.endswith("\n"):
        stripped += "\n"
    separator = "\n" if stripped else ""
    config_path.write_text(stripped + separator + _toml_mcp_block(), encoding="utf-8")


def _remove_toml_mcp_block(config_path: Path) -> None:
    if not config_path.exists():
        return
    content = config_path.read_text(encoding="utf-8")
    stripped = _strip_toml_mcp_block(content)
    if stripped != content:
        config_path.write_text(stripped, encoding="utf-8")


def _mcp_server_entry() -> Dict[str, Any]:
    return {"command": _mcp_command(), "args": ["primitive-mcp", "serve"]}


def _load_json(path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
    if not path.exists():
        return default
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default
    return data if isinstance(data, dict) else default


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def _upsert_json_mcp(config_path: Path) -> None:
    data = _load_json(config_path, {})
    servers = data.setdefault("mcpServers", {})
    servers[MCP_SERVER_NAME] = _mcp_server_entry()
    _write_json(config_path, data)


def _remove_json_mcp(config_path: Path) -> None:
    data = _load_json(config_path, {})
    servers = data.get("mcpServers", {})
    if MCP_SERVER_NAME in servers:
        del servers[MCP_SERVER_NAME]
        _write_json(config_path, data)


# Ownership marker inside the shared cursor hooks.json: our entries are the only
# ones whose command carries this flag, so insert/remove stays entry-scoped.
_CURSOR_HOOK_MARKER = "--harness cursor"
_CURSOR_HOOK_EVENTS = ("sessionStart", "preCompact")


def _cursor_hook_command() -> str:
    return (f'{_mcp_command()} comms brief --project-root "$PWD" '
            f"{_CURSOR_HOOK_MARKER} --json 2>/dev/null || true")


def _is_cursor_hook_ours(entry: Any) -> bool:
    return isinstance(entry, dict) and _CURSOR_HOOK_MARKER in str(entry.get("command", ""))


def _upsert_cursor_hooks(hooks_path: Path) -> None:
    data = _load_json(hooks_path, {"version": 1, "hooks": {}})
    data.setdefault("version", 1)
    hooks = data.setdefault("hooks", {})
    for event in _CURSOR_HOOK_EVENTS:
        entries = [e for e in hooks.get(event, []) if not _is_cursor_hook_ours(e)]
        entries.append({"command": _cursor_hook_command(), "timeout": 15})
        hooks[event] = entries
    _write_json(hooks_path, data)


def _remove_cursor_hooks(hooks_path: Path) -> None:
    if not hooks_path.exists():
        return
    data = _load_json(hooks_path, {})
    hooks = data.get("hooks", {})
    changed = False
    for event, entries in list(hooks.items()):
        kept = [e for e in entries if not _is_cursor_hook_ours(e)]
        if len(kept) != len(entries):
            hooks[event] = kept
            changed = True
    if changed:
        _write_json(hooks_path, data)


def _hook_content(name: str) -> str:
    command = (f'{_mcp_command()} comms brief --project-root "$PWD" '
               f"--harness {name} --json 2>/dev/null || true")
    entry = {"hooks": [{"type": "command", "command": command, "timeout": 15}]}
    payload = {
        "_pro_managed": {
            "created_by": "aethermind_pro",
            "remove_with": REMOVE_HINT.format(name=name),
        },
        "hooks": {
            "SessionStart": [entry],
            "PostCompact": [entry],
        },
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _apply_hermes(command: str, basis: List[str], approval_id: Optional[str],
                  state_dir: "str | Path | None") -> Dict[str, Any]:
    """Hermes integration is the published plugin, installed through Hermes's own
    plugin manager, plus a Pro handoff file for Pro's value-added services above
    the plugin. Native depth is claimed only when a compatible plugin is present."""
    from . import plugins as plugins_mod

    degradation: List[Dict[str, str]] = []
    records: List[Dict[str, Any]] = []
    installed_by_pro = False

    installed = plugins_mod.probe_installed()
    if installed is None:
        attempt = plugins_mod.install_via_hermes_cli()
        if attempt["ok"]:
            installed = plugins_mod.probe_installed()
            installed_by_pro = installed is not None
        else:
            code = "plugin_missing" if attempt["reason"] == "hermes_cli_missing" else "plugin_install_failed"
            degradation.append({
                "code": code,
                "message": f"published plugin not installed ({attempt['reason']})",
                "next_action": plugins_mod.HERMES_INSTALL_COMMAND,
            })
    if installed is not None and not installed["compatible"]:
        degradation.append({
            "code": "plugin_incompatible",
            "message": f"installed plugin version {installed['version']} is outside {plugins_mod.COMPATIBILITY_RANGE}",
            "next_action": "aethermind-pro plugins repair --approve --json",
        })
        installed = None

    now = datetime.now(timezone.utc).isoformat()
    approval = approval_id or "cli-approve-hermes"
    if installed is not None:
        records.append({
            "surface_id": "surface-hermes-plugin",
            "harness": "hermes",
            "surface_kind": "plugin",
            "target": installed["path"],
            "plugin_version": installed["version"],
            "created_by": "aethermind_pro" if installed_by_pro else "preexisting_user_install",
            "created_at": now,
            "approval_id": approval,
            "trust_event_id": None,
            "rollback": "remove" if installed_by_pro else "manual_review_required",
            "default_uninstall": "remove" if installed_by_pro else "preserve",
        })

    surface = _INTEGRATION_SURFACES["hermes"]
    target = _home() / surface["relpath"]
    handoff_record = {
        "surface_id": "surface-hermes-handoff_file",
        "harness": "hermes",
        "surface_kind": "handoff_file",
        "target": str(target),
        "created_by": "aethermind_pro",
        "created_at": now,
        "approval_id": approval,
        "trust_event_id": None,
        "rollback": "remove",
        "default_uninstall": "remove",
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(_surface_content("hermes", surface, handoff_record), encoding="utf-8")
    records.append(handoff_record)

    state = ProState(state_dir)
    data = state.load()
    surfaces = [s for s in data.get("pro_managed_surfaces", [])
                if s.get("harness") != "hermes"]
    surfaces.extend(records)
    data["pro_managed_surfaces"] = surfaces
    cfg = data.setdefault("harnesses", {}).get("hermes") or default_config("hermes", "hermes")
    cfg["enabled"] = True
    if installed is not None:
        cfg["plugin"] = {"required": True, "name": plugins_mod.PLUGIN_NAME,
                         "install_policy": "hermes_plugin_manager"}
    data["harnesses"]["hermes"] = cfg
    state.save(data)

    return responses.ok(
        command,
        action="integrated",
        harness={"name": "hermes", "detected": True, "detection_basis": basis},
        created_surfaces=records,
        depth_tier_now=4 if installed is not None else 2,
        plugin={"present": installed is not None,
                "version": installed["version"] if installed else None,
                "source": plugins_mod.PUBLIC_PLUGIN_SOURCE},
        degradation=degradation,
        rollback=REMOVE_HINT.format(name="hermes"),
        uninstall_behavior="removed_by_default",
        evidence=_evidence_block(),
    )


def bootstrap_remove(name: Optional[str], *, remove_all: bool = False,
                     state_dir: "str | Path | None" = None) -> Dict[str, Any]:
    """Remove Pro-managed harness surfaces and their ownership records."""
    command = "harnesses bootstrap remove"
    if not name and not remove_all:
        return responses.error(command, "name_required",
                               "harnesses bootstrap remove requires --name or --all",
                               REMOVE_HINT.format(name="claude_code"))

    state = ProState(state_dir)
    data = state.load()
    keep: List[Dict[str, Any]] = []
    removed: List[Dict[str, Any]] = []
    for record in data.get("pro_managed_surfaces", []):
        if remove_all or record.get("harness") == name:
            writer = record.get("writer") or ("toml_mcp" if record.get("surface_kind") == "mcp_config" else "")
            if record.get("surface_kind") == "plugin":
                # Only a Pro-installed plugin is removed; user installs are preserved.
                if record.get("created_by") == "aethermind_pro":
                    from . import plugins as plugins_mod
                    plugins_mod.remove_via_hermes_cli()
            elif writer == "toml_mcp":
                # Strip only the Pro-managed marked block; the config file is user-owned.
                _remove_toml_mcp_block(Path(record.get("target", "")))
            elif writer == "json_mcp":
                _remove_json_mcp(Path(record.get("target", "")))
            elif writer == "cursor_hooks":
                _remove_cursor_hooks(Path(record.get("target", "")))
            else:
                target = Path(record.get("target", ""))
                if target.is_file():
                    target.unlink()
                # Rollback must not leave Pro-created droppings: the per-product
                # directory we created is removed once its last surface is gone.
                parent = target.parent
                if parent.name == "aethermind-pro" and parent.is_dir() and not any(parent.iterdir()):
                    parent.rmdir()
            removed.append(record)
            harness_cfg = data.get("harnesses", {}).get(record.get("harness"))
            if harness_cfg:
                harness_cfg["enabled"] = False
        else:
            keep.append(record)
    data["pro_managed_surfaces"] = keep
    state.save(data)

    return responses.ok(command, removed_surfaces=removed, remaining=len(keep),
                        evidence=_evidence_block())


_SURFACE_KIND_TIERS = {"plugin": 4, "skill": 4, "hook": 4, "mcp_config": 4, "handoff_file": 2}


def _surface_still_present(record: Dict[str, Any]) -> bool:
    target = Path(record.get("target", ""))
    writer = record.get("writer") or ("toml_mcp" if record.get("surface_kind") == "mcp_config" else "")
    if writer == "toml_mcp":
        return target.exists() and _TOML_MARK_BEGIN in target.read_text(encoding="utf-8")
    if writer == "json_mcp":
        return MCP_SERVER_NAME in _load_json(target, {}).get("mcpServers", {})
    if writer == "cursor_hooks":
        hooks = _load_json(target, {}).get("hooks", {})
        return any(_is_cursor_hook_ours(e) for entries in hooks.values() for e in entries)
    return target.exists()


def _integration_status(name: str, state: Dict[str, Any]) -> Dict[str, Any]:
    status = {"integrated": False, "depth_tier": 0, "record": None}
    for record in state.get("pro_managed_surfaces", []):
        if record.get("harness") != name or not _surface_still_present(record):
            continue
        tier = _SURFACE_KIND_TIERS.get(record.get("surface_kind", ""), 2)
        if not status["integrated"] or tier > status["depth_tier"]:
            status = {"integrated": True, "depth_tier": tier, "record": record}
    return status


def _surface_content(name: str, surface: Dict[str, Any], record: Dict[str, Any]) -> str:
    display = name.replace("_", " ").title()
    body = f"""# AetherMind Pro continuity for {display}

This machine runs AetherMind Pro, a local continuity coordinator. Use the
`aethermind-pro` CLI to orient before work and to record durable context.

At the start of work in any project:

1. `aethermind-pro status --project-root . --json` — orient from existing continuity.
2. If the project has no continuity yet: `aethermind-pro first-run --project-root . --json`.

Before ending or handing off non-trivial work:

- `aethermind-pro comms brief --project-root . --harness {name} --json` — orientation brief.
- `aethermind-pro comms write --project-root . --capsule <json-file> --json` — record
  durable decisions, corrections, and friction for the next session.
- `aethermind-pro layers inspect --project-root . --json` — browse existing layers.

<!-- pro-managed: created_by=aethermind_pro surface_id={record['surface_id']}
     remove with: {REMOVE_HINT.format(name=name)} -->
"""
    if name == "hermes":
        body += """
## Pro services above the base plugin

The `aethermind` Hermes plugin handles project-local layer/texture continuity.
AetherMind Pro adds coordinator services on top of it:

- `aethermind-pro coordinate --project-root . --json` — cross-project coordination.
- `aethermind-pro map --json` — local machine continuity map.
- `aethermind-pro trust review --subject <path> --json` — trust review of foreign material.
- `aethermind-pro doctor --human` — health and harness status.
"""
    if surface["surface_kind"] == "skill":
        frontmatter = (
            "---\n"
            "name: aethermind-pro\n"
            "description: Use AetherMind Pro local continuity at session start to orient in any "
            "project, and before ending non-trivial work to record durable decisions, corrections, "
            "and context for the next session.\n"
            "---\n\n"
        )
        return frontmatter + body
    return body


def discover(*, state_dir: "str | Path | None" = None) -> Dict[str, Any]:
    state = ProState(state_dir).load()
    configured = state.get("harnesses", {})
    harnesses: List[Dict[str, Any]] = []
    for kind in FIRST_CLASS:
        detected, basis = _detect(kind)
        cfg = configured.get(kind)
        integration = _integration_status(kind, state)
        if integration["integrated"]:
            current_tier = integration["depth_tier"]
            next_action = f"aethermind-pro harnesses check --name {kind} --json"
        else:
            current_tier = 2 if cfg and cfg.get("enabled") else (1 if detected else 0)
            next_action = (INTEGRATE_HINT.format(name=kind) if detected
                           else f"aethermind-pro harnesses bootstrap plan --name {kind} --json")
        harnesses.append({
            "name": kind,
            "display_name": kind.replace("_", " ").title(),
            "classification": "first_class_known",
            "detected": detected,
            "detection_basis": basis,
            "integrated": integration["integrated"],
            "trusted": False,
            "trust_review": "not_required" if cfg else "required",
            "depth": {
                "current_tier": current_tier,
                "max_planned_tier": 5,
                "surfaces_available": ["plaintext_handoff", "json_capsule", "cli"],
                "surfaces_missing": ["check_in_loop"],
            },
            "next_action": next_action,
        })
    for name, hints in _FUTURE_CANDIDATE_HINTS.items():
        if name in configured:
            continue
        detected, basis = _detect_from_hints(hints)
        if detected:
            harnesses.append({
                "name": name,
                "display_name": name.replace("_", " ").title(),
                "classification": "future_unknown",
                "detected": True,
                "detection_basis": basis,
                "integrated": False,
                "trusted": False,
                "trust_review": "required",
                "depth": {
                    "current_tier": 1,
                    "max_planned_tier": 5,
                    "surfaces_available": ["plaintext_handoff", "cli_candidate"],
                    "surfaces_missing": ["configured_handoff", "trust_review", "check_in_loop"],
                },
                "next_action": f"aethermind-pro harnesses bootstrap plan --name {name} --json",
            })
    return responses.ok("harnesses discover", harnesses=harnesses, evidence=_evidence_block())


def check(name: Optional[str], project_root: Optional[str] = None, *,
          state_dir: "str | Path | None" = None) -> Dict[str, Any]:
    if not name:
        return responses.error("harnesses check", "name_required",
                               "harnesses check requires --name",
                               "aethermind-pro harnesses check --name <name> --project-root . --json")
    state_data = ProState(state_dir).load()
    configured = state_data.get("harnesses", {})
    cfg = configured.get(name)
    classification = "first_class_known" if name in FIRST_CLASS else "custom"
    integration = _integration_status(name, state_data)

    detected, _ = _detect(name) if name in FIRST_CLASS else (bool(cfg), [])
    degradation: List[Dict[str, str]] = []
    if not cfg and not detected:
        degradation.append({"code": "harness_missing",
                            "message": f"{name} is not configured or detected",
                            "next_action": f"configure it: aethermind-pro harnesses configure --name {name}"})
    if not cfg:
        degradation.append({"code": "manual_only",
                            "message": "only manual/plaintext handoff is available until configured",
                            "next_action": "configure a handoff surface to deepen integration"})

    def cap(supported: bool) -> str:
        return "available" if supported else "degraded"

    capabilities = {
        "read_orientation": "available",
        "write_or_request_continuity": cap(bool(integration["integrated"] or (cfg and cfg.get("handoff_output") not in (None, "manual")))),
        "resume_session": cap(bool(cfg and cfg.get("resume_session", {}).get("supported"))),
        "check_in": cap(bool(cfg and cfg.get("check_in", {}).get("supported"))),
        "mcp_or_plugin": cap(bool(integration["integrated"] or (cfg and cfg.get("plugin", {}).get("required")))),
    }
    if integration["integrated"]:
        depth_tier_proven = integration["depth_tier"]
    else:
        depth_tier_proven = 2 if cfg else (1 if detected else 0)

    return responses.ok(
        "harnesses check",
        harness=name,
        classification=classification,
        depth_tier_proven=depth_tier_proven,
        capabilities=capabilities,
        created_surfaces=[integration["record"]] if integration["record"] else [],
        degradation=degradation,
        evidence=_evidence_block(),
    )


def _home() -> Path:
    return Path(os.environ.get("HOME", str(Path.home())))


def _detect(kind: str) -> Tuple[bool, List[str]]:
    detected, basis = _detect_from_hints(_DETECTION_HINTS.get(kind, []))
    for hint in _CONFIG_SURFACE_HINTS.get(kind, []):
        if (_home() / hint).is_dir():
            basis = basis + ["config_surface_present"]
            return True, basis
    return detected, basis


def _classification_for(name: str, cfg: Optional[Dict[str, Any]] = None) -> str:
    if name in FIRST_CLASS:
        return "first_class_known"
    kind = (cfg or {}).get("kind")
    if kind == "future" or name in _FUTURE_CANDIDATE_HINTS:
        return "future_unknown"
    return "custom"


def _is_detected(name: str, cfg: Optional[Dict[str, Any]] = None) -> bool:
    if cfg:
        return True
    if name in FIRST_CLASS:
        detected, _ = _detect(name)
        return detected
    if name in _FUTURE_CANDIDATE_HINTS:
        detected, _ = _detect_from_hints(_FUTURE_CANDIDATE_HINTS[name])
        return detected
    return False


def _bootstrap_prompts(name: str, classification: str, detected: bool) -> List[Dict[str, Any]]:
    trust_review = "required" if classification in {"future_unknown", "custom"} else "not_required"
    target = f"supported_public_surface:{name}"
    return [
        _prompt(name, detected, "write_handoff_file", target, "pro_managed_external_surface",
                "remove_pro_managed_file", "removed_by_default", trust_review),
        _prompt(name, detected, "write_custom_harness_config", target, "external_harness_config",
                "restore_previous_config", "offer_removal", trust_review),
        _prompt(name, detected, "manual_instruction_only", "terminal_or_harness_prompt",
                "user_workspace", "not_applicable", "offer_removal", trust_review),
    ]


def _prompt(name: str, detected: bool, kind: str, target: str, owner: str, rollback: str,
            uninstall_behavior: str, trust_review: str) -> Dict[str, Any]:
    prompt = {
        "prompt_id": f"prompt-{name}-{kind}",
        "harness": {
            "name": name,
            "detected": detected,
            "current_depth_tier": 1,
            "target_depth_tier": 4,
        },
        "proposed_change": {
            "kind": kind,
            "target": target,
            "owner": owner,
            "required_for_first_value": False,
            "required_for_harness_depth": True,
            "network_required": False,
            "trust_review": trust_review,
        },
        "explanation": {
            "why": "deepen harness integration through supported public or user-configured surfaces",
            "what_will_change": "no files are changed unless this prompt is explicitly approved",
            "rollback": rollback,
            "uninstall_behavior": uninstall_behavior,
        },
        "approval": {
            "default": "deny",
            "accepted_values": ["approve_once", "deny", "show_details", "manual_steps_only"],
        },
    }
    ownership = _ownership_preview(prompt)
    if ownership is not None:
        prompt["ownership_preview"] = ownership
    return prompt


def _ownership_preview(prompt: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    change = prompt["proposed_change"]
    kind = change["kind"]
    surface_kind = {
        "write_handoff_file": "handoff_file",
        "write_custom_harness_config": "custom_config",
    }.get(kind)
    if not surface_kind:
        return None
    rollback = {
        "remove_pro_managed_file": "remove",
        "restore_previous_config": "restore_previous",
        "manual_review_required": "manual_review_required",
    }.get(prompt["explanation"]["rollback"], "manual_review_required")
    default_uninstall = {
        "removed_by_default": "remove",
        "offer_removal": "offer_removal",
        "preserved_user_owned": "preserve",
    }.get(prompt["explanation"]["uninstall_behavior"], "offer_removal")
    harness = prompt["harness"]["name"]
    return {
        "surface_id": f"preview-{harness}-{surface_kind}",
        "harness": harness,
        "surface_kind": surface_kind,
        "target": change["target"],
        "created_by": "aethermind_pro",
        "created_at": None,
        "approval_id": prompt["prompt_id"],
        "trust_event_id": None,
        "rollback": rollback,
        "default_uninstall": default_uninstall,
    }


def _detect_from_hints(hints: List[str]):
    basis: List[str] = []
    for hint in hints:
        if shutil.which(hint):
            basis.append("executable_present")
            return True, basis
    return False, basis
