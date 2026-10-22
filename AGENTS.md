# Guía para agentes: ModeloDemo

Este repo genera personajes 3D conversacionales por código (bocetos SVG, modelo y rig con Blender Python, GLB y demo three.js) y luego los integra en Nati-App. El primero fue **Robin**. Está terminado, aprobado y publicado en Nati-App.

## Por dónde empezar

1. Lee `README.md`. Recoge la estructura, los comandos para regenerar cada pieza y las decisiones de Robin.
2. Lee el prompt del personaje que te toque. Es la especificación de la tarea, con sus fases y sus puntos de aprobación 🛑.
   - Hoy es `dragon/prompt.dragon.md` (Ignis), con su ficha `dragon/model_spec.json` y la imagen `dragon/img-referencia.jpg`.
   - `dragon/*.template.*` son borradores descartados: mencionan Windows, `run.cmd` y otras rutas que no aplican aquí.
3. Antes de escribir código, lee este archivo completo. Recoge lo que el código no cuenta: los fallos que ya costaron horas con Robin.

Una fase 🛑 termina cuando le has mostrado al usuario imágenes que tú mismo abriste y revisaste con `Read`, y él responde. Hasta ese momento no empieces la siguiente fase.

## Entorno

- **Sistema y herramientas:** Fedora, Node 22, Python 3 (Pillow para componer hojas), Google Chrome y Blender 5.2 como flatpak `org.blender.Blender`.
- **Sin generadores:** no hay generadores de imágenes ni de 3D. Todo se dibuja en SVG o se modela con `bpy`.
- **Blender:** ejecútalo siempre con `blender/run.sh <script.py> [-- args]`.
  - El flatpak arranca en `/app/blender` y no resuelve rutas relativas. `run.sh` le pasa la ruta absoluta.
  - Dentro de los scripts, construye las rutas desde `Path(__file__).resolve()`.
  - Si Blender dice que no puede abrir el archivo, falta el permiso: `flatpak override --user --filesystem=$PWD org.blender.Blender`.
- **Importar entre scripts de Blender:** usa `sys.path.insert(0, str(Path(__file__).resolve().parent))` y luego `import build_robin as B`. `blender/render_portrait.py` es el ejemplo.
- **SVG a PNG:** `concepts/svg2png.sh`. Lee `width` y `height` del primer elemento del SVG, así que el `<svg>` raíz debe declararlos en píxeles enteros.

## Blender 5.2 y el exportador glTF

- **Acciones con slots:** Blender 5 usa acciones con slots. Una tira NLA sin `strip.action_slot` asignado exporta y renderiza la pose de reposo en todos los frames. Copia el patrón de `rig_robin.py` (`bake_action` y `render_pose_sheets`).
  - Para renderizar un clip concreto: pon `use_nla = False`, asigna la acción activa y asigna también `animation_data.action_slot`.
- **Clips:** los keyframes empiezan en el frame 0 y `scene.frame_start = 0`. Con 1 los bucles saltan 1/30 s.
  - En un clip en bucle, el primer frame es igual al último.
- **Nombres:** ninguna malla puede llamarse igual que un hueso. three.js resuelve las pistas por nombre y anima el primer objeto que encuentra; por eso Robin usa `HeadShell` y `NeckRing`.
  - Blender añade `.001` al duplicar, y three.js elimina `.` y `:` de los nombres. Renombra explícitamente todo lo que dupliques o espejes.
- **Skinning:** Robin usa `export_skins=False` porque sus piezas son rígidas, emparentadas a un hueso.
  - Un personaje con malla deformable (Ignis) necesita `export_skins=True` y `export_morph=True` para los shape keys. Revisa cada argumento de `export_glb` antes de copiar esa función.
- **Shape keys y modificadores:** con `export_apply=True`, el exportador no aplica los modificadores de una malla que tiene shape keys.
  - Aplica los modificadores (bevel, mirror, weld…) antes de crear las shape keys.
- **Huesos que no se deben animar:** `export_force_sampling=True` muestrea los huesos de la armadura, y puede generar pistas constantes en huesos sin keyframes, como `Jaw`.
  - No lo verificamos con Robin. Compruébalo leyendo los `channels` del GLB exportado: es el chequeo de "ningún clip anima `Jaw`" que pide el prompt.
- **Color:** los renders usan la transformación "Khronos PBR Neutral", y la demo usa su equivalente, `THREE.NeutralToneMapping`. Mantén los dos alineados para que los colores coincidan entre render y web.
- **Validación:** `node tools/validate_glb.mjs [glb]`. Tiene que dar 0 errores. Los avisos informativos (nodos vacíos, textura que no es potencia de dos) se aceptan.

## three.js en la demo

- **Cara en `CanvasTexture`:** sobre las UV de un glTF necesita `flipY = false`, `colorSpace = SRGBColorSpace` y `needsUpdate = true` en cada dibujo.
  - Robin usa `emissiveMap` (pantalla). Unos ojos orgánicos van en `map` para recibir luz.
- **Capa procedural (`BodyAnimator._procedural`):** rota los huesos después de `mixer.update()`, sobre el valor que dejó el mixer.
  - Si un hueso no tiene pista en el clip activo, el mixer no lo reescribe y el offset se acumula frame a frame. En Nati-App la cabeza llegó a girar 44°.
  - Con Robin no ocurre en la demo porque sus clips muestrean todos los huesos. Al hacer configurables los huesos de la capa, porta la guarda `restoreUnanimated()` de Nati-App (`robot-motion-layer.ts`, ver `docs/integracion-nati-app.md`).
- **Huesos controlados en tiempo de ejecución (`Jaw`, shape keys):** escribe un valor absoluto en cada frame, calculado desde la pose de reposo que guardaste al cargar: `restQuat · rotación(ángulo)`. No lo apliques de forma incremental.
- **Gancho del test:** `window.__robin` (estado, `face`, `visemes`, `body`, `errors`) es el contrato con `demo/tests/smoke.spec.js`. Si añades campos, que sean aditivos.

## Test de humo (`cd demo && npm test`)

- Usa el Chrome del sistema con GPU (`--enable-gpu`). Con SwiftShader va a 1-4 FPS y los tiempos del ciclo fallan. `PW_SWIFTSHADER=1` existe solo como último recurso.
- Los píxeles se comprueban sobre `page.screenshot()`. `readPixels` del canvas WebGL devuelve vacío sin `preserveDrawingBuffer`.
- El test falla con cualquier error de consola, incluido un 404. Por eso el favicon es un data-URI en `index.html`, y cualquier recurso nuevo debe existir de verdad.
- Revisa tú mismo las capturas en `demo/tests/output/` antes de dar el test por bueno.

## Reglas del repo

- **Robin no se toca:** `build_robin.py`, `rig_robin.py`, `assets/robin.glb` y `robin/` (bundles) son de solo lectura. Un personaje nuevo va en archivos propios.
- **Dependencias:** versión exacta y publicada hace más de dos semanas. Las fijadas ahora son `three@0.186.1`, `vite@8.3.3` y `@playwright/test@1.63.0`.
- **Seguridad:** la clave de Azure Speech o del LLM vive solo en un backend. El frontend pide un token a un endpoint propio (ver README, "Conectar Azure Speech + LLM reales").
- **Git:** haz commit solo cuando el usuario lo pida.
- **Decisiones:** las menores (un ángulo, un tono, un grosor) las tomas tú y las anotas en la sección "Decisiones y desviaciones" del README. Si algo de la ficha es inviable, díselo al usuario con el motivo y propón la alternativa más cercana.

## Llevar un personaje a Nati-App

Cuando el usuario pida integrar o publicar el personaje en Nati-App, generar el bundle `.br` o el retrato para la selección de avatar, lee `docs/integracion-nati-app.md`.
