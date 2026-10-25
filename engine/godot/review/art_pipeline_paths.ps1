# Origin: art-pipeline original (2026-10-25): the PowerShell twin of S:\Repos\art-pipeline\tools\pipeline_paths.py,
#   so the review scripts below (ported from trick-or-treat\tools and OpenXcom-Extended-3D\art\tools) resolve the
#   game the same way the Python tools do instead of using $PSScriptRoot\.. as the game root.
# Dot-source it:  . "$PSScriptRoot\art_pipeline_paths.ps1"
#   Resolve-ArtGameRoot [-GameRoot x]   explicit, else $env:ART_GAME_ROOT, else the nearest folder at or above the
#                                       current directory holding art\pipeline.json, else the current directory
#   Get-ArtPipelinePath -GameRoot r -Key k -Default 'rel/path'   art\pipeline.json "paths" entry (or the default) as
#                                       an absolute path; $null when the game set it to null
#   Get-ArtPipelineSetting -GameRoot r -Key k -Default v
#   Resolve-GodotProject -GameRoot r [-Project sub]   the Godot project folder (default: pipeline.json godot_project, 'game')
#   Resolve-GodotExe [-Godot x]          explicit, else $env:GODOT_EXE, else the Godot 4.7 console exe default
#   ConvertTo-ResPath -ProjectDir p -Path f   absolute file path inside the project -> res://...

$script:ArtDefaultGodot = 'C:\GameDev\Godot_v4.7-stable_win64\Godot_v4.7-stable_win64_console.exe'

function Resolve-ArtGameRoot {
    param([string]$GameRoot = '')
    if ($GameRoot) { return (Resolve-Path -LiteralPath $GameRoot).Path }
    if ($env:ART_GAME_ROOT) { return (Resolve-Path -LiteralPath $env:ART_GAME_ROOT).Path }
    $d = (Get-Location).Path
    while ($d) {
        if (Test-Path -LiteralPath (Join-Path $d 'art\pipeline.json')) { return $d }
        $parent = Split-Path $d -Parent
        if (-not $parent -or $parent -eq $d) { break }
        $d = $parent
    }
    return (Get-Location).Path
}

function Get-ArtPipelineConfig {
    param([Parameter(Mandatory = $true)][string]$GameRoot)
    $file = Join-Path $GameRoot 'art\pipeline.json'
    if (Test-Path -LiteralPath $file) { return (Get-Content -LiteralPath $file -Raw | ConvertFrom-Json) }
    return $null
}

function Get-ArtPipelinePath {
    param([Parameter(Mandatory = $true)][string]$GameRoot, [Parameter(Mandatory = $true)][string]$Key, [string]$Default)
    $cfg = Get-ArtPipelineConfig -GameRoot $GameRoot
    $rel = $Default
    if ($cfg -and $cfg.paths -and ($cfg.paths.PSObject.Properties.Name -contains $Key)) { $rel = $cfg.paths.$Key }
    if ($null -eq $rel -or $rel -eq '') { return $null }
    if ([IO.Path]::IsPathRooted($rel)) { return [IO.Path]::GetFullPath($rel) }
    return [IO.Path]::GetFullPath((Join-Path $GameRoot $rel))
}

function Get-ArtPipelineSetting {
    param([Parameter(Mandatory = $true)][string]$GameRoot, [Parameter(Mandatory = $true)][string]$Key, $Default)
    $cfg = Get-ArtPipelineConfig -GameRoot $GameRoot
    if ($cfg -and $cfg.settings -and ($cfg.settings.PSObject.Properties.Name -contains $Key)) { return $cfg.settings.$Key }
    return $Default
}

function Resolve-GodotProject {
    param([Parameter(Mandatory = $true)][string]$GameRoot, [string]$Project = '')
    if ($Project) {
        $p = if ([IO.Path]::IsPathRooted($Project)) { $Project } else { Join-Path $GameRoot $Project }
    } else {
        $p = Get-ArtPipelinePath -GameRoot $GameRoot -Key 'godot_project' -Default 'game'
    }
    if (-not (Test-Path -LiteralPath (Join-Path $p 'project.godot'))) { throw "No Godot project at $p (pass -Project <subfolder>)" }
    return [IO.Path]::GetFullPath($p)
}

function Resolve-GodotExe {
    param([string]$Godot = '')
    if ($Godot) { return $Godot }
    if ($env:GODOT_EXE) { return $env:GODOT_EXE }
    return $script:ArtDefaultGodot
}

function ConvertTo-ResPath {
    param([Parameter(Mandatory = $true)][string]$ProjectDir, [Parameter(Mandatory = $true)][string]$Path)
    $proj = [IO.Path]::GetFullPath($ProjectDir).TrimEnd('\') + '\'
    $full = [IO.Path]::GetFullPath($Path)
    if (-not $full.StartsWith($proj, [StringComparison]::OrdinalIgnoreCase)) { throw "$full is outside the Godot project $proj" }
    return 'res://' + $full.Substring($proj.Length).Replace('\', '/')
}
