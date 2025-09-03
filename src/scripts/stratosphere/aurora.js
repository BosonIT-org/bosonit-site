import * as THREE from 'three';

export default function initAurora(selectors = ['#aurora', '#aurora2']) {
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const els = selectors.flatMap(sel => Array.from(document.querySelectorAll(sel))).filter(Boolean);
  els.forEach((root) => mount(root, { reduceMotion }));
}

function mount(root, opts) {
  const w = root.clientWidth || root.offsetWidth || root.parentElement?.clientWidth || window.innerWidth;
  const h = root.clientHeight || 360;
  const scene = new THREE.Scene();
  const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
  const renderer = new THREE.WebGLRenderer({ antialias: false, alpha: true });
  renderer.setSize(w, h, false);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  root.innerHTML = '';
  root.appendChild(renderer.domElement);

  const uniforms = {
    u_time: { value: 0 },
    u_res: { value: new THREE.Vector2(w, h) },
    u_hue: { value: Math.random() },
  };
  const material = new THREE.ShaderMaterial({
    uniforms,
    fragmentShader: `precision highp float; uniform float u_time; uniform vec2 u_res; uniform float u_hue; vec3 hsl2rgb(vec3 c){ vec3 rgb = clamp(abs(mod(c.x*6.0+vec3(0,4,2),6.0)-3.0)-1.0,0.0,1.0); return c.z + c.y*(rgb-0.5)*(1.0-abs(2.0*c.z-1.0)); } float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1,311.7)))*43758.5453123); } float noise(in vec2 p){ vec2 i = floor(p), f = fract(p); float a = hash(i), b = hash(i+vec2(1.0,0.0)); float c = hash(i+vec2(0.0,1.0)), d = hash(i+vec2(1.0,1.0)); vec2 u = f*f*(3.0-2.0*f); return mix(a,b,u.x) + (c-a)*u.y*(1.0-u.x) + (d-b)*u.x*u.y; } void main(){ vec2 uv = gl_FragCoord.xy / u_res.xy; uv.y = 1.0-uv.y; float t = u_time*0.05; float n = noise(uv*4.0 + vec2(t, -t*0.6)) * 0.6 + noise(uv*2.0 - vec2(t*0.5, t*0.3))*0.4; float l = 0.45 + 0.25*n + 0.15*pow(uv.y, 2.0); vec3 col = hsl2rgb(vec3(u_hue + 0.08*sin(t*0.2) + 0.02*n, 0.65, l)); gl_FragColor = vec4(col, 0.85); }`,
    vertexShader: `void main(){ gl_Position = vec4(position, 1.0); }`,
    transparent: true,
  });
  const quad = new THREE.Mesh(new THREE.PlaneGeometry(2,2), material);
  scene.add(quad);

  let raf = null; let last = performance.now();
  const tick = (now) => {
    const dt = (now - last) / 16.6667; last = now;
    uniforms.u_time.value += opts.reduceMotion ? 0.0 : dt;
    renderer.render(scene, camera);
    raf = requestAnimationFrame(tick);
  };

  const start = () => { if (!raf) { last = performance.now(); raf = requestAnimationFrame(tick); } };
  const stop = () => { if (raf) cancelAnimationFrame(raf); raf = null; };
  start();

  const onResize = () => { const W = root.clientWidth || window.innerWidth; const H = root.clientHeight || h; uniforms.u_res.value.set(W, H); renderer.setSize(W, H, false); };
  window.addEventListener('resize', onResize);
  const obs = new ResizeObserver(onResize); obs.observe(root);

  const io = new IntersectionObserver(([e]) => { e.isIntersecting ? start() : stop(); });
  io.observe(root);
}

