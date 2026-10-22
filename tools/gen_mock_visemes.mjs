// Genera demo/mock/visemes.json: eventos de visema en formato Azure ({ visemeId, audioOffset })
// para una frase en espanol, con una aproximacion letra -> visema y duraciones tipicas.
// audioOffset en ticks de 100 ns (ms = ticks / 10 000), igual que SpeechSynthesisVisemeEventArgs.
// Uso: node tools/gen_mock_visemes.mjs ["texto"] [archivo en demo/mock/, por defecto visemes.json]
import { writeFile } from 'node:fs/promises';

const text = process.argv[2] ??
  '¡Hola! Soy Robin. Estoy aquí para ayudarte con lo que necesites. Cuéntame, ¿por dónde empezamos?';

// visemas Azure (en-US): 0 silencio, 1 æəʌ, 2 ɑ, 3 ɔ, 4 ɛʊ, 5 ɝ, 6 jiɪ, 7 wu, 8 o, 9 aʊ, 10 ɔɪ, 11 aɪ,
// 12 h, 13 ɹ, 14 l, 15 s z, 16 ʃ tʃ dʒ ʒ, 17 ð, 18 f v, 19 d t n θ, 20 k g ŋ, 21 p b m
const MAP = {
  a: 2, á: 2, e: 4, é: 4, i: 6, í: 6, y: 6, o: 8, ó: 8, u: 7, ú: 7, ü: 7, w: 7,
  b: 21, v: 21, m: 21, p: 21, f: 18, d: 19, t: 19, n: 19, ñ: 19, s: 15, z: 15, x: 15,
  l: 14, r: 13, k: 20, q: 20, g: 20, j: 12, c: 20,
};
const VOWELS = new Set('aáeéiíoóuú');

let seed = 7; // pseudoaleatorio determinista: el JSON se regenera identico
const rand = () => ((seed = (seed * 1103515245 + 12345) % 2147483648) / 2147483648);
const events = [];
let t = 50; // ms
const push = (id, dur) => { events.push({ visemeId: id, audioOffset: Math.round(t * 10000) }); t += dur; };

push(0, 80);
const s = text.toLowerCase();
for (let i = 0; i < s.length; i++) {
  const ch = s[i], nx = s[i + 1] ?? '';
  if (ch === 'h' && s[i - 1] !== 'c') continue; // h muda
  if (ch === 'c' && nx === 'h') { push(16, 70); i++; continue; }
  if (ch === 'l' && nx === 'l') { push(16, 70); i++; continue; }
  if (ch === 'q' && nx === 'u') { push(20, 60); i++; continue; }
  if (ch === 'c' && 'eéií'.includes(nx)) { push(15, 70); continue; }
  if (ch === 'r' && nx === 'r') { push(13, 80); i++; continue; }
  if (ch === 'y' && VOWELS.has(nx)) { push(16, 65); continue; }
  if (ch in MAP) {
    const vowel = VOWELS.has(ch);
    const prev = events.at(-1);
    if (prev && prev.visemeId === MAP[ch]) { t += vowel ? 70 : 40; continue; } // fusiona repetidos
    push(MAP[ch], vowel ? 95 + Math.round(rand() * 30) : 55 + Math.round(rand() * 20));
  } else if (',;:'.includes(ch)) push(0, 220);
  else if ('.!?'.includes(ch)) push(0, 380);
  else if (ch === ' ') t += 15;
}
if (events.at(-1).visemeId !== 0) push(0, 150);
const out = {
  text,
  description: 'Mock de eventos de visema Azure TTS (visemeId 0-21, audioOffset en ticks de 100 ns).',
  audioDurationTicks: Math.round((t + 100) * 10000),
  visemes: events,
};
const file = process.argv[3] ?? 'visemes.json';
const path = new URL(`../demo/mock/${file}`, import.meta.url);
await writeFile(path, JSON.stringify(out, null, 1) + '\n');
console.log(`${events.length} eventos, ${(t / 1000).toFixed(2)} s -> demo/mock/${file}`);
