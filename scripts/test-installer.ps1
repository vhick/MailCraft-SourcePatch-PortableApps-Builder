param([Parameter(Mandatory)][string]$Installer)
$ErrorActionPreference = 'Stop'
$installerFull = (Resolve-Path -LiteralPath $Installer).Path
if (-not $IsWindows) { throw 'NSIS install acceptance requires Windows' }
if (-not $env:RUNNER_TEMP) { throw 'Refusing to execute installer outside controlled GitHub Actions runner' }
$parent = Join-Path $env:RUNNER_TEMP 'MailCraft-Installer-Acceptance'
$dest = Join-Path $parent 'Unicode 測試 and spaces\MailCraftPortable'
New-Item -ItemType Directory -Force (Split-Path $dest -Parent) | Out-Null
if (Test-Path -LiteralPath $dest) { throw "Refusing nonempty installer fixture: $dest" }
function Invoke-SandboxInstall {
  # These exact silent and destination switches are documented by NSIS itself.
  # /D= MUST BE LAST and its path MUST NOT contain quotes, including when it has spaces.
  $p = Start-Process -FilePath $installerFull -ArgumentList "/S /D=$dest" -PassThru -Wait
  if ($p.ExitCode -ne 0) { throw "Sandbox installation failed: exit $($p.ExitCode), destination=$dest" }
}
Invoke-SandboxInstall
foreach ($name in @('MailCraftPortable.exe','App\MailCraft\mailcraft.exe','App\AppInfo\appinfo.ini')) {
  if (-not (Test-Path -LiteralPath (Join-Path $dest $name))) { throw "Installer payload missing: $name" }
}
$data = Join-Path $dest 'Data'
$sentinel = Join-Path $data 'MailCraft\sentinel-preserve.txt'
New-Item -ItemType Directory -Force (Split-Path $sentinel -Parent) | Out-Null
[IO.File]::WriteAllText($sentinel, 'Mailbox data must survive an installer upgrade.', [Text.Encoding]::UTF8)
$original = (Get-FileHash -LiteralPath $sentinel -Algorithm SHA256).Hash
$empty = Join-Path $data 'TraceGuard\Recovered\NestedEmpty\ChildEmpty'
New-Item -ItemType Directory -Force $empty | Out-Null
$obsolete = Join-Path $dest 'App\MailCraft\obsolete-test-binary.exe'
[IO.File]::WriteAllBytes($obsolete, [byte[]](1,2,3,4))
# Reinstall triggers the real shared-NSIS backup/replace/rollback path.
Invoke-SandboxInstall
if (-not (Test-Path -LiteralPath $sentinel)) { throw 'Installer lost Data sentinel on reinstall' }
if ((Get-FileHash -LiteralPath $sentinel -Algorithm SHA256).Hash -ne $original) { throw 'Installer altered Data sentinel' }
if (-not (Test-Path -LiteralPath $empty -PathType Container)) { throw 'Installer lost nested empty Data tree' }
if (Test-Path -LiteralPath $obsolete) { throw 'Installer left obsolete App binary after upgrade' }
if (Test-Path -LiteralPath (Join-Path $dest '.__UPB_Backup')) { throw 'Installer left an unfinished backup after successful upgrade' }
if (Test-Path -LiteralPath (Join-Path $dest '.__UPB_Stage')) { throw 'Installer left an unfinished staged package after successful upgrade' }
Write-Host 'AUTOMATED-RUNTIME-TESTED: sandbox NSIS first install, reinstall, Data hash, nested empty directory, obsolete binary cleanup.'
Remove-Item -LiteralPath $parent -Recurse -Force
