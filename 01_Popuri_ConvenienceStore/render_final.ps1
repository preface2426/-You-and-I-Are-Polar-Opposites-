$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$blender = Get-Command blender -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -First 1
if (-not $blender) { $blender = Get-ChildItem -LiteralPath 'D:\Blender' -Filter blender.exe -Recurse | Select-Object -ExpandProperty FullName -First 1 }
if (-not $blender) { throw '找不到 Blender，请把 Blender 加入 PATH。' }
foreach ($mode in @('day','night','checkout','sign','aisle')) {
    & $blender -b (Join-Path $root 'Popuri_Store.blend') --python-exit-code 1 --python (Join-Path $root 'popuri_render.py') -- --mode $mode --width 1920 --height 1080 --samples 96
    if ($LASTEXITCODE -ne 0) { throw "渲染失败: $mode" }
}
