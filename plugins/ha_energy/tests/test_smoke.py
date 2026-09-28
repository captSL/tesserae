"""Smoke tests for the Home Assistant Energy widget."""

from __future__ import annotations

import importlib.util
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

_SERVER_PATH = Path(__file__).resolve().parent.parent / "server.py"


def _load_server() -> Any:
    """Load this plugin's ``server.py`` under a unique module name.

    Every plugin ships a module called ``server``; a bare ``import server``
    here would hand back whichever plugin's module a sibling suite imported
    first (pytest collects ``plugins/`` alphabetically, so calendar_day's).
    """
    spec = importlib.util.spec_from_file_location("ha_energy_server_under_test", _SERVER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


server = _load_server()


def test_widget_clock_uses_app_timezone() -> None:
    zone = ZoneInfo("Europe/Berlin")

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            assert tz is zone
            return cls(2026, 9, 28, 20, 5, tzinfo=tz)

    core = MagicMock()
    core.get_states.return_value = []
    registry = MagicMock()
    registry.get.return_value = SimpleNamespace(server_module=core)
    app = SimpleNamespace(config={"PLUGIN_REGISTRY": registry})

    with (
        patch.object(server, "current_app", app),
        patch.object(server, "datetime", FixedDateTime),
        patch.object(server, "app_timezone", return_value=zone),
    ):
        result = server.fetch(options={}, settings={}, ctx={})

    assert result["time"] == "20:05"
    assert result["hour"] == 20
