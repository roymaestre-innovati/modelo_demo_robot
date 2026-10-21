"""Hoja turnaround de Robin (variante B · Chibi), fase 2.

Todas las medidas en unidades Blender (Z arriba, frente = -Y, origen en el suelo entre los pies).
Estas constantes son el plano que sigue blender/build_robin.py.

Uso: python3 concepts/gen_turnaround.py && concepts/svg2png.sh concepts/turnaround.svg
"""
import math
from pathlib import Path

from gen_concepts import ACCENT, DEFS, LINE, DLINE

OUT = Path(__file__).parent

# ---- Medidas (unidades Blender) ----
HEIGHT = 1.60
HEAD = dict(w=0.60, h=0.48, d=0.46, z=1.36, r=0.20)           # caja redondeada
SCREEN = dict(w=0.50, h=0.34, z=1.37, r=0.15)                 # pantalla frontal
EAR = dict(r=0.075, t=0.05, x=0.315)                          # discos laterales
NECK = dict(r=0.05, z0=1.05, z1=1.13)
TORSO = dict(z0=0.73, z1=1.07, w_top=0.40, w_bot=0.34, d_top=0.26, d_bot=0.24, r=0.05)
LED = dict(z=0.97, r=0.014)
BELT = dict(z0=0.695, z1=0.73, w=0.22, d=0.18)
PELVIS = dict(z0=0.58, z1=0.695, w_top=0.27, w_bot=0.22, d=0.21)
HIP = dict(x=0.077, z=0.585, r=0.038)
THIGH = dict(z0=0.57, z1=0.37, r=0.057)
KNEE = dict(z=0.35, r=0.036)
SHIN = dict(z0=0.34, z1=0.12, r0=0.055, r1=0.05)
FOOT = dict(x=0.085, w=0.16, h=0.11, y_front=-0.15, y_back=0.11)
SHOULDER = dict(x=0.215, z=1.00, r=0.05)
ARM_ANGLE = 35  # grados desde la vertical (A-pose)
UPPER = dict(L=0.17, r=0.042)
ELBOW_R = 0.03
FORE = dict(L=0.15, r0=0.04, r1=0.036)
HAND = dict(palm_L=0.075, palm_W=0.08, palm_T=0.045, fing_L=0.05, fing_r=0.018, thumb_L=0.04, thumb_r=0.017)

S = 500          # px por unidad
GROUND = 960
W, H = 2620, 1080
CX_FRONT, CX_SIDE, CX_BACK = 440, 940, 1440

a = math.radians(ARM_ANGLE)
ADIR = (math.sin(a), -math.cos(a))
ELBOW = (SHOULDER["x"] + ADIR[0] * UPPER["L"], SHOULDER["z"] + ADIR[1] * UPPER["L"])
WRIST = (ELBOW[0] + ADIR[0] * FORE["L"], ELBOW[1] + ADIR[1] * FORE["L"])


def P(cx, u, z):
    return cx + u * S, GROUND - z * S


def seg_px(p1, p2, r, r2=None, fill="url(#body)"):
    (x1, y1), (x2, y2) = p1, p2
    L = math.hypot(x2 - x1, y2 - y1)
    ang = math.degrees(math.atan2(y2 - y1, x2 - x1)) - 90
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    r2 = r if r2 is None else r2
    h = L / 2
    d = f"M {-r} {-h} A {r} {r} 0 0 1 {r} {-h} L {r2} {h} A {r2} {r2} 0 0 1 {-r2} {h} Z"
    return f'<path d="{d}" fill="{fill}" {LINE} transform="translate({mx:.1f},{my:.1f}) rotate({ang:.2f})"/>'


def circ(cx, u, z, r, fill="url(#darkR)", stroke=DLINE):
    x, y = P(cx, u, z)
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r * S:.1f}" fill="{fill}" {stroke}/>'


def rrect(cx, u0, u1, z0, z1, r, fill="url(#body)", stroke=LINE):
    x0, y1 = P(cx, u0, z0)
    x1, y0 = P(cx, u1, z1)
    return (f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{x1 - x0:.1f}" height="{y1 - y0:.1f}" '
            f'rx="{r * S:.1f}" fill="{fill}" {stroke}/>')


def trap(cx, w_top, w_bot, z0, z1, r, fill="url(#body)", off_top=0.0, off_bot=0.0):
    """Trapecio redondeado, simetrico respecto a off."""
    rr = r * S
    tl = P(cx, off_top - w_top / 2, z1); tr = P(cx, off_top + w_top / 2, z1)
    bl = P(cx, off_bot - w_bot / 2, z0); br = P(cx, off_bot + w_bot / 2, z0)
    d = (f"M {tl[0] + rr:.1f} {tl[1]:.1f} L {tr[0] - rr:.1f} {tr[1]:.1f} Q {tr[0]:.1f} {tr[1]:.1f} {tr[0]:.1f} {tr[1] + rr:.1f} "
         f"L {br[0]:.1f} {br[1] - rr:.1f} Q {br[0]:.1f} {br[1]:.1f} {br[0] - rr:.1f} {br[1]:.1f} "
         f"L {bl[0] + rr:.1f} {bl[1]:.1f} Q {bl[0]:.1f} {bl[1]:.1f} {bl[0]:.1f} {bl[1] - rr:.1f} "
         f"L {tl[0]:.1f} {tl[1] + rr:.1f} Q {tl[0]:.1f} {tl[1]:.1f} {tl[0] + rr:.1f} {tl[1]:.1f} Z")
    return f'<path d="{d}" fill="{fill}" {LINE}/>'


def face(x, y, w, h, eyes="neutral", mouth="REST", glow=True):
    """Dibuja ojos y boca en un rect de pantalla (coords px)."""
    g = [f'<g {"filter=\"url(#glow)\"" if glow else ""} fill="{ACCENT}" stroke="{ACCENT}">']
    ecx, ecy = x + w / 2, y + h * 0.44
    ex, er = w * 0.2, h * 0.16
    for sx in (-1, 1):
        cx = ecx + sx * ex
        if eyes == "neutral":
            g.append(f'<ellipse cx="{cx:.1f}" cy="{ecy:.1f}" rx="{er * 0.85:.1f}" ry="{er:.1f}" stroke="none"/>')
        elif eyes == "listening":
            g.append(f'<ellipse cx="{cx:.1f}" cy="{ecy:.1f}" rx="{er * 1.0:.1f}" ry="{er * 1.18:.1f}" stroke="none"/>')
        elif eyes == "happy":
            g.append(f'<path d="M {cx - er:.1f} {ecy + er * 0.4:.1f} Q {cx:.1f} {ecy - er * 1.3:.1f} {cx + er:.1f} {ecy + er * 0.4:.1f}" '
                     f'fill="none" stroke-width="{er * 0.45:.1f}" stroke-linecap="round"/>')
        elif eyes == "thinking":
            g.append(f'<ellipse cx="{cx + er * 0.35:.1f}" cy="{ecy - er * 0.35:.1f}" rx="{er * 0.8:.1f}" ry="{er * 0.62:.1f}" stroke="none"/>')
    mcx, mcy, mw = x + w / 2, y + h * 0.74, w * 0.16
    if mouth == "REST":
        g.append(f'<path d="M {mcx - mw / 2:.1f} {mcy:.1f} Q {mcx:.1f} {mcy + mw * 0.32:.1f} {mcx + mw / 2:.1f} {mcy:.1f}" '
                 f'fill="none" stroke-width="{h * 0.03:.1f}" stroke-linecap="round"/>')
    elif mouth == "A":
        g.append(f'<rect x="{mcx - mw * 0.5:.1f}" y="{mcy - mw * 0.25:.1f}" width="{mw:.1f}" height="{mw * 0.7:.1f}" '
                 f'rx="{mw * 0.33:.1f}" stroke="none"/>')
    elif mouth == "O":
        g.append(f'<ellipse cx="{mcx:.1f}" cy="{mcy:.1f}" rx="{mw * 0.28:.1f}" ry="{mw * 0.34:.1f}" stroke="none"/>')
    elif mouth == "E":
        g.append(f'<rect x="{mcx - mw * 0.6:.1f}" y="{mcy - mw * 0.12:.1f}" width="{mw * 1.2:.1f}" height="{mw * 0.32:.1f}" '
                 f'rx="{mw * 0.16:.1f}" stroke="none"/>')
    elif mouth == "dots":
        for i in (-1, 0, 1):
            g.append(f'<circle cx="{mcx + i * mw * 0.35:.1f}" cy="{mcy:.1f}" r="{h * 0.025:.1f}" stroke="none" opacity="{0.45 + 0.25 * (i + 1)}"/>')
    g.append("</g>")
    return "".join(g)


# ---------------- vistas ----------------

def hand_edge(cx, side):
    """Mano en vista frontal/trasera: palma hacia el muslo, se ve de canto."""
    wx, wz = WRIST
    w = P(cx, side * wx, wz)
    ang = math.degrees(math.atan2(-ADIR[1], side * ADIR[0])) - 90
    t, pl, fl = HAND["palm_T"] * S, HAND["palm_L"] * S, HAND["fing_L"] * S
    fr = HAND["fing_r"] * S
    g = [f'<g transform="translate({w[0]:.1f},{w[1]:.1f}) rotate({ang:.2f})">',
         f'<rect x="{-t / 2:.1f}" y="-4" width="{t:.1f}" height="{pl:.1f}" rx="{t * 0.45:.1f}" fill="url(#body)" {LINE}/>',
         seg_px((0, pl - 4), (0, pl + fl - fr - 4), fr),
         "</g>"]
    return "".join(g)


def limbs(cx, side, view):
    """Brazo y pierna de un lado (side=+1 derecha de la imagen)."""
    g = []
    # pierna
    hx = side * HIP["x"]
    g.append(seg_px(P(cx, hx, THIGH["z0"]), P(cx, hx, THIGH["z1"]), THIGH["r"] * S))
    g.append(seg_px(P(cx, hx, SHIN["z0"]), P(cx, hx, SHIN["z1"]), SHIN["r0"] * S, SHIN["r1"] * S))
    g.append(circ(cx, hx, KNEE["z"], KNEE["r"]))
    fx = side * FOOT["x"]
    g.append(rrect(cx, fx - FOOT["w"] / 2, fx + FOOT["w"] / 2, 0, FOOT["h"], 0.055, fill="url(#bodyR)"))
    g.append(circ(cx, hx, HIP["z"], HIP["r"]))
    # brazo
    sh = P(cx, side * SHOULDER["x"], SHOULDER["z"])
    el = P(cx, side * ELBOW[0], ELBOW[1])
    wr = P(cx, side * WRIST[0], WRIST[1])
    g.append(seg_px(sh, el, UPPER["r"] * S))
    g.append(seg_px(el, wr, FORE["r0"] * S, FORE["r1"] * S))
    g.append(circ(cx, side * ELBOW[0], ELBOW[1], ELBOW_R))
    g.append(hand_edge(cx, side))
    g.append(circ(cx, side * SHOULDER["x"], SHOULDER["z"], SHOULDER["r"], fill="url(#bodyR)", stroke=LINE))
    # oreja
    g.append(rrect(cx, side * EAR["x"] - EAR["t"] / 2 * (1 if side > 0 else 1), side * EAR["x"] + EAR["t"] / 2,
                   HEAD["z"] - EAR["r"], HEAD["z"] + EAR["r"], 0.025, fill="url(#darkR)", stroke=DLINE)
               if side > 0 else
               rrect(cx, side * EAR["x"] - EAR["t"] / 2, side * EAR["x"] + EAR["t"] / 2,
                     HEAD["z"] - EAR["r"], HEAD["z"] + EAR["r"], 0.025, fill="url(#darkR)", stroke=DLINE))
    return "".join(g)


def core_front_back(cx, back=False):
    g = []
    g.append(rrect(cx, -NECK["r"], NECK["r"], NECK["z0"], NECK["z1"], 0.015, fill="url(#dark)", stroke=DLINE))
    g.append(trap(cx, PELVIS["w_top"], PELVIS["w_bot"], PELVIS["z0"], PELVIS["z1"], 0.03))
    g.append(rrect(cx, -BELT["w"] / 2, BELT["w"] / 2, BELT["z0"], BELT["z1"], 0.017, fill="url(#dark)", stroke=DLINE))
    g.append(trap(cx, TORSO["w_top"], TORSO["w_bot"], TORSO["z0"], TORSO["z1"], TORSO["r"]))
    if not back:
        x, y = P(cx, 0, LED["z"])
        g.append(f'<circle cx="{x}" cy="{y}" r="{LED["r"] * S}" fill="{ACCENT}" filter="url(#glow)"/>')
    else:
        g.append(rrect(cx, -0.08, 0.08, 0.84, 0.98, 0.02, fill="#D9DDE3"))
        for z in (0.875, 0.91, 0.945):
            a_, b_ = P(cx, -0.06, z), P(cx, 0.06, z)
            g.append(f'<line x1="{a_[0]}" y1="{a_[1]}" x2="{b_[0]}" y2="{b_[1]}" stroke="#7D8590" stroke-width="3" stroke-linecap="round"/>')
    for side in (-1, 1):
        g.append(limbs(cx, side, "back" if back else "front"))
    hw, hh = HEAD["w"], HEAD["h"]
    g.append(rrect(cx, -hw / 2, hw / 2, HEAD["z"] - hh / 2, HEAD["z"] + hh / 2, HEAD["r"], fill="url(#bodyR)"))
    if not back:
        sw, sh = SCREEN["w"], SCREEN["h"]
        x0, y0 = P(cx, -sw / 2, SCREEN["z"] + sh / 2)
        g.append(rrect(cx, -sw / 2, sw / 2, SCREEN["z"] - sh / 2, SCREEN["z"] + sh / 2, SCREEN["r"],
                       fill="url(#screen)", stroke=DLINE))
        gx, gy = P(cx, -0.05, SCREEN["z"] + 0.135)
        g.append(f'<ellipse cx="{gx}" cy="{gy}" rx="{0.14 * S}" ry="{0.028 * S}" fill="url(#gloss)"/>')
        g.append(face(x0, y0, sw * S, sh * S))
    else:
        g.append(rrect(cx, -0.20, 0.20, 1.20, 1.50, 0.12, fill="none"))
        for i in range(-2, 3):
            x, y = P(cx, i * 0.035, 1.25)
            g.append(f'<circle cx="{x}" cy="{y}" r="5" fill="#9AA2AD"/>')
    return "".join(g)


def side_view(cx):
    g = []
    hd = HEAD["d"]
    # pierna (pie primero)
    g.append(f'<path d="M {P(cx, FOOT["y_front"] + 0.06, 0)[0]:.1f} {P(cx, 0, 0)[1]:.1f} '
             f'L {P(cx, FOOT["y_back"] - 0.05, 0)[0]:.1f} {P(cx, 0, 0)[1]:.1f} '
             f'Q {P(cx, FOOT["y_back"], 0)[0]:.1f} {P(cx, 0, 0)[1]:.1f} {P(cx, FOOT["y_back"], 0.05)[0]:.1f} {P(cx, 0, 0.05)[1]:.1f} '
             f'Q {P(cx, FOOT["y_back"], FOOT["h"])[0]:.1f} {P(cx, 0, FOOT["h"])[1]:.1f} {P(cx, 0.04, FOOT["h"])[0]:.1f} {P(cx, 0, FOOT["h"])[1]:.1f} '
             f'L {P(cx, -0.04, FOOT["h"])[0]:.1f} {P(cx, 0, FOOT["h"])[1]:.1f} '
             f'Q {P(cx, FOOT["y_front"], FOOT["h"] * 0.9)[0]:.1f} {P(cx, 0, FOOT["h"] * 0.9)[1]:.1f} {P(cx, FOOT["y_front"], 0.035)[0]:.1f} {P(cx, 0, 0.035)[1]:.1f} '
             f'Q {P(cx, FOOT["y_front"], 0)[0]:.1f} {P(cx, 0, 0)[1]:.1f} {P(cx, FOOT["y_front"] + 0.06, 0)[0]:.1f} {P(cx, 0, 0)[1]:.1f} Z" '
             f'fill="url(#bodyR)" {LINE}/>')
    g.append(seg_px(P(cx, 0, THIGH["z0"]), P(cx, 0, THIGH["z1"]), THIGH["r"] * S))
    g.append(seg_px(P(cx, 0, SHIN["z0"]), P(cx, 0, SHIN["z1"]), SHIN["r0"] * S, SHIN["r1"] * S))
    g.append(circ(cx, 0, KNEE["z"], KNEE["r"]))
    g.append(circ(cx, 0, HIP["z"], HIP["r"]))
    # nucleo
    g.append(rrect(cx, -NECK["r"], NECK["r"], NECK["z0"], NECK["z1"], 0.015, fill="url(#dark)", stroke=DLINE))
    g.append(trap(cx, PELVIS["d"], PELVIS["d"] * 0.85, PELVIS["z0"], PELVIS["z1"], 0.035, off_bot=0.01))
    g.append(rrect(cx, -BELT["d"] / 2, BELT["d"] / 2, BELT["z0"], BELT["z1"], 0.017, fill="url(#dark)", stroke=DLINE))
    g.append(trap(cx, TORSO["d_top"], TORSO["d_bot"], TORSO["z0"], TORSO["z1"], TORSO["r"]))
    # brazo (en el plano coronal: en lateral se ve vertical sobre el torso)
    sh, el, wr = P(cx, 0, SHOULDER["z"]), P(cx, 0, ELBOW[1]), P(cx, 0, WRIST[1])
    g.append(seg_px(sh, el, UPPER["r"] * S))
    g.append(seg_px(el, wr, FORE["r0"] * S, FORE["r1"] * S))
    g.append(circ(cx, 0, ELBOW[1], ELBOW_R))
    # mano de dorso: palma 0.08 ancho (Y), pulgar hacia delante (-Y)
    pw, pl = HAND["palm_W"] * S, HAND["palm_L"] * S
    fr, fl = HAND["fing_r"] * S, HAND["fing_L"] * S
    hcos = math.cos(a)  # longitud proyectada en Z
    g.append(f'<g transform="translate({wr[0]:.1f},{wr[1] - 4:.1f}) scale(1,{hcos:.3f})">')
    g.append(seg_px((-pw * 0.42, pl * 0.35), (-pw * 0.42 - 16, pl * 0.35 + 22), HAND["thumb_r"] * S))
    g.append(f'<rect x="{-pw / 2:.1f}" y="0" width="{pw:.1f}" height="{pl:.1f}" rx="{pw * 0.32:.1f}" fill="url(#body)" {LINE}/>')
    for fx in (-pw * 0.22, pw * 0.22):
        g.append(seg_px((fx, pl - 2), (fx, pl + fl - fr), fr))
    g.append("</g>")
    g.append(circ(cx, 0, SHOULDER["z"], SHOULDER["r"], fill="url(#bodyR)", stroke=LINE))
    # cabeza
    g.append(rrect(cx, -hd / 2, hd / 2, HEAD["z"] - HEAD["h"] / 2, HEAD["z"] + HEAD["h"] / 2, 0.17, fill="url(#bodyR)"))
    # canto de la pantalla (ligeramente abombada)
    sz0, sz1 = SCREEN["z"] - SCREEN["h"] / 2, SCREEN["z"] + SCREEN["h"] / 2
    t0, t1 = P(cx, -hd / 2 + 0.012, sz1), P(cx, -hd / 2 + 0.012, sz0)
    bx = P(cx, -hd / 2 - 0.02, 0)[0]
    g.append(f'<path d="M {t0[0]:.1f} {t0[1]:.1f} Q {bx:.1f} {(t0[1] + t1[1]) / 2:.1f} {t1[0]:.1f} {t1[1]:.1f}" '
             f'fill="none" stroke="#0B0D10" stroke-width="9" stroke-linecap="round"/>')
    g.append(circ(cx, 0.0, HEAD["z"], EAR["r"]))
    g.append(circ(cx, 0.0, HEAD["z"], EAR["r"] * 0.5, fill="url(#bodyR)", stroke=LINE))
    return "".join(g)


# ---------------- anotaciones ----------------

def guides():
    levels = [(HEIGHT, "1.60 tope cabeza"), (HEAD["z"] - HEAD["h"] / 2, "1.12 base cabeza"),
              (TORSO["z1"], "1.07 hombros/torso"), (TORSO["z0"], "0.73 cintura"),
              (HIP["z"], "0.585 cadera"), (KNEE["z"], "0.35 rodilla"), (FOOT["h"], "0.11 tobillo"), (0, "0.00 suelo")]
    g = []
    for z, lbl in levels:
        y = GROUND - z * S
        g.append(f'<line x1="20" y1="{y}" x2="1710" y2="{y}" stroke="#7FA7C9" stroke-width="1" stroke-dasharray="6 6" opacity="0.7"/>')
        g.append(f'<text x="20" y="{y - 5}" font-family="sans-serif" font-size="14" fill="#4A6A88">{lbl}</text>')
    return "".join(g)


def dim_h(x0, x1, y, txt):
    return (f'<g stroke="#C2410C" stroke-width="1.5" fill="#C2410C" font-family="sans-serif" font-size="15">'
            f'<line x1="{x0}" y1="{y}" x2="{x1}" y2="{y}"/>'
            f'<line x1="{x0}" y1="{y - 7}" x2="{x0}" y2="{y + 7}"/><line x1="{x1}" y1="{y - 7}" x2="{x1}" y2="{y + 7}"/>'
            f'<text x="{(x0 + x1) / 2}" y="{y - 8}" text-anchor="middle" stroke="none">{txt}</text></g>')


def dim_v(x, y0, y1, txt):
    return (f'<g stroke="#C2410C" stroke-width="1.5" fill="#C2410C" font-family="sans-serif" font-size="15">'
            f'<line x1="{x}" y1="{y0}" x2="{x}" y2="{y1}"/>'
            f'<line x1="{x - 7}" y1="{y0}" x2="{x + 7}" y2="{y0}"/><line x1="{x - 7}" y1="{y1}" x2="{x + 7}" y2="{y1}"/>'
            f'<text x="{x + 10}" y="{(y0 + y1) / 2 + 5}" stroke="none">{txt}</text></g>')


def label(x, y, txt, size=24, weight=700, anchor="middle", fill="#2A2E35"):
    return (f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="sans-serif" font-size="{size}" '
            f'font-weight="{weight}" fill="{fill}">{txt}</text>')


def dims():
    g = []
    hy = GROUND - (HEAD["z"] + HEAD["h"] / 2) * S - 18
    g.append(dim_h(CX_FRONT - HEAD["w"] / 2 * S, CX_FRONT + HEAD["w"] / 2 * S, hy, "0.60"))
    g.append(dim_h(CX_SIDE - HEAD["d"] / 2 * S, CX_SIDE + HEAD["d"] / 2 * S, hy, "0.46"))
    g.append(dim_v(CX_FRONT + 215, GROUND - (HEAD["z"] + HEAD["h"] / 2) * S, GROUND - (HEAD["z"] - HEAD["h"] / 2) * S, "0.48"))
    ty = GROUND - TORSO["z1"] * S - 12
    by = GROUND - BELT["z0"] * S + 2
    g.append(dim_h(CX_BACK - TORSO["w_top"] / 2 * S, CX_BACK + TORSO["w_top"] / 2 * S, ty + 4, ""))
    g.append(label(CX_BACK + TORSO["w_top"] / 2 * S + 12, ty - 2, "0.40 (base 0.34)", 15, 400, "start", "#C2410C"))
    g.append(dim_h(CX_SIDE - TORSO["d_top"] / 2 * S, CX_SIDE + TORSO["d_top"] / 2 * S, ty + 4, ""))
    g.append(label(CX_SIDE + TORSO["d_top"] / 2 * S + 40, ty - 2, "prof. 0.26", 15, 400, "start", "#C2410C"))
    g.append(dim_h(CX_SIDE + FOOT["y_front"] * S, CX_SIDE + FOOT["y_back"] * S, GROUND + 26, "pie 0.26"))
    g.append(dim_h(CX_FRONT + (FOOT["x"] - FOOT["w"] / 2) * S, CX_FRONT + (FOOT["x"] + FOOT["w"] / 2) * S, GROUND + 26, "0.16"))
    g.append(dim_v(CX_BACK + 260, GROUND - HEIGHT * S, GROUND, "1.60 total"))
    # angulo brazo
    sx, sy = P(CX_FRONT, -SHOULDER["x"], SHOULDER["z"])
    g.append(f'<line x1="{sx}" y1="{sy}" x2="{sx}" y2="{sy + 150}" stroke="#C2410C" stroke-dasharray="4 4"/>')
    g.append(label(sx - 30, sy + 150, "35°", 15, 400, "end", "#C2410C"))
    return "".join(g)


def screen_panel(x, y):
    sw, sh = 470, 470 * SCREEN["h"] / SCREEN["w"]
    g = [label(x + sw / 2, y - 18, "Pantalla FaceScreen (0.50 × 0.34, ratio 1.47:1)", 20)]
    g.append(f'<rect x="{x - 14}" y="{y - 14}" width="{sw + 28}" height="{sh + 28}" rx="{sh * 0.5}" fill="url(#bodyR)" {LINE}/>')
    g.append(f'<rect x="{x}" y="{y}" width="{sw}" height="{sh}" rx="{sh * 0.44}" fill="url(#screen)" {DLINE}/>')
    g.append(face(x, y, sw, sh, "neutral", "REST"))
    g.append(f'<g font-family="monospace" font-size="13" fill="#A9B0BA">'
             f'<text x="{x + 10}" y="{y + sh - 8}">UV (0,0)</text>'
             f'<text x="{x + sw - 10}" y="{y + 18}" text-anchor="end">UV (1,1)</text></g>')
    g.append(label(x + sw / 2, y + sh + 34, "ejemplo: ojos neutral · boca REST", 15, 400, fill="#5A616B"))
    # miniaturas de estados
    tw, th = 106, 106 * SCREEN["h"] / SCREEN["w"]
    states = [("listening", "O", "listening · O"), ("thinking", "dots", "thinking"),
              ("happy", "A", "happy · A"), ("neutral", "E", "neutral · E")]
    for i, (e, m, t) in enumerate(states):
        tx, ty = x + i * (tw + 15), y + sh + 60
        g.append(f'<rect x="{tx}" y="{ty}" width="{tw}" height="{th}" rx="{th * 0.44}" fill="url(#screen)" {DLINE}/>')
        g.append(face(tx, ty, tw, th, e, m, glow=False))
        g.append(label(tx + tw / 2, ty + th + 18, t, 13, 400, fill="#5A616B"))
    return "".join(g)


def hand_panel(x, y):
    k = 1000  # px/u
    pw, pl, pt = HAND["palm_W"] * k, HAND["palm_L"] * k, HAND["palm_T"] * k
    fr, fl = HAND["fing_r"] * k, HAND["fing_L"] * k
    tr, tl = HAND["thumb_r"] * k, HAND["thumb_L"] * k
    g = [label(x + 150, y - 18, "Mano (pulgar + 2 dedos), escala ×2", 18)]
    # dorso
    ox = x + 80
    g.append(seg_px((ox - pw * 0.42, y + pl * 0.35), (ox - pw * 0.42 - tl * 0.7, y + pl * 0.35 + tl * 0.7), tr))
    g.append(f'<rect x="{ox - pw / 2}" y="{y}" width="{pw}" height="{pl}" rx="{pw * 0.32}" fill="url(#body)" {LINE}/>')
    for fx in (-pw * 0.22, pw * 0.22):
        g.append(seg_px((ox + fx, y + pl - 3), (ox + fx, y + pl + fl - fr), fr))
    g.append(label(ox, y + pl + fl + 30, "dorso", 14, 400, fill="#5A616B"))
    # canto
    ox = x + 220
    g.append(f'<rect x="{ox - pt / 2}" y="{y}" width="{pt}" height="{pl}" rx="{pt * 0.45}" fill="url(#body)" {LINE}/>')
    g.append(seg_px((ox, y + pl - 3), (ox, y + pl + fl - fr), fr))
    g.append(seg_px((ox + pt * 0.3, y + pl * 0.3), (ox + pt * 0.3 + tl * 0.55, y + pl * 0.3 + tl * 0.8), tr))
    g.append(label(ox, y + pl + fl + 30, "canto (palma → muslo)", 14, 400, fill="#5A616B"))
    return "".join(g)


def table(x, y):
    rows = [
        ("Cabeza", "0.60 × 0.46 × 0.48, radio 0.20"),
        ("Pantalla", "0.50 × 0.34, radio 0.15, abombada"),
        ("Orejas", "disco r 0.075, grosor 0.05"),
        ("Cuello", "cil. r 0.05, z 1.05–1.13"),
        ("Torso", "0.40→0.34 × 0.26, z 0.73–1.07"),
        ("Cinturón", "0.22 × 0.18, z 0.695–0.73"),
        ("Pelvis", "0.27→0.22 × 0.21, z 0.58–0.695"),
        ("Brazo / antebrazo", "0.17 r 0.042 / 0.15 r 0.04"),
        ("Mano", "palma 0.075 × 0.08 × 0.045"),
        ("Muslo / pierna", "0.20 r 0.057 / 0.22 r 0.055"),
        ("Pie", "0.16 × 0.26 × 0.11"),
        ("Articulaciones", "esferas gris oscuro r 0.03–0.04"),
    ]
    g = [label(x, y, "Medidas (unidades Blender)", 18, 700, "start")]
    for i, (k, v) in enumerate(rows):
        yy = y + 26 + i * 22
        g.append(label(x, yy, k, 14, 700, "start", "#2A2E35"))
        g.append(label(x + 150, yy, v, 14, 400, "start", "#4A505A"))
    yy = y + 26 + len(rows) * 22 + 12
    g.append(f'<rect x="{x}" y="{yy - 13}" width="16" height="16" fill="#F2F3F5" {LINE}/>'
             + label(x + 22, yy, "cuerpo blanco mate", 13, 400, "start"))
    g.append(f'<rect x="{x + 165}" y="{yy - 13}" width="16" height="16" fill="#3A3F47"/>'
             + label(x + 187, yy, "articulaciones", 13, 400, "start"))
    g.append(f'<rect x="{x + 300}" y="{yy - 13}" width="16" height="16" fill="#000"/>'
             + label(x + 322, yy, "pantalla", 13, 400, "start"))
    g.append(f'<rect x="{x + 390}" y="{yy - 13}" width="16" height="16" fill="{ACCENT}"/>'
             + label(x + 412, yy, ACCENT, 13, 400, "start"))
    return "".join(g)


def build():
    body = [f'<rect width="{W}" height="{H}" fill="#ECEFF3"/>',
            label(W / 2, 46, "Robin · Turnaround A-pose (variante B · Chibi)", 30),
            guides()]
    for cx in (CX_FRONT, CX_SIDE, CX_BACK):
        body.append(f'<ellipse cx="{cx}" cy="{GROUND + 2}" rx="150" ry="12" fill="#000" opacity="0.08"/>')
    body.append(core_front_back(CX_FRONT))
    body.append(side_view(CX_SIDE))
    body.append(core_front_back(CX_BACK, back=True))
    body.append(dims())
    for cx, t in ((CX_FRONT, "FRONTAL"), (CX_SIDE, "LATERAL (frente ←)"), (CX_BACK, "TRASERA")):
        body.append(label(cx, GROUND + 70, t, 22))
    body.append(f'<line x1="1730" y1="80" x2="1730" y2="{H - 30}" stroke="#C8CDD4" stroke-width="2"/>')
    body.append(screen_panel(1800, 130))
    body.append(hand_panel(1780, 700))
    body.append(table(2100, 680))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
            + DEFS + "".join(body) + "</svg>\n")


if __name__ == "__main__":
    (OUT / "turnaround.svg").write_text(build())
    print("ok")
