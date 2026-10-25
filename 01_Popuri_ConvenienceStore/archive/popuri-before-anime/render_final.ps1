$ErrorActionPreference = "Continue"
$bl = 'D:\Blender\blender-5.4.0-alpha+main.445db6c5f639-windows.amd64-release\blender.exe'
$base = 'D:\Projects\Blender\Popuri_Store.blend'
$render = 'D:\Projects\Blender\popuri_render.py'
$post = 'D:\Projects\Blender\popuri_post.py'
$py = 'C:\Users\youli\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe'
$root = 'D:\Projects\Blender'
$raw = Join-Path $root 'renders\raw'
New-Item -ItemType Directory -Force -Path $raw | Out-Null

Write-Output '=== RENDER INTERIOR ==='
& $bl -b $base --python $render -- --mode day --width 1800 --height 1012 --samples 96 --exposure -0.2 --out 'raw/Popuri_Interior_raw.png' 2>&1 | Tee-Object -FilePath (Join-Path $root 'renders\render_interior_final.log') | Select-Object -Last 3
Write-Output "interior exit: $LASTEXITCODE"

Write-Output '=== RENDER EXTERIOR ==='
& $bl -b $base --python $render -- --mode night --width 1800 --height 1012 --samples 128 --exposure 0.0 --out 'raw/Popuri_Exterior_Night_raw.png' 2>&1 | Tee-Object -FilePath (Join-Path $root 'renders\render_night_final.log') | Select-Object -Last 3
Write-Output "night exit: $LASTEXITCODE"

Write-Output '=== RENDER FACADE DETAIL ==='
& $bl -b $base --python $render -- --mode sign --width 1600 --height 1000 --samples 128 --exposure 0.0 --out 'raw/Popuri_Storefront_Detail_raw.png' 2>&1 | Tee-Object -FilePath (Join-Path $root 'renders\render_detail_final.log') | Select-Object -Last 3
Write-Output "detail exit: $LASTEXITCODE"

Write-Output '=== RENDER CHECKOUT DETAIL ==='
& $bl -b $base --python $render -- --mode checkout --width 1600 --height 1000 --samples 128 --exposure -0.2 --out 'raw/Popuri_Checkout_Detail_raw.png' 2>&1 | Tee-Object -FilePath (Join-Path $root 'renders\render_checkout_final.log') | Select-Object -Last 3
Write-Output "checkout exit: $LASTEXITCODE"

Write-Output '=== POST ==='
& $py $post --src (Join-Path $raw 'Popuri_Interior_raw.png') --dst (Join-Path $root 'renders\Popuri_Interior.png') --mode day
& $py $post --src (Join-Path $raw 'Popuri_Exterior_Night_raw.png') --dst (Join-Path $root 'renders\Popuri_Exterior_Night.png') --mode night
& $py $post --src (Join-Path $raw 'Popuri_Storefront_Detail_raw.png') --dst (Join-Path $root 'renders\Popuri_Storefront_Detail.png') --mode sign
& $py $post --src (Join-Path $raw 'Popuri_Checkout_Detail_raw.png') --dst (Join-Path $root 'renders\Popuri_Checkout_Detail.png') --mode day
Write-Output '=== DONE ==='
