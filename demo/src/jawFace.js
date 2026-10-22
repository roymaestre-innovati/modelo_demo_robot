import * as THREE from 'three';
import { EyeScreen } from './eyeScreen.js';

// Forma de boca -> [jawOpen, wide, round] (tabla de dragon/prompt.dragon.md; ajustes en el README)
export const MOUTH_POSES = Object.freeze({
  REST: [0, 0, 0],
  MBP: [0, 0, 0],
  FV: [0.1, 0.2, 0],
  A: [0.8, 0.2, 0],
  E: [0.45, 0.7, 0],
  O: [0.6, 0, 0.7],
  U: [0.25, 0, 0.9],
  CONS: [0.25, 0.3, 0],
});

/**
 * Cara con mandibula (Ignis): ojos en canvas (EyeScreen) y boca con el hueso Jaw mas dos shape keys.
 * Misma interfaz que FaceScreen: setEyes, setMouth, update(dt) y los getters eyes/mouth/mouthChanges.
 *
 * Jaw y los shape keys no tienen pistas en los clips: se escriben aqui cada frame con un valor
 * absoluto (rotacion de reposo · apertura), despues de que el AnimationMixer haya actualizado.
 */
export class JawFace {
  /**
   * @param {THREE.Object3D} model escena del GLB, en pose de reposo (antes del primer mixer.update)
   * @param {{ jawBone?: string, jawMaxDeg?: number, smoothMs?: number, wideKey?: string, roundKey?: string,
   *           eyeMesh?: string, openAxis?: THREE.Vector3 }} [opts]
   */
  constructor(model, {
    jawBone = 'Jaw', jawMaxDeg = 24, smoothMs = 60, wideKey = 'MouthWide', roundKey = 'MouthRound',
    eyeMesh = 'FaceScreen', openAxis = new THREE.Vector3(1, 0, 0),
  } = {}) {
    const eyes = model.getObjectByName(eyeMesh);
    if (!eyes) throw new Error(`no se encontro la malla ${eyeMesh}`);
    this.eyeScreen = new EyeScreen(eyes);
    this.texture = this.eyeScreen.texture;

    this.jaw = model.getObjectByName(jawBone);
    if (!this.jaw) throw new Error(`no se encontro el hueso ${jawBone}`);
    this.jawRest = this.jaw.quaternion.clone();
    // eje de apertura (X del modelo) expresado en el espacio del padre de Jaw, en reposo
    model.updateMatrixWorld(true);
    const parentQ = this.jaw.parent.getWorldQuaternion(new THREE.Quaternion());
    const modelQ = model.getWorldQuaternion(new THREE.Quaternion());
    this.axis = openAxis.clone().applyQuaternion(modelQ).applyQuaternion(parentQ.invert()).normalize();
    this.jawMax = THREE.MathUtils.degToRad(jawMaxDeg);
    this.smooth = smoothMs / 1000;

    // shape keys: el GLB parte la malla por material, asi que puede haber varias con morphs
    this.morphs = [];
    model.traverse((o) => {
      const dict = o.morphTargetDictionary;
      if (o.isMesh && dict && (wideKey in dict || roundKey in dict)) {
        this.morphs.push({ mesh: o, wide: dict[wideKey], round: dict[roundKey] });
      }
    });
    if (!this.morphs.length) throw new Error(`no se encontraron los shape keys ${wideKey}/${roundKey}`);

    this.shape = 'REST';
    this.target = [0, 0, 0];
    this.cur = [0, 0, 0];
    this.mouthChanges = 0;
    this._q = new THREE.Quaternion();
  }

  setEyes(state) {
    this.eyeScreen.setEyes(state);
  }

  /** @param {'REST'|'MBP'|'FV'|'A'|'E'|'O'|'U'|'CONS'} shape */
  setMouth(shape) {
    const pose = MOUTH_POSES[shape];
    if (!pose) throw new Error(`forma de boca desconocida: ${shape}`);
    if (shape !== this.shape) this.mouthChanges++;
    this.shape = shape;
    this.target = pose;
  }

  get eyes() {
    return this.eyeScreen.state;
  }

  get mouth() {
    return this.shape;
  }

  /** Apertura actual suavizada (0..1). */
  get jawOpen() {
    return this.cur[0];
  }

  /** Angulo real del hueso respecto a su reposo, en grados (lo usa el test). */
  get jawAngleDeg() {
    const d = this.jawRest.clone().invert().multiply(this.jaw.quaternion);
    return THREE.MathUtils.radToDeg(2 * Math.acos(Math.min(1, Math.abs(d.w))));
  }

  update(dt) {
    // suavizado exponencial (~60 ms): la mandibula no salta de una forma a otra
    const k = 1 - Math.exp(-dt / this.smooth);
    for (let i = 0; i < 3; i++) this.cur[i] += (this.target[i] - this.cur[i]) * k;
    const [jaw, wide, round] = this.cur;
    this._q.setFromAxisAngle(this.axis, jaw * this.jawMax);
    this.jaw.quaternion.copy(this._q).multiply(this.jawRest);
    for (const m of this.morphs) {
      if (m.wide !== undefined) m.mesh.morphTargetInfluences[m.wide] = wide;
      if (m.round !== undefined) m.mesh.morphTargetInfluences[m.round] = round;
    }
    this.eyeScreen.update(dt);
  }
}
