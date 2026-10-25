"""Prepare the offline file:// fallback; HTTP viewers load the GLB directly."""
from pathlib import Path
import base64
import gzip
root=Path(__file__).resolve().parent
raw=(root/'web'/'Train_Station.glb').read_bytes()
compressed=gzip.compress(raw,compresslevel=9,mtime=0)
assert gzip.decompress(compressed)==raw
out=root/'web'/'glb-data.js'
out.write_text('window.STATION_GLB_GZIP_BASE64 = "'+base64.b64encode(compressed).decode('ascii')+'";\n',encoding='ascii')
print('GLB',len(raw),'OFFLINE_JS',out.stat().st_size)
