// Cara de Robin dibujada proceduralmente en un <canvas> 2D (sin sprites).
// No depende de three.js: demo/src/faceScreen.js la envuelve en un CanvasTexture.
//
// Ojos: 5 estados (neutral, listening, thinking, happy, surprised) con transicion suave
// y parpadeo automatico. Boca: 8 formas (REST, MBP, FV, A, E, O, U, CONS) interpoladas.
//
// Emociones (pendiente): hoy el LLM no emite emociones; la app decide los ojos segun el
// ciclo de conversacion. Para anadirlas, pide al LLM que antepone una etiqueta a la respuesta,
// p. ej. "[happy] ¡Claro que si!", parseala en el cliente (quitandola del texto que va al TTS)
// y llama a setEyes(etiqueta) al empezar a hablar; los nombres validos son EYE_STATES.

export const ACCENT = '#3DE0FF'; // color de acento; unico punto de cambio en la web

// Proporcion de la pantalla FaceScreen: 0.50 x 0.34 (ver concepts/turnaround.svg)
export const FACE_ASPECT = 0.5 / 0.34;

export const EYE_STATES = ['neutral', 'listening', 'thinking', 'happy', 'surprised'];
export const MOUTH_SHAPES = ['REST', 'MBP', 'FV', 'A', 'E', 'O', 'U', 'CONS'];

// Parametros de ojo en fracciones del alto del canvas (w, h = diametros; dx, dy = desplazamiento de mirada)
// arc = 1 dibuja el ojo en arco (^ ^)
const EYES = {
  neutral: { w: 0.19, h: 0.31, dx: 0, dy: 0, arc: 0, glow: 1.0 },
  listening: { w: 0.22, h: 0.36, dx: 0, dy: -0.01, arc: 0, glow: 1.25 },
  thinking: { w: 0.18, h: 0.24, dx: 0.06, dy: -0.07, arc: 0, glow: 0.9 },
  happy: { w: 0.22, h: 0.2, dx: 0, dy: 0.0, arc: 1, glow: 1.15 },
  surprised: { w: 0.29, h: 0.36, dx: 0, dy: -0.02, arc: 0, glow: 1.3 },
};

// Boca: w/h en fracciones del ancho/alto, n = exponente de superelipse (2 = elipse, mayor = mas rectangular),
// smile = curvatura de la linea media (+ = sonrisa), t = grosor minimo (lineas cerradas)
const MOUTHS = {
  REST: { w: 0.15, h: 0.0, n: 2, smile: 0.035, t: 0.03 },
  MBP: { w: 0.12, h: 0.0, n: 2, smile: 0.0, t: 0.042 },
  FV: { w: 0.12, h: 0.035, n: 4, smile: -0.008, t: 0.03 },
  A: { w: 0.15, h: 0.17, n: 2.6, smile: 0.012, t: 0.03 },
  E: { w: 0.18, h: 0.075, n: 3, smile: 0.012, t: 0.03 },
  O: { w: 0.085, h: 0.13, n: 2, smile: 0, t: 0.03 },
  U: { w: 0.05, h: 0.075, n: 2, smile: 0, t: 0.03 },
  CONS: { w: 0.12, h: 0.04, n: 3, smile: 0.006, t: 0.03 },
};

const lerp = (a, b, t) => a + (b - a) * t;
const lerpObj = (cur, target, t) => {
  for (const k in target) cur[k] = lerp(cur[k], target[k], t);
};

export class FaceRenderer {
  /**
   * @param {HTMLCanvasElement} canvas
   * @param {{ accent?: string, width?: number }} [opts]
   */
  constructor(canvas, { accent = ACCENT, width = 1024 } = {}) {
    this.canvas = canvas;
    canvas.width = width;
    canvas.height = Math.round(width / FACE_ASPECT);
    this.ctx = canvas.getContext('2d');
    this.accent = accent;
    this.eyeState = 'neutral';
    this.mouthShape = 'REST';
    this.eye = { ...EYES.neutral };
    this.mouth = { ...MOUTHS.REST };
    this.time = 0;
    this.blink = 0; // 0 abierto .. 1 cerrado
    this.blinkT = -1;
    this.nextBlink = this._randomBlinkDelay();
    this.thinkPhase = 0;
  }

  setEyes(state) {
    if (!EYES[state]) throw new Error(`estado de ojos desconocido: ${state}`);
    this.eyeState = state;
  }

  setMouth(shape) {
    if (!MOUTHS[shape]) throw new Error(`forma de boca desconocida: ${shape}`);
    this.mouthShape = shape;
  }

  _randomBlinkDelay() {
    return 2 + Math.random() * 4; // 2-6 s
  }

  /** Avanza animaciones internas. dt en segundos. */
  update(dt) {
    this.time += dt;
    // ojos: transicion suave hacia el estado objetivo
    lerpObj(this.eye, EYES[this.eyeState], 1 - Math.exp(-dt * 12));
    // boca: rapida para seguir los visemas (~60 ms)
    const mt = { ...MOUTHS[this.mouthShape] };
    if (this.mouthShape === 'REST') {
      // pequeno bucle en reposo para que la pantalla no se vea estatica
      mt.w *= 1 + 0.04 * Math.sin(this.time * 1.3);
      mt.smile *= 1 + 0.15 * Math.sin(this.time * 0.7 + 1);
    }
    lerpObj(this.mouth, mt, 1 - Math.exp(-dt * 28));

    // parpadeo automatico en neutral/listening/thinking
    const canBlink = this.eyeState !== 'happy';
    this.nextBlink -= dt;
    if (this.blinkT < 0 && this.nextBlink <= 0 && canBlink) {
      this.blinkT = 0;
      this.nextBlink = this._randomBlinkDelay();
      if (Math.random() < 0.2) this.nextBlink = 0.25; // a veces doble parpadeo
    }
    if (this.blinkT >= 0) {
      this.blinkT += dt;
      const d = 0.16; // duracion total
      const p = this.blinkT / d;
      this.blink = p < 0.5 ? p * 2 : Math.max(0, 2 - p * 2);
      if (this.blinkT >= d) {
        this.blinkT = -1;
        this.blink = 0;
      }
    }
    this.thinkPhase += dt;
  }

  draw() {
    const { ctx, canvas } = this;
    const W = canvas.width;
    const H = canvas.height;
    ctx.save();
    ctx.globalCompositeOperation = 'source-over';
    ctx.fillStyle = '#000';
    ctx.fillRect(0, 0, W, H);

    ctx.fillStyle = this.accent;
    ctx.strokeStyle = this.accent;
    ctx.shadowColor = this.accent;
    ctx.shadowBlur = H * 0.05 * this.eye.glow;
    this._drawEyes(W, H);
    ctx.shadowBlur = H * 0.04;
    this._drawMouth(W, H);
    ctx.restore();
  }

  _drawEyes(W, H) {
    const { ctx, eye } = this;
    let { dx, dy } = eye;
    if (this.eyeState === 'thinking') {
      // mirada que deriva lentamente (animacion de "pensar")
      dx += Math.sin(this.thinkPhase * 1.6) * 0.025;
      dy += Math.cos(this.thinkPhase * 1.1) * 0.01;
    }
    const cy = H * (0.44 + dy);
    const ew = eye.w * H;
    const eh = Math.max(eye.h * H * (1 - this.blink * 0.92), H * 0.018);
    const arcA = eye.arc;
    for (const sx of [-1, 1]) {
      const cx = W * 0.5 + sx * W * 0.2 + dx * H;
      // ojo lleno (elipse redondeada)
      if (arcA < 0.999) {
        ctx.globalAlpha = 1 - arcA;
        ctx.beginPath();
        ctx.ellipse(cx, cy, ew / 2, eh / 2, 0, 0, Math.PI * 2);
        ctx.fill();
        if (this.eyeState === 'surprised') {
          // brillo interior
          ctx.save();
          ctx.globalAlpha = (1 - arcA) * 0.9;
          ctx.fillStyle = '#000';
          ctx.shadowBlur = 0;
          ctx.beginPath();
          ctx.ellipse(cx, cy, ew * 0.22, eh * 0.22 * (ew / eh), 0, 0, Math.PI * 2);
          ctx.fill();
          ctx.restore();
        }
      }
      // ojo en arco (^ ^)
      if (arcA > 0.001) {
        ctx.globalAlpha = arcA;
        ctx.lineWidth = H * 0.055;
        ctx.lineCap = 'round';
        ctx.beginPath();
        const r = ew * 0.55;
        ctx.arc(cx, cy + r * 0.45, r, Math.PI * 1.15, Math.PI * 1.85);
        ctx.stroke();
      }
    }
    ctx.globalAlpha = 1;
  }

  _drawMouth(W, H) {
    const { ctx, mouth } = this;
    const cx = W * 0.5;
    const cy = H * 0.74;
    const w = mouth.w * W;
    const h = mouth.h * H;
    const t = mouth.t * H;
    const n = Math.max(1.2, mouth.n);
    const N = 40;
    const top = [];
    const bot = [];
    for (let i = 0; i <= N; i++) {
      const u = (i / N) * 2 - 1; // -1..1
      const x = cx + (u * w) / 2;
      const half = (h / 2) * Math.pow(Math.max(0, 1 - Math.pow(Math.abs(u), n)), 1 / n);
      const g = mouth.smile * H * (1 - u * u);
      const hh = Math.max(half, (t / 2) * Math.sqrt(Math.max(0, 1 - Math.pow(Math.abs(u), 8))));
      top.push([x, cy + g - hh]);
      bot.push([x, cy + g + hh]);
    }
    ctx.beginPath();
    ctx.moveTo(top[0][0], top[0][1]);
    for (const p of top) ctx.lineTo(p[0], p[1]);
    for (let i = bot.length - 1; i >= 0; i--) ctx.lineTo(bot[i][0], bot[i][1]);
    ctx.closePath();
    ctx.fill();
    // extremos redondeados (solo cuando la boca esta casi cerrada)
    const r = (t / 2) * Math.min(1, Math.max(0, 1.5 - h / t));
    if (r <= 0.5) return;
    for (const p of [top[0], top[N]]) {
      ctx.beginPath();
      ctx.arc(p[0], p[1], r, 0, Math.PI * 2);
      ctx.fill();
    }
  }
}
