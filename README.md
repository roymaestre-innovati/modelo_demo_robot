# Robin: robot 3D conversacional (demo three.js)

Robin es un robot mascota (variante B "Chibi") con una pantalla por cara. La demo web recorre el
ciclo completo de una conversación (`listening` → `thinking` → hablando con boca sincronizada
por visemas y gestos → `neutral`) usando datos simulados. Está preparada para conectar Azure
Speech y un LLM reales.

```
concepts/   conceptos SVG + PNG, turnaround y los scripts que los generan
blender/    build_robin.py (modelo), rig_robin.py (rig + clips + export), run.sh, renders/
assets/     robin.glb, face/ (dibujo procedural de la cara + hoja de previsualización)
demo/       proyecto Vite (JS plano, three 0.186.1), mock/visemes.json, tests/ (Playwright)
tools/      validate_glb.mjs (gltf-validator), gen_mock_visemes.mjs
```

## Requisitos

- Node 22, Python 3 (con Pillow solo para componer hojas de render), Google Chrome.
- Blender 5.2 instalado como flatpak (`org.blender.Blender`) con acceso al proyecto:
  `flatpak override --user --filesystem=<ruta del proyecto> org.blender.Blender`

## Arrancar la demo

```bash
cd demo
npm install && npm run dev        # http://localhost:5173
```

- **Hablar**: ejecuta el ciclo `listening` (2.2 s simulados) → `thinking` (LLM mock, 1.4 s) →
  hablando (8 s de visemas de `mock/visemes.json` + gestos `talk_1..3`) → reposo.
- **Cuerpo completo / Plano medio** (tecla `F`): cambia el encuadre. También se puede orbitar con el ratón.
- **tono de prueba**: reproduce un tono modulado por la boca, y el reloj de los visemas pasa a ser el del `AudioContext`.
- **ojos**: panel de depuración para probar los 5 estados (`happy` y `surprised` incluidos).

Test de humo (levanta Vite en el puerto 5199 y usa el Chrome del sistema con GPU):

```bash
cd demo && npm test                     # capturas en demo/tests/output/
PW_SWIFTSHADER=1 npm test               # sin GPU (render por software, ~1-4 FPS)
```

El test comprueba que la página carga sin errores de consola, que el GLB tiene los 4 clips, que
`FaceScreen` usa un `CanvasTexture`, que hay píxeles cian en pantalla, y que el ciclo de "Hablar"
pasa por todos los estados, consume todos los visemas y alterna gestos sin repetir.

## Regenerar cada pieza desde cero

Todo se ejecuta desde la raíz del proyecto.

| Pieza | Comando | Salida |
|---|---|---|
| Conceptos (fase 1) | `python3 concepts/gen_concepts.py && concepts/svg2png.sh concepts/concept_*.svg concepts/overview.svg` | `concepts/concept_{a..d}.{svg,png}`, `overview.png` |
| Turnaround (fase 2) | `cd concepts && python3 gen_turnaround.py && ./svg2png.sh turnaround.svg` | `concepts/turnaround.{svg,png}` |
| Modelo + renders (fase 3) | `blender/run.sh build_robin.py -- --render --save` | `blender/renders/*.png`, `blender/robin.blend` |
| Rig, clips y GLB (fase 4) | `blender/run.sh rig_robin.py` (añade `-- --render-poses` para las hojas de poses) | `assets/robin.glb`, `blender/renders/poses/` |
| Validar el GLB | `cd tools && npm install && node validate_glb.mjs` | 0 errores; ≤ 30 000 triángulos; clips, `FaceScreen` |
| Hoja de la cara (fase 5) | `python3 -m http.server -d assets/face 8123` y abrir `/preview.html` | `assets/face/preview.png` (captura) |
| Mock de visemas | `node tools/gen_mock_visemes.mjs ["otro texto"]` | `demo/mock/visemes.json` |

Notas:
- `blender/run.sh` existe porque el flatpak de Blender no resuelve rutas relativas: su directorio
  de trabajo es `/app/blender`. El script pasa la ruta absoluta del `.py`.
- Las proporciones, `ACCENT`, `BEVEL_SEGMENTS` y `SUBSURF_LEVEL` están al inicio de
  `blender/build_robin.py`. En la web, el color de la cara es `ACCENT` en `assets/face/faceRenderer.js`.

## Detalles técnicos

**Modelo** (`robin.glb`, ~500 KB): 14 408 triángulos, 46 mallas separadas y 5 materiales PBR
planos (`BodyMat`, `BodyDetailMat`, `JointMat`, `AccentMat`, `FaceScreenMat`). La única textura
es la cara de ejemplo (512×348) de `FaceScreenMat`, que three.js reemplaza al cargar.
`FaceScreen` tiene UVs planas que llenan 0–1 (el abombamiento es de 1.6 cm, así que la
distorsión es despreciable).

**Rig**: 28 huesos con nombres Mixamo sin prefijo (`Hips`, `Spine`, `Spine1`, `Spine2`, `Neck`,
`Head`, `Left/RightShoulder`, `Arm`, `ForeArm`, `Hand`, `HandThumb1`, `HandIndex1`,
`HandMiddle1`, `UpLeg`, `Leg`, `Foot`, `ToeBase`). El skinning es rígido: cada malla está
emparentada al 100 % a su hueso (parent tipo *bone*), sin pesos. Por eso el GLB no lleva
`skin`, solo jerarquía de nodos. Las mallas de la cabeza y el cuello se llaman `HeadShell` y
`NeckRing` para no chocar con los huesos `Head` y `Neck` al resolver las animaciones en three.js.

**Clips** (30 fps, con el primer frame igual al último): `idle` 5 s, `talk_1` 4 s (abrir palmas),
`talk_2` 4 s (señalar con énfasis), `talk_3` 4.6 s (enumerar con los dedos). Se generan por
código en `rig_robin.py` a partir de poses semánticas (`fwd`, `bend`, `sup`, `curl`…) que se
convierten a cuaterniones de hueso.

**Validador**: 0 errores y 0 avisos. Quedan 3 mensajes informativos: dos nodos vacíos (los huesos
`ToeBase`, sin malla) y la textura de ejemplo, que no es potencia de dos.

**Demo**:
- `src/faceScreen.js`: `setEyes(estado)` y `setMouth(forma)` sobre un `CanvasTexture` (`emissiveMap` de `FaceScreenMat`).
- `src/visemePlayer.js`: encola `{ visemeId, audioOffset }` (ticks de 100 ns; ms = ticks / 10 000) y los aplica cuando el reloj de audio los alcanza.
- `src/visemeMap.js`: tabla de los 22 visemas de Azure a las 8 formas de boca.
- `src/bodyAnimator.js`: `AnimationMixer` con `idle`; al hablar alterna `talk_1..3` al azar con crossfade de 0.4 s, sin repetir el último; al terminar vuelve a `idle` con 0.5 s. Encima añade una capa procedural de respiración y micro-movimientos de cabeza, con sesgo según el estado (ladea la cabeza al escuchar, mira arriba al pensar).
- `src/conversation.js`: orquesta el ciclo y no sabe si las piezas son mock o reales.

## Conectar Azure Speech + LLM reales

La demo depende de tres interfaces. Para pasar a producción basta con sustituir las implementaciones mock en `demo/src/main.js`.

### 1. Voz (TTS + visemas): `SpeechSource`

`demo/src/speech/AzureSpeechSource.js` ya implementa el contrato con el SDK de Azure. Sigue
llegando `visemeReceived` con `visemeId` y `audioOffset`, y el reloj es
`SpeakerAudioDestination.currentTime`.

```bash
cd demo && npm install microsoft-cognitiveservices-speech-sdk
```

```js
// demo/src/main.js
import * as sdk from 'microsoft-cognitiveservices-speech-sdk';
import { AzureSpeechSource } from './speech/AzureSpeechSource.js';

const speech = new AzureSpeechSource({
  sdk,
  region: 'westeurope',
  voice: 'es-ES-ElviraNeural',
  getToken: () => fetch('/api/speech-token').then((r) => r.text()),
});
```

**Seguridad:** nunca pongas la clave de Azure en el frontend. Crea en tu backend un endpoint
`/api/speech-token` que llame a `POST https://<región>.api.cognitive.microsoft.com/sts/v1.0/issueToken`
con la cabecera `Ocp-Apim-Subscription-Key` y devuelva el token (válido 10 minutos).

### 2. LLM: `LLMClient`

`demo/src/llm/LLMClient.js` incluye `HttpLLM`, que hace `POST` del historial a un endpoint propio
(`/api/chat`, que debe responder `{ text }`). El backend es quien llama al proveedor del LLM con
su clave. Sustituye `new MockLLM(...)` por `new HttpLLM('/api/chat')`.

**Emociones (opcional):** hoy el LLM no emite emociones y los ojos quedan en `neutral` al hablar.
Para activarlas:
1. Pide en el prompt de sistema que la respuesta empiece con `[happy]`, `[surprised]` o `[neutral]`.
2. `HttpLLM` ya aplica `parseEmotion()`: separa la etiqueta del texto que va al TTS.
3. `Conversation` llama a `face.setEyes(reply.emotion)` al empezar a hablar.

### 3. Escucha (STT): `listener`

`MockListener` solo espera 2.2 s. Una implementación real debe cumplir `listen(): Promise<string>`,
por ejemplo con `sdk.SpeechRecognizer.recognizeOnceAsync` del mismo SDK, configurando
`speechRecognitionLanguage = 'es-ES'` y `AudioConfig.fromDefaultMicrophoneInput()`.
Mientras escucha, los ojos están en `listening`.

## Decisiones y desviaciones

- **Conversión de SVG a PNG:** con Chrome headless (`concepts/svg2png.sh`), porque no hay `rsvg-convert` ni `inkscape`.
- **Cambios respecto al turnaround:**
  - Articulación de la cadera más baja (z 0.57) y más grande, para que no quede oculta en la pelvis.
  - Más bevel en torso y pelvis.
  - Brazos y piernas un ~25 % más gruesos (pedido en la aprobación 3).
- **Renders de Blender:** usan la transformación de color "Khronos PBR Neutral" para que el cian
  no se desature. La demo usa su equivalente, `NeutralToneMapping`.
- **Test de humo:** usa la GPU en headless (`--enable-gpu`). Con SwiftShader la escena va a
  ~1-4 FPS y los gestos avanzan demasiado despacio para el test. `PW_SWIFTSHADER=1` lo fuerza y
  relaja las comprobaciones de ritmo.
- **Versiones fijadas** (publicadas hace más de dos semanas): `three@0.186.1`, `vite@8.3.3`
  (8.3.1 tenía un aviso de seguridad moderado), `@playwright/test@1.63.0` y
  `gltf-validator@2.0.0-dev.3.10`.
