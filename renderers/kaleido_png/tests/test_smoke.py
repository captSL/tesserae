"""kaleido_png renderer smoke: composition PNG in, Kaleido 3 colour PNG out.

Confirms the loader registers the renderer, the manifest says what the
device service and the KOReader plugin rely on (PNG, dedicated to the
``kaleido3`` gamut), output is 24-bit RGB with every channel on the
16-level ramp, colour survives (it is not a greyscale PNG), the dither
modes behave, and a landscape composition is turned onto a portrait
reader's buffer.
"""

from __future__ import annotations

import io

import pytest
from PIL import Image

from app.main import REPO_ROOT
from app.quantizer import KALEIDO3_CHANNEL_LEVELS
from app.renderer_loader import discover
from app.state.page_store import Panel

_LEVELS = set(KALEIDO3_CHANNEL_LEVELS)


@pytest.fixture
def kaleido_png(tmp_path):
    registry = discover(
        REPO_ROOT / "renderers",
        schema_path=REPO_ROOT / "schema" / "renderer.schema.json",
        data_root=tmp_path,
    )
    assert registry.errors == [], registry.errors
    renderer = registry.get("kaleido_png")
    assert renderer is not None
    return renderer


@pytest.fixture
def composition_png() -> bytes:
    """A 200x100 colour gradient: red rises left to right, green top to
    bottom, blue fixed mid-way. Every channel has tonal content, so a
    per-channel dither regression (a channel collapsing to two levels,
    or chroma being dropped) shows up in the level counts."""
    img = Image.new("RGB", (200, 100))
    for y in range(100):
        for x in range(200):
            img.putpixel((x, y), (x * 255 // 199, y * 255 // 99, 128))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _png_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _channel_levels(out: Image.Image) -> list[set[int]]:
    assert out.mode == "RGB", f"expected 24-bit RGB, got {out.mode!r}"
    return [set(band.getdata()) for band in out.split()]


def test_manifest_is_a_png_dedicated_to_kaleido3(kaleido_png) -> None:
    """``extension`` is what ``/frame`` echoes as ``format``; ``gamuts``
    is what ``renderer_id_for_gamut`` reads to pin a colour reader here."""
    assert kaleido_png.extension == "png"
    assert kaleido_png.mime == "image/png"
    assert kaleido_png.orientation == "composition"
    assert kaleido_png.retain is False
    assert kaleido_png.manifest["gamuts"] == ["kaleido3"]
    assert kaleido_png.topic == "tesserae/koreader/frame/png"


def test_output_is_rgb_with_16_levels_per_channel(kaleido_png, composition_png) -> None:
    panel = Panel(w=200, h=100, gamut="kaleido3")
    artifact = kaleido_png.transform(
        composition_png, panel=panel, settings=kaleido_png.settings_defaults()
    )
    out = Image.open(io.BytesIO(artifact))
    assert out.size == (200, 100)
    r, g, b = _channel_levels(out)
    for levels in (r, g, b):
        assert levels <= _LEVELS, sorted(levels - _LEVELS)[:8]
    # Full-range ramps through 16 levels should use most of the ramp, not
    # collapse to black + white.
    assert len(r) >= 8 and len(g) >= 8
    # The constant 128 blue channel dithers between its two neighbours
    # (119 and 136) and nowhere else; if the renderer had gone greyscale
    # the blue channel would carry the red/green ramps instead.
    assert b <= {119, 136}, sorted(b)


def test_none_dither_snaps_each_channel_to_nearest_level(kaleido_png, composition_png) -> None:
    panel = Panel(w=200, h=100, gamut="kaleido3")
    settings = {**kaleido_png.settings_defaults(), "dither": "none"}
    artifact = kaleido_png.transform(composition_png, panel=panel, settings=settings)
    out = Image.open(io.BytesIO(artifact))
    r, g, b = _channel_levels(out)
    assert r <= _LEVELS and g <= _LEVELS
    # 128 is nearer 136 than 119, so with no diffusion the whole channel
    # snaps to one level.
    assert b == {136}, sorted(b)


def test_colour_survives_a_flat_fill(kaleido_png) -> None:
    """A solid on-ramp colour comes back as itself: the renderer keeps
    chroma rather than taking luminance the way the grey renderers do."""
    img = Image.new("RGB", (64, 32), (221, 34, 170))  # 13, 2, 10 on the ramp
    panel = Panel(w=64, h=32, gamut="kaleido3")
    artifact = kaleido_png.transform(
        _png_bytes(img), panel=panel, settings=kaleido_png.settings_defaults()
    )
    out = Image.open(io.BytesIO(artifact))
    assert out.mode == "RGB"
    assert set(out.getdata()) == {(221, 34, 170)}


def test_landscape_composition_rotated_onto_portrait_buffer(kaleido_png) -> None:
    """A landscape dashboard composed at 200x100 for a reader whose
    framebuffer is 100x200 portrait is turned CW onto that buffer, so the
    plugin blits it full screen without squashing."""
    img = Image.new("RGB", (200, 100), "white")
    img.paste((255, 0, 0), (100, 0, 200, 100))
    panel = Panel(w=200, h=100, native_w=100, native_h=200, native_declared=True, gamut="kaleido3")
    artifact = kaleido_png.transform(
        _png_bytes(img), panel=panel, settings=kaleido_png.settings_defaults()
    )
    out = Image.open(io.BytesIO(artifact))
    assert out.size == (100, 200)
    # Composition left (white) lands at the top, right (red) at the bottom.
    assert out.getpixel((50, 10)) == (255, 255, 255)
    assert out.getpixel((50, 190)) == (255, 0, 0)


def test_no_native_block_keeps_composition_dims(kaleido_png, composition_png) -> None:
    panel = Panel(w=200, h=100, gamut="kaleido3")
    artifact = kaleido_png.transform(
        composition_png, panel=panel, settings=kaleido_png.settings_defaults()
    )
    assert Image.open(io.BytesIO(artifact)).size == (200, 100)


def test_payload_points_at_png_artifact(kaleido_png) -> None:
    out = kaleido_png.payload("abc123", "http://tesserae.local/", settings={})
    assert out == {"url": "http://tesserae.local/renders/abc123.png"}
