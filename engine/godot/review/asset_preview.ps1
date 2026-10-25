# Origin: S:\Repos\trick-or-treat\tools\asset_preview.ps1 (imported 2026-10-25)
# Changes: game root / project / Godot exe are parameters (see review.ps1); the catalog, model folder, toon material
#   and output folder come from <GameRoot>\art\pipeline.json "paths" (defaults: art/asset_catalog.json,
#   game/assets/models, game/materials/toon.tres, art/review/engine). New -Scene switch:
#     addon (default)  run the addon's GDScript previewer (review/asset_preview.tscn, a port of trick-or-treat's C++
#                      preview mode) with -Material (default: the game's toon material when it exists, 'none' keeps
#                      the glTF materials), -Environment (default: presets/env_night_storybook.tres), and optional
#                      -GroundUv2 / -PathUv2 'layer,u,v' toon cells for the lawn / path (else a grid floor);
#     main             the original behaviour: run the game's main scene, which must handle --preview=<res> and
#                      --capture=<png> itself (trick-or-treat's C++ FestivalGame does, with its real lawn ground).
#   Import + capture logic unchanged.
# In-engine preview of one catalog asset with the real textured toon shader and lighting:
#   asset_preview.ps1 -Id pumpkin_round      -> <review_engine>\pumpkin_round.png
# Top row: night lighting (moon + warm porch light). Bottom row: neutral studio light for textures.
# Imports new/changed models first. Safe to run from several workers at once (serialised by a lock).
param(
    [Parameter(Mandatory = $true)][string]$Id,
    [string]$Out = '',
    [ValidateSet('addon', 'main')][string]$Scene = 'addon',
    [string]$AddonRes = 'res://addons/art_pipeline',
    [string]$Material = '',
    [string]$Environment = '',
    [string]$GroundUv2 = '',
    [string]$PathUv2 = '',
    [string]$Resolution = '1600x900',
    [string]$GameRoot = '',
    [string]$Project = '',
    [string]$Godot = ''
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\godot_lock.ps1"
$root = Resolve-ArtGameRoot -GameRoot $GameRoot
$proj = Resolve-GodotProject -GameRoot $root -Project $Project
$Godot = Resolve-GodotExe -Godot $Godot
$catalogPath = Get-ArtPipelinePath -GameRoot $root -Key 'catalog' -Default 'art/asset_catalog.json'
$modelsDir = Get-ArtPipelinePath -GameRoot $root -Key 'models_out' -Default 'game/assets/models'
$catalog = Get-Content -LiteralPath $catalogPath -Raw | ConvertFrom-Json
$asset = $catalog.assets | Where-Object { $_.id -eq $Id }
if (-not $asset) { throw "Unknown asset id '$Id'" }
$gltf = Join-Path $modelsDir "$($asset.path).gltf"
$res = ConvertTo-ResPath -ProjectDir $proj -Path $gltf
if (-not (Test-Path -LiteralPath $gltf)) { throw "Not exported yet: $res" }
if (-not $Out) {
    $reviewDir = Get-ArtPipelinePath -GameRoot $root -Key 'review_engine' -Default 'art/review/engine'
    New-Item -ItemType Directory -Force $reviewDir | Out-Null
    $Out = Join-Path $reviewDir "$Id.png"
}
$Out = [IO.Path]::GetFullPath($Out)
$godotArgs = @('--path', $proj, '--resolution', $Resolution)
$userArgs = @("--preview=$res", "--capture=$Out")
if ($Scene -eq 'addon') {
    if (-not $Material) {
        $toon = Get-ArtPipelinePath -GameRoot $root -Key 'toon_material' -Default 'game/materials/toon.tres'
        $Material = if ($toon -and (Test-Path -LiteralPath $toon)) { ConvertTo-ResPath -ProjectDir $proj -Path $toon } else { 'none' }
    }
    $godotArgs += "$AddonRes/review/asset_preview.tscn"
    $userArgs += "--material=$Material"
    if ($Environment) { $userArgs += "--env=$Environment" }
    if ($GroundUv2) { $userArgs += "--ground-uv2=$GroundUv2" }
    if ($PathUv2) { $userArgs += "--path-uv2=$PathUv2" }
}
$ErrorActionPreference = 'Continue'
$lock = Enter-GodotLock -Root $root
try {
    & $Godot --headless --import --path $proj *> $null
    & $Godot @godotArgs -- @userArgs *> "$Out.log"
} finally {
    Exit-GodotLock $lock
}
if (Test-Path $Out) { Write-Output $Out } else { Write-Output "FAILED (see $Out.log)" }
