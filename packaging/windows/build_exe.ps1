# Builds dist\MySQLDBManager-<version>.exe from main.py using PyInstaller.
#
# Run on a Windows machine, from PowerShell, with the project venv active:
#   .venv\Scripts\Activate.ps1
#   pip install pyinstaller
#   packaging\windows\build_exe.ps1
#
# PyInstaller can't cross-compile, so this has to run on Windows.

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $Root

$AppBin = "MySQLDBManager"
$Version = (Get-Content "VERSION" -Raw).Trim()
$Out = "dist\$AppBin-$Version.exe"

if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    throw "pyinstaller not found. Activate .venv and run: pip install pyinstaller"
}

Write-Host "==> Building $AppBin with PyInstaller"
pyinstaller --noconfirm --onefile --windowed --name $AppBin --specpath build main.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE" }

Write-Host "==> Copying to $Out"
Copy-Item "dist\$AppBin.exe" $Out -Force

Write-Host ""
Write-Host "Done: $Out"
