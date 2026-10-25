# Toolchain

Everything runs on the user's Windows 11 machine. Paths below are the known-good installs; override
them per machine with the environment variables in the last table.

| Tool | Version / path | Used for |
|---|---|---|
| Blender | 5.1, `C:\Program Files\Blender Foundation\Blender 5.1\blender.exe` | every model build, VFX sprite renders, Workbench review sheets. Always headless: `--background --factory-startup --python <script> [-- args]` (XCOM workers add `--threads 2` when several run at once) |
| Godot | 4.7 standard (not mono), `C:\GameDev\Godot_v4.7-stable_win64\Godot_v4.7-stable_win64_console.exe` | import, in-engine previews and captures. Use the `_console` exe from scripts so stdout and exit codes come back |
| Python | 3.13 on PATH as `python` | tools outside Blender. Needs `numpy` and `Pillow` (`pip install numpy pillow`); some XCOM texture tools also need what `tools/textures/texture-requirements.txt` lists, XCOM reference tools need `pyyaml` |
| PowerShell | Windows PowerShell 5.1 | all shell work and the `.ps1` wrappers |
| MinGW g++ + SCons | `C:\msys64\mingw64\bin` (not on PATH), SCons from Python313 Scripts | only for games with a GDExtension (`review.ps1 -BuildNative`) |
| Codex CLI | signed-in ChatGPT account, `codex.cmd` on PATH (or the nvm4w vendor exe) | `tools/imagegen/codex_imagegen.ps1` painted texture sources. No API key is involved |
| Node + esbuild | optional | only to rebuild the three.js bundle for `tools/review/asset-review` |

## Machine gotchas

- The Claude Code **Bash tool is broken on this machine** ("Top-level not found"). Agents use the
  PowerShell tool. Windows PowerShell 5.1 has no `&&`; chain with `;` and `if ($?) { }`.
- Never kill the user's Godot editor. If they playtest with a project open, its GDExtension DLL is
  locked: rename the locked DLL aside before a native build. Do not run `--import` while their editor
  has the project open, or run it under the game's Godot lock (`engine/godot/review/godot_lock.ps1`).
  Concurrent imports corrupt `.godot` (XCOM learned this the hard way).
- Godot re-imports a glTF only when the `.gltf` text changes; the geometry lives in the `.bin`. The
  kit stamps a build id into the scene extras (`build_stamp_key`) so every rebuild re-imports. XCOM's
  stronger version seals buffer hashes into the glTF (`tools/review/seal_model_versions.py`) and
  checks Godot's cached `source_md5`, not file times.
- Blender 5.1 API notes: `create_icosphere(subdivisions=1)` is the bare 20-triangle icosahedron;
  EEVEE's enum may be `BLENDER_EEVEE` or `BLENDER_EEVEE_NEXT` (try both).

## Environment variables

| Variable | Meaning | Default |
|---|---|---|
| `ART_GAME_ROOT` | the game repo the tools act on | nearest folder above the cwd with `art/pipeline.json`, else the cwd |
| `ART_PIPELINE` | this repo (build scripts use it to find `kits/`) | `S:\Repos\art-pipeline` |
| `BLENDER_EXE` | Blender executable | the path above |
| `GODOT_EXE` | Godot console executable | the path above |
| `CODEX_HOME` | Codex data dir (generated images) | `%USERPROFILE%\.codex` |

Check what a tool will touch before running it: `python <pipeline>\tools\pipeline_paths.py` prints the
resolved game root and every path.
