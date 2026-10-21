"""Construye a Robin (variante B · Chibi) desde una escena vacia.

Medidas en unidades Blender segun concepts/turnaround.svg (Z arriba, frente = -Y,
origen en el suelo entre los pies, izquierda de Robin = +X).

Uso (ver blender/run.sh, flatpak necesita rutas absolutas):
    flatpak run org.blender.Blender --background --python /ruta/blender/build_robin.py -- [--render] [--save]
"""
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

# ---------------------------------------------------------------- parametros
ACCENT = "#3DE0FF"          # acento de ojos/boca/LED; unico punto de cambio
BODY_COLOR = "#F2F3F5"      # blanco/gris claro mate
JOINT_COLOR = "#3A3F47"     # articulaciones y detalles
BEVEL_SEGMENTS = 4          # nivel de bevel general
SUBSURF_LEVEL = 1           # subdivision sobre piezas con bevel (torso, pelvis, pies)
SEG = 16                    # segmentos radiales de capsulas/esferas

HEAD = dict(w=0.60, h=0.48, d=0.46, z=1.36, r=0.20, bevel=0.05)
SCREEN = dict(w=0.50, h=0.34, z=1.37, r=0.15, bulge=0.016, gap=0.003)
EAR = dict(r=0.075, t=0.05, x=0.315)
NECK = dict(r=0.05, z0=1.05, z1=1.13)
TORSO = dict(z0=0.73, z1=1.07, w_top=0.40, w_bot=0.34, d_top=0.26, d_bot=0.24, bevel=0.085)
LED = dict(z=0.97, r=0.014)
BELT = dict(z0=0.695, z1=0.73, w=0.22, d=0.18)
PELVIS = dict(z0=0.58, z1=0.695, w_top=0.27, w_bot=0.22, d_top=0.21, d_bot=0.18, bevel=0.06)
HIP = dict(x=0.088, z=0.57, r=0.05)
THIGH = dict(z0=0.555, z1=0.37, r=0.071)
KNEE = dict(z=0.35, r=0.046)
SHIN = dict(z0=0.33, z1=0.09, r0=0.069, r1=0.062)
FOOT = dict(x=0.095, w=0.16, h=0.11, y_front=-0.15, y_back=0.11, bevel=0.045)
SHOULDER = dict(x=0.222, z=1.00, r=0.062)
ARM_ANGLE = 35.0            # grados desde la vertical (A-pose)
UPPER = dict(L=0.17, r=0.054)
ELBOW_R = 0.041
FORE = dict(L=0.15, r0=0.052, r1=0.046)
JOINT_GAP = 0.026           # hueco entre segmento y esfera de articulacion
HAND = dict(L=0.086, W=0.092, T=0.054, fing_L=0.056, fing_r=0.021, thumb_L=0.045, thumb_r=0.02, curl=12.0)

SCREEN_EMISSION = 2.2       # intensidad de la cara en Blender (en three.js se ajusta aparte)
FACE_TEX = (512, 348)       # textura placeholder de la cara (ratio 1.47:1)

ROOT = Path(__file__).resolve().parent.parent
RENDERS = ROOT / "blender" / "renders"

# puntos de articulacion (mundo) que usa rig_robin.py; se rellenan al construir
JOINTS = {}


# ---------------------------------------------------------------- utilidades
def hex_rgb(h):
    h = h.lstrip("#")
    srgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb]


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def collection(name):
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    return col


def make_obj(name, bm, mat, col):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    obj.data.materials.append(mat)
    col.objects.link(obj)
    return obj


def set_origin(obj, point):
    """Mueve el origen del objeto a 'point' (mundo) sin mover la geometria."""
    point = Vector(point)
    obj.data.transform(Matrix.Translation(-point))
    obj.matrix_world = Matrix.Translation(point) @ obj.matrix_world


def add_bevel(obj, width, segments=BEVEL_SEGMENTS, angle=None, subsurf=0):
    m = obj.modifiers.new("Bevel", "BEVEL")
    m.width = width
    m.segments = segments
    m.limit_method = "ANGLE" if angle else "NONE"
    if angle:
        m.angle_limit = math.radians(angle)
    if subsurf:
        s = obj.modifiers.new("Subsurf", "SUBSURF")
        s.levels = s.render_levels = subsurf


def capsule(name, p0, p1, r0, r1, mat, col, seg=SEG, rings=10):
    """Capsula (opcionalmente conica) cuyo volumen va de p0 a p1, incluidas las tapas."""
    p0, p1 = Vector(p0), Vector(p1)
    d = (p1 - p0).normalized()
    c0, c1 = p0 + d * r0, p1 - d * r1
    L = (c1 - c0).length
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=1.0)
    for v in bm.verts:
        if v.co.z >= -1e-6:
            v.co = Vector((v.co.x * r1, v.co.y * r1, v.co.z * r1 + L))
        else:
            v.co = Vector((v.co.x * r0, v.co.y * r0, v.co.z * r0))
    rot = Vector((0, 0, 1)).rotation_difference(d).to_matrix().to_4x4()
    bmesh.ops.transform(bm, matrix=Matrix.Translation(c0) @ rot, verts=bm.verts)
    obj = make_obj(name, bm, mat, col)
    set_origin(obj, p0)
    return obj


def sphere(name, center, r, mat, col, seg=SEG, rings=8):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=r)
    bmesh.ops.translate(bm, vec=Vector(center), verts=bm.verts)
    obj = make_obj(name, bm, mat, col)
    set_origin(obj, center)
    return obj


def cylinder(name, center, r, depth, axis, mat, col, seg=SEG, bevel=0.0):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r, depth=depth)
    rot = Vector((0, 0, 1)).rotation_difference(Vector(axis)).to_matrix().to_4x4()
    bmesh.ops.transform(bm, matrix=Matrix.Translation(Vector(center)) @ rot, verts=bm.verts)
    obj = make_obj(name, bm, mat, col)
    set_origin(obj, center)
    if bevel:
        add_bevel(obj, bevel, segments=3, angle=40)
    return obj


def tapered_box(name, z0, z1, w_top, w_bot, d_top, d_bot, mat, col, x=0.0, y_top=0.0, y_bot=0.0):
    """Caja con seccion superior/inferior distinta (torso, pelvis)."""
    bm = bmesh.new()
    vs = []
    for z, w, d, yc in ((z0, w_bot, d_bot, y_bot), (z1, w_top, d_top, y_top)):
        for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            vs.append(bm.verts.new((x + sx * w / 2, yc + sy * d / 2, z)))
    b, t = vs[:4], vs[4:]
    bm.faces.new(list(reversed(b)))
    bm.faces.new(t)
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new((b[i], b[j], t[j], t[i]))
    bm.normal_update()
    return make_obj(name, bm, mat, col)


def rounded_rect(w, h, r, n=8):
    """Contorno 2D (x, z) de un rectangulo redondeado, antihorario."""
    pts = []
    corners = ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90),
               (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270))
    for cx, cz, a0 in corners:
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((cx + r * math.cos(a), cz + r * math.sin(a)))
    return pts


# ---------------------------------------------------------------- materiales
def principled(name, color, rough, metal=0.0, emission=None, strength=0.0):
    mat = bpy.data.materials.new(name)
    if mat.node_tree is None:  # Blender < 5: activar nodos
        mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*hex_rgb(color), 1)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if emission:
        bsdf.inputs["Emission Color"].default_value = (*hex_rgb(emission), 1)
        bsdf.inputs["Emission Strength"].default_value = strength
    mat.diffuse_color = (*hex_rgb(color), 1)
    return mat


def face_placeholder():
    """Textura de cara de ejemplo (ojos neutral + boca REST). three.js la reemplaza en runtime."""
    W, H = FACE_TEX
    acc = np.array(hex_rgb(ACCENT))
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    u, v = (xx + 0.5) / W, (yy + 0.5) / H          # v=0 abajo (convencion Blender)
    mask = np.zeros((H, W), np.float32)
    er = 0.16
    for ex in (0.30, 0.70):
        d = ((u - ex) * W / (0.85 * er * H)) ** 2 + ((v - 0.56) / er) ** 2
        mask = np.maximum(mask, np.clip((1 - d) * 12, 0, 1))
    # sonrisa: parabola entre u 0.42 y 0.58
    t = np.clip((u - 0.42) / 0.16, 0, 1)
    curve_v = 0.26 - 0.16 * W / H * 0.32 * 4 * t * (1 - t) * 0.5
    inside = (u > 0.415) & (u < 0.585)
    dist = np.abs(v - curve_v) * H
    mask = np.maximum(mask, np.where(inside, np.clip((0.015 * H - dist) / 2, 0, 1), 0))
    # glow simple: desenfoque por cajas
    glow = mask.copy()
    for _ in range(3):
        glow = (np.roll(glow, 3, 0) + np.roll(glow, -3, 0) + np.roll(glow, 3, 1) + np.roll(glow, -3, 1) + glow) / 5
    val = np.clip(mask + glow * 0.6, 0, 1)
    rgba = np.ones((H, W, 4), np.float32)
    rgba[..., :3] = val[..., None] * acc
    img = bpy.data.images.new("FaceScreenTex", W, H, alpha=False)
    img.pixels.foreach_set(rgba.ravel())
    img.pack()
    return img


def screen_material():
    mat = principled("FaceScreenMat", "#000000", 0.08, emission="#FFFFFF", strength=SCREEN_EMISSION)
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = face_placeholder()
    tex.interpolation = "Linear"
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
    bsdf.inputs["Specular IOR Level"].default_value = 0.6
    return mat


# ---------------------------------------------------------------- piezas
def build_head(col, m):
    pts = rounded_rect(HEAD["w"], HEAD["h"], HEAD["r"])
    bm = bmesh.new()
    front = [bm.verts.new((x, -HEAD["d"] / 2, z + HEAD["z"])) for x, z in pts]
    back = [bm.verts.new((x, HEAD["d"] / 2, z + HEAD["z"])) for x, z in pts]
    bm.faces.new(front)
    bm.faces.new(list(reversed(back)))
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((front[j], front[i], back[i], back[j]))
    bm.normal_update()
    head = make_obj("HeadShell", bm, m["body"], col)
    add_bevel(head, HEAD["bevel"], segments=5, angle=30)
    set_origin(head, (0, 0, NECK["z1"]))

    # pantalla: anillos concentricos del contorno, abombada en Y, UV planar 0-1
    sw, sh = SCREEN["w"], SCREEN["h"]
    outline = rounded_rect(sw, sh, SCREEN["r"], n=10)
    rings = 7
    y0 = -HEAD["d"] / 2 - SCREEN["gap"]
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")

    def pos(x, z):
        bulge = SCREEN["bulge"] * (1 - (2 * x / sw) ** 2) * (1 - 0.5 * (2 * z / sh) ** 2)
        return Vector((x, y0 - bulge, z + SCREEN["z"]))

    center = bm.verts.new(pos(0, 0))
    grid = []
    for k in range(1, rings + 1):
        s = k / rings
        grid.append([bm.verts.new(pos(x * s, z * s)) for x, z in outline])
    no = len(outline)
    faces = []
    for i in range(no):
        j = (i + 1) % no
        faces.append(bm.faces.new((center, grid[0][j], grid[0][i])))
        for k in range(rings - 1):
            a, b = grid[k], grid[k + 1]
            faces.append(bm.faces.new((a[i], a[j], b[j], b[i])))
    for f in bm.faces:
        for loop in f.loops:
            co = loop.vert.co
            loop[uv].uv = ((co.x + sw / 2) / sw, (co.z - SCREEN["z"] + sh / 2) / sh)
    bm.normal_update()
    # que las normales miren al frente (-Y)
    if sum(f.normal.y for f in bm.faces) > 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    screen = make_obj("FaceScreen", bm, m["screen"], col)
    set_origin(screen, (0, y0, SCREEN["z"]))

    for s, side in ((1, "L"), (-1, "R")):
        cylinder(f"Ear{side}", (s * EAR["x"], 0, HEAD["z"]), EAR["r"], EAR["t"], (1, 0, 0), m["joint"], col, seg=24, bevel=0.012)
        cylinder(f"EarCap{side}", (s * (EAR["x"] + EAR["t"] / 2), 0, HEAD["z"]), EAR["r"] * 0.5, 0.012, (1, 0, 0), m["body"], col, seg=20, bevel=0.004)
    # rejilla de altavoz trasera
    for i in range(-2, 3):
        cylinder(f"HeadGrill{i + 2}", (i * 0.035, HEAD["d"] / 2 + 0.001, 1.25), 0.009, 0.006, (0, 1, 0), m["joint"], col, seg=10)


def build_core(col, m):
    neck = cylinder("NeckRing", (0, 0, (NECK["z0"] + NECK["z1"]) / 2), NECK["r"], NECK["z1"] - NECK["z0"], (0, 0, 1), m["joint"], col, seg=20, bevel=0.008)
    set_origin(neck, (0, 0, NECK["z0"]))

    t = TORSO
    torso = tapered_box("Torso", t["z0"], t["z1"], t["w_top"], t["w_bot"], t["d_top"], t["d_bot"], m["body"], col)
    add_bevel(torso, t["bevel"], subsurf=SUBSURF_LEVEL)
    set_origin(torso, (0, 0, t["z0"]))
    # LED de pecho
    zf = (LED["z"] - t["z0"]) / (t["z1"] - t["z0"])
    yfront = -(t["d_bot"] + (t["d_top"] - t["d_bot"]) * zf) / 2
    cylinder("ChestLED", (0, yfront - 0.002, LED["z"]), LED["r"], 0.008, (0, 1, 0), m["accent"], col, seg=16)
    # panel trasero con rejillas
    yb = (t["d_bot"] + (t["d_top"] - t["d_bot"]) * 0.5) / 2
    panel = tapered_box("BackPanel", 0.84, 0.98, 0.16, 0.16, 0.012, 0.012, m["body_light"], col, y_top=yb, y_bot=yb)
    add_bevel(panel, 0.005, segments=2)
    for i, z in enumerate((0.875, 0.91, 0.945)):
        slot = tapered_box(f"BackSlot{i}", z - 0.006, z + 0.006, 0.12, 0.12, 0.008, 0.008, m["joint"], col,
                           y_top=yb + 0.006, y_bot=yb + 0.006)
        add_bevel(slot, 0.004, segments=2)

    b = BELT
    belt = tapered_box("Belt", b["z0"], b["z1"], b["w"], b["w"], b["d"], b["d"], m["joint"], col)
    add_bevel(belt, 0.015, segments=3)
    p = PELVIS
    pelvis = tapered_box("Pelvis", p["z0"], p["z1"], p["w_top"], p["w_bot"], p["d_top"], p["d_bot"], m["body"], col,
                         y_bot=0.01)
    add_bevel(pelvis, p["bevel"], subsurf=SUBSURF_LEVEL)
    set_origin(pelvis, (0, 0, p["z1"]))


def build_arm(col, m, s, side):
    a = math.radians(ARM_ANGLE)
    d = Vector((s * math.sin(a), 0, -math.cos(a)))
    sh = Vector((s * SHOULDER["x"], 0, SHOULDER["z"]))
    el = sh + d * UPPER["L"]
    wr = el + d * FORE["L"]

    JOINTS.update({f"shoulder{side}": sh, f"elbow{side}": el, f"wrist{side}": wr})
    sphere(f"Shoulder{side}", sh, SHOULDER["r"], m["body"], col, rings=10)
    capsule(f"UpperArm{side}", sh, el - d * JOINT_GAP, UPPER["r"], UPPER["r"] * 0.92, m["body"], col)
    sphere(f"Elbow{side}", el, ELBOW_R, m["joint"], col)
    capsule(f"ForeArm{side}", el + d * JOINT_GAP, wr, FORE["r0"], FORE["r1"], m["body"], col)

    # mano: eje local -Z a lo largo del brazo, palma hacia el cuerpo (-X local*s), pulgar al frente (-Y)
    rot = Matrix.Rotation(-s * a, 4, "Y")

    def W(x, y, z):  # local (x medial positivo hacia fuera) -> mundo
        return wr + (rot @ Vector((s * x, y, z)))

    h = HAND
    palm = tapered_box(f"Hand{side}", -h["L"], 0.0, h["W"], h["W"], h["T"], h["T"], m["body"], col)
    # tapered_box crea ancho en X y fondo en Y: girar para que el grosor quede en X
    palm.data.transform(Matrix.Rotation(math.radians(90), 4, "Z"))
    palm.data.transform(Matrix.Translation((0, 0, 0.004)))
    palm.data.transform(rot)
    palm.data.transform(Matrix.Translation(wr))
    add_bevel(palm, 0.018, segments=3)
    set_origin(palm, wr)

    JOINTS[f"hand_end{side}"] = W(0, 0, -h["L"] + 0.012)
    curl = math.radians(h["curl"])
    for i, fy in enumerate((-0.023, 0.023)):
        base = W(0.0, fy, -h["L"] + 0.012)
        dirl = Vector((-math.sin(curl), 0, -math.cos(curl)))   # dobla hacia la palma (medial)
        tip = W(dirl.x * h["fing_L"], fy, -h["L"] + 0.012 + dirl.z * h["fing_L"])
        JOINTS[f"finger{i + 1}{side}"] = (base, tip)
        capsule(f"Finger{i + 1}{side}", base, tip, h["fing_r"], h["fing_r"] * 0.9, m["body"], col, seg=12, rings=8)
    tbase = W(-0.006, -h["W"] / 2 + 0.008, -0.022)
    tdir = Vector((-0.35, -0.55, -0.76)).normalized()
    ttip = W(-0.006 + tdir.x * h["thumb_L"], -h["W"] / 2 + 0.008 + tdir.y * h["thumb_L"], -0.022 + tdir.z * h["thumb_L"])
    JOINTS[f"thumb{side}"] = (tbase, ttip)
    capsule(f"Thumb{side}", tbase, ttip, h["thumb_r"], h["thumb_r"] * 0.9, m["body"], col, seg=12, rings=8)


def build_leg(col, m, s, side):
    x = s * HIP["x"]
    JOINTS.update({f"hip{side}": Vector((x, 0, HIP["z"])), f"knee{side}": Vector((x, 0, KNEE["z"])),
                   f"ankle{side}": Vector((x, 0, FOOT["h"] - 0.02)),
                   f"ball{side}": Vector((s * FOOT["x"], FOOT["y_front"] + 0.07, 0.035)),
                   f"toe{side}": Vector((s * FOOT["x"], FOOT["y_front"], 0.035))})
    sphere(f"HipJoint{side}", (x, 0, HIP["z"]), HIP["r"], m["joint"], col)
    capsule(f"Thigh{side}", (x, 0, THIGH["z0"]), (x, 0, THIGH["z1"]), THIGH["r"], THIGH["r"] * 0.96, m["body"], col)
    sphere(f"Knee{side}", (x, 0, KNEE["z"]), KNEE["r"], m["joint"], col)
    capsule(f"Shin{side}", (x, 0, SHIN["z0"]), (x, 0, SHIN["z1"]), SHIN["r0"], SHIN["r1"], m["body"], col)
    f = FOOT
    fx = s * f["x"]
    foot = tapered_box(f"Foot{side}", 0.0, f["h"], f["w"] * 0.82, f["w"], f["y_back"] - f["y_front"] - 0.09,
                       f["y_back"] - f["y_front"], m["body"], col, x=fx,
                       y_top=(f["y_front"] + f["y_back"]) / 2 + 0.04, y_bot=(f["y_front"] + f["y_back"]) / 2)
    add_bevel(foot, f["bevel"], subsurf=SUBSURF_LEVEL)
    set_origin(foot, (fx, 0, f["h"]))


def finalize(col):
    """Aplica modificadores, suaviza por angulo y cuenta triangulos."""
    dg = bpy.context.evaluated_depsgraph_get()
    tris = 0
    for obj in col.objects:
        if obj.type != "MESH":
            continue
        if obj.modifiers:
            me = bpy.data.meshes.new_from_object(obj.evaluated_get(dg))
            old = obj.data
            obj.modifiers.clear()
            obj.data = me
            me.name = old.name
            bpy.data.meshes.remove(old)
        obj.data.shade_smooth()
        obj.data.set_sharp_from_angle(angle=math.radians(40))
        tris += sum(len(p.vertices) - 2 for p in obj.data.polygons)
    return tris


def build():
    clear_scene()
    col = collection("Robin")
    m = {
        "body": principled("BodyMat", BODY_COLOR, 0.55),
        "body_light": principled("BodyDetailMat", "#D9DDE3", 0.6),
        "joint": principled("JointMat", JOINT_COLOR, 0.42, metal=0.15),
        "accent": principled("AccentMat", ACCENT, 0.3, emission=ACCENT, strength=3.0),
        "screen": screen_material(),
    }
    build_head(col, m)
    build_core(col, m)
    for s, side in ((1, "L"), (-1, "R")):
        build_arm(col, m, s, side)
        build_leg(col, m, s, side)
    tris = finalize(col)
    print(f"[robin] objetos={len(col.objects)} triangulos={tris}")
    return col, tris


# ---------------------------------------------------------------- render de previsualizacion
def setup_studio():
    sc = bpy.context.scene
    studio = collection("Studio")
    bpy.ops.mesh.primitive_plane_add(size=20)
    floor = bpy.context.active_object
    floor.name = "Floor"
    floor.data.materials.append(principled("FloorMat", "#D5D9DE", 0.8))
    for c in floor.users_collection:
        c.objects.unlink(floor)
    studio.objects.link(floor)

    def area(name, loc, energy, size, color=(1, 1, 1)):
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy, ld.size, ld.color = energy, size, color
        ob = bpy.data.objects.new(name, ld)
        ob.location = loc
        direction = Vector((0, 0, 1.0)) - Vector(loc)
        ob.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
        studio.objects.link(ob)

    area("Key", (-2.0, -2.6, 2.6), 300, 2.0)
    area("Fill", (2.4, -2.0, 1.6), 120, 2.5, (0.92, 0.96, 1.0))
    area("Rim", (0.8, 2.6, 2.4), 240, 1.5)
    world = bpy.data.worlds.new("World")
    sc.world = world
    if world.node_tree is None:
        world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.80, 0.83, 0.87, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.4

    cam_d = bpy.data.cameras.new("Cam")
    cam = bpy.data.objects.new("Cam", cam_d)
    studio.objects.link(cam)
    sc.camera = cam
    for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            sc.render.engine = eng
            break
        except TypeError:
            continue
    sc.view_settings.view_transform = "Khronos PBR Neutral"
    sc.view_settings.exposure = 0.0
    sc.render.film_transparent = False
    return cam


def render_views(cam):
    sc = bpy.context.scene
    RENDERS.mkdir(parents=True, exist_ok=True)
    views = [
        # nombre, posicion, objetivo, lente, resolucion
        ("full_front", (0, -3.7, 0.85), (0, 0, 0.80), 50, (900, 1200)),
        ("full_34", (-2.3, -2.9, 1.0), (0, 0, 0.80), 50, (900, 1200)),
        ("medium_front", (0, -2.4, 1.15), (0, 0, 1.08), 50, (1200, 900)),
        ("medium_34", (-1.6, -2.1, 1.25), (0, 0, 1.08), 50, (1200, 900)),
    ]
    for name, loc, target, lens, res in views:
        cam.location = loc
        cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        cam.data.lens = lens
        sc.render.resolution_x, sc.render.resolution_y = res
        sc.render.filepath = str(RENDERS / f"{name}.png")
        bpy.ops.render.render(write_still=True)
        print(f"[robin] render {name}")


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    build()
    if "--render" in argv:
        render_views(setup_studio())
    if "--save" in argv:
        bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "blender" / "robin.blend"))
