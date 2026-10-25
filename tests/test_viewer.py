"""Browser smoke/performance check. Run: python tests/test_viewer.py"""
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
    start=time.perf_counter();page.goto((ROOT/'Popuri_Gallery.html').as_uri())
    page.wait_for_function('window.popuri && window.popuri.doors.length >= 4',timeout=60000)
    load=time.perf_counter()-start
    page.wait_for_timeout(1500)
    before=page.evaluate('popuri.frames');page.wait_for_timeout(500)
    assert page.evaluate('popuri.frames')==before,'Idle viewer keeps rendering'
    page.locator('#spin').check();before=page.evaluate('popuri.frames')
    page.wait_for_timeout(4000)
    frames=page.evaluate('popuri.frames')-before
    info=page.evaluate('({calls:popuri.renderer.info.render.calls,triangles:popuri.renderer.info.render.triangles})')
    page.locator('#spin').uncheck()
    page.locator('[data-preset="aerial"]').click();page.wait_for_timeout(850)
    assert page.evaluate('popuri.roofs.every(o=>!o.visible)')
    page.locator('[data-preset="entrance"]').click();page.wait_for_timeout(2100)
    assert page.evaluate('popuri.doorAmount')>.999,'Proximity must open both leaves'
    opened=page.evaluate('popuri.doors.map(d=>({side:d.side,x:d.obj.position.x-d.closed}))')
    assert all(abs(d['x']-d['side']*1.47)<.001 for d in opened),opened
    assert page.evaluate('popuri.roofs.every(o=>o.visible)')
    page.screenshot(path=str(OUT/'door-open.png'))
    page.locator('#doorMode').select_option('closed');page.wait_for_timeout(1200)
    assert page.evaluate('popuri.doorAmount')<.001
    page.locator('#doorMode').select_option('auto')
    page.locator('[data-preset="overview"]').click();page.wait_for_timeout(2700)
    assert page.evaluate('popuri.doorAmount')<.001,'Door must close after leaving sensor'
    page.locator('[data-time="night"]').click();page.wait_for_timeout(150)
    page.screenshot(path=str(OUT/'viewer-night.png'))
    page.locator('[data-preset="aisle"]').click();page.wait_for_timeout(1000)
    page.locator('[data-time="day"]').click();page.wait_for_timeout(100)
    page.screenshot(path=str(OUT/'viewer-aisle.png'))
    page.locator('#fly').check()
    before=page.evaluate('popuri.camera.position.toArray()')
    page.locator('#scene').click(position={'x':1000,'y':400})
    page.keyboard.down('w');page.wait_for_timeout(400);page.keyboard.up('w')
    after=page.evaluate('popuri.camera.position.toArray()')
    assert sum((a-b)**2 for a,b in zip(before,after))>.1,'Free movement must move camera'
    assert not errors,errors
    gl_info=page.evaluate('''(()=>{const gl=popuri.renderer.getContext();const ext=gl.getExtension('WEBGL_debug_renderer_info');return ext?gl.getParameter(ext.UNMASKED_RENDERER_WEBGL):'unavailable';})()''')
    result={'gpu':gl_info,'loadSeconds':round(load,2),'fourSecondMotionFrames':frames,'motionFPS':round(frames/4,1),**info,'idleFramesPerHalfSecond':0,'browserErrors':errors}
    (OUT/'viewer-result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result));browser.close()
