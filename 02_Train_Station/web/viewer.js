/* Offline anime viewer. Three.js r128; render only while something changes. */
(function () {
  "use strict";
  const $ = id => document.getElementById(id);
  const presets = {
    overview:{pos:[36,37,67],target:[0,5,5],fov:46},
    platform:{pos:[-.85,7.85,-23],target:[.1,7.8,-48],fov:45},
    across:{pos:[10,7.9,23],target:[0,7.85,16],fov:36},
    reverse:{pos:[-1.5,7.9,-27],target:[.2,7.9,37],fov:43},
    exterior:{pos:[7,9.8,28],target:[4.55,7.4,6],fov:36},
    interior:{pos:[4.55,7.75,12],target:[4.55,7.6,-3.7],fov:48},
    bench:{pos:[5.75,7.7,5.6],target:[3.15,7.32,5.8],fov:50},
    entrance:{pos:[.2,2.8,68],target:[-.4,3.6,51],fov:36}
  };
  const doorPoints=[-13.35,-8.45,-3.55,1.35,7.15,12.05,16.95,21.85];
  const params=new URLSearchParams((location.search || location.hash).replace(/^[?#]/,''));
  const state={night:params.get('time')==='night',exposure:.85,ambient:1,indoor:1,
    preset:presets[params.get('view')]?params.get('view'):'exterior',fly:false,doorMode:'auto'};
  let renderer,scene,camera,controls,sun,hemi,ambient,fill;
  const indoor=[],signLights=[],roofs=[],trainRoofs=[],doors=[],keys=new Set();
  let pending=false,lastTime=0,tween=null,doorAmount=0,holdUntil=0,loaded=false;
  let frames=0,lastStats=performance.now(),motionFrames=0;
  const movement=new THREE.Vector3(),forward=new THREE.Vector3(),right=new THREE.Vector3();
  function fail(message){$('loading').style.display='none';$('fail').style.display='flex';$('fail').querySelector('.fail-message').textContent=message;}
  function invalidate(){if(!pending&&!document.hidden){pending=true;requestAnimationFrame(frame);}}
  function init(){
    try {renderer=new THREE.WebGLRenderer({canvas:$('scene'),antialias:true,powerPreference:'high-performance'});}
    catch(e){fail('无法打开 WebGL，请使用 Edge / Chrome，或打开 Blender 实时版。');return;}
    renderer.outputEncoding=THREE.sRGBEncoding;
    renderer.toneMapping=THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure=state.exposure;
    renderer.shadowMap.enabled=true;
    renderer.shadowMap.type=THREE.PCFSoftShadowMap;
    renderer.shadowMap.autoUpdate=false;
    scene=new THREE.Scene();
    camera=new THREE.PerspectiveCamera(50,innerWidth/innerHeight,.04,250);
    controls=new THREE.OrbitControls(camera,renderer.domElement);
    controls.enableDamping=true;controls.dampingFactor=.12;
    controls.screenSpacePanning=true;controls.minDistance=.15;controls.maxDistance=220;
    controls.maxPolarAngle=Math.PI*.97;controls.autoRotateSpeed=.65;
    controls.addEventListener('change',invalidate);
    controls.addEventListener('start',()=>{tween=null;});
    hemi=new THREE.HemisphereLight(0xe4f4ff,0x7f8c70,.85);scene.add(hemi);
    ambient=new THREE.AmbientLight(0xffffff,.20);scene.add(ambient);
    sun=new THREE.DirectionalLight(0xfff1ce,1.4);sun.position.set(25,40,20);
    sun.castShadow=true;sun.shadow.mapSize.set(1024,1024);
    Object.assign(sun.shadow.camera,{left:-40,right:40,top:70,bottom:-70,near:.5,far:170});
    sun.shadow.bias=-.0003;sun.shadow.normalBias=.025;scene.add(sun);
    fill=new THREE.DirectionalLight(0x8ba9dc,.22);fill.position.set(-18,15,-8);scene.add(fill);
    [[4.55,8.4,6],[4.55,8.4,-14],[0,10,-20],[0,10,20]].forEach(p=>{
      const l=new THREE.PointLight(0xeaffd7,1.6,12,1);l.position.fromArray(p);scene.add(l);indoor.push(l);
    });
    [[0,7.5,49,0xffebc7]].forEach(p=>{
      const l=new THREE.PointLight(p[3],1,18,1);l.position.set(...p.slice(0,3));scene.add(l);signLights.push(l);
    });
    bind();resize();setPreset(state.preset,true);lighting();
    $('loadingText').textContent='正在读取轻量场景…';
    // HTTP opens the binary directly. file:// keeps the zero-install offline fallback.
    if(location.protocol==='file:'){
      const script=document.createElement('script');script.src='web/glb-data.js';
      script.onload=()=>{try{
        const bytes=Uint8Array.from(atob(window.STATION_GLB_GZIP_BASE64),c=>c.charCodeAt(0));
        const glb=pako.inflate(bytes);window.STATION_GLB_GZIP_BASE64=null;
        new THREE.GLTFLoader().parse(glb.buffer,'',onModel,e=>fail(String(e)));
      }catch(e){fail(e.message);}};
      script.onerror=()=>fail('缺少 web/glb-data.js，请保留完整 web 文件夹。');document.body.appendChild(script);
    }else new THREE.GLTFLoader().load('web/Train_Station.glb',onModel,undefined,e=>fail('模型读取失败：'+(e.message||e)));
  }
  function onModel(gltf){
    const values=new Uint8Array([45,125,205,255]);
    const ramp=new THREE.DataTexture(values,4,1,THREE.LuminanceFormat);
    ramp.minFilter=ramp.magFilter=THREE.NearestFilter;ramp.generateMipmaps=false;ramp.needsUpdate=true;
    const toon=new THREE.MeshToonMaterial({vertexColors:true,gradientMap:ramp});
    const glow=new THREE.MeshBasicMaterial({vertexColors:true});
    const glass=new THREE.MeshBasicMaterial({vertexColors:true,transparent:true,opacity:.12,depthWrite:false,side:THREE.DoubleSide});
    const root=gltf.scene;
    root.traverse(obj=>{
      if(!obj.isMesh)return;
      const name=obj.material.name;
      obj.material=name==='WEB_Glass'?glass:name==='WEB_Glow'?glow:toon;
      obj.castShadow=name==='WEB_Opaque';obj.receiveShadow=name==='WEB_Opaque';
      if(obj.name.startsWith('CanopyRoofGroup'))roofs.push(obj);
      if(obj.name.startsWith('TrainRoofGroup'))trainRoofs.push(obj);
      if(/^TrainLeaf(Left|Right)_/.test(obj.name))doors.push({obj,closed:obj.position.z,side:obj.name.startsWith('TrainLeafLeft')?-1:1});
    });
    scene.add(root);loaded=true;
    roofs.forEach(o=>o.visible=!$('roof').checked);
    renderer.shadowMap.needsUpdate=true;
    $('loading').style.display='none';
    $('status').textContent='拖动旋转 · 滚轮缩放 · 静止时暂停渲染';
    // A tiny read-only inspection surface supports repeatable browser checks.
    window.station={state,renderer,camera,controls,doors,roofs,trainRoofs,scene,
      get doorAmount(){return doorAmount;},get frames(){return frames;},
      setPreset,requestRender:invalidate};
    invalidate();
  }
  function lighting(){
    const n=state.night;
    scene.background=new THREE.Color(n?0x172438:0xaed6e1);
    hemi.intensity=(n?.20:.50)*state.ambient;ambient.intensity=(n?.03:.08)*state.ambient;
    sun.color.setHex(n?0x7899d6:0xfff1ce);sun.intensity=n?.25:.75;
    fill.intensity=(n?.10:.22)*state.ambient;
    indoor.forEach(l=>l.intensity=(n?.7:.15)*state.indoor);
    signLights.forEach(l=>l.intensity=n?.45:.08);
    document.querySelectorAll('[data-time]').forEach(b=>b.classList.toggle('active',(b.dataset.time==='night')===n));
    document.body.classList.toggle('is-night',n);renderer.shadowMap.needsUpdate=true;invalidate();
  }
  function setPreset(key,immediate=false){
    if(!presets[key])return;
    state.preset=key;const p=presets[key];
    document.querySelectorAll('[data-preset]').forEach(b=>b.classList.toggle('active',b.dataset.preset===key));
    if(key==='aerial'){$('roof').checked=true;roofs.forEach(o=>o.visible=false);renderer.shadowMap.needsUpdate=true;}
    else if($('roof').checked){$('roof').checked=false;roofs.forEach(o=>o.visible=true);renderer.shadowMap.needsUpdate=true;}
    controls.autoRotate=false;$('spin').checked=false;
    const pos=new THREE.Vector3().fromArray(p.pos),target=new THREE.Vector3().fromArray(p.target);
    if(immediate){camera.position.copy(pos);controls.target.copy(target);camera.fov=p.fov;camera.updateProjectionMatrix();controls.update();}
    else tween={start:performance.now(),from:camera.position.clone(),look:controls.target.clone(),fov:camera.fov,pos,target,toFov:p.fov};
    invalidate();
  }
  function updateDoor(now,dt){
    if(!loaded)return false;
    const near=doorPoints.some(y=>Math.hypot(camera.position.x-3.04,camera.position.z+y)<2.6)&&Math.abs(camera.position.y-7.8)<1.2;
    if(near)holdUntil=now+1600;
    const opening=state.doorMode==='open'||(state.doorMode==='auto'&&(near||now<holdUntil));
    const target=opening?1:0,delta=target-doorAmount;
    if(Math.abs(delta)>.0001){
      doorAmount+=Math.sign(delta)*Math.min(Math.abs(delta),dt/0.85);
      const eased=doorAmount*doorAmount*(3-2*doorAmount);
      doors.forEach(d=>d.obj.position.z=d.closed-d.side*.69*eased);
      renderer.shadowMap.needsUpdate=true;
    }
    return Math.abs(target-doorAmount)>.0001||(state.doorMode==='auto'&&!near&&now<holdUntil);
  }
  function move(dt){
    if(!state.fly||!keys.size)return;
    camera.getWorldDirection(forward);forward.y=0;forward.normalize();
    right.crossVectors(forward,camera.up).normalize();movement.set(0,0,0);
    if(keys.has('w'))movement.add(forward);if(keys.has('s'))movement.sub(forward);
    if(keys.has('d'))movement.add(right);if(keys.has('a'))movement.sub(right);
    if(keys.has('e'))movement.y++;if(keys.has('q'))movement.y--;
    movement.normalize().multiplyScalar(dt*(keys.has('shift')?7:2.6));
    if(camera.position.y+movement.y<.25)movement.y=.25-camera.position.y;
    camera.position.add(movement);controls.target.add(movement);
  }
  function frame(now){
    pending=false;if(document.hidden)return;
    if(now-lastTime>250){lastStats=now;motionFrames=0;}
    const dt=Math.min(.05,lastTime?(now-lastTime)/1000:1/60);lastTime=now;
    if(tween){const a=Math.min(1,(now-tween.start)/650),t=1-(1-a)**3;
      camera.position.lerpVectors(tween.from,tween.pos,t);controls.target.lerpVectors(tween.look,tween.target,t);
      camera.fov=tween.fov+(tween.toFov-tween.fov)*t;camera.updateProjectionMatrix();if(a===1)tween=null;
    }
    move(dt);controls.update();const doorMoving=updateDoor(now,dt);
    renderer.render(scene,camera);frames++;motionFrames++;
    if(now-lastStats>700){$('status').textContent=(state.night?'夜景':'日间')+' · '+Math.round(motionFrames*1000/(now-lastStats))+' FPS · 拖动旋转 / 滚轮缩放';motionFrames=0;lastStats=now;}
    if(tween||controls.autoRotate||(state.fly&&keys.size)||doorMoving)invalidate();
  }
  function resize(){
    const scale=Number($('quality').value);
    renderer.setPixelRatio(Math.min(devicePixelRatio||1,scale));renderer.setSize(innerWidth,innerHeight);
    camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();invalidate();
  }
  function bind(){
    renderer.domElement.tabIndex=0;
    renderer.domElement.addEventListener('pointerdown',()=>renderer.domElement.focus({preventScroll:true}));
    $('hidePanel').onclick=()=>document.body.classList.add('panel-hidden');
    $('showPanel').onclick=()=>document.body.classList.remove('panel-hidden');
    document.querySelectorAll('[data-preset]').forEach(b=>b.onclick=()=>setPreset(b.dataset.preset));
    document.querySelectorAll('[data-time]').forEach(b=>b.onclick=()=>{state.night=b.dataset.time==='night';lighting();});
    ['exposure','ambient','indoor'].forEach(id=>{$(id).oninput=()=>{state[id]=Number($(id).value);$(id+'Val').textContent=state[id].toFixed(2);renderer.toneMappingExposure=state.exposure;lighting();};});
    $('roof').onchange=()=>{roofs.forEach(o=>o.visible=!$('roof').checked);renderer.shadowMap.needsUpdate=true;invalidate();};
    $('trainRoof').onchange=()=>{trainRoofs.forEach(o=>o.visible=!$('trainRoof').checked);renderer.shadowMap.needsUpdate=true;invalidate();};
    $('spin').onchange=()=>{controls.autoRotate=$('spin').checked;invalidate();};
    $('fly').onchange=()=>{state.fly=$('fly').checked;keys.clear();};
    $('doorMode').onchange=()=>{state.doorMode=$('doorMode').value;invalidate();};
    $('quality').onchange=resize;$('reset').onclick=()=>setPreset('overview');
    addEventListener('resize',resize);
    addEventListener('keydown',e=>{
      if(/INPUT|SELECT|TEXTAREA/.test(e.target.tagName))return;
      const k=e.key.toLowerCase();
      if(state.fly&&['w','a','s','d','q','e','shift'].includes(k)){e.preventDefault();keys.add(k);tween=null;invalidate();return;}
      const map={'1':'platform','2':'interior','3':'bench','4':'entrance','5':'exterior','6':'overview','7':'reverse','8':'across'};
      if(map[k])setPreset(map[k]);if(k==='n'||k==='d'){state.night=k==='n';lighting();}
    });
    addEventListener('keyup',e=>keys.delete(e.key.toLowerCase()));
    addEventListener('blur',()=>keys.clear());
    document.addEventListener('visibilitychange',()=>{keys.clear();lastTime=0;if(!document.hidden)invalidate();});
    renderer.domElement.addEventListener('webglcontextlost',e=>{e.preventDefault();fail('显卡上下文已中断，请刷新页面重新打开。');});
  }
  init();
})();
