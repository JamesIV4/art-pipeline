# Origin: S:\Repos\OpenXcom-Extended-3D\art\tools\CaptureGodotReview.ps1 (imported 2026-10-25)
# Changes: game root / Godot project / Godot exe are parameters (-GameRoot as in review.ps1; -Project, default
#   pipeline.json paths.godot_project or 'game' (XCOM: 'xcom-3d-godot\x-com--ufo-defense-3d'); -Godot, default
#   $env:GODOT_EXE or the 4.7 console exe; XCOM used the windowed exe, both work). The render-control launchers come
#   from .\controls\ (-DiagnosticScript takes a file name such as ssao_control.gd or a full path; the v1
#   shadow_scene_aware_control.gd was not ported, v2 supersedes it). The runtime receipt (native DLL + viewer source
#   hashes) is written only when -NativeLibrary is given (-ViewerSource optional; XCOM passed
#   <project>\native\tactical_native.windows.template_debug.x86_64.dll and native\src\tactical_level_viewer.cpp).
#   The capture loop now holds the shared Godot lock (godot_lock.ps1; -NoLock skips it) and the per-view timeout is
#   -TimeoutSeconds (was a fixed 45 s). Validation logic unchanged.
# CONTRACT (game-specific): the project's main scene must be a review viewer that understands the user args
#   --asset= --review-catalog= --capture-view= --capture-frame= --screenshot= [--instances= --tile-patch=
#   --reflection-gray= --neutral-lighting --corner* --ground-context= --ground-ring-only --review-layout=] and prints
#   the TACTICAL_CATALOG_CHECK / TACTICAL_SOURCE_CHECK / TACTICAL_SURFACE_CHECK lines (plus TACTICAL_*_READY and
#   TACTICAL_LIGHTING) checked below, as XCOM's C++ tactical_level_viewer does. The catalog must use XCOM's schema
#   (assets[].model, metrics.triangles, variants, review_layouts) and every glTF must seal its sidecar files in
#   asset.extras.render_dependency_sha256. The -Corner defaults (terrain/BARN, terrain/CULTIVAT ids) are XCOM data.
#   Generic parts worth reusing: the import-freshness check (Confirm-ImportedResource: .import -> cache + .md5 must
#   match the source MD5), sealed-sidecar hash checks, JSON receipts, the hidden off-screen Godot window with a hard
#   timeout, and validating the capture against the viewer's stdout contract.
param(
    [string]$Asset = 'terrain/CULTIVAT/014',
    [string]$Godot = '',
    [string]$GameRoot = '',
    [string]$Project = '',
    [string]$NativeLibrary = '',
    [string]$ViewerSource = '',
    [int]$TimeoutSeconds = 45,
    [switch]$NoLock,
    [int[]]$Views = @(0,1,2,3),
    [int]$Instances = 0,
    [string]$ReviewTag = '',
    [string]$Catalog = 'assets/catalog.json',
    [string]$Layout = '',
    [int]$TilePatch = 0,
    [double]$ReflectionGray = -1,
    [switch]$NeutralLighting,
    [string]$DiagnosticScript = '',
    [switch]$RequireMaskedDoubleSided,
    [string]$GroundAsset = '',
    [switch]$GroundRingOnly,
    [string]$CornerWest = '',
    [string]$CornerNorth = '',
    [string]$CornerVariant = 'with_west_wall',
    [switch]$Corner
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\godot_lock.ps1"
$repoRoot = Resolve-ArtGameRoot -GameRoot $GameRoot
$projectRoot = Resolve-GodotProject -GameRoot $repoRoot -Project $Project
$Godot = Resolve-GodotExe -Godot $Godot
$controlsDir = Join-Path $PSScriptRoot 'controls'
if ($DiagnosticScript) {
    $diagnosticScriptPath = if ([IO.Path]::IsPathRooted($DiagnosticScript)) { [IO.Path]::GetFullPath($DiagnosticScript) } else { [IO.Path]::GetFullPath((Join-Path $controlsDir ([IO.Path]::GetFileName($DiagnosticScript)))) }
    $diagnosticName = [IO.Path]::GetFileName($diagnosticScriptPath)
    $allowedDiagnosticScripts = @('shadow_control.gd', 'shadow_distance_control.gd', 'shadow_scene_aware_control_v2.gd', 'ssao_control.gd', 'lod_control.gd') | ForEach-Object { [IO.Path]::GetFullPath((Join-Path $controlsDir $_)) }
    if ($diagnosticScriptPath -notin $allowedDiagnosticScripts) { throw 'Only scoped render-control launchers are permitted.' }
    if (-not (Test-Path -LiteralPath $diagnosticScriptPath)) { throw 'Missing shadow-control launcher.' }
}
if ($Catalog -notmatch '^assets/[A-Za-z0-9_/-]+\.json$') { throw 'Invalid local review catalog path.' }
if ($Asset -notmatch '^[A-Za-z0-9_/-]+$') { throw 'Invalid catalog asset identity.' }
if ($Layout -and $Layout -notmatch '^[A-Za-z0-9_-]+$') { throw 'Invalid exact review layout.' }
if ($Layout -and ($Corner -or $GroundAsset -or $Instances -gt 0 -or $TilePatch -gt 0)) { throw 'Layout must be captured without other fixture modes.' }
if ($GroundAsset -and $GroundAsset -notmatch '^[A-Za-z0-9_/-]+$') { throw 'Invalid ground-context identity.' }
if ($GroundAsset -and ($Corner -or $Instances -gt 0 -or $TilePatch -gt 0)) { throw 'Ground context requires an individual model review.' }
if ($GroundRingOnly -and -not $GroundAsset) { throw 'GroundRingOnly requires a ground-context asset.' }
if (($CornerWest -or $CornerNorth) -and -not $Corner) { throw 'Explicit corner identities require Corner.' }
if (($CornerWest -and $CornerWest -notmatch '^[A-Za-z0-9_/-]+$') -or ($CornerNorth -and $CornerNorth -notmatch '^[A-Za-z0-9_/-]+$') -or $CornerVariant -notmatch '^[A-Za-z0-9_-]+$') { throw 'Invalid exact corner identity/variant.' }
$reviewRoot = Join-Path $repoRoot ('art\review\godot\' + $Asset.Replace('/', '\'))
if ($ReviewTag) {
    if ($ReviewTag -notmatch '^[A-Za-z0-9_-]+$') { throw 'Invalid review revision tag.' }
    $reviewRoot = Join-Path $reviewRoot $ReviewTag
}
New-Item -ItemType Directory -Path $reviewRoot -Force | Out-Null
$reviewCatalogPath = [IO.Path]::GetFullPath((Join-Path $projectRoot $Catalog))
if (-not $reviewCatalogPath.StartsWith($projectRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Review catalog escaped the project.' }
$runtimeCatalog = Get-Content -LiteralPath $reviewCatalogPath -Raw | ConvertFrom-Json
$entry = @($runtimeCatalog.assets | Where-Object id -eq $Asset)
if ($entry.Count -ne 1 -or -not $entry[0].model) { throw 'Asset is not published as an exported model.' }
$modelPath = [IO.Path]::GetFullPath((Join-Path $projectRoot ($entry[0].model -replace '^res://','')))
$sourceModel = Get-Content -LiteralPath $modelPath -Raw | ConvertFrom-Json
if ($RequireMaskedDoubleSided -and @($sourceModel.materials | Where-Object { $_.alphaMode -ne 'MASK' -or $_.doubleSided -ne $true }).Count) { throw 'Expected source MASK/double-sided diagnostic materials.' }
if (-not $sourceModel.asset.extras.render_dependency_sha256) {
    throw "Export must seal separate buffer/image hashes before capture: $modelPath"
}
foreach ($sealed in $sourceModel.asset.extras.render_dependency_sha256) {
    $sealedPath = [IO.Path]::GetFullPath((Join-Path (Split-Path $modelPath -Parent) ([Uri]::UnescapeDataString($sealed.uri))))
    $actualSealed = (Get-FileHash -LiteralPath $sealedPath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actualSealed -ne $sealed.sha256) { throw "External resource changed after glTF version seal: $sealedPath" }
}
$modelDependencies = @($modelPath)
foreach ($buffer in $sourceModel.buffers) {
    $modelDependencies += [IO.Path]::GetFullPath((Join-Path (Split-Path $modelPath -Parent) ([Uri]::UnescapeDataString($buffer.uri))))
}
function Confirm-ImportedResource([string]$sourcePath, [string[]]$dependencies) {
    $importPath = $sourcePath + '.import'
    if (-not (Test-Path -LiteralPath $importPath)) { throw "Godot has not imported $sourcePath" }
    $config = Get-Content -LiteralPath $importPath -Raw
    # VRAM-compressed textures remap as path.s3tc= (cache x.png-<hash>.s3tc.ctex, digest x.png-<hash>.md5).
    $match = [regex]::Match($config, '(?m)^path(?:\.(?:s3tc|bptc|etc2|astc))?="res://([^"]+)"')
    if (-not $match.Success) { throw "No imported cache for $sourcePath" }
    $cachePath = [IO.Path]::GetFullPath((Join-Path $projectRoot $match.Groups[1].Value))
    $digestPath = [regex]::Replace($cachePath, '(?:\.(?:s3tc|bptc|etc2|astc))?\.[^.\\/]+$', '.md5')
    if (-not (Test-Path -LiteralPath $cachePath) -or -not (Test-Path -LiteralPath $digestPath)) { throw "Missing cache: $sourcePath" }
    $digest = Get-Content -LiteralPath $digestPath -Raw
    $actual = (Get-FileHash -LiteralPath $sourcePath -Algorithm MD5).Hash.ToLowerInvariant()
    if ($digest -notmatch ('source_md5="' + $actual + '"')) {
        throw "Stale Godot cache for $sourcePath. Finish headless import before capturing."
    }
    # Equal bytes may be rewritten with a later timestamp. Source MD5 plus
    # sealed sidecar hashes are authoritative; mtime alone is not freshness.
    return @{ source=$sourcePath; cache=$cachePath; source_md5=$actual; cache_sha256=(Get-FileHash -LiteralPath $cachePath -Algorithm SHA256).Hash.ToLowerInvariant() }
}
$receipt = @(Confirm-ImportedResource $modelPath $modelDependencies)
foreach ($texture in $sourceModel.images) {
    $texturePath = [IO.Path]::GetFullPath((Join-Path (Split-Path $modelPath -Parent) ([Uri]::UnescapeDataString($texture.uri))))
    $receipt += Confirm-ImportedResource $texturePath @($texturePath)
}
if ($Layout) {
    $selectedLayout = @($runtimeCatalog.review_layouts | Where-Object id -eq $Layout)
    if ($selectedLayout.Count -ne 1) { throw 'Missing or ambiguous exact layout.' }
    foreach ($layoutPart in $selectedLayout[0].instances) {
        $layoutEntry = @($runtimeCatalog.assets | Where-Object id -eq $layoutPart.asset_id)
        if ($layoutEntry.Count -ne 1 -or -not $layoutEntry[0].model -or $layoutPart.position_godot.Count -ne 3) { throw 'Invalid source-linked layout entry.' }
        $layoutPath = [IO.Path]::GetFullPath((Join-Path $projectRoot ($layoutEntry[0].model -replace '^res://','')))
        $layoutModel = Get-Content -LiteralPath $layoutPath -Raw | ConvertFrom-Json
        if (-not $layoutModel.asset.extras.render_dependency_sha256) { throw 'Layout resource lacks dependency seals.' }
        foreach ($sealed in $layoutModel.asset.extras.render_dependency_sha256) {
            $sealedPath = [IO.Path]::GetFullPath((Join-Path (Split-Path $layoutPath -Parent) ([Uri]::UnescapeDataString($sealed.uri))))
            if ((Get-FileHash -LiteralPath $sealedPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $sealed.sha256) { throw 'Layout dependency changed after seal.' }
        }
        $receipt += Confirm-ImportedResource $layoutPath @($layoutPath)
        foreach ($texture in $layoutModel.images) {
            $texturePath = [IO.Path]::GetFullPath((Join-Path (Split-Path $layoutPath -Parent) ([Uri]::UnescapeDataString($texture.uri))))
            $receipt += Confirm-ImportedResource $texturePath @($texturePath)
        }
    }
}
if ($Corner) {
    $isDamagedCorner = $Asset -in @('terrain/BARN/021','terrain/BARN/022')
    $cornerWestId = if ($CornerWest) { $CornerWest } elseif ($isDamagedCorner) { 'terrain/BARN/022' } elseif ($Asset -like 'terrain/BARN/*') { 'terrain/BARN/011' } else { 'terrain/CULTIVAT/014' }
    $cornerNorthId = if ($CornerNorth) { $CornerNorth } elseif ($isDamagedCorner) { 'terrain/BARN/021' } elseif ($Asset -like 'terrain/BARN/*') { 'terrain/BARN/010' } else { 'terrain/CULTIVAT/015' }
    if ($Asset -ne $cornerWestId -and $Asset -ne $cornerNorthId) { throw 'Corner capture requires a supported exact west/north identity.' }
    $cornerWestEntry = @($runtimeCatalog.assets | Where-Object id -eq $cornerWestId)[0]
    $cornerNorthEntry = @($runtimeCatalog.assets | Where-Object id -eq $cornerNorthId)[0]
    if (-not $cornerWestEntry.model -or -not $cornerNorthEntry.variants.$CornerVariant) { throw 'Missing exact connected-corner exports.' }
    if ($cornerNorthEntry.variant_context_west.$CornerVariant -and $cornerNorthEntry.variant_context_west.$CornerVariant -ne $cornerWestId) { throw 'Corner variant belongs to a different exact west context.' }
    $cornerNorthMetrics = if ($cornerNorthEntry.variant_metrics.$CornerVariant) { $cornerNorthEntry.variant_metrics.$CornerVariant } else { $cornerNorthEntry.metrics }
    foreach ($cornerResource in @($cornerWestEntry.model, $cornerNorthEntry.variants.$CornerVariant)) {
        $cornerPath = [IO.Path]::GetFullPath((Join-Path $projectRoot ($cornerResource -replace '^res://','')))
        $cornerModel = Get-Content -LiteralPath $cornerPath -Raw | ConvertFrom-Json
        if (-not $cornerModel.asset.extras.render_dependency_sha256) { throw 'Corner resource lacks dependency seals.' }
        foreach ($sealed in $cornerModel.asset.extras.render_dependency_sha256) {
            $sealedPath = [IO.Path]::GetFullPath((Join-Path (Split-Path $cornerPath -Parent) ([Uri]::UnescapeDataString($sealed.uri))))
            if ((Get-FileHash -LiteralPath $sealedPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $sealed.sha256) { throw "Corner dependency changed: $sealedPath" }
        }
        $receipt += Confirm-ImportedResource $cornerPath @($cornerPath)
        foreach ($texture in $cornerModel.images) {
            $texturePath = [IO.Path]::GetFullPath((Join-Path (Split-Path $cornerPath -Parent) ([Uri]::UnescapeDataString($texture.uri))))
            $receipt += Confirm-ImportedResource $texturePath @($texturePath)
        }
    }
}
if ($GroundAsset) {
    $groundEntry = @($runtimeCatalog.assets | Where-Object id -eq $GroundAsset)
    if ($groundEntry.Count -ne 1 -or -not $groundEntry[0].model) { throw 'Ground-context asset is not published as a model.' }
    $groundPath = [IO.Path]::GetFullPath((Join-Path $projectRoot ($groundEntry[0].model -replace '^res://','')))
    $groundModel = Get-Content -LiteralPath $groundPath -Raw | ConvertFrom-Json
    if (-not $groundModel.asset.extras.render_dependency_sha256) { throw 'Ground-context model lacks sidecar seals.' }
    foreach ($sealed in $groundModel.asset.extras.render_dependency_sha256) {
        $sealedPath = [IO.Path]::GetFullPath((Join-Path (Split-Path $groundPath -Parent) ([Uri]::UnescapeDataString($sealed.uri))))
        if ((Get-FileHash -LiteralPath $sealedPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $sealed.sha256) { throw "Ground dependency changed: $sealedPath" }
    }
    $receipt += Confirm-ImportedResource $groundPath @($groundPath)
    foreach ($texture in $groundModel.images) {
        $texturePath = [IO.Path]::GetFullPath((Join-Path (Split-Path $groundPath -Parent) ([Uri]::UnescapeDataString($texture.uri))))
        $receipt += Confirm-ImportedResource $texturePath @($texturePath)
    }
}
$receipt | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $reviewRoot 'import-receipt.json') -Encoding UTF8
$nativeLibrary = $NativeLibrary
if ($nativeLibrary -and (Test-Path -LiteralPath $nativeLibrary)) {
    $runtimeReceipt = @{ native_library=$nativeLibrary; native_sha256=(Get-FileHash -LiteralPath $nativeLibrary -Algorithm SHA256).Hash.ToLowerInvariant();
       viewer_source_sha256=$(if ($ViewerSource) { (Get-FileHash -LiteralPath $ViewerSource -Algorithm SHA256).Hash.ToLowerInvariant() } else { '' });
       review_catalog=$reviewCatalogPath; review_catalog_sha256=(Get-FileHash -LiteralPath $reviewCatalogPath -Algorithm SHA256).Hash.ToLowerInvariant();
       godot_executable_sha256=(Get-FileHash -LiteralPath $Godot -Algorithm SHA256).Hash.ToLowerInvariant() }
    if ($DiagnosticScript) {
        $runtimeReceipt.diagnostic_only = $true
        $runtimeReceipt.diagnostic_script = $diagnosticScriptPath
        $runtimeReceipt.diagnostic_script_sha256 = (Get-FileHash -LiteralPath $diagnosticScriptPath -Algorithm SHA256).Hash.ToLowerInvariant()
    }
    $runtimeReceipt | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $reviewRoot 'runtime-receipt.json') -Encoding UTF8
}
$lock = if ($NoLock) { $null } else { Enter-GodotLock -Root $repoRoot }
try {
foreach ($view in $Views) {
    $suffix = if ($Layout) { 'layout' } elseif ($GroundAsset) { 'ground-context' } elseif ($Corner) { 'corner' } elseif ($TilePatch -gt 0) { 'tile-patch-' + $TilePatch } elseif ($Instances -gt 0) { 'instances-' + $Instances } else { 'model' }
    $destination = Join-Path $reviewRoot ("$suffix-view-$view.png")
    $outputLog = Join-Path $reviewRoot ("$suffix-view-$view.stdout.log")
    $errorLog = Join-Path $reviewRoot ("$suffix-view-$view.stderr.log")
    $captureArguments = @('--path', ('"' + $projectRoot + '"'), '--position', '-10000,-10000',
        '--resolution', '1440x900', '--', ('--asset=' + $Asset), ('--review-catalog=res://' + $Catalog), ('--capture-view=' + $view),
        '--capture-frame=180', ('"--screenshot=' + $destination + '"'))
    if ($Instances -gt 0) { $captureArguments += '--instances=' + $Instances }
    if ($TilePatch -gt 0) { $captureArguments += '--tile-patch=' + $TilePatch }
    if ($ReflectionGray -ge 0) { $captureArguments += '--reflection-gray=' + $ReflectionGray.ToString([Globalization.CultureInfo]::InvariantCulture) }
    if ($NeutralLighting) { $captureArguments += '--neutral-lighting' }
    if ($Corner) { $captureArguments += @('--corner', ('--corner-west=' + $cornerWestId), ('--corner-north=' + $cornerNorthId), ('--corner-variant=' + $CornerVariant)) }
    if ($GroundAsset) { $captureArguments += '--ground-context=' + $GroundAsset }
    if ($GroundRingOnly) { $captureArguments += '--ground-ring-only' }
    if ($Layout) { $captureArguments += '--review-layout=' + $Layout }
    if ($DiagnosticScript) {
        $captureArguments = @('--script', ('"' + $diagnosticScriptPath + '"')) + $captureArguments
    }
    $captureProcess = Start-Process -FilePath $Godot -ArgumentList $captureArguments -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput $outputLog -RedirectStandardError $errorLog
    if (-not $captureProcess.WaitForExit($TimeoutSeconds * 1000)) {
        Stop-Process -Id $captureProcess.Id -ErrorAction SilentlyContinue
        throw "Godot capture timed out for this task's process $($captureProcess.Id)"
    }
    if (-not (Test-Path -LiteralPath $destination)) {
        Get-Content -LiteralPath $outputLog -Tail 12
        Get-Content -LiteralPath $errorLog -Tail 12
        throw "Godot did not produce a review image for $Asset view $view"
    }
    $captureOutput = Get-Content -LiteralPath $outputLog -Raw
    if ($captureOutput -notmatch ('TACTICAL_CATALOG_CHECK path=' + [regex]::Escape('res://' + $Catalog))) { throw 'The requested exact review catalog was not loaded.' }
    if ($DiagnosticScript) {
        $expectedControl = if ($diagnosticName -eq 'lod_control.gd') { 'TACTICAL_LOD_CONTROL prior=.* threshold=0.0 full_detail=true shadows_ssao_energy_transform_unchanged=true' } elseif ($diagnosticName -eq 'ssao_control.gd') { 'TACTICAL_SSAO_CONTROL prior_enabled=true enabled=false shadow_enabled=true energy_transform_ambient_tone_unchanged=true' } elseif ($diagnosticName -in @('shadow_scene_aware_control.gd','shadow_scene_aware_control_v2.gd')) { 'TACTICAL_SHADOW_SCENE_CONTROL meshes=\d+ .*full_actual_bounds_covered=true shadows_enabled=true energy_transform_bias_fade_mode_unchanged=true' } elseif ($diagnosticName -eq 'shadow_distance_control.gd') { 'TACTICAL_SHADOW_DISTANCE_CONTROL prior=.* distance=24.0 shadows_enabled=true energy_transform_bias_unchanged=true' } else { 'TACTICAL_SHADOW_CONTROL lights=1 prior_enabled=true enabled=false energy_unchanged=true transform_unchanged=true' }
        if ($captureOutput -notmatch $expectedControl) { throw 'Exact shadow control was not applied.' }
    }
    if ($NeutralLighting -and $captureOutput -notmatch 'TACTICAL_LIGHTING mode=neutral ') { throw 'Neutral diagnostic lighting was not applied.' }
    if ($captureOutput -notmatch ('TACTICAL_SOURCE_CHECK id=' + [regex]::Escape($Asset) + ' .*matched=true')) {
        throw "The loaded runtime mesh was not verified against $Asset's export metrics."
    }
    $surfaceChecks = [regex]::Matches($captureOutput, ('TACTICAL_SURFACE_CHECK id=' + [regex]::Escape($Asset) + ' .*color_vertices=(\d+).*vertex_albedo=(true|false)'))
    $sourceColorSurfaces = @($sourceModel.meshes | ForEach-Object { $_.primitives } | Where-Object { $null -ne $_.attributes.COLOR_0 })
    if ($sourceColorSurfaces.Count -gt 0 -and $surfaceChecks.Count -lt $sourceColorSurfaces.Count) { throw 'Missing effective-material color audit for exported COLOR_0 surfaces.' }
    foreach ($surface in $surfaceChecks) {
        if ([int]$surface.Groups[1].Value -gt 0 -and $surface.Groups[2].Value -ne 'true') {
            throw 'Authored vertex colors exist but are not enabled in the actual runtime material.'
        }
    }
    if ($RequireMaskedDoubleSided) {
        $maskedChecks = [regex]::Matches($captureOutput, ('TACTICAL_SURFACE_CHECK id=' + [regex]::Escape($Asset) + ' .*transparency=(\d+).*cull_mode=(\d+)'))
        if ($maskedChecks.Count -lt $sourceModel.materials.Count) { throw 'Missing effective masked-material audit.' }
        foreach ($maskedSurface in $maskedChecks) {
            # Installed4.7 binding enums: ALPHA_SCISSOR=2 / CULL_DISABLED=2.
            if ($maskedSurface.Groups[1].Value -ne '2' -or $maskedSurface.Groups[2].Value -ne '2') { throw 'Actual diagnostic material is not MASK/two-sided.' }
        }
    }
    if ($GroundAsset -and ($captureOutput -notmatch ('TACTICAL_SOURCE_CHECK id=' + [regex]::Escape($GroundAsset) + ' .*matched=true') -or
        $captureOutput -notmatch ('TACTICAL_GROUND_CONTEXT_READY ground=' + [regex]::Escape($GroundAsset)))) {
        throw 'The actual imported ground-context geometry/placement was not verified.'
    }
    if ($Corner) {
        $ready = 'TACTICAL_CORNER_READY west=' + [regex]::Escape($cornerWestId) + ' north=' + [regex]::Escape($cornerNorthId) + ' variant=' + [regex]::Escape($CornerVariant) + ' triangles=' + $cornerNorthMetrics.triangles
        $northCheck = 'TACTICAL_SOURCE_CHECK id=' + [regex]::Escape($cornerNorthId) + ' actual_triangles=' + $cornerNorthMetrics.triangles + ' expected_triangles=' + $cornerNorthMetrics.triangles + ' matched=true'
        $westCheck = 'TACTICAL_SOURCE_CHECK id=' + [regex]::Escape($cornerWestId) + ' actual_triangles=' + $cornerWestEntry.metrics.triangles + ' expected_triangles=' + $cornerWestEntry.metrics.triangles + ' matched=true'
        if ($captureOutput -notmatch $ready -or $captureOutput -notmatch $northCheck -or $captureOutput -notmatch $westCheck) { throw 'Actual connected corner or variant geometry was not verified.' }
    }
    if ($Layout) {
        if ($captureOutput -notmatch ('TACTICAL_LAYOUT_READY id=' + [regex]::Escape($Layout) + ' instances=' + $selectedLayout[0].instances.Count)) { throw 'Exact layout was not rendered.' }
        foreach ($layoutPart in $selectedLayout[0].instances) {
            $layoutEntry = @($runtimeCatalog.assets | Where-Object id -eq $layoutPart.asset_id)[0]
            $layoutCheck = 'TACTICAL_SOURCE_CHECK id=' + [regex]::Escape($layoutPart.asset_id) + ' actual_triangles=' + $layoutEntry.metrics.triangles + ' expected_triangles=' + $layoutEntry.metrics.triangles + ' matched=true'
            if ($captureOutput -notmatch $layoutCheck) { throw 'Actual layout geometry was not verified.' }
        }
    }
    Write-Output ("Captured " + $Asset + ' view ' + $view)
}
} finally {
    Exit-GodotLock $lock
}
