# Origin: S:\Repos\trick-or-treat\tools\godot_lock.ps1 (imported 2026-10-25)
# Changes: the lock file lives in the game root given by -Root (default: Resolve-ArtGameRoot, i.e. -GameRoot /
#   $env:ART_GAME_ROOT / the folder holding art\pipeline.json / the current directory) instead of $PSScriptRoot\..;
#   locking logic unchanged. Reference: S:\Repos\OpenXcom-Extended-3D\art\tools\godot_main_lock.py does the same job
#   for Python callers with an O_EXCL JSON lock file (owner, pid, 3 h stale timeout); this handle-based lock needs no
#   stale timeout because Windows drops the handle when the process dies. The two kinds do not exclude each other.
# Dot-source this, then wrap Godot runs:  $lock = Enter-GodotLock -Root $gameRoot; try { ... } finally { Exit-GodotLock $lock }
# Only one Godot import/run touches the project at a time (several art workers preview in parallel).
. "$PSScriptRoot\art_pipeline_paths.ps1"

function Enter-GodotLock {
    param([string]$Root = '', [int]$TimeoutSeconds = 900)
    if (-not $Root) { $Root = Resolve-ArtGameRoot }
    $path = Join-Path $Root '.godot_lock'
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ($true) {
        try {
            $stream = [IO.File]::Open($path, 'OpenOrCreate', 'ReadWrite', 'None')
            return $stream
        } catch {
            if ((Get-Date) -gt $deadline) { throw "Timed out waiting for the Godot lock ($path)" }
            Start-Sleep -Milliseconds 700
        }
    }
}
function Exit-GodotLock {
    param($Stream)
    if ($Stream) { $Stream.Dispose() }
}
