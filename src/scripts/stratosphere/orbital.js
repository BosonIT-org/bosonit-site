import * as THREE from 'three';

export default function initOrbital(selector = '#orbital'){
  const root = document.querySelector(selector); if (!root) return;
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const W = root.clientWidth || 640, H = root.clientHeight || 360;
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(55, W/H, 0.1, 100);
  camera.position.set(0, 1.2, 3.2);
  const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
  renderer.setSize(W, H, false); renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 2));
  root.innerHTML = ''; root.appendChild(renderer.domElement);

  scene.add(new THREE.AmbientLight(0xffffff, 0.6));
  const dir = new THREE.DirectionalLight(0xffffff, 0.8); dir.position.set(2,3,2); scene.add(dir);
  const core = new THREE.Mesh(new THREE.IcosahedronGeometry(0.35, 0), new THREE.MeshStandardMaterial({ color: 0x4cc9f0, metalness: 0.4, roughness: 0.2 }));
  scene.add(core);

  const nodes = []; const colors = [0x90EE90, 0xFFD580, 0xFF6B6B, 0xA78BFA, 0xF59E0B];
  for (let i=0;i<8;i++){
    const n = new THREE.Mesh(new THREE.SphereGeometry(0.08, 16, 16), new THREE.MeshStandardMaterial({ color: colors[i%colors.length], metalness: 0.3, roughness: 0.5 }));
    n.userData = { r: 0.9 + 0.25*(i%3), spd: 0.4 + 0.1*i, phase: Math.random()*Math.PI*2 };
    scene.add(n); nodes.push(n);
  }
  const ringMat = new THREE.LineBasicMaterial({ color: 0x2a3140, transparent: true, opacity: 0.7 });
  [0.9, 1.15, 1.4].forEach((R)=>{ const g = new THREE.BufferGeometry(); const pts = []; for(let a=0;a<Math.PI*2+0.01;a+=0.1){ pts.push(new THREE.Vector3(Math.cos(a)*R, 0, Math.sin(a)*R)); } g.setFromPoints(pts); scene.add(new THREE.LineLoop(g, ringMat)); });

  const raycaster = new THREE.Raycaster(); const mouse = new THREE.Vector2(); let hover;
  function onMouseMove(ev){ const r = renderer.domElement.getBoundingClientRect(); mouse.x = ((ev.clientX - r.left)/r.width)*2 - 1; mouse.y = -((ev.clientY - r.top)/r.height)*2 + 1; }
  renderer.domElement.addEventListener('mousemove', onMouseMove);

  let t = 0; let raf = null; const tick = () => {
    t += reduceMotion ? 0.0 : 0.016;
    nodes.forEach((n)=>{ const {r, spd, phase} = n.userData; const a = t*spd + phase; n.position.set(Math.cos(a)*r, 0.06*Math.sin(t*0.9+phase), Math.sin(a)*r); });
    core.rotation.y += 0.006; core.rotation.x += 0.002;
    raycaster.setFromCamera(mouse, camera); const hits = raycaster.intersectObjects(nodes);
    if (hits[0]) { if (hover !== hits[0].object) { if (hover) hover.scale.set(1,1,1); hover = hits[0].object; hover.scale.set(1.6,1.6,1.6);} } else if (hover) { hover.scale.set(1,1,1); hover = null; }
    renderer.render(scene, camera); raf = requestAnimationFrame(tick);
  };
  const start = () => { if (!raf) raf = requestAnimationFrame(tick); };
  const stop = () => { if (raf) cancelAnimationFrame(raf); raf = null; };
  start();
  const onResize = () => { const W2 = root.clientWidth || W, H2 = root.clientHeight || H; camera.aspect = W2/H2; camera.updateProjectionMatrix(); renderer.setSize(W2, H2, false); };
  window.addEventListener('resize', onResize); new ResizeObserver(onResize).observe(root);
  const io = new IntersectionObserver(([e]) => { e.isIntersecting ? start() : stop(); }); io.observe(root);
}

