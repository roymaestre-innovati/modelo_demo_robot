"""Rig, animaciones y exportacion de Robin (fase 4).

Construye el modelo con build_robin.py, crea un esqueleto humanoide con nombres estilo Mixamo
(sin prefijo 'mixamorig:'), emparenta cada pieza al 100 % a su hueso (skinning rigido),
genera los clips idle / talk_1..3 en bucle y exporta assets/robin.glb.

Uso:
    blender/run.sh rig_robin.py                       # exporta el GLB
    blender/run.sh rig_robin.py -- --render-poses      # ademas renderiza hojas de poses
    blender/run.sh rig_robin.py -- --save              # guarda blender/robin_rigged.blend

Convenciones (espacio de armature = mundo, Z arriba, frente -Y, izquierda de Robin +X):
  columna/cabeza: x = inclinar adelante, y = ladear a su izquierda, z = girar a su izquierda (grados)
  brazo: fwd = levantar al frente, out = abrir hacia fuera, twist = rotacion sobre el eje
  antebrazo: bend = flexionar codo, sup = supinar (palma hacia arriba)
  mano: flex = doblar muneca hacia la palma, dev = desviacion lateral
  dedos: curl = cerrar hacia la palma
  pierna: fwd / out (muslo), bend (rodilla), x / y (pie)
Todas las rotaciones se expresan en ejes de reposo y se aplican en el marco del padre ya posado (FK).
"""
import math
import sys
from pathlib import Path

import bpy
from mathutils import Quaternion, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_robin as B  # noqa: E402

FPS = 30
GLB_PATH = B.ROOT / "assets" / "robin.glb"
SIDES = (("Left", "L", 1), ("Right", "R", -1))

# pieza -> hueso
PIECE_BONE = {
    "HeadShell": "Head", "FaceScreen": "Head", "EarL": "Head", "EarR": "Head", "EarCapL": "Head", "EarCapR": "Head",
    "NeckRing": "Neck", "Torso": "Spine2", "ChestLED": "Spine2", "BackPanel": "Spine2",
    "Belt": "Spine", "Pelvis": "Hips",
}
for i in range(5):
    PIECE_BONE[f"HeadGrill{i}"] = "Head"
for i in range(3):
    PIECE_BONE[f"BackSlot{i}"] = "Spine2"
for full, sh, _ in SIDES:
    PIECE_BONE.update({
        f"Shoulder{sh}": f"{full}Arm", f"UpperArm{sh}": f"{full}Arm", f"Elbow{sh}": f"{full}ForeArm",
        f"ForeArm{sh}": f"{full}ForeArm", f"Hand{sh}": f"{full}Hand", f"Thumb{sh}": f"{full}HandThumb1",
        f"Finger1{sh}": f"{full}HandIndex1", f"Finger2{sh}": f"{full}HandMiddle1",
        f"HipJoint{sh}": f"{full}UpLeg", f"Thigh{sh}": f"{full}UpLeg", f"Knee{sh}": f"{full}Leg",
        f"Shin{sh}": f"{full}Leg", f"Foot{sh}": f"{full}Foot",
    })


# ------------------------------------------------------------------ esqueleto
def build_armature():
    J = B.JOINTS
    arm_data = bpy.data.armatures.new("RobinSkeleton")
    arm = bpy.data.objects.new("Robin", arm_data)
    bpy.context.scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm_data.edit_bones

    def bone(name, head, tail, parent=None, connect=False):
        b = eb.new(name)
        b.head, b.tail = Vector(head), Vector(tail)
        b.align_roll(Vector((0, -1, 0)) if abs((b.tail - b.head).normalized().y) < 0.9 else Vector((0, 0, 1)))
        if parent:
            b.parent = eb[parent]
            b.use_connect = connect
        return b

    bone("Hips", (0, 0, 0.62), (0, 0, 0.70))
    bone("Spine", (0, 0, 0.70), (0, 0, 0.80), "Hips", True)
    bone("Spine1", (0, 0, 0.80), (0, 0, 0.92), "Spine", True)
    bone("Spine2", (0, 0, 0.92), (0, 0, 1.05), "Spine1", True)
    bone("Neck", (0, 0, 1.05), (0, 0, B.NECK["z1"]), "Spine2", True)
    bone("Head", (0, 0, B.NECK["z1"]), (0, 0, 1.45), "Neck", True)
    for full, sh, s in SIDES:
        bone(f"{full}Shoulder", (s * 0.05, 0, B.SHOULDER["z"]), J[f"shoulder{sh}"], "Spine2")
        bone(f"{full}Arm", J[f"shoulder{sh}"], J[f"elbow{sh}"], f"{full}Shoulder", True)
        bone(f"{full}ForeArm", J[f"elbow{sh}"], J[f"wrist{sh}"], f"{full}Arm", True)
        bone(f"{full}Hand", J[f"wrist{sh}"], J[f"hand_end{sh}"], f"{full}ForeArm", True)
        for key, nm in (("thumb", "Thumb1"), ("finger1", "Index1"), ("finger2", "Middle1")):
            base, tip = J[f"{key}{sh}"]
            bone(f"{full}Hand{nm}", base, tip, f"{full}Hand")
        bone(f"{full}UpLeg", J[f"hip{sh}"], J[f"knee{sh}"], "Hips")
        bone(f"{full}Leg", J[f"knee{sh}"], J[f"ankle{sh}"], f"{full}UpLeg", True)
        bone(f"{full}Foot", J[f"ankle{sh}"], J[f"ball{sh}"], f"{full}Leg", True)
        bone(f"{full}ToeBase", J[f"ball{sh}"], J[f"toe{sh}"], f"{full}Foot", True)
    bpy.ops.object.mode_set(mode="OBJECT")
    return arm


def parent_pieces(arm, col):
    bpy.context.view_layer.update()
    for obj in col.objects:
        bone = PIECE_BONE.get(obj.name)
        if bone is None:
            raise RuntimeError(f"pieza sin hueso asignado: {obj.name}")
        mw = obj.matrix_world.copy()
        obj.parent = arm
        obj.parent_type = "BONE"
        obj.parent_bone = bone
        bpy.context.view_layer.update()
        obj.matrix_world = mw
    bpy.context.view_layer.update()


# ------------------------------------------------------------------ ejes semanticos
A = math.radians(B.ARM_ANGLE)
X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))


def side_axes(s):
    d = Vector((s * math.sin(A), 0, -math.cos(A)))       # eje del brazo
    a = Vector((math.cos(A), 0, s * math.sin(A)))        # bisagra codo/hombro (fwd = -angulo)
    n = -s * a                                           # normal de la palma (hacia el cuerpo)
    k = d.cross(n).normalized()                          # eje de cierre de dedos/muneca
    return d, a, n, k


AX = {sh: side_axes(s) for _, sh, s in SIDES}


def R(axis, deg):
    return Quaternion(Vector(axis).normalized(), math.radians(deg))


def spine_q(c):
    return R(Z, c.get("z", 0)) @ R(X, c.get("x", 0)) @ R(Y, c.get("y", 0))


def bone_quat(name, c, thumb_axes):
    """Componentes semanticas -> quaternion en espacio de armature (reposo)."""
    side = "L" if name.startswith("Left") else "R" if name.startswith("Right") else None
    s = 1 if side == "L" else -1
    base = name.removeprefix("Left").removeprefix("Right")
    if side is None:
        return spine_q(c)
    d, a, n, k = AX[side]
    if base == "Shoulder":
        return R(Z, -s * c.get("fwd", 0)) @ R(Y, -s * c.get("up", 0))
    if base == "Arm":
        return R(a, -c.get("fwd", 0)) @ R(Y, -s * c.get("out", 0)) @ R(d, -s * c.get("twist", 0))
    if base == "ForeArm":
        return R(a, -c.get("bend", 0)) @ R(d, -s * c.get("sup", 0))
    if base == "Hand":
        return R(k, c.get("flex", 0)) @ R(n, c.get("dev", 0))
    if base in ("HandIndex1", "HandMiddle1"):
        return R(k, c.get("curl", 0))
    if base == "HandThumb1":
        return R(thumb_axes[side], c.get("curl", 0))
    if base == "UpLeg":
        return R(X, -c.get("fwd", 0)) @ R(Y, -s * c.get("out", 0)) @ R(Z, c.get("twist", 0))
    if base == "Leg":
        return R(X, c.get("bend", 0))
    if base == "Foot":
        return R(X, c.get("x", 0)) @ R(Y, c.get("y", 0))
    return Quaternion()


# ------------------------------------------------------------------ poses y clips
def both(base, **c):
    return {f"Left{base}": dict(c), f"Right{base}": dict(c)}


def merge(*poses):
    out = {}
    for p in poses:
        for b, c in p.items():
            out.setdefault(b, {}).update(c)
    return out


def lerp_pose(p0, p1, t):
    out = {}
    for b in set(p0) | set(p1):
        c0, c1 = p0.get(b, {}), p1.get(b, {})
        out[b] = {k: c0.get(k, 0) * (1 - t) + c1.get(k, 0) * t for k in set(c0) | set(c1)}
    return out


def add_pose(p, q):
    out = {b: dict(c) for b, c in p.items()}
    for b, c in q.items():
        o = out.setdefault(b, {})
        for k, v in c.items():
            o[k] = o.get(k, 0) + v
    return out


def ease(t):
    return t * t * t * (t * (6 * t - 15) + 10)


def keyed(keys, t):
    """Interpola una lista [(tiempo, pose), ...] con smootherstep."""
    for (t0, p0), (t1, p1) in zip(keys, keys[1:]):
        if t0 <= t <= t1:
            return lerp_pose(p0, p1, ease((t - t0) / (t1 - t0)))
    return keys[-1][1]


def wave(t, T, cycles, phase=0.0):
    return math.sin(2 * math.pi * (cycles * t / T + phase))


RELAX = merge(both("Arm", fwd=3, out=-4), both("ForeArm", bend=12, sup=10),
              both("HandIndex1", curl=18), both("HandMiddle1", curl=24), both("HandThumb1", curl=8))

READY = merge(both("Arm", fwd=14, out=-6), both("ForeArm", bend=58, sup=40), both("Hand", flex=6),
              both("HandIndex1", curl=22), both("HandMiddle1", curl=28), both("HandThumb1", curl=10))


def weight_shift(dx, roll):
    """Desplaza la cadera en X manteniendo los pies plantados (aprox.)."""
    leg_len = B.JOINTS["hipL"].z - B.JOINTS["ankleL"].z
    th = math.degrees(math.asin(dx / leg_len))
    return merge({"Hips": dict(tx=dx, y=roll), "Spine": dict(y=-roll * 0.8)},
                 {"LeftUpLeg": dict(out=th - roll), "RightUpLeg": dict(out=-(th - roll))},
                 {"LeftFoot": dict(y=-th), "RightFoot": dict(y=-th)})


def breathing(t, T, amp=1.0, cycles=2):
    w = wave(t, T, cycles)
    return merge({"Spine2": dict(x=-1.2 * amp * w), "Spine1": dict(x=-0.4 * amp * w),
                  "Head": dict(x=0.8 * amp * w)},
                 both("Shoulder", up=0.8 * amp * w))


def idle(t):
    T = 5.0
    dx = 0.010 * wave(t, T, 1)
    p = add_pose(RELAX, weight_shift(dx, 1.4 * wave(t, T, 1)))
    p = add_pose(p, breathing(t, T, 1.0, 2))
    p = add_pose(p, {
        "Head": dict(z=4.0 * wave(t, T, 1, 0.15) + 1.2 * wave(t, T, 3, 0.4), x=1.5 * wave(t, T, 2, 0.3),
                     y=1.5 * wave(t, T, 1, 0.6)),
        "Neck": dict(z=1.0 * wave(t, T, 1, 0.15)),
        "LeftArm": dict(fwd=1.2 * wave(t, T, 2, 0.1)), "RightArm": dict(fwd=1.2 * wave(t, T, 2, 0.15)),
        "LeftForeArm": dict(bend=2.0 * wave(t, T, 2, 0.2)), "RightForeArm": dict(bend=2.0 * wave(t, T, 2, 0.25)),
        "LeftHandIndex1": dict(curl=3 * wave(t, T, 1, 0.3)), "RightHandMiddle1": dict(curl=3 * wave(t, T, 1, 0.7)),
    })
    return p


def talk_layer(t, T, head_amp=1.0):
    """Movimiento leve de torso/cabeza comun a los clips de habla."""
    p = add_pose(breathing(t, T, 0.6, 2), weight_shift(0.004 * wave(t, T, 1), 0.6 * wave(t, T, 1)))
    return add_pose(p, {
        "Head": dict(x=2.0 * head_amp * wave(t, T, 4, 0.1), z=3.0 * head_amp * wave(t, T, 2, 0.3),
                     y=1.5 * head_amp * wave(t, T, 1, 0.5)),
        "Spine2": dict(z=2.0 * wave(t, T, 1, 0.2)),
    })


def talk_1(t):
    """Abrir palmas: explicar algo con ambas manos."""
    T = 4.0
    OPEN = merge(both("Arm", fwd=22, out=6), both("ForeArm", bend=72, sup=105), both("Hand", flex=-18),
                 both("HandIndex1", curl=2), both("HandMiddle1", curl=4), both("HandThumb1", curl=-12),
                 {"Spine2": dict(x=2.5), "Head": dict(x=-3)})
    HALF = merge(both("Arm", fwd=18, out=0), both("ForeArm", bend=64, sup=80), both("Hand", flex=-8),
                 both("HandIndex1", curl=10), both("HandMiddle1", curl=14), both("HandThumb1", curl=0))
    keys = [(0.0, READY), (0.7, merge(READY, OPEN)), (1.25, merge(READY, HALF)), (1.75, merge(READY, OPEN)),
            (2.5, merge(READY, HALF, {"Spine2": dict(x=1)})), (3.0, merge(READY, OPEN, both("ForeArm", bend=80))),
            (4.0, READY)]
    return add_pose(keyed(keys, t), talk_layer(t, T))


def talk_2(t):
    """Senalar suave con la mano derecha, con pequenos golpes de enfasis."""
    T = 4.0
    POINT = merge({"RightArm": dict(fwd=60, out=2, twist=-6), "RightForeArm": dict(bend=48, sup=20),
                   "RightHand": dict(flex=-10), "RightHandIndex1": dict(curl=0), "RightHandMiddle1": dict(curl=85),
                   "RightHandThumb1": dict(curl=55)},
                  {"LeftArm": dict(fwd=8, out=-4), "LeftForeArm": dict(bend=40, sup=30)},
                  {"Spine2": dict(z=-4, x=2), "Head": dict(z=-6)})
    BEAT = merge(POINT, {"RightArm": dict(fwd=64, out=2, twist=-6), "RightForeArm": dict(bend=38, sup=20),
                         "RightHand": dict(flex=4), "Head": dict(z=-6, x=4)})
    keys = [(0.0, READY), (0.8, merge(READY, POINT)), (1.25, merge(READY, BEAT)), (1.6, merge(READY, POINT)),
            (2.05, merge(READY, BEAT)), (2.45, merge(READY, POINT)), (2.85, merge(READY, BEAT)),
            (3.3, merge(READY, POINT)), (4.0, READY)]
    return add_pose(keyed(keys, t), talk_layer(t, T, 0.7))


def talk_3(t):
    """Enumerar: la izquierda muestra los dedos, la derecha los va tocando."""
    T = 4.6
    LIST = merge({"LeftArm": dict(fwd=30, out=-12), "LeftForeArm": dict(bend=88, sup=55), "LeftHand": dict(flex=-10),
                  "LeftHandIndex1": dict(curl=0), "LeftHandMiddle1": dict(curl=0), "LeftHandThumb1": dict(curl=-15)},
                 {"RightArm": dict(fwd=28, out=-12), "RightForeArm": dict(bend=78, sup=25),
                  "RightHandIndex1": dict(curl=0), "RightHandMiddle1": dict(curl=80), "RightHandThumb1": dict(curl=50)},
                 {"Spine2": dict(z=3, x=2), "Head": dict(x=6, z=4)})

    def tap(i):
        p = merge(LIST, {"RightArm": dict(fwd=32, out=-16 - 2 * i), "RightForeArm": dict(bend=86, sup=25),
                         "Head": dict(x=7, z=4, y=(-3 if i % 2 else 3))})
        finger = ("LeftHandThumb1", "LeftHandIndex1", "LeftHandMiddle1")[i]
        p[finger] = dict(curl=(25 if i else 5))
        return p

    keys = [(0.0, READY), (0.8, merge(READY, LIST)), (1.2, merge(READY, tap(0))), (1.6, merge(READY, LIST)),
            (2.0, merge(READY, tap(1))), (2.4, merge(READY, LIST)), (2.8, merge(READY, tap(2))),
            (3.4, merge(READY, LIST, {"Head": dict(x=-2, z=0)})), (4.6, READY)]
    return add_pose(keyed(keys, t), talk_layer(t, T, 0.6))


CLIPS = [("idle", idle, 5.0), ("talk_1", talk_1, 4.0), ("talk_2", talk_2, 4.0), ("talk_3", talk_3, 4.6)]


# ------------------------------------------------------------------ horneado a acciones
def thumb_axes(arm):
    out = {}
    for full, sh, _ in SIDES:
        b = arm.data.bones[f"{full}HandThumb1"]
        t = (b.tail_local - b.head_local).normalized()
        out[sh] = t.cross(AX[sh][1] * -1 if sh == "L" else AX[sh][1]).normalized()
    return out


def apply_pose(arm, pose, taxes, prev):
    for pb in arm.pose.bones:
        c = pose.get(pb.name, {})
        q_arm = bone_quat(pb.name, c, taxes)
        rest = pb.bone.matrix_local.to_quaternion()
        q = rest.inverted() @ q_arm @ rest
        if pb.name in prev and prev[pb.name].dot(q) < 0:
            q.negate()
        prev[pb.name] = q.copy()
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = q
        loc = Vector((c.get("tx", 0), c.get("ty", 0), c.get("tz", 0)))
        pb.location = rest.inverted() @ loc


def bake_clip(arm, name, fn, dur, step=2):
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    arm.animation_data_create()
    arm.animation_data.action = act
    taxes = thumb_axes(arm)
    last = round(dur * FPS)
    frames = list(range(0, last, step)) + [last]
    prev = {}
    for f in frames:
        t = min(f / FPS, dur)
        apply_pose(arm, fn(t) if f < last else fn(0.0), taxes, prev)   # ultimo frame == primero
        for pb in arm.pose.bones:
            pb.keyframe_insert("rotation_quaternion", frame=f)
            if pb.name == "Hips":
                pb.keyframe_insert("location", frame=f)
    act.use_frame_range = True
    act.frame_start, act.frame_end = 0, last
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


# ------------------------------------------------------------------ export y verificacion
def export_glb(arm, col):
    GLB_PATH.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True)
    for o in col.objects:
        o.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.export_scene.gltf(
        filepath=str(GLB_PATH), export_format="GLB", use_selection=True, export_yup=True,
        export_apply=True, export_animations=True, export_animation_mode="NLA_TRACKS",
        export_force_sampling=True, export_frame_step=1, export_skins=False, export_anim_single_armature=True,
        export_materials="EXPORT", export_image_format="AUTO", export_cameras=False, export_lights=False,
    )
    print(f"[rig] exportado {GLB_PATH} ({GLB_PATH.stat().st_size / 1024:.0f} KB)")


def render_poses(arm):
    """Hoja de poses por clip para revision visual."""
    cam = B.setup_studio()
    sc = bpy.context.scene
    out = B.RENDERS / "poses"
    out.mkdir(parents=True, exist_ok=True)
    cam.location = (-1.0, -2.9, 1.1)
    cam.rotation_euler = (Vector((0, 0, 0.82)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = 50
    sc.render.resolution_x, sc.render.resolution_y = 480, 640
    sc.render.fps = FPS
    arm.animation_data.use_nla = False
    for name, fn, dur in CLIPS:
        arm.animation_data.action = bpy.data.actions[name]
        if hasattr(arm.animation_data, "action_slot") and bpy.data.actions[name].slots:
            arm.animation_data.action_slot = bpy.data.actions[name].slots[0]
        n = 6
        for i in range(n):
            f = round(i * dur * FPS / n)
            sc.frame_set(f)
            sc.render.filepath = str(out / f"{name}_{i}.png")
            bpy.ops.render.render(write_still=True)
    arm.animation_data.action = None
    arm.animation_data.use_nla = True


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    col, tris = B.build()
    arm = build_armature()
    parent_pieces(arm, col)
    bpy.context.scene.render.fps = FPS
    bpy.context.scene.frame_start = 0
    for name, fn, dur in CLIPS:
        bake_clip(arm, name, fn, dur)
    reset_pose(arm)
    print(f"[rig] huesos={len(arm.data.bones)} clips={[c[0] for c in CLIPS]} triangulos={tris}")
    export_glb(arm, col)
    if "--render-poses" in argv:
        render_poses(arm)
    if "--save" in argv:
        bpy.ops.wm.save_as_mainfile(filepath=str(B.ROOT / "blender" / "robin_rigged.blend"))


if __name__ == "__main__":
    main()
