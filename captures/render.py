# -*- coding: utf-8 -*-
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import ImageFormatter
from PIL import Image, ImageDraw, ImageFont

FILES = [
    ("snippet_1_raw_to_D.py", "raw_to_D.png", "원시데이터(raw telemetry) → 열화추세 → D(검출도) 산출 공식"),
    ("snippet_2_SOD_formula.py", "SOD_formula.png", "S · O · D 산출 공식"),
    ("snippet_3_IPS_linkage.py", "IPS_linkage.png", "IPS 연계 코드 (FMECA → RCM → LORA → 보급소요 → IETM → ECP)"),
]

TITLEBAR_H = 64
PAD = 28

for src, out, title in FILES:
    code = open(src, encoding="utf-8").read()
    fmt = ImageFormatter(
        style="one-dark",
        font_name="Malgun Gothic",
        font_size=17,
        line_numbers=True,
        line_number_bg="#282c34",
        line_number_fg="#5c6370",
        line_number_pad=14,
        line_pad=5,
        image_pad=PAD,
    )
    img_bytes = highlight(code, PythonLexer(), fmt)
    with open("_tmp.png", "wb") as f:
        f.write(img_bytes)
    code_img = Image.open("_tmp.png").convert("RGB")
    w, h = code_img.size

    canvas = Image.new("RGB", (w, h + TITLEBAR_H), "#21252b")
    draw = ImageDraw.Draw(canvas)
    # traffic-light dots
    for i, c in enumerate(["#ec6a5f", "#f4bf4f", "#61c454"]):
        draw.ellipse([PAD + i * 22, TITLEBAR_H // 2 - 7, PAD + i * 22 + 14, TITLEBAR_H // 2 + 7], fill=c)
    try:
        font = ImageFont.truetype("malgunbd.ttf", 18)
    except Exception:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), title, font=font)
    tw = bbox[2] - bbox[0]
    draw.text(((w - tw) / 2, TITLEBAR_H // 2 - 11), title, fill="#abb2bf", font=font)
    canvas.paste(code_img, (0, TITLEBAR_H))
    canvas.save(out)
    print(out, canvas.size)

import os
os.remove("_tmp.png")
