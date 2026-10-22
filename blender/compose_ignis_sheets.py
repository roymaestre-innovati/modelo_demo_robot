"""Compone las hojas de poses de Ignis (Python del sistema con Pillow, no Blender).

Uso: python3 blender/compose_ignis_sheets.py
Lee blender/renders/ignis/poses/*.png y escribe <clip>_sheet.png y mouths_sheet.png.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

D = Path(__file__).resolve().parent / "renders" / "ignis" / "poses"
FONT = "/usr/share/fonts/open-sans/OpenSans-Semibold.ttf"


def sheet(files, labels, cols, out, scale=0.6):
    ims = [Image.open(f).convert("RGB") for f in files]
    w, h = int(ims[0].width * scale), int(ims[0].height * scale)
    rows = (len(ims) + cols - 1) // cols
    S = Image.new("RGB", (cols * w, rows * (h + 34)), (27, 30, 35))
    dr = ImageDraw.Draw(S)
    try:
        f = ImageFont.truetype(FONT, 22)
    except OSError:
        f = ImageFont.load_default()
    for i, (im, lab) in enumerate(zip(ims, labels)):
        x, y = (i % cols) * w, (i // cols) * (h + 34)
        S.paste(im.resize((w, h)), (x, y))
        dr.text((x + w / 2, y + h + 17), lab, fill=(220, 226, 234), font=f, anchor="mm")
    S.save(out)
    print(out)


DUR = {"idle": 5.0, "talk_1": 4.0, "talk_2": 4.0, "talk_3": 4.6}
for clip, dur in DUR.items():
    files = [D / f"{clip}_{i}.png" for i in range(6)]
    sheet(files, [f"{clip} · {i * dur / 6:.2f} s" for i in range(6)], 3, D / f"{clip}_sheet.png")
sheet([D / f"mouth_{m}.png" for m in ("REST", "A", "O", "E")], ["REST", "A", "O", "E"], 4, D / "mouths_sheet.png")
