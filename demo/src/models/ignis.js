import * as THREE from 'three';
import ignisUrl from '@assets/ignis.glb?url';
import visemes from '../../mock/visemes_ignis.json';
import { JawFace } from '../jawFace.js';
import { FlameEffects } from './flameEffects.js';

/** Perfil de Ignis: dragon cuadrupedo con ojos en canvas y boca con mandibula + shape keys. */
export default {
  id: 'ignis',
  label: 'Ignis',
  glb: ignisUrl,
  visemes,
  greeting: 'Hola Ignis, ¿qué puedes hacer?',
  accent: '#ff5733',
  accentInk: '#3a0c02',
  scene: { background: 0x2b2f36, fog: [7, 16], environmentIntensity: 0.6 },
  // Ignis es horizontal y largo: el encuadre completo va en tres cuartos e incluye la cola (z -1.2)
  framing: {
    medium: { pos: new THREE.Vector3(0.75, 1.2, 2.55), target: new THREE.Vector3(0, 0.98, 0.3) },
    full: { pos: new THREE.Vector3(2.7, 1.35, 2.6), target: new THREE.Vector3(0, 0.62, -0.22) },
  },
  bodyBones: { spine2: 'Spine2', neck: 'Neck1', head: 'Head' },

  createFace(model) {
    return new JawFace(model, { jawMaxDeg: 24, smoothMs: 60 });
  },

  setupEffects({ scene, model }) {
    return new FlameEffects(scene, model.getObjectByName('TailFlame'));
  },
};
