"""Sets ONE palette row in the game's palette spec without touching any other line, then rebuilds
the palette textures (make_palette.py).

Origin: generalised from S:/Repos/trick-or-treat/art/team/<lane>/batch03/set_palette_row.py
(decor, monsters, characters_candy copies; imported 2026-10-25). Each lane owned one row; several
workers edit the palette concurrently, so this rewrites only that row's line, byte-for-byte.

    python <pipeline>/tools/set_palette_row.py --row 10 --owner bunting_cream \\
        "bunting_cream:#f6ead0" "glow_jack_shell:#a0400c:0.08" "glow_jack_face:#ffd864:0.05"
    python <pipeline>/tools/set_palette_row.py --row 12 --owner mon_green --append ...   # new row

Entries are "name:#rrggbb" or "name:#rrggbb:flicker" (a flicker value marks a glow cell).
--owner is the first cell name the row must already start with (guards against clobbering
another lane's row). --append adds the row when it does not exist yet (it must be the next row).
Never insert cells mid-row in a shipped palette: every later column shifts (see
techniques/palette-tint-uv.md). Run from the game root or set ART_GAME_ROOT.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipeline_paths as P  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--row", type=int, required=True)
    ap.add_argument("--owner", required=True, help="first cell name of the existing row")
    ap.add_argument("--append", action="store_true", help="append the row if it is missing")
    ap.add_argument("--no-build", action="store_true", help="skip make_palette.py")
    ap.add_argument("entries", nargs="+")
    a = ap.parse_args(argv)

    spec = P.path("palette_spec")
    text = spec.read_text(encoding="utf-8")
    data = json.loads(text)
    rows = data["rows"]
    grid = data.get("grid", P.setting("palette_grid"))
    if len(a.entries) > grid:
        raise SystemExit(f"{len(a.entries)} entries > grid {grid}")
    new_line = json.dumps(a.entries)
    if a.row < len(rows):
        old = rows[a.row]
        if not (old and old[0].split(":")[0] == a.owner):
            raise SystemExit(f"row {a.row} is not owned by '{a.owner}': {old}")
        old_line = json.dumps(old)
        if text.count(old_line) != 1:
            raise SystemExit(f"row text not found exactly once (reformat the spec one row per line): {old_line}")
        text = text.replace(old_line, new_line)
    elif a.append and a.row == len(rows):
        last = json.dumps(rows[-1])
        if text.count(last) != 1:
            raise SystemExit("could not locate the last row to append after")
        line_start = text.rfind("\n", 0, text.index(last)) + 1
        indent = text[line_start:text.index(last)]
        indent = indent if indent.strip() == "" else "  "
        text = text.replace(last, last + ",\n" + indent + new_line)
    else:
        raise SystemExit(f"row {a.row} does not exist ({len(rows)} rows); use --append for the next row")
    names = [e.split(":")[0] for r in json.loads(text)["rows"] for e in r]
    dup = {n for n in names if names.count(n) > 1}
    if dup:
        raise SystemExit(f"duplicate palette names: {sorted(dup)}")
    spec.write_text(text, encoding="utf-8", newline="\n")
    print("row", a.row, "->", a.entries)
    if not a.no_build:
        subprocess.check_call([sys.executable, str(Path(__file__).resolve().parent / "make_palette.py")])


if __name__ == "__main__":
    main()
