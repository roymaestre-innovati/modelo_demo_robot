"""Ojos de Ignis sobre el modelo: un render de la cabeza por estado de EyeRenderer.

Las texturas salen de assets/face/ignis_eyes.html (?state=...&blink=...) capturadas con Chrome
en blender/renders/ignis/eyes/tex/. Uso: blender/run.sh render_ignis_eyes.py
Salida: blender/renders/ignis/eyes/<estado>.png
"""
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_ignis as B  # noqa: E402

OUT = B.RENDERS / "eyes"
STATES = ["neutral", "listening", "thinking", "happy", "surprised", "blink_0.5", "blink_1"]


def main():
    B.build()
    cam = B.setup_studio()
    sc = bpy.context.scene
    tex = next(n for n in bpy.data.materials["FaceScreenMat"].node_tree.nodes if n.type == "TEX_IMAGE")
    loc, target = Vector((0.75, -1.75, 1.22)), Vector((0, -0.48, 1.12))
    cam.location = loc
    cam.rotation_euler = (target - loc).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = 85
    v = target - loc
    bpy.data.objects["Floor"].rotation_euler = (0, 0, __import__("math").atan2(-v.x, v.y))
    sc.render.resolution_x, sc.render.resolution_y = 640, 560
    for s in STATES:
        img = bpy.data.images.load(str(OUT / "tex" / f"{s}.png"))
        tex.image = img
        sc.render.filepath = str(OUT / f"{s}.png")
        bpy.ops.render.render(write_still=True)
        print(f"[ignis] ojos {s}")


if __name__ == "__main__":
    main()
