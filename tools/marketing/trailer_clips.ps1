# Origin: art-pipeline original (2026-10-26), generalised from trick-or-treat's trailer session scripts.
# A trailer built one shot at a time from a game's own scripted cinematic mode (see
# techniques/trailer-shot-capture.md):
#   record    each shot is its own Godot movie-writer clip (so a bad shot is re-recorded on its own)
#   review    six frames sampled through every clip, tiled 3 x 2 into one PNG per clip; LOOK at them
#   assemble  trims each clip's world-loading head, dips to black between shots, concatenates, and lays
#             one continuous music bed under the shots' own sound effects
# The game must run one named shot with the user args in -ShotArgs ('{0}' = the shot name; default
# '--cine={0}' '--cine-no-music') and quit when it ends, as trick-or-treat's festival_cine.cpp does.
#
#   trailer_clips.ps1 -Stage record   -Order doorbell,door,lights,... [-Shots door,lights]
#   trailer_clips.ps1 -Stage review   -Order ...                      [-Shots ...]
#   trailer_clips.ps1 -Stage assemble -Order ... -Music game\assets\music\theme.wav -Output marketing\trailer.mp4
#                     [-MaxLength @{ jump = 2.6 }]
# Clip files are named NN_<shot>.avi by their place in -Order, so a single re-recorded shot slots back in.
# Needs ffmpeg / ffprobe on PATH. Recording runs a visible window at -Width x -Height (an override.cfg is
# written into the project for the run and removed afterwards); run long passes as a detached process.
param(
    [ValidateSet('record', 'review', 'assemble')][string]$Stage = 'record',
    [Parameter(Mandatory = $true)][string[]]$Order,
    [string[]]$Shots = @(),
    [string]$Clips = '',
    [string[]]$ShotArgs = @('--cine={0}', '--cine-no-music'),
    [int]$Fps = 30,
    [int]$Width = 2560,
    [int]$Height = 1440,
    [double]$Trim = 0.75,
    [hashtable]$MaxLength = @{},
    [string]$Music = '',
    [double]$MusicDb = -9.0,
    [string]$Output = '',
    [string]$LogPattern = 'SCRIPT ERROR|Done recording',
    [string]$GameRoot = '',
    [string]$Project = '',
    [string]$Godot = ''
)
. "$PSScriptRoot\..\..\engine\godot\review\art_pipeline_paths.ps1"
$ErrorActionPreference = 'Continue'
$root = Resolve-ArtGameRoot -GameRoot $GameRoot
$proj = Resolve-GodotProject -GameRoot $root -Project $Project
$Godot = Resolve-GodotExe -Godot $Godot
if (-not $Clips) { $Clips = Join-Path $root 'art\review\trailer' }
# `powershell -File` hands arrays over as one comma-separated string.
$Order = @($Order | ForEach-Object { $_ -split ',' } | Where-Object { $_ })
$Shots = @($Shots | ForEach-Object { $_ -split ',' } | Where-Object { $_ })
New-Item -ItemType Directory -Force $Clips | Out-Null
if ($Shots.Count -eq 0) { $Shots = $Order }

function Get-ClipName([string]$shot) {
    $i = [array]::IndexOf($Order, $shot)
    if ($i -lt 0) { throw "Shot '$shot' is not in -Order" }
    return '{0:D2}_{1}' -f ($i + 1), $shot
}

function Get-Duration([string]$file) {
    # Godot's MJPEG AVI only has a duration once the movie writer has finalised it.
    $probe = & ffprobe -v error -show_entries format=duration -of csv=p=0 $file
    $len = 0.0
    if ([double]::TryParse("$probe", [Globalization.NumberStyles]::Float, [Globalization.CultureInfo]::InvariantCulture, [ref]$len)) { return $len }
    return -1.0
}

if ($Stage -eq 'record') {
    $cfg = Join-Path $proj 'override.cfg'
    if (Test-Path $cfg) { throw "$cfg already exists; move it aside first (this script writes its own for the run)" }
    "[display]`nwindow/size/window_width_override=$Width`nwindow/size/window_height_override=$Height`n[editor]`nmovie_writer/mjpeg_quality=1.0`n" | Set-Content -Encoding ascii $cfg
    try {
        foreach ($s in $Shots) {
            $name = Get-ClipName $s
            $raw = Join-Path $Clips "$name.avi"
            Remove-Item $raw -ErrorAction SilentlyContinue
            $userArgs = $ShotArgs | ForEach-Object { $_ -f $s }
            # Collect the whole log before filtering it: cutting the pipeline short (Select-Object -First)
            # kills Godot before the movie writer finalises the AVI, which then has no duration.
            $log = & $Godot --path $proj -f --write-movie $raw --fixed-fps $Fps -- @userArgs 2>&1 | ForEach-Object { "$_" }
            $log | Select-String -Pattern $LogPattern | Select-Object -First 4 | ForEach-Object { "  $_" }
            $len = Get-Duration $raw
            if ($len -lt 0) { Write-Output "${name}: BAD CLIP (no duration; see the log above)"; continue }
            Write-Output ('{0}: {1:N1} s' -f $name, $len)
        }
    } finally {
        Remove-Item $cfg -ErrorAction SilentlyContinue
    }
}

if ($Stage -eq 'review') {
    $rev = Join-Path $Clips 'review'
    New-Item -ItemType Directory -Force $rev | Out-Null
    foreach ($s in $Shots) {
        $name = Get-ClipName $s
        $raw = Join-Path $Clips "$name.avi"
        if (-not (Test-Path $raw)) { Write-Output "missing $name"; continue }
        $len = (Get-Duration $raw) - $Trim
        if ($len -le 0) { Write-Output "${name}: BAD CLIP"; continue }
        $step = $len / 6.0
        & ffmpeg -y -v error -ss $Trim -i $raw -vf "fps=1/$step,scale=640:-1,tile=3x2" -frames:v 1 (Join-Path $rev "$name.png")
        Write-Output (Join-Path $rev "$name.png")
    }
}

if ($Stage -eq 'assemble') {
    if (-not $Output) { throw '-Output is required for assemble' }
    $Output = if ([IO.Path]::IsPathRooted($Output)) { $Output } else { Join-Path $root $Output }
    $parts = @()
    foreach ($s in $Order) {
        $name = Get-ClipName $s
        $raw = Join-Path $Clips "$name.avi"
        if (-not (Test-Path $raw)) { Write-Output "missing $name"; exit 1 }
        $len = (Get-Duration $raw) - $Trim
        if ($MaxLength.ContainsKey($s)) { $len = [math]::Min($len, [double]$MaxLength[$s]) }
        $part = Join-Path $Clips "part_$name.mp4"
        $out = $len - 0.4
        # Each shot fades in from and out to black: the dip-to-black cut between trailer beats.
        & ffmpeg -y -v error -ss $Trim -i $raw -t $len -vf "fade=t=in:st=0:d=0.3,fade=t=out:st=${out}:d=0.4" `
            -af "afade=t=in:st=0:d=0.2,afade=t=out:st=${out}:d=0.4" -c:v libx264 -preset medium -crf 12 -pix_fmt yuv420p `
            -c:a aac -b:a 320k -ar 48000 -ac 2 $part
        $parts += $part
    }
    $list = Join-Path $Clips 'parts.txt'
    ($parts | ForEach-Object { "file '$($_ -replace '\\', '/')'" }) | Set-Content -Encoding ascii $list
    $joined = Join-Path $Clips 'joined.mp4'
    & ffmpeg -y -v error -f concat -safe 0 -i $list -c copy $joined
    $total = Get-Duration $joined
    New-Item -ItemType Directory -Force (Split-Path $Output -Parent) | Out-Null
    if ($Music) {
        $Music = if ([IO.Path]::IsPathRooted($Music)) { $Music } else { Join-Path $root $Music }
        # The music bed loops under the whole trailer at the in-game level, mixed with the shots' sound
        # effects (recorded with the game's own music off), fading in and out.
        $end = $total - 2
        & ffmpeg -y -v error -i $joined -stream_loop -1 -i $Music -filter_complex `
            "[1:a]volume=${MusicDb}dB,atrim=0:$total,afade=t=in:st=0:d=1,afade=t=out:st=${end}:d=2[m];[0:a][m]amix=inputs=2:duration=first:normalize=0[a]" `
            -map 0:v -map "[a]" -c:v libx264 -preset slow -crf 14 -pix_fmt yuv420p -c:a aac -b:a 320k -movflags +faststart -t $total $Output
    } else {
        & ffmpeg -y -v error -i $joined -c:v libx264 -preset slow -crf 14 -pix_fmt yuv420p -c:a aac -b:a 320k -movflags +faststart $Output
    }
    Write-Output ('encoded {0} ({1:N1} s)' -f $Output, $total)
}
Write-Output 'ALL DONE'
