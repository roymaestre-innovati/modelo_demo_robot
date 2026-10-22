import * as THREE from 'three';

const SPARKS = 48;

/** Textura redonda y difusa para las chispas (canvas: sin archivos extra que puedan dar 404). */
function sparkTexture() {
  const c = document.createElement('canvas');
  c.width = c.height = 64;
  const ctx = c.getContext('2d');
  const g = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
  g.addColorStop(0, 'rgba(255,255,255,1)');
  g.addColorStop(0.35, 'rgba(255,255,255,0.8)');
  g.addColorStop(1, 'rgba(255,255,255,0)');
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 64, 64);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

/**
 * Efectos de la llama de la cola, solo en three.js: parpadeo de escala y emision, una luz calida
 * que la acompana y chispas (Points) que suben y se apagan.
 */
export class FlameEffects {
  /** @param {THREE.Scene} scene @param {THREE.Mesh} flame malla TailFlame (origen en su base) */
  constructor(scene, flame) {
    this.flame = flame;
    this.time = 0;
    this.baseScale = flame.scale.clone();
    // menos color base y mas emision: con NeutralToneMapping la llama se lava a melocoton si no
    this.materials = (Array.isArray(flame.material) ? flame.material : [flame.material]).map((m) => {
      const c = m.clone();
      c.color.multiplyScalar(0.3);
      c.emissiveIntensity *= 1.2;
      return c;
    });
    flame.material = Array.isArray(flame.material) ? this.materials : this.materials[0];
    this.baseEmissive = this.materials.map((m) => m.emissiveIntensity);
    flame.castShadow = false;

    this.light = new THREE.PointLight(0xff8a2a, 0.8, 1.8, 2);
    scene.add(this.light);

    const geo = new THREE.BufferGeometry();
    this.pos = new Float32Array(SPARKS * 3);
    this.col = new Float32Array(SPARKS * 3);
    this.vel = new Float32Array(SPARKS * 3);
    this.life = new Float32Array(SPARKS);
    this.age = new Float32Array(SPARKS);
    geo.setAttribute('position', new THREE.BufferAttribute(this.pos, 3));
    geo.setAttribute('color', new THREE.BufferAttribute(this.col, 3));
    this.points = new THREE.Points(geo, new THREE.PointsMaterial({
      size: 0.09, map: sparkTexture(), vertexColors: true, transparent: true, depthWrite: false,
      blending: THREE.AdditiveBlending, sizeAttenuation: true,
    }));
    this.points.frustumCulled = false;
    scene.add(this.points);
    this._base = new THREE.Vector3();
    for (let i = 0; i < SPARKS; i++) this.age[i] = this.life[i] = Math.random(); // arranque escalonado
  }

  _spawn(i) {
    const b = this._base;
    const a = Math.random() * Math.PI * 2;
    const r = Math.random() * 0.05;
    this.pos.set([b.x + Math.cos(a) * r, b.y + 0.05 + Math.random() * 0.12, b.z + Math.sin(a) * r], i * 3);
    this.vel.set([(Math.random() - 0.5) * 0.12, 0.22 + Math.random() * 0.3, (Math.random() - 0.5) * 0.12], i * 3);
    this.life[i] = 0.7 + Math.random() * 0.9;
    this.age[i] = 0;
  }

  update(dt) {
    this.time += dt;
    const t = this.time;
    const n = (a, b, c) => Math.sin(t * a) * 0.5 + Math.sin(t * b + 1.7) * 0.3 + Math.sin(t * c + 0.4) * 0.2;
    // parpadeo de la llama: escala desde su base y emision
    const s = 1 + 0.07 * n(9.1, 13.7, 23.3);
    this.flame.scale.copy(this.baseScale).multiplyScalar(s);
    const e = 0.85 + 0.3 * (0.5 + 0.5 * n(11.3, 17.9, 29.1));
    this.materials.forEach((m, i) => (m.emissiveIntensity = this.baseEmissive[i] * e));

    this.flame.getWorldPosition(this._base);
    this.light.position.copy(this._base).add({ x: 0, y: 0.18, z: 0 });
    this.light.intensity = 0.8 * e;

    for (let i = 0; i < SPARKS; i++) {
      this.age[i] += dt;
      if (this.age[i] >= this.life[i]) this._spawn(i);
      const k = i * 3;
      this.vel[k + 1] -= 0.05 * dt; // apenas frenan al subir
      for (let j = 0; j < 3; j++) this.pos[k + j] += this.vel[k + j] * dt;
      const f = 1 - this.age[i] / this.life[i]; // con mezcla aditiva, oscurecer = apagar
      const glow = Math.min(1, f * 1.6);
      this.col[k] = glow;
      this.col[k + 1] = (0.5 + 0.4 * f) * glow;
      this.col[k + 2] = 0.2 * f * glow;
    }
    this.points.geometry.attributes.position.needsUpdate = true;
    this.points.geometry.attributes.color.needsUpdate = true;
  }
}
