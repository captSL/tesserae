"""Smoke tests for the Home Assistant Energy widget."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import server


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
