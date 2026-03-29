"""
create_icon.py
Generates icon.ico for the Spotify Playlist Rotator.
Run: python create_icon.py
Requires: pip install Pillow
"""

from PIL import Image, ImageDraw, ImageFont
import os

def make_icon():
    sizes = [256, 128, 64, 48, 32, 16]
    frames = []

    for size in sizes:
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        padding = int(size * 0.08)
        r = size - padding * 2

        # Dark background circle
        draw.ellipse(
            [padding, padding, padding + r, padding + r],
            fill=(15, 15, 20, 255)
        )

        # Green ring
        ring = max(2, int(size * 0.04))
        draw.ellipse(
            [padding, padding, padding + r, padding + r],
            outline=(29, 185, 84, 255),
            width=ring
        )

        # Inner green glow ring (slightly smaller, translucent)
        glow_pad = padding + ring + max(1, int(size * 0.02))
        draw.ellipse(
            [glow_pad, glow_pad, size - glow_pad, size - glow_pad],
            outline=(29, 185, 84, 80),
            width=max(1, ring // 2)
        )

        # Music note ♫ drawn as simple shapes (works at all sizes)
        cx, cy = size // 2, size // 2
        note_scale = size / 256.0

        # Note stem
        stem_x = int(cx + 18 * note_scale)
        stem_top = int(cy - 38 * note_scale)
        stem_bot = int(cy + 12 * note_scale)
        stem_w = max(2, int(6 * note_scale))
        draw.rectangle(
            [stem_x, stem_top, stem_x + stem_w, stem_bot],
            fill=(29, 185, 84, 255)
        )

        # Note head (ellipse)
        head_w = int(22 * note_scale)
        head_h = int(16 * note_scale)
        hx = stem_x - head_w + stem_w // 2
        hy = stem_bot - head_h // 2
        draw.ellipse(
            [hx, hy, hx + head_w, hy + head_h],
            fill=(29, 185, 84, 255)
        )

        # Flag on stem
        flag_x2 = int(stem_x + stem_w + 20 * note_scale)
        flag_y2 = int(stem_top + 22 * note_scale)
        flag_w = max(2, int(4 * note_scale))
        draw.line(
            [(stem_x + stem_w, stem_top),
             (flag_x2, stem_top + int(10 * note_scale))],
            fill=(29, 185, 84, 255), width=flag_w
        )
        draw.line(
            [(stem_x + stem_w, int(stem_top + 10 * note_scale)),
             (flag_x2, flag_y2)],
            fill=(29, 185, 84, 255), width=flag_w
        )

        frames.append(img)

    out_path = os.path.join(os.path.dirname(__file__), "icon.ico")
    frames[0].save(
        out_path,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=frames[1:]
    )
    print(f"✓ icon.ico created ({len(sizes)} sizes: {', '.join(str(s) for s in sizes)}px)")
    return out_path


if __name__ == "__main__":
    make_icon()
