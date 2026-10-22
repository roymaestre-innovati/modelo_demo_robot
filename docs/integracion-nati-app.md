# Integración de un personaje en Nati-App

Así se llevó Robin a Nati-App. Sirve de receta para un personaje nuevo, con las diferencias que trae Ignis. El código de Robin en Nati-App es la referencia viva: léelo antes de cambiar nada.

## Dónde está

- **Repo:** `~/Innovati/Nati-App` (Angular). La integración de Robin está en el commit `e724b96` ("Demo de Robin lista") de la rama `demo-robin`. Crea una rama nueva desde ella o desde la que indique el usuario.
- **Motor:** `Engine.Three` (`src/app/services/engine/engine.service.ts`). Unity es otro motor y no se toca.
- **Código del avatar:** `src/app/components/threejs/threejs-avatars/`.
  - `threejs-avatars.component.ts`: bucle de render. Llama a `animationSystemService.update()` y después a `robotFaceService.update()`.
  - `services/avatar/avatar-loader.service.ts`: carga el GLB, aplica la transformación y detecta las mallas y huesos especiales.
  - `services/animation/animation-system.service.ts`: clasifica los clips por nombre (`idling`, `idle`, `talk`, `greeting`, `point`) y hace los crossfades.
  - `services/robot/`: lo específico de Robin (ver abajo).

## Publicar el modelo (bundles)

1. **Nombre:** el avatar se identifica por el nombre del archivo. `robin.bundle.br` da la clave `robin`, la misma que usan los diccionarios del código.
2. **Generar los dos archivos:**
   - `<id>.bundle.glb`: copia exacta del GLB.
   - `<id>.bundle.br`: el GLB comprimido con brotli, calidad 11:
     ```bash
     node -e "const z=require('zlib'),f=require('fs');f.writeFileSync('ignis/ignis.bundle.br',z.brotliCompressSync(f.readFileSync('assets/ignis.glb'),{params:{[z.constants.BROTLI_PARAM_QUALITY]:11}}))"
     ```
   - iOS descarga el `.glb` (`downloadThreeBundleIOS` cambia `.br` por `.glb`) y el resto descarga el `.br`, así que hacen falta los dos.
3. **Comprobar:** el `.br` debe descomprimirse a los mismos bytes que el GLB (compara las sumas de comprobación).
4. **Subir:** el usuario sube los archivos a `https://natistoragedllo.blob.core.windows.net/bundle/` y asigna el avatar al tenant de prueba. Ninguna de las dos cosas la haces tú.
   - Content-Type `application/octet-stream`, sin `Content-Encoding: br`: la app descomprime por su cuenta.
5. **Git:** los bundles van en una carpeta `<id>/` del repo, ignorados en `.gitignore` igual que `robin/robin.bundle.*`.

Mientras el bundle no esté en el storage, se puede probar en local con un override temporal en `engine.service.ts` que apunte a `src/assets/threejs/models/<id>/`. Así se probó Robin. Elimínalo junto con la carpeta local cuando el bundle esté publicado, para que `engine.service.ts` quede sin diff.

## Registrar el avatar en el código

- **`services/avatar/avatar-transform-dict.ts`:** escala, posición y `preserveMaterials: true` para conservar los materiales PBR del GLB.
  - Robin usa `scale 6.26` y `position (0, 6.98, 0)`, de modo que la cabeza llega a `y ≈ 17` y la cámara Standard lo encuadra de cintura para arriba.
  - Un cuadrúpedo largo necesita otro encuadre. Ajústalo mirando capturas, no por cálculo.
- **`services/animation/avatar-animation-timescale.ts`:** entrada con todos los valores a 1 si los clips están autorados a velocidad real.
- **Nombres de clip:** `idle` y `talk_1..3` encajan en la clasificación existente.
  - Los gestos al hablar dependen del campo `movements` que manda el backend.
  - La lógica vuelve a `idle` cuando quedan menos de 4.5 s de audio. Es comportamiento de la app, no un fallo del modelo.
- **Guarda de crossfade:** en `onCycleFinished` hay una guarda para que un único clip `idle` no haga crossfade consigo mismo. Ya está y sirve para cualquier avatar.
- **Detección por nombre en el loader:** el loader decide qué servicios se activan según los nombres de mallas y huesos.

  | El loader detecta | Qué activa | Para Ignis |
  |---|---|---|
  | Malla `SkinnedMesh` con `body` en el nombre y morph targets | La toma como `skinnedMesh` para lipsync y expresiones | `IgnisBody` cumple las tres condiciones: verifica en la consola del navegador que los servicios de expresiones y parpadeo no escriben en `MouthWide` ni `MouthRound` |
  | Hueso con `jawroot` | `AzureLipsyncService` | `Jaw` no lo activa (correcto, la boca la mueve el servicio del personaje); conserva ese nombre |
  | Hueso con `base_head`, `l_eye`, `r_eye` | Mirada y parpadeo | Evita esos nombres |
  | Objeto con `hair` | Material de pelo | Evita ese nombre |

## Servicios del personaje (`services/robot/`)

| Archivo | Qué hace |
|---|---|
| `robot-face.service.ts` | Se activa si el GLB trae la malla `FaceScreen`: crea el `CanvasTexture`, reemplaza el material y orquesta la boca, los ojos y la capa de movimiento en cada frame |
| `robot-face-renderer.ts` | Port en TypeScript de `assets/face/faceRenderer.js`: ojos y boca de pantalla |
| `robot-mouth.util.ts` (+ spec) | Pasa los blendshapes de Azure a las 8 formas de boca, con calibración por locución |
| `robot-motion-layer.ts` | Respiración y micro-movimientos de cabeza, con la guarda `restoreUnanimated()` |

`RobotFaceService` está atado a Robin: usa un material emisivo de pantalla y dibuja la boca en el canvas. Para Ignis, generalízalo con perfiles según el nombre del avatar, como los perfiles de la demo:

- Ojos en `map` en lugar de `emissiveMap`.
- Boca con `Jaw` y shape keys.

No dupliques el servicio entero.

### Señales de la conversación

- `useCasesService.getVoiceCaptureActive()`: el usuario habla (`listening`).
- `webSocketService.getChatState()`: `false` después del primer `true` significa esperando respuesta (`thinking`). La guarda `chatStarted` ignora el valor inicial.
- `unityControllerService.getSpeechBlendData()` y `getSpeechCanceled()`: el avatar habla (`speaking`) y se corta la voz. Pese al nombre, se usan también con Three.

### Datos de Azure TTS

No llegan `visemeId` 0–21 como en la demo. La app pide `<mstts:viseme type="FacialExpression"/>`, así que cada frame (60 fps) trae 55 blendshapes estilo ARKit, indexados con `blendShapeDictionary` (`dictionaries/threejs-avatars.component.azure-dict.ts`).

- Medido con voces es-CO, `Jaw_Open` casi nunca baja de ~0.15, y `Mouth_Close` sube junto con la mandíbula en M, B y P. La apertura real de los labios es `Jaw_Open − Mouth_Close`.
- `calibrateMouth()` ajusta los umbrales a cada locución (percentil 90 de apertura y percentil 10 de mandíbula).
- Para Ignis, reutiliza `mouthFromBlendshapes()` para obtener la forma y luego aplica la tabla `jawOpen/wide/round` del prompt, con la misma suavización que en la demo.
- El reloj de la boca es `duration / frames` con el recorte `SPEECH_SHORTEN`, el mismo que usa `AzureLipsyncService`. Así la boca termina a la vez que el audio.

## Retrato para la selección de avatar

`blender/render_portrait.py` hace el de Robin:

- Importa `build_robin`, oculta el suelo, encuadra cabeza y hombros (lente de 85 mm) y saca dos PNG de 1024²: uno con fondo transparente y otro con fondo claro.
- Para Ignis, crea un script propio que importe `build_ignis`.
- El retrato aprobado de Robin está en `blender/renders/AvatarRobin.png` (es la excepción en `.gitignore`).

## Probar en Nati-App

- **Servidor:** `npm run start:local` sirve en `http://localhost:4202`. Comprueba antes si ya hay uno corriendo en ese puerto.
- **Enlace:** `http://localhost:4202/<uuid-del-tenant>`. El usuario da el uuid con el avatar ya configurado. Con Robin fue `55f9c573-ae26-4bf2-aba5-4eff1545b1dd`, que pertenece a EPM.
  - EPM tiene narración silenciada y clips de vídeo del avatar anterior. Es comportamiento del tenant, no un fallo del personaje.
- **Verificación con Playwright** (script temporal en el scratchpad, que borras al terminar):
  - La página pide `.../bundle/<id>.bundle.br`.
  - La malla `FaceScreen` tiene el `CanvasTexture`.
  - En la captura se ve el personaje.
  - Para comprobar la boca con TTS real hace falta una conversación de verdad en el enlace.
- **Tests:**
  ```bash
  npx ng test --watch=false --browsers=ChromeHeadless --no-code-coverage --include='src/app/components/threejs/threejs-avatars/**/*.spec.ts'
  ```
  - Antes de nuestros cambios ya fallaban 11 tests, porque al TestBed le falta el provider de `TranslateService`; entre ellos están los de `animation-system.service.spec.ts`.
  - Lo que importa: `robot-mouth.util.spec.ts` pasa entero y los specs del componente no rompen. Si inyectas un servicio nuevo en el componente, añade su mock a `threejs-avatars.component.spec.ts`.
