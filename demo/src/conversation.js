/**
 * Ciclo de conversacion: listening -> thinking -> speaking -> idle.
 * Las tres piezas externas son intercambiables:
 *   listener.listen()          -> texto del usuario (mock: espera; real: Azure Speech-to-Text)
 *   llm.reply(texto)           -> { text, emotion }
 *   speech.speak(texto, {...}) -> reproduccion con visemas (ver speech/SpeechSource.js)
 */
export class MockListener {
  constructor(text = 'Hola Robin, ¿qué puedes hacer?', { durationMs = 2200 } = {}) {
    this.text = text;
    this.durationMs = durationMs;
  }

  async listen() {
    await new Promise((r) => setTimeout(r, this.durationMs));
    return this.text;
  }
}

export class Conversation {
  constructor({ face, body, visemes, listener, llm, speech, onState = () => {} }) {
    Object.assign(this, { face, body, visemes, listener, llm, speech, onState });
    this.state = 'idle';
    this.busy = false;
  }

  _set(state) {
    this.state = state;
    this.body.setState(state);
    this.onState(state);
  }

  async run() {
    if (this.busy) return;
    this.busy = true;
    try {
      this._set('listening');
      this.face.setEyes('listening');
      const userText = await this.listener.listen();

      this._set('thinking');
      this.face.setEyes('thinking');
      const reply = await this.llm.reply(userText);

      this._set('speaking');
      this.face.setEyes(reply.emotion ?? 'neutral');
      this.visemes.reset();
      const playback = await this.speech.speak(reply.text, { onViseme: (ev) => this.visemes.push(ev) });
      this.visemes.start(playback.clockMs);
      this.body.startTalking();
      await playback.finished;
    } catch (err) {
      console.error(err);
    } finally {
      this.visemes.stop();
      this.body.stopTalking();
      this.face.setEyes('neutral');
      this._set('idle');
      this.busy = false;
    }
  }
}
