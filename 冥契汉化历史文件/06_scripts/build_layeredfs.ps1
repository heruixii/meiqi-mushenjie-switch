param(
    [Parameter(Mandatory = $true)]
    [string]$TranslationSheet,
    [Parameter(Mandatory = $true)]
    [string]$Output
)

$ErrorActionPreference = 'Stop'
$project = Split-Path -Parent $PSScriptRoot
$python = Join-Path $project '.venv\Scripts\python.exe'
$fontPython = @((Get-Command py -CommandType Application -ErrorAction Stop))[0].Source
$romfs = Join-Path $project '01_extracted\romfs'
$buildName = Split-Path -Leaf $Output
$work = Join-Path $project "02_work\layeredfs-build-$buildName"
$patchRomfs = Join-Path $Output 'atmosphere\contents\01003080177CA000\romfs'
$fontSource = 'C:\Windows\Fonts\simhei.ttf'

foreach ($path in @($python, $fontPython, $romfs, $TranslationSheet, $fontSource)) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Required path not found: $path"
    }
}

New-Item -ItemType Directory -Force -Path $work | Out-Null
New-Item -ItemType Directory -Force -Path $patchRomfs | Out-Null

& $python (Join-Path $project '06_scripts\apply_binu8_translations.py') `
    $romfs $TranslationSheet --output $work
if ($LASTEXITCODE -ne 0) {
    throw "BINU8 build failed with exit code $LASTEXITCODE"
}

Copy-Item -LiteralPath (Join-Path $work 'Script') -Destination $patchRomfs -Recurse -Force
$config = Join-Path $work 'Config'
if (Test-Path -LiteralPath $config) {
    Copy-Item -LiteralPath $config -Destination $patchRomfs -Recurse -Force
}

$fontAliasWork = Join-Path $work 'System-alias'
& $fontPython (Join-Path $project '06_scripts\patch_ttc_cmap_aliases.py') `
    (Join-Path $romfs 'System') $TranslationSheet --output $fontAliasWork
if ($LASTEXITCODE -ne 0) {
    throw "TTC cmap build failed with exit code $LASTEXITCODE"
}

$fontWork = Join-Path $work 'System'
New-Item -ItemType Directory -Force -Path $fontWork | Out-Null
foreach ($font in Get-ChildItem -LiteralPath $fontAliasWork -Filter '*.ttc' -File) {
    & $fontPython (Join-Path $project '06_scripts\add_ttc_glyphs.py') `
        $font.FullName $fontSource $TranslationSheet `
        --output (Join-Path $fontWork $font.Name)
    if ($LASTEXITCODE -ne 0) {
        throw "TTC glyph build failed for $($font.Name) with exit code $LASTEXITCODE"
    }
}
Copy-Item -LiteralPath $fontWork -Destination $patchRomfs -Recurse -Force

Write-Host "LayeredFS patch written to: $Output"
Write-Host "Install the contents of atmosphere into the SD card's root."
