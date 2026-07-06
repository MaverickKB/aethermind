"""Optional UI surfaces and platform status contract.

tracker and admin-ui are optional visual surfaces; core commands never require them.
Platform status reports where the source-available build runs.
"""

from aethermind_pro import coordinator, investigate, platform


def test_tracker_is_optional_not_required():
    result = platform.tracker()
    assert result["status"] == "optional_not_required_for_core"
    assert result["required_for_core"] is False


def test_admin_ui_is_optional_not_required():
    result = platform.admin_ui()
    assert result["status"] == "optional_not_required_for_core"
    assert result["required_for_core"] is False


def test_platform_status_reports_targets():
    result = platform.platform_status()
    assert "macos" in result["primary_targets"]
    assert "linux" in result["primary_targets"]


def test_core_commands_do_not_require_optional_surfaces(code_repo, state_dir):
    # investigate / status / coordinate must work with no tracker/admin-ui present.
    inv = investigate.investigate(code_repo, state_dir=state_dir)
    assert inv["ok"] is True
    st = coordinator.status(code_repo, state_dir=state_dir)
    assert st["ok"] is True
    co = coordinator.coordinate(code_repo, state_dir=state_dir)
    assert co["ok"] is True
