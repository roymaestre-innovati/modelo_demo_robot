# Ignis: dragón 3D conversacional para la demo de three.js

## Contexto

Este repo ya contiene a **Robin**, un robot conversacional generado de punta a punta: bocetos en SVG, modelo y rig por código en Blender, `assets/robin.glb` y una demo Vite en `demo/` que recorre el ciclo de conversación (`listening` → `thinking` → hablando con visemas de Azure y gestos → `neutral`). Lee `README.md` antes de empezar: describe la estructura, los comandos y las decisiones que ya se tomaron.

Ahora vamos a sumar un segundo personaje, **Ignis**, un dragón de fuego joven, y que la misma demo pueda mostrar uno u otro. Tu trabajo es diseñarlo, modelarlo, riggearlo, animarlo e integrarlo en la demo **sin romper a Robin**.

Fuentes de verdad:
- `dragon/model_spec.json`: ficha con el diseño, los materiales, la anatomía, los huesos, los clips y las restricciones de exportación. Síguela. Si algo de la ficha resulta inviable, avísame en vez de ignorarlo.
- `dragon/img-referencia.jpg`: imagen de referencia del diseño. Ignis debe parecerse a ella: cuadrúpedo, cuello erguido, low-poly facetado, cuernos naranjas, vientre de placas, alas granate y cola con llama.
- Este prompt define el proceso, la cara y la integración.

`dragon/generation_prompt.template.md` y `dragon/model_spec.template.json` son borradores anteriores. No los uses ni los modifiques.

## Entorno

Fedora, Node 22, Python 3 y Blender 5.2 como flatpak. Ejecuta Blender siempre con `blender/run.sh <script.py> [-- args]`: el flatpak no resuelve rutas relativas, y por eso existe ese wrapper. La conversión de SVG a PNG se hace con `concepts/svg2png.sh` (Chrome headless). No tienes generadores de imágenes ni de 3D: dibujas en SVG y modelas por código.

## Diseño de la cara

La cara de Ignis no es una pantalla como la de Robin:

- **Ojos:** se dibujan en 2D sobre un `CanvasTexture`. Van en una malla `FaceScreen` formada por dos parches que siguen la curvatura de la cabeza en las cuencas de los ojos, con el material `FaceScreenMat`. Layout de UV: el ojo izquierdo de Ignis en u 0–0.5 y el derecho en u 0.5–1. El aspecto sale de la imagen de referencia: esclerótica blanca, iris ámbar grande, pupila, brillo y párpado superior del color del cuerpo. Los ojos deben recibir la luz de la escena (`map`, no solo `emissiveMap`) para no verse como pantallas. Usa los mismos cinco estados de Robin (`neutral` con parpadeo automático, `listening`, `thinking`, `happy`, `surprised`) con la API `setEyes(estado)`.
- **Boca:** se mueve con el hueso `Jaw` más dos shape keys (`MouthWide` y `MouthRound`). Al abrirse muestra un interior oscuro y una lengua, sin dientes. La demo ya traduce los 22 visemas de Azure a 8 formas de boca (`demo/src/visemeMap.js`). Para Ignis, cada forma se convierte en tres valores:

| Forma | `jawOpen` | `wide` | `round` |
|---|---|---|---|
| `REST` | 0.0 | 0.0 | 0.0 |
| `MBP` | 0.0 | 0.0 | 0.0 |
| `FV` | 0.1 | 0.2 | 0.0 |
| `A` | 0.8 | 0.2 | 0.0 |
| `E` | 0.45 | 0.7 | 0.0 |
| `O` | 0.6 | 0.0 | 0.7 |
| `U` | 0.25 | 0.0 | 0.9 |
| `CONS` | 0.25 | 0.3 | 0.0 |

`jawOpen` = 1 es la apertura máxima natural de la mandíbula; elige ese ángulo para que se vea expresivo sin parecer agresivo. Estos valores son un punto de partida: ajústalos a ojo y documenta lo que cambies. La sprite de Robin puede cambiar de golpe, pero una mandíbula que salta se ve mal, así que interpola cada valor hacia su objetivo con una suavización de ~50–70 ms.

`Jaw` y los shape keys los controla three.js en tiempo de ejecución, así que **ningún clip debe tener keyframes en `Jaw` ni en los shape keys**: el `AnimationMixer` los pisaría.

## Fases y puntos de aprobación

En cada 🛑 detente, muéstrame la evidencia (imágenes que tú mismo hayas revisado antes) y espera mi respuesta. Las decisiones menores que no cambian la ficha (un ángulo, un grosor, un tono) las tomas tú y las anotas en la sección de decisiones del README, sin detenerte.

### Fase 1: Turnaround

La imagen de referencia reemplaza la fase de conceptos. A partir de ella, dibuja en SVG, en `concepts/ignis/`, una hoja turnaround en la pose de reposo:

- Vistas ortográficas frontal, lateral y superior, alineadas y a la misma escala. La superior sirve para definir las alas y la cola.
- Medidas aproximadas en metros (altura 1.5 m hasta los cuernos), con la posición de las articulaciones principales marcada.
- Un recuadro de la cabeza con los ojos en `neutral` y la boca en `REST` y en `A`.
- Las alas en una vista aparte, abiertas a la mitad, para definir los tres segmentos.

Puedes reutilizar el enfoque de `concepts/gen_turnaround.py`, pero en un script propio (`concepts/ignis/gen_turnaround.py`).

🛑 **Aprobación 1:** turnaround.

### Fase 2: Modelo

Crea `blender/build_ignis.py`, un script reproducible desde una escena vacía:

- Una malla principal (`IgnisBody`) para el torso, el cuello, la cabeza, las patas y la cola, pensada para deformar con pesos suaves. Pon loops de vértices suficientes en las articulaciones (cuello, hombros, caderas, base y segmentos de la cola), aunque el estilo sea low-poly.
- Flat shading en todo, para el aspecto facetado de la referencia. Sin subdivision en la exportación.
- Alas, cuernos, púas, garras, interior de la boca, `FaceScreen` y `TailFlame` según `anatomy.parts` de la ficha.
- Los materiales de la ficha. `WingMembraneMat` debe ser de doble cara (`doubleSided` en el glTF).
- Las proporciones, el acento y los colores, como constantes al inicio del script.
- ≤ 30 000 triángulos. Por el estilo debería quedar muy por debajo.

Renderiza en `blender/renders/ignis/` con la misma transformación de color que Robin (Khronos PBR Neutral): frontal, lateral, tres cuartos de cuerpo completo y un plano medio de la cabeza y el pecho.

🛑 **Aprobación 2:** modelo sin rig.

### Fase 3: Rig y animaciones

Crea `blender/rig_ignis.py`:

- El esqueleto de `rig.bones` de la ficha (con los espejos `_R`), pesos automáticos y correcciones donde la deformación falle (axilas de las alas, base del cuello, unión de la cola). Las piezas rígidas (llama, cuernos y garras si las separaste, `FaceScreen`) se emparentan a su hueso.
- Las shape keys `MouthWide` y `MouthRound` sobre la malla que forma la boca.
- Los clips `idle`, `talk_1`, `talk_2` y `talk_3` según `animations` de la ficha, a 30 fps. `idle` va en bucle limpio. Los `talk_*` empiezan y terminan cerca de la pose de `idle` para que el crossfade sea limpio.
- **Las patas apoyadas no deben deslizarse.** Usa constraints IK para las patas mientras animas y hornea el resultado a keyframes FK antes de exportar. El deslizamiento de un pie apoyado debe ser menor a 1 cm. En `talk_1` solo se separa del suelo la garra que se levanta.
- Exporta `assets/ignis.glb`.

Generaliza `tools/validate_glb.mjs` para que acepte el modelo como argumento y compruebe sus requisitos: los cuatro clips, `FaceScreen` y `FaceScreenMat`, ≤ 30 000 triángulos, sin `:` ni `.` en los nombres, y además para Ignis el hueso `Jaw`, los dos shape keys y que ningún clip anime `Jaw`. `node tools/validate_glb.mjs` sin argumentos debe seguir validando Robin igual que hoy.

Renderiza hojas de poses (varios frames de cada clip) en `blender/renders/ignis/poses/`, y también la boca en `A`, `O` y `E`.

🛑 **Aprobación 3:** rig y animaciones.

### Fase 4: Integración en la demo

La demo hoy está atada a Robin (`main.js` carga `robin.glb` y crea `FaceScreen` directamente). Refactorízala a perfiles de modelo:

- La URL `?model=robin` (por defecto) o `?model=ignis` elige el perfil.
- Cada perfil en `demo/src/models/` define: el GLB, cómo crear la cara, los encuadres de cámara (plano medio y cuerpo completo; Ignis es horizontal y largo, así que su encuadre completo debe incluir la cola), los huesos que usa la capa procedural de `BodyAnimator` (hoy fijos en `Spine2`, `Neck` y `Head`) y el fondo e iluminación si hace falta.
- La cara pasa a ser una interfaz con `setEyes`, `setMouth`, `update(dt)` y los getters `eyes`/`mouth`/`mouthChanges` que usa el test. Implementaciones: el `FaceScreen` actual para Robin y una nueva `JawFace` para Ignis, que combina `EyeScreen` (canvas de los ojos) con el control suavizado de `Jaw` y los shape keys según la tabla de arriba. `VisemePlayer`, `Conversation` y `BodyAnimator` no deben saber qué modelo está cargado.
- Efectos de Ignis solo en three.js: parpadeo leve de la llama (escala y emisión) y chispas opcionales con `Points` alrededor de la llama.
- Un selector visible en la interfaz para cambiar de modelo.
- `window.__robin` sigue existiendo para el test. Puedes añadir `window.__demo` como alias genérico.

Extiende `demo/tests/smoke.spec.js` para que el mismo conjunto de comprobaciones corra con los dos modelos. Para Ignis, además: que `Jaw` se mueva durante el habla y vuelva a reposo al terminar. Revisa tú mismo las capturas de los dos modelos.

## Entregables

```
dragon/model_spec.json           ficha (actualízala si una aprobación cambia el diseño)
concepts/ignis/                  turnaround SVG + PNG y su script
blender/build_ignis.py           modelo
blender/rig_ignis.py             rig, shape keys, clips y exportación
blender/renders/ignis/           renders y hojas de poses
assets/ignis.glb
assets/face/                     renderer de ojos de Ignis junto al de Robin
demo/src/models/                 perfiles robin e ignis
tools/validate_glb.mjs           generalizado
README.md                        sección de Ignis: comandos para regenerar, decisiones, detalles técnicos
```

## Criterios de terminado

- Las tres aprobaciones están dadas.
- `node tools/validate_glb.mjs assets/ignis.glb` pasa con 0 errores, y `node tools/validate_glb.mjs` sigue pasando con Robin.
- `npm run dev` con `?model=ignis` muestra a Ignis haciendo el ciclo completo: ojos con estados, mandíbula sincronizada con los visemas, gestos `talk_1..3` alternados sin repetir y vuelta a `idle`.
- `?model=robin` se comporta exactamente como antes.
- `npm test` pasa con los dos modelos.
- No modificaste `build_robin.py`, `rig_robin.py` ni `robin.glb`.

Si algo no se puede cumplir tal como está descrito (una limitación de Blender, del exportador glTF o de three.js), dímelo con el motivo y propone la alternativa más cercana en vez de improvisar en silencio.
