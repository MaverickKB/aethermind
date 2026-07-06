"""Shared bounded response builders.

All command output is JSON by default (docs/PRO_SYSTEM_CONTRACT.md, design choice 2).
Errors are always JSON with an honest reason and a next action
(docs/plans/source-contract-first-slice-spec.md lines 182-200).
"""

from __future__ import annotations

from typing import Any, Dict

from . import evidence


def ok(command: str, **fields: Any) -> Dict[str, Any]:
    result: Dict[str, Any] = {"ok": True, "command": command}
    result.update(fields)
    return result


def error(command: str, code: str, message: str, next_action: str) -> Dict[str, Any]:
    return {
        "ok": False,
        "command": command,
        "error": {"code": code, "message": message, "next_action": next_action},
        "evidence": evidence.error_evidence(),
    }
