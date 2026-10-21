/**
 * Contrato del cliente de LLM.
 * @typedef {{ text: string, emotion?: 'neutral'|'happy'|'surprised'|null }} LLMReply
 *
 * Emociones: hoy ninguna implementacion las emite (emotion = null y los ojos quedan en 'neutral').
 * Para anadirlas, instruye al LLM en el prompt de sistema a empezar con una etiqueta, p. ej.
 * "[happy] ¡Me encanta la idea!", y usa parseEmotion() sobre su respuesta: devuelve la
 * emocion y el texto limpio que se manda al TTS.
 */
export class LLMClient {
  /** @param {string} _userText @returns {Promise<LLMReply>} */
  async reply(_userText) {
    throw new Error('LLMClient.reply no implementado');
  }
}

const EMOTION_TAG = /^\s*\[(neutral|happy|surprised)\]\s*/i;

/** Extrae una etiqueta de emocion inicial ("[happy] ..."). */
export function parseEmotion(raw) {
  const m = raw.match(EMOTION_TAG);
  return m ? { emotion: m[1].toLowerCase(), text: raw.slice(m[0].length) } : { emotion: null, text: raw };
}

/** LLM simulado: devuelve siempre el texto del mock de visemas tras una espera. */
export class MockLLM extends LLMClient {
  constructor(text, { delayMs = 1400 } = {}) {
    super();
    this.text = text;
    this.delayMs = delayMs;
  }

  async reply() {
    await new Promise((r) => setTimeout(r, this.delayMs));
    return { text: this.text, emotion: null };
  }
}

/**
 * Ejemplo de cliente real: llama a un backend propio que habla con el LLM
 * (la clave del proveedor vive en el servidor). Espera { text } en la respuesta.
 */
export class HttpLLM extends LLMClient {
  constructor(url = '/api/chat') {
    super();
    this.url = url;
    this.history = [];
  }

  async reply(userText) {
    this.history.push({ role: 'user', content: userText });
    const res = await fetch(this.url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages: this.history }),
    });
    if (!res.ok) throw new Error(`LLM HTTP ${res.status}`);
    const { text: raw } = await res.json();
    this.history.push({ role: 'assistant', content: raw });
    return parseEmotion(raw);
  }
}
