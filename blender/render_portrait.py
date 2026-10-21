"""Retrato de Robin (cabeza y hombros) para la seleccion de avatar.

Uso: blender/run.sh render_portrait.py
Salida: blender/renders/robin_avatar.png (fondo transparente) y robin_avatar_bg.png (fondo neutro), 1024x1024.
"""
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_robin as B  # noqa: E402

SIZE = 1024
BG_COLOR = (1.6, 1.68, 1.78, 1)  # se ve como gris azulado muy claro tras el tone mapping
SCREEN_EMISSION = 1.3  # algo menor que en build_robin para que el cian no se lave


def main():
    B.build()
    cam = B.setup_studio()
    sc = bpy.context.scene
    bpy.data.objects["Floor"].hide_render = True

    bpy.data.materials["FaceScreenMat"].node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = SCREEN_EMISSION

    cam.location = (-0.75, -2.9, 1.5)
    cam.rotation_euler = (Vector((0, 0, 1.17)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = 85
    sc.render.resolution_x = sc.render.resolution_y = SIZE
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"

    sc.render.film_transparent = True
    sc.render.filepath = str(B.RENDERS / "robin_avatar.png")
    bpy.ops.render.render(write_still=True)

    sc.render.film_transparent = False
    sc.world.node_tree.nodes["Background"].inputs["Color"].default_value = BG_COLOR
    sc.render.filepath = str(B.RENDERS / "robin_avatar_bg.png")
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
