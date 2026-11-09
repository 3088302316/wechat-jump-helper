param(
    [string]$IsccPath = 'ISCC.exe',
    [string]$PythonExe = 'python.exe',
    [string]$LanguageFile
)
$ErrorActionPreference = 'Stop'
$iscc = (Get-Command $IsccPath -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source
$release = Join-Path $PSScriptRoot '发布'
New-Item -ItemType Directory -Path $release -Force | Out-Null

$dist = Join-Path $PSScriptRoot 'dist'
$work = Join-Path $PSScriptRoot 'build'
& $PythonExe -m PyInstaller --noconfirm --clean --onedir --windowed --noupx --name WeChatJumpHelper `
    --distpath $dist --workpath $work --specpath $work (Join-Path $PSScriptRoot 'wechat_jump_space_backspace.py')
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed.' }
$payload = Join-Path $dist 'WeChatJumpHelper'
$basePython = & $PythonExe -c 'import sys; print(sys.base_prefix)'
$pythonLicense = Join-Path $basePython 'LICENSE.txt'
if (Test-Path -LiteralPath $pythonLicense) {
    Copy-Item -LiteralPath $pythonLicense -Destination (Join-Path $payload 'Python-LICENSE.txt')
}
$arguments = @("/O$release", "/DPayloadDir=$payload")
if ($LanguageFile) { $arguments += '/DLanguageFile=' + (Resolve-Path -LiteralPath $LanguageFile).Path }
& $iscc @arguments (Join-Path $PSScriptRoot 'installer.iss')
if ($LASTEXITCODE -ne 0) { throw 'Installer compilation failed.' }
