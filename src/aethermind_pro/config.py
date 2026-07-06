"""Explicit config and state-path resolution.

Derived from docs/PRO_SYSTEM_CONTRACT.md (customer-owned local state), the
non-negotiable design choice that hidden cwd assumptions are rejected, and the
non-loss invariant that no Pro artifact may require private operator roots
(docs/PRODUCT_DEFINITION.md lines 63-70).

State location precedence is explicit and never hard-codes an operator path.
"""

from __future__ import annotations

import os
import platform
from pathlib import Path

ENV_STATE_DIR = "AETHERMIND_PRO_STATE_DIR"


def resolve_state_dir(explicit: "str | os.PathLike | None" = None) -> Path:
    """Resolve the customer-owned Pro state directory without hidden assumptions.

    Precedence: explicit argument > AETHERMIND_PRO_STATE_DIR env var > platform
    default under the current user's home. No private operator path is ever assumed.
    """
    if explicit:
        return Path(explicit).expanduser().resolve()

    env_value = os.environ.get(ENV_STATE_DIR)
    if env_value:
        return Path(env_value).expanduser().resolve()

    home = Path.home()
    system = platform.system().lower()
    if system == "darwin":
        base = home / "Library" / "Application Support" / "aethermind-pro"
    elif system == "windows":
        base = Path(os.environ.get("APPDATA", str(home))) / "aethermind-pro"
    else:
        xdg = os.environ.get("XDG_STATE_HOME")
        base = (Path(xdg) if xdg else home / ".local" / "state") / "aethermind-pro"
    return base.resolve()


def ensure_state_dir(explicit: "str | os.PathLike | None" = None) -> Path:
    """Resolve and create the Pro state directory."""
    state_dir = resolve_state_dir(explicit)
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir


def current_platform() -> str:
    """Return a bounded platform label: macos|linux|windows|unknown."""
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    if system == "linux":
        return "linux"
    if system == "windows":
        return "windows"
    return "unknown"
