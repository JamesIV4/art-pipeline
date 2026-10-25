# Instructions for agents working on art (any game)

This repo (`S:\Repos\art-pipeline`) is the user's single art pipeline. Whenever you do art work in
any game repo (models, textures, palette, materials, VFX, audio, shaders, lighting, review captures),
you use this repo's tools and knowledge, and you write what you learn back here. Game repos hold data
and outputs; this repo holds tools, kits, engine assets and knowledge.

## Before an art task

1. Read `README.md` (flow and layout), `docs/quality-contract.md`, and the game's `art/team/BRIEF.md`
   and catalog entries for the assets involved.
2. Look up relevant notes in `techniques/README.md` and recent `research/`; reuse a known technique
   before inventing one. Read the gotchas.
3. Check which game you are acting on: run tools from the game root or set `ART_GAME_ROOT`;
   `python S:\Repos\art-pipeline\tools\pipeline_paths.py` prints the resolved paths. Never run a build
   or publish against a game you did not mean to change.
4. Toolchain facts are in `docs/toolchain.md`: Blender 5.1 headless only, Godot 4.7 console exe, use
   the PowerShell tool (the Bash tool is broken on this machine), never kill the user's Godot editor,
   one Godot import at a time (the lock scripts).

## Doing the work

- Use the tools and kits from here by path (`tools/`, `kits/lowpoly/`, `engine/godot/review/`). Don't
  copy them into the game. Lane-specific helpers that are not reusable yet may live in the game's
  `art/team/<lane>/<batch>/`.
- Follow `docs/lane-batch-workflow.md` for root/worker roles, batch folders, `results.json` and
  `CHECKPOINT.md`, and the shared-file rules (catalog, palette row, Godot lock).
- Gates passing is not approval. Review in the engine under the game's real lighting, at gameplay
  distance, then iterate (`docs/review-gates.md`).
- Fidelity, not conformity: a concept image raises polish; never delete or restyle established
  features, palettes or lighting to match it without asking the user
  (`techniques/art-direction-fidelity.md`).

## After every art task: write back

Do this in the same session, before reporting done. Keep each write-back small and specific.

1. **New technique** (a method that worked, or a reusable fix): add or update
   `techniques/<kebab-name>.md` with What / Why / How (numbers, the tool or kit function) / Gotchas /
   Source (game, file paths, date). Add it to `techniques/README.md`. Prefer updating an existing note
   over creating a near-duplicate; date significant changes inside the note.
2. **Research** (anything investigated, measured, compared or rejected): add
   `research/YYYY-MM-DD-<game>-<topic>.md` with the question, findings with numbers, the decision, and
   what was rejected and why. Add it to `research/README.md`. Never rewrite old notes; add a
   "Superseded by" line instead.
3. **Tool or kit improvement**: make it here, not only in the game. Keep the `Origin:` header and add a
   `Changed:` line if behaviour changed; keep game paths behind `tools/pipeline_paths.py` (add a key to
   `DEFAULT_PATHS` / `DEFAULT_SETTINGS` whose default keeps existing games working). Add a
   `CHANGELOG.md` entry under "Unreleased" (what, why, which games are affected, any migration).
4. **Keep docs in sync with tools**: if a tool's arguments, outputs, gate rules or defaults change,
   update the docs that describe it in the same change: the folder README, `docs/*.md`, the technique
   note and, for engine files, `engine/godot/README.md`. Grep the repo for the tool's name.
5. **User preferences** stated during the task that apply beyond one game go into the relevant
   technique or `docs/quality-contract.md` (game-specific taste stays in the game's brief).
6. Commit in this repo only when the user asks; then end the commit message with the attribution line
   the session requires. Never push unless asked.

## Pulling improvements back from a game repo

Games may hold improved copies (trick-or-treat still runs its own `art/tools/` and lane kits; a game
may edit its vendored `addons/art_pipeline/`). To upstream:

1. Find the changes: `git -C <game> log -p -- art/tools tools art/team/*/*/*_kit.py ...` for tools and
   kits; `tools\sync_engine_addon.ps1 -GameRoot <game> -Diff` for the engine addon (lists game-edited,
   game-only and pipeline-newer files).
2. Diff the game file against the pipeline copy. Port the logic change into the pipeline file, keeping
   its path parameterisation (game paths stay in `pipeline_paths`, not literals). Don't paste a game's
   hard-coded paths back in.
3. Run the checks below against that game (read-only tools first, e.g. `gates.py --all`), plus a scratch
   game root for tools that write.
4. CHANGELOG entry naming the source game and commit; update docs and techniques.
5. Re-sync the engine addon into the game (`sync_engine_addon.ps1`, `-Force` only once the game-side
   edits are upstreamed) so the game and pipeline agree.

## Checks before calling a pipeline change done

- `python -m py_compile` on changed Python files; PowerShell scripts parse
  (`[System.Management.Automation.Language.Parser]::ParseFile`).
- Read-only run against a real game where possible: `$env:ART_GAME_ROOT='S:\Repos\trick-or-treat';
  python tools\gates.py --all` (184 assets PASS at import time).
- Tools that write (palette, materials, publish, catalog, Blender builds) run against a scratch game
  root in the session scratchpad, never against a game unless that is the task.
- No generated outputs in this repo: no `.glb/.gltf/.bin`, renders, review PNGs, `.blend`, audio,
  `__pycache__`, `.godot` caches, large binaries, secrets or `.env` content (`.gitignore` covers most).
