#Requires -Version 5.1
<#
.SYNOPSIS
  Build unsigned MSI wrapping PyInstaller one-folder output (Track 6 P0 MSI).

.DESCRIPTION
  1. Ensures dist/AICommandCenter exists (runs scripts/build_windows.py if needed)
  2. Harvests files with heat.exe
  3. Compiles with candle.exe and links with light.exe

  Authenticode signing is NOT performed here. For release:
    signtool sign /fd SHA256 /a /tr http://timestamp.digicert.com dist\AICommandCenter.msi

.PARAMETER SkipPyInstaller
  Skip PyInstaller rebuild when dist output already exists.

.EXAMPLE
  .\scripts\build_msi.ps1
#>
param(
    [switch]$SkipPyInstaller
)

$ErrorActionPreference = "Stop"

function Find-WixTool {
    param([string]$Name)
    $cmd = Get-Command $Name -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $candidates = @(
        "${env:ProgramFiles(x86)}\WiX Toolset v3.11\bin\$Name",
        "${env:ProgramFiles}\WiX Toolset v3.11\bin\$Name"
    )
    foreach ($path in $candidates) {
        if (Test-Path $path) { return $path }
    }
    throw "WiX tool not found: $Name. Install WiX Toolset v3.11+ or add to PATH."
}

$repo = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$distDir = Join-Path $repo "dist\AICommandCenter"
$exe = Join-Path $distDir "AICommandCenter.exe"
$wixOut = Join-Path $repo "build\wix"
$harvestWxs = Join-Path $wixOut "AppHarvest.wxs"
$productWxs = Join-Path $repo "packaging\windows\Product.wxs"
$msiOut = Join-Path $repo "dist\AICommandCenter.msi"

if (-not (Test-Path $exe)) {
    if ($SkipPyInstaller) {
        throw "PyInstaller output missing: $exe (run python scripts/build_windows.py first)"
    }
    Write-Host "PyInstaller output missing — running build_windows.py"
    & python (Join-Path $repo "scripts\build_windows.py")
    if (-not (Test-Path $exe)) {
        throw "PyInstaller build did not produce $exe"
    }
}

$heat = Find-WixTool "heat.exe"
$candle = Find-WixTool "candle.exe"
$light = Find-WixTool "light.exe"

New-Item -ItemType Directory -Force -Path $wixOut | Out-Null

Write-Host "Harvesting $distDir ..."
& $heat dir $distDir `
    -cg AppHarvest `
    -dr INSTALLFOLDER `
    -gg -sfrag -srd `
    -var var.SourceDir `
    -out $harvestWxs

Write-Host "Compiling WiX sources ..."
& $candle `
    "-dSourceDir=$distDir" `
    -out "$wixOut\" `
    $productWxs $harvestWxs

Write-Host "Linking MSI ..."
& $light `
    "-b$distDir" `
    -out $msiOut `
    -ext WixUIExtension `
    (Join-Path $wixOut "Product.wixobj") `
    (Join-Path $wixOut "AppHarvest.wixobj")

if (-not (Test-Path $msiOut)) {
    throw "MSI build failed — output not found: $msiOut"
}

Write-Host "MSI build OK: $msiOut"
Write-Host "Note: artifact is UNSIGNED. Sign with signtool before release (see packaging/README.md)."
