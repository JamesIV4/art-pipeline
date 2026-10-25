# Origin: S:/Repos/OpenXcom-Extended-3D/art/team/avenger_v2/common/run_gen_chain.ps1 (imported 2026-10-25)
# Changed: -Work (old lane folder) and -ImageGen (art-pipeline/tools/imagegen/codex_imagegen.ps1) parameters replace the hard-coded paths
param([string[]]$Jobs, [string]$Work = 'art/team/avenger_v2/common',
      [string]$ImageGen = (Join-Path $PSScriptRoot '..\..\tools\imagegen\codex_imagegen.ps1'))
# Sequential image_gen calls: each job = "promptname|outname|ref1;ref2"
$ErrorActionPreference = 'Continue'
foreach ($j in $Jobs) {
    $p = $j.Split('|')
    $refs = $p[2].Split(';') | ForEach-Object { "$Work/refs/$_" }
    Write-Output "== $($p[1])"
    & $ImageGen -PromptFile "$Work/prompts/$($p[0]).txt" -Out "$Work/textures/$($p[1]).png" -Reference $refs
}
