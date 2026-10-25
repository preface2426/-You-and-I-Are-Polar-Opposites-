$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$blender = Get-Command blender -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -First 1
if (-not $blender) { $blender = Get-ChildItem -LiteralPath 'D:\Blender' -Filter blender.exe -Recurse | Select-Object -ExpandProperty FullName -First 1 }
if (-not $blender) { throw 'Blender not found. Add Blender to PATH.' }
foreach ($view in @('platform','across','reverse','exterior','aisle','bench','entrance','overview')) {
    & $blender -b (Join-Path $root 'Train_Station.blend') --python-exit-code 1 --python (Join-Path $root 'station_render.py') -- --view $view
    if ($LASTEXITCODE -ne 0) { throw "Render failed: $view" }
}
