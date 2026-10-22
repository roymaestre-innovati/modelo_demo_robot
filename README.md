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
npm install && npm run dev        # http://localhost:5173 (Robin) · http://localhost:5173/?model=ignis (Ignis)
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

## Ignis (dragón)

Especificación: `dragon/prompt.dragon.md` y `dragon/model_spec.json`.

La misma demo muestra a Robin o a Ignis: `npm run dev` y abre `http://localhost:5173/?model=ignis`
(sin parámetro, o con `?model=robin`, carga Robin). El selector "modelo" de la barra recarga la
página con el otro perfil. `npm test` ejecuta el mismo test de humo con los dos modelos.

```
demo/src/models/       robin.js, ignis.js (perfiles), index.js (?model=), flameEffects.js
demo/src/jawFace.js    cara de Ignis: EyeScreen + Jaw + shape keys (misma interfaz que FaceScreen)
demo/src/eyeScreen.js  ojos en canvas como `map` de FaceScreenMat
assets/face/           eyeRenderer.js (ojos de Ignis) e ignis_eyes.html (previsualización)
demo/mock/visemes_ignis.json   visemas simulados de la frase de Ignis
```

**Perfiles:** cada perfil define el GLB, los visemas simulados y el saludo, el acento de la
interfaz, el fondo, los dos encuadres, los huesos de la capa procedural (`Spine2`, `Neck`/`Neck1`,
`Head`), `createFace(model)` y `setupEffects()`. `VisemePlayer`, `Conversation` y `BodyAnimator` no
saben qué modelo hay cargado. `window.__robin` sigue existiendo; `window.__demo` es el mismo objeto,
con el campo nuevo `profile`.

**Cara de Ignis (`JawFace`):** cada forma de boca se traduce en `[jawOpen, wide, round]` con la
tabla del prompt, sin cambios. Los tres valores se suavizan con una constante de 60 ms. `Jaw` se
escribe cada frame como valor absoluto (`rotación(eje X del modelo) · reposo`), y los shape keys se
aplican en todas las mallas en las que el GLB parte `IgnisBody`. El test mide el ángulo real del
hueso: ~17° de máximo durante el habla y menos de 0.5° al volver a reposo.

| Pieza | Comando | Salida |
|---|---|---|
| Turnaround (fase 1) | `python3 concepts/ignis/gen_turnaround.py && concepts/svg2png.sh concepts/ignis/turnaround.svg` | `concepts/ignis/turnaround.{svg,png}` |
| Modelo + renders (fase 2) | `blender/run.sh build_ignis.py -- --render --save` | `blender/renders/ignis/*.png`, `blender/ignis.blend` |
| Rig, clips y GLB (fase 3) | `blender/run.sh rig_ignis.py` (`-- --render-poses` para las hojas; `-- --save` guarda `blender/ignis_rigged.blend`) | `assets/ignis.glb`, `blender/renders/ignis/poses/` |
| Hojas de poses | `python3 blender/compose_ignis_sheets.py` | `blender/renders/ignis/poses/*_sheet.png` |
| Validar el GLB | `node tools/validate_glb.mjs assets/ignis.glb` | 0 errores; clips, `FaceScreen`, `Jaw`, shape keys, ningún clip anima `Jaw` |
| Mock de visemas de Ignis | `node tools/gen_mock_visemes.mjs "texto" visemes_ignis.json` | `demo/mock/visemes_ignis.json` |
| Ojos sobre el modelo | servir `assets/face` en 8123, capturar `ignis_eyes.html?state=<estado>` con Chrome en `blender/renders/ignis/eyes/tex/` y `blender/run.sh render_ignis_eyes.py` | `blender/renders/ignis/eyes/*.png` |

### Decisiones y desviaciones (Ignis)

- **Turnaround:** el dragón se describe como volúmenes 3D (elipsoides encadenados, prismas y polígonos)
  y se proyecta en ortográfica a cada vista, así frontal, lateral y superior quedan alineadas por
  construcción. Las constantes del script son el plano de `blender/build_ignis.py`.
- **Envergadura:** con alas totalmente abiertas mide 1.35 m, ≈1.4× el torso (0.96 m), algo por
  debajo del 1.6× de la ficha, para mantener las alas proporcionadas a las de la imagen de
  referencia. Pendiente de confirmar en la aprobación 1.
- **Púas dorsales y aletas de las mejillas:** `BodyMat`. **Varillas del ala:** `WingMembraneMat`.
  **Lengua:** `BodyMat` (la ficha no define material para la lengua).
- **Mandíbula:** `jawOpen = 1` equivale a 24°; la forma `A` (0.8) abre 19°.
- **Malla del cuerpo:** `IgnisBody` sale de los volúmenes del turnaround unidos con un remesh por
  vóxeles (8 mm) y un suavizado leve. Después se reduce en dos pasadas de `Decimate` simétrico:
  1) toda la malla a `HEAD_PASS_TRIS` (7 000); 2) solo el cuerpo hasta `BODY_TRIS` (6 000), con la
  cabeza protegida. Así la cabeza conserva el doble de densidad que el resto (~2 900 de 5 400
  triángulos). Las facetas quedan triangulares e irregulares, como en la referencia. En lugar de
  loops de aristas en las articulaciones hay una densidad uniforme (~3 cm), suficiente para
  deformar con pesos suaves.
- **Boca:** un booleano abre una hendidura de 6 mm entre el hocico y la mandíbula y una cavidad
  interior que ocupa casi todo el hocico (labios de ~2 cm). Al abrirse se ve interior oscuro
  (`MouthMat`) y la lengua, sin repisas planas. `MouthMat` se asigna sobre la malla densa, antes de
  reducirla, y los labios se protegen del `Decimate` y se suavizan: así el borde no queda dentado
  (parecía una fila de dientes). En reposo la hendidura se lee como la línea de la sonrisa. La
  barbilla es naranja (`BellyHornsMat`), como en la referencia.
- **Piezas rígidas aparte:** cuernos, garras, `FaceScreen`, `Tongue` y `TailFlame`. Las púas
  dorsales y las aletas de las mejillas están dentro de `IgnisBody` para que deformen con él.
- **Varillas del ala:** `ClawMat` (más oscuro que la membrana, como en la referencia), en lugar de
  `WingMembraneMat` como se anotó en la fase 1.
- **Emisión de la llama:** 0.8 en lugar del 2.5 de la ficha. Con 2.5 el tone mapping Khronos PBR
  Neutral la lavaba a un melocotón pálido; con 0.8 se ve naranja.
- **Ojos (`assets/face/eyeRenderer.js`):** se dibujan en el canvas, sin geometría de párpados. El
  párpado superior baja desde arriba y el inferior sube desde abajo. Al parpadear se juntan en una
  línea a media altura y el contorno del ojo se desvanece. `happy` sube el párpado inferior (ojos
  sonrientes) y no parpadea; `thinking` mira hacia arriba y hacia fuera.
- **Ojos de ejemplo:** el párpado superior es un arco (más alto en el centro) para una expresión
  amable. La textura de ejemplo se escribe en sRGB.
- **Renders:** fondo de ciclorama gris oscuro orientado hacia cada cámara.
- **Rig:** 38 huesos de la ficha (con `Root`). Pesos automáticos en `IgnisBody` (sin `Root` ni las
  alas). La cabeza se reparte entre `Head` y `Jaw` por geometría: todo lo que queda bajo la
  hendidura y por delante de la comisura va a `Jaw`, con transición hacia atrás. Las alas se pesan
  por distancia a sus segmentos, porque el pesado automático no es fiable en una membrana plana.
  El borde unido al lomo sigue a `Spine2`/`Spine`. Máximo 4 huesos por vértice, normalizados.
- **Piezas rígidas:** `FaceScreen` y cuernos a `Head`, `Tongue` a `Jaw`, garras a los `*Toes` y
  `TailFlame` a `Tail_6`. Las mallas con skin quedan en la raíz del glTF (solo con el modificador
  Armature) para evitar el aviso `NODE_SKINNED_MESH_NON_ROOT`.
- **Patas:** IK de Blender (cadena de 2 en `*LowerLeg` y Copy Rotation en `*Foot` hacia un empty
  fijo en el suelo), horneado a FK por frame. El deslizamiento máximo de un pie apoyado es 0.8 mm
  (`rig_ignis.py` lo informa al exportar). En `talk_1` despega solo la garra delantera izquierda
  (11.6 cm). En `talk_2` despegan las delanteras 6.5 cm: con las patas casi rectas en reposo no
  se puede elevar el pecho con las cuatro apoyadas, y la ficha solo pide apoyadas las traseras.
- **Alas a medio abrir:** las rotaciones salen de las direcciones del turnaround (plegada → a
  medias). El abanico de dedos es rígido porque la ficha define un solo hueso, `Wing3`.
- **Shape keys:** `MouthWide` estira las comisuras hacia atrás y arriba, y `MouthRound` adelanta y
  estrecha los labios. Se generan por código sobre `IgnisBody`.
- **Exportación:** `export_force_sampling=False` y optimización de canales constantes. Con
  muestreo forzado el exportador creaba pistas constantes en `Jaw`. Sin ellas, los huesos que no
  se mueven en un clip (`Root`, `*Toes`, `Jaw` y a veces `Spine`, `Neck2`, `Wing3_*` o `Tail_1/2`)
  no tienen pista: la capa procedural de la demo necesita la guarda `restoreUnanimated()`.
- **Demo, capa procedural:** `BodyAnimator.restoreUnanimated()` devuelve a reposo, antes de
  `mixer.update()`, los huesos procedurales que ninguna acción activa anima. Con Robin no cambia
  nada, porque sus clips muestrean todos los huesos.
- **Demo, llama:** `TailFlame` tiene el origen en su base para escalar desde ahí. En three.js se baja
  el color base (×0.3) y se sube la emisión (×1.2): con `NeutralToneMapping` la llama se veía color
  melocotón. Parpadea en escala y emisión, con una `PointLight` cálida y 48 chispas (`Points` con
  mezcla aditiva y textura generada en canvas, para no depender de archivos que puedan dar 404).
- **Demo, fondo:** gris pizarra oscuro (`#2b2f36`) para Ignis, para que destaquen la llama y las
  chispas, como en la referencia. Robin conserva su fondo claro.
- **Ojos en la demo:** el párpado superior en `neutral` baja a 0.12 (antes 0.2) y el borde del
  párpado se curva menos. Con la cámara de la demo, más baja que la de los renders, los ojos se
  veían adormilados.
- **Mock de visemas:** `tools/gen_mock_visemes.mjs` acepta un segundo argumento opcional con el
  archivo de salida. Sin él escribe `visemes.json` como antes; el de Robin se regenera idéntico.
