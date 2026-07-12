#!/usr/bin/env python3
from PIL import Image, ImageDraw, ImageFont
import os, sys

OUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'artifacts', 'HCS.iconset')
os.makedirs(OUT_DIR, exist_ok=True)

sizes = {
    'icon_16x16.png': 16,
    'icon_16x16@2x.png': 32,
    'icon_32x32.png': 32,
    'icon_32x32@2x.png': 64,
    'icon_128x128.png': 128,
    'icon_128x128@2x.png': 256,
    'icon_256x256.png': 256,
    'icon_256x256@2x.png': 512,
    'icon_512x512.png': 512,
    'icon_512x512@2x.png': 1024,
}

# Try to find a useful system font
def find_font():
    candidates = [
        '/Library/Fonts/Arial.ttf',
        '/Library/Fonts/Arial Unicode.ttf',
        '/Library/Fonts/Helvetica.ttf',
        '/System/Library/Fonts/SFNS.ttf',
        '/System/Library/Fonts/SFNSDisplay.ttf',
        '/System/Library/Fonts/SFNSText.ttf'
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None

font_path = find_font()

for name, size in sizes.items():
    img = Image.new('RGBA', (size, size), (0,0,0,0))
    draw = ImageDraw.Draw(img)

    # vertical gradient background
    top = (18, 92, 255)
    bottom = (32, 170, 243)
    for y in range(size):
        t = y / max(1, size - 1)
        r = int((1-t)*top[0] + t*bottom[0])
        g = int((1-t)*top[1] + t*bottom[1])
        b = int((1-t)*top[2] + t*bottom[2])
        draw.line([(0,y),(size,y)], fill=(r,g,b))

    # draw subtle white glow circle
    cx = cy = size // 2
    radius = int(size * 0.38)
    glow = Image.new('RGBA', (size, size), (0,0,0,0))
    gdraw = ImageDraw.Draw(glow)
    gdraw.ellipse((cx-radius, cy-radius, cx+radius, cy+radius), fill=(255,255,255,50))
    img = Image.alpha_composite(img, glow)

    # Draw letter H# centered
    if font_path:
        # scale font to fit
        font_size = int(size * 0.6)
        try:
            font = ImageFont.truetype(font_path, font_size)
        except Exception:
            font = ImageFont.load_default()
    else:
        font = ImageFont.load_default()

    text = 'H#'
    try:
        bbox = draw.textbbox((0,0), text, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
    except Exception:
        try:
            w, h = font.getsize(text)
        except Exception:
            w, h = draw.textsize(text, font=font)
    draw.text(((size-w)/2, (size-h)/2), text, font=font, fill=(255,255,255,255))

    out_path = os.path.join(OUT_DIR, name)
    img.save(out_path, format='PNG')
    print('Wrote', out_path)

print('Iconset created at', OUT_DIR)
