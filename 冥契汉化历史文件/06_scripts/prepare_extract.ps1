$ErrorActionPreference = 'Stop'

$project = Split-Path -Parent $PSScriptRoot
$sourceDir = 'D:\switch游戏\个人汉化\冥契的牧神节 Meikei no Lupercalia\本体'
$nszPython = Join-Path $project '.venv\Scripts\python.exe'
$hactool = Join-Path $project 'tools\hactool\hactool.exe'
$key = 'D:\switch游戏\个人汉化\密钥\prod.keys'
$containerOut = Join-Path $project '01_extracted\container'

if (-not (Test-Path -LiteralPath $nszPython -PathType Leaf)) {
    throw "NSZ Python runtime not found: $nszPython"
}
if (-not (Test-Path -LiteralPath $hactool -PathType Leaf)) {
    throw "hactool not found: $hactool"
}
if (-not (Test-Path -LiteralPath $key -PathType Leaf)) {
    throw "Legal prod.keys not found at: $key"
}

$nsz = Get-ChildItem -LiteralPath $sourceDir -File -Filter '*.nsz' |
    Select-Object -First 1
if ($null -eq $nsz) {
    throw "No NSZ file found in: $sourceDir"
}

New-Item -ItemType Directory -Force -Path $containerOut | Out-Null

Write-Host "Input : $($nsz.FullName)"
Write-Host "Output: $containerOut"
Write-Host "Stage 1/1: decompressing NSZ to NSP"

& $nszPython -c "import nsz; nsz.main()" --keys $key --output $containerOut -D $nsz.FullName
if ($LASTEXITCODE -ne 0) {
    throw "NSZ decompression failed with exit code $LASTEXITCODE"
}

Write-Host "Done. Inspect NCA files in $containerOut with hactool -i before extracting RomFS."
