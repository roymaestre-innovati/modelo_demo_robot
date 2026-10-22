"""Rig, shape keys, animaciones y exportacion de Ignis (fase 3).

Construye el modelo con build_ignis.py, crea el esqueleto de dragon/model_spec.json, pesa la malla
(automatico en el cuerpo, por distancia a los huesos en las alas, reparto geometrico Head/Jaw en la
boca), crea las shape keys MouthWide y MouthRound, genera idle / talk_1..3 y exporta assets/ignis.glb.

Las patas se animan con IK (empties fijos en el suelo) y el resultado se hornea a FK por frame;
Jaw y las shape keys no llevan keyframes: los controla three.js en tiempo de ejecucion.

Uso:
    blender/run.sh rig_ignis.py                     # exporta el GLB e informa del deslizamiento de pies
    blender/run.sh rig_ignis.py -- --render-poses   # ademas hojas de poses y bocas A/O/E
    blender/run.sh rig_ignis.py -- --save           # guarda blender/ignis_rigged.blend

Convencion de rotaciones (grados, ejes del armature = mundo, frente -Y, izquierda de Ignis +X),
aplicadas en la cabeza del hueso, en ejes de reposo y en el marco del padre ya posado (FK):
  x = cabecear (+ baja el hocico / la punta del hueso hacia abajo si apunta al frente)
  y = ladear (+ inclina la parte de arriba hacia su izquierda)
  z = girar (+ hacia su izquierda)
Los huesos _R se escriben como espejo de los _L (x igual, y y z con signo cambiado).
"""
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_ignis as B  # noqa: E402

FPS = 30
GLB_PATH = B.ROOT / "assets" / "ignis.glb"
POSES_DIR = B.RENDERS / "poses"
X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
LEGS = ("Front", "Back")
SIDES = (("_L", 1), ("_R", -1))
WING_HALF = dict(hum=(1.0, 0.15, 0.5), fore=(1.0, 0.25, 0.15), f1=(0.85, 0.45, -0.05))  # turnaround

# mouth shapes for jawOpen / MouthWide / MouthRound previews (prompt table)
MOUTH_PREVIEW = {"A": (0.8, 0.2, 0.0), "O": (0.6, 0.0, 0.7), "E": (0.45, 0.7, 0.0)}

# pieza rigida -> hueso
PIECE_BONE = {"FaceScreen": "Head", "Horn_L": "Head", "Horn_R": "Head", "Tongue": "Jaw", "TailFlame": "Tail_6"}
for _sfx in ("_L", "_R"):
    PIECE_BONE[f"FrontClaws{_sfx}"] = f"FrontToes{_sfx}"
    PIECE_BONE[f"BackClaws{_sfx}"] = f"BackToes{_sfx}"


# ------------------------------------------------------------------ esqueleto
def bone_table():
    """nombre -> (cabeza, cola, padre)."""
    T = {
        "Root": ((0, 0, 0), (0, 0, 0.15), None),
        "Hips": ((0, 0.22, 0.47), (0, 0.06, 0.49), "Root"),
        "Spine": ((0, 0.06, 0.49), (0, -0.08, 0.50), "Hips"),
        "Spine1": ((0, -0.08, 0.50), (0, -0.20, 0.52), "Spine"),
        "Spine2": ((0, -0.20, 0.52), (0, -0.31, 0.62), "Spine1"),
        "Neck": ((0, -0.31, 0.62), (0, -0.355, 0.76), "Spine2"),
        "Neck1": ((0, -0.355, 0.76), (0, -0.365, 0.88), "Neck"),
        "Neck2": ((0, -0.365, 0.88), (0, -0.38, 1.00), "Neck1"),
        "Head": ((0, -0.38, 1.00), (0, -0.42, 1.28), "Neck2"),
        "Jaw": (B.JAW_PIVOT, (0, -0.66, 1.00), "Head"),
    }
    tp = [c for c, _ in B.TAIL]
    heads = [tp[0], tp[1], tp[2], tp[3], tp[4], tp[5], tp[7]]
    for i in range(6):
        T[f"Tail_{i + 1}"] = (heads[i], heads[i + 1], "Hips" if i == 0 else f"Tail_{i}")
    for sfx, s in SIDES:
        m = lambda p: (s * p[0], p[1], p[2])  # noqa: E731
        f = [c for c, _ in B.FRONT_LEG] + [B.FRONT_PAD[0], (0.14, -0.36, 0.03)]
        b = [c for c, _ in B.BACK_LEG] + [B.BACK_PAD[0], (0.16, 0.06, 0.03)]
        for name, pts, root in (("Front", f, "Spine2"), ("Back", b, "Hips")):
            prev = root
            for i, part in enumerate(("UpperLeg", "LowerLeg", "Foot", "Toes")):
                T[f"{name}{part}{sfx}"] = (m(pts[i]), m(pts[i + 1]), prev)
                prev = f"{name}{part}{sfx}"
        J = B.wing_joints(s)
        T[f"Wing1{sfx}"] = (tuple(J["S"]), tuple(J["E"]), "Spine2")
        T[f"Wing2{sfx}"] = (tuple(J["E"]), tuple(J["W"]), f"Wing1{sfx}")
        T[f"Wing3{sfx}"] = (tuple(J["W"]), tuple(J["F1"]), f"Wing2{sfx}")
    return T


def build_armature():
    data = bpy.data.armatures.new("IgnisSkeleton")
    arm = bpy.data.objects.new("Ignis", data)
    bpy.context.scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    eb = data.edit_bones
    for name, (h, t, parent) in bone_table().items():
        b = eb.new(name)
        b.head, b.tail = Vector(h), Vector(t)
        d = (b.tail - b.head).normalized()
        b.align_roll(Vector((0, 0, 1)) if abs(d.z) < 0.7 else Vector((0, -1, 0)))
        if parent:
            b.parent = eb[parent]
    bpy.ops.object.mode_set(mode="OBJECT")
    data.bones["Root"].use_deform = False
    return arm


# ------------------------------------------------------------------ pesos
def select_only(objs, active):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = active


def auto_weights(arm, obj, deform):
    """ARMATURE_AUTO limitado a los huesos de 'deform'."""
    saved = {b.name: b.use_deform for b in arm.data.bones}
    for b in arm.data.bones:
        b.use_deform = b.name in deform
    select_only([obj, arm], arm)
    bpy.ops.object.parent_set(type="ARMATURE_AUTO")
    for b in arm.data.bones:
        b.use_deform = saved[b.name]


def jaw_factor(co):
    """1 en la mandibula (bajo la hendidura y por delante de la comisura), 0 en el resto de la cabeza."""
    y, z = co[:, 1], co[:, 2]
    yc = np.minimum(y, B.MOUTH_CORNER_Y)
    below = z < np.array([B.mouth_z(v) for v in yc])
    fade = np.clip((-0.38 - y) / 0.065, 0, 1)
    return below * fade


def fix_head_jaw(body):
    """Reparte el peso de la cabeza entre Head y Jaw con la hendidura de la boca como frontera."""
    me = body.data
    vg = body.vertex_groups
    for name in ("Head", "Jaw"):
        if name not in vg:
            vg.new(name=name)
    gH, gJ = vg["Head"].index, vg["Jaw"].index
    co = B.verts_np(me)
    j = jaw_factor(co)
    for v, jf in zip(me.vertices, j):
        w = 0.0
        for g in v.groups:
            if g.group in (gH, gJ):
                w += g.weight
        if w <= 0:
            continue
        vg["Head"].add([v.index], w * (1 - jf), "REPLACE")
        vg["Jaw"].add([v.index], w * jf, "REPLACE")


def segment_dist(p, a, b):
    ab = b - a
    t = np.clip(((p - a) @ ab) / (ab @ ab), 0, 1)
    return np.linalg.norm(p - (a + t[:, None] * ab), axis=1)


def wing_weights(arm, obj, sfx, s):
    """Pesos por distancia a los segmentos del ala; el borde que se une al lomo sigue a la columna."""
    J = {k: np.array(v) for k, v in B.wing_joints(s).items()}
    mid = (J["S"] + J["B"]) / 2
    segs = [("Wing1" + sfx, J["S"], J["E"]), ("Wing2" + sfx, J["E"], J["W"]),
            ("Wing3" + sfx, J["W"], J["F1"]), ("Wing3" + sfx, J["W"], J["F2"]), ("Wing3" + sfx, J["W"], J["F3"]),
            ("Spine2", J["S"], mid), ("Spine", mid, J["B"])]
    co = B.verts_np(obj.data)
    d = np.stack([segment_dist(co, a, b) for _, a, b in segs], 1)
    w = 1.0 / (d + 0.01) ** 4
    names = sorted({n for n, _, _ in segs})
    agg = np.stack([w[:, [i for i, (n, _, _) in enumerate(segs) if n == nm]].sum(1) for nm in names], 1)
    agg /= agg.sum(1, keepdims=True)
    for k, nm in enumerate(names):
        g = obj.vertex_groups.new(name=nm)
        for i in range(len(co)):
            if agg[i, k] > 0.02:
                g.add([i], float(agg[i, k]), "REPLACE")
    obj.parent = arm
    mod = obj.modifiers.new("Armature", "ARMATURE")
    mod.object = arm


def parent_rigid(arm, col):
    bpy.context.view_layer.update()
    for name, bone in PIECE_BONE.items():
        obj = col.objects[name]
        mw = obj.matrix_world.copy()
        obj.parent = arm
        obj.parent_type = "BONE"
        obj.parent_bone = bone
        bpy.context.view_layer.update()
        obj.matrix_world = mw
    bpy.context.view_layer.update()


def limit_influences(obj, n=4):
    """Como mucho n huesos por vertice, normalizados (glTF usa 4)."""
    names = {g.index: g.name for g in obj.vertex_groups}
    for v in obj.data.vertices:
        ws = sorted(((g.weight, g.group) for g in v.groups if g.weight > 0), reverse=True)
        keep = ws[:n]
        tot = sum(w for w, _ in keep) or 1.0
        for w, gi in ws[n:]:
            obj.vertex_groups[names[gi]].remove([v.index])
        for w, gi in keep:
            obj.vertex_groups[names[gi]].add([v.index], w / tot, "REPLACE")


def skin(arm, col):
    body = col.objects["IgnisBody"]
    body_bones = [b.name for b in arm.data.bones if b.name != "Root" and not b.name.startswith("Wing")]
    auto_weights(arm, body, body_bones)
    fix_head_jaw(body)
    for sfx, s in SIDES:
        for part in ("WingMembrane", "WingArm"):
            wing_weights(arm, col.objects[f"{part}{sfx}"], sfx, s)
    for o in col.objects:
        if o.vertex_groups:
            limit_influences(o)
            mw = o.matrix_world.copy()         # malla con skin en la raiz del glTF (solo el modificador)
            o.parent = None
            o.matrix_world = mw
    parent_rigid(arm, col)
    empty = [v.index for v in body.data.vertices if not v.groups]
    print(f"[rig] IgnisBody: {len(body.vertex_groups)} grupos, vertices sin peso={len(empty)}")
    return body


# ------------------------------------------------------------------ shape keys de la boca
def mouth_shape_keys(body):
    """MouthWide estira las comisuras hacia atras y arriba; MouthRound adelanta y estrecha los labios."""
    me = body.data
    body.shape_key_add(name="Basis")
    co = B.verts_np(me)
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    mz = np.array([B.mouth_z(min(v, B.MOUTH_CORNER_Y)) for v in y])
    near_lip = np.exp(-((z - mz) / 0.035) ** 2) * (y < -0.38) * (np.abs(x) < 0.16)
    corner = np.array([0.105, B.MOUTH_CORNER_Y, B.mouth_z(B.MOUTH_CORNER_Y)])
    dc = np.sqrt((np.abs(x) - corner[0]) ** 2 + (y - corner[1]) ** 2 + (z - corner[2]) ** 2)
    corner_w = np.exp(-(dc / 0.06) ** 2)
    front_w = near_lip * np.clip((-0.48 - y) / 0.12, 0, 1)
    sx = np.sign(x)

    wide = np.zeros_like(co)
    wide[:, 0] = sx * (0.016 * corner_w + 0.006 * front_w)
    wide[:, 1] = 0.014 * corner_w
    wide[:, 2] = 0.006 * corner_w
    rnd = np.zeros_like(co)
    rnd[:, 0] = -x * 0.22 * front_w - sx * 0.012 * corner_w
    rnd[:, 1] = -0.014 * front_w - 0.008 * corner_w
    for name, d in (("MouthWide", wide), ("MouthRound", rnd)):
        k = body.shape_key_add(name=name, from_mix=False)
        k.data.foreach_set("co", (co + d).ravel())
    return body


# ------------------------------------------------------------------ poses
def R(axis, deg):
    return Quaternion(Vector(axis).normalized(), math.radians(deg))


def euler_q(c):
    return R(Z, c.get("z", 0)) @ R(X, c.get("x", 0)) @ R(Y, c.get("y", 0))


def mirror_c(c):
    return {k: (-v if k in ("y", "z", "tx") else v) for k, v in c.items()}


def LR(base, **c):
    """Pose para el hueso _L y su espejo _R."""
    return {f"{base}_L": dict(c), f"{base}_R": mirror_c(c)}


def merge(*poses):
    out = {}
    for p in poses:
        for b, c in p.items():
            out.setdefault(b, {}).update(c)
    return out


def add_pose(*poses):
    out = {}
    for p in poses:
        for b, c in p.items():
            o = out.setdefault(b, {})
            for k, v in c.items():
                o[k] = o.get(k, 0) + v
    return out


def lerp_pose(p0, p1, t):
    out = {}
    for b in set(p0) | set(p1):
        c0, c1 = p0.get(b, {}), p1.get(b, {})
        out[b] = {k: c0.get(k, 0) * (1 - t) + c1.get(k, 0) * t for k in set(c0) | set(c1)}
    return out


def ease(t):
    return t * t * t * (t * (6 * t - 15) + 10)


def keyed(keys, t):
    for (t0, p0), (t1, p1) in zip(keys, keys[1:]):
        if t0 <= t <= t1:
            return lerp_pose(p0, p1, ease((t - t0) / (t1 - t0)))
    return keys[-1][1]


def wave(t, T, cycles, phase=0.0):
    return math.sin(2 * math.pi * (cycles * t / T + phase))


def ik(foot, **c):
    """Desplazamiento del objetivo IK de un pie (tx, ty, tz en metros; x en grados)."""
    return {f"_ik_{foot}": c}


def wings(open_=0.0):
    return {"_wing": dict(open=open_)}


def breathing(t, T, amp=1.0, cycles=2):
    b = wave(t, T, cycles)
    return add_pose({"Spine1": dict(x=-0.8 * amp * b), "Spine2": dict(x=-1.6 * amp * b),
                     "Neck": dict(x=1.2 * amp * b), "Head": dict(x=0.4 * amp * b),
                     "Hips": dict(tz=0.003 * amp * b)},
                    LR("Wing1", y=3.0 * amp * b, x=-1.5 * amp * b), LR("Wing2", y=1.5 * amp * b))


def tail_sway(t, T, amp=1.0, cycles=1):
    return {f"Tail_{i}": dict(z=amp * a * wave(t, T, cycles, ph)) for i, a, ph in
            ((3, 2.0, 0.0), (4, 4.0, 0.08), (5, 8.0, 0.16), (6, 11.0, 0.24))}


def idle(t):
    T = 5.0
    w1 = wave(t, T, 1)
    return add_pose(
        breathing(t, T, 1.0, 2), tail_sway(t, T, 1.0, 1),
        {"Hips": dict(tx=0.012 * w1, y=1.0 * w1), "Spine": dict(y=-0.6 * w1), "Spine2": dict(y=-0.6 * w1),
         "Neck1": dict(z=2.0 * wave(t, T, 1, 0.1)),
         "Head": dict(z=5.0 * wave(t, T, 1, 0.15) + 1.5 * wave(t, T, 3, 0.4), x=2.0 * wave(t, T, 2, 0.3),
                      y=2.0 * wave(t, T, 1, 0.6))})


def talk_layer(t, T, head_amp=1.0):
    return add_pose(breathing(t, T, 0.6, 2), tail_sway(t, T, 0.7, 2),
                    {"Head": dict(x=2.0 * head_amp * wave(t, T, 4, 0.1), z=3.0 * head_amp * wave(t, T, 2, 0.3))})


def talk_1(t):
    """Alza la garra delantera izquierda a media altura, asiente para remarcar y la apoya."""
    T = 4.0
    LIFT = merge(ik("FrontFoot_L", tz=0.13, ty=-0.07, x=35),
                 {"Hips": dict(tx=-0.022, y=-2.0), "Spine2": dict(y=-3.0, z=4.0), "Spine1": dict(y=-1.5),
                  "Neck": dict(x=-3.0), "Head": dict(z=4.0)})
    NOD = merge(LIFT, {"Head": dict(x=13.0, z=4.0), "Neck2": dict(x=4.0),
                       "_ik_FrontFoot_L": dict(tz=0.12, ty=-0.08, x=45)})
    keys = [(0.0, {}), (0.75, LIFT), (1.15, NOD), (1.5, LIFT), (1.9, NOD), (2.3, LIFT),
            (2.7, merge(NOD, {"Head": dict(x=8.0, z=4.0)})), (3.15, LIFT), (3.75, {}), (4.0, {})]
    return add_pose(keyed(keys, t), talk_layer(t, T, 0.6))


def talk_2(t):
    """Se yergue (traseras apoyadas), abre las alas a la mitad y estira el cuello: entusiasmo."""
    T = 4.0
    REAR = merge({"Spine": dict(x=-4.0), "Spine1": dict(x=-4.0), "Spine2": dict(x=-4.0),
                  "Neck": dict(x=-6.0), "Neck1": dict(x=-4.0), "Neck2": dict(x=4.0), "Head": dict(x=12.0),
                  "Tail_1": dict(x=6.0), "Tail_2": dict(x=-3.0)},
                 ik("FrontFoot_L", tz=0.075, ty=0.03, x=18), ik("FrontFoot_R", tz=0.075, ty=0.03, x=18),
                 wings(1.0))
    FLAP = merge(REAR, wings(0.8), {"Head": dict(x=9.0)})
    keys = [(0.0, {}), (0.9, REAR), (1.5, FLAP), (2.1, REAR), (2.7, FLAP), (3.2, merge(REAR, wings(0.9))),
            (4.0, {})]
    return add_pose(keyed(keys, t), talk_layer(t, T, 0.5))


def talk_3(t):
    """Ladea la cabeza con curiosidad, pliega las alas contra el cuerpo y da un toque con la cola."""
    T = 4.6
    FOLD = merge(LR("Wing1", x=-22.0, y=-7.0), LR("Wing2", x=-6.0))
    TILT = merge(FOLD, {"Head": dict(y=17.0, z=9.0, x=-3.0), "Neck2": dict(z=5.0, y=3.0), "Neck1": dict(x=-3.0)})
    TILT2 = merge(FOLD, {"Head": dict(y=-8.0, z=-4.0, x=2.0), "Neck2": dict(z=-2.0)})
    UP = {"Tail_3": dict(x=16.0), "Tail_4": dict(x=12.0), "Tail_5": dict(x=8.0)}
    TAP = {"Tail_3": dict(x=-1.0), "Tail_4": dict(x=-1.5)}
    keys = [(0.0, {}), (0.9, TILT), (1.55, merge(TILT, UP)), (1.95, merge(TILT, TAP)), (2.15, merge(TILT, UP)),
            (2.35, merge(TILT, TAP)), (2.7, TILT), (3.3, TILT2), (3.8, merge(TILT2, {"Head": dict(y=-4.0)})),
            (4.6, {})]
    return add_pose(keyed(keys, t), talk_layer(t, T, 0.4))


CLIPS = [("idle", idle, 5.0), ("talk_1", talk_1, 4.0), ("talk_2", talk_2, 4.0), ("talk_3", talk_3, 4.6)]
LIFTING = {"talk_1": {"FrontFoot_L"}, "talk_2": {"FrontFoot_L", "FrontFoot_R"}}  # pies que pueden despegar


# ------------------------------------------------------------------ IK y horneado
def wing_open_quats(sfx, s):
    """Rotaciones locales (ejes de reposo) de Wing1..3 que llevan el ala de plegada a medio abrir."""
    fold = {k: Vector(v).normalized() for k, v in B.WING_DIRS.items()}
    half = {k: Vector(v).normalized() for k, v in WING_HALF.items()}
    q1 = fold["hum"].rotation_difference(half["hum"])
    q2 = fold["fore"].rotation_difference(q1.inverted() @ half["fore"])
    q3 = fold["f1"].rotation_difference((q1 @ q2).inverted() @ half["f1"])
    qs = [q1, q2, q3]
    if s < 0:
        qs = [Quaternion((q.w, q.x, -q.y, -q.z)) for q in qs]
    return qs


def setup_ik(arm):
    targets = {}
    for leg in LEGS:
        for sfx, _ in SIDES:
            foot = arm.data.bones[f"{leg}Foot{sfx}"]
            e = bpy.data.objects.new(f"IK_{leg}Foot{sfx}", None)
            bpy.context.scene.collection.objects.link(e)
            e.matrix_world = arm.matrix_world @ foot.matrix_local
            targets[f"{leg}Foot{sfx}"] = (e, foot.matrix_local.copy())
            c = arm.pose.bones[f"{leg}LowerLeg{sfx}"].constraints.new("IK")
            c.target, c.chain_count, c.use_tail = e, 2, True
            cr = arm.pose.bones[f"{leg}Foot{sfx}"].constraints.new("COPY_ROTATION")
            cr.target = e
    return targets


def clear_ik(arm, targets):
    for pb in arm.pose.bones:
        for c in list(pb.constraints):
            pb.constraints.remove(c)
    for e, _ in targets.values():
        bpy.data.objects.remove(e)


IK_DRIVEN = {f"{leg}{part}{sfx}" for leg in LEGS for part in ("UpperLeg", "LowerLeg", "Foot") for sfx, _ in SIDES}


def apply_pose(arm, pose, targets, wq):
    op = pose.get("_wing", {}).get("open", 0.0)
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
        if pb.name in IK_DRIVEN:
            pb.rotation_quaternion = Quaternion()
            pb.location = Vector()
            continue
        c = pose.get(pb.name, {})
        rest = pb.bone.matrix_local.to_quaternion()
        qa = euler_q(c)
        if pb.name in wq and op:
            qa = qa @ Quaternion().slerp(wq[pb.name], op)
        q = rest.inverted() @ qa @ rest
        pb.rotation_quaternion = q
        pb.location = rest.inverted() @ Vector((c.get("tx", 0), c.get("ty", 0), c.get("tz", 0)))
    for foot, (e, rest_m) in targets.items():
        c = pose.get(f"_ik_{foot}", {})
        off = Matrix.Translation((c.get("tx", 0), c.get("ty", 0), c.get("tz", 0)))
        rot = R(X, c.get("x", 0)).to_matrix().to_4x4()
        loc = Matrix.Translation(rest_m.translation)
        e.matrix_world = arm.matrix_world @ off @ loc @ rot @ loc.inverted() @ rest_m


def sample_clip(arm, fn, dur, targets, wq):
    """Evalua la pose con IK por frame y devuelve las matrices de pose de todos los huesos."""
    last = round(dur * FPS)
    frames = []
    for f in range(last + 1):
        apply_pose(arm, fn(min(f / FPS, dur)) if f < last else fn(0.0), targets, wq)
        bpy.context.view_layer.update()
        frames.append({pb.name: pb.matrix.copy() for pb in arm.pose.bones})
    return frames


def basis_from_pose(arm, mats):
    out = {}
    for pb in arm.pose.bones:
        b = pb.bone
        if b.parent:
            rel = b.parent.matrix_local.inverted() @ b.matrix_local
            out[pb.name] = rel.inverted() @ mats[b.parent.name].inverted() @ mats[pb.name]
        else:
            out[pb.name] = b.matrix_local.inverted() @ mats[pb.name]
    return out


def bake_clip(arm, name, frames):
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    arm.animation_data_create()
    arm.animation_data.action = act
    prev = {}
    for f, mats in enumerate(frames):
        basis = basis_from_pose(arm, mats)
        for pb in arm.pose.bones:
            if pb.name in ("Root", "Jaw"):
                continue                                  # Jaw lo controla three.js
            loc, q, _ = basis[pb.name].decompose()
            if pb.name in prev and prev[pb.name].dot(q) < 0:
                q.negate()
            prev[pb.name] = q.copy()
            pb.rotation_quaternion = q
            pb.keyframe_insert("rotation_quaternion", frame=f)
            if pb.name == "Hips":
                pb.location = loc
                pb.keyframe_insert("location", frame=f)
    act.use_frame_range = True
    act.frame_start, act.frame_end = 0, len(frames) - 1
    slot = arm.animation_data.action_slot
    track = arm.animation_data.nla_tracks.new()
    track.name = name
    strip = track.strips.new(name, 0, act)
    if slot is not None and hasattr(strip, "action_slot"):
        strip.action_slot = slot
    arm.animation_data.action = None
    arm.animation_data.use_nla = True
    return act


def reset_pose(arm):
    for pb in arm.pose.bones:
        pb.rotation_quaternion = Quaternion()
        pb.location = Vector()


def use_action(arm, name):
    arm.animation_data.use_nla = False
    act = bpy.data.actions[name]
    arm.animation_data.action = act
    if hasattr(arm.animation_data, "action_slot") and act.slots:
        arm.animation_data.action_slot = act.slots[0]


def check_feet(arm):
    """Deslizamiento de los pies apoyados (sobre la animacion horneada, sin constraints)."""
    sc = bpy.context.scene
    worst = 0.0
    for name, _, dur in CLIPS:
        use_action(arm, name)
        rest = {}
        report = []
        for f in range(round(dur * FPS) + 1):
            sc.frame_set(f)
            for leg in LEGS:
                for sfx, _ in SIDES:
                    foot = f"{leg}Foot{sfx}"
                    p = arm.matrix_world @ arm.pose.bones[foot].tail
                    rest.setdefault(foot, []).append(p.copy())
        for foot, ps in rest.items():
            d = max((p - ps[0]).length for p in ps)
            if foot in LIFTING.get(name, ()):
                report.append(f"{foot} despega {max(p.z - ps[0].z for p in ps) * 100:.1f} cm")
                continue
            worst = max(worst, d)
            report.append(f"{foot} {d * 1000:.1f} mm")
        print(f"[rig] pies {name}: " + ", ".join(report))
    arm.animation_data.action = None
    arm.animation_data.use_nla = True
    print(f"[rig] deslizamiento maximo de un pie apoyado: {worst * 1000:.1f} mm")
    return worst


# ------------------------------------------------------------------ export
def export_glb(arm, col):
    GLB_PATH.parent.mkdir(parents=True, exist_ok=True)
    select_only([arm] + [o for o in col.objects], arm)
    bpy.ops.export_scene.gltf(
        filepath=str(GLB_PATH), export_format="GLB", use_selection=True, export_yup=True,
        export_apply=False, export_animations=True, export_animation_mode="NLA_TRACKS",
        export_force_sampling=False, export_frame_step=1, export_skins=True, export_morph=True,
        export_optimize_animation_size=True, export_optimize_animation_keep_anim_armature=False,
        export_morph_normal=False, export_anim_single_armature=True, export_def_bones=False,
        export_materials="EXPORT", export_image_format="AUTO", export_cameras=False, export_lights=False,
    )
    print(f"[rig] exportado {GLB_PATH} ({GLB_PATH.stat().st_size / 1024:.0f} KB)")


# ------------------------------------------------------------------ renders de revision
def aim(cam, loc, target, lens):
    cam.location = Vector(loc)
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = lens
    floor = bpy.data.objects.get("Floor")
    if floor:
        v = Vector(target) - Vector(loc)
        floor.rotation_euler = (0, 0, math.atan2(-v.x, v.y))


def render_poses(arm, body):
    cam = B.setup_studio()
    sc = bpy.context.scene
    POSES_DIR.mkdir(parents=True, exist_ok=True)
    sc.render.resolution_x, sc.render.resolution_y = 720, 560
    aim(cam, (3.0, -3.1, 1.3), (0, 0.2, 0.68), 50)
    for name, _, dur in CLIPS:
        use_action(arm, name)
        n = 6
        for i in range(n):
            sc.frame_set(round(i * dur * FPS / n))
            sc.render.filepath = str(POSES_DIR / f"{name}_{i}.png")
            bpy.ops.render.render(write_still=True)
    # bocas: Jaw y shape keys fijados a mano (no van en ningun clip)
    arm.animation_data.action = None
    arm.animation_data.use_nla = False
    reset_pose(arm)
    keys = body.data.shape_keys.key_blocks
    jaw = arm.pose.bones["Jaw"]
    rest = jaw.bone.matrix_local.to_quaternion()
    aim(cam, (0.75, -1.75, 1.18), (0, -0.5, 1.08), 85)
    sc.render.resolution_x, sc.render.resolution_y = 640, 560
    for shape, (jo, wd, rd) in [("REST", (0, 0, 0))] + list(MOUTH_PREVIEW.items()):
        jaw.rotation_quaternion = rest.inverted() @ R(X, jo * B.JAW_MAX_DEG) @ rest
        keys["MouthWide"].value, keys["MouthRound"].value = wd, rd
        sc.frame_set(0)
        sc.render.filepath = str(POSES_DIR / f"mouth_{shape}.png")
        bpy.ops.render.render(write_still=True)
    jaw.rotation_quaternion = Quaternion()
    keys["MouthWide"].value = keys["MouthRound"].value = 0
    arm.animation_data.use_nla = True


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    col, tris = B.build()
    arm = build_armature()
    body = skin(arm, col)
    mouth_shape_keys(body)
    sc = bpy.context.scene
    sc.render.fps = FPS
    sc.frame_start = 0
    targets = setup_ik(arm)
    wq = {}
    for sfx, s in SIDES:
        for i, q in enumerate(wing_open_quats(sfx, s)):
            wq[f"Wing{i + 1}{sfx}"] = q
    sampled = [(name, sample_clip(arm, fn, dur, targets, wq)) for name, fn, dur in CLIPS]
    clear_ik(arm, targets)
    for name, frames in sampled:
        bake_clip(arm, name, frames)
    reset_pose(arm)
    print(f"[rig] huesos={len(arm.data.bones)} clips={[c[0] for c in CLIPS]} triangulos={tris}")
    check_feet(arm)
    export_glb(arm, col)
    if "--render-poses" in argv:
        render_poses(arm, body)
    if "--save" in argv:
        bpy.ops.wm.save_as_mainfile(filepath=str(B.ROOT / "blender" / "ignis_rigged.blend"))


if __name__ == "__main__":
    main()
