param(
    [string]$IsccPath = 'ISCC.exe',
    [string]$PythonExe = 'python.exe',
    [string]$LanguageFile,
    [string]$ReleaseDirectory = (Join-Path $PSScriptRoot '发布')
)
$ErrorActionPreference = 'Stop'
$iscc = (Get-Command $IsccPath -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source
$release = [IO.Path]::GetFullPath($ReleaseDirectory)
New-Item -ItemType Directory -Path $release -Force | Out-Null
$tempRoot = (Resolve-Path -LiteralPath ([IO.Path]::GetTempPath())).Path
$staging = Join-Path $tempRoot ('WeChatJumpHelperBuild-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $staging | Out-Null
try {
    $dist = Join-Path $staging 'dist'
    $work = Join-Path $staging 'build'
    & $PythonExe -m PyInstaller --noconfirm --clean --onedir --windowed --noupx --name WeChatJumpHelper `
        --distpath $dist --workpath $work --specpath $work (Join-Path $PSScriptRoot 'wechat_jump_space_backspace.py')
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed.' }
    $payload = Join-Path $dist 'WeChatJumpHelper'
    $basePython = & $PythonExe -c 'import sys; print(sys.base_prefix)'
    if ($LASTEXITCODE -ne 0) { throw 'Cannot locate the base Python installation.' }
    $pythonLicense = Join-Path $basePython 'LICENSE.txt'
    if (Test-Path -LiteralPath $pythonLicense) {
        Copy-Item -LiteralPath $pythonLicense -Destination (Join-Path $payload 'Python-LICENSE.txt')
    }
    $arguments = @("/O$release", "/DPayloadDir=$payload")
    if ($LanguageFile) { $arguments += '/DLanguageFile=' + (Resolve-Path -LiteralPath $LanguageFile).Path }
    & $iscc @arguments (Join-Path $PSScriptRoot 'installer.iss')
    if ($LASTEXITCODE -ne 0) { throw 'Installer compilation failed.' }
} finally {
    $directory = Get-Item -LiteralPath $staging
    if ($directory.FullName -eq $staging -and $directory.Parent.FullName -eq $tempRoot -and
        -not ($directory.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        Remove-Item -LiteralPath $directory.FullName -Recurse -Force
    }
}
