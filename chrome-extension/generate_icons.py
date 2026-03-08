"""
One-time script to generate RecapAI extension icons.
Run from the chrome-extension/ directory:
    python3 generate_icons.py
Requires Pillow: pip install Pillow
"""
from PIL import Image, ImageDraw, ImageFont
import os

os.makedirs("icons", exist_ok=True)

for size in [16, 48, 128]:
    img = Image.new("RGB", (size, size), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)
    font_size = max(int(size * 0.55), 8)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
    except Exception:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
        except Exception:
            font = ImageFont.load_default()
    text = "R"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = (size - tw) / 2 - bbox[0]
    y = (size - th) / 2 - bbox[1]
    draw.text((x, y), text, fill=(255, 255, 255), font=font)
    out = f"icons/icon{size}.png"
    img.save(out)
    print(f"Saved {out}")
