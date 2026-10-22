import * as THREE from 'three';
import { EyeRenderer } from '@assets/face/eyeRenderer.js';

/**
 * Ojos de Ignis: dibuja los ojos en un canvas y lo aplica como `map` del material FaceScreenMat,
 * asi reciben la luz de la escena (no son una pantalla). Un poco de emision mantiene vivo el blanco.
 */
export class EyeScreen {
  /**
   * @param {THREE.Mesh} mesh malla 'FaceScreen' del GLB (dos parches, UV: ojo izquierdo en u 0-0.5)
   * @param {{ emissive?: number }} [opts]
   */
  constructor(mesh, { emissive = 0.12 } = {}) {
    this.canvas = document.createElement('canvas');
    this.renderer = new EyeRenderer(this.canvas);

    this.texture = new THREE.CanvasTexture(this.canvas);
    this.texture.colorSpace = THREE.SRGBColorSpace;
    this.texture.flipY = false; // UV de glTF: v = 0 arriba
    this.texture.anisotropy = 4;

    const old = mesh.material;
    const mat = old.clone();
    mat.name = 'FaceScreenMat';
    mat.map = this.texture;
    mat.color.set(0xffffff);
    mat.emissive.set(0xffffff);
    mat.emissiveMap = this.texture;
    mat.emissiveIntensity = emissive;
    mat.roughness = 0.45;
    mat.metalness = 0.0;
    mat.needsUpdate = true;
    mesh.material = mat;
    old.map?.dispose();
    old.dispose();
    this.material = mat;
  }

  /** @param {'neutral'|'listening'|'thinking'|'happy'|'surprised'} state */
  setEyes(state) {
    this.renderer.setEyes(state);
  }

  get state() {
    return this.renderer.eyeState;
  }

  update(dt) {
    this.renderer.update(dt);
    this.renderer.draw();
    this.texture.needsUpdate = true;
  }
}
