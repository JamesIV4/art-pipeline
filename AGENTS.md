# AGENTS.md

All agent instructions for this repo live in [CLAUDE.md](CLAUDE.md). Read it before doing any art
work in any game: it says how to use these tools and how to write techniques, research and tool
improvements back here after each task.

The short version, for agents that only read this file:

- This repo holds the tools, Blender kits, Godot engine files and the knowledge (techniques,
  research) for every game's art. Game repos hold the data and outputs. Run tools **from the game
  root**; `python tools/pipeline_paths.py` shows which game a tool will act on.
- Start with [README.md](README.md) ("For AI agents: start here"), then
  [docs/recipes.md](docs/recipes.md) for commands and [docs/glossary.md](docs/glossary.md) for terms.
- Reuse a technique from [techniques/README.md](techniques/README.md) before inventing one.
- Gates passing is not approval: look at the in-engine render at play distance and iterate.
- A concept image is a quality bar, not a style guide; never remove or restyle established features
  to match it without asking.
- Windows only; PowerShell, not Bash; Blender headless; never kill or import over the user's open
  Godot editor.
- After the task, write back: a technique note, a dated research note, or a tool change with a
  `CHANGELOG.md` entry. Commit or push only when the user asks.
