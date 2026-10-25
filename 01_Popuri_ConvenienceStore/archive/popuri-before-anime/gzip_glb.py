import gzip, base64, os, json
src = r'D:\Projects\Blender\web\Popuri_Store.glb'
dst = r'D:\Projects\Blender\web\Popuri_Store.glb.gz'
with open(src,'rb') as f: raw=f.read()
with gzip.open(dst,'wb',compresslevel=9) as f: f.write(raw)
with open(dst,'rb') as f: comp=f.read()
b64=base64.b64encode(comp).decode('ascii')
js = 'window.POPURI_GLB_GZIP_BASE64 = "' + b64 + '";\n'
with open(r'D:\Projects\Blender\web\glb-data.js','w',encoding='ascii') as f: f.write(js)
print('RAW',len(raw),'GZ',len(comp),'B64',len(b64),'JS',os.path.getsize(r'D:\Projects\Blender\web\glb-data.js'))
