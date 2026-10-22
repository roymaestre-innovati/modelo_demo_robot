import * as THREE from 'three';
import robinUrl from '@assets/robin.glb?url';
import visemes from '../../mock/visemes.json';
import { FaceScreen } from '../faceScreen.js';

/** Perfil de Robin: robot con pantalla por cara (valores de la demo original). */
export default {
  id: 'robin',
  label: 'Robin',
  glb: robinUrl,
  visemes,
  greeting: 'Hola Robin, ¿qué puedes hacer?',
  accent: '#3de0ff',
  accentInk: '#0b3a45',
  scene: { background: 0xe4e8ed, fog: [6, 14], environmentIntensity: 0.55 },
  framing: {
    medium: { pos: new THREE.Vector3(0, 1.15, 2.6), target: new THREE.Vector3(0, 1.02, 0) },
    full: { pos: new THREE.Vector3(0, 0.9, 4.4), target: new THREE.Vector3(0, 0.62, 0) },
  },
  bodyBones: { spine2: 'Spine2', neck: 'Neck', head: 'Head' },

  createFace(model) {
    const mesh = model.getObjectByName('FaceScreen');
    if (!mesh) throw new Error('no se encontro la malla FaceScreen');
    return new FaceScreen(mesh);
  },

  /** Robin no tiene efectos extra. */
  setupEffects() {
    return null;
  },
};
