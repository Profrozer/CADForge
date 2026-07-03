import { useEffect, useRef } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { STLLoader } from "three/addons/loaders/STLLoader.js";

// Dark metrology stage: grid floor, soft key/fill lights, orbit controls.
export default function Viewport({ stlUrl, onSnapshot, busy }) {
  const mountRef = useRef(null);
  const stateRef = useRef(null);

  useEffect(() => {
    const mount = mountRef.current;
    const scene = new THREE.Scene();

    const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 5000);
    camera.position.set(120, 90, 120);

    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
      preserveDrawingBuffer: true,
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    mount.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;

    scene.add(new THREE.HemisphereLight(0x8fb8e8, 0x0a1020, 1.1));
    const key = new THREE.DirectionalLight(0xffffff, 1.6);
    key.position.set(80, 140, 60);
    scene.add(key);
    const rim = new THREE.DirectionalLight(0x67e0ff, 0.5);
    rim.position.set(-90, 40, -80);
    scene.add(rim);

    const grid = new THREE.GridHelper(400, 40, 0x1d4a66, 0x122236);
    grid.material.transparent = true;
    grid.material.opacity = 0.55;
    scene.add(grid);

    const axes = new THREE.AxesHelper(28);
    scene.add(axes);

    const resize = () => {
      const { clientWidth: w, clientHeight: h } = mount;
      if (!w || !h) return;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    const observer = new ResizeObserver(resize);
    observer.observe(mount);
    resize();

    let alive = true;
    const loop = () => {
      if (!alive) return;
      controls.update();
      renderer.render(scene, camera);
      requestAnimationFrame(loop);
    };
    loop();

    stateRef.current = { scene, camera, renderer, controls, grid, mesh: null };
    return () => {
      alive = false;
      observer.disconnect();
      renderer.dispose();
      mount.removeChild(renderer.domElement);
      stateRef.current = null;
    };
  }, []);

  useEffect(() => {
    const state = stateRef.current;
    if (!state) return;
    if (state.mesh) {
      state.scene.remove(state.mesh);
      state.mesh.geometry.dispose();
      state.mesh.material.dispose();
      state.mesh = null;
    }
    if (!stlUrl) return;

    let cancelled = false;
    new STLLoader().load(stlUrl, (geometry) => {
      if (cancelled || !stateRef.current) return;
      geometry.computeVertexNormals();
      geometry.computeBoundingBox();
      const bb = geometry.boundingBox;
      const center = new THREE.Vector3();
      bb.getCenter(center);
      // Rest the part on the grid, centered.
      geometry.translate(-center.x, -center.y, -bb.min.z);
      // CadQuery is Z-up; three.js is Y-up.
      geometry.rotateX(-Math.PI / 2);

      const material = new THREE.MeshStandardMaterial({
        color: 0x9db8dc,
        metalness: 0.45,
        roughness: 0.38,
      });
      const mesh = new THREE.Mesh(geometry, material);
      state.scene.add(mesh);
      state.mesh = mesh;

      const size = new THREE.Vector3();
      bb.getSize(size);
      const radius = Math.max(size.x, size.y, size.z, 1);
      state.camera.position.set(radius * 1.6, radius * 1.2, radius * 1.6);
      state.controls.target.set(0, size.z * 0.35, 0);
      state.controls.update();

      // Client-rendered thumbnail for the history rail.
      if (onSnapshot) {
        state.renderer.render(state.scene, state.camera);
        const src = state.renderer.domElement;
        const thumb = document.createElement("canvas");
        const scale = 256 / Math.max(src.width, src.height, 1);
        thumb.width = Math.max(1, Math.round(src.width * scale));
        thumb.height = Math.max(1, Math.round(src.height * scale));
        thumb.getContext("2d").drawImage(src, 0, 0, thumb.width, thumb.height);
        onSnapshot(thumb.toDataURL("image/png"));
      }
    });
    return () => {
      cancelled = true;
    };
  }, [stlUrl]);

  return (
    <div className="glass hud-corners relative flex-1 min-h-0 overflow-hidden">
      <span className="hud-b" />
      <div ref={mountRef} className="absolute inset-0" />
      {!stlUrl && !busy && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 pointer-events-none">
          <svg width="72" height="72" viewBox="0 0 24 24" className="opacity-40">
            <path
              fill="none"
              stroke="#67E0FF"
              strokeWidth="0.9"
              d="M12 2 21 7v10l-9 5-9-5V7z M12 2v10 M21 7l-9 5-9-5 M12 12v10"
            />
          </svg>
          <p className="font-mono text-xs tracking-[0.3em] text-muted">
            NO SOLID LOADED
          </p>
          <p className="text-sm text-muted/80 max-w-xs text-center">
            Describe a part below and CADForge will forge real parametric
            geometry into this stage.
          </p>
        </div>
      )}
      <div className="absolute top-3 left-1/2 -translate-x-1/2 font-mono text-[10px] tracking-[0.35em] text-line/50 pointer-events-none">
        ISO VIEW · ORBIT / PAN / ZOOM
      </div>
    </div>
  );
}
