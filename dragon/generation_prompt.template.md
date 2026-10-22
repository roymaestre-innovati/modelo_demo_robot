# Prompt para generar un modelo nuevo

Copia este prompt y reemplaza los campos entre corchetes. Adjunta o pega también el contenido
completo de `blender/models/<id>/model_spec.json`.

```text
Trabaja como artista técnico de personajes 3D y desarrollador de Blender Python para este repo.

Quiero crear un modelo nuevo a partir de esta ficha:
[PEGAR model_spec.json COMPLETO]

Implementa un generador separado para este modelo:
- ID: [id]
- Carpeta de trabajo: blender/models/[id]/
- Salida GLB: assets/models/[id]/model.glb
- Metadatos: assets/models/[id]/metadata.json

Reglas:
1. Basa la forma, la anatomía y el movimiento en la ficha. No conviertas el diseño en un robot
   humanoide ni copies a Robin si la ficha describe otra criatura.
2. Crea build_model.py y, si la geometría y el rig se benefician de separarse, rig_model.py.
   Usa bpy y deja ambos scripts ejecutables desde blender/run.cmd.
3. Mantén el generador aislado en la carpeta de este modelo. No alteres build_robin.py, rig_robin.py,
   perfiles existentes ni GLB existentes.
4. Usa piezas independientes cuando faciliten articulación, y una malla con skinning cuando la
   forma lo necesite. Ajusta el tipo de rig a la anatomía; no impongas nombres Mixamo.
5. Si runtime.target es "conversation_demo", incluye los clips idle, talk_1, talk_2 y talk_3, además
   de FaceScreen UV y FaceScreenMat. Haz que los gestos tengan sentido para esta especie. Spine2,
   Neck y Head son opcionales.
6. Si runtime.target es "standalone_glb", respeta su cara y rig propios y no añadas requisitos de
   la demo conversacional.
7. Exporta GLB con materiales PBR, transformaciones aplicadas, escala en metros, Z arriba y frente
   hacia -Y. Respeta max_triangles y evita nombres de nodo con dos puntos.
8. Añade metadata.json con id, name, accent y la ruta de model_spec.json. No escribas metadatos
   si el GLB no se exportó correctamente.
9. Antes de terminar, revisa los archivos modificados y da los comandos Windows para generar y, si
   corresponde, validar el modelo.

Si falta un detalle, decide una opción sencilla que preserve la ficha y anota la decisión en la
respuesta. No detengas el trabajo para pedir decisiones de estilo menores.
```
