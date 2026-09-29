"""Mosaic, the design system code elements can opt into, is vendored and wired into the sandbox.

An element that names a look (``data-look``), uses Mosaic's classes or calls ``Mosaic.`` gets the
core CSS, that look's CSS, the script, the look's fonts and the icon weights the look draws with.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
VENDOR = REPO_ROOT / "static" / "vendor" / "mosaic"


def test_mosaic_build_is_vendored_with_every_look() -> None:
    meta = json.loads((VENDOR / "mosaic.json").read_text(encoding="utf-8"))
    assert set(meta["looks"]) >= {"bauhaus", "almanac", "signal", "pixel", "os7"}
    for look in meta["looks"]:
        assert (VENDOR / "looks" / f"{look}.css").is_file(), look
    assert (VENDOR / "core.css").is_file()
    # Inlined into a <script>, so it must not close the tag.
    assert "</script" not in (VENDOR / "mosaic.js").read_text(encoding="utf-8")


def test_both_sandbox_templates_point_at_mosaic() -> None:
    for name in ("panels_compose.html", "panels_editor.html"):
        tpl = (REPO_ROOT / "templates" / name).read_text(encoding="utf-8")
        for key in ("mosaic_core", "mosaic_js", "mosaic_json", "mosaic_looks"):
            assert f"{key}:" in tpl, f"{name} lacks {key}"


def test_decorate_reads_the_look_for_fonts_and_icons() -> None:
    js = (REPO_ROOT / "static" / "panels" / "decorate.js").read_text(encoding="utf-8")
    assert "mosaic.icons.indexOf(ICON_LIBS[lib.name])" in js, "icon weights must come from the look"
    assert "var fontProbe = mosaic ? probe" in js, "fonts must be scanned in the look's CSS too"
