"""The canvas editor, the MCP API and the template marketplace are regular
features: on by default, each switchable off in Settings (Features card) or
pinned by ``TESSERAE_EXPERIMENT_<NAME>``, with a saved choice honoured.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from flask import Flask

from app import experiments, heartbeat
from app.main import REPO_ROOT, create_app

_FEATURES = ("composer", "mcp", "templates")


@pytest.fixture
def app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Flask:
    for name in _FEATURES:
        monkeypatch.delenv(f"TESSERAE_EXPERIMENT_{name.upper()}", raising=False)
    a = create_app(
        testing=False,
        data_root=tmp_path,
        plugins_dir=REPO_ROOT / "plugins",
        renderers_dir=REPO_ROOT / "renderers",
        devices_dir=REPO_ROOT / "devices",
    )
    a.config["TESTING"] = True
    return a


def _sign_in(client: Any) -> None:
    client.post("/setup", data={"password": "abcdefgh", "password_confirm": "abcdefgh"})


# -- resolution ---------------------------------------------------------


@pytest.mark.parametrize("name", _FEATURES)
def test_on_by_default_with_no_saved_value(app: Flask, name: str) -> None:
    assert name not in (app.config["SETTINGS_STORE"].get_section("experiments") or {})
    with app.app_context():
        assert experiments.is_enabled(name) is True
    assert experiments.resolve(None, name) is True


@pytest.mark.parametrize("name", _FEATURES)
def test_env_var_zero_turns_each_off(
    app: Flask, monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    monkeypatch.setenv(f"TESSERAE_EXPERIMENT_{name.upper()}", "0")
    app.config["SETTINGS_STORE"].patch_section("experiments", {name: True})
    with app.app_context():
        assert experiments.is_enabled(name) is False
        assert experiments.env_override(name) is False


@pytest.mark.parametrize("name", _FEATURES)
def test_saved_false_keeps_it_off(app: Flask, name: str) -> None:
    app.config["SETTINGS_STORE"].patch_section("experiments", {name: False})
    with app.app_context():
        assert experiments.is_enabled(name) is False


def test_routes_follow_the_defaults(app: Flask) -> None:
    client = app.test_client()
    _sign_in(client)
    # composer: the canvas editor's blueprint answers.
    assert client.get("/pages/canvas/catalog.json").status_code == 200
    # mcp: loopback reaches the API with no token.
    assert client.get("/api/mcp/catalog").status_code == 200
    # templates: Browse offers the Templates type.
    assert '"templates_enabled": true' in client.get("/plugins/browse").get_data(as_text=True)


# -- MCP stays authenticated ----------------------------------------------

_REMOTE = {"REMOTE_ADDR": "192.168.1.50"}


def test_mcp_remote_caller_needs_the_token(app: Flask) -> None:
    assert app.test_client().get("/api/mcp/catalog", environ_base=_REMOTE).status_code == 401


def test_mcp_forwarded_loopback_is_not_trusted(app: Flask) -> None:
    """A LAN client claiming ``X-Forwarded-For: 127.0.0.1`` must not pass for
    a local caller (ProxyFix would otherwise rewrite remote_addr to it)."""
    client = app.test_client()
    resp = client.get(
        "/api/mcp/catalog", environ_base=_REMOTE, headers={"X-Forwarded-For": "127.0.0.1"}
    )
    assert resp.status_code == 401
    # Same for a proxy on this host relaying a remote caller.
    resp = client.get("/api/mcp/catalog", headers={"X-Forwarded-For": "203.0.113.9"})
    assert resp.status_code == 401
    resp = client.get("/api/mcp/catalog", headers={"X-Real-IP": "203.0.113.9"})
    assert resp.status_code == 401


def test_mcp_token_still_works_through_a_proxy(app: Flask) -> None:
    from app.mcp_api import rotate_token

    token = rotate_token(app.config["SETTINGS_STORE"])
    resp = app.test_client().get(
        "/api/mcp/catalog",
        environ_base=_REMOTE,
        headers={"X-Forwarded-For": "203.0.113.9", "Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200


# -- agent watching stays quiet without an agent --------------------------


def test_no_activity_poll_until_an_agent_connects(app: Flask) -> None:
    client = app.test_client()
    _sign_in(client)
    assert 'id="agent-follow"' not in client.get("/send").get_data(as_text=True)


def test_heartbeat_mcp_means_an_agent_connected(app: Flask) -> None:
    store = app.config["SETTINGS_STORE"]
    assert heartbeat._features(app, store, [])["mcp"] is False
    from app import mcp_bridge

    mcp_bridge.record_request(store, "tesserae-mcp/0.18.0")
    assert heartbeat._features(app, store, [])["mcp"] is True
    store.patch_section("experiments", {"mcp": False})
    assert heartbeat._features(app, store, [])["mcp"] is False


# -- no "experimental" in the UI -------------------------------------------


def test_canvas_editor_has_no_experimental_wording(app: Flask) -> None:
    client = app.test_client()
    _sign_in(client)
    resp = client.post("/pages/new", data={"name": "Mine", "layout_kind": "canvas"})
    assert resp.status_code == 302 and "/pages/canvas/c/" in resp.location
    html = client.get(resp.location).get_data(as_text=True)
    assert "experimental" not in html.lower()
    assert "panels-disclaimer" not in html
    assert "<title>Canvas editor, Tesserae</title>" in html


def test_dashboards_create_form_offers_the_canvas(app: Flask) -> None:
    client = app.test_client()
    _sign_in(client)
    html = client.get("/pages").get_data(as_text=True)
    assert '<option value="canvas">Freeform canvas</option>' in html


def test_calibration_edge_handling_is_not_labelled_experimental(app: Flask) -> None:
    client = app.test_client()
    _sign_in(client)
    resp = client.post("/settings/devices/add", data={"id": "esp32_demo", "kind": "esp32_client"})
    assert resp.status_code == 302
    html = client.get("/settings/devices/esp32_demo/calibration").get_data(as_text=True)
    assert "<summary>Edge handling</summary>" in html
    assert "Experimental: edge handling" not in html
    assert "dx-palette-experimental" not in html


def test_settings_features_card_replaces_experiments(app: Flask) -> None:
    client = app.test_client()
    _sign_in(client)
    html = client.get("/settings/system").get_data(as_text=True)
    assert 'id="features"' in html
    assert "Experiments" not in html
    assert "Experimental." not in html
