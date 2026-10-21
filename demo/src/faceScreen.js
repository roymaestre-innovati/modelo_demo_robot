import * as THREE from 'three';
import { FaceRenderer, ACCENT } from '@assets/face/faceRenderer.js';

/**
 * Pantalla-cara de Robin: dibuja ojos y boca en un canvas y lo aplica como
 * emissiveMap del material FaceScreenMat (reemplaza la textura de ejemplo del GLB).
 */
export class FaceScreen {
  /**
   * @param {THREE.Mesh} mesh malla 'FaceScreen' del GLB
   * @param {{ accent?: string, intensity?: number }} [opts]
   */
  constructor(mesh, { accent = ACCENT, intensity = 1.6 } = {}) {
    this.canvas = document.createElement('canvas');
    this.face = new FaceRenderer(this.canvas, { accent });

    this.texture = new THREE.CanvasTexture(this.canvas);
    this.texture.colorSpace = THREE.SRGBColorSpace;
    this.texture.flipY = false; // UV de glTF: v = 0 arriba
    this.texture.anisotropy = 4;

    const old = mesh.material;
    const mat = old.clone();
    mat.name = 'FaceScreenMat';
    mat.map = null;
    mat.color.set(0x000000);
    mat.emissive.set(0xffffff);
    mat.emissiveMap = this.texture;
    mat.emissiveIntensity = intensity;
    mat.roughness = 0.22;
    mat.metalness = 0.0;
    mat.envMapIntensity = 0.2; // reflejo sutil: que no tape la cara
    mat.needsUpdate = true;
    mesh.material = mat;
    old.emissiveMap?.dispose();
    old.dispose();
    this.material = mat;
    this.mouthChanges = 0;
  }

  /** @param {'neutral'|'listening'|'thinking'|'happy'|'surprised'} state */
  setEyes(state) {
    this.face.setEyes(state);
  }

  /** @param {'REST'|'MBP'|'FV'|'A'|'E'|'O'|'U'|'CONS'} shape */
  setMouth(shape) {
    if (shape !== this.face.mouthShape) this.mouthChanges++;
    this.face.setMouth(shape);
  }

  get eyes() {
    return this.face.eyeState;
  }

  get mouth() {
    return this.face.mouthShape;
  }

  update(dt) {
    this.face.update(dt);
    this.face.draw();
    this.texture.needsUpdate = true;
  }
}
