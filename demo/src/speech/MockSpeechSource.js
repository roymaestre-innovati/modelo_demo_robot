import { SpeechSource } from './SpeechSource.js';
import { VISEME_TO_MOUTH, ticksToMs } from '../visemeMap.js';

// apertura aproximada de cada forma de boca, para modular el tono de prueba
const OPENNESS = { REST: 0, MBP: 0, FV: 0.25, CONS: 0.35, U: 0.45, O: 0.75, E: 0.7, A: 1 };

/**
 * Fuente de voz simulada: reproduce una lista de visemas en formato Azure contra un reloj.
 * Sin audio usa performance.now(); con `tone` genera un tono de prueba en WebAudio
 * cuya amplitud sigue a la boca, y el reloj sale de AudioContext.currentTime.
 */
export class MockSpeechSource extends SpeechSource {
  /**
   * @param {{ text: string, audioDurationTicks: number, visemes: {visemeId:number,audioOffset:number}[] }} data
   * @param {{ tone?: boolean }} [opts]
   */
  constructor(data, { tone = false } = {}) {
    super();
    this.data = data;
    this.tone = tone;
    this.audioCtx = null;
  }

  async speak(_text, { onViseme }) {
    const { visemes, audioDurationTicks } = this.data;
    // Azure entrega los visemas por adelantado: los emitimos todos de golpe
    for (const ev of visemes) onViseme(ev);
    const durationMs = ticksToMs(audioDurationTicks);

    let clockMs;
    let stopAudio = () => {};
    if (this.tone) {
      const ctx = (this.audioCtx ??= new AudioContext());
      await ctx.resume();
      const t0 = ctx.currentTime + 0.05;
      stopAudio = this._scheduleTone(ctx, t0, visemes, durationMs);
      clockMs = () => (ctx.currentTime - t0) * 1000 - (ctx.outputLatency || 0) * 1000;
    } else {
      const t0 = performance.now();
      clockMs = () => performance.now() - t0;
    }

    let cancel;
    const finished = new Promise((resolve) => {
      const timer = setTimeout(resolve, durationMs + 50);
      cancel = () => {
        clearTimeout(timer);
        stopAudio();
        resolve();
      };
    });
    return { clockMs, finished, cancel };
  }

  _scheduleTone(ctx, t0, visemes, durationMs) {
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'triangle';
    osc.frequency.value = 190;
    gain.gain.setValueAtTime(0, t0);
    for (const ev of visemes) {
      const t = t0 + ticksToMs(ev.audioOffset) / 1000;
      const open = OPENNESS[VISEME_TO_MOUTH[ev.visemeId]] ?? 0;
      gain.gain.linearRampToValueAtTime(0.12 * open, t + 0.03);
      osc.frequency.linearRampToValueAtTime(170 + 60 * open, t + 0.05);
    }
    const end = t0 + durationMs / 1000;
    gain.gain.linearRampToValueAtTime(0, end);
    osc.connect(gain).connect(ctx.destination);
    osc.start(t0);
    osc.stop(end + 0.1);
    return () => {
      try {
        osc.stop();
      } catch {
        /* ya detenido */
      }
    };
  }
}
