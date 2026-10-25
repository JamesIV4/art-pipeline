@echo off
rem Origin: S:/Repos/OpenXcom-Extended-3D/art/tools/asset-review/asset_review.bat (imported 2026-10-25)
rem Changed: header only
rem Asset revision reviewer: opens http://127.0.0.1:8765/ in the browser. Close this window to stop it.
python "%~dp0asset_review.py" %*
