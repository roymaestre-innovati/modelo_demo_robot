import { SpeechSource } from './SpeechSource.js';

/**
 * Implementacion real con el SDK de Azure Speech (no se usa en la demo por defecto).
 *
 * Para activarla:
 *   1. npm install microsoft-cognitiveservices-speech-sdk
 *   2. En main.js:
 *        import * as sdk from 'microsoft-cognitiveservices-speech-sdk';
 *        import { AzureSpeechSource } from './speech/AzureSpeechSource.js';
 *        const speech = new AzureSpeechSource({
 *          sdk, region: 'westeurope', voice: 'es-ES-ElviraNeural',
 *          getToken: () => fetch('/api/speech-token').then((r) => r.text()),
 *        });
 *   3. Expon un endpoint en tu backend que canjee la clave de Azure por un token de corta
 *      duracion (POST https://<region>.api.cognitive.microsoft.com/sts/v1.0/issueToken).
 *      Nunca pongas la clave de suscripcion en el frontend.
 *
 * El SDK emite visemeReceived (visemeId + audioOffset en ticks) antes/durante la sintesis;
 * el reloj de audio sale de SpeakerAudioDestination.currentTime.
 */
export class AzureSpeechSource extends SpeechSource {
  /**
   * @param {{ sdk: any, region: string, voice?: string, getToken: () => Promise<string> }} opts
   */
  constructor({ sdk, region, voice = 'es-ES-ElviraNeural', getToken }) {
    super();
    Object.assign(this, { sdk, region, voice, getToken });
  }

  async speak(text, { onViseme }) {
    const { sdk } = this;
    const token = await this.getToken();
    const speechConfig = sdk.SpeechConfig.fromAuthorizationToken(token, this.region);
    speechConfig.speechSynthesisVoiceName = this.voice;

    const player = new sdk.SpeakerAudioDestination();
    const audioConfig = sdk.AudioConfig.fromSpeakerOutput(player);
    const synth = new sdk.SpeechSynthesizer(speechConfig, audioConfig);
    synth.visemeReceived = (_s, e) => onViseme({ visemeId: e.visemeId, audioOffset: e.audioOffset });

    let started = false;
    let resolveStarted;
    const startedP = new Promise((r) => (resolveStarted = r));
    let resolveFinished;
    const finished = new Promise((r) => (resolveFinished = r));
    player.onAudioStart = () => {
      started = true;
      resolveStarted();
    };
    player.onAudioEnd = () => resolveFinished();

    synth.speakTextAsync(
      text,
      () => synth.close(),
      (err) => {
        console.error('Azure TTS:', err);
        synth.close();
        resolveStarted();
        resolveFinished();
      },
    );
    await startedP;
    return {
      clockMs: () => (started ? player.currentTime * 1000 : -1),
      finished,
      cancel: () => {
        player.pause();
        resolveFinished();
      },
    };
  }
}
