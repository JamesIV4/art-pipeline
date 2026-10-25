# Origin: S:/Repos/OpenXcom-Extended-3D/art/team/guns_v2/lib/to_webp.py (imported 2026-10-25)
# Changed: header only
"""Convert baked PNG maps to 8-bit lossless WebP (system Python + Pillow), verifying the pixels survive exactly.
python to_webp.py a.png b.png ...   -> writes a.webp, b.webp next to them (never overwrites) and prints JSON {png: webp}."""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

out = {}
for p in sys.argv[1:]:
    p = Path(p)
    w = p.with_suffix(".webp")
    im = Image.open(p)
    im = im.convert("RGB") if im.mode not in ("RGB",) else im
    if im.mode != "RGB" or np.asarray(im).dtype != np.uint8:
        raise SystemExit(f"{p}: not 8-bit RGB")
    if not w.exists():
        im.save(w, "WEBP", lossless=True, quality=100, method=6, exact=True)
    back = Image.open(w).convert("RGB")
    assert np.array_equal(np.asarray(back), np.asarray(im)), f"{w}: lossless round trip failed"
    out[str(p)] = str(w)
print("WEBP", json.dumps(out))
