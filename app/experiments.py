"""Feature switches for optional features, all on by default.

These began life as experiment flags and have since graduated; the module keeps
its name (and the ``experiments`` settings section and env var prefix) so a
saved choice and an operator's environment carry over unchanged.

Resolution order for a switch: the ``TESSERAE_EXPERIMENT_<NAME>`` env var wins
(so a deployment can force it on/off without editing settings.json, and tests
can flip one per-process); otherwise an explicit value in the ``experiments``
settings section (written only when someone flips the switch in Settings, so an
install that never touched it has no value and gets the default); otherwise the
switch's built-in default in ``_DEFAULTS``, which is ON for every switch.

Route guards call :func:`is_enabled` per request, so a settings change takes
effect with no restart.

Env var convention: ``TESSERAE_EXPERIMENT_<NAME_UPPER>`` (e.g.
``TESSERAE_EXPERIMENT_MCP=0`` turns the MCP API off for the deployment).

mypy --strict applies to this module, see pyproject.toml.
"""

from __future__ import annotations

import os
from typing import Any

from flask import current_app

_TRUTHY = frozenset({"1", "true", "yes", "on"})

# Built-in defaults for switches with no explicit env/settings value. Every
# catalogued feature is on; absent names default off.
_DEFAULTS: dict[str, bool] = {
    # The canvas (freeform) dashboard editor, reached from Dashboards by
    # creating a "Freeform canvas" dashboard or opening one.
    "composer": True,
    # MCP API (app.mcp_api): lets an agent build canvas dashboards. Remote
    # callers need the token from Settings → System → MCP; only a direct
    # loopback caller is trusted without one.
    "mcp": True,
    # Template marketplace (share + browse community dashboard templates via
    # api.tesserae.ink). Gates the Share dialog, the share routes, and the
    # Browse Templates tab in one switch, and stays inert until the master
    # online-features opt-in is on (see REQUIRES_ONLINE).
    "templates": True,
}


# Settings → System → Features card: one row per switch. Kept here beside
# _DEFAULTS so adding a switch and describing it happen in the same file.
CATALOG: tuple[dict[str, str], ...] = (
    {
        "name": "composer",
        "label": "Canvas editor",
        "description": (
            "Freeform dashboards you lay out by dragging widgets, text and shapes "
            "anywhere on the panel. Pick Freeform canvas when creating a dashboard."
        ),
    },
    {
        "name": "mcp",
        "label": "MCP API (agent access)",
        "description": (
            "Lets an AI agent build canvas dashboards through /api/mcp. Remote "
            "agents need the token from the MCP card below."
        ),
    },
    {
        "name": "templates",
        "label": "Template marketplace",
        "description": (
            "Share dashboards to the community catalog and install templates "
            "from Browse. Submissions are reviewed before they go public."
        ),
    },
)


# Switches whose feature is hosted on api.tesserae.ink, so being on does
# nothing until the master online-features opt-in is also on. The Settings row
# says so rather than leaving the toggle a silent no-op (#224).
REQUIRES_ONLINE: frozenset[str] = frozenset({"templates"})


def _env_flag(name: str) -> bool | None:
    """The env override for ``name``, or None when the var is unset."""
    raw = os.environ.get(f"TESSERAE_EXPERIMENT_{name.upper()}")
    if raw is None:
        return None
    return raw.strip().lower() in _TRUTHY


def env_override(name: str) -> bool | None:
    """The forced env-var value for ``name`` (None = not forced). The Settings
    card disables a row's toggle when a deployment pins the flag this way."""
    return _env_flag(name)


def resolve(settings: Any, name: str) -> bool:
    """Whether ``name`` is on, given a settings store (or None). The shared
    resolution behind :func:`is_enabled`, usable without an app context (the
    heartbeat builds its payload off-request): env var, then an explicit
    ``experiments`` settings value, then the built-in default."""
    env = _env_flag(name)
    if env is not None:
        return env
    if settings is not None:
        try:
            section = settings.get_section("experiments") or {}
        except Exception:
            section = {}
        if isinstance(section, dict) and name in section:
            return bool(section[name])
    return _DEFAULTS.get(name, False)


def is_enabled(name: str) -> bool:
    """True when feature ``name`` is switched on. Env var wins, then an
    explicit ``experiments`` settings value, then the built-in default."""
    return resolve(current_app.config.get("SETTINGS_STORE"), name)
