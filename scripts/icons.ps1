param([Parameter(Mandatory)][string]$Icon, [Parameter(Mandatory)][string]$Destination)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
foreach ($size in @(16, 32)) {
  $i = [System.Drawing.Icon]::new($Icon, $size, $size)
  try {
    $b = $i.ToBitmap()
    try {
      $path = Join-Path $Destination "appicon_$size.png"
      $b.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
      if (-not (Test-Path $path)) { throw "PNG failed: $path" }
    } finally { $b.Dispose() }
  } finally { $i.Dispose() }
}
