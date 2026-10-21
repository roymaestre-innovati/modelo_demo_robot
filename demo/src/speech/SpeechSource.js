/**
 * Contrato de una fuente de voz (TTS + visemas). Implementaciones:
 *   - MockSpeechSource: eventos de demo/mock/visemes.json, reloj simulado o tono de prueba.
 *   - AzureSpeechSource: Azure Speech SDK (ver AzureSpeechSource.js y README).
 *
 * @typedef {{ visemeId: number, audioOffset: number }} VisemeEvent
 *   visemeId 0-21 (Azure), audioOffset en ticks de 100 ns desde el inicio del audio.
 *
 * @typedef {object} SpeechPlayback
 * @property {() => number} clockMs  ms de audio reproducidos desde el inicio (-1 si aun no suena).
 * @property {Promise<void>} finished resuelve cuando el audio termina (o se cancela).
 * @property {() => void} cancel     detiene el audio.
 *
 * @typedef {object} SpeakOptions
 * @property {(ev: VisemeEvent) => void} onViseme se llama por cada visema; puede llegar antes de
 *   que suene el audio correspondiente (Azure los emite por adelantado).
 */
export class SpeechSource {
  /**
   * Sintetiza y reproduce `text`. Resuelve cuando la reproduccion ha arrancado
   * (o esta a punto), devolviendo el control de la reproduccion.
   * @param {string} text
   * @param {SpeakOptions} opts
   * @returns {Promise<SpeechPlayback>}
   */
  // eslint-disable-next-line no-unused-vars
  async speak(text, opts) {
    throw new Error('SpeechSource.speak no implementado');
  }
}
