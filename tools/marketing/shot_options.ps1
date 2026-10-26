# Origin: art-pipeline original (2026-10-26), generalised from trick-or-treat's trailer session scripts.
# Candidate worlds for one cinematic shot, for the user to choose from: one clip per seed (kept, so the
# chosen one can be copied straight into the trailer's clips folder) and one labelled still from each,
# tiled two across into a sheet. See techniques/trailer-shot-capture.md ("Let the user pick the world").
#   shot_options.ps1 -Shot monsters -Seeds 103,105,109,110 [-SeedArg '--cine-seed={0}'] [-At 2.4]
# -SeedArg is how the game takes a seed for that shot: a whole-world seed ('--seed={0}') when the shot
# picks its location from the reel's world, or a per-shot override ('--cine-seed={0}' in trick-or-treat).
# Rendering is visible and takes ~15 s per seed; the user may watch the window and pick before the
# sheet is done, so run it detached and don't block on it.
param(
    [Parameter(Mandatory = $true)][string]$Shot,
    [string[]]$Seeds = @('101', '103', '104', '105', '107', '108'),
    [string]$SeedArg = '--seed={0}',
    [string[]]$ShotArgs = @('--cine={0}', '--cine-no-music'),
    [double]$At = 1.8,
    [string]$Out = '',
    [int]$Fps = 30,
    [int]$Width = 2560,
    [int]$Height = 1440,
    [string]$GameRoot = '',
    [string]$Project = '',
    [string]$Godot = ''
)
. "$PSScriptRoot\..\..\engine\godot\review\art_pipeline_paths.ps1"
$ErrorActionPreference = 'Continue'
$root = Resolve-ArtGameRoot -GameRoot $GameRoot
$proj = Resolve-GodotProject -GameRoot $root -Project $Project
$Godot = Resolve-GodotExe -Godot $Godot
if (-not $Out) { $Out = Join-Path $root 'art\review\trailer\options' }
# `powershell -File` hands arrays over as one comma-separated string.
$Seeds = @($Seeds | ForEach-Object { "$_" -split ',' } | Where-Object { $_ } | ForEach-Object { [int]$_ })
New-Item -ItemType Directory -Force $Out | Out-Null
$cfg = Join-Path $proj 'override.cfg'
if (Test-Path $cfg) { throw "$cfg already exists; move it aside first (this script writes its own for the run)" }
"[display]`nwindow/size/window_width_override=$Width`nwindow/size/window_height_override=$Height`n[editor]`nmovie_writer/mjpeg_quality=1.0`n" | Set-Content -Encoding ascii $cfg
$stills = @()
try {
    foreach ($seed in $Seeds) {
        $raw = Join-Path $Out "${Shot}_$seed.avi"
        Remove-Item $raw -ErrorAction SilentlyContinue
        $userArgs = @($ShotArgs | ForEach-Object { $_ -f $Shot }) + @($SeedArg -f $seed)
        # Never cut this pipeline short: Godot must exit on its own for the AVI to be finalised.
        $null = & $Godot --path $proj -f --write-movie $raw --fixed-fps $Fps -- @userArgs 2>&1 | ForEach-Object { "$_" }
        $png = Join-Path $Out "${Shot}_$seed.png"
        $label = "Option $($stills.Count + 1)  (seed $seed)"
        & ffmpeg -y -v error -ss $At -i $raw -frames:v 1 -vf "scale=960:-1,drawtext=fontfile='C\:/Windows/Fonts/arialbd.ttf':text='$label':x=24:y=24:fontsize=34:fontcolor=white:box=1:boxcolor=black@0.6:boxborderw=10" $png
        if (Test-Path $png) { $stills += $png; Write-Output "$Shot seed $seed ok" } else { Write-Output "$Shot seed $seed FAILED" }
    }
} finally {
    Remove-Item $cfg -ErrorAction SilentlyContinue
}
if ($stills.Count -eq 0) { exit 1 }
$inputs = @(); foreach ($p in $stills) { $inputs += '-i'; $inputs += $p }
$n = $stills.Count
$sheet = Join-Path $Out "${Shot}_options.png"
if ($n -eq 1) {
    Copy-Item $stills[0] $sheet -Force
} else {
    $layout = (0..($n - 1) | ForEach-Object { '{0}_{1}' -f (($_ % 2) * 960), ([math]::Floor($_ / 2) * 540) }) -join '|'
    & ffmpeg -y -v error @inputs -filter_complex "xstack=inputs=${n}:layout=${layout}:fill=black" $sheet
}
Write-Output $sheet
