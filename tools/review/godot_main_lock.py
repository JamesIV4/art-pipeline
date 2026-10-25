# Origin: S:/Repos/OpenXcom-Extended-3D/art/tools/godot_main_lock.py (imported 2026-10-25)
# Changed: LOCK = <godot_project>/../.godot_main_project.lock via pipeline_paths (same file as before for XCOM)
"""Exclusive lock for running Godot on the MAIN project (x-com--ufo-defense-3d).

Concurrent Godot imports corrupt the shared .godot cache, so root's review gate and
any native/renderer worker must hold this lock while Godot runs on the main project.

  python art/tools/godot_main_lock.py acquire --owner "native-worker" [--wait 3600]
  python art/tools/godot_main_lock.py release --owner "native-worker"
  python art/tools/godot_main_lock.py status

Library use: `with main_lock("root-gate"): ...`
The lock file lives beside (not inside) the project so Godot never imports it.
A lock older than 3 hours is treated as stale.
"""
import argparse
import contextlib
import json
import os
import sys
import time
from pathlib import Path

import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # art-pipeline/tools (pipeline_paths)
import pipeline_paths  # noqa: E402
ROOT = pipeline_paths.GAME_ROOT
LOCK = pipeline_paths.path("godot_project").parent / ".godot_main_project.lock"
STALE_SECONDS = 3 * 3600


def _read():
    try:
        return json.loads(LOCK.read_text(encoding="utf-8"))
    except Exception:
        return None


def acquire(owner, wait=3600, poll=15):
    deadline = time.time() + wait
    while True:
        try:
            fd = os.open(str(LOCK), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump({"owner": owner, "pid": os.getpid(), "since": time.time()}, handle)
            return True
        except FileExistsError:
            info = _read() or {}
            if time.time() - info.get("since", 0) > STALE_SECONDS:
                LOCK.unlink(missing_ok=True)
                continue
            if time.time() > deadline:
                raise TimeoutError(f"Godot main-project lock held by {info.get('owner')}")
            time.sleep(poll)


def release(owner):
    info = _read()
    if info and info.get("owner") == owner:
        LOCK.unlink(missing_ok=True)


@contextlib.contextmanager
def main_lock(owner, wait=3600):
    acquire(owner, wait)
    try:
        yield
    finally:
        release(owner)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["acquire", "release", "status"])
    parser.add_argument("--owner", default="")
    parser.add_argument("--wait", type=int, default=3600)
    args = parser.parse_args()
    if args.action == "acquire":
        acquire(args.owner, args.wait)
        print("acquired", args.owner)
    elif args.action == "release":
        release(args.owner)
        print("released", args.owner)
    else:
        print(json.dumps(_read()))
