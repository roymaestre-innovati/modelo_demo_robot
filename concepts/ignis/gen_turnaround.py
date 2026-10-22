"""Hoja turnaround de Ignis (dragon de fuego joven), fase 1.

El dragon se describe como volumenes 3D sencillos (elipsoides encadenados, prismas, poligonos)
en unidades Blender (Z arriba, frente = -Y, izquierda del personaje = +X, origen en el suelo
entre las cuatro patas) y se proyecta en ortografica a cada vista. Asi las vistas quedan
alineadas por construccion, y estas constantes son el plano que sigue blender/build_ignis.py.

Uso: python3 concepts/ignis/gen_turnaround.py && concepts/svg2png.sh concepts/ignis/turnaround.svg
"""
import math
from pathlib import Path

OUT = Path(__file__).parent

# ---- Colores (materiales de dragon/model_spec.json) ----
BODY = "#D93829"        # BodyMat
BELLY = "#FCA311"       # BellyHornsMat (vientre y cuernos)
WING = "#7A1426"        # WingMembraneMat
WING_BONE = "#5E0F1E"   # varillas del ala (mismo material, tono mas oscuro solo en el boceto)
CLAW = "#5A0F1A"        # ClawMat
MOUTH = "#4A0E14"       # MouthMat
TONGUE = "#B3303A"      # lengua (BodyMat en el modelo)
FLAME_OUT = "#FF7A1A"   # TailFlameMat (emision)
FLAME_IN = "#FFB020"    # TailFlameMat (base)
IRIS = "#B5651D"
OUTLINE = "#3B0A10"
BG = "#EEF0F3"

# ---- Medidas (metros, unidades Blender) ----
HEIGHT = 1.50
JAW_MAX_DEG = 24.0      # jawOpen = 1
EYE_R = 0.066

# Cadenas de volumen: (centro, radios). Radio escalar = esfera.
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
JAW = ((0, -0.545, 1.015), (0.095, 0.135, 0.045))
JAW_PIVOT = (0, -0.42, 1.06)
EYE = dict(c=(0.105, -0.535, 1.195), n=(0.50, -0.82, 0.28))   # ojo izquierdo (+X)
NOSTRIL = dict(c=(0.035, -0.695, 1.135), n=(0.25, -0.8, 0.55), r=0.012)
HORN = [((0.085, -0.37, 1.25), 0.046), ((0.12, -0.30, 1.32), 0.038), ((0.15, -0.22, 1.36), 0.030),
        ((0.165, -0.165, 1.42), 0.020), ((0.165, -0.165, 1.50), 0.007)]

FRONT_LEG = [((0.13, -0.22, 0.46), 0.09), ((0.14, -0.19, 0.27), 0.065),
             ((0.14, -0.22, 0.09), 0.055)]
FRONT_PAD = ((0.14, -0.26, 0.04), (0.07, 0.09, 0.04))
BACK_LEG = [((0.15, 0.22, 0.47), 0.12), ((0.16, 0.13, 0.26), 0.08),
            ((0.16, 0.24, 0.10), 0.055)]
BACK_PAD = ((0.16, 0.17, 0.04), (0.075, 0.11, 0.04))
CLAW_LEN = 0.05

# Ala: hombro y longitudes de cada segmento; la pose se define por direcciones.
WING_SHOULDER = (0.10, -0.14, 0.64)
WING_ROOT = (0.12, 0.22, 0.60)        # union de la membrana con el lomo
WING_LEN = dict(hum=0.16, fore=0.18, f1=0.24, f2=0.22, f3=0.18)
WING_POSES = {
    "folded": dict(hum=(0.2, 0.25, 1.0), fore=(0.08, 0.9, 0.45),
                   f1=(0.05, 0.9, -0.1), f2=(0.06, 0.6, -0.75), f3=(0.04, 0.15, -1.0)),
    "half": dict(hum=(1.0, 0.15, 0.5), fore=(1.0, 0.25, 0.15),
                 f1=(0.85, 0.45, -0.05), f2=(0.5, 0.85, -0.15), f3=(0.15, 1.0, -0.2)),
    "open": dict(hum=(1.0, 0.05, 0.2), fore=(1.0, 0.1, 0.05),
                 f1=(1.0, 0.2, 0.0), f2=(0.6, 0.8, -0.1), f3=(0.2, 1.0, -0.15)),
}

FLAME_BASE = (0, 1.14, 0.40)
FLAME_H = 0.30
# perfil de la llama (ancho, altura) normalizado; se dibuja en dos planos cruzados
FLAME_PROFILE = [(0.0, 0.0), (0.42, 0.08), (0.55, 0.30), (0.38, 0.52), (0.48, 0.66), (0.22, 0.80),
                 (0.10, 1.0), (0.0, 0.84), (-0.20, 0.70), (-0.12, 0.58), (-0.45, 0.42),
                 (-0.52, 0.22), (-0.38, 0.06)]


# ---------------- vectores ----------------

def add(a, b): return tuple(x + y for x, y in zip(a, b))
def sub(a, b): return tuple(x - y for x, y in zip(a, b))
def mul(a, s): return tuple(x * s for x in a)
def dot(a, b): return sum(x * y for x, y in zip(a, b))
def cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def norm(a):
    L = math.sqrt(dot(a, a))
    return mul(a, 1 / L)
def mirror(p): return (-p[0], p[1], p[2])


def rot_x(p, pivot, deg):
    """Rota p alrededor del eje X que pasa por pivot (grados positivos abren la mandibula)."""
    a = math.radians(deg)
    _, y, z = sub(p, pivot)
    return add(pivot, (p[0] - pivot[0], y * math.cos(a) - z * math.sin(a), y * math.sin(a) + z * math.cos(a)))


# ---------------- primitivas (nubes de puntos 3D) ----------------

def ell(c, r, n=10, m=5):
    rx, ry, rz = (r, r, r) if isinstance(r, (int, float)) else r
    pts = [(c[0], c[1], c[2] + rz), (c[0], c[1], c[2] - rz)]
    for j in range(1, m):
        phi = math.pi * j / m - math.pi / 2
        for i in range(n):
            th = 2 * math.pi * (i + 0.5 * (j % 2)) / n
            pts.append((c[0] + rx * math.cos(phi) * math.cos(th),
                        c[1] + ry * math.cos(phi) * math.sin(th),
                        c[2] + rz * math.sin(phi)))
    return pts


def chain(nodes, n=10):
    return [ell(a[0], a[1], n) + ell(b[0], b[1], n) for a, b in zip(nodes, nodes[1:])]


def disk(c, n, r, k=18, h_min=None):
    """Puntos de un circulo en el plano normal a n. h_min recorta por debajo (segmento superior)."""
    n = norm(n)
    up = (0, 0, 1)
    v = norm(sub(up, mul(n, dot(up, n))))
    u = cross(v, n)
    pts = []
    if h_min is None:
        for i in range(k):
            t = 2 * math.pi * i / k
            pts.append(add(c, add(mul(u, r * math.cos(t)), mul(v, r * math.sin(t)))))
    else:
        a0 = math.asin(max(-1, min(1, h_min / r)))
        for i in range(k + 1):
            t = a0 + (math.pi - 2 * a0) * i / k
            pts.append(add(c, add(mul(u, r * math.cos(t)), mul(v, r * math.sin(t)))))
    return pts, u, v


def wing_joints(pose, side=1):
    d = WING_POSES[pose]
    L = WING_LEN
    S = WING_SHOULDER
    E = add(S, mul(norm(d["hum"]), L["hum"]))
    W = add(E, mul(norm(d["fore"]), L["fore"]))
    F = [add(W, mul(norm(d[k]), L[k])) for k in ("f1", "f2", "f3")]
    J = dict(S=S, E=E, W=W, F1=F[0], F2=F[1], F3=F[2], B=WING_ROOT)
    if side < 0:
        J = {k: mirror(p) for k, p in J.items()}
    return J


def scallop(a, b, w, k=0.12):
    """Punto medio del borde de fuga, metido hacia la muneca."""
    m = mul(add(a, b), 0.5)
    return add(m, mul(sub(w, m), k))


# ---------------- huesos (cabeza, cola) para marcar articulaciones ----------------

def bones(wing_pose="folded"):
    B = {
        "Root": ((0, 0, 0), (0, 0, 0.15)),
        "Hips": ((0, 0.22, 0.47), (0, 0.06, 0.49)),
        "Spine": ((0, 0.06, 0.49), (0, -0.08, 0.50)),
        "Spine1": ((0, -0.08, 0.50), (0, -0.20, 0.52)),
        "Spine2": ((0, -0.20, 0.52), (0, -0.31, 0.62)),
        "Neck": ((0, -0.31, 0.62), (0, -0.355, 0.76)),
        "Neck1": ((0, -0.355, 0.76), (0, -0.365, 0.88)),
        "Neck2": ((0, -0.365, 0.88), (0, -0.38, 1.00)),
        "Head": ((0, -0.38, 1.00), (0, -0.42, 1.28)),
        "Jaw": (JAW_PIVOT, (0, -0.66, 1.00)),
    }
    fl = [p for p, _ in FRONT_LEG] + [FRONT_PAD[0], (0.14, -0.36, 0.03)]
    bl = [p for p, _ in BACK_LEG] + [BACK_PAD[0], (0.16, 0.06, 0.03)]
    for side, sfx in ((1, "_L"), (-1, "_R")):
        f = fl if side > 0 else [mirror(p) for p in fl]
        b = bl if side > 0 else [mirror(p) for p in bl]
        for i, nm in enumerate(("UpperLeg", "LowerLeg", "Foot", "Toes")):
            B[f"Front{nm}{sfx}"] = (f[i], f[i + 1])
            B[f"Back{nm}{sfx}"] = (b[i], b[i + 1])
        J = wing_joints(wing_pose, side)
        B[f"Wing1{sfx}"] = (J["S"], J["E"])
        B[f"Wing2{sfx}"] = (J["E"], J["W"])
        B[f"Wing3{sfx}"] = (J["W"], J["F1"])
    tp = [p for p, _ in TAIL]
    tail_heads = [tp[0], tp[1], tp[2], tp[3], tp[4], tp[5], tp[7]]
    for i in range(6):
        B[f"Tail_{i + 1}"] = (tail_heads[i], tail_heads[i + 1])
    return B


# ---------------- escena ----------------

def G(name, fill, pieces, depth=None, bias=0.0, kind="hull", **kw):
    return dict(name=name, fill=fill, pieces=pieces, depth=depth, bias=bias, kind=kind, **kw)


def centroid(pieces):
    pts = [p for pc in pieces for p in pc]
    return tuple(sum(c) / len(pts) for c in zip(*pts))


def eye_layers(side, jaw_deg=0.0):
    c = EYE["c"] if side > 0 else mirror(EYE["c"])
    n = EYE["n"] if side > 0 else mirror(EYE["n"])
    c = add(c, mul(norm(n), 0.008))
    sclera, u, v = disk(c, n, EYE_R)
    nn = norm(n)
    f = (0, -1, 0)
    fp = norm(sub(f, mul(nn, dot(f, nn))))
    ic = add(add(c, mul(fp, EYE_R * 0.14)), mul(v, -EYE_R * 0.04))
    iris, _, _ = disk(ic, n, EYE_R * 0.64)
    pupil, _, _ = disk(ic, n, EYE_R * 0.34)
    hc = add(add(ic, mul(v, EYE_R * 0.24)), mul(fp, EYE_R * 0.18))
    hl, _, _ = disk(hc, n, EYE_R * 0.13, 10)
    lid, _, _ = disk(add(c, mul(nn, 0.003)), n, EYE_R * 1.08, 14, h_min=EYE_R * 0.36)
    return [(sclera, "#FFFFFF", True), (iris, IRIS, False), (pupil, "#1E0B06", False),
            (hl, "#FFFFFF", False), (lid, BODY, True)]


def spikes(nodes, n_per, h0, h1, skip_first=0):
    """Pua dorsal = prisma triangular en el plano YZ sobre la cadena."""
    out = []
    pts = []
    for a, b in zip(nodes, nodes[1:]):
        for k in range(n_per):
            t = (k + 0.5) / n_per
            c = add(mul(a[0], 1 - t), mul(b[0], t))
            r = (a[1] if isinstance(a[1], float) else a[1][2]) * (1 - t) + \
                (b[1] if isinstance(b[1], float) else b[1][2]) * t
            tan = norm(sub(b[0], a[0]))
            pts.append((c, r, tan))
    pts = pts[skip_first:]
    N = len(pts)
    for i, (c, r, tan) in enumerate(pts):
        up = norm(sub((0, 0, 1), mul(tan, dot((0, 0, 1), tan))))
        if dot(up, (0, 0, 1)) < 0.2:
            up = norm(add(up, (0, 0.3, 0.6)))
        h = h0 + (h1 - h0) * i / max(1, N - 1)
        base = add(c, mul(up, r * 0.85))
        back = norm(add(tan, mul(up, 0.0)))
        p0 = add(base, mul(back, -h * 0.55))
        p1 = add(base, mul(back, h * 0.55))
        tip = add(add(base, mul(up, h)), mul(back, h * 0.45))
        tri = [p0, p1, tip]
        out.append([add(p, (dx, 0, 0)) for p in tri for dx in (-0.012, 0.012)])
    return out


def claws(pad, sign_y):
    c, r = pad
    out = []
    for dx in (-0.038, 0.0, 0.038):
        base = (c[0] + dx, c[1] + sign_y * (r[1] - 0.02), 0.025)
        tip = (c[0] + dx * 1.2, c[1] + sign_y * (r[1] + CLAW_LEN - 0.02), 0.006)
        out.append(ell(base, (0.017, 0.012, 0.02), 6, 3) + [tip])
    return out


def flame_pieces(scale=1.0, inner=False):
    s = FLAME_H * scale
    b = add(FLAME_BASE, (0, 0, 0.02 if inner else 0))
    yz = [add(b, (0, w * s * 0.55, h * s)) for w, h in FLAME_PROFILE]
    xz = [add(b, (w * s * 0.45, 0, h * s)) for w, h in FLAME_PROFILE]
    return [yz, xz]


def scene(jaw_deg=0.0, wing_pose="folded"):
    g = []
    body_d = (0, 0, 0.5)
    head_d = (0, -0.45, 1.12)
    J = lambda pts: [rot_x(p, JAW_PIVOT, jaw_deg) for p in pts]

    # cuerpo: torso + cuello + cola en una silueta
    body = chain(TORSO) + chain(NECK) + chain(TAIL) + [ell(TORSO[1][0], TORSO[1][1]) + ell(NECK[0][0], NECK[0][1])]
    g.append(G("spikes", BODY, spikes(NECK[1:], 2, 0.045, 0.05) + spikes(TORSO[1:], 2, 0.05, 0.05)
               + spikes(TAIL[:6], 2, 0.05, 0.025), depth=body_d, bias={"top": 0.001, "*": -0.001}))
    g.append(G("body", BODY, body, depth=body_d, clipname="body"))
    # vientre de placas: cadena desplazada hacia delante/abajo, recortada por la silueta del cuerpo
    belly_nodes = []
    for c, r in NECK[:3]:
        belly_nodes.append(((c[0], c[1] - 1.15 * r, c[2]), (0.62 * r, r, r)))
    for (c, r), d in zip(TORSO[:4], [(0, -0.9, -0.45), (0, -0.62, -0.78), (0, -0.05, -1), (0, 0.1, -1)]):
        rx, ry, rz = r
        k = 1.45
        belly_nodes.append(((c[0], c[1] + d[1] * ry * k, c[2] + d[2] * rz * k), (0.62 * rx, ry, rz)))
    belly_nodes.sort(key=lambda t: -t[0][2])
    g.append(G("belly", BELLY, chain(belly_nodes), depth=body_d, bias=0.0005, clip="body",
               views=("front", "side"), plates=True))

    # patas
    for side, sfx in ((1, "L"), (-1, "R")):
        m = (lambda p: p) if side > 0 else mirror
        fl = [(m(c), r) for c, r in FRONT_LEG]
        fpad = (m(FRONT_PAD[0]), FRONT_PAD[1])
        bl = [(m(c), r) for c, r in BACK_LEG]
        bpad = (m(BACK_PAD[0]), BACK_PAD[1])
        fpieces = chain(fl) + [ell(fl[-1][0], fl[-1][1]) + ell(fpad[0], fpad[1])]
        bpieces = chain(bl) + [ell(bl[-1][0], bl[-1][1]) + ell(bpad[0], bpad[1])]
        g.append(G(f"backleg{sfx}", BODY, bpieces))
        g.append(G(f"backclaw{sfx}", CLAW, claws(bpad, -1), depth=bpad[0], bias=0.0005))
        g.append(G(f"frontleg{sfx}", BODY, fpieces))
        g.append(G(f"frontclaw{sfx}", CLAW, claws(fpad, -1), depth=fpad[0], bias=0.0005))

    # alas
    for side, sfx in ((1, "L"), (-1, "R")):
        Jw = wing_joints(wing_pose, side)
        W = Jw["W"]
        mem = [[Jw["S"], Jw["E"], W, Jw["F1"]],
               [W, Jw["F1"], scallop(Jw["F1"], Jw["F2"], W), Jw["F2"]],
               [W, Jw["F2"], scallop(Jw["F2"], Jw["F3"], W), Jw["F3"]],
               [W, Jw["F3"], scallop(Jw["F3"], Jw["B"], W, 0.18), Jw["B"], Jw["S"]]]
        dc = centroid(mem)
        g.append(G(f"wing{sfx}", WING, mem, depth=dc, kind="poly"))
        struts = []
        for a, b, r0, r1 in (("S", "E", 0.026, 0.02), ("E", "W", 0.02, 0.016),
                             ("W", "F1", 0.014, 0.006), ("W", "F2", 0.012, 0.006), ("W", "F3", 0.012, 0.006)):
            struts.append(ell(Jw[a], r0, 8, 3) + ell(Jw[b], r1, 8, 3))
        g.append(G(f"wingbone{sfx}", WING_BONE, struts, depth=dc, bias=0.0005))

    # llama de la cola
    g.append(G("flame", FLAME_OUT, flame_pieces(1.0) + [ell(add(FLAME_BASE, (0, 0, 0.12)), (0.06, 0.07, 0.1), 8, 4)],
               kind="poly", depth=add(FLAME_BASE, (0, 0, 0.15)), bias=0.002))
    g.append(G("flame_in", FLAME_IN, flame_pieces(0.6, True), kind="poly",
               depth=add(FLAME_BASE, (0, 0, 0.15)), bias=0.0021, stroke=False))

    # cabeza
    pal = []
    flo = []
    for y, w in ((-0.43, 0.075), (-0.52, 0.08), (-0.60, 0.065), (-0.645, 0.04)):
        for sx in (-1, 1):
            pal.append((sx * w, y, 1.06))
            flo.append((sx * w, y, 1.045))
    g.append(G("mouth", MOUTH, [pal + J(flo)], depth=head_d, bias=0.007))
    g.append(G("tongue", TONGUE, [J(ell((0, -0.56, 1.05), (0.05, 0.085, 0.02), 10, 4))], depth=head_d, bias=0.008))
    # la parte trasera de la mandibula queda detras de la abertura en frontal
    g.append(G("jawback", BODY, [J(ell((0, -0.45, 1.03), (0.12, 0.09, 0.06)))], depth=head_d,
               bias={"front": 0.0049, "*": 0.009}))
    g.append(G("jaw", BODY, [J(ell(JAW[0], JAW[1]))], depth=head_d, bias=0.0091))
    # mejillas con aletas y puas de la nuca (por detras de la cabeza)
    fins = []
    for side in (1, -1):
        for (y, z, h) in ((-0.31, 1.13, 0.07), (-0.30, 1.21, 0.06), (-0.33, 1.06, 0.05)):
            base = (side * 0.12, y, z)
            tip = (side * 0.17, y + h * 1.1, z + h * 0.25)
            fins.append([add(base, (0, dy, dz)) for dy in (-0.03, 0.03) for dz in (-0.02, 0.02)] + [tip])
    g.append(G("fins", BODY, fins, depth=head_d, bias={"top": 0.0115, "*": 0.0095}))
    # en frontal el craneo va detras de la boca abierta; en lateral, delante
    g.append(G("cranium", BODY, [ell(CRANIUM[0], CRANIUM[1], 12, 6)], depth=head_d,
               bias={"front": 0.005, "*": 0.010}))
    g.append(G("head", BODY, [ell(SNOUT[0], SNOUT[1], 12, 5), ell((0, -0.50, 1.14), (0.13, 0.10, 0.10))],
               depth=head_d, bias={"front": 0.0101, "*": 0.0101}))
    # pliegue de la sonrisa (solo en reposo)
    if jaw_deg < 1:
        for side in (1, -1):
            pts = [(side * 0.100, -0.53, 1.058), (side * 0.112, -0.47, 1.07), (side * 0.112, -0.435, 1.092)]
            g.append(G(f"smile{side}", OUTLINE, [pts], depth=head_d, bias=0.0102, kind="line"))
    for side in (1, -1):
        hn = [(c if side > 0 else mirror(c), r) for c, r in HORN]
        g.append(G(f"horn{side}", BELLY, chain(hn, 8), depth=hn[1][0], bias=0.0))
        g.append(G(f"eye{side}", None, eye_layers(side), depth=EYE["c"] if side > 0 else mirror(EYE["c"]),
                   bias=0.0103, kind="layers"))
        nc = NOSTRIL["c"] if side > 0 else mirror(NOSTRIL["c"])
        nn = NOSTRIL["n"] if side > 0 else mirror(NOSTRIL["n"])
        g.append(G(f"nostril{side}", None, [(disk(add(nc, mul(norm(nn), 0.004)), nn, NOSTRIL["r"], 10)[0], MOUTH, False)],
                   depth=nc, bias=0.011, kind="layers"))
    return g


# ---------------- proyeccion y SVG ----------------

VIEWS = {
    # right, up, hacia la camara
    "front": ((1, 0, 0), (0, 0, 1), (0, -1, 0)),
    "side": ((0, 1, 0), (0, 0, 1), (1, 0, 0)),
    "top": ((0, 1, 0), (-1, 0, 0), (0, 0, 1)),
    "wingtop": ((-1, 0, 0), (0, -1, 0), (0, 0, 1)),
}


def hull(pts):
    pts = sorted(set((round(x, 2), round(y, 2)) for x, y in pts))
    if len(pts) < 3:
        return pts
    def half(seq):
        h = []
        for p in seq:
            while len(h) >= 2 and ((h[-1][0] - h[-2][0]) * (p[1] - h[-2][1]) - (h[-1][1] - h[-2][1]) * (p[0] - h[-2][0])) <= 0:
                h.pop()
            h.append(p)
        return h
    lo, up = half(pts), half(reversed(pts))
    return lo[:-1] + up[:-1]


def path(pts, close=True):
    d = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in pts)
    return d + (" Z" if close else "")


class Cam:
    def __init__(self, view, ox, oy, s):
        self.R, self.U, self.C = VIEWS[view]
        self.view, self.ox, self.oy, self.s = view, ox, oy, s

    def __call__(self, p):
        return (self.ox + self.s * dot(p, self.R), self.oy - self.s * dot(p, self.U))


def render(groups, cam, uid, lw=2.0, fade=None, bones_mark=None, labels=False):
    view = cam.view
    out = []
    defs = []
    items = []
    for i, gr in enumerate(groups):
        if gr.get("views") and view not in gr["views"] and not (view == "wingtop" and "top" in gr["views"]):
            continue
        if view == "wingtop" and gr["name"] == "belly":
            continue
        dpt = gr["depth"] or centroid(gr["pieces"] if gr["kind"] != "layers" else [l[0] for l in gr["pieces"]])
        b = gr["bias"]
        if isinstance(b, dict):
            b = b.get("top" if view in ("top", "wingtop") else view, b.get("*", 0))
        items.append((dot(dpt, cam.C) + b, i, gr))
    items.sort(key=lambda t: (t[0], t[1]))
    clips = {}
    for _, _, gr in items:
        k = gr["kind"]
        op = ""
        if fade and not any(gr["name"].startswith(f) for f in fade):
            op = ' opacity="0.28"'
        if k in ("hull", "poly"):
            polys = [hull([cam(p) for p in pc]) if k == "hull" else [cam(p) for p in pc] for pc in gr["pieces"]]
            polys = [p for p in polys if len(p) >= 3]
            if gr.get("clipname"):
                cid = f"{uid}-{gr['clipname']}"
                clips[gr["clipname"]] = cid
                defs.append(f'<clipPath id="{cid}">' + "".join(f'<path d="{path(p)}"/>' for p in polys) + "</clipPath>")
            wrap0, wrap1 = "", ""
            if gr.get("clip") and gr["clip"] in clips:
                wrap0, wrap1 = f'<g clip-path="url(#{clips[gr["clip"]]})">', "</g>"
            out.append(f"<g{op}>" + wrap0)
            if gr.get("stroke", True):
                for p in polys:
                    out.append(f'<path d="{path(p)}" fill="{OUTLINE}" stroke="{OUTLINE}" stroke-width="{2 * lw:.1f}" stroke-linejoin="round"/>')
            for p in polys:
                out.append(f'<path d="{path(p)}" fill="{gr["fill"]}"/>')
            if gr.get("plates"):
                bid = f"{uid}-belly"
                defs.append(f'<clipPath id="{bid}">' + "".join(f'<path d="{path(p)}"/>' for p in polys) + "</clipPath>")
                out.append(f'<g clip-path="url(#{bid})">' + plates(cam, lw) + "</g>")
            out.append(wrap1 + "</g>")
        elif k == "line":
            for pc in gr["pieces"]:
                out.append(f'<path d="{path([cam(p) for p in pc], False)}" fill="none" stroke="{OUTLINE}" '
                           f'stroke-width="{1.3 * lw:.1f}" stroke-linecap="round"{op}/>')
        elif k == "layers":
            out.append(f"<g{op}>")
            for pts, fill, stroke in gr["pieces"]:
                q = [cam(p) for p in pts]
                st = f' stroke="{OUTLINE}" stroke-width="{lw:.1f}" stroke-linejoin="round"' if stroke else ""
                out.append(f'<path d="{path(q)}" fill="{fill}"{st}/>')
            out.append("</g>")
    if bones_mark:
        for nm, (h, t) in bones_mark.items():
            if nm == "Root":
                continue
            if view == "side" and nm.endswith("_R"):
                continue
            if view == "front" and (nm.endswith("_R") or nm.startswith("Tail")):
                continue
            x, y = cam(h)
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="#FFFFFF" stroke="#1F4E79" stroke-width="2"/>')
            if labels:
                out.append(f'<text x="{x + 6:.1f}" y="{y - 5:.1f}" font-family="sans-serif" font-size="11" '
                           f'fill="#1F4E79" stroke="{BG}" stroke-width="3" paint-order="stroke">{nm.replace("_L", "")}</text>')
    return "<defs>" + "".join(defs) + "</defs>" + "".join(out)


def plates(cam, lw):
    """Lineas de separacion de las placas ventrales (se recortan con el vientre)."""
    out = []
    view = cam.view
    if view == "front":
        for z in (0.30, 0.38, 0.47, 0.56, 0.66, 0.76, 0.86):
            a, b = cam((-0.3, -0.5, z)), cam((0.3, -0.5, z + 0.012))
            out.append((a, (a[0] / 2 + b[0] / 2, a[1] + 6), b))
    elif view == "side":
        segs = [(NECK[2][0], NECK[1][0]), (NECK[1][0], NECK[0][0]), (NECK[0][0], TORSO[1][0]),
                (TORSO[1][0], TORSO[2][0]), (TORSO[2][0], TORSO[3][0])]
        for a3, b3 in segs:
            for t in (0.0, 0.5):
                c = add(mul(a3, 1 - t), mul(b3, t))
                tan = norm(sub(b3, a3))
                perp = norm(cross((1, 0, 0), tan))
                p0, p1 = cam(add(c, mul(perp, 0.35))), cam(add(c, mul(perp, -0.35)))
                out.append((p0, ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2), p1))
    return "".join(f'<path d="M {a[0]:.1f} {a[1]:.1f} Q {m[0]:.1f} {m[1]:.1f} {b[0]:.1f} {b[1]:.1f}" fill="none" '
                   f'stroke="#B8640A" stroke-width="{1.4 * lw:.1f}"/>' for a, m, b in out)


def extents(groups, axis):
    vals = [dot(p, axis) for gr in groups if gr["kind"] in ("hull", "poly") for pc in gr["pieces"] for p in pc]
    return min(vals), max(vals)


# ---------------- hoja ----------------

W, H = 2760, 1500
S = 430
GROUND = 800
FRONT_CX = 330
SIDE_OX = 1110          # px de y = 0 en lateral y superior
TOP_OY = 1170           # px de x = 0 en la vista superior
WING_CX, WING_CY = 330, 1210
TXT = 'font-family="sans-serif"'


def text(x, y, s, size=14, fill="#33475B", anchor="start", weight="normal"):
    return (f'<text x="{x:.1f}" y="{y:.1f}" {TXT} font-size="{size}" fill="{fill}" text-anchor="{anchor}" '
            f'font-weight="{weight}">{s}</text>')


def dim(p0, p1, txt, off=(0, 0), vertical=False, anchor="middle"):
    (x0, y0), (x1, y1) = p0, p1
    c = "#C2410C"
    t = (f'<g stroke="{c}" stroke-width="1.5"><line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}"/>')
    if vertical:
        t += f'<line x1="{x0 - 7:.1f}" y1="{y0:.1f}" x2="{x0 + 7:.1f}" y2="{y0:.1f}"/><line x1="{x1 - 7:.1f}" y1="{y1:.1f}" x2="{x1 + 7:.1f}" y2="{y1:.1f}"/>'
    else:
        t += f'<line x1="{x0:.1f}" y1="{y0 - 7:.1f}" x2="{x0:.1f}" y2="{y0 + 7:.1f}"/><line x1="{x1:.1f}" y1="{y1 - 7:.1f}" x2="{x1:.1f}" y2="{y1 + 7:.1f}"/>'
    t += "</g>"
    t += text((x0 + x1) / 2 + off[0], (y0 + y1) / 2 + off[1], txt, 15, c, anchor)
    return t


def main():
    rest = scene(0.0, "folded")
    B = bones("folded")
    zmin, zmax = extents(rest, (0, 0, 1))
    ymin, ymax = extents(rest, (0, 1, 0))
    xmin, xmax = extents(rest, (1, 0, 0))
    half = scene(0.0, "half")
    hx0, hx1 = extents([g for g in half if g["name"].startswith("wing")], (1, 0, 0))
    print(f"altura {zmax:.3f}  largo {ymax - ymin:.3f} (y {ymin:.3f}..{ymax:.3f})  ancho {xmax - xmin:.3f}")
    print(f"envergadura alas a medias {hx1 - hx0:.3f}")
    full = scene(0.0, "open")
    fx0, fx1 = extents([g for g in full if g["name"].startswith("wing")], (1, 0, 0))
    torso_len = (TORSO[-1][0][1] + TORSO[-1][1][1]) - (TORSO[0][0][1] - TORSO[0][1][1])
    print(f"envergadura abiertas {fx1 - fx0:.3f}  torso {torso_len:.3f}  ratio {(fx1 - fx0) / torso_len:.2f}")

    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
         f'<rect width="{W}" height="{H}" fill="{BG}"/>',
         text(W / 2, 46, "Ignis · Turnaround en pose de reposo (dragón de fuego joven)", 30, "#1E2A36", "middle", "bold")]

    # niveles
    levels = [(zmax, f"{zmax:.2f} punta cuernos"), (1.31, "1.31 tope cráneo"), (EYE["c"][2], f"{EYE['c'][2]:.2f} ojos"),
              (JAW_PIVOT[2], f"{JAW_PIVOT[2]:.2f} bisagra Jaw"), (0.68, "0.68 lomo"),
              (0.47, "0.47 hombro / cadera"), (0.27, "0.27 codo / rodilla"), (0.0, "0.00 suelo")]
    for z, lbl in levels:
        y = GROUND - z * S
        s.append(f'<line x1="20" y1="{y:.1f}" x2="1680" y2="{y:.1f}" stroke="#7FA7C9" stroke-width="1" stroke-dasharray="6 6" opacity="0.7"/>')
        s.append(text(20, y - 5, lbl, 13, "#4A6A88"))

    # sombras
    for cx, rx in ((FRONT_CX, 0.32), (SIDE_OX + 0.22 * S, 0.95)):
        s.append(f'<ellipse cx="{cx:.1f}" cy="{GROUND + 2}" rx="{rx * S:.1f}" ry="12" fill="#000" opacity="0.10"/>')

    cf = Cam("front", FRONT_CX, GROUND, S)
    cs = Cam("side", SIDE_OX, GROUND, S)
    ct = Cam("top", SIDE_OX, TOP_OY, S)
    s.append(render(rest, cf, "f", bones_mark=B))
    s.append(render(rest, cs, "s", bones_mark=B, labels=True))
    s.append(render(rest, ct, "t"))
    s.append(text(FRONT_CX, GROUND + 80, "FRONTAL", 20, "#1E2A36", "middle", "bold"))
    s.append(text(SIDE_OX + 0.22 * S, GROUND + 80, "LATERAL izquierda (frente ←)", 20, "#1E2A36", "middle", "bold"))
    s.append(text(SIDE_OX + 0.22 * S, TOP_OY + 0.36 * S + 34, "SUPERIOR (alas plegadas, frente ←)", 20, "#1E2A36", "middle", "bold"))

    # cotas
    s.append(dim(cs((0, 1.32, 0)), cs((0, 1.32, zmax)), f"{zmax:.2f} total", (-10, -200), vertical=True, anchor="end"))
    s.append(dim((cs((0, ymin, 0))[0], GROUND + 22), (cs((0, ymax, 0))[0], GROUND + 22), f"largo {ymax - ymin:.2f}", (0, 20)))
    s.append(dim((cf((xmin, 0, 0))[0], GROUND + 22), (cf((xmax, 0, 0))[0], GROUND + 22), f"ancho {xmax - xmin:.2f}", (0, 20)))
    hw = CRANIUM[1][0] * 2
    s.append(dim((cf((-CRANIUM[1][0], 0, 0))[0], cf((0, 0, 1.56))[1]), (cf((CRANIUM[1][0], 0, 0))[0], cf((0, 0, 1.56))[1]),
                 f"cráneo {hw:.2f}", (0, -10)))
    s.append(dim(cs((0, -0.36, 1.58)), cs((0, -0.36, 1.58)), "", (0, 0))[:0])
    hy0 = SNOUT[0][1] - SNOUT[1][1]
    hy1 = CRANIUM[0][1] + CRANIUM[1][1]
    s.append(dim((cs((0, hy0, 0))[0], cs((0, 0, 1.6))[1]), (cs((0, hy1, 0))[0], cs((0, 0, 1.6))[1]),
                 f"cabeza {hy1 - hy0:.2f}", (0, -10)))
    s.append(dim((ct((0, ymin, 0))[0], TOP_OY + 0.36 * S), (ct((0, ymax, 0))[0], TOP_OY + 0.36 * S), "", (0, 0)))

    # alas a medias (vista superior)
    PY0, PY1 = 935, H - 20
    s.append(f'<defs><clipPath id="wclip"><rect x="10" y="{PY0}" width="740" height="{PY1 - PY0}" rx="14"/></clipPath></defs>')
    s.append(f'<rect x="10" y="{PY0}" width="740" height="{PY1 - PY0}" rx="14" fill="#E3E7EC" stroke="#C9CFD6"/>')
    s.append(text(380, PY0 + 30, "Alas abiertas a la mitad · vista superior (frente ↑)", 18, "#1E2A36", "middle", "bold"))
    cw = Cam("wingtop", 380, PY0 + 120 + 0.7 * S * 0.8, S * 0.8)
    s.append('<g clip-path="url(#wclip)">' + render(half, cw, "w", fade=("wing",)) + "</g>")
    Jw = wing_joints("half", 1)
    for a, b, nm in (("S", "E", "1"), ("E", "W", "2"), ("W", "F1", "3")):
        pa, pb = cw(Jw[a]), cw(Jw[b])
        mx, my = (pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2 - 18
        s.append(f'<circle cx="{mx:.1f}" cy="{my:.1f}" r="11" fill="#1F4E79"/>' + text(mx, my + 5, nm, 13, "#FFF", "middle", "bold"))
    for k in ("S", "E", "W"):
        x, y = cw(Jw[k])
        s.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="#FFFFFF" stroke="#1F4E79" stroke-width="2"/>')
    leg = [f"1 Wing1 hombro→codo {WING_LEN['hum']:.2f}", f"2 Wing2 antebrazo {WING_LEN['fore']:.2f}",
           f"3 Wing3 dedos de membrana {WING_LEN['f1']:.2f} / {WING_LEN['f2']:.2f} / {WING_LEN['f3']:.2f}"]
    for i, t in enumerate(leg):
        s.append(text(40, PY1 - 92 + i * 20, t, 14, "#1F4E79"))
    s.append(text(40, PY1 - 22, f"envergadura a medias {hx1 - hx0:.2f} m · abiertas {fx1 - fx0:.2f} m "
                  f"(≈{(fx1 - fx0) / torso_len:.1f}× torso {torso_len:.2f})", 14, "#33475B"))

    # recuadro de la cabeza
    RX, RY = 1720, 80
    s.append(f'<line x1="{RX - 20}" y1="70" x2="{RX - 20}" y2="{H - 30}" stroke="#C9CFD6" stroke-width="1.5"/>')
    s.append(text(RX + 510, RY + 10, "Cabeza · ojos neutral · boca REST y A", 22, "#1E2A36", "middle", "bold"))
    HS = 520
    panels = [("front", 0.0, "frontal · REST"), ("side", 0.0, "lateral · REST"),
              ("front", 0.8 * JAW_MAX_DEG, f"frontal · A (Jaw {0.8 * JAW_MAX_DEG:.0f}°)"),
              ("side", 0.8 * JAW_MAX_DEG, f"lateral · A (Jaw {0.8 * JAW_MAX_DEG:.0f}°)")]
    for i, (view, jaw, lbl) in enumerate(panels):
        col, row = i % 2, i // 2
        px, py = RX + col * 520, RY + 30 + row * 450
        pw, ph = 500, 420
        cid = f"hp{i}"
        s.append(f'<defs><clipPath id="{cid}"><rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="14"/></clipPath></defs>')
        s.append(f'<rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="14" fill="#E3E7EC" stroke="#C9CFD6"/>')
        if view == "front":
            cam = Cam("front", px + pw / 2, py + ph * 0.47 + 1.24 * HS, HS)
        else:
            cam = Cam("side", px + pw / 2 + 0.44 * HS, py + ph * 0.47 + 1.24 * HS, HS)
        s.append(f'<g clip-path="url(#{cid})">' + render(scene(jaw, "folded"), cam, f"h{i}", lw=2.4) + "</g>")
        s.append(f'<rect x="{px + pw / 2 - 120}" y="{py + ph - 36}" width="240" height="28" rx="14" fill="#FFFFFF" opacity="0.9"/>')
        s.append(text(px + pw / 2, py + ph - 16, lbl, 16, "#1E2A36", "middle", "bold"))

    # medidas
    TX, TY = RX, 1020
    rows = [
        ("Altura", f"{zmax:.2f} hasta los cuernos · lomo 0.68"),
        ("Largo / ancho", f"{ymax - ymin:.2f} hocico→llama · {xmax - xmin:.2f} (muslos)"),
        ("Cabeza", f"cráneo {CRANIUM[1][0] * 2:.2f}×{CRANIUM[1][1] * 2:.2f}×{CRANIUM[1][2] * 2:.2f} · hocico hasta y {hy0:.2f}"),
        ("Ojos", f"r {EYE_R:.3f}, centro x ±{EYE['c'][0]:.3f} z {EYE['c'][2]:.2f}, 35° hacia fuera"),
        ("Mandíbula", f"bisagra z {JAW_PIVOT[2]:.2f} · jawOpen 1 = {JAW_MAX_DEG:.0f}°"),
        ("Cuello", "3 huesos, r 0.12 → 0.085, en S suave"),
        ("Torso", "pera 0.86 de largo, ancho 0.33 → 0.42 (atrás)"),
        ("Patas", "del. r 0.09→0.055 · tras. muslo r 0.12 · 3 garras romas"),
        ("Cola", "6 huesos, r 0.12 → 0.03, apoya en y 0.83 · llama 0.30"),
        ("Alas", "Wing1 0.16 · Wing2 0.18 · dedos 0.24/0.22/0.18"),
    ]
    s.append(text(TX, TY, "Medidas (metros)", 18, "#1E2A36", "start", "bold"))
    for i, (k, v) in enumerate(rows):
        s.append(text(TX, TY + 28 + i * 22, k, 14, "#1E2A36", "start", "bold"))
        s.append(text(TX + 130, TY + 28 + i * 22, v, 14))
    sw = [(BODY, "BodyMat"), (BELLY, "BellyHornsMat"), (WING, "WingMembraneMat"), (CLAW, "ClawMat"),
          (MOUTH, "MouthMat"), (FLAME_IN, "TailFlameMat")]
    for i, (c, n) in enumerate(sw):
        x = TX + (i % 3) * 330
        y = TY + 270 + (i // 3) * 26
        s.append(f'<rect x="{x}" y="{y - 13}" width="16" height="16" fill="{c}" stroke="{OUTLINE}"/>')
        s.append(text(x + 24, y, f"{n} {c}", 13))
    s.append(text(TX, TY + 340, "○ articulaciones (cabeza del hueso, nombres de dragon/model_spec.json)", 13, "#1F4E79"))
    s.append("</svg>")
    (OUT / "turnaround.svg").write_text("\n".join(s))
    print(OUT / "turnaround.svg")


if __name__ == "__main__":
    main()
