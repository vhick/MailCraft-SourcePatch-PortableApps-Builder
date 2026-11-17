param(
  [Parameter(Mandatory)][string]$Upstream,
  [Parameter(Mandatory)][string]$Workspace
)
$ErrorActionPreference = 'Stop'
$source = (Resolve-Path -LiteralPath $Upstream).Path
$workspace = (Resolve-Path -LiteralPath $Workspace).Path
$vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
if (-not (Test-Path -LiteralPath $vswhere)) { throw 'vswhere.exe missing; Windows Visual Studio C++ build tools required.' }
$vs = & $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if ($LASTEXITCODE -ne 0 -or -not $vs) { throw 'Visual Studio with C++ tools was not found.' }
$dev = Join-Path ($vs | Select-Object -First 1) 'Common7\Tools\VsDevCmd.bat'
if (-not (Test-Path -LiteralPath $dev)) { throw "Cannot find VS developer prompt: $dev" }
$manifest = Join-Path $source 'Cargo.toml'
$rust = (& python -c 'import pathlib,sys,tomllib; d=tomllib.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")); print(d["workspace"]["package"]["rust-version"])' $manifest).Trim()
if ($LASTEXITCODE -ne 0 -or $rust -notmatch '^\d+\.\d+(\.\d+)?$') { throw "Unsupported upstream Rust toolchain: $rust" }
& rustup toolchain install $rust --profile minimal --target x86_64-pc-windows-msvc
if ($LASTEXITCODE -ne 0) { throw "rustup install failed: $rust" }
$launcher = Join-Path $workspace 'launcher\MailCraftPortable.cpp'
$out = Join-Path $workspace 'build\MailCraftPortable.exe'
New-Item -ItemType Directory -Force (Split-Path $out -Parent) | Out-Null
# Pass paths through Unicode Windows environment variables. The CMD file itself is ASCII-only.
$env:MC_UPSTREAM_SRC = $source
$env:MC_VSDEV = $dev
$env:MC_RUST = $rust
$env:MC_LAUNCHER_CXX = $launcher
$env:MC_LAUNCHER_OUT = $out
$env:MC_ICON = Join-Path $source 'assets\app-icon\mailcraft.ico'
$env:MC_RC_FILE = Join-Path $workspace 'build\MailCraftPortable.rc'
$env:MC_RES_FILE = Join-Path $workspace 'build\MailCraftPortable.res'
# Resource file name is ASCII-only; image path stays in env to handle Unicode.
$iconForRc = $env:MC_ICON.Replace('\', '\\')
'1 ICON "' + $iconForRc + '"' | Set-Content -LiteralPath $env:MC_RC_FILE -Encoding utf8
$cmdFile = Join-Path $workspace 'build\compile.cmd'
@'
@echo off
call "%MC_VSDEV%" -arch=x64 -host_arch=x64 || exit /b 1
cd /d "%MC_UPSTREAM_SRC%"
set "CARGO_TARGET_X86_64_PC_WINDOWS_MSVC_RUSTFLAGS=-C target-feature=+crt-static"
set "MAILCRAFT_REQUIRE_WINRES=1"
rustup run %MC_RUST% cargo build --release --locked -p mailcraft -p mailcraft-cli --target x86_64-pc-windows-msvc
if errorlevel 1 exit /b 1
rc /nologo /fo "%MC_RES_FILE%" "%MC_RC_FILE%"
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /W4 /EHsc /O2 /DUNICODE /D_UNICODE /DWIN32_LEAN_AND_MEAN /Fe:"%MC_LAUNCHER_OUT%" "%MC_LAUNCHER_CXX%" "%MC_RES_FILE%" shell32.lib user32.lib
if errorlevel 1 exit /b 1
exit /b 0
'@ | Set-Content -LiteralPath $cmdFile -Encoding ascii
& cmd.exe /d /c ('"' + $cmdFile + '"')
if ($LASTEXITCODE -ne 0) { throw "Windows compilation failed (exit $LASTEXITCODE)" }
foreach ($file in @($out, (Join-Path $source 'target\x86_64-pc-windows-msvc\release\mailcraft.exe'), (Join-Path $source 'target\x86_64-pc-windows-msvc\release\mailcraft-cli.exe'))) {
  if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { throw "Missing compiled executable $file" }
  Write-Host "BUILT: $file"
}
