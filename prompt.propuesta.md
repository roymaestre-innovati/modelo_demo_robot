# Robin: robot 3D conversacional para demo en three.js

## Contexto

Vamos a montar una demo de un asistente conversacional con cuerpo: un robot llamado **Robin**, renderizado en un navegador con three.js. Más adelante Robin estará conectado a un LLM y al servicio text-to-speech de Azure; Azure entrega, junto con el audio, una secuencia de eventos de visema (`visemeId` 0–21 con su `audioOffset`) que usaremos para animar la boca. En esta etapa no hay credenciales: todo debe funcionar con datos simulados y quedar listo para enchufar los servicios reales.

Tu trabajo cubre el flujo completo: bocetos, modelo 3D, rig, animaciones, cara animada e integración en una demo web. Trabajas en este directorio con bash, Node 22, Python 3 y Blender. No tienes generadores de imágenes ni de 3D externos, así que los bocetos los dibujas tú en SVG y el modelo lo construyes por código en Blender.

## Diseño de Robin

- **Estética:** mascota amigable y estilizada, formas redondeadas y limpias (referencia de tono: Eve de Wall-E, robots de producto de consumo). Nada agresivo, industrial ni realista. Geometría simple: favorece lo que se ve bien en un plano medio y pesa poco en tiempo real.
- **Cuerpo completo**, de pie, sin locomoción. La cámara normalmente lo encuadra de cintura para arriba, pero a veces se verá entero, así que las piernas deben estar terminadas y proporcionadas.
- **Cabeza con pantalla como cara.** La pantalla es una superficie negra brillante donde se dibujan ojos y boca en 2D. La boca y los ojos no son geometría.
- **Manos** con dedos simplificados (p. ej. pulgar + dos o tres dedos agrupados) que permitan gestos legibles al hablar.
- **Paleta:** cuerpo blanco/gris claro mate, articulaciones y detalles gris oscuro, pantalla negra brillante, ojos y boca en cian `#3DE0FF`. No hay color de marca: deja el acento como una constante única fácil de cambiar (en el script de Blender y en el código de la cara).
- **Pose base:** A-pose.

## Fases y puntos de aprobación

Avanza fase por fase. En cada punto de aprobación (🛑) detente, muéstrame la evidencia y espera mi respuesta antes de continuar; cada fase posterior depende de que la anterior esté aprobada, y rehacer un modelo 3D por un diseño no validado es caro.

### Fase 1: Conceptos

1. Dibuja 3 o 4 variantes de concepto de Robin, claramente distintas entre sí (proporciones, forma de cabeza/pantalla, silueta del torso, tipo de manos), como SVG en `concepts/`.
2. Conviértelas a PNG con la herramienta que haya disponible (`rsvg-convert`, `inkscape`, o Chromium headless) y verifica que el PNG se ve como esperas antes de mostrármelo.
3. Para cada variante, una línea explicando su idea.

🛑 **Aprobación 1:** elijo una variante (o pido cambios).

### Fase 2: Turnaround

Sobre la variante elegida, dibuja en SVG una hoja turnaround en A-pose con vistas ortográficas frontal, lateral y trasera, alineadas en altura, fondo neutro y medidas aproximadas (altura total ~1.6 unidades Blender, proporciones de cada pieza). Esta hoja es el plano que seguirás para modelar, así que debe ser coherente entre vistas. Incluye una vista de la pantalla con un ejemplo de ojos y boca.

🛑 **Aprobación 2:** apruebo el turnaround.

### Fase 3: Modelo 3D

Blender está instalado como flatpak (versión 5.2). Ejecútalo en modo headless:

```
flatpak run org.blender.Blender --background --python blender/build_robin.py
```

Si el sandbox de flatpak no puede leer o escribir en el directorio del proyecto, pídeme permiso para ejecutar `flatpak override --user --filesystem=<ruta del proyecto> org.blender.Blender`.

Escribe `blender/build_robin.py`, un script reproducible que construye Robin desde cero (escena vacía, sin depender de archivos `.blend` previos):

- Robot hard-surface **segmentado**: cabeza, cuello, torso, pelvis, brazo, antebrazo, mano y dedos, muslo, pierna, pie. Cada pieza es una malla separada.
- Formas redondeadas con modificadores (bevel, subdivision) aplicados antes de exportar.
- La pantalla es una malla independiente llamada `FaceScreen` con material `FaceScreenMat`, UVs que llenan el rango 0–1 sin distorsión y material emisivo; three.js reemplazará su textura en tiempo de ejecución.
- Parámetros principales (proporciones, color de acento, nivel de bevel) como constantes al inicio del script.
- Presupuesto: ≤ 30 000 triángulos totales, texturas ≤ 2K (idealmente sin texturas, solo materiales PBR planos).

Renderiza vistas previas (frontal y tres cuartos, de cuerpo entero y en plano medio) en `blender/renders/`.

🛑 **Aprobación 3:** apruebo el modelo sin rig.

### Fase 4: Rig y animaciones

Extiende el script (o añade `blender/rig_robin.py`) para:

- Crear un esqueleto humanoide propio con nombres de hueso estilo Mixamo **sin el prefijo `mixamorig:`** (`Hips`, `Spine`, `Spine1`, `Spine2`, `Neck`, `Head`, `LeftShoulder`, `LeftArm`, `LeftForeArm`, `LeftHand`, dedos simplificados, `LeftUpLeg`, `LeftLeg`, `LeftFoot`, `LeftToeBase`, y equivalentes `Right*`). El prefijo con dos puntos se evita porque three.js altera los nombres con `:` al resolver animaciones; con nombres estándar se podrán retargetear animaciones externas más adelante.
- Skinning **rígido**: cada pieza emparentada al 100 % a su hueso. Sin weight painting.
- Clips con keyframes, en bucle limpio (primer y último frame iguales):
  - `idle`: respiración leve, balanceo sutil de peso entre piernas, pequeños movimientos de cabeza. 4–6 s.
  - `talk_1`, `talk_2`, `talk_3`: gestos de manos y brazos de alguien explicando algo (abrir palmas, señalar suave, enumerar), con movimiento leve de torso y cabeza. Distintos entre sí. 3–5 s cada uno. Las piernas apenas se mueven.
- Exportar `assets/robin.glb` (glTF binario, con los cuatro clips, Y-up).

Valida el GLB con `gltf-validator` (vía npm) y corrige cualquier error.

### Fase 5: Cara en pantalla

La cara se dibuja en un `CanvasTexture` aplicado a `FaceScreenMat`. Genera los sprites (o el código de dibujo procedural en canvas, lo que resulte más limpio) en `assets/face/`.

**Ojos**, cinco estados controlados por la aplicación según el ciclo de la conversación:

| Estado | Cuándo | Aspecto sugerido |
|---|---|---|
| `neutral` | reposo y mientras habla | ojos abiertos, parpadeo automático aleatorio cada 2–6 s |
| `listening` | el usuario está hablando | ojos ligeramente más grandes, atentos |
| `thinking` | esperando al LLM | ojos mirando hacia arriba/lado o animación de carga |
| `happy` | respuestas positivas | ojos en arco (^ ^) |
| `surprised` | reservado | ojos redondos grandes |

En esta versión el LLM no emite emociones; deja documentado en el código cómo se podría añadir después (p. ej. etiquetas de emoción en la respuesta).

**Boca**, 8 formas. Mapea los 22 visemas de Azure así:

| Forma | Visemas Azure |
|---|---|
| `REST` (cerrada) | 0 |
| `MBP` (labios juntos) | 21 |
| `FV` | 18 |
| `A` (abierta) | 1, 2, 9, 11 |
| `E` (media, ancha) | 4, 5, 6, 12, 13 |
| `O` (redonda) | 3, 8, 10 |
| `U` (pequeña, redonda) | 7 |
| `CONS` (semicerrada, consonantes) | 14, 15, 16, 17, 19, 20 |

La boca en reposo puede tener un pequeño loop sutil para que la pantalla no se vea estática.

### Fase 6: Demo en three.js

Proyecto Vite en `demo/`, JavaScript plano, three.js como dependencia npm con versión fija. Se arranca con `npm install && npm run dev`.

- Carga `assets/robin.glb`, cámara en plano medio por defecto con opción (tecla o botón) de ver cuerpo completo. Iluminación agradable y sencilla.
- **`FaceScreen`**: módulo que dibuja ojos y boca en el canvas, expone `setEyes(estado)` y `setMouth(forma)`.
- **Reproductor de visemas**: recibe la lista de eventos `{ visemeId, audioOffset }` (`audioOffset` en ticks de 100 ns; ms = ticks / 10 000), los agenda contra el reloj del audio y actualiza la boca usando la tabla de mapeo.
- **Animación del cuerpo**: `AnimationMixer` con `idle` en reposo. Al hablar, alterna aleatoriamente entre `talk_1..3` con crossfade de ~0.4 s, sin repetir el mismo clip dos veces seguidas; al terminar vuelve a `idle` con fundido. Encima, una capa procedural leve (respiración, micro-movimientos de cabeza) para que los bucles no se noten.
- **Interfaz `SpeechSource`** con una implementación mock: un JSON de eventos de visema en formato Azure (`demo/mock/visemes.json`) y un reloj que los reproduce sin audio real o con un tono de prueba. Debe ser trivial sustituirla por una implementación real con el SDK de Azure Speech y el LLM.
- Botón **"Hablar"** que recorre el ciclo completo: `listening` → `thinking` → hablando (visemas + gestos) → `neutral`.

Verifica la demo con un test de humo en Playwright: la página carga sin errores en consola, el GLB aparece y una captura de pantalla muestra a Robin. Revisa tú la captura.

## Entregables

```
concepts/      variantes SVG + PNG, turnaround
blender/       build_robin.py (y rig_robin.py si lo separas), renders/
assets/        robin.glb, face/
demo/          proyecto Vite, mock/visemes.json
README.md      cómo regenerar cada pieza y cómo conectar Azure + LLM reales
```

## Criterios de terminado

- Los tres puntos de aprobación fueron aprobados por mí.
- `robin.glb` pasa `gltf-validator` sin errores, tiene ≤ 30 000 triángulos y contiene `idle`, `talk_1`, `talk_2`, `talk_3`.
- La malla `FaceScreen` existe y su textura se reemplaza en tiempo de ejecución.
- `npm run dev` levanta la demo; el botón "Hablar" ejecuta el ciclo completo con boca sincronizada y gestos.
- El test de humo de Playwright pasa.
- El README permite regenerar todo desde cero.

Si algo no se puede cumplir tal como está descrito (una herramienta no funciona, una limitación de Blender o three.js), dímelo explicando el motivo y propone la alternativa más cercana en vez de improvisar en silencio.
