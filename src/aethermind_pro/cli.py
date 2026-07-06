"""AetherMind Pro command router.

Derived from docs/PRO_SYSTEM_CONTRACT.md lines 21-43 (shipped command contract),
docs/FIRST_TEN_MINUTES_CONTRACT.md (investigate/status/doctor), and the build plan
section 5 command list.

JSON is the default output; ``--human`` is opt-in only. Unknown commands return a
structured JSON error. No command requires admin UI, tracker, or HUD to function.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from . import (
    bootstrap,
    comms,
    coordinator,
    evidence,
    harnesses,
    investigate as investigate_mod,
    layers,
    platform as platform_mod,
    plugins,
    product_ux,
    primitive_mcp,
    provenance as provenance_mod,
    responses,
    roots,
    settings as settings_mod,
    smoke as smoke_mod,
    substrate,
    support,
    trust,
)
from .audit import AuditLog
from .export import export_state
from .roots import RootsRegistry
from .state import stable_root_id

SUBCOMMAND_COMMANDS = {
    "bootstrap", "substrate", "primitive-mcp", "comms", "harnesses", "trust",
    "layers", "services", "settings", "plugins", "roots",
}

KNOWN_COMMANDS = {
    "status", "bootstrap", "substrate", "primitive-mcp", "roots", "investigate", "first-run",
    "map", "coordinate", "comms", "harnesses", "services", "trust", "layers",
    "settings", "plugins", "audit", "support-bundle", "export", "smoke", "doctor",
    "tracker", "admin-ui", "uninstall", "keygen", "sign", "verify",
}

BOOLEAN_FLAGS = {"human", "json", "no-write", "confirm", "approve", "all"}


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        return _emit(_help_error("no command provided"), human=False)

    command = argv[0]
    if command in ("-h", "--help", "help"):
        return _emit(_help(), human=False)
    if command not in KNOWN_COMMANDS:
        return _emit(_unknown(command), human=False)

    subcommand, rest = _split_subcommand(command, argv[1:])
    positional, flags = _parse(rest)
    human = bool(flags.get("human"))
    state_dir = flags.get("state-dir")
    project_root = flags.get("project-root")

    try:
        result = _dispatch(command, subcommand, positional, flags, project_root, state_dir)
    except Exception as exc:  # noqa: BLE001 - surfaced as bounded JSON error
        result = responses.error(command, "internal_error",
                                 f"unexpected error: {type(exc).__name__}",
                                 "report this with the command you ran")
    return _emit(result, human=human)


def _dispatch(command: str, sub: Optional[str], positional: List[str], flags: Dict[str, Any],
              project_root: Optional[str], state_dir: Optional[str]) -> Dict[str, Any]:
    if command == "status":
        return coordinator.status(project_root, state_dir=state_dir)

    if command == "bootstrap":
        if sub in (None, "status"):
            return bootstrap.status(state_dir=state_dir)
        if sub == "plan":
            return bootstrap.plan(project_root, state_dir=state_dir)
        if sub == "apply":
            return bootstrap.apply(project_root, state_dir=state_dir)
        return _unknown_sub(command, sub)

    if command == "substrate":
        if sub in (None, "status"):
            return responses.ok("substrate status", **substrate.status(project_root),
                                evidence=_source_evidence())
        return _unknown_sub(command, sub)

    if command == "primitive-mcp":
        if sub == "serve":
            raise SystemExit(primitive_mcp.serve())
        if sub == "call":
            tool = flags.get("tool")
            params = _json_arg(flags.get("params")) or {}
            if not isinstance(params, dict):
                params = {}
            if flags.get("data-root"):
                params["data_root"] = flags["data-root"]
            layer = _json_arg(flags.get("layer"))
            if layer is not None:
                params["layer"] = layer
            if not tool:
                return responses.error("primitive-mcp call", "tool_required",
                                       "primitive-mcp call requires --tool",
                                       "aethermind-pro primitive-mcp call --tool status --data-root .")
            result = primitive_mcp.call(tool, params)
            result["command"] = "primitive-mcp call"
            return result
        return _unknown_sub(command, sub)

    if command == "roots":
        return _roots(sub, flags, project_root, state_dir)

    if command == "investigate":
        return investigate_mod.investigate(project_root, no_write=bool(flags.get("no-write")),
                                           state_dir=state_dir)

    if command == "first-run":
        return product_ux.first_run(project_root, state_dir=state_dir)

    if command == "map":
        return coordinator.map_command(state_dir=state_dir)

    if command == "coordinate":
        return coordinator.coordinate(project_root, state_dir=state_dir)

    if command == "comms":
        if sub == "brief":
            return comms.brief(project_root, state_dir=state_dir,
                               harness_target=flags.get("harness", "custom"))
        if sub == "write":
            return comms.write(project_root, _json_arg(flags.get("capsule")), state_dir=state_dir)
        if sub == "read":
            return comms.read(project_root, state_dir=state_dir)
        return _unknown_sub(command, sub)

    if command == "harnesses":
        if sub in (None, "list"):
            return harnesses.list_harnesses(state_dir=state_dir)
        if sub == "configure":
            return harnesses.configure(flags.get("name"), _json_arg(flags.get("config")),
                                       state_dir=state_dir)
        if sub == "check":
            return harnesses.check(flags.get("name"), project_root, state_dir=state_dir)
        if sub == "discover":
            return harnesses.discover(state_dir=state_dir)
        if sub == "bootstrap":
            action = positional[0] if positional else "plan"
            if action == "plan":
                return harnesses.bootstrap_plan(flags.get("name"), state_dir=state_dir)
            if action == "apply":
                approval = flags.get("approval")
                return harnesses.bootstrap_apply(
                    flags.get("name"),
                    approve=bool(flags.get("approve")),
                    approval_id=approval if isinstance(approval, str) else None,
                    state_dir=state_dir)
            if action == "remove":
                return harnesses.bootstrap_remove(flags.get("name"),
                                                  remove_all=bool(flags.get("all")),
                                                  state_dir=state_dir)
            return _unknown_sub("harnesses bootstrap", action)
        return _unknown_sub(command, sub)

    if command == "services":
        if sub in (None, "status"):
            return _services_status(state_dir)
        if sub in ("start", "stop", "restart"):
            from . import services
            return services.control(sub, flags.get("name"), state_dir=state_dir)
        return _unknown_sub(command, sub)

    if command == "trust":
        if sub == "review":
            return trust.review(flags.get("subject"), project_root,
                                origin=flags.get("origin", "downloaded"), state_dir=state_dir)
        if sub == "approve":
            return trust.approve(flags.get("subject-digest"), state_dir=state_dir)
        return _unknown_sub(command, sub)

    if command == "layers":
        if sub in (None, "browse"):
            return layers.browse(state_dir=state_dir)
        if sub == "inspect":
            return layers.inspect(project_root, state_dir=state_dir)
        if sub == "mark":
            return layers.mark(project_root, flags.get("layer-id"), flags.get("mark"),
                               state_dir=state_dir)
        if sub == "remove":
            return layers.remove(project_root, flags.get("layer-id"),
                                 confirm=bool(flags.get("confirm")), state_dir=state_dir)
        return _unknown_sub(command, sub)

    if command == "settings":
        if sub in (None, "show"):
            return settings_mod.show(state_dir=state_dir)
        if sub == "set":
            key, value = _settings_kv(positional, flags)
            return settings_mod.set_value(key, value, state_dir=state_dir)
        return _unknown_sub(command, sub)

    if command == "plugins":
        if sub in (None, "detect"):
            return plugins.detect()
        if sub == "install":
            return plugins.install(approve=bool(flags.get("approve")))
        if sub == "repair":
            return plugins.repair(approve=bool(flags.get("approve")))
        return _unknown_sub(command, sub)

    if command == "audit":
        events = AuditLog(state_dir).tail(limit=int(flags.get("limit", 50) or 50))
        return responses.ok("audit", events=events, count=len(events),
                            evidence=_source_evidence())

    if command == "support-bundle":
        return support.support_bundle(flags.get("output"), state_dir=state_dir)

    if command == "export":
        return export_state(flags.get("output"), state_dir=state_dir)

    if command == "smoke":
        return smoke_mod.smoke(project_root)

    if command == "keygen":
        return _keygen(flags)

    if command == "sign":
        return _sign(flags, project_root, state_dir)

    if command == "verify":
        return _verify(flags, project_root)

    if command == "doctor":
        return support.doctor(project_root=project_root, state_dir=state_dir,
                              human=bool(flags.get("human")))

    if command == "uninstall":
        if sub in (None, "plan"):
            return product_ux.uninstall_plan(project_root, state_dir=state_dir)
        return _unknown_sub(command, sub)

    if command == "tracker":
        return platform_mod.tracker()

    if command == "admin-ui":
        return platform_mod.admin_ui()

    return _unknown(command)


def _roots(sub: Optional[str], flags: Dict[str, Any], project_root: Optional[str],
           state_dir: Optional[str]) -> Dict[str, Any]:
    registry = RootsRegistry(state_dir)
    if sub in (None, "list"):
        return responses.ok("roots list", roots=registry.list(), evidence=_source_evidence())
    if sub == "add":
        path, err = roots.resolve_root(project_root)
        if err:
            return responses.error("roots add", err,
                                   "roots add requires an explicit, existing --project-root",
                                   "aethermind-pro roots add --project-root . --json")
        assert path is not None
        record = roots.build_root_record(path, trust_state="trusted")
        registry.add(record)
        return responses.ok("roots add", root=record, evidence=_source_evidence())
    if sub == "remove":
        root_id = flags.get("root-id")
        if not root_id:
            return responses.error("roots remove", "root_id_required",
                                   "roots remove requires --root-id",
                                   "aethermind-pro roots remove --root-id <id> --json")
        removed = registry.remove(root_id)
        return responses.ok("roots remove", removed=removed, root_id=root_id,
                            evidence=_source_evidence())
    return _unknown_sub("roots", sub)


def _keygen(flags: Dict[str, Any]) -> Dict[str, Any]:
    out = flags.get("out") or flags.get("key")
    if not out:
        return responses.error("keygen", "out_required",
                               "keygen requires --out <path> for the secret key",
                               "aethermind-pro keygen --out ~/.config/aethermind/provenance.key --json")
    try:
        info = provenance_mod.generate_keypair(out)
    except FileExistsError as exc:
        return responses.error("keygen", "key_exists", str(exc),
                               "choose a different --out path or remove the existing key yourself")
    except OSError as exc:
        return responses.error("keygen", "keygen_failed", f"could not write key: {exc}",
                               "check the --out directory is writable")
    return responses.ok("keygen", public_key=info["public_key"], key_id=info["key_id"],
                        secret_path=info["secret_path"], public_path=info["public_path"],
                        note="keep the secret key private; distribute only the .pub / key_id",
                        evidence=_source_evidence())


def _sign(flags: Dict[str, Any], project_root: Optional[str],
          state_dir: Optional[str]) -> Dict[str, Any]:
    key = flags.get("key")
    if not key:
        return responses.error("sign", "key_required",
                               "sign requires --key <secret-key-path>",
                               "aethermind-pro sign --project-root . --key <path> --json")
    store, err = _resolve_store(project_root)
    if err:
        return err
    try:
        secret = provenance_mod.load_secret(key)
    except (OSError, ValueError) as exc:
        return responses.error("sign", "key_unreadable", f"could not read secret key: {exc}",
                               "pass a valid 32-byte secret key with --key")
    result = provenance_mod.sign_store(store, secret)
    result.update({"ok": True, "command": "sign", "evidence": _source_evidence()})
    return result


def _verify(flags: Dict[str, Any], project_root: Optional[str]) -> Dict[str, Any]:
    store, err = _resolve_store(project_root)
    if err:
        return err
    pubkey = None
    pub_hex = flags.get("pubkey")
    if pub_hex:
        try:
            pubkey = bytes.fromhex(str(pub_hex))
        except ValueError:
            return responses.error("verify", "pubkey_invalid",
                                   "--pubkey must be hex-encoded",
                                   "pass the public key hex from `aethermind-pro keygen`")
    report = provenance_mod.verify_store(store, pubkey)
    report.update({"ok": True, "command": "verify", "evidence": _source_evidence()})
    return report


def _resolve_store(project_root: Optional[str]) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    path, resolve_error = roots.resolve_root(project_root)
    if resolve_error:
        return None, responses.error("provenance", resolve_error,
                                     "provenance commands require an explicit, existing --project-root",
                                     "aethermind-pro verify --project-root . --json")
    assert path is not None
    return str(path), None


def _services_status(state_dir: Optional[str]) -> Dict[str, Any]:
    from . import services
    return services.status(state_dir=state_dir)


def _settings_kv(positional: List[str], flags: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    if flags.get("key"):
        return flags.get("key"), flags.get("value")
    if len(positional) >= 2:
        return positional[0], positional[1]
    if len(positional) == 1:
        return positional[0], None
    return None, None


def _split_subcommand(command: str, args: List[str]) -> Tuple[Optional[str], List[str]]:
    if command in SUBCOMMAND_COMMANDS and args and not args[0].startswith("--"):
        return args[0], args[1:]
    return None, args


def _parse(args: List[str]) -> Tuple[List[str], Dict[str, Any]]:
    positional: List[str] = []
    flags: Dict[str, Any] = {}
    i = 0
    while i < len(args):
        token = args[i]
        if token.startswith("--"):
            key = token[2:]
            if key in BOOLEAN_FLAGS:
                flags[key] = True
                i += 1
            elif i + 1 < len(args) and not args[i + 1].startswith("--"):
                flags[key] = args[i + 1]
                i += 2
            else:
                flags[key] = True
                i += 1
        else:
            positional.append(token)
            i += 1
    return positional, flags


def _json_arg(value: Any) -> Any:
    if value is None or value is True:
        return None
    candidate = Path(str(value)).expanduser()
    try:
        if candidate.exists():
            return json.loads(candidate.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pass
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return value


def _source_evidence() -> Dict[str, Any]:
    return {
        "proof_surface": "source_tree",
        "tier_eligible": [evidence.TIER_SOURCE_CONTRACT],
        "blockers": list(evidence.STANDARD_BLOCKERS),
    }


def _unknown(command: str) -> Dict[str, Any]:
    return responses.error(command, "unknown_command",
                           f"unknown command: {command}",
                           "run `aethermind-pro help` for the command list")


def _unknown_sub(command: str, sub: Optional[str]) -> Dict[str, Any]:
    return responses.error(command, "unknown_subcommand",
                           f"unknown {command} subcommand: {sub}",
                           f"run `aethermind-pro help` for {command} usage")


def _help_error(message: str) -> Dict[str, Any]:
    return responses.error("help", "no_command", message,
                           "run `aethermind-pro help` for the command list")


def _help() -> Dict[str, Any]:
    return responses.ok("help", commands=sorted(KNOWN_COMMANDS), evidence=_source_evidence())


def _emit(result: Dict[str, Any], human: bool) -> int:
    if human:
        print(_humanize(result))
    else:
        print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("ok") else 1


def _humanize(result: Dict[str, Any]) -> str:
    if "human" in result:
        return result["human"]
    command = result.get("command", "?")
    status = "ok" if result.get("ok") else "error"
    lines = [f"AetherMind Pro: {command} [{status}]"]
    if not result.get("ok"):
        err = result.get("error", {})
        lines.append(f"  error: {err.get('code')} - {err.get('message')}")
        lines.append(f"  next: {err.get('next_action')}")
        return "\n".join(lines)
    for key, value in result.items():
        if key in ("ok", "command", "evidence"):
            continue
        rendered = value if isinstance(value, (str, int, float, bool)) else json.dumps(value)
        lines.append(f"  {key}: {rendered}")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
