import { VISEME_TO_MOUTH, ticksToMs } from './visemeMap.js';

/**
 * Reproductor de visemas: recibe eventos { visemeId, audioOffset } (ticks de 100 ns)
 * en cualquier momento (Azure los emite por adelantado, en streaming) y los aplica a la boca
 * cuando el reloj del audio alcanza su audioOffset.
 */
export class VisemePlayer {
  /**
   * @param {{ setMouth(shape: string): void }} face
   * @param {Record<number, string>} [map]
   */
  constructor(face, map = VISEME_TO_MOUTH) {
    this.face = face;
    this.map = map;
    this.queue = [];
    this.clock = null;
    this.applied = 0;
  }

  /** Vacia la cola; llamar antes de empezar una nueva locucion. */
  reset() {
    this.queue = [];
    this.clock = null;
    this.applied = 0;
  }

  /** Encola un evento de visema (orden de llegada indiferente). */
  push({ visemeId, audioOffset }) {
    const ev = { visemeId, ms: ticksToMs(audioOffset) };
    let i = this.queue.length;
    while (i > 0 && this.queue[i - 1].ms > ev.ms) i--;
    this.queue.splice(i, 0, ev);
  }

  /** Empieza a sincronizar contra un reloj de audio que devuelve ms desde el inicio del audio. */
  start(clockMs) {
    this.clock = clockMs;
  }

  /** Llamar cada frame. */
  update() {
    if (!this.clock) return;
    const t = this.clock();
    if (t < 0) return;
    let last = null;
    while (this.queue.length && this.queue[0].ms <= t) last = this.queue.shift();
    if (last) {
      this.face.setMouth(this.map[last.visemeId] ?? 'REST');
      this.applied++;
    }
  }

  stop() {
    this.reset();
    this.face.setMouth('REST');
  }
}
