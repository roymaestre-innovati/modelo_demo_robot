import * as THREE from 'three';

const TALK_FADE = 0.4;
const IDLE_FADE = 0.5;

const AX = {
  pitch: new THREE.Vector3(1, 0, 0), // + inclina hacia delante (Robin mira a +Z)
  yaw: new THREE.Vector3(0, 1, 0), // + gira a su izquierda
  roll: new THREE.Vector3(0, 0, -1), // + ladea hacia su izquierda
};
const DEG = Math.PI / 180;

// sesgo de la capa procedural segun el estado de la conversacion (grados)
const STATE_BIAS = {
  idle: { pitch: 0, yaw: 0, roll: 0 },
  listening: { pitch: -2, yaw: 0, roll: 5 },
  thinking: { pitch: -6, yaw: 7, roll: -2 },
  speaking: { pitch: 0, yaw: 0, roll: 0 },
};

/**
 * Animacion del cuerpo: AnimationMixer con 'idle' en reposo y talk_1..3 aleatorios al hablar
 * (crossfade ~0.4 s, sin repetir clip), mas una capa procedural leve encima.
 */
export class BodyAnimator {
  /**
   * @param {THREE.Object3D} root escena del GLB
   * @param {THREE.AnimationClip[]} clips
   */
  constructor(root, clips) {
    this.root = root;
    this.mixer = new THREE.AnimationMixer(root);
    const get = (name) => {
      const clip = THREE.AnimationClip.findByName(clips, name);
      if (!clip) throw new Error(`falta el clip ${name}`);
      return this.mixer.clipAction(clip);
    };
    this.idle = get('idle');
    this.talks = ['talk_1', 'talk_2', 'talk_3'].map(get);
    for (const a of this.talks) {
      a.setLoop(THREE.LoopOnce, 1);
      a.clampWhenFinished = true;
    }
    this.idle.play();
    this.current = this.idle;
    this.lastTalk = null;
    this.talking = false;
    this.talkHistory = [];

    this.bones = {
      spine2: root.getObjectByName('Spine2'),
      neck: root.getObjectByName('Neck'),
      head: root.getObjectByName('Head'),
    };
    this.time = 0;
    this.state = 'idle';
    this.bias = { ...STATE_BIAS.idle };
    this._q = new THREE.Quaternion();
    this._pq = new THREE.Quaternion();
  }

  setState(state) {
    this.state = STATE_BIAS[state] ? state : 'idle';
  }

  startTalking() {
    this.talking = true;
    this._nextTalk();
  }

  stopTalking() {
    this.talking = false;
    this._fadeTo(this.idle, IDLE_FADE);
  }

  _nextTalk() {
    const options = this.talks.filter((a) => a !== this.lastTalk);
    const next = options[Math.floor(Math.random() * options.length)];
    this.lastTalk = next;
    this.talkHistory.push(next.getClip().name);
    this._fadeTo(next, TALK_FADE);
  }

  _fadeTo(action, dur) {
    if (action === this.current && action.isRunning()) return;
    action.reset().setEffectiveWeight(1).fadeIn(dur).play();
    this.current?.fadeOut(dur);
    this.current = action;
  }

  update(dt) {
    this.time += dt;
    // encadenar gestos: al acercarse el final del clip, crossfade a otro distinto
    if (this.talking && this.current !== this.idle) {
      const remaining = this.current.getClip().duration - this.current.time;
      if (remaining <= TALK_FADE) this._nextTalk();
    }
    this.mixer.update(dt);
    this._procedural(dt);
  }

  /** Capa procedural leve encima del mixer (respiracion y micro-movimientos de cabeza). */
  _procedural(dt) {
    const { spine2, neck, head } = this.bones;
    if (!spine2 || !head) return;
    const target = STATE_BIAS[this.state];
    const k = 1 - Math.exp(-dt * 3);
    for (const key in this.bias) this.bias[key] += (target[key] - this.bias[key]) * k;

    const t = this.time;
    const n = (a, b, c) => Math.sin(t * a) * 0.5 + Math.sin(t * b + 1.3) * 0.3 + Math.sin(t * c + 2.1) * 0.2;
    this.root.updateMatrixWorld(true);
    this._rotate(spine2, AX.pitch, 0.7 * DEG * Math.sin((t * 2 * Math.PI) / 4.3));
    this._rotate(neck, AX.yaw, 0.6 * DEG * n(0.37, 0.61, 0.93));
    this._rotate(head, AX.pitch, (this.bias.pitch + 1.0 * n(0.29, 0.53, 0.87)) * DEG);
    this._rotate(head, AX.yaw, (this.bias.yaw + 1.6 * n(0.23, 0.47, 0.71)) * DEG);
    this._rotate(head, AX.roll, (this.bias.roll + 0.8 * n(0.19, 0.41, 0.67)) * DEG);
  }

  /** Rota un hueso alrededor de un eje del modelo (no del hueso), sobre su pivote. */
  _rotate(bone, axis, angle) {
    bone.parent.updateWorldMatrix(true, false);
    bone.parent.getWorldQuaternion(this._pq);
    this._q.setFromAxisAngle(axis, angle);
    const conj = this._pq.clone().invert().multiply(this._q).multiply(this._pq);
    bone.quaternion.premultiply(conj);
    bone.updateMatrixWorld(true);
  }
}
