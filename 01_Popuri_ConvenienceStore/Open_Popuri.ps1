$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$blender = Get-Command blender -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -First 1
if (-not $blender) {
    $blender = Get-ChildItem -LiteralPath 'D:\Blender' -Filter blender.exe -Recurse -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName -First 1
}
if (-not $blender) { throw '没有找到 Blender。请把 Blender 加入 PATH，或直接打开 Popuri_Store.blend。' }
Start-Process -FilePath $blender -ArgumentList @(('"' + (Join-Path $root 'Popuri_Store.blend') + '"'), '--python', ('"' + (Join-Path $root 'popuri_live.py') + '"'))
