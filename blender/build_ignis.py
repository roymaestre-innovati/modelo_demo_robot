"""Construye a Ignis (dragon de fuego joven) desde una escena vacia.

Medidas en unidades Blender segun concepts/ignis/turnaround.svg (Z arriba, frente = -Y,
izquierda de Ignis = +X, origen en el suelo entre las cuatro patas).

La malla principal (IgnisBody) se arma con los mismos volumenes del turnaround (cascos convexos
de elipsoides encadenados), se une con un remesh por voxeles, se le recorta la boca con un
booleano y se reduce con Decimate simetrico para el aspecto low-poly facetado.

Uso: blender/run.sh build_ignis.py [-- --render] [--save]
"""
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

# ---------------------------------------------------------------- parametros
ACCENT = "#FF5733"          # acento del personaje (runtime.accent de la ficha)
COLORS = dict(
    body="#D93829", belly="#FCA311", wing="#7A1426", claw="#5A0F1A", mouth="#4A0E14",
    flame="#FFB020", flame_emit="#FF7A1A", iris="#B5651D", pupil="#1E0B06",
)
FLAME_EMISSION = 0.8
VOXEL = 0.008               # resolucion del remesh que une los volumenes
BODY_TRIS = 6000            # objetivo de triangulos de IgnisBody tras Decimate
HEAD_PASS_TRIS = 7000       # densidad de la primera pasada, la que conserva la cabeza
LIP_SMOOTH = 6              # pasadas de suavizado del borde de los labios
SMOOTH = (0.5, 4)           # factor e iteraciones del suavizado antes de reducir

HEIGHT = 1.50
EYE_R = 0.066
JAW_MAX_DEG = 24.0          # jawOpen = 1 (la forma A abre 0.8 * 24 = 19 grados)

TORSO = [((0, -0.40, 0.56), (0.13, 0.10, 0.13)),
         ((0, -0.26, 0.52), (0.165, 0.17, 0.18)),
         ((0, -0.02, 0.48), (0.19, 0.20, 0.20)),
         ((0, 0.20, 0.46), (0.21, 0.18, 0.20)),
         ((0, 0.34, 0.45), (0.15, 0.12, 0.15))]
NECK = [((0, -0.31, 0.64), 0.12), ((0, -0.355, 0.77), 0.095),
        ((0, -0.365, 0.89), 0.085), ((0, -0.38, 1.00), 0.09)]
TAIL = [((0, 0.36, 0.46), 0.12), ((0, 0.52, 0.36), 0.10), ((0, 0.67, 0.21), 0.085),
        ((0, 0.83, 0.075), 0.07), ((0, 0.98, 0.08), 0.06), ((0, 1.09, 0.20), 0.05),
        ((0, 1.135, 0.33), 0.04), ((0, 1.145, 0.42), 0.03)]
CRANIUM = ((0, -0.42, 1.16), (0.16, 0.16, 0.15))
SNOUT = ((0, -0.585, 1.11), (0.105, 0.12, 0.07))
MUZZLE = ((0, -0.50, 1.14), (0.13, 0.10, 0.10))     # puente entre craneo y hocico
JAW = ((0, -0.54, 1.03), (0.098, 0.13, 0.05))
JAW_BACK = ((0, -0.45, 1.03), (0.12, 0.09, 0.06))
JAW_PIVOT = (0, -0.42, 1.06)
CHIN = ((0, -0.50, 0.975), (0.075, 0.15, 0.035))     # zona naranja bajo la mandibula
EYE = dict(c=(0.105, -0.535, 1.195), n=(0.50, -0.82, 0.28))     # ojo izquierdo (+X)
NOSTRIL = dict(c=(0.035, -0.695, 1.135), r=0.014)
HORN = [((0.085, -0.37, 1.25), 0.046), ((0.12, -0.30, 1.32), 0.038), ((0.15, -0.22, 1.36), 0.030),
        ((0.165, -0.165, 1.42), 0.020), ((0.165, -0.165, 1.50), 0.007)]

# boca: hendidura (z del labio en funcion de y) y cavidad interior
MOUTH_CORNER_Y = -0.445
MOUTH_TIP_Y = -0.76
MOUTH_GAP = 0.003           # media apertura de la hendidura en reposo
MOUTH_CAVITY = ((0, -0.545, 1.050), (0.082, 0.105, 0.034))   # casi todo el hocico: labios de ~2 cm

FRONT_LEG = [((0.13, -0.22, 0.46), 0.09), ((0.14, -0.19, 0.27), 0.065), ((0.14, -0.22, 0.09), 0.055)]
FRONT_PAD = ((0.14, -0.26, 0.04), (0.07, 0.09, 0.04))
BACK_LEG = [((0.15, 0.22, 0.47), 0.12), ((0.16, 0.13, 0.26), 0.08), ((0.16, 0.24, 0.10), 0.055)]
BACK_PAD = ((0.16, 0.17, 0.04), (0.075, 0.11, 0.04))
CLAW_LEN = 0.05

WING_SHOULDER = (0.10, -0.14, 0.64)
WING_ROOT = (0.12, 0.22, 0.60)
WING_LEN = dict(hum=0.16, fore=0.18, f1=0.24, f2=0.22, f3=0.18)
WING_DIRS = dict(hum=(0.2, 0.25, 1.0), fore=(0.08, 0.9, 0.45),          # pose plegada de reposo
                 f1=(0.05, 0.9, -0.1), f2=(0.06, 0.6, -0.75), f3=(0.04, 0.15, -1.0))

FLAME_BASE = (0, 1.14, 0.40)
FLAME_H = 0.30

PLATE_LEN = 0.075           # largo de cada placa ventral
GROOVE = (0.010, 0.005)     # ancho y profundidad del surco entre placas

ROOT = Path(__file__).resolve().parent.parent
RENDERS = ROOT / "blender" / "renders" / "ignis"


# ---------------------------------------------------------------- utilidades
def hex_rgb(h):
    h = h.lstrip("#")
    srgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb]


def srgb(h):
    h = h.lstrip("#")
    return [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]


def mirror(p):
    return (-p[0], p[1], p[2])


def radii(r):
    return (r, r, r) if isinstance(r, (int, float)) else tuple(r)


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def collection(name):
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    return col


def make_obj(name, bm, mats, col):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    for m in mats if isinstance(mats, (list, tuple)) else [mats]:
        obj.data.materials.append(m)
    col.objects.link(obj)
    return obj


def set_origin(obj, point):
    """Mueve el origen del objeto a 'point' (mundo) sin mover la geometria."""
    point = Vector(point)
    obj.data.transform(Matrix.Translation(-point))
    obj.matrix_world = Matrix.Translation(point) @ obj.matrix_world


def ell_points(c, r, n=12, m=7):
    rx, ry, rz = radii(r)
    pts = [(c[0], c[1], c[2] + rz), (c[0], c[1], c[2] - rz)]
    for j in range(1, m):
        phi = math.pi * j / m - math.pi / 2
        for i in range(n):
            th = 2 * math.pi * (i + 0.5 * (j % 2)) / n
            pts.append((c[0] + rx * math.cos(phi) * math.cos(th),
                        c[1] + ry * math.cos(phi) * math.sin(th),
                        c[2] + rz * math.sin(phi)))
    return pts


def add_hull(bm, pts):
    vs = [bm.verts.new(p) for p in pts]
    res = bmesh.ops.convex_hull(bm, input=vs)
    junk = list({g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)})
    bmesh.ops.delete(bm, geom=junk, context="VERTS")


def add_chain(bm, nodes, n=14, m=8):
    for a, b in zip(nodes, nodes[1:]):
        add_hull(bm, ell_points(a[0], a[1], n, m) + ell_points(b[0], b[1], n, m))


def apply_modifiers(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(obj.evaluated_get(dg))
    old = obj.data
    obj.modifiers.clear()
    obj.data = me
    me.name = old.name
    bpy.data.meshes.remove(old)


def verts_np(me):
    co = np.empty(len(me.vertices) * 3, np.float64)
    me.vertices.foreach_get("co", co)
    return co.reshape(-1, 3)


def face_centers(me):
    c = np.empty(len(me.polygons) * 3, np.float64)
    me.polygons.foreach_get("center", c)
    return c.reshape(-1, 3)


def norm(v):
    v = Vector(v)
    return v.normalized()


# ---------------------------------------------------------------- materiales
def principled(name, color, rough, metal=0.0, emission=None, strength=0.0):
    mat = bpy.data.materials.new(name)
    if mat.node_tree is None:
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


def eye_placeholder(w=512, h=256):
    """Ojos de ejemplo en neutral (izquierdo u 0-0.5, derecho u 0.5-1). three.js la reemplaza."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    u, v = (xx + 0.5) / w, (yy + 0.5) / h          # v = 0 abajo (convencion Blender)
    rgb = np.empty((h, w, 3), np.float32)
    rgb[:] = srgb(COLORS["body"])
    for half, look in ((0, -1), (1, 1)):        # el iris mira hacia el centro de la cara
        cu = 0.25 + 0.5 * half
        x = (u - cu) / 0.25                     # -1..1 dentro del parche
        y = (v - 0.5) / 0.5
        r2 = x * x + y * y
        sclera = r2 < 0.93 ** 2
        ix, iy = x - look * 0.12, y + 0.04
        iris = ix * ix + iy * iy < 0.55 ** 2
        pupil = ix * ix + iy * iy < 0.29 ** 2
        hx, hy = ix + look * 0.16, iy - 0.22
        hl = hx * hx + hy * hy < 0.11 ** 2
        lid = np.hypot(x, y + 0.9) > 1.55          # parpado en arco, mas alto en el centro
        rgb[sclera] = (1, 1, 1)
        rgb[sclera & iris] = srgb(COLORS["iris"])
        rgb[sclera & pupil] = srgb(COLORS["pupil"])
        rgb[sclera & hl] = (1, 1, 1)
        rgb[lid & (r2 < 1.0)] = srgb(COLORS["body"])
        ring = (np.abs(np.sqrt(r2) - 0.93) < 0.035) & ~lid
        rgb[ring] = srgb("#3B0A10")
        lidline = (np.abs(np.hypot(x, y + 0.9) - 1.55) < 0.035) & (r2 < 0.93 ** 2)
        rgb[lidline] = srgb("#3B0A10")
    rgba = np.ones((h, w, 4), np.float32)
    rgba[..., :3] = rgb
    img = bpy.data.images.new("FaceScreenTex", w, h, alpha=False)
    img.pixels.foreach_set(rgba.ravel())
    img.pack()
    return img


def face_material():
    mat = principled("FaceScreenMat", "#FFFFFF", 0.5)
    nt = mat.node_tree
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = eye_placeholder()
    nt.links.new(tex.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"])
    return mat


def materials():
    m = dict(
        body=principled("BodyMat", COLORS["body"], 0.55),
        belly=principled("BellyHornsMat", COLORS["belly"], 0.6),
        wing=principled("WingMembraneMat", COLORS["wing"], 0.7),
        claw=principled("ClawMat", COLORS["claw"], 0.5),
        mouth=principled("MouthMat", COLORS["mouth"], 0.8),
        flame=principled("TailFlameMat", COLORS["flame"], 0.5, emission=COLORS["flame_emit"], strength=FLAME_EMISSION),
        face=face_material(),
    )
    for k, mat in m.items():                    # solo la membrana es de doble cara en el glTF
        mat.use_backface_culling = k != "wing"
    return m


# ---------------------------------------------------------------- volumenes del cuerpo
def belly_nodes():
    """Cadena del vientre: igual que en el turnaround (adelantada/bajada respecto al cuerpo)."""
    out = []
    for c, r in NECK[:3]:
        out.append(((c[0], c[1] - 0.95 * r, c[2]), (0.62 * r, r, r)))
    for (c, r), d in zip(TORSO[:4], [(0, -0.9, -0.45), (0, -0.62, -0.78), (0, -0.05, -1), (0, 0.1, -1)]):
        rx, ry, rz = r
        out.append(((c[0], c[1] + d[1] * ry * 1.3, c[2] + d[2] * rz * 1.3), (0.62 * rx, ry, rz)))
    out.sort(key=lambda t: -t[0][2])
    return out


def interp_nodes(nodes, steps=10):
    cs, rs = [], []
    for a, b in zip(nodes, nodes[1:]):
        for k in range(steps):
            t = k / steps
            cs.append((1 - t) * np.array(a[0]) + t * np.array(b[0]))
            rs.append((1 - t) * np.array(radii(a[1])) + t * np.array(radii(b[1])))
    cs.append(np.array(nodes[-1][0], float))
    rs.append(np.array(radii(nodes[-1][1]), float))
    return np.array(cs), np.array(rs)


def spike_hulls(bm, nodes, n_per, h0, h1):
    pts = []
    for a, b in zip(nodes, nodes[1:]):
        for k in range(n_per):
            t = (k + 0.5) / n_per
            c = Vector(a[0]).lerp(Vector(b[0]), t)
            r = radii(a[1])[2] * (1 - t) + radii(b[1])[2] * t
            pts.append((c, r, (Vector(b[0]) - Vector(a[0])).normalized()))
    N = len(pts)
    for i, (c, r, tan) in enumerate(pts):
        up = Vector((0, 0, 1))
        up = (up - tan * up.dot(tan)).normalized()
        h = h0 + (h1 - h0) * i / max(1, N - 1)
        base = c + up * r * 0.8
        tri = [base - tan * h * 0.55, base + tan * h * 0.55, base + up * h + tan * h * 0.45]
        add_hull(bm, [p + Vector((dx, 0, 0)) for p in tri for dx in (-0.013, 0.013)])


def mouth_z(y):
    """Altura del labio en funcion de y: casi recta en el hocico, sube en la comisura (sonrisa)."""
    t = max(0.0, (y + 0.53) / (0.53 + MOUTH_CORNER_Y))
    return 1.050 + 0.004 * (y + 0.70) / 0.25 + 0.034 * t * t


def body_cutters(col, m):
    """Hendidura de la boca (lamina curva) y cavidad interior."""
    bm = bmesh.new()
    ys = np.linspace(MOUTH_TIP_Y, MOUTH_CORNER_Y, 24)
    rings = []
    for y in ys:
        z = mouth_z(y)
        taper = 1.0 if y < -0.50 else max(0.25, (MOUTH_CORNER_Y - y) / (MOUTH_CORNER_Y + 0.50))
        g = MOUTH_GAP * taper
        rings.append([bm.verts.new((x, y, z + dz)) for x, dz in ((-0.25, -g), (0.25, -g), (0.25, g), (-0.25, g))])
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(4):
            bm.faces.new((r0[i], r0[(i + 1) % 4], r1[(i + 1) % 4], r1[i]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    slit = make_obj("CutSlit", bm, m["mouth"], col)
    bm = bmesh.new()
    add_hull(bm, ell_points(MOUTH_CAVITY[0], MOUTH_CAVITY[1], 16, 8))
    cav = make_obj("CutCavity", bm, m["mouth"], col)
    return slit, cav


def build_body(col, m):
    bm = bmesh.new()
    add_chain(bm, TORSO)
    add_chain(bm, NECK)
    add_chain(bm, TAIL)
    add_hull(bm, ell_points(*TORSO[1]) + ell_points(*NECK[0]))
    for c, r in (CRANIUM, SNOUT, MUZZLE, JAW, JAW_BACK):
        add_hull(bm, ell_points(c, r, 16, 9))
    for side in (1, -1):
        mm = (lambda p: p) if side > 0 else mirror
        fl = [(mm(c), r) for c, r in FRONT_LEG]
        bl = [(mm(c), r) for c, r in BACK_LEG]
        add_chain(bm, fl, 12, 7)
        add_hull(bm, ell_points(*fl[-1], 12, 7) + ell_points(mm(FRONT_PAD[0]), FRONT_PAD[1], 12, 7))
        add_chain(bm, bl, 12, 7)
        add_hull(bm, ell_points(*bl[-1], 12, 7) + ell_points(mm(BACK_PAD[0]), BACK_PAD[1], 12, 7))
        # aletas de las mejillas
        for (y, z, h) in ((-0.31, 1.13, 0.07), (-0.30, 1.21, 0.06), (-0.33, 1.06, 0.05)):
            base = Vector((side * 0.12, y, z))
            tip = Vector((side * 0.17, y + h * 1.1, z + h * 0.25))
            add_hull(bm, [base + Vector((0, dy, dz)) for dy in (-0.03, 0.03) for dz in (-0.02, 0.02)] + [tip])
    spike_hulls(bm, NECK[1:], 2, 0.045, 0.05)
    spike_hulls(bm, TORSO[1:], 2, 0.05, 0.05)
    spike_hulls(bm, TAIL[:6], 2, 0.05, 0.025)
    body = make_obj("IgnisBody", bm, [m["body"], m["belly"], m["mouth"]], col)

    # 1) union de volumenes + suavizado
    r = body.modifiers.new("Remesh", "REMESH")
    r.mode = "VOXEL"
    r.voxel_size = VOXEL
    r.adaptivity = 0.0
    s = body.modifiers.new("Smooth", "SMOOTH")
    s.factor, s.iterations = SMOOTH
    apply_modifiers(body)

    # 2) surcos de las placas ventrales y fosas nasales, sobre la malla densa
    me = body.data
    co = verts_np(me)
    nr = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("normal", nr)
    nr = nr.reshape(-1, 3)
    cs, rs = interp_nodes(belly_nodes(), 12)
    seg = np.r_[0, np.cumsum(np.linalg.norm(np.diff(cs, axis=0), axis=1))]
    d = (((co[:, None, :] - cs[None]) / rs[None]) ** 2).sum(-1)
    inside = d.min(1) < 1.0
    s_along = seg[d.argmin(1)]
    groove = inside & ((s_along % PLATE_LEN) < GROOVE[0]) & (s_along > 0.03)
    co[groove] -= nr[groove] * GROOVE[1]
    for side in (1, -1):
        nc = np.array(NOSTRIL["c"]) * (side, 1, 1)
        dn = np.linalg.norm(co - nc, axis=1)
        k = dn < NOSTRIL["r"]
        co[k] -= nr[k] * 0.006 * (1 - dn[k] / NOSTRIL["r"])[:, None]
    me.vertices.foreach_set("co", co.ravel())
    me.update()

    # 3) boca y 4) reduccion low-poly simetrica
    slit, cav = body_cutters(col, m)
    for cutter in (slit, cav):
        b = body.modifiers.new(cutter.name, "BOOLEAN")
        b.operation = "DIFFERENCE"
        b.object = cutter
        b.solver = "EXACT"
        b.material_mode = "TRANSFER"
    apply_modifiers(body)
    for cutter in (slit, cav):
        bpy.data.objects.remove(cutter)
    # interior de la boca: se marca sobre la malla densa, asi el borde con el labio queda limpio
    me = body.data
    while len(me.materials) > 3:
        me.materials.pop()
    fc = face_centers(me)
    cc, cr = np.array(MOUTH_CAVITY[0]), np.array(MOUTH_CAVITY[1]) * 1.02
    me.polygons.foreach_set("material_index", np.where((((fc - cc) / cr) ** 2).sum(1) < 1.0, 2, 0).astype(np.int32))
    # Reduccion en dos pasadas: 1) todo a HEAD_PASS_TRIS (densidad uniforme, labios protegidos);
    # 2) solo el cuerpo hasta BODY_TRIS, con la cabeza protegida: la cabeza conserva la densidad de 1).
    def keep_group(weights):
        for g in list(body.vertex_groups):
            body.vertex_groups.remove(g)
        vg = body.vertex_groups.new(name="Keep")
        for i in np.nonzero(weights)[0]:
            vg.add([int(i)], float(weights[i]), "REPLACE")

    def decimate(ratio, factor):
        dec = body.modifiers.new("Decimate", "DECIMATE")
        dec.vertex_group = "Keep"
        dec.invert_vertex_group = True
        dec.vertex_group_factor = factor
        dec.decimate_type = "COLLAPSE"
        dec.ratio = min(1.0, ratio)
        dec.use_symmetry = True
        dec.symmetry_axis = "X"
        dec.use_collapse_triangulate = True
        apply_modifiers(body)

    def lips_and_head():
        co = verts_np(body.data)
        lipd = np.abs(co[:, 2] - np.array([mouth_z(y) for y in co[:, 1]]))
        lips = np.where((co[:, 1] < MOUTH_CORNER_Y + 0.04) & (co[:, 2] > 0.96) & (co[:, 2] < 1.12),
                        np.clip(1.5 - lipd / 0.015, 0, 1), 0.0)
        head = np.clip((-0.30 - co[:, 1]) / 0.04, 0, 1) * np.clip((co[:, 2] - 0.93) / 0.04, 0, 1)
        return lips, head

    ntri = lambda: sum(len(p.vertices) - 2 for p in body.data.polygons)  # noqa: E731
    lips, _ = lips_and_head()
    keep_group(lips)
    decimate(HEAD_PASS_TRIS / ntri(), 8.0)
    lips, head = lips_and_head()
    keep_group(np.maximum(lips, head))
    decimate(BODY_TRIS / ntri(), 8.0)
    apply_modifiers(body)
    body.vertex_groups.clear()
    # limpiar astillas que deja el booleano junto a la hendidura (con flat shading brillan como dientes)
    bm = bmesh.new()
    bm.from_mesh(body.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0025)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=0.002)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    # redondear el borde de los labios: sin esto el contorno queda dentado y parece una fila de dientes
    lip_verts = [v for v in bm.verts if v.co.y < MOUTH_CORNER_Y + 0.03 and 0.98 < v.co.z < 1.10
                 and abs(v.co.z - mouth_z(min(v.co.y, MOUTH_CORNER_Y))) < 0.02]
    for _ in range(LIP_SMOOTH):
        bmesh.ops.smooth_vert(bm, verts=lip_verts, factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    bm.to_mesh(body.data)
    bm.free()
    body.data.validate(clean_customdata=False)

    # 5) materiales por region: vientre, interior de la boca y fosas nasales
    me = body.data
    while len(me.materials) > 3:
        me.materials.pop()
    fc = face_centers(me)
    d = (((fc[:, None, :] - cs[None]) / rs[None]) ** 2).sum(-1)
    mat_idx = np.where(d.min(1) < 1.0, 1, 0)
    # barbilla del color del vientre, como en la referencia
    mat_idx[(((fc - np.array(CHIN[0])) / np.array(CHIN[1])) ** 2).sum(1) < 1.0] = 1
    # el vientre no invade las patas
    for side in (1, -1):
        for chain_ in (FRONT_LEG, BACK_LEG):
            for (a, ra), (b, rb) in zip(chain_, chain_[1:]):
                a, b = np.array(a) * (side, 1, 1), np.array(b) * (side, 1, 1)
                ab = b - a
                t = np.clip(((fc - a) @ ab) / (ab @ ab), 0, 1)
                dist = np.linalg.norm(fc - (a + t[:, None] * ab), axis=1)
                mat_idx[dist < (ra * (1 - t) + rb * t) * 1.1] = 0
    mat_idx[(fc[:, 2] < 0.24) & (np.abs(fc[:, 0]) > 0.06)] = 0     # ni la cara interna de las patas
    old = np.empty(len(me.polygons), np.int32)
    me.polygons.foreach_get("material_index", old)
    mat_idx[old == 2] = 2                               # interior marcado antes de reducir
    head_f = (fc[:, 1] < -0.27) & (fc[:, 2] > 0.92)
    print(f"[ignis] triangulos de la cabeza: {int(head_f.sum())}")
    for side in (1, -1):
        nc = np.array(NOSTRIL["c"]) * (side, 1, 1)
        mat_idx[np.linalg.norm(fc - nc, axis=1) < NOSTRIL["r"] * 1.3] = 2
    me.polygons.foreach_set("material_index", mat_idx.astype(np.int32))
    me.shade_flat()
    me.update()
    return body


# ---------------------------------------------------------------- piezas
def tube(bm, pts, rads, sides=6, tip=True):
    """Tubo poligonal por una polilinea (cuernos, varillas del ala)."""
    rings = []
    for i, (p, r) in enumerate(zip(pts, rads)):
        p = Vector(p)
        t = (Vector(pts[min(i + 1, len(pts) - 1)]) - Vector(pts[max(i - 1, 0)])).normalized()
        a = t.orthogonal().normalized()
        b = t.cross(a)
        rings.append([bm.verts.new(p + (a * math.cos(2 * math.pi * k / sides) + b * math.sin(2 * math.pi * k / sides)) * r)
                      for k in range(sides)])
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(sides):
            bm.faces.new((r0[k], r0[(k + 1) % sides], r1[(k + 1) % sides], r1[k]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)


def catmull(nodes, steps=3):
    P = [Vector(c) for c, _ in nodes]
    R = [r for _, r in nodes]
    out_p, out_r = [], []
    for i in range(len(P) - 1):
        p0, p1, p2, p3 = P[max(i - 1, 0)], P[i], P[i + 1], P[min(i + 2, len(P) - 1)]
        for k in range(steps):
            t = k / steps
            out_p.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                                + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
            out_r.append(R[i] * (1 - t) + R[i + 1] * t)
    out_p.append(P[-1])
    out_r.append(R[-1])
    return out_p, out_r


def build_horns(col, m):
    objs = []
    for side, sfx in ((1, "L"), (-1, "R")):
        nodes = [((side * c[0], c[1], c[2]), r) for c, r in HORN]
        bm = bmesh.new()
        p, r = catmull(nodes, 3)
        tube(bm, p, r, 6)
        o = make_obj(f"Horn_{sfx}", bm, m["belly"], col)
        o.data.shade_flat()
        objs.append(o)
    return objs


def build_claws(col, m):
    out = {}
    for side, sfx in ((1, "L"), (-1, "R")):
        for name, pad in (("Front", FRONT_PAD), ("Back", BACK_PAD)):
            c = Vector(pad[0]) * Vector((side, 1, 1))
            r = pad[1]
            bm = bmesh.new()
            for dx in (-0.038, 0.0, 0.038):
                base = (c.x + dx, c.y - (r[1] - 0.02), 0.025)
                tip = (c.x + dx * 1.2, c.y - (r[1] + CLAW_LEN - 0.02), 0.004)
                add_hull(bm, ell_points(base, (0.018, 0.013, 0.021), 6, 3) + [tip])
            o = make_obj(f"{name}Claws_{sfx}", bm, m["claw"], col)
            o.data.shade_flat()
            out[f"{name}{sfx}"] = o
    return out


def wing_joints(side=1):
    L = WING_LEN
    d = {k: Vector(v).normalized() for k, v in WING_DIRS.items()}
    S = Vector(WING_SHOULDER)
    E = S + d["hum"] * L["hum"]
    W = E + d["fore"] * L["fore"]
    J = dict(S=S, E=E, W=W, F1=W + d["f1"] * L["f1"], F2=W + d["f2"] * L["f2"], F3=W + d["f3"] * L["f3"],
             B=Vector(WING_ROOT))
    if side < 0:
        J = {k: Vector(mirror(p)) for k, p in J.items()}
    return J


def build_wings(col, m):
    out = []
    for side, sfx in ((1, "L"), (-1, "R")):
        J = wing_joints(side)
        W = J["W"]

        def scallop(a, b, k=0.12):
            mid = (a + b) / 2
            return mid + (W - mid) * k
        panels = [[J["S"], J["E"], W, J["F1"]],
                  [W, J["F1"], scallop(J["F1"], J["F2"]), J["F2"]],
                  [W, J["F2"], scallop(J["F2"], J["F3"]), J["F3"]],
                  [W, J["F3"], scallop(J["F3"], J["B"], 0.18), J["B"], J["S"]]]
        bm = bmesh.new()
        cache = {}

        def vert(p):
            key = tuple(round(x, 5) for x in p)
            if key not in cache:
                cache[key] = bm.verts.new(p)
            return cache[key]
        for poly in panels:
            ctr = sum(poly, Vector()) / len(poly)
            cv = vert(ctr)
            for a, b in zip(poly, poly[1:] + poly[:1]):
                bm.faces.new((cv, vert(a), vert(b)))
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=1, use_grid_fill=True)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
        # normales hacia fuera/arriba (da igual en doble cara, pero que sean coherentes)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        mem = make_obj(f"WingMembrane_{sfx}", bm, m["wing"], col)
        mem.data.shade_flat()
        bm = bmesh.new()
        for a, b, r0, r1 in (("S", "E", 0.026, 0.02), ("E", "W", 0.02, 0.016),
                             ("W", "F1", 0.014, 0.005), ("W", "F2", 0.012, 0.005), ("W", "F3", 0.012, 0.005)):
            tube(bm, [J[a], J[b]], [r0, r1], 5)
        arm = make_obj(f"WingArm_{sfx}", bm, m["claw"], col)
        arm.data.shade_flat()
        out += [mem, arm]
    return out


def build_flame(col, m):
    """Llama low-poly: anillos que se estrechan, se tuercen y ondulan, con dos lenguas laterales."""
    bm = bmesh.new()
    base = Vector(FLAME_BASE)
    prof = [(0.00, 0.050), (0.12, 0.095), (0.30, 0.100), (0.50, 0.075), (0.70, 0.045), (0.86, 0.020)]
    sides = 5
    rings = []
    for i, (h, r) in enumerate(prof):
        c = base + Vector((0, 0.03 * math.sin(i * 1.3), h * FLAME_H))
        tw = i * 0.45
        rings.append([bm.verts.new(c + Vector((math.cos(tw + 2 * math.pi * k / sides) * r * 0.9,
                                               math.sin(tw + 2 * math.pi * k / sides) * r, 0)))
                      for k in range(sides)])
    tip = bm.verts.new(base + Vector((0, -0.02, FLAME_H)))
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(sides):
            bm.faces.new((r0[k], r0[(k + 1) % sides], r1[(k + 1) % sides], r1[k]))
    for k in range(sides):
        bm.faces.new((rings[-1][k], rings[-1][(k + 1) % sides], tip))
    bm.faces.new(list(reversed(rings[0])))
    for sx, h, yy in ((1, 0.55, 0.05), (-1, 0.45, -0.04)):
        c = base + Vector((sx * 0.03, yy, 0.25 * FLAME_H))
        t = base + Vector((sx * 0.09, yy * 1.6, h * FLAME_H))
        add_hull(bm, ell_points(c, (0.035, 0.035, 0.05), 5, 3) + [t])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = make_obj("TailFlame", bm, m["flame"], col)
    o.data.shade_flat()
    set_origin(o, FLAME_BASE)                   # la demo escala la llama desde su base
    return o


def build_tongue(col, m):
    bm = bmesh.new()
    add_hull(bm, ell_points((0, -0.56, 1.038), (0.046, 0.08, 0.013), 10, 5))
    o = make_obj("Tongue", bm, m["body"], col)
    o.data.shade_flat()
    return o


def build_face(col, m, body):
    """FaceScreen: dos parches que siguen la superficie del craneo en las cuencas de los ojos."""
    dg = bpy.context.evaluated_depsgraph_get()
    bvh = BVHTree.FromObject(body, dg)
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    R = EYE_R * 1.05
    rings, segs = 6, 24
    for side in (1, -1):
        c = Vector(EYE["c"]) * Vector((side, 1, 1))
        n = Vector(EYE["n"]) * Vector((side, 1, 1))
        n.normalize()
        up = Vector((0, 0, 1))
        v_ax = (up - n * up.dot(n)).normalized()
        u_ax = v_ax.cross(n).normalized()
        if u_ax.x < 0:
            u_ax = -u_ax                        # +u hacia +X: en vista frontal, izquierda a derecha
        u0 = 0.0 if side > 0 else 0.5

        def surf(x, y):
            p = c + u_ax * x + v_ax * y
            hit, hn, _, _ = bvh.ray_cast(p + n * 0.1, -n, 0.3)
            if hit is None:
                hit = p
            bulge = 0.0035 + 0.006 * max(0.0, 1 - (x * x + y * y) / (R * R))
            return hit + n * bulge
        center = bm.verts.new(surf(0, 0))
        grid = []
        for i in range(1, rings + 1):
            rr = R * i / rings
            grid.append([bm.verts.new(surf(rr * math.cos(2 * math.pi * k / segs), rr * math.sin(2 * math.pi * k / segs)))
                         for k in range(segs)])

        def uvof(x, y):
            return (u0 + 0.25 + 0.25 * x / R, 0.5 + 0.5 * y / R)
        coords = {center: (0.0, 0.0)}
        for i, ring in enumerate(grid):
            rr = R * (i + 1) / rings
            for k, vtx in enumerate(ring):
                coords[vtx] = (rr * math.cos(2 * math.pi * k / segs), rr * math.sin(2 * math.pi * k / segs))
        faces = []
        for k in range(segs):
            faces.append((center, grid[0][k], grid[0][(k + 1) % segs]))
        for r0, r1 in zip(grid, grid[1:]):
            for k in range(segs):
                faces.append((r0[k], r1[k], r1[(k + 1) % segs], r0[(k + 1) % segs]))
        for fv in faces:
            # orientar hacia fuera
            a, b, cc = (v.co for v in fv[:3])
            if (b - a).cross(cc - a).dot(n) < 0:
                fv = tuple(reversed(fv))
            f = bm.faces.new(fv)
            for loop in f.loops:
                loop[uv].uv = uvof(*coords[loop.vert])
    o = make_obj("FaceScreen", bm, m["face"], col)
    o.data.shade_smooth()
    return o


# ---------------------------------------------------------------- escena
def build():
    clear_scene()
    col = collection("Ignis")
    m = materials()
    body = build_body(col, m)
    build_face(col, m, body)
    build_tongue(col, m)
    build_horns(col, m)
    build_claws(col, m)
    build_wings(col, m)
    build_flame(col, m)
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in col.objects if o.type == "MESH")
    btris = sum(len(p.vertices) - 2 for p in body.data.polygons)
    print(f"[ignis] objetos={len(col.objects)} triangulos={tris} (IgnisBody {btris})")
    return col, tris


def setup_studio():
    sc = bpy.context.scene
    studio = collection("Studio")
    # ciclorama: suelo que se curva en pared por detras, sin linea de horizonte
    bm = bmesh.new()
    prof = [(y, 0.0) for y in (-8.0, 1.5)]
    prof += [(1.5 + 2.5 * math.sin(a), 2.5 - 2.5 * math.cos(a)) for a in np.linspace(0.15, math.pi / 2, 10)]
    prof += [(4.0, 8.0)]
    rows = [[bm.verts.new((x, y, z)) for x in (-12.0, 12.0)] for y, z in prof]
    for r0, r1 in zip(rows, rows[1:]):
        bm.faces.new((r0[0], r0[1], r1[1], r1[0]))
    floor = make_obj("Floor", bm, principled("FloorMat", "#4A4D53", 0.85), studio)
    floor.data.shade_smooth()

    def area(name, loc, energy, size, color=(1, 1, 1), target=(0, 0.1, 0.7)):
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy, ld.size, ld.color = energy, size, color
        ob = bpy.data.objects.new(name, ld)
        ob.location = loc
        ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        studio.objects.link(ob)

    area("Key", (2.4, -2.6, 2.8), 260, 1.5)
    area("Fill", (-2.6, -2.0, 1.6), 50, 2.5, (0.92, 0.96, 1.0))
    area("Rim", (-0.8, 2.8, 2.4), 220, 1.5, (1.0, 0.9, 0.8))
    world = bpy.data.worlds.new("World")
    sc.world = world
    if world.node_tree is None:
        world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.16, 0.17, 0.19, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
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
    return cam


def render_views(cam, views=None, out=RENDERS):
    sc = bpy.context.scene
    out.mkdir(parents=True, exist_ok=True)
    allv = [
        ("full_front", (0, -3.4, 0.80), (0, 0.15, 0.74), 50, (1000, 1000)),
        ("full_side", (4.2, 0.25, 0.80), (0, 0.25, 0.74), 50, (1400, 1000)),
        ("full_34", (2.9, -3.3, 1.25), (0, 0.2, 0.66), 50, (1400, 1000)),
        ("medium_head", (0.9, -2.2, 1.20), (0, -0.42, 1.00), 50, (1200, 1000)),
    ]
    for name, loc, target, lens, res in allv:
        if views and name not in views:
            continue
        cam.location = loc
        cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        cam.data.lens = lens
        floor = bpy.data.objects.get("Floor")
        if floor:                               # la pared del ciclorama siempre detras del personaje
            v = Vector(target) - Vector(loc)
            floor.rotation_euler = (0, 0, math.atan2(-v.x, v.y))
        sc.render.resolution_x, sc.render.resolution_y = res
        sc.render.filepath = str(out / f"{name}.png")
        bpy.ops.render.render(write_still=True)
        print(f"[ignis] render {name}")


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    build()
    if "--render" in argv:
        render_views(setup_studio())
    if "--save" in argv:
        bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "blender" / "ignis.blend"))
