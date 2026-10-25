"""Path glue for the XCOM kit (art-pipeline/kits/xcom).

Origin: art-pipeline original (2026-10-25). Replaces the `ROOT = HERE.parents[3]` and
`sys.path.insert(0, str(ROOT / "art/tools"))` lines the kit files had while they lived in
S:/Repos/OpenXcom-Extended-3D/art/team/<lane>/... . Stdlib only, so it also works inside Blender.

Importing it:
  * puts this folder, art-pipeline/tools, tools/review and tools/textures on sys.path, so kit files
    import each other and the ported review/texture tools (catalog_reference, root_independent_checks,
    materials, ...) without any game path;
  * exposes the game root resolved by pipeline_paths (ART_GAME_ROOT env, nearest art/pipeline.json,
    or the working directory) and the lanes' working folders:

    ROOT / GAME_ROOT  the game repo (for XCOM: S:/Repos/OpenXcom-Extended-3D)
    WORK / AVENGER_WORK  AVENGER v2 lane data (sources/, notes/, textures/, refs/, prompts/):
                      $XCOM_AVENGER_WORK, else <game>/art/team/avenger_v2/common (the old location)
    OPUS_WORK         opus_lib.py lane folder (its textures/): $XCOM_OPUS_WORK,
                      else <game>/art/team/terrain_rebuild/opus_batch04 (the old location)
"""
import os
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent
PIPELINE_ROOT = KIT.parents[1]
TOOLS = PIPELINE_ROOT / "tools"
for _p in (TOOLS / "textures", TOOLS / "review", TOOLS, KIT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import pipeline_paths  # noqa: E402

GAME_ROOT = ROOT = pipeline_paths.GAME_ROOT
AVENGER_WORK = WORK = Path(os.environ.get("XCOM_AVENGER_WORK") or GAME_ROOT / "art/team/avenger_v2/common")
OPUS_WORK = Path(os.environ.get("XCOM_OPUS_WORK") or GAME_ROOT / "art/team/terrain_rebuild/opus_batch04")
