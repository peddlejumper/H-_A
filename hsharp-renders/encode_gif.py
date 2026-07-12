#!/usr/bin/env python3
"""
encode_gif.py — Combine frame_NNNNNN.png files in a directory
into an animated GIF.  Used as a post-processing step for the
H# raytracer window-recording demo (no ffmpeg required).

Usage:
    python3 encode_gif.py <frames_dir> <out_gif> [fps]
"""
import os
import sys
from PIL import Image

if len(sys.argv) < 3:
    print("usage: encode_gif.py <frames_dir> <out_gif> [fps]", file=sys.stderr)
    sys.exit(1)

frames_dir = sys.argv[1]
out_gif    = sys.argv[2]
fps        = int(sys.argv[3]) if len(sys.argv) > 3 else 5

# Gather frames in name order.
files = sorted(f for f in os.listdir(frames_dir) if f.startswith("frame_") and f.endswith(".png"))
if not files:
    print(f"no frame_*.png files in {frames_dir}", file=sys.stderr)
    sys.exit(2)
print(f"loading {len(files)} frames from {frames_dir}...")

frames = []
for fn in files:
    img = Image.open(os.path.join(frames_dir, fn)).convert("P", palette=Image.ADAPTIVE, colors=128)
    frames.append(img)

# Resize to keep file size reasonable while preserving the JFrame detail.
target_w = 720
scaled = []
for img in frames:
    if img.width > target_w:
        ratio = target_w / img.width
        img = img.resize((target_w, int(img.height * ratio)), Image.LANCZOS)
    scaled.append(img)

duration_ms = 1000 // fps
print(f"writing {out_gif} ({len(scaled)} frames @ {fps} fps = {duration_ms} ms/frame)...")
scaled[0].save(
    out_gif,
    save_all=True,
    append_images=scaled[1:],
    duration=duration_ms,
    loop=0,
    optimize=True,
    disposal=2,
)
print(f"done -> {out_gif} ({os.path.getsize(out_gif)} bytes)")
