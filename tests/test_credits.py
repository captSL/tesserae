"""The Credits page lists everything Tesserae ships that someone else made, and cannot drift.

static/credits/attributions.json is the one list; scripts/gen_credits.py renders it (with the
Python packages) as docs/credits.md, and Tesserae Cloud builds its Credits page from the same file.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = json.loads((ROOT / "static/credits/attributions.json").read_text(encoding="utf-8"))


def test_every_bundled_font_is_credited_with_its_copyright() -> None:
    folders = {d.name for d in (ROOT / "plugins/fonts_core/static").iterdir() if d.is_dir()}
    # A family whose dir is elsewhere is bundled by Tesserae Cloud, which builds its Credits page
    # from this same file; it is credited here but need not be in fonts_core.
    local = [f for f in DOC["fonts"] if f["dir"].startswith("plugins/fonts_core/static/")]
    credited = {Path(f["dir"]).name for f in local}
    assert folders == credited, (
        f"add these to attributions.json (scripts/gen_credits.py --fonts): {sorted(folders - credited)}"
    )
    for f in DOC["fonts"]:
        assert f["copyright"], f"{f['family']} has no copyright notice"


def test_every_vendored_library_is_credited() -> None:
    covered = [p for lib in DOC["libraries"] + DOC["icons"] for p in lib["files"]]
    for item in sorted((ROOT / "static/vendor").iterdir()):
        rel = f"static/vendor/{item.name}"
        assert any(c == rel or c.startswith(rel + "/") for c in covered), (
            f"{rel} has no entry in attributions.json"
        )


def test_docs_page_is_current() -> None:
    spec = importlib.util.spec_from_file_location("gen_credits", ROOT / "scripts/gen_credits.py")
    assert spec and spec.loader
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)
    py = json.loads((ROOT / "static/credits/python.json").read_text(encoding="utf-8"))
    want = gen.render(DOC, py)
    assert (ROOT / "docs/credits.md").read_text(encoding="utf-8") == want, (
        "run scripts/gen_credits.py"
    )
