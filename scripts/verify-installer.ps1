param([Parameter(Mandatory)][string]$Installer,[Parameter(Mandatory)][string]$ExpectedSha)
$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $Installer -PathType Leaf)) { throw "Installer not found: $Installer" }
$actual = (Get-FileHash -LiteralPath $Installer -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actual -ne $ExpectedSha.ToLowerInvariant()) { throw 'Installer SHA-256 does not match shared Package Builder output' }
$exe = if (Get-Command 7z.exe -ErrorAction SilentlyContinue) { (Get-Command 7z.exe).Source } else { "$env:ProgramFiles\7-Zip\7z.exe" }
if (-not (Test-Path -LiteralPath $exe)) { throw '7-Zip required to validate NSIS payload' }
& $exe t -bso0 -bsp0 $Installer | Out-Host
if ($LASTEXITCODE -ne 0) { throw 'NSIS archive integrity test failed' }
$listing = (& $exe l -slt $Installer) -join "`n"
if ($LASTEXITCODE -ne 0) { throw 'NSIS listing failed' }
foreach ($name in @('MailCraftPortable.exe','mailcraft.exe','mailcraft-cli.exe','appinfo.ini','appicon.ico')) {
  if (-not $listing.Contains($name)) { throw "Expected application payload missing from NSIS listing: $name" }
}
Write-Host "STATIC-VALIDATED: NSIS PE/archive integrity and embedded payload (not installed runtime). SHA256=$actual"
