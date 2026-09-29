#!/usr/bin/env python3
"""Copy a built Mosaic (https://github.com/dmellok/tesserae-mosaic) into static/vendor/mosaic/.

    python3 scripts/sync_mosaic.py [~/Documents/Projects/tesserae-mosaic]

Run ``npm run build`` in the Mosaic checkout first. Copies dist/: core.css, looks/*.css,
mosaic.js, mosaic.json (which names the looks and the icon weights each draws with) and
specimens.json (six example dashboards).
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

SRC = (
    Path(sys.argv[1]).expanduser()
    if len(sys.argv) > 1
    else Path.home() / "Documents/Projects/tesserae-mosaic"
)
DIST = SRC / "dist"
DEST = Path(__file__).resolve().parent.parent / "static" / "vendor" / "mosaic"

if not (DIST / "mosaic.json").exists():
    sys.exit(f"no build in {DIST}; run `npm run build` there first")
if DEST.exists():
    shutil.rmtree(DEST)
(DEST / "looks").mkdir(parents=True)
for name in ("core.css", "mosaic.js", "mosaic.json", "specimens.json"):
    shutil.copy2(DIST / name, DEST / name)
for css in sorted((DIST / "looks").glob("*.css")):
    shutil.copy2(css, DEST / "looks" / css.name)
print(f"copied Mosaic into {DEST}")
