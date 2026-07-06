"""Customer-owned state, bounded audit, and export contract.

Controlling docs: docs/PRIVACY_AND_AUDIT.md lines 3-12,
docs/plans/customer-state-source-contract-spec.md lines 102-211,
docs/plans/source-contract-test-spec.md required test group 9.
"""

import json

from aethermind_pro import config, export, roots
from aethermind_pro.audit import AuditLog, build_event
from aethermind_pro.roots import RootsRegistry


def test_state_dir_is_explicit_no_operator_path(monkeypatch, tmp_path):
    resolved = config.resolve_state_dir(str(tmp_path / "explicit"))
    assert str(tmp_path) in str(resolved)
    monkeypatch.setenv(config.ENV_STATE_DIR, str(tmp_path / "fromenv"))
    assert "fromenv" in str(config.resolve_state_dir())


def test_audit_event_is_bounded_and_redacted():
    event = build_event("workspace_investigated", component="investigate",
                        root_id="root-abc", verdict_status="proceed")
    assert event["redaction"] == {
        "raw_project_content_included": False,
        "secrets_included": False,
        "private_paths_included": False,
        "arbitrary_snippets_included": False,
    }
    # No raw path-like fields are present.
    assert "/" not in (event.get("root_id") or "")


def test_audit_append_and_tail(state_dir):
    log = AuditLog(state_dir)
    log.record_event("workspace_investigated", component="investigate")
    log.record_event("trust_reviewed", component="trust")
    tail = log.tail()
    assert len(tail) == 2
    assert tail[-1]["event_name"] == "trust_reviewed"


def test_roots_registry_uses_hashed_id(code_repo, state_dir):
    path, err = roots.resolve_root(code_repo)
    assert err is None
    record = roots.build_root_record(path)
    assert record["root_id"].startswith("root-")
    assert code_repo not in record["root_id"]
    registry = RootsRegistry(state_dir)
    registry.add(record)
    assert any(r["root_id"] == record["root_id"] for r in registry.list())
    assert registry.remove(record["root_id"]) is True


def test_export_always_available(state_dir, tmp_path):
    # Export of customer-owned state is unconditional in the source-available build.
    out_file = tmp_path / "export.json"
    result = export.export_state(str(out_file), state_dir=state_dir)
    assert result["ok"] is True
    assert result["always_available"] is True
    assert out_file.exists()
    bundle = json.loads(out_file.read_text())
    assert bundle["customer_owned_artifacts"] is True


def test_export_excludes_sensitive_content(state_dir):
    result = export.export_state(None, state_dir=state_dir)
    for excluded in ("secrets", "raw_project_content", "private_operator_paths", "active_product_code"):
        assert excluded in result["excluded"]
