"""Harness integration must be real: consent-gated bootstrap apply writes
Pro-managed surfaces into detected harnesses, install/first-run/doctor offer
integration (including harnesses added later), and uninstall ownership covers
every created surface.

Controlling docs: docs/plans/harness-discovery-bootstrap-source-contract-spec.md
(prompts, apply command, ownership records, depth tiers, trust review),
docs/HARNESS_CONFORMANCE_CONTRACT.md (all first-class harnesses, no shortcuts).
"""

import json
import os
import stat
from pathlib import Path

import pytest

from aethermind_pro import harnesses, product_ux, support

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    empty_bin = tmp_path / "empty-bin"
    empty_bin.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("PATH", str(empty_bin))
    return home


def claude_skill_path(home: Path) -> Path:
    return home / ".claude" / "skills" / "aethermind-pro" / "SKILL.md"


def test_discover_detects_config_surface(fake_home, state_dir):
    (fake_home / ".claude").mkdir()
    result = harnesses.discover(state_dir=state_dir)
    assert result["ok"] is True
    claude = next(h for h in result["harnesses"] if h["name"] == "claude_code")
    assert claude["detected"] is True
    assert "config_surface_present" in claude["detection_basis"]
    assert claude["integrated"] is False
    assert "bootstrap" in claude["next_action"]


def test_discover_honest_when_nothing_present(fake_home, state_dir):
    result = harnesses.discover(state_dir=state_dir)
    for h in result["harnesses"]:
        if h["classification"] == "first_class_known":
            assert h["detected"] is False
            assert h["integrated"] is False


def test_bootstrap_apply_defaults_to_deny(fake_home, state_dir):
    (fake_home / ".claude").mkdir()
    result = harnesses.bootstrap_apply("claude_code", approve=False, state_dir=state_dir)
    assert result["ok"] is True
    assert result["action"] == "denied_default_no_approval"
    assert result["nothing_written"] is True
    assert not claude_skill_path(fake_home).exists()


def test_bootstrap_apply_writes_pro_managed_skill_with_consent(fake_home, state_dir):
    (fake_home / ".claude").mkdir()
    result = harnesses.bootstrap_apply("claude_code", approve=True, state_dir=state_dir)
    assert result["ok"] is True
    assert result["action"] == "integrated"

    skill = claude_skill_path(fake_home)
    assert skill.exists()
    content = skill.read_text(encoding="utf-8")
    assert "aethermind-pro status --project-root" in content
    assert "aethermind-pro comms brief" in content
    assert "pro-managed" in content.lower()

    surfaces = result["created_surfaces"]
    assert len(surfaces) == 1
    record = surfaces[0]
    assert record["harness"] == "claude_code"
    assert record["surface_kind"] == "skill"
    assert record["created_by"] == "aethermind_pro"
    assert record["created_at"]
    assert record["approval_id"]
    assert record["rollback"] == "remove"
    assert record["default_uninstall"] == "remove"
    assert record["target"] == str(skill)
    assert result["depth_tier_now"] == 4


def hermes_stub(fake_home: Path, *, version: str = "0.1.1") -> Path:
    """Fake `hermes` CLI: plugins install creates the plugin dir, remove deletes it."""
    exe_dir = Path(os.environ["PATH"].split(os.pathsep)[0])
    exe = exe_dir / "hermes"
    exe.write_text(
        '#!/bin/sh\n'
        'PATH=/usr/bin:/bin\n'
        'if [ "$1" = "plugins" ] && [ "$2" = "install" ]; then\n'
        '  mkdir -p "$HOME/.hermes/plugins/aethermind"\n'
        f'  printf "name: aethermind\\nversion: {version}\\n" > "$HOME/.hermes/plugins/aethermind/plugin.yaml"\n'
        '  exit 0\n'
        'fi\n'
        'if [ "$1" = "plugins" ] && { [ "$2" = "remove" ] || [ "$2" = "uninstall" ]; }; then\n'
        '  rm -rf "$HOME/.hermes/plugins/aethermind"\n'
        '  exit 0\n'
        'fi\n'
        'exit 0\n',
        encoding="utf-8",
    )
    exe.chmod(0o755)
    return exe


def installed_plugin_manifest(fake_home: Path, version: str) -> Path:
    plugin_dir = fake_home / ".hermes" / "plugins" / "aethermind"
    plugin_dir.mkdir(parents=True)
    manifest = plugin_dir / "plugin.yaml"
    manifest.write_text(f"name: aethermind\nversion: {version}\n", encoding="utf-8")
    return manifest


def test_hermes_apply_installs_published_plugin_via_hermes_cli(fake_home, state_dir):
    (fake_home / ".hermes").mkdir()
    hermes_stub(fake_home)

    result = harnesses.bootstrap_apply("hermes", approve=True, state_dir=state_dir)
    assert result["ok"] is True
    assert result["action"] == "integrated"
    # The published plugin is the native surface: full native-extension depth.
    assert result["depth_tier_now"] == 4
    assert (fake_home / ".hermes" / "plugins" / "aethermind" / "plugin.yaml").exists()

    kinds = {r["surface_kind"]: r for r in result["created_surfaces"]}
    assert "plugin" in kinds and "handoff_file" in kinds
    plugin_record = kinds["plugin"]
    assert plugin_record["created_by"] == "aethermind_pro"
    assert plugin_record["default_uninstall"] == "remove"


def test_hermes_apply_uses_existing_compatible_plugin(fake_home, state_dir):
    installed_plugin_manifest(fake_home, "0.1.1")

    result = harnesses.bootstrap_apply("hermes", approve=True, state_dir=state_dir)
    assert result["ok"] is True
    assert result["depth_tier_now"] == 4
    plugin_record = next(r for r in result["created_surfaces"] if r["surface_kind"] == "plugin")
    # Pro did not install it, so Pro must not remove it by default.
    assert plugin_record["created_by"] == "preexisting_user_install"
    assert plugin_record["default_uninstall"] == "preserve"


def test_hermes_apply_falls_back_honestly_without_hermes_cli(fake_home, state_dir):
    (fake_home / ".hermes").mkdir()
    result = harnesses.bootstrap_apply("hermes", approve=True, state_dir=state_dir)
    assert result["ok"] is True
    handoff = fake_home / ".hermes" / "aethermind-pro" / "HANDOFF.md"
    assert handoff.exists()
    # No plugin, no native-depth claim.
    assert result["depth_tier_now"] == 2
    codes = {d["code"] for d in result["degradation"]}
    assert "plugin_missing" in codes
    assert all(r["surface_kind"] != "plugin" for r in result["created_surfaces"])


def test_hermes_apply_reports_incompatible_plugin(fake_home, state_dir):
    installed_plugin_manifest(fake_home, "0.2.0")
    result = harnesses.bootstrap_apply("hermes", approve=True, state_dir=state_dir)
    assert result["ok"] is True
    assert result["depth_tier_now"] == 2
    codes = {d["code"] for d in result["degradation"]}
    assert "plugin_incompatible" in codes


def test_hermes_remove_uninstalls_pro_installed_plugin_only(fake_home, state_dir):
    (fake_home / ".hermes").mkdir()
    hermes_stub(fake_home)
    harnesses.bootstrap_apply("hermes", approve=True, state_dir=state_dir)
    assert (fake_home / ".hermes" / "plugins" / "aethermind").exists()

    result = harnesses.bootstrap_remove("hermes", state_dir=state_dir)
    assert result["ok"] is True
    assert not (fake_home / ".hermes" / "plugins" / "aethermind").exists()
    assert not (fake_home / ".hermes" / "aethermind-pro" / "HANDOFF.md").exists()


def test_hermes_remove_preserves_user_installed_plugin(fake_home, state_dir):
    installed_plugin_manifest(fake_home, "0.1.1")
    harnesses.bootstrap_apply("hermes", approve=True, state_dir=state_dir)

    result = harnesses.bootstrap_remove("hermes", state_dir=state_dir)
    assert result["ok"] is True
    # User-installed plugin stays; only Pro-managed surfaces go.
    assert (fake_home / ".hermes" / "plugins" / "aethermind" / "plugin.yaml").exists()
    assert not (fake_home / ".hermes" / "aethermind-pro" / "HANDOFF.md").exists()


def test_bootstrap_apply_requires_detection(fake_home, state_dir):
    result = harnesses.bootstrap_apply("grok_build", approve=True, state_dir=state_dir)
    assert result["ok"] is False
    assert result["error"]["code"] == "harness_missing"
    assert not (fake_home / ".grok").exists()


def test_bootstrap_apply_unknown_candidate_requires_trust_review(fake_home, state_dir, tmp_path):
    exe_dir = Path(os.environ["PATH"])
    exe = exe_dir / "openclaw"
    exe.write_text("#!/bin/sh\n", encoding="utf-8")
    exe.chmod(exe.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    result = harnesses.bootstrap_apply("openclaw", approve=True, state_dir=state_dir)
    assert result["ok"] is True
    assert result["action"] == "trust_review_required"
    assert result["nothing_written"] is True


def test_first_run_offers_harness_integration(fake_home, code_repo, state_dir):
    (fake_home / ".claude").mkdir()
    result = product_ux.first_run(code_repo, state_dir=state_dir)
    assert result["ok"] is True
    # First value never depends on harness integration.
    assert result["first_value"]["requires_harness"] is False

    block = result["harnesses"]
    names = [h["name"] for h in block["detected"]]
    assert "claude_code" in names
    offered = next(h for h in block["detected"] if h["name"] == "claude_code")
    assert offered["integrated"] is False
    assert "bootstrap apply" in offered["next_action"]
    assert block["integration_default"] == "deny_until_approved"
    assert "discover" in block["rerun_after_adding_harness"]


def test_doctor_reports_harness_integration(fake_home, state_dir):
    (fake_home / ".claude").mkdir()
    (fake_home / ".hermes").mkdir()
    harnesses.bootstrap_apply("claude_code", approve=True, state_dir=state_dir)

    result = support.doctor(state_dir=state_dir)
    checks = result["checks"]["harnesses"]
    assert "claude_code" in checks["integrated"]
    assert "hermes" in checks["detected_not_integrated"]
    assert "bootstrap apply" in checks["next_action"]


def test_uninstall_plan_lists_created_surfaces(fake_home, code_repo, state_dir):
    (fake_home / ".claude").mkdir()
    harnesses.bootstrap_apply("claude_code", approve=True, state_dir=state_dir)

    plan = product_ux.uninstall_plan(code_repo, state_dir=state_dir)
    surfaces = plan["pro_managed_surfaces"]
    assert surfaces["count"] >= 1
    kinds = {item.get("surface_kind") for item in surfaces["items"]}
    assert "skill" in kinds


def test_bootstrap_remove_deletes_surface_and_record(fake_home, state_dir):
    (fake_home / ".claude").mkdir()
    harnesses.bootstrap_apply("claude_code", approve=True, state_dir=state_dir)
    assert claude_skill_path(fake_home).exists()

    result = harnesses.bootstrap_remove("claude_code", state_dir=state_dir)
    assert result["ok"] is True
    assert not claude_skill_path(fake_home).exists()
    # Rollback leaves no Pro-created droppings: the empty per-product dir goes too.
    assert not claude_skill_path(fake_home).parent.exists()

    disc = harnesses.discover(state_dir=state_dir)
    claude = next(h for h in disc["harnesses"] if h["name"] == "claude_code")
    assert claude["integrated"] is False


def test_grok_apply_writes_skill_hook_and_mcp_config(fake_home, state_dir):
    (fake_home / ".grok").mkdir()
    (fake_home / ".grok" / "config.toml").write_text(
        '[mcp_servers.user_server]\nurl = "http://example.invalid/mcp"\n', encoding="utf-8")

    result = harnesses.bootstrap_apply("grok_build", approve=True, state_dir=state_dir)
    assert result["ok"] is True
    assert result["depth_tier_now"] == 4
    kinds = {r["surface_kind"] for r in result["created_surfaces"]}
    assert kinds == {"skill", "hook", "mcp_config"}

    skill = fake_home / ".grok" / "skills" / "aethermind-pro" / "SKILL.md"
    assert skill.exists()

    hook = fake_home / ".grok" / "hooks" / "aethermind-pro.json"
    hook_payload = json.loads(hook.read_text(encoding="utf-8"))
    assert "SessionStart" in hook_payload["hooks"]
    commands = json.dumps(hook_payload)
    assert "aethermind-pro" in commands

    config = (fake_home / ".grok" / "config.toml").read_text(encoding="utf-8")
    assert "[mcp_servers.aethermind_pro]" in config
    assert '"primitive-mcp", "serve"' in config
    # User content is untouched.
    assert "[mcp_servers.user_server]" in config


def test_grok_apply_is_idempotent_for_mcp_block(fake_home, state_dir):
    (fake_home / ".grok").mkdir()
    harnesses.bootstrap_apply("grok_build", approve=True, state_dir=state_dir)
    harnesses.bootstrap_apply("grok_build", approve=True, state_dir=state_dir)
    config = (fake_home / ".grok" / "config.toml").read_text(encoding="utf-8")
    assert config.count("[mcp_servers.aethermind_pro]") == 1


def test_grok_remove_strips_only_pro_managed_pieces(fake_home, state_dir):
    (fake_home / ".grok").mkdir()
    (fake_home / ".grok" / "config.toml").write_text(
        '[mcp_servers.user_server]\nurl = "http://example.invalid/mcp"\n', encoding="utf-8")
    harnesses.bootstrap_apply("grok_build", approve=True, state_dir=state_dir)

    result = harnesses.bootstrap_remove("grok_build", state_dir=state_dir)
    assert result["ok"] is True
    assert not (fake_home / ".grok" / "skills" / "aethermind-pro" / "SKILL.md").exists()
    assert not (fake_home / ".grok" / "hooks" / "aethermind-pro.json").exists()
    config = (fake_home / ".grok" / "config.toml").read_text(encoding="utf-8")
    assert "[mcp_servers.aethermind_pro]" not in config
    assert "[mcp_servers.user_server]" in config

    disc = harnesses.discover(state_dir=state_dir)
    grok = next(h for h in disc["harnesses"] if h["name"] == "grok_build")
    assert grok["integrated"] is False


def test_codex_apply_writes_skill_and_mcp_config(fake_home, state_dir):
    (fake_home / ".codex").mkdir()
    (fake_home / ".codex" / "config.toml").write_text("model = \"gpt\"\n", encoding="utf-8")

    result = harnesses.bootstrap_apply("codex", approve=True, state_dir=state_dir)
    assert result["ok"] is True
    assert result["depth_tier_now"] == 4
    kinds = {r["surface_kind"] for r in result["created_surfaces"]}
    assert kinds == {"skill", "mcp_config"}
    assert (fake_home / ".codex" / "skills" / "aethermind-pro" / "SKILL.md").exists()
    config = (fake_home / ".codex" / "config.toml").read_text(encoding="utf-8")
    assert "[mcp_servers.aethermind_pro]" in config
    assert config.startswith('model = "gpt"')

    harnesses.bootstrap_remove("codex", state_dir=state_dir)
    config = (fake_home / ".codex" / "config.toml").read_text(encoding="utf-8")
    assert "[mcp_servers.aethermind_pro]" not in config
    assert 'model = "gpt"' in config


def cursor_env(fake_home: Path) -> None:
    cursor = fake_home / ".cursor"
    cursor.mkdir()
    (cursor / "mcp.json").write_text(json.dumps({
        "mcpServers": {"user_server": {"url": "http://example.invalid/mcp"}}
    }, indent=2) + "\n", encoding="utf-8")
    (cursor / "hooks.json").write_text(json.dumps({
        "version": 1,
        "hooks": {"sessionStart": [{"command": "python3 /home/user/own-hook.py", "timeout": 10}]},
    }, indent=2) + "\n", encoding="utf-8")


def test_cursor_discover_detects_config_surface(fake_home, state_dir):
    (fake_home / ".cursor").mkdir()
    result = harnesses.discover(state_dir=state_dir)
    cursor = next(h for h in result["harnesses"] if h["name"] == "cursor")
    assert cursor["classification"] == "first_class_known"
    assert cursor["detected"] is True
    assert "config_surface_present" in cursor["detection_basis"]


def test_cursor_apply_writes_skill_mcp_json_and_hook_entries(fake_home, state_dir):
    cursor_env(fake_home)
    result = harnesses.bootstrap_apply("cursor", approve=True, state_dir=state_dir)
    assert result["ok"] is True
    assert result["depth_tier_now"] == 4
    kinds = {r["surface_kind"] for r in result["created_surfaces"]}
    assert kinds == {"skill", "mcp_config", "hook"}

    assert (fake_home / ".cursor" / "skills" / "aethermind-pro" / "SKILL.md").exists()

    mcp = json.loads((fake_home / ".cursor" / "mcp.json").read_text(encoding="utf-8"))
    assert "aethermind_pro" in mcp["mcpServers"]
    assert mcp["mcpServers"]["aethermind_pro"]["args"] == ["primitive-mcp", "serve"]
    # User entries untouched.
    assert mcp["mcpServers"]["user_server"] == {"url": "http://example.invalid/mcp"}

    hooks = json.loads((fake_home / ".cursor" / "hooks.json").read_text(encoding="utf-8"))
    assert hooks["version"] == 1
    session = hooks["hooks"]["sessionStart"]
    assert any("--harness cursor" in e["command"] for e in session)
    assert any("own-hook.py" in e["command"] for e in session)
    assert any("--harness cursor" in e["command"] for e in hooks["hooks"]["preCompact"])


def test_cursor_apply_is_idempotent(fake_home, state_dir):
    cursor_env(fake_home)
    harnesses.bootstrap_apply("cursor", approve=True, state_dir=state_dir)
    harnesses.bootstrap_apply("cursor", approve=True, state_dir=state_dir)
    hooks = json.loads((fake_home / ".cursor" / "hooks.json").read_text(encoding="utf-8"))
    ours = [e for e in hooks["hooks"]["sessionStart"] if "--harness cursor" in e["command"]]
    assert len(ours) == 1
    mcp = json.loads((fake_home / ".cursor" / "mcp.json").read_text(encoding="utf-8"))
    assert list(mcp["mcpServers"]).count("aethermind_pro") == 1


def test_cursor_remove_strips_only_pro_managed_pieces(fake_home, state_dir):
    cursor_env(fake_home)
    harnesses.bootstrap_apply("cursor", approve=True, state_dir=state_dir)
    result = harnesses.bootstrap_remove("cursor", state_dir=state_dir)
    assert result["ok"] is True

    assert not (fake_home / ".cursor" / "skills" / "aethermind-pro" / "SKILL.md").exists()
    mcp = json.loads((fake_home / ".cursor" / "mcp.json").read_text(encoding="utf-8"))
    assert "aethermind_pro" not in mcp["mcpServers"]
    assert "user_server" in mcp["mcpServers"]
    hooks = json.loads((fake_home / ".cursor" / "hooks.json").read_text(encoding="utf-8"))
    assert all("--harness cursor" not in e["command"] for e in hooks["hooks"]["sessionStart"])
    assert any("own-hook.py" in e["command"] for e in hooks["hooks"]["sessionStart"])

    disc = harnesses.discover(state_dir=state_dir)
    cursor = next(h for h in disc["harnesses"] if h["name"] == "cursor")
    assert cursor["integrated"] is False


def test_discover_shows_integrated_depth(fake_home, state_dir):
    (fake_home / ".claude").mkdir()
    harnesses.bootstrap_apply("claude_code", approve=True, state_dir=state_dir)
    disc = harnesses.discover(state_dir=state_dir)
    claude = next(h for h in disc["harnesses"] if h["name"] == "claude_code")
    assert claude["integrated"] is True
    assert claude["depth"]["current_tier"] == 4
