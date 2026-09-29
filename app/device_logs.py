"""Device log upload and failure reporting (``notes/device-log-upload-plan.md``,
"Protocol v1").

Native firmware advertises ``{"logs": {"schema": 1, "ring_bytes": N}}`` on
every status beat and, after a latched failure, a ``diag`` object with a
per-failure ``id``. The server answers a status with top-level
``{"logs": {"upload": true}}`` while the operator has collection running or
when the beat carried a new ``diag``, and the firmware then POSTs its log as
``text/plain`` to ``/api/v1/device/<id>/log``.

This module holds the body parsing and the gating decision; storage lives in
:mod:`app.state.device_logs`.
"""

from __future__ import annotations

import json
from typing import Any

# Values the firmware may send; anything else is kept as sent (capped) so a
# newer firmware's reason still reads in the timeline.
PAINT_ERRORS = ("init_failed", "ready_timeout", "refresh_timeout")
RESET_REASONS = ("brownout", "panic", "watchdog")

_UINT32_MAX = 0xFFFFFFFF
_REASON_CAP = 64


def _body(payload: bytes | str | dict[str, Any]) -> dict[str, Any] | None:
    if isinstance(payload, (bytes, bytearray, str)):
        try:
            body = json.loads(payload)
        except (ValueError, TypeError):
            return None
    else:
        body = payload
    return body if isinstance(body, dict) else None


def _int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def advertised_logs_schema(payload: bytes | str | dict[str, Any]) -> int | None:
    """The log-upload schema a device advertises in the ``logs`` capability
    object of its heartbeat (``{"logs": {"schema": 1}}``), or None."""
    body = _body(payload)
    if body is None:
        return None
    cap = body.get("logs")
    if not isinstance(cap, dict):
        return None
    return _int(cap.get("schema"))


def parse_diag(payload: bytes | str | dict[str, Any]) -> dict[str, Any] | None:
    """The ``diag`` failure report from a heartbeat body, or None.

    ``id`` is required (a uint32): without it a re-sent report can't be told
    from a new one, so the report is ignored. ``paint_error`` and ``reset``
    are optional strings, ``at`` the epoch of the latch (0 when the device
    clock was unknown)."""
    body = _body(payload)
    if body is None:
        return None
    diag = body.get("diag")
    if not isinstance(diag, dict):
        return None
    diag_id = _int(diag.get("id"))
    if diag_id is None or not 0 <= diag_id <= _UINT32_MAX:
        return None
    out: dict[str, Any] = {"id": diag_id}
    for key in ("paint_error", "reset"):
        val = diag.get(key)
        if isinstance(val, str) and val.strip():
            out[key] = val.strip()[:_REASON_CAP]
    at = _int(diag.get("at"))
    if at is not None and at >= 0:
        out["at"] = at
    return out


def describe_diag(diag: dict[str, Any]) -> str:
    """One readable line for the Events row and the device page, e.g.
    ``paint failed: refresh_timeout`` or ``reset: brownout``."""
    parts = []
    if diag.get("paint_error"):
        parts.append(f"paint failed: {diag['paint_error']}")
    if diag.get("reset"):
        parts.append(f"reset: {diag['reset']}")
    return "; ".join(parts) or "device reported a failure"


def logs_capable(
    device_id: str,
    status_cache: dict[str, dict[str, Any]] | None,
    facts: Any,
) -> bool:
    """Whether this device advertised ``logs.schema >= 1``. The live status
    cache first (sticky across beats), then the persisted device facts, so a
    server restart doesn't forget the capability until the next wake."""
    schema: Any = None
    entry = (status_cache or {}).get(device_id)
    if isinstance(entry, dict):
        schema = entry.get("logs_schema")
    if schema is None and facts is not None:
        fact = facts.get(device_id)
        if isinstance(fact, dict):
            schema = fact.get("logs_schema")
    return isinstance(schema, int) and not isinstance(schema, bool) and schema >= 1
