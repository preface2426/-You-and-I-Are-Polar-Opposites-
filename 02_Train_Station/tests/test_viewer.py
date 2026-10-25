"""Browser checks for offline load, boarding doors, roof controls and free movement."""
from pathlib import Path
import json
import time
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'.qa';OUT.mkdir(exist_ok=True)
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True,args=['--allow-file-access-from-files','--ignore-gpu-blocklist'])
    page=browser.new_page(viewport={'width':1400,'height':850},device_scale_factor=1)
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    start=time.perf_counter();page.goto((ROOT/'Station_Gallery.html').as_uri())
    page.wait_for_function('window.station && station.doors.length>=16',timeout=60000)
    load=time.perf_counter()-start
    page.wait_for_timeout(1800)
    before=page.evaluate('station.frames');page.wait_for_timeout(500)
    assert page.evaluate('station.frames')==before,'Idle viewer must stop rendering'
    page.locator('#spin').check();before=page.evaluate('station.frames')
    page.wait_for_timeout(4000)
    frames=page.evaluate('station.frames')-before
    info=page.evaluate('({calls:station.renderer.info.render.calls,triangles:station.renderer.info.render.triangles})')
    page.locator('#spin').uncheck()
    page.locator('[data-preset="interior"]').click();page.wait_for_timeout(2100)
    assert page.evaluate('station.doorAmount')>.999,'Boarding doors must open near the camera'
    opened=page.evaluate('station.doors.map(d=>({side:d.side,z:d.obj.position.z-d.closed}))')
    assert all(abs(d['z']+d['side']*.69)<.001 for d in opened),opened
    page.screenshot(path=str(OUT/'carriage-browser.png'))
    page.locator('#doorMode').select_option('closed');page.wait_for_timeout(1200)
    assert page.evaluate('station.doorAmount')<.001
    page.locator('#doorMode').select_option('auto')
    page.locator('#trainRoof').check();page.wait_for_timeout(100)
    assert page.evaluate('station.trainRoofs.length>0 && station.trainRoofs.every(o=>!o.visible)')
    page.locator('#trainRoof').uncheck()
    page.locator('#roof').check();page.wait_for_timeout(100)
    assert page.evaluate('station.roofs.length>0 && station.roofs.every(o=>!o.visible)')
    page.locator('#roof').uncheck()
    page.locator('[data-preset="exterior"]').click();page.wait_for_timeout(2800)
    assert page.evaluate('station.doorAmount')<.001,'Doors must close after leaving'
    page.screenshot(path=str(OUT/'exterior-browser.png'))
    page.locator('[data-time="night"]').click();page.wait_for_timeout(100)
    assert page.evaluate('station.state.night')
    page.locator('[data-time="day"]').click()
    page.locator('#fly').check();before=page.evaluate('station.camera.position.toArray()')
    page.locator('#scene').click(position={'x':1000,'y':400})
    page.keyboard.down('w');page.wait_for_timeout(400);page.keyboard.up('w')
    after=page.evaluate('station.camera.position.toArray()')
    assert sum((a-b)**2 for a,b in zip(before,after))>.1
    gl_info=page.evaluate("(()=>{const gl=station.renderer.getContext(),ext=gl.getExtension('WEBGL_debug_renderer_info');return ext?gl.getParameter(ext.UNMASKED_RENDERER_WEBGL):'unavailable';})()")
    assert not errors,errors
    result={'viewport':'1400x850 / device pixel ratio 1 / Chrome headless','gpu':gl_info,'loadSeconds':round(load,2),'motionFPS':round(frames/4,1),**info,'idleFramesPerHalfSecond':0,'browserErrors':errors}
    (ROOT/'web/performance.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result));browser.close()
