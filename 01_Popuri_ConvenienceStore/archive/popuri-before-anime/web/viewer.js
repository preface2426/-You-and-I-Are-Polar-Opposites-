/* Popuri store interactive viewer — Three.js r128, no external network. */
(function () {
  "use strict";

  const canvas = document.getElementById("scene");
  const loading = document.getElementById("loading");
  const loadingText = document.getElementById("loadingText");
  const fail = document.getElementById("fail");
  const panel = document.getElementById("panel");
  const status = document.getElementById("status");

  const PRESETS = {
    overview: { pos: [14.2, 8.6, 18.4], target: [0.0, 1.7, 0.2], fov: 38 },
    interior: { pos: [4.4, 1.72, 0.7], target: [-5.0, 1.28, 4.3], fov: 56 },
    checkout: { pos: [-3.2, 1.80, 3.9], target: [-6.7, 1.2, 0.4], fov: 43 },
    entrance: { pos: [-1.4, 2.0, 12.6], target: [-4.7, 1.4, 4.8], fov: 45 },
    sign: { pos: [10.5, 3.0, 15.5], target: [-0.3, 3.3, 4.9], fov: 44 },
    aerial: { pos: [0.0, 20.0, 18.0], target: [0.0, 0.2, 0.5], fov: 38 },
  };

  const query = new URLSearchParams(window.location.search);
  const hashQuery = new URLSearchParams(window.location.hash.replace(/^#/, ""));
  const queryView = query.get("view") || hashQuery.get("view");
  const queryTime = query.get("time") || hashQuery.get("time");
  const initialState = {
    night: queryTime === "night",
    exposure: 0.50,
    ambient: 1.0,
    indoor: 1.0,
    roofHidden: false,
    preset: PRESETS[queryView] ? queryView : "overview",
  };

  const state = initialState;

  let renderer, scene, camera, controls, clock;
  let hemi, ambient, sun, fill, interiorLights = [], signLights = [];
  let envDay, envNight, stars, roofGroup;
  let fromState = null, toState = null, tweenStart = 0, tweenDur = 950;

  function showFail(message) {
    loading.style.display = "none";
    fail.style.display = "flex";
    fail.querySelector(".fail-message").textContent = message;
  }

  function init() {
    if (!window.THREE) {
      showFail("Three.js 未能加载。请确认 web/vendor 文件夹完整。");
      return;
    }
    if (!window.POPURI_GLB_GZIP_BASE64) {
      showFail("没有找到场景数据 web/glb-data.js。");
      return;
    }

    try {
      renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false });
    } catch (err) {
      showFail("当前浏览器无法创建 WebGL 上下文。请尝试更新 Edge / Chrome，或查看静态渲染图。");
      return;
    }

    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.outputEncoding = THREE.sRGBEncoding;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = state.exposure;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;

    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x89b6dd);
    clock = new THREE.Clock();

    camera = new THREE.PerspectiveCamera(PRESETS[state.preset].fov, window.innerWidth / window.innerHeight, 0.05, 220);
    camera.position.fromArray(PRESETS[state.preset].pos);

    controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.target.fromArray(PRESETS[state.preset].target);
    controls.enableDamping = true;
    controls.dampingFactor = 0.075;
    controls.rotateSpeed = 0.65;
    controls.zoomSpeed = 0.8;
    controls.panSpeed = 0.8;
    controls.screenSpacePanning = true;
    controls.minDistance = 0.8;
    controls.maxDistance = 65;
    controls.maxPolarAngle = Math.PI * 0.495;
    controls.autoRotateSpeed = 0.7;
    controls.update();

    buildLights();
    envDay = makeEnvironment(false);
    envNight = makeEnvironment(true);
    scene.environment = envDay;

    loadingText.textContent = "正在解压场景数据…";
    setTimeout(loadModel, 40);
    bindUi();
    setPreset(state.preset, true);
    document.querySelectorAll("[data-time]").forEach((x) => {
      x.classList.toggle("active", (x.getAttribute("data-time") === "night") === state.night);
    });
    animate();
  }

  function buildLights() {
    hemi = new THREE.HemisphereLight(0xd7eaff, 0x5c5348, 0.50);
    scene.add(hemi);

    ambient = new THREE.AmbientLight(0xffffff, 0.11);
    scene.add(ambient);

    sun = new THREE.DirectionalLight(0xfff0d9, 0.95);
    sun.position.set(14, 9, 20);
    sun.target.position.set(0, 1.0, 3.5);
    scene.add(sun.target);
    sun.castShadow = true;
    sun.shadow.mapSize.set(2048, 2048);
    sun.shadow.camera.near = 0.5;
    sun.shadow.camera.far = 70;
    sun.shadow.camera.left = -24;
    sun.shadow.camera.right = 24;
    sun.shadow.camera.top = 24;
    sun.shadow.camera.bottom = -24;
    sun.shadow.bias = -0.00035;
    sun.shadow.normalBias = 0.02;
    scene.add(sun);

    fill = new THREE.DirectionalLight(0xa8c8ff, 0.20);
    fill.position.set(-14, 10, 8);
    fill.target.position.set(0, 1, 0);
    scene.add(fill);
    scene.add(fill.target);

    const interiorPositions = [
      [-4.8, 3.18, 2.7], [0.0, 3.18, 2.7], [4.8, 3.18, 2.7],
      [-4.8, 3.18, -0.2], [0.0, 3.18, -0.2], [4.8, 3.18, -0.2],
      [-4.6, 3.18, -3.0], [4.6, 3.18, -3.0],
    ];
    interiorLights = interiorPositions.map((p) => {
      const l = new THREE.PointLight(0xffd4a0, 0.50, 11, 2);
      l.position.set(p[0], p[1], p[2]);
      scene.add(l);
      return l;
    });

    const sign = new THREE.PointLight(0xd24bff, 2.0, 13, 2);
    sign.position.set(0, 4.5, 6.1);
    scene.add(sign);
    signLights.push(sign);

    const canopy = new THREE.PointLight(0xffbd72, 1.1, 9, 2);
    canopy.position.set(-3.55, 3.4, 5.4);
    scene.add(canopy);
    signLights.push(canopy);
  }

  function makeEnvironment(night) {
    const c = document.createElement("canvas");
    c.width = 1024;
    c.height = 512;
    const ctx = c.getContext("2d");
    const g = ctx.createLinearGradient(0, 0, 0, 512);
    if (night) {
      g.addColorStop(0.0, "#02050e");
      g.addColorStop(0.48, "#0a1028");
      g.addColorStop(0.55, "#1b1838");
      g.addColorStop(0.6, "#08090d");
      g.addColorStop(1.0, "#030303");
    } else {
      g.addColorStop(0.0, "#5c95d6");
      g.addColorStop(0.45, "#a9cdec");
      g.addColorStop(0.55, "#e8eef2");
      g.addColorStop(0.62, "#b8b5a8");
      g.addColorStop(1.0, "#4d4a42");
    }
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, 1024, 512);

    if (!night) {
      const sunGrad = ctx.createRadialGradient(760, 170, 2, 760, 170, 120);
      sunGrad.addColorStop(0, "rgba(255,245,215,0.95)");
      sunGrad.addColorStop(0.16, "rgba(255,237,195,0.48)");
      sunGrad.addColorStop(1, "rgba(255,237,195,0)");
      ctx.fillStyle = sunGrad;
      ctx.fillRect(0, 0, 1024, 512);
    } else {
      for (let i = 0; i < 80; i++) {
        const x = Math.random() * 1024;
        const y = Math.random() * 230;
        const a = 0.15 + Math.random() * 0.65;
        ctx.fillStyle = `rgba(210,225,255,${a})`;
        ctx.fillRect(x, y, Math.random() < 0.2 ? 2 : 1, 1);
      }
    }

    const tex = new THREE.CanvasTexture(c);
    tex.mapping = THREE.EquirectangularReflectionMapping;
    tex.encoding = THREE.sRGBEncoding;
    const pmrem = new THREE.PMREMGenerator(renderer);
    pmrem.compileEquirectangularShader();
    const env = pmrem.fromEquirectangular(tex).texture;
    tex.dispose();
    pmrem.dispose();
    return env;
  }

  function loadModel() {
    let bytes;
    try {
      const raw = atob(window.POPURI_GLB_GZIP_BASE64);
      bytes = new Uint8Array(raw.length);
      for (let i = 0; i < raw.length; i++) bytes[i] = raw.charCodeAt(i);
    } catch (err) {
      showFail("场景数据解码失败：" + err.message);
      return;
    }

    loadingText.textContent = "正在解压并构建 3D 场景…";
    let glb;
    try {
      glb = window.pako.inflate(bytes);
    } catch (err) {
      showFail("场景解压失败：" + err.message);
      return;
    }
    const buffer = glb.buffer.slice(glb.byteOffset, glb.byteOffset + glb.byteLength);
    const loader = new THREE.GLTFLoader();

    loader.parse(buffer, "", (gltf) => {
      const root = gltf.scene;
      root.traverse((obj) => {
        if (obj.isMesh) {
          obj.castShadow = true;
          obj.receiveShadow = true;
          obj.frustumCulled = true;
          const mats = Array.isArray(obj.material) ? obj.material : [obj.material];
          mats.forEach(upgradeMaterial);
        }
        if (obj.name.indexOf("RoofGroup") !== -1) {
          roofGroup = obj;
          if (state.roofHidden) obj.visible = false;
        }
        if (obj.name.indexOf("Stars") !== -1) stars = obj;
      });
      scene.add(root);
      if (stars) stars.visible = false;
      applyLighting();
      loading.style.display = "none";
      status.textContent = "拖动旋转 · 滚轮缩放 · 右键平移";
      // One shadow update, then freeze the map until lights change.
      renderer.shadowMap.autoUpdate = true;
    }, (err) => {
      showFail("3D 场景加载失败：" + (err.message || err));
    });
  }

  function upgradeMaterial(mat) {
    if (!mat) return;
    const name = mat.name || "";

    if (name.indexOf("Glass") !== -1) {
      const freezer = name.toLowerCase().indexOf("freezer") !== -1;
      mat.transparent = true;
      mat.opacity = freezer ? 0.17 : 0.11;
      mat.depthWrite = false;
      mat.roughness = freezer ? 0.08 : 0.035;
      mat.metalness = 0.0;
      mat.envMapIntensity = 2.0;
      mat.side = THREE.DoubleSide;
      mat.color = new THREE.Color(freezer ? 0xc9edf0 : 0xd8f0ea);
      mat.needsUpdate = true;
      return;
    }

    mat.envMapIntensity = 0.28;

    // Restore the neon / luminaire values that glTF cannot carry directly.
    if (name.indexOf("purple emission") !== -1) {
      mat.emissive = new THREE.Color(0x540a9e);
      mat.emissiveIntensity = 0.95;
      mat.color = new THREE.Color(0x140020);
      mat.roughness = 0.26;
    } else if (name.indexOf("pink strips") !== -1) {
      mat.emissive = new THREE.Color(0xff147e);
      mat.emissiveIntensity = 1.35;
      mat.color = new THREE.Color(0x3a001b);
    } else if (name.indexOf("ivory letters") !== -1) {
      mat.emissive = new THREE.Color(0xffac24);
      mat.emissiveIntensity = 1.45;
      mat.color = new THREE.Color(0x3a2201);
    } else if (name.indexOf("warm diffuser") !== -1) {
      mat.emissive = new THREE.Color(0xffd39a);
      mat.emissiveIntensity = 2.4;
      mat.color = new THREE.Color(0x5c4b31);
    } else if (name.indexOf("cold case") !== -1) {
      mat.emissive = new THREE.Color(0x48b9ff);
      mat.emissiveIntensity = 2.2;
      mat.color = new THREE.Color(0x0a2a3b);
    } else if (name.indexOf("POS screen") !== -1) {
      mat.emissive = new THREE.Color(0x3bc3e6);
      mat.emissiveIntensity = 1.3;
    } else if (name.indexOf("heat lamp") !== -1) {
      mat.emissive = new THREE.Color(0xff3c09);
      mat.emissiveIntensity = 1.6;
    } else if (name.indexOf("white backing") !== -1) {
      mat.emissive = new THREE.Color(0xfff2d8);
      mat.emissiveIntensity = 0.35;
    } else if (name.indexOf("purple emission") !== -1 || name.indexOf("Sign | purple emission") !== -1) {
      mat.emissive = new THREE.Color(0x8e27ff);
      mat.emissiveIntensity = 1.4;
    }
    mat.envMapIntensity = 0.28;
    mat.needsUpdate = true;
  }

  function applyLighting() {
    const night = state.night;
    scene.background = new THREE.Color(night ? 0x040817 : 0x9dc4e8);
    scene.environment = night ? envNight : envDay;

    hemi.intensity = (night ? 0.12 : 0.50) * state.ambient;
    ambient.intensity = (night ? 0.025 : 0.11) * state.ambient;
    sun.intensity = night ? 0.06 : 0.95;
    fill.intensity = night ? 0.025 : 0.20 * state.ambient;

    interiorLights.forEach((l) => {
      l.intensity = (night ? 1.85 : 0.50) * state.indoor;
    });
    signLights[0].intensity = night ? 1.2 : 0.45;
    signLights[1].intensity = night ? 1.4 : 0.30;

    if (stars) stars.visible = night;
    document.body.classList.toggle("is-night", night);
    if (renderer) {
      renderer.toneMappingExposure = state.exposure;
      renderer.shadowMap.needsUpdate = true;
    }
  }

  function setPreset(key, immediate) {
    const p = PRESETS[key];
    if (!p) return;
    state.preset = key;
    document.querySelectorAll("[data-preset]").forEach((b) => {
      b.classList.toggle("active", b.getAttribute("data-preset") === key);
    });
    if (key === "aerial") {
      state.roofHidden = true;
      const roofCheck = document.getElementById("roof");
      if (roofCheck) roofCheck.checked = true;
      if (roofGroup) roofGroup.visible = false;
      if (renderer) renderer.shadowMap.needsUpdate = true;
    }
    // The close-up camera views should not be hidden by the control panel.
    setPanelVisible(!(key === "entrance" || key === "checkout" || key === "sign"));
    const targetPos = new THREE.Vector3().fromArray(p.pos);
    const targetLook = new THREE.Vector3().fromArray(p.target);
    if (immediate) {
      camera.position.copy(targetPos);
      controls.target.copy(targetLook);
      camera.fov = p.fov;
      camera.updateProjectionMatrix();
      controls.update();
      return;
    }
    fromState = {
      pos: camera.position.clone(),
      target: controls.target.clone(),
      fov: camera.fov,
    };
    toState = { pos: targetPos, target: targetLook, fov: p.fov };
    tweenStart = performance.now();
    controls.autoRotate = false;
    document.getElementById("spin").checked = false;
  }

  function updateTween(now) {
    if (!toState) return;
    const t = Math.min(1, (now - tweenStart) / tweenDur);
    const e = 1 - Math.pow(1 - t, 3);
    camera.position.lerpVectors(fromState.pos, toState.pos, e);
    controls.target.lerpVectors(fromState.target, toState.target, e);
    camera.fov = fromState.fov + (toState.fov - fromState.fov) * e;
    camera.updateProjectionMatrix();
    if (t >= 1) {
      toState = null;
    }
  }

  function setPanelVisible(visible) {
    document.body.classList.toggle("panel-hidden", !visible);
  }

  function bindUi() {
    const hidePanel = document.getElementById("hidePanel");
    const showPanel = document.getElementById("showPanel");
    if (hidePanel) hidePanel.addEventListener("click", () => setPanelVisible(false));
    if (showPanel) showPanel.addEventListener("click", () => setPanelVisible(true));

    document.querySelectorAll("[data-preset]").forEach((b) => {
      b.addEventListener("click", () => setPreset(b.getAttribute("data-preset"), false));
    });

    document.querySelectorAll("[data-time]").forEach((b) => {
      b.addEventListener("click", () => {
        state.night = b.getAttribute("data-time") === "night";
        document.querySelectorAll("[data-time]").forEach((x) => x.classList.toggle("active", x === b));
        applyLighting();
      });
    });

    const exposure = document.getElementById("exposure");
    const exposureVal = document.getElementById("exposureVal");
    exposure.addEventListener("input", () => {
      state.exposure = parseFloat(exposure.value);
      exposureVal.textContent = state.exposure.toFixed(2);
      renderer.toneMappingExposure = state.exposure;
    });

    const ambient = document.getElementById("ambient");
    const ambientVal = document.getElementById("ambientVal");
    ambient.addEventListener("input", () => {
      state.ambient = parseFloat(ambient.value);
      ambientVal.textContent = state.ambient.toFixed(2);
      applyLighting();
    });

    const indoor = document.getElementById("indoor");
    const indoorVal = document.getElementById("indoorVal");
    indoor.addEventListener("input", () => {
      state.indoor = parseFloat(indoor.value);
      indoorVal.textContent = state.indoor.toFixed(2);
      applyLighting();
    });

    const roof = document.getElementById("roof");
    roof.addEventListener("change", () => {
      state.roofHidden = roof.checked;
      if (roofGroup) roofGroup.visible = !state.roofHidden;
      renderer.shadowMap.needsUpdate = true;
    });

    const spin = document.getElementById("spin");
    spin.addEventListener("change", () => {
      controls.autoRotate = spin.checked;
    });

    document.getElementById("reset").addEventListener("click", () => {
      setPreset("overview", false);
    });

    window.addEventListener("resize", onResize);
    window.addEventListener("keydown", (event) => {
      const map = { "1": "overview", "2": "interior", "3": "checkout", "4": "entrance", "5": "sign" };
      if (map[event.key]) setPreset(map[event.key], false);
      if (event.key.toLowerCase() === "d") document.querySelector('[data-time="day"]').click();
      if (event.key.toLowerCase() === "n") document.querySelector('[data-time="night"]').click();
    });
  }

  function onResize() {
    const w = window.innerWidth;
    const h = window.innerHeight;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(w, h);
  }

  function animate(now) {
    requestAnimationFrame(animate);
    const t = now || performance.now();
    updateTween(t);
    controls.update();
    renderer.render(scene, camera);
    // Once the static shadow map has been drawn, stop re-rendering it each frame.
    if (renderer.shadowMap.autoUpdate) {
      renderer.shadowMap.autoUpdate = false;
    }
  }

  init();
})();
