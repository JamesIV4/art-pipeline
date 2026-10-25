<#
Copies engine/godot from this pipeline into a game's Godot project as res://addons/art_pipeline/,
or compares the two so changes made inside a game can be pulled back into the pipeline.

Origin: art-pipeline original (2026-10-25).

  powershell -NoProfile -File S:\Repos\art-pipeline\tools\sync_engine_addon.ps1 -GameRoot S:\Repos\<game> [-Project game]
  ... -Diff        list files that differ between the game's copy and the pipeline (no writes)
  ... -Force       overwrite game-side files that were edited since the last sync

The copy is a plain vendored folder (it ships with the game's export). A VERSION.txt records the
pipeline commit it came from and a hash per file, so -Diff and the next sync can tell game-side
edits (to upstream) from pipeline-side updates. Without -Force a sync stops if the game copy has
local edits; upstream them first (CLAUDE.md, "Pulling improvements back").
#>
param(
    [string]$GameRoot = $(if ($env:ART_GAME_ROOT) { $env:ART_GAME_ROOT } else { (Get-Location).Path }),
    [string]$Project = '',
    [switch]$Diff,
    [switch]$Force
)
$ErrorActionPreference = 'Stop'
$pipeline = Split-Path $PSScriptRoot -Parent
$src = Join-Path $pipeline 'engine\godot'
$GameRoot = [IO.Path]::GetFullPath($GameRoot)
if (-not $Project) {
    $Project = 'game'
    $cfg = Join-Path $GameRoot 'art\pipeline.json'
    if (Test-Path -LiteralPath $cfg) {
        $j = Get-Content -LiteralPath $cfg -Raw | ConvertFrom-Json
        if ($j.paths -and $j.paths.godot_project) { $Project = $j.paths.godot_project }
    }
}
$dst = Join-Path (Join-Path $GameRoot $Project) 'addons\art_pipeline'
$versionFile = Join-Path $dst 'VERSION.txt'

function Get-Hashes([string]$dir) {
    $h = @{}
    if (Test-Path -LiteralPath $dir) {
        Get-ChildItem -LiteralPath $dir -Recurse -File | Where-Object { $_.Name -ne 'VERSION.txt' -and $_.Extension -notin '.uid', '.import' } | ForEach-Object {
            $rel = $_.FullName.Substring($dir.Length + 1)
            $h[$rel] = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash
        }
    }
    return $h
}

$srcH = Get-Hashes $src
$dstH = Get-Hashes $dst
$synced = @{}
if (Test-Path -LiteralPath $versionFile) {
    foreach ($line in Get-Content -LiteralPath $versionFile) {
        if ($line -match '^([0-9A-F]{64})  (.+)$') { $synced[$Matches[2]] = $Matches[1] }
    }
}
$gameEdited = @($dstH.Keys | Where-Object { $synced.ContainsKey($_) -and $synced[$_] -ne $dstH[$_] } | Sort-Object)
$gameOnly = @($dstH.Keys | Where-Object { -not $synced.ContainsKey($_) -and -not $srcH.ContainsKey($_) } | Sort-Object)
$pipelineChanged = @($srcH.Keys | Where-Object { $dstH[$_] -ne $srcH[$_] } | Sort-Object)

if ($Diff) {
    Write-Output "pipeline: $src"
    Write-Output "game:     $dst"
    $gameEdited | ForEach-Object { Write-Output "game-edited     $_" }
    $gameOnly | ForEach-Object { Write-Output "game-only       $_" }
    $pipelineChanged | Where-Object { $gameEdited -notcontains $_ } | ForEach-Object { Write-Output "pipeline-newer  $_" }
    return
}
if (($gameEdited.Count -or $gameOnly.Count) -and -not $Force) {
    $gameEdited + $gameOnly | ForEach-Object { Write-Output "local change: $_" }
    throw 'The game copy has local changes; upstream them into the pipeline (or pass -Force to overwrite).'
}
New-Item -ItemType Directory -Force $dst | Out-Null
foreach ($rel in $srcH.Keys) {
    $to = Join-Path $dst $rel
    New-Item -ItemType Directory -Force (Split-Path $to -Parent) | Out-Null
    Copy-Item -LiteralPath (Join-Path $src $rel) -Destination $to -Force
}
$commit = ''
try { $commit = (& git -C $pipeline rev-parse HEAD 2>$null) } catch { }
$dirty = ''
try { if (& git -C $pipeline status --porcelain -- engine/godot 2>$null) { $dirty = ' (+ uncommitted changes)' } } catch { }
$lines = @("art-pipeline engine/godot synced $(Get-Date -Format 'yyyy-MM-dd HH:mm')", "pipeline commit: $commit$dirty", '')
$lines += $srcH.Keys | Sort-Object | ForEach-Object { "$($srcH[$_])  $_" }
Set-Content -LiteralPath $versionFile -Value $lines -Encoding ascii
Write-Output "synced $($srcH.Count) files -> $dst"
