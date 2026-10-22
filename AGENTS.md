# Guía para agentes: ModeloDemo

Este repo genera personajes 3D conversacionales por código (bocetos SVG, modelo y rig con Blender Python, GLB y demo three.js) y luego los integra en Nati-App. Hay dos personajes terminados y aprobados:

- **Robin**: robot con pantalla por cara. Publicado en Nati-App.
- **Ignis**: dragón cuadrúpedo con ojos en canvas y boca con mandíbula. Está en la demo (`?model=ignis`).

## Por dónde empezar

1. Lee `README.md`. Recoge la estructura, los comandos para regenerar cada pieza (tablas de Robin y de Ignis) y las decisiones de cada personaje.
2. Elige tu caso:
   - **Modificar a Ignis**: sigue la sección "Modificar a Ignis" de este archivo. La especificación original es `dragon/prompt.dragon.md`, con la ficha `dragon/model_spec.json` y la imagen `dragon/img-referencia.jpg`.
   - **Crear un personaje nuevo**: escribe o pide su prompt con fases y puntos de aprobación 🛑, tomando `dragon/prompt.dragon.md` como modelo.
   - `dragon/*.template.*` son borradores descartados: mencionan Windows, `run.cmd` y otras rutas que no aplican aquí.
3. Antes de escribir código, lee este archivo completo. Recoge lo que el código no cuenta: los fallos que ya costaron horas con Robin y con Ignis.

**Revisión visual.** Todo cambio que se vea (modelo, rig, animación, ojos, demo) termina con imágenes revisadas: renders de Blender, hojas de poses o capturas del test. Ábrelas y míralas tú mismo antes de dar el trabajo por bueno. Si tu entorno no te deja ver imágenes, dile al usuario qué archivos abrir y espera su respuesta. Una fase 🛑 termina cuando el usuario ha visto esas imágenes y responde; hasta entonces no empieces la siguiente.

## Modificar a Ignis

Todo Ignis sale de código: cambia el script y regenera la cadena. Nunca edites `assets/ignis.glb` ni los `.blend` a mano; se sobrescriben al regenerar.

| Qué cambiar | Dónde |
|---|---|
| Proporciones, colores, densidad de la malla, boca, ojos (posición) | constantes al inicio de `blender/build_ignis.py` |
| Huesos, pesos, shape keys, poses y duración de los clips | `blender/rig_ignis.py` (`bone_table`, `idle`, `talk_1..3`, `mouth_shape_keys`) |
| Dibujo y estados de los ojos | `assets/face/eyeRenderer.js` (previsualización: `assets/face/ignis_eyes.html`) |
| Tabla de bocas, suavizado de la mandíbula | `demo/src/jawFace.js` |
| Encuadres, fondo, huesos de la capa procedural | `demo/src/models/ignis.js` |
| Llama y chispas | `demo/src/models/flameEffects.js` |

**Cadena de regeneración** (comandos exactos en la tabla de Ignis del README):

1. `blender/run.sh rig_ignis.py -- --render-poses` reconstruye el modelo, el rig y los clips, y exporta el GLB. Al terminar imprime el deslizamiento de los pies apoyados: tiene que ser menor de 1 cm. `rig_ignis.py` llama a `build_ignis.py`, así que un cambio en el modelo también pasa por aquí.
2. `python3 blender/compose_ignis_sheets.py` compone las hojas de poses y bocas. Revísalas.
3. `node tools/validate_glb.mjs assets/ignis.glb` tiene que terminar en `OK`. Comprueba que ningún clip anima `Jaw` ni los shape keys.
4. `cd demo && npm test` tiene que pasar con los dos modelos. Revisa las capturas de `demo/tests/output/`.

**Invariantes de Ignis:**

- `Jaw`, `MouthWide` y `MouthRound` los controla three.js en tiempo de ejecución. Ningún clip les pone keyframes.
- Las patas apoyadas no deslizan: se animan con objetivos IK (`ik(...)` en `rig_ignis.py`) que se hornean a FK. Para levantar una pata, mueve su objetivo IK y añádela a `LIFTING`.
- Solo `WingMembraneMat` es de doble cara.
- Anota cada decisión menor en "Decisiones y desviaciones (Ignis)" del README.

## Entorno

- **Herramientas:** Node 22, Python 3 (Pillow para componer hojas), Google Chrome y Blender 5.2. Ningún generador de imágenes ni de 3D: todo se dibuja en SVG o se modela con `bpy`.
- **Blender:** ejecútalo siempre con `blender/run.sh <script.py> [-- args]`.
  - Por defecto usa el flatpak `org.blender.Blender`. Con otra instalación (Mac, Windows/WSL, Linux sin flatpak), define `BLENDER` con la ruta del ejecutable: `BLENDER=/ruta/a/blender blender/run.sh rig_ignis.py`.
  - Dentro de los scripts, construye las rutas desde `Path(__file__).resolve()`.
  - Para importar entre scripts: `sys.path.insert(0, str(Path(__file__).resolve().parent))` y luego `import build_ignis as B`. `blender/render_ignis_eyes.py` es el ejemplo.
- **Solo con el flatpak:**
  - Arranca en `/app/blender` y no resuelve rutas relativas; `run.sh` le pasa la ruta absoluta.
  - Solo puede leer y escribir dentro del proyecto: los renders y archivos temporales van en carpetas del repo, nunca en `/tmp`.
  - Si dice que no puede abrir el archivo, falta el permiso: `flatpak override --user --filesystem=$PWD org.blender.Blender`.
- **SVG a PNG:** `concepts/svg2png.sh`. Lee `width` y `height` del primer elemento del SVG, así que el `<svg>` raíz debe declararlos en píxeles enteros.
- **Páginas con módulos ES en Chrome headless** (por ejemplo `assets/face/ignis_eyes.html`): sírvelas por HTTP (`python3 -m http.server -d assets/face 8123`). Desde `file://` Chrome bloquea los `import`.

## Blender 5.2 y el exportador glTF

- **Acciones con slots:** Blender 5 usa acciones con slots. Una tira NLA sin `strip.action_slot` asignado exporta y renderiza la pose de reposo en todos los frames. Copia el patrón de `bake_clip` en `rig_ignis.py`.
  - Para renderizar un clip concreto: pon `use_nla = False`, asigna la acción activa y asigna también `animation_data.action_slot` (`use_action` en `rig_ignis.py`).
- **Clips:** los keyframes empiezan en el frame 0 y `scene.frame_start = 0`. Con 1 los bucles saltan 1/30 s.
  - En un clip en bucle, el primer frame es igual al último.
- **Nombres:** ninguna malla puede llamarse igual que un hueso. three.js resuelve las pistas por nombre y anima el primer objeto que encuentra; por eso Robin usa `HeadShell` y `NeckRing`, e Ignis `IgnisBody`.
  - Blender añade `.001` al duplicar, y three.js elimina `.` y `:` de los nombres de nodo. Renombra explícitamente todo lo que dupliques o espejes.
- **Skinning:** Robin usa `export_skins=False` (piezas rígidas emparentadas a un hueso). Ignis usa `export_skins=True` y `export_morph=True`.
  - Las mallas con skin van sin padre, solo con el modificador Armature: así quedan en la raíz del glTF y el validador no avisa `NODE_SKINNED_MESH_NON_ROOT`. El aviso del exportador "Armature must be the parent of skinned mesh" es inofensivo.
  - Como mucho 4 huesos por vértice, normalizados (`limit_influences` en `rig_ignis.py`).
- **Pistas que no deben existir:** `export_force_sampling=True` crea pistas constantes en todos los huesos, `Jaw` incluido. Ignis exporta con `export_force_sampling=False`, `export_optimize_animation_size=True` y `export_optimize_animation_keep_anim_armature=False`.
  - Consecuencia: en cada clip, los huesos que no se mueven no tienen pista. La demo lo compensa con `restoreUnanimated()` (ver "three.js en la demo").
- **Shape keys y modificadores:** con `export_apply=True`, el exportador no aplica los modificadores de una malla que tiene shape keys. Aplica los modificadores (remesh, booleano, decimate…) antes de crear las shape keys.
- **Malla low-poly de Ignis:** se une con remesh por vóxeles, se recorta la boca con booleanos y se reduce con `Decimate` en dos pasadas (cabeza más densa).
  - Las zonas definidas por material (interior de la boca) se marcan sobre la malla densa, antes de `Decimate`. Asignadas después, el borde sale dentado y parece una fila de dientes.
  - Tras `Decimate`, limpia astillas (`remove_doubles`, `dissolve_degenerate`) y ejecuta `mesh.validate()`.
- **Texturas escritas con `image.pixels`:** en una imagen byte, los valores van en sRGB. No los pases a lineal.
- **Color:** los renders usan la transformación "Khronos PBR Neutral", y la demo usa su equivalente, `THREE.NeutralToneMapping`. Mantén los dos alineados para que los colores coincidan entre render y web.
  - Los emisivos brillantes se desaturan hacia blanco con este tone mapping (la llama de Ignis se veía color melocotón). Baja el color base y sube la emisión antes de tocar la curva.
- **Validación:** `node tools/validate_glb.mjs [glb]`. Tiene que dar 0 errores. Los avisos informativos (nodos vacíos, textura que no es potencia de dos) se aceptan. Un nombre de archivo que empieza por `ignis` activa las comprobaciones de la boca.

## three.js en la demo

- **Perfiles:** `?model=robin|ignis` elige un perfil de `demo/src/models/`. Un personaje nuevo es un perfil nuevo más su entrada en `models/index.js`. `VisemePlayer`, `Conversation` y `BodyAnimator` no saben qué modelo hay cargado; mantenlos así.
- **Cara en `CanvasTexture`:** sobre las UV de un glTF necesita `flipY = false`, `colorSpace = SRGBColorSpace` y `needsUpdate = true` en cada dibujo.
  - Robin usa `emissiveMap` (pantalla). Los ojos de Ignis van en `map` para recibir luz.
- **Capa procedural (`BodyAnimator._procedural`):** rota los huesos después de `mixer.update()`, sobre el valor que dejó el mixer.
  - Si un hueso no tiene pista en el clip activo, el mixer no lo reescribe y el offset se acumula frame a frame (en Nati-App la cabeza llegó a girar 44°). `BodyAnimator.restoreUnanimated()` lo evita devolviendo esos huesos a reposo. Los huesos de la capa salen de `bodyBones` del perfil.
- **Huesos controlados en tiempo de ejecución (`Jaw`, shape keys):** escribe un valor absoluto en cada frame, calculado desde la pose de reposo que guardaste al cargar: `rotación · restQuat` (ver `JawFace.update`). No lo apliques de forma incremental. Crea la cara antes del primer `mixer.update()`, con el modelo aún en reposo.
- **Mallas con skin:** `frustumCulled = false`; la caja de reposo no sigue a la animación.
- **Gancho del test:** `window.__robin` (alias `window.__demo`: estado, `face`, `visemes`, `body`, `profile`, `errors`) es el contrato con `demo/tests/smoke.spec.js`. Si añades campos, que sean aditivos.

## Test de humo (`cd demo && npm test`)

- Corre las mismas comprobaciones con cada modelo de `MODELS` en `smoke.spec.js`. Para Ignis, además, que `Jaw` se mueva al hablar y vuelva a reposo.
- Usa el Chrome del sistema con GPU (`--enable-gpu`). Con SwiftShader va a 1-4 FPS y los tiempos del ciclo fallan. `PW_SWIFTSHADER=1` existe solo como último recurso.
- Los píxeles se comprueban sobre `page.screenshot()`. `readPixels` del canvas WebGL devuelve vacío sin `preserveDrawingBuffer`.
- El test falla con cualquier error de consola, incluido un 404. Por eso el favicon es un data-URI en `index.html` y las chispas de Ignis usan una textura generada en canvas. Cualquier recurso nuevo debe existir de verdad.

## Reglas del repo

- **Robin no se toca:** `build_robin.py`, `rig_robin.py`, `assets/robin.glb` y `robin/` (bundles) son de solo lectura. Un personaje nuevo va en archivos propios. Los cambios compartidos de la demo deben dejar a Robin igual (el test de Robin tiene que seguir pasando).
- **Dependencias:** versión exacta y publicada hace más de dos semanas. Las fijadas ahora son `three@0.186.1`, `vite@8.3.3` y `@playwright/test@1.63.0`.
- **Seguridad:** la clave de Azure Speech o del LLM vive solo en un backend. El frontend pide un token a un endpoint propio (ver README, "Conectar Azure Speech + LLM reales").
- **Git:** haz commit solo cuando el usuario lo pida.
- **Decisiones:** las menores (un ángulo, un tono, un grosor) las tomas tú y las anotas en la sección de decisiones del personaje en el README. Si algo de la ficha es inviable, díselo al usuario con el motivo y propón la alternativa más cercana.

## Llevar un personaje a Nati-App

Cuando el usuario pida integrar o publicar el personaje en Nati-App, generar el bundle `.br` o el retrato para la selección de avatar, lee `docs/integracion-nati-app.md`.
