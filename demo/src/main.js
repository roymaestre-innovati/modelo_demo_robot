import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import robinUrl from '@assets/robin.glb?url';
import { EYE_STATES } from '@assets/face/faceRenderer.js';
import mockVisemes from '../mock/visemes.json';
import { FaceScreen } from './faceScreen.js';
import { VisemePlayer } from './visemePlayer.js';
import { BodyAnimator } from './bodyAnimator.js';
import { Conversation, MockListener } from './conversation.js';
import { MockSpeechSource } from './speech/MockSpeechSource.js';
import { MockLLM } from './llm/LLMClient.js';

const STATE_LABEL = { idle: 'en reposo', listening: 'escuchando…', thinking: 'pensando…', speaking: 'hablando' };
const FRAMING = {
  medium: { pos: new THREE.Vector3(0, 1.15, 2.6), target: new THREE.Vector3(0, 1.02, 0) },
  full: { pos: new THREE.Vector3(0, 0.9, 4.4), target: new THREE.Vector3(0, 0.62, 0) },
};

// estado expuesto para depuracion y el test de humo
const debug = (window.__robin = { ready: false, state: 'loading', errors: [] });

// ---------------------------------------------------------------- escena
const canvas = document.getElementById('scene');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.toneMapping = THREE.NeutralToneMapping;
renderer.toneMappingExposure = 1.0;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFShadowMap;

const scene = new THREE.Scene();
scene.background = new THREE.Color(0xe4e8ed);
scene.fog = new THREE.Fog(0xe4e8ed, 6, 14);
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
scene.environmentIntensity = 0.55;

const camera = new THREE.PerspectiveCamera(32, 1, 0.05, 50);
camera.position.copy(FRAMING.medium.pos);
const controls = new OrbitControls(camera, canvas);
controls.target.copy(FRAMING.medium.target);
controls.enableDamping = true;
controls.minDistance = 1.2;
controls.maxDistance = 7;
controls.maxPolarAngle = Math.PI * 0.55;
controls.enablePan = false;

const hemi = new THREE.HemisphereLight(0xffffff, 0xb8c0cc, 0.9);
scene.add(hemi);
const key = new THREE.DirectionalLight(0xffffff, 2.2);
key.position.set(-1.6, 3.0, 2.4);
key.castShadow = true;
key.shadow.mapSize.set(2048, 2048);
key.shadow.camera.left = key.shadow.camera.bottom = -2;
key.shadow.camera.right = key.shadow.camera.top = 2;
key.shadow.camera.near = 0.5;
key.shadow.camera.far = 8;
key.shadow.bias = -0.0005;
key.shadow.normalBias = 0.02;
scene.add(key);
const rim = new THREE.DirectionalLight(0xdfeeff, 1.4);
rim.position.set(1.5, 2.2, -2.5);
scene.add(rim);

const ground = new THREE.Mesh(new THREE.CircleGeometry(4, 64), new THREE.ShadowMaterial({ opacity: 0.18 }));
ground.rotation.x = -Math.PI / 2;
ground.receiveShadow = true;
scene.add(ground);

function resize() {
  const w = window.innerWidth;
  const h = window.innerHeight;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}
window.addEventListener('resize', resize);
resize();

// ---------------------------------------------------------------- encuadre
let framing = 'medium';
let tween = null;
function setFraming(name) {
  framing = name;
  tween = {
    t: 0,
    fromPos: camera.position.clone(),
    fromTarget: controls.target.clone(),
    to: FRAMING[name],
  };
  document.getElementById('framing').textContent = name === 'medium' ? 'Cuerpo completo' : 'Plano medio';
}
function updateTween(dt) {
  if (!tween) return;
  tween.t = Math.min(1, tween.t + dt / 0.9);
  const e = tween.t < 0.5 ? 4 * tween.t ** 3 : 1 - (-2 * tween.t + 2) ** 3 / 2;
  camera.position.lerpVectors(tween.fromPos, tween.to.pos, e);
  controls.target.lerpVectors(tween.fromTarget, tween.to.target, e);
  if (tween.t >= 1) tween = null;
}
document.getElementById('framing').addEventListener('click', () => setFraming(framing === 'medium' ? 'full' : 'medium'));
window.addEventListener('keydown', (e) => {
  if (e.key === 'f' || e.key === 'F') setFraming(framing === 'medium' ? 'full' : 'medium');
});

// ---------------------------------------------------------------- Robin
let face, body, visemes, conversation;
const statusEl = document.getElementById('status');
const statusText = document.getElementById('status-text');
const talkBtn = document.getElementById('talk');

function showState(state) {
  debug.state = state;
  statusEl.dataset.state = state;
  statusText.textContent = STATE_LABEL[state] ?? state;
  talkBtn.disabled = state !== 'idle';
}

new GLTFLoader().load(
  robinUrl,
  (gltf) => {
    const model = gltf.scene;
    model.traverse((o) => {
      if (o.isMesh) {
        o.castShadow = true;
        o.receiveShadow = true;
      }
    });
    scene.add(model);

    const screenMesh = model.getObjectByName('FaceScreen');
    if (!screenMesh) throw new Error('no se encontro la malla FaceScreen');
    face = new FaceScreen(screenMesh);
    body = new BodyAnimator(model, gltf.animations);
    visemes = new VisemePlayer(face);

    const speech = new MockSpeechSource(mockVisemes);
    conversation = new Conversation({
      face,
      body,
      visemes,
      speech,
      listener: new MockListener(),
      llm: new MockLLM(mockVisemes.text),
      onState: showState,
    });
    document.getElementById('tone').addEventListener('change', (e) => (speech.tone = e.target.checked));
    talkBtn.addEventListener('click', () => conversation.run());

    const eyeBox = document.getElementById('eye-buttons');
    for (const s of EYE_STATES) {
      const b = document.createElement('button');
      b.textContent = s;
      b.addEventListener('click', () => face.setEyes(s));
      eyeBox.append(b);
    }

    Object.assign(debug, {
      ready: true,
      model,
      face,
      body,
      visemes,
      clips: gltf.animations.map((c) => c.name),
      faceTextureIsCanvas: screenMesh.material.emissiveMap?.isCanvasTexture === true,
    });
    showState('idle');
  },
  undefined,
  (err) => {
    console.error(err);
    debug.errors.push(String(err));
    statusText.textContent = 'error al cargar robin.glb';
  },
);

// ---------------------------------------------------------------- bucle
const timer = new THREE.Timer();
renderer.setAnimationLoop((now) => {
  timer.update(now);
  const dt = Math.min(timer.getDelta(), 0.1);
  updateTween(dt);
  controls.update();
  if (body) {
    visemes.update();
    body.update(dt);
    face.update(dt);
  }
  renderer.render(scene, camera);
});
