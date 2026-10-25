$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$blender = Get-Command blender -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -First 1
if (-not $blender) { $blender = Get-ChildItem -LiteralPath 'D:\Blender' -Filter blender.exe -Recurse -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName -First 1 }
if (-not $blender) { throw 'Blender not found. Add Blender to PATH.' }
Start-Process -FilePath $blender -ArgumentList @(('"' + (Join-Path $root 'Train_Station.blend') + '"'), '--python', ('"' + (Join-Path $root 'station_live.py') + '"'))
