[CmdletBinding()]
param(
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
$packagingDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectDirectory = Split-Path -Parent $packagingDirectory
Set-Location -LiteralPath $projectDirectory

$pythonExecutable = $null
$pythonArguments = @()
$virtualEnvironmentPython = Join-Path $projectDirectory ".venv\Scripts\python.exe"

if (Test-Path -LiteralPath $virtualEnvironmentPython) {
    $pythonExecutable = $virtualEnvironmentPython
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $pythonExecutable = (Get-Command py).Source
    $pythonArguments = @("-3")
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonExecutable = (Get-Command python).Source
} else {
    throw "Python 3.10 or newer is required to build the Windows package."
}

& $pythonExecutable @pythonArguments -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"
if ($LASTEXITCODE -ne 0) {
    throw "Python 3.10 or newer is required to build the Windows package."
}

if (-not $SkipInstall) {
    & $pythonExecutable @pythonArguments -m pip install -e ".[gui,packaging]"
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install packaging dependencies."
    }
}

$originalPath = $env:PATH
$pythonDirectory = Split-Path -Parent $pythonExecutable
$cleanPath = @(
    $pythonDirectory,
    (Join-Path $env:SystemRoot "System32"),
    $env:SystemRoot
) | Select-Object -Unique
$buildExitCode = 1
try {
    # PyInstaller resolves transitive DLLs through PATH. Restrict it during the
    # build so unrelated tools (for example Poppler or FFmpeg) cannot inject
    # incompatible ICU/OpenSSL/UCRT binaries into the desktop distribution.
    $env:PATH = $cleanPath -join [IO.Path]::PathSeparator
    & $pythonExecutable @pythonArguments -m PyInstaller --clean --noconfirm "packaging\GPT-DeepSeek.spec"
    $buildExitCode = $LASTEXITCODE
} finally {
    $env:PATH = $originalPath
}
if ($buildExitCode -ne 0) {
    throw "PyInstaller build failed."
}

$desktopExecutable = Join-Path $projectDirectory "dist\GPT-DeepSeek\GPT-DeepSeek.exe"
if (-not (Test-Path -LiteralPath $desktopExecutable)) {
    throw "Build completed without the expected GPT-DeepSeek.exe output."
}

$distributionDirectory = Split-Path -Parent $desktopExecutable
Copy-Item -LiteralPath (Join-Path $projectDirectory "docs\installation-windows.md") -Destination (Join-Path $distributionDirectory "README-Windows.md") -Force
Copy-Item -LiteralPath (Join-Path $projectDirectory "LICENSE") -Destination (Join-Path $distributionDirectory "LICENSE") -Force
$archivePath = Join-Path $projectDirectory "dist\GPT-DeepSeek-v1.2.0-windows-x64.zip"
Compress-Archive -Path (Join-Path $distributionDirectory "*") -DestinationPath $archivePath -CompressionLevel Optimal -Force

Write-Host ""
Write-Host "GPT-DeepSeek v1.2.0 Windows package created:" -ForegroundColor Green
Write-Host $desktopExecutable
Write-Host $archivePath
