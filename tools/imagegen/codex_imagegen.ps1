<#
Origin: S:/Repos/trick-or-treat/art/tools/codex_imagegen.ps1 (imported 2026-10-25; identical to the XCOM copy).
Changed: the workspace root is -Root (default $env:ART_GAME_ROOT, else the current directory)
instead of two folders above this script; -Codex overrides the codex.exe path. No credentials are
stored or read here: it uses the signed-in Codex CLI session.

Generate one image with Codex's built-in image_gen tool (signed-in ChatGPT account,
no API key) and copy it into the workspace with a provenance sidecar.

  powershell -NoProfile -File <pipeline>/tools/imagegen/codex_imagegen.ps1 [-Root <game>] `
      -PromptFile prompt.txt -Out art/team/<folder>/textures/name.png `
      [-Reference a.png,b.png] [-Transparent]

-Prompt can replace -PromptFile for short prompts. -Out must not exist (no overwrites).
Codex runs read-only in an empty scratch folder and is told only to call image_gen.
Writes <Out> and <Out>.provenance.json, and prints the saved path. Generated images are
AI-made reference/texture material: record them honestly as such, never as source art.
#>
param(
    [string]$Prompt = '',
    [string]$PromptFile = '',
    [Parameter(Mandatory = $true)][string]$Out,
    [string[]]$Reference = @(),
    [switch]$Transparent,
    [int]$TimeoutSeconds = 600,
    [string]$Root = $(if ($env:ART_GAME_ROOT) { $env:ART_GAME_ROOT } else { (Get-Location).Path }),
    [string]$Codex = ''
)
$ErrorActionPreference = 'Stop'
$repoRoot = [IO.Path]::GetFullPath($Root).TrimEnd('\')
if ($PromptFile) { $Prompt = Get-Content -LiteralPath $PromptFile -Raw -Encoding UTF8 }
if (-not $Prompt.Trim()) { throw 'Empty prompt.' }
$outPath = [IO.Path]::GetFullPath($(if ([IO.Path]::IsPathRooted($Out)) { $Out } else { Join-Path $repoRoot $Out }))
if (-not $outPath.StartsWith($repoRoot, [StringComparison]::OrdinalIgnoreCase)) { throw 'Out must be inside the workspace.' }
if (Test-Path -LiteralPath $outPath) { throw "Refusing to overwrite $outPath" }
$refPaths = @($Reference | Where-Object { $_ } | ForEach-Object {
    $p = [IO.Path]::GetFullPath($(if ([IO.Path]::IsPathRooted($_)) { $_ } else { Join-Path $repoRoot $_ }))
    if (-not (Test-Path -LiteralPath $p)) { throw "Missing reference $p" }
    $p })

$exe = if ($Codex) { $Codex } else { 'C:\nvm4w\nodejs\node_modules\@openai\codex\node_modules\@openai\codex-win32-x64\vendor\x86_64-pc-windows-msvc\bin\codex.exe' }
if (-not (Test-Path -LiteralPath $exe)) { $exe = (Get-Command codex.cmd).Source }
$codexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE '.codex' }

$work = Join-Path $env:TEMP ('codex_imagegen_' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $work | Out-Null
$instruction = @"
Call your built-in image_gen tool exactly once to generate the image specified below, then reply with only the word DONE.
Do not run shell commands, read or write files, use other tools, or ask questions.
$(if ($refPaths.Count) { "The attached image(s) are reference inputs for subject, style or material; follow the spec for how to use them." })
$(if ($Transparent) { 'Request a genuinely transparent background and preserve the alpha channel.' })

IMAGE SPEC:
$Prompt
"@
$promptPath = Join-Path $work 'prompt.txt'
[IO.File]::WriteAllText($promptPath, $instruction, (New-Object Text.UTF8Encoding $false))
$events = Join-Path $work 'events.jsonl'
$errors = Join-Path $work 'stderr.log'
$arguments = @('exec', '--json', '--sandbox', 'read-only', '--skip-git-repo-check', '-C', ('"' + $work + '"'))
foreach ($r in $refPaths) { $arguments += @('-i', ('"' + $r + '"')) }
$arguments += '-'
$started = Get-Date
$process = Start-Process -FilePath $exe -ArgumentList $arguments -WorkingDirectory $work -WindowStyle Hidden -PassThru `
    -RedirectStandardInput $promptPath -RedirectStandardOutput $events -RedirectStandardError $errors
if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
    Stop-Process -Id $process.Id -ErrorAction SilentlyContinue
    throw "Codex image generation timed out; log in $work"
}

# Find the thread id from the JSONL events, then the image saved for that thread.
$threadId = $null
foreach ($line in Get-Content -LiteralPath $events -Encoding UTF8) {
    if ($line -match '"thread_id"\s*:\s*"([0-9a-f-]{36})"') { $threadId = $Matches[1]; break }
}
$root = Join-Path $codexHome 'generated_images'
$candidates = @()
if ($threadId -and (Test-Path -LiteralPath (Join-Path $root $threadId))) {
    $candidates = @(Get-ChildItem -LiteralPath (Join-Path $root $threadId) -File)
}
if (-not $candidates.Count) {
    $candidates = @(Get-ChildItem -LiteralPath $root -Recurse -File | Where-Object { $_.LastWriteTime -ge $started })
}
if (-not $candidates.Count) {
    Get-Content -LiteralPath $events -Tail 20
    Get-Content -LiteralPath $errors -Tail 20
    throw "No generated image found; log in $work"
}
$image = $candidates | Sort-Object LastWriteTime -Descending | Select-Object -First 1
New-Item -ItemType Directory -Path (Split-Path $outPath -Parent) -Force | Out-Null
Copy-Item -LiteralPath $image.FullName -Destination $outPath
$provenance = [ordered]@{
    tool = 'Codex built-in image_gen via codex exec'
    codex_version = ((& $exe --version) -join ' ').Trim()
    generated_utc = (Get-Date).ToUniversalTime().ToString('yyyy-MM-dd HH:mm:ss') + ' UTC'
    thread_id = $threadId
    codex_source_file = $image.FullName
    sha256 = (Get-FileHash -LiteralPath $outPath -Algorithm SHA256).Hash.ToLowerInvariant()
    prompt = $Prompt
    references = @($refPaths | ForEach-Object { [ordered]@{ path = $_; sha256 = (Get-FileHash -LiteralPath $_ -Algorithm SHA256).Hash.ToLowerInvariant() } })
    transparent_requested = [bool]$Transparent
    note = 'AI-generated image. Not original game source art; use as texture/reference material only.'
}
$provenance | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath ($outPath + '.provenance.json') -Encoding UTF8
Remove-Item -LiteralPath $work -Recurse -Force
Write-Output $outPath
