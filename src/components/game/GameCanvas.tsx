import { useEffect, useRef } from "react";
import * as THREE from "three";
import { PointerLockControls } from "three/examples/jsm/controls/PointerLockControls.js";
import { NPCS } from "@/constants/npcs";

import skyUrl from "@/assets/game/sky.jpg";
import cobbleUrl from "@/assets/game/cobble.jpg";
import stoneUrl from "@/assets/game/stone.jpg";
import mageUrl from "@/assets/game/mage.jpg";
import woodUrl from "@/assets/game/wood.jpg";
import roofUrl from "@/assets/game/roof.jpg";

interface Props {
  paused: boolean;
  onNearbyChange: (npcId: string | null) => void;
  onInteract: (npcId: string) => void;
}

export function GameCanvas({ paused, onNearbyChange, onInteract }: Props) {
  const mountRef = useRef<HTMLDivElement>(null);
  const pausedRef = useRef(paused);
  const nearbyRef = useRef<string | null>(null);
  const interactRef = useRef(onInteract);
  const nearbyCbRef = useRef(onNearbyChange);

  useEffect(() => { pausedRef.current = paused; }, [paused]);
  useEffect(() => { interactRef.current = onInteract; }, [onInteract]);
  useEffect(() => { nearbyCbRef.current = onNearbyChange; }, [onNearbyChange]);

  useEffect(() => {
    const mount = mountRef.current!;
    const w = () => mount.clientWidth;
    const h = () => mount.clientHeight;

    // Scene
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0a0a1a);
    scene.fog = new THREE.FogExp2(0x0a0a1a, 0.04);

    const camera = new THREE.PerspectiveCamera(72, w() / h(), 0.1, 200);
    camera.position.set(0, 1.7, 6);

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(w(), h());
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    mount.appendChild(renderer.domElement);

    // Loader
    const texLoader = new THREE.TextureLoader();
    const loadTex = (url: string, repeat = 1) => {
      const t = texLoader.load(url);
      t.colorSpace = THREE.SRGBColorSpace;
      t.wrapS = t.wrapT = THREE.RepeatWrapping;
      t.repeat.set(repeat, repeat);
      t.anisotropy = 8;
      return t;
    };

    // Skybox (inverted sphere)
    const skyTex = texLoader.load(skyUrl);
    skyTex.colorSpace = THREE.SRGBColorSpace;
    skyTex.mapping = THREE.EquirectangularReflectionMapping;
    const skyGeo = new THREE.SphereGeometry(80, 40, 20);
    const skyMat = new THREE.MeshBasicMaterial({ map: skyTex, side: THREE.BackSide, fog: false, depthWrite: false });
    const skyMesh = new THREE.Mesh(skyGeo, skyMat);
    scene.add(skyMesh);

    // Ground
    const groundTex = loadTex(cobbleUrl, 20);
    const ground = new THREE.Mesh(
      new THREE.PlaneGeometry(120, 120),
      new THREE.MeshStandardMaterial({ map: groundTex, roughness: 0.95 })
    );
    ground.rotation.x = -Math.PI / 2;
    ground.receiveShadow = true;
    scene.add(ground);

    // Lighting
    const ambient = new THREE.AmbientLight(0x223355, 0.45);
    scene.add(ambient);
    const moon = new THREE.DirectionalLight(0x8aa0d6, 0.35);
    moon.position.set(20, 40, 10);
    scene.add(moon);

    // Helper to build a building
    interface BuildingOpts {
      pos: [number, number, number];
      size: [number, number, number]; // w, h, d
      wallTex: THREE.Texture;
      roofTex: THREE.Texture;
      torchColor: number;
      label: string;
    }
    const buildings: THREE.Object3D[] = [];

    function makeBuilding({ pos, size, wallTex, roofTex, torchColor }: BuildingOpts) {
      const group = new THREE.Group();
      group.position.set(pos[0], 0, pos[2]);
      const [bw, bh, bd] = size;

      const wallMat = new THREE.MeshStandardMaterial({ map: wallTex, roughness: 0.9 });
      const walls = new THREE.Mesh(new THREE.BoxGeometry(bw, bh, bd), wallMat);
      walls.position.y = bh / 2;
      group.add(walls);

      // Door (dark inset plane)
      const door = new THREE.Mesh(
        new THREE.PlaneGeometry(1.4, 2.4),
        new THREE.MeshStandardMaterial({ color: 0x110805, roughness: 1 })
      );
      door.position.set(0, 1.2, bd / 2 + 0.01);
      group.add(door);

      // Roof (pyramid)
      const roofMat = new THREE.MeshStandardMaterial({ map: roofTex, roughness: 0.85 });
      const roof = new THREE.Mesh(
        new THREE.ConeGeometry(Math.max(bw, bd) * 0.78, bh * 0.55, 4),
        roofMat
      );
      roof.rotation.y = Math.PI / 4;
      roof.position.y = bh + bh * 0.275;
      group.add(roof);

      // Torches (two flanking the door)
      for (const offset of [-bw / 2 + 0.4, bw / 2 - 0.4]) {
        const torchBase = new THREE.Mesh(
          new THREE.CylinderGeometry(0.05, 0.08, 0.6, 6),
          new THREE.MeshStandardMaterial({ color: 0x2a1a08, roughness: 1 })
        );
        torchBase.position.set(offset, 2.0, bd / 2 + 0.2);
        group.add(torchBase);

        const flame = new THREE.Mesh(
          new THREE.SphereGeometry(0.13, 8, 8),
          new THREE.MeshBasicMaterial({ color: torchColor })
        );
        flame.position.set(offset, 2.4, bd / 2 + 0.2);
        group.add(flame);

        const light = new THREE.PointLight(torchColor, 2.2, 14, 1.6);
        light.position.set(offset, 2.5, bd / 2 + 0.3);
        group.add(light);

        // Store for flicker
        (light as any).userData.base = 2.2;
        flickerLights.push(light);
      }

      scene.add(group);
      buildings.push(group);
    }

    const flickerLights: THREE.PointLight[] = [];

    const stoneTex = loadTex(stoneUrl, 3);
    const mageTex  = loadTex(mageUrl, 3);
    const woodTex  = loadTex(woodUrl, 3);
    const roofTex  = loadTex(roofUrl, 4);

    // Temple (left)
    makeBuilding({
      pos: [-18, 0, 0], size: [9, 6, 8], wallTex: stoneTex, roofTex,
      torchColor: 0xff6a1c, label: "Temple",
    });
    // Mages Guild (right)
    makeBuilding({
      pos: [18, 0, 0], size: [9, 7, 8], wallTex: mageTex, roofTex,
      torchColor: 0xb070ff, label: "Mages Guild",
    });
    // Market stall (back)
    makeBuilding({
      pos: [0, 0, -20], size: [10, 4, 6], wallTex: woodTex, roofTex,
      torchColor: 0xffb060, label: "Market",
    });

    // NPC sprites + glow lights
    interface NpcEntry { id: string; sprite: THREE.Sprite; light: THREE.PointLight; }
    const npcEntries: NpcEntry[] = [];

    for (const npc of NPCS) {
      const tex = texLoader.load(npc.sprite);
      tex.colorSpace = THREE.SRGBColorSpace;
      const mat = new THREE.SpriteMaterial({ map: tex, transparent: true, alphaTest: 0.2, depthWrite: false });
      const sprite = new THREE.Sprite(mat);
      sprite.scale.set(1.8, 3.6, 1);
      sprite.position.set(npc.position[0], 1.8, npc.position[2]);
      sprite.userData.npcId = npc.id;
      scene.add(sprite);

      // Make sprite face the door (rotate so they look outward)
      // Glow light
      const light = new THREE.PointLight(npc.glow, 1.4, 6, 2);
      light.position.set(npc.position[0], 1.4, npc.position[2]);
      scene.add(light);

      // Ground glow disc
      const disc = new THREE.Mesh(
        new THREE.CircleGeometry(0.9, 24),
        new THREE.MeshBasicMaterial({ color: npc.glow, transparent: true, opacity: 0.25, depthWrite: false })
      );
      disc.rotation.x = -Math.PI / 2;
      disc.position.set(npc.position[0], 0.02, npc.position[2]);
      scene.add(disc);

      npcEntries.push({ id: npc.id, sprite, light });
    }

    // Controls
    const controls = new PointerLockControls(camera, renderer.domElement);
    scene.add(controls.object);

    const keys: Record<string, boolean> = {};
    const onKeyDown = (e: KeyboardEvent) => {
      keys[e.code] = true;
      if (e.code === "KeyE" && nearbyRef.current && !pausedRef.current) {
        interactRef.current(nearbyRef.current);
      }
    };
    const onKeyUp = (e: KeyboardEvent) => { keys[e.code] = false; };
    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("keyup", onKeyUp);

    const onCanvasClick = () => {
      if (pausedRef.current) return;
      if (!controls.isLocked) {
        controls.lock();
      } else if (nearbyRef.current) {
        interactRef.current(nearbyRef.current);
      }
    };
    renderer.domElement.addEventListener("click", onCanvasClick);

    // Raycaster for NPC detection
    const raycaster = new THREE.Raycaster();
    const centerNDC = new THREE.Vector2(0, 0);
    const npcSprites = npcEntries.map((n) => n.sprite);

    // Resize
    const onResize = () => {
      camera.aspect = w() / h();
      camera.updateProjectionMatrix();
      renderer.setSize(w(), h());
    };
    window.addEventListener("resize", onResize);

    // Loop
    const playerVel = new THREE.Vector3();
    const playerDir = new THREE.Vector3();
    const clock = new THREE.Clock();
    let frame = 0;

    const loop = () => {
      frame = requestAnimationFrame(loop);
      const dt = Math.min(clock.getDelta(), 0.05);

      // Movement
      if (!pausedRef.current && controls.isLocked) {
        const speed = 5;
        playerVel.set(0, 0, 0);
        if (keys["KeyW"]) playerVel.z -= 1;
        if (keys["KeyS"]) playerVel.z += 1;
        if (keys["KeyA"]) playerVel.x -= 1;
        if (keys["KeyD"]) playerVel.x += 1;
        if (playerVel.lengthSq() > 0) {
          playerVel.normalize().multiplyScalar(speed * dt);
          controls.moveRight(playerVel.x);
          controls.moveForward(-playerVel.z);
        }
      }

      // Keep within bounds
      const p = controls.object.position;
      p.x = Math.max(-55, Math.min(55, p.x));
      p.z = Math.max(-55, Math.min(55, p.z));
      p.y = 1.7;

      // Torch flicker
      const t = clock.elapsedTime;
      for (const l of flickerLights) {
        const base = (l as any).userData.base ?? 2;
        l.intensity = base * (0.85 + Math.sin(t * 8 + l.position.x) * 0.08 + Math.random() * 0.05);
      }

      // NPC light pulse
      for (const n of npcEntries) {
        n.light.intensity = 1.2 + Math.sin(t * 2 + n.sprite.position.x) * 0.25;
      }

      // Sky subtle rotation
      skyMesh.rotation.y += dt * 0.005;

      // Nearby NPC raycast (look ray from camera)
      camera.getWorldDirection(playerDir);
      raycaster.setFromCamera(centerNDC, camera);
      const hits = raycaster.intersectObjects(npcSprites, false);
      let near: string | null = null;
      if (hits.length) {
        const hit = hits[0];
        const dist = hit.point.distanceTo(camera.position);
        if (dist <= 3.5) near = (hit.object as THREE.Sprite).userData.npcId;
      }
      // Also allow proximity-only detection within 2.2 units even without looking
      if (!near) {
        let best: { id: string; d: number } | null = null;
        for (const n of npcEntries) {
          const d = n.sprite.position.distanceTo(camera.position);
          if (d < 2.2 && (!best || d < best.d)) best = { id: n.id, d };
        }
        if (best) near = best.id;
      }
      if (near !== nearbyRef.current) {
        nearbyRef.current = near;
        nearbyCbRef.current(near);
      }

      renderer.render(scene, camera);
    };
    loop();

    // Pointer lock state sync
    const onLockChange = () => {
      // If paused state forced unlock, that's fine
    };
    document.addEventListener("pointerlockchange", onLockChange);

    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("keyup", onKeyUp);
      window.removeEventListener("resize", onResize);
      document.removeEventListener("pointerlockchange", onLockChange);
      renderer.domElement.removeEventListener("click", onCanvasClick);
      controls.dispose();
      renderer.dispose();
      mount.removeChild(renderer.domElement);
      scene.traverse((o) => {
        const m = o as THREE.Mesh;
        if (m.geometry) m.geometry.dispose();
        if ((m as any).material) {
          const mat = (m as any).material;
          if (Array.isArray(mat)) mat.forEach((mm) => mm.dispose());
          else mat.dispose();
        }
      });
    };
  }, []);

  // When paused, exit pointer lock
  useEffect(() => {
    if (paused && document.pointerLockElement) {
      document.exitPointerLock();
    }
  }, [paused]);

  return <div ref={mountRef} className="absolute inset-0" />;
}
