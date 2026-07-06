"""Layer inspection and soft user actions contract.

Controlling docs: docs/PRO_SYSTEM_CONTRACT.md line 35, docs/PRIVACY_AND_AUDIT.md line 9,
docs/plans/local-coordinator-source-contract-spec.md.
"""

from aethermind_pro import investigate, layers


def test_inspect_no_raw_content(code_repo, state_dir):
    investigate.investigate(code_repo, state_dir=state_dir)
    result = layers.inspect(code_repo, state_dir=state_dir)
    assert result["ok"] is True
    assert result["raw_content_included"] is False
    assert result["count"] >= 1
    first = result["layers"][0]
    for key in ("layer_id", "kind", "created_at", "mark"):
        assert key in first


def test_mark_does_not_rewrite_store(code_repo, state_dir):
    investigate.investigate(code_repo, state_dir=state_dir)
    inspected = layers.inspect(code_repo, state_dir=state_dir)
    layer_id = inspected["layers"][0]["layer_id"]
    result = layers.mark(code_repo, layer_id, "archived", state_dir=state_dir)
    assert result["ok"] is True
    assert result["store_rewritten"] is False
    again = layers.inspect(code_repo, state_dir=state_dir)
    marked = [l for l in again["layers"] if l["layer_id"] == layer_id][0]
    assert marked["mark"] == "archived"


def test_invalid_mark_rejected(code_repo, state_dir):
    investigate.investigate(code_repo, state_dir=state_dir)
    inspected = layers.inspect(code_repo, state_dir=state_dir)
    layer_id = inspected["layers"][0]["layer_id"]
    # 'deleted' is a legacy hard label and is not a preferred customer mark.
    result = layers.mark(code_repo, layer_id, "deleted", state_dir=state_dir)
    assert result["ok"] is False
    assert result["error"]["code"] == "invalid_mark"


def test_marks_are_only_preferred_terms():
    assert set(layers.MARKS) == {"hidden", "archived", "quarantined", "stale"}
    for legacy in ("deleted", "ignored", "superseded"):
        assert legacy not in layers.MARKS


def test_remove_requires_explicit_confirmation(code_repo, state_dir):
    investigate.investigate(code_repo, state_dir=state_dir)
    inspected = layers.inspect(code_repo, state_dir=state_dir)
    layer_id = inspected["layers"][0]["layer_id"]
    result = layers.remove(code_repo, layer_id, confirm=False, state_dir=state_dir)
    assert result["performed"] is False
    assert result["requires_explicit_confirmation"] is True


def test_remove_with_confirm_does_not_rewrite_store(code_repo, state_dir):
    investigate.investigate(code_repo, state_dir=state_dir)
    inspected = layers.inspect(code_repo, state_dir=state_dir)
    layer_id = inspected["layers"][0]["layer_id"]
    result = layers.remove(code_repo, layer_id, confirm=True, state_dir=state_dir)
    assert result["performed"] is True
    assert result["store_rewritten"] is False
    assert result["method"] == "soft_quarantine"


def test_browse_groups_by_kind(code_repo, state_dir):
    investigate.investigate(code_repo, state_dir=state_dir)
    result = layers.browse(state_dir=state_dir)
    assert result["ok"] is True
    assert isinstance(result["directory_groups"], dict)
