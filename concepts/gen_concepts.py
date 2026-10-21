"""Genera los SVG de concepto de Robin (fase 1).

Uso: python3 concepts/gen_concepts.py
Salida: concepts/concept_{a,b,c,d}.svg y concepts/overview.svg
"""
import math
from pathlib import Path

ACCENT = "#3DE0FF"  # color de acento (ojos/boca); unico punto de cambio
OUT = Path(__file__).parent
W, H = 600, 960
CX = 300
GROUND = 860

DEFS = f"""
<defs>
  <linearGradient id="body" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#C9CED6"/>
    <stop offset="0.35" stop-color="#F7F8FA"/>
    <stop offset="0.6" stop-color="#FFFFFF"/>
    <stop offset="1" stop-color="#D3D8DF"/>
  </linearGradient>
  <radialGradient id="bodyR" cx="0.4" cy="0.35" r="0.75">
    <stop offset="0" stop-color="#FFFFFF"/>
    <stop offset="0.6" stop-color="#EEF0F3"/>
    <stop offset="1" stop-color="#C3C9D1"/>
  </radialGradient>
  <linearGradient id="dark" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#2A2E35"/>
    <stop offset="0.45" stop-color="#555B65"/>
    <stop offset="1" stop-color="#2A2E35"/>
  </linearGradient>
  <radialGradient id="darkR" cx="0.4" cy="0.35" r="0.7">
    <stop offset="0" stop-color="#6A707A"/>
    <stop offset="1" stop-color="#25282E"/>
  </radialGradient>
  <radialGradient id="screen" cx="0.35" cy="0.25" r="0.9">
    <stop offset="0" stop-color="#2B3038"/>
    <stop offset="0.45" stop-color="#0B0D10"/>
    <stop offset="1" stop-color="#000000"/>
  </radialGradient>
  <linearGradient id="gloss" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#FFFFFF" stop-opacity="0.35"/>
    <stop offset="1" stop-color="#FFFFFF" stop-opacity="0"/>
  </linearGradient>
  <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
    <feGaussianBlur stdDeviation="4" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
</defs>
"""

LINE = 'stroke="#9AA2AD" stroke-width="1.5"'
DLINE = 'stroke="#1A1D22" stroke-width="1.5"'


def seg(p1, p2, r, fill="url(#body)", r2=None):
    """Capsula (rect redondeado rotado) entre dos puntos."""
    (x1, y1), (x2, y2) = p1, p2
    L = math.hypot(x2 - x1, y2 - y1)
    ang = math.degrees(math.atan2(y2 - y1, x2 - x1)) - 90
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    if r2 is None:
        return (f'<rect x="{-r}" y="{-L/2 - r}" width="{2*r}" height="{L + 2*r}" rx="{r}" '
                f'fill="{fill}" {LINE} transform="translate({mx},{my}) rotate({ang})"/>')
    # capsula conica: r arriba, r2 abajo
    h = L / 2
    d = (f"M {-r} {-h} A {r} {r} 0 0 1 {r} {-h} L {r2} {h} A {r2} {r2} 0 0 1 {-r2} {h} Z")
    return f'<path d="{d}" fill="{fill}" {LINE} transform="translate({mx},{my}) rotate({ang})"/>'


def joint(x, y, r):
    return f'<circle cx="{x}" cy="{y}" r="{r}" fill="url(#darkR)" {DLINE}/>'


def hand(x, y, ang, style, s=1.0):
    """Mano en coords locales: origen en muneca, apuntando hacia +y. Pulgar hacia +x (hacia el cuerpo)."""
    g = []
    if style == "mitten":  # pulgar + 3 dedos fusionados
        g.append('<rect x="-19" y="-4" width="38" height="34" rx="14" fill="url(#body)" ' + LINE + '/>')
        g.append('<rect x="-18" y="22" width="34" height="30" rx="15" fill="url(#body)" ' + LINE + '/>')
        g.append('<path d="M -6 30 L -6 48 M 5 30 L 5 48" stroke="#A9B0BA" stroke-width="1.5"/>')
        g.append(seg((14, 8), (27, 28), 7))
    elif style == "two":  # pulgar + 2 dedos redondos
        g.append('<ellipse cx="0" cy="14" rx="22" ry="20" fill="url(#bodyR)" ' + LINE + '/>')
        g.append(seg((-9, 28), (-10, 46), 9))
        g.append(seg((9, 28), (10, 46), 9))
        g.append(seg((16, 8), (30, 22), 8))
    elif style == "three":  # pulgar + 3 dedos gruesos
        g.append('<rect x="-21" y="-4" width="42" height="34" rx="12" fill="url(#body)" ' + LINE + '/>')
        for fx in (-13, 0, 13):
            g.append(seg((fx, 30), (fx, 46), 6.5))
        g.append(seg((18, 6), (31, 24), 7))
    elif style == "slim":  # pulgar + 2 dedos largos
        g.append('<rect x="-14" y="-4" width="28" height="32" rx="11" fill="url(#body)" ' + LINE + '/>')
        g.append(seg((-6, 28), (-7, 54), 6))
        g.append(seg((6, 28), (7, 54), 6))
        g.append(seg((12, 6), (24, 26), 5.5))
    return f'<g transform="translate({x},{y}) rotate({ang}) scale({s})">' + "".join(g) + "</g>"


def eyes_mouth(cy, ex, ew, eh, mouth_w, mouth_y, shape="pill"):
    g = [f'<g filter="url(#glow)" fill="{ACCENT}">']
    for sx in (-1, 1):
        x = CX + sx * ex
        if shape == "pill":
            g.append(f'<rect x="{x - ew/2}" y="{cy - eh/2}" width="{ew}" height="{eh}" rx="{min(ew, eh)/2}"/>')
        else:
            g.append(f'<ellipse cx="{x}" cy="{cy}" rx="{ew/2}" ry="{eh/2}"/>')
    g.append(f'<path d="M {CX - mouth_w/2} {mouth_y} Q {CX} {mouth_y + mouth_w*0.35} {CX + mouth_w/2} {mouth_y}" '
             f'fill="none" stroke="{ACCENT}" stroke-width="5" stroke-linecap="round"/>')
    g.append("</g>")
    return "".join(g)


def mirror(uid, content):
    return (f'<g id="{uid}">{content}</g>'
            f'<use href="#{uid}" transform="translate({2*CX},0) scale(-1,1)"/>')


def frame(title, subtitle, body):
    return (f'<rect width="{W}" height="{H}" fill="#ECEFF3"/>'
            f'<ellipse cx="{CX}" cy="{GROUND + 2}" rx="150" ry="16" fill="#000" opacity="0.10"/>'
            + body +
            f'<text x="{CX}" y="910" text-anchor="middle" font-family="sans-serif" font-size="30" '
            f'font-weight="700" fill="#2A2E35">{title}</text>'
            f'<text x="{CX}" y="942" text-anchor="middle" font-family="sans-serif" font-size="17" '
            f'fill="#5A616B">{subtitle}</text>')


def concept_a(p):
    """Capsula: cabeza ovalada ancha, torso en huevo, mitones."""
    half = []
    # pierna
    half.append(seg((263, 548), (258, 688), 22))
    half.append(seg((258, 700), (255, 818), 21, r2=17))
    half.append(joint(258, 694, 15))
    half.append(f'<rect x="222" y="822" width="68" height="38" rx="18" fill="url(#body)" {LINE}/>')
    half.append(joint(263, 544, 16))
    # brazo
    half.append(seg((196, 300), (152, 410), 17))
    half.append(seg((150, 420), (122, 515), 16, r2=13))
    half.append(joint(151, 415, 13))
    half.append(hand(118, 522, 18, "mitten"))
    half.append(joint(200, 292, 17))
    legs_arms = mirror(f"{p}h", "".join(half))
    torso = (f'<path d="M 300 248 C 392 248 402 300 396 342 C 388 410 350 468 300 472 '
             f'C 250 468 212 410 204 342 C 198 300 208 248 300 248 Z" fill="url(#body)" {LINE}/>'
             f'<path d="M 245 455 Q 300 490 355 455 L 360 470 Q 300 505 240 470 Z" fill="url(#dark)"/>'
             f'<path d="M 238 478 Q 300 470 362 478 L 352 532 Q 300 556 248 532 Z" fill="url(#body)" {LINE}/>')
    neck = f'<rect x="284" y="226" width="32" height="28" rx="8" fill="url(#dark)" {DLINE}/>'
    head = (f'<ellipse cx="300" cy="150" rx="108" ry="86" fill="url(#bodyR)" {LINE}/>'
            f'<ellipse cx="300" cy="156" rx="86" ry="56" fill="url(#screen)" {DLINE}/>'
            f'<ellipse cx="282" cy="124" rx="44" ry="12" fill="url(#gloss)"/>'
            + eyes_mouth(148, 34, 22, 34, 34, 178))
    return frame("A · Cápsula", "cabeza ovalada ancha, torso en huevo, mitones",
                 legs_arms + torso + neck + head)


def concept_b(p):
    """Chibi: cabeza grande, cuerpo compacto, manos de 2 dedos."""
    half = []
    half.append(seg((262, 575), (258, 680), 28))
    half.append(seg((258, 690), (256, 790), 27, r2=24))
    half.append(joint(258, 686, 18))
    half.append(f'<ellipse cx="252" cy="830" rx="44" ry="30" fill="url(#bodyR)" {LINE}/>')
    half.append(joint(262, 570, 19))
    half.append(seg((200, 362), (168, 438), 21))
    half.append(seg((166, 448), (148, 515), 20, r2=18))
    half.append(joint(167, 443, 15))
    half.append(hand(144, 522, 14, "two", 1.15))
    half.append(f'<circle cx="203" cy="354" r="25" fill="url(#bodyR)" {LINE}/>')
    half.append(f'<ellipse cx="146" cy="190" rx="16" ry="36" fill="url(#darkR)" {DLINE}/>')
    legs_arms = mirror(f"{p}h", "".join(half))
    torso = (f'<path d="M 222 330 L 378 330 Q 400 330 398 356 L 386 470 Q 382 500 352 502 '
             f'L 248 502 Q 218 500 214 470 L 202 356 Q 200 330 222 330 Z" fill="url(#body)" {LINE}/>'
             f'<circle cx="300" cy="380" r="7" fill="{ACCENT}" filter="url(#glow)"/>'
             f'<rect x="246" y="502" width="108" height="16" rx="8" fill="url(#dark)"/>'
             f'<path d="M 236 518 L 364 518 Q 372 518 370 530 L 360 566 Q 300 586 240 566 L 230 530 Q 228 518 236 518 Z" '
             f'fill="url(#body)" {LINE}/>')
    neck = f'<rect x="276" y="300" width="48" height="36" rx="10" fill="url(#dark)" {DLINE}/>'
    head = (f'<rect x="150" y="68" width="300" height="240" rx="112" fill="url(#bodyR)" {LINE}/>'
            f'<rect x="174" y="102" width="252" height="172" rx="84" fill="url(#screen)" {DLINE}/>'
            f'<ellipse cx="270" cy="124" rx="70" ry="14" fill="url(#gloss)"/>'
            + eyes_mouth(182, 52, 46, 54, 44, 226, "round"))
    return frame("B · Chibi", "cabeza grande, cuerpo compacto, manos de 2 dedos",
                 legs_arms + torso + neck + head)


def concept_c(p):
    """Casco: cabeza TV redondeada, hombros anchos, guantes de 3 dedos."""
    half = []
    half.append(seg((262, 552), (258, 668), 24))
    half.append(seg((258, 682), (254, 792), 25, r2=28))
    half.append(joint(258, 675, 16))
    half.append(f'<path d="M 214 800 L 290 800 Q 300 800 300 812 L 300 848 Q 300 860 288 860 L 208 860 '
                f'Q 196 860 198 846 L 202 812 Q 204 800 214 800 Z" fill="url(#body)" {LINE}/>')
    half.append(f'<rect x="200" y="842" width="100" height="18" rx="7" fill="url(#dark)"/>')
    half.append(joint(262, 548, 17))
    half.append(seg((172, 318), (140, 430), 19))
    half.append(seg((138, 444), (114, 538), 22, r2=19))
    half.append(joint(139, 437, 15))
    half.append(hand(110, 548, 15, "three"))
    half.append(f'<circle cx="180" cy="306" r="36" fill="url(#bodyR)" {LINE}/>')
    half.append(f'<circle cx="182" cy="160" r="22" fill="url(#darkR)" {DLINE}/>')
    half.append(f'<circle cx="180" cy="160" r="10" fill="url(#bodyR)"/>')
    legs_arms = mirror(f"{p}h", "".join(half))
    torso = (f'<path d="M 206 276 L 394 276 Q 418 276 414 302 L 386 450 Q 380 474 356 474 L 244 474 '
             f'Q 220 474 214 450 L 186 302 Q 182 276 206 276 Z" fill="url(#body)" {LINE}/>'
             f'<path d="M 252 312 L 348 312 Q 356 312 354 322 L 346 382 Q 344 392 334 392 L 266 392 '
             f'Q 256 392 254 382 L 246 322 Q 244 312 252 312 Z" fill="none" stroke="#A9B0BA" stroke-width="2"/>'
             f'<rect x="232" y="476" width="136" height="20" rx="6" fill="url(#dark)"/>'
             f'<path d="M 232 498 L 368 498 L 362 548 Q 300 566 238 548 Z" fill="url(#body)" {LINE}/>')
    neck = (f'<rect x="270" y="244" width="60" height="36" rx="8" fill="url(#dark)" {DLINE}/>'
            '<path d="M 272 256 L 328 256 M 272 268 L 328 268" stroke="#1A1D22" stroke-width="2"/>')
    head = (f'<rect x="192" y="64" width="216" height="186" rx="56" fill="url(#bodyR)" {LINE}/>'
            f'<rect x="210" y="84" width="180" height="140" rx="40" fill="#2A2E35"/>'
            f'<rect x="216" y="90" width="168" height="128" rx="36" fill="url(#screen)" {DLINE}/>'
            f'<ellipse cx="280" cy="106" rx="56" ry="10" fill="url(#gloss)"/>'
            + eyes_mouth(146, 38, 30, 40, 36, 182))
    return frame("C · Casco", "cabeza TV redondeada, hombros anchos, guantes de 3 dedos",
                 legs_arms + torso + neck + head)


def concept_d(p):
    """Esbelto: cabeza oval vertical con pantalla total, cintura visible, extremidades largas."""
    half = []
    half.append(seg((266, 552), (262, 690), 19))
    half.append(seg((262, 702), (259, 820), 18, r2=14))
    half.append(joint(262, 696, 13))
    half.append(f'<path d="M 236 824 Q 258 814 282 824 L 286 852 Q 286 860 276 860 L 232 860 Q 222 860 224 850 Z" '
                f'fill="url(#body)" {LINE}/>')
    half.append(joint(266, 548, 14))
    half.append(seg((204, 322), (164, 446), 13))
    half.append(seg((162, 458), (132, 566), 12.5, r2=10))
    half.append(joint(163, 452, 11))
    half.append(hand(129, 572, 16, "slim"))
    half.append(joint(206, 316, 15))
    legs_arms = mirror(f"{p}h", "".join(half))
    torso = (f'<path d="M 216 298 Q 300 284 384 298 Q 400 302 396 322 L 362 418 Q 352 436 330 438 '
             f'L 270 438 Q 248 436 238 418 L 204 322 Q 200 302 216 298 Z" fill="url(#body)" {LINE}/>'
             f'<rect x="280" y="432" width="40" height="44" rx="10" fill="url(#dark)" {DLINE}/>'
             '<path d="M 282 448 L 318 448 M 282 461 L 318 461" stroke="#1A1D22" stroke-width="2"/>'
             f'<path d="M 244 474 Q 300 466 356 474 Q 364 476 362 488 L 348 534 Q 300 556 252 534 L 238 488 '
             f'Q 236 476 244 474 Z" fill="url(#body)" {LINE}/>')
    neck = f'<rect x="288" y="250" width="24" height="46" rx="8" fill="url(#dark)" {DLINE}/>'
    head = (f'<ellipse cx="300" cy="158" rx="86" ry="100" fill="url(#bodyR)" {LINE}/>'
            f'<ellipse cx="300" cy="162" rx="72" ry="80" fill="url(#screen)" {DLINE}/>'
            f'<ellipse cx="284" cy="108" rx="38" ry="14" fill="url(#gloss)"/>'
            + eyes_mouth(150, 28, 20, 36, 30, 190))
    return frame("D · Esbelto", "pantalla total, cintura visible, extremidades largas",
                 legs_arms + torso + neck + head)


def svg(inner, w=W, h=H):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            + DEFS + inner + "</svg>\n")


if __name__ == "__main__":
    concepts = {"a": concept_a, "b": concept_b, "c": concept_c, "d": concept_d}
    parts = []
    for i, (k, fn) in enumerate(concepts.items()):
        (OUT / f"concept_{k}.svg").write_text(svg(fn(k)))
        parts.append(f'<g transform="translate({i * W},0)">{fn("o" + k)}</g>')
    (OUT / "overview.svg").write_text(svg("".join(parts), W * 4, H))
    print("ok")
