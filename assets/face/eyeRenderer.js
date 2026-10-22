// Ojos de Ignis dibujados proceduralmente en un <canvas> 2D (sin sprites).
// No depende de three.js: la demo lo envuelve en un CanvasTexture que va en el `map` de FaceScreenMat.
//
// Layout (igual que las UV de FaceScreen): ojo izquierdo de Ignis en la mitad izquierda del canvas
// (u 0-0.5) y ojo derecho en la mitad derecha (u 0.5-1). Cada mitad es el disco del parche:
// el centro del canvas-mitad es el centro del ojo y el borde del disco toca los bordes de la mitad.
// En ambas mitades +x del canvas apunta hacia +X del modelo (izquierda a derecha en vista frontal),
// asi que "hacia el hocico" es -x en el ojo izquierdo y +x en el derecho.
//
// Parpados: el superior baja desde arriba (upper 0 = abierto del todo, 1 = cerrado) con el borde en
// arco; el inferior sube desde abajo (lower) con el borde curvado hacia arriba, para la mirada feliz.

export const EYE_STATES = ['neutral', 'listening', 'thinking', 'happy', 'surprised'];

export const IGNIS_EYE_COLORS = {
  body: '#D93829', // BodyMat: el parpado es del color del cuerpo
  sclera: '#FFFFFF',
  iris: '#B5651D',
  irisDark: '#7A3E0E',
  pupil: '#1E0B06',
  line: '#3B0A10',
};

// lookX: + hacia el hocico; lookY: + hacia arriba (fracciones del radio del ojo)
// upper/lower: cierre de cada parpado (0..1); tilt: + baja el lado interior del parpado superior
// iris/pupil: radios relativos al radio del ojo
const EYES = {
  neutral: { upper: 0.12, lower: 0.0, lookX: 0.12, lookY: 0.0, iris: 0.6, pupil: 0.3, tilt: 0.0 },
  listening: { upper: 0.04, lower: 0.0, lookX: 0.1, lookY: 0.06, iris: 0.62, pupil: 0.34, tilt: -0.08 },
  thinking: { upper: 0.14, lower: 0.12, lookX: -0.3, lookY: 0.3, iris: 0.56, pupil: 0.27, tilt: 0.12 },
  happy: { upper: 0.16, lower: 0.5, lookX: 0.1, lookY: 0.05, iris: 0.6, pupil: 0.3, tilt: -0.1 },
  surprised: { upper: 0.0, lower: 0.0, lookX: 0.0, lookY: 0.04, iris: 0.5, pupil: 0.18, tilt: -0.12 },
};

const SCLERA_R = 0.93; // radio de la esclerotica respecto al disco del parche
const lerp = (a, b, t) => a + (b - a) * t;

export class EyeRenderer {
  /**
   * @param {HTMLCanvasElement} canvas
   * @param {{ width?: number, colors?: Partial<typeof IGNIS_EYE_COLORS> }} [opts]
   */
  constructor(canvas, { width = 512, colors = {} } = {}) {
    this.canvas = canvas;
    canvas.width = width;
    canvas.height = width / 2;
    this.ctx = canvas.getContext('2d');
    this.colors = { ...IGNIS_EYE_COLORS, ...colors };
    this.eyeState = 'neutral';
    this.eye = { ...EYES.neutral };
    this.time = 0;
    this.blink = 0; // 0 abierto .. 1 cerrado
    this.blinkT = -1;
    this.nextBlink = this._randomBlinkDelay();
    this.autoBlink = true;
  }

  setEyes(state) {
    if (!EYES[state]) throw new Error(`estado de ojos desconocido: ${state}`);
    this.eyeState = state;
  }

  /** Salta al estado sin transicion (previsualizaciones). */
  snap(state, blink = 0) {
    this.setEyes(state);
    this.eye = { ...EYES[state] };
    this.blink = blink;
  }

  _randomBlinkDelay() {
    return 2 + Math.random() * 4; // 2-6 s
  }

  /** Avanza animaciones internas. dt en segundos. */
  update(dt) {
    this.time += dt;
    const k = 1 - Math.exp(-dt * 10);
    const target = EYES[this.eyeState];
    for (const key in target) this.eye[key] = lerp(this.eye[key], target[key], k);

    // parpadeo automatico (no en happy: los ojos ya estan entornados)
    if (!this.autoBlink) return;
    this.nextBlink -= dt;
    if (this.blinkT < 0 && this.nextBlink <= 0 && this.eyeState !== 'happy') {
      this.blinkT = 0;
      this.nextBlink = Math.random() < 0.2 ? 0.3 : this._randomBlinkDelay(); // a veces doble
    }
    if (this.blinkT >= 0) {
      this.blinkT += dt;
      const d = 0.18;
      const p = this.blinkT / d;
      this.blink = p < 0.45 ? p / 0.45 : Math.max(0, 1 - (p - 0.45) / 0.55);
      if (this.blinkT >= d) {
        this.blinkT = -1;
        this.blink = 0;
      }
    }
  }

  draw() {
    const { ctx, canvas, colors } = this;
    const H = canvas.height;
    ctx.save();
    ctx.fillStyle = colors.body;
    ctx.fillRect(0, 0, canvas.width, H);
    // mitad izquierda = ojo izquierdo de Ignis (el hocico queda hacia -x); mitad derecha = ojo derecho
    this._drawEye(H / 2, H / 2, H / 2, -1);
    this._drawEye(H * 1.5, H / 2, H / 2, 1);
    ctx.restore();
  }

  /** nose: direccion del hocico en x del canvas (-1 ojo izquierdo, +1 ojo derecho). */
  _drawEye(cx, cy, R, nose) {
    const { ctx, colors } = this;
    const e = { ...this.eye };
    let lookX = e.lookX;
    let lookY = e.lookY;
    if (this.eyeState === 'thinking') {
      lookX += Math.sin(this.time * 1.4) * 0.06;
      lookY += Math.cos(this.time * 0.9) * 0.03;
    }
    const r = R * SCLERA_R;
    // al parpadear el superior baja hasta un poco por debajo del centro y el inferior sube a su encuentro
    const upper = Math.min(1, e.upper + (1 - e.upper) * this.blink);
    const lower = Math.max(e.lower, 0.45 * this.blink);

    ctx.save();
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.clip();

    // esclerotica + sombra superior suave (el parpado proyecta sombra)
    ctx.fillStyle = colors.sclera;
    ctx.fillRect(cx - r, cy - r, 2 * r, 2 * r);
    const shade = ctx.createLinearGradient(0, cy - r, 0, cy);
    shade.addColorStop(0, 'rgba(120,60,50,0.28)');
    shade.addColorStop(1, 'rgba(120,60,50,0)');
    ctx.fillStyle = shade;
    ctx.fillRect(cx - r, cy - r, 2 * r, r);

    // iris con degradado, pupila y brillos
    const ix = cx + nose * lookX * r;
    const iy = cy - lookY * r;
    const ir = e.iris * r;
    const g = ctx.createRadialGradient(ix, iy + ir * 0.2, ir * 0.15, ix, iy, ir);
    g.addColorStop(0, colors.iris);
    g.addColorStop(0.75, colors.iris);
    g.addColorStop(1, colors.irisDark);
    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.arc(ix, iy, ir, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = colors.pupil;
    ctx.beginPath();
    ctx.arc(ix, iy, e.pupil * r, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#FFFFFF';
    ctx.beginPath();
    ctx.arc(ix + nose * ir * 0.3, iy - ir * 0.38, ir * 0.22, 0, Math.PI * 2);
    ctx.fill();
    ctx.globalAlpha = 0.8;
    ctx.beginPath();
    ctx.arc(ix - nose * ir * 0.32, iy + ir * 0.35, ir * 0.09, 0, Math.PI * 2);
    ctx.fill();
    ctx.globalAlpha = 1;

    // parpado inferior: sube desde abajo con el borde en arco hacia arriba
    if (lower > 0.01) {
      const yb = cy + r - lower * 2 * r; // altura del borde en el centro
      ctx.fillStyle = colors.body;
      ctx.beginPath();
      ctx.moveTo(cx - r - 2, cy + r + 2);
      ctx.lineTo(cx - r - 2, yb + r * 0.35);
      ctx.quadraticCurveTo(cx, yb - r * 0.3, cx + r + 2, yb + r * 0.35);
      ctx.lineTo(cx + r + 2, cy + r + 2);
      ctx.closePath();
      ctx.fill();
      if (e.lower > 0.01) {
        ctx.strokeStyle = colors.line;
        ctx.lineWidth = R * 0.05;
        ctx.beginPath();
        ctx.moveTo(cx - r - 2, yb + r * 0.35);
        ctx.quadraticCurveTo(cx, yb - r * 0.3, cx + r + 2, yb + r * 0.35);
        ctx.stroke();
      }
    }

    // parpado superior: baja desde arriba con el borde en arco; tilt inclina el lado del hocico
    const yt = cy - r + upper * 1.5 * r; // a upper = 1 el borde queda en cy + 0.5 r (ojo cerrado)
    const tilt = e.tilt * r;
    const yIn = yt + tilt; // lado del hocico
    const yOut = yt - tilt;
    const xIn = cx + nose * (r + 2);
    const xOut = cx - nose * (r + 2);
    const sag = r * 0.14 * (1 - upper * 0.6); // curvatura del borde (mas plano al cerrar)
    ctx.fillStyle = colors.body;
    ctx.beginPath();
    ctx.moveTo(xOut, cy - r - 2);
    ctx.lineTo(xOut, yOut);
    ctx.quadraticCurveTo(cx, (yIn + yOut) / 2 + sag, xIn, yIn);
    ctx.lineTo(xIn, cy - r - 2);
    ctx.closePath();
    ctx.fill();
    ctx.strokeStyle = colors.line;
    ctx.lineWidth = R * 0.06;
    ctx.lineCap = 'round';
    ctx.beginPath();
    ctx.moveTo(xOut, yOut);
    ctx.quadraticCurveTo(cx, (yIn + yOut) / 2 + sag, xIn, yIn);
    ctx.stroke();
    ctx.restore();

    // contorno del ojo; se desvanece al cerrar para que el ojo cerrado sea solo la linea del parpado
    ctx.globalAlpha = 1 - 0.85 * this.blink;
    ctx.strokeStyle = colors.line;
    ctx.lineWidth = R * 0.05;
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.stroke();
    ctx.globalAlpha = 1;
  }
}
