"""Adds or updates a lane's entries in the game's asset catalog in one read-modify-write.

Origin: generalised from S:/Repos/trick-or-treat/art/team/<lane>/batch03/register.py and
catalog_update.py (decor, landmarks, vehicles, play_props, foliage, vines, monsters copies;
imported 2026-10-25). Several workers edit the catalog concurrently, so the file is read
immediately before writing, only the given ids are touched, and formatting (indent=1, UTF-8,
trailing newline) is preserved.

    python <pipeline>/tools/catalog_register.py entries.json            # list of full entries
    python <pipeline>/tools/catalog_register.py entries.json --merge    # merge fields into existing ids
    python <pipeline>/tools/catalog_register.py --show <id>

entries.json is a JSON list of catalog entries (see docs/catalog-schema.md); each needs at least
"id". Without --merge an existing entry is replaced wholesale; with --merge only the given fields
change (use this to update a brief or budget). New ids are appended. Run from the game root or
set ART_GAME_ROOT.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipeline_paths as P  # noqa: E402

REQUIRED_NEW = ("id", "path", "lane", "tris", "brief")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("entries", nargs="?")
    ap.add_argument("--merge", action="store_true")
    ap.add_argument("--show")
    a = ap.parse_args(argv)
    cat = P.path("catalog")
    data = json.loads(cat.read_text(encoding="utf-8"))
    ids = {e["id"]: i for i, e in enumerate(data["assets"])}
    if a.show:
        print(json.dumps(data["assets"][ids[a.show]], indent=1, ensure_ascii=False))
        return 0
    if not a.entries:
        ap.error("entries.json required")
    new = json.loads(Path(a.entries).read_text(encoding="utf-8"))
    added, updated = [], []
    for e in new:
        if e["id"] in ids:
            cur = data["assets"][ids[e["id"]]]
            data["assets"][ids[e["id"]]] = {**cur, **e} if a.merge else e
            updated.append(e["id"])
        else:
            missing = [k for k in REQUIRED_NEW if k not in e]
            if missing:
                raise SystemExit(f"new entry {e['id']} lacks {missing}")
            data["assets"].append(e)
            ids[e["id"]] = len(data["assets"]) - 1
            added.append(e["id"])
    cat.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print("added", added, "updated", updated)
    return 0


if __name__ == "__main__":
    sys.exit(main())
