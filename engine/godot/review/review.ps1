# Origin: S:\Repos\trick-or-treat\tools\review.ps1 (imported 2026-10-25)
# Changes: game root / Godot project / Godot exe are parameters (-GameRoot, default $env:ART_GAME_ROOT, the folder
#   holding art\pipeline.json, else the current directory; -Project, default pipeline.json paths.godot_project or
#   'game'; -Godot, default $env:GODOT_EXE or the 4.7 console exe). The native (GDExtension) build is now opt-in with
#   -BuildNative (the original built unless -NoBuild); its folder, MinGW bin and scons arguments are parameters with
#   the trick-or-treat values as defaults. -Out defaults to pipeline.json paths.review_captures (art\review\captures).
#   Capture loop unchanged.
# Captures in-engine screenshots through the GAME's own command-line review mode:
#   review.ps1 -Seeds 101,102 -Views play,overview,lot:3 [-BuildNative]
# The game's main scene must implement --seed= --capture=<png> --capture-frames=<n> --capture-view=<view> (user args
# after "--"), as trick-or-treat's C++ FestivalGame does; view names are the game's.
# Everything runs under the shared Godot lock (art workers preview assets in parallel, and a running Godot holds the
# extension DLL).
param(
    [int[]]$Seeds = @(101),
    [string[]]$Views = @('play'),
    [string]$Out = '',
    [int]$Frames = 200,
    [switch]$BuildNative,
    [string]$NativeDir = '',
    [string]$MingwBin = 'C:\msys64\mingw64\bin',
    [string[]]$SconsArgs = @('platform=windows', 'use_mingw=yes', 'mingw_prefix=', 'target=template_debug', 'custom_api_file=extension_api.json', '-j8'),
    [string]$Resolution = '1600x900',
    [string]$GameRoot = '',
    [string]$Project = '',
    [string]$Godot = ''
)
. "$PSScriptRoot\godot_lock.ps1"
$root = Resolve-ArtGameRoot -GameRoot $GameRoot
$proj = Resolve-GodotProject -GameRoot $root -Project $Project
$Godot = Resolve-GodotExe -Godot $Godot
if (-not $Out) { $Out = Get-ArtPipelinePath -GameRoot $root -Key 'review_captures' -Default 'art/review/captures' }
if (-not $NativeDir) { $NativeDir = Join-Path $root 'native' }
New-Item -ItemType Directory -Force $Out | Out-Null
$ErrorActionPreference = 'Continue'
$lock = Enter-GodotLock -Root $root
try {
    if ($BuildNative) {
        $env:PATH = "$MingwBin;$env:PATH"
        Push-Location $NativeDir
        & scons @SconsArgs *> build.log
        $code = $LASTEXITCODE
        Pop-Location
        if ($code -ne 0) {
            Select-String -Path (Join-Path $NativeDir 'build.log') -Pattern 'error' | Select-Object -First 20 | ForEach-Object { $_.Line }
            throw 'native build failed'
        }
    }
    & $Godot --headless --import --path $proj *> "$Out\import.log"
    foreach ($seed in $Seeds) {
        foreach ($view in $Views) {
            $name = "seed$seed`_$($view -replace ':', '')"
            $png = Join-Path (Resolve-Path $Out) "$name.png"
            & $Godot --path $proj --resolution $Resolution -- "--seed=$seed" "--capture=$png" "--capture-frames=$Frames" "--capture-view=$view" *> "$Out\$name.log"
            if (Test-Path $png) { Write-Output $png } else { Write-Output "FAILED $name (see $Out\$name.log)" }
        }
    }
} finally {
    Exit-GodotLock $lock
}
