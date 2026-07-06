"""Public plugin dependency boundary contract.

Controlling docs: docs/SUBSTRATE_OWNERSHIP.md lines 17-23,
docs/AETHERMIND_PRIMITIVE_MCP.md, docs/LOCAL_COORDINATOR_ARCHITECTURE.md.
"""

from aethermind_pro import plugins


def test_plugin_absent_by_default():
    result = plugins.detect()
    assert result["ok"] is True
    assert result["plugin"]["present"] is False
    assert result["vendored_as_pro_source"] is False
    assert result["pro_state_separate_from_plugin"] is True


def test_compatible_plugin_is_used():
    result = plugins.detect(installed={"version": "0.1.1", "compatible": True})
    assert result["plugin"]["state"] == "compatible"


def test_install_needs_approval():
    result = plugins.install(approve=False)
    assert result["action"] == "needs_approval"
    assert result["requires_user_approval"] is True


def test_install_degrades_without_network():
    result = plugins.install(approve=True, network_available=False)
    assert result["action"] == "degraded_network_unavailable"
    assert result["network_required"] is True


def test_use_existing_compatible_without_fetch():
    result = plugins.install(installed={"version": "0.1.1", "compatible": True})
    assert result["action"] == "use_existing_compatible"


def test_repair_requires_approval():
    result = plugins.repair(installed={"version": "0.0.1", "compatible": False})
    assert result["action"] == "needs_approval"


def test_never_vendors_as_source():
    # The dependency boundary fact must be explicit in output.
    assert plugins.detect()["vendored_as_pro_source"] is False
