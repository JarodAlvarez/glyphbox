#!/usr/bin/env python3
"""
img-to-sprites.py  —  Convert a PNG/JPG image into GLYPHBOX sprites.txt format.

Each 8×8 block of pixels becomes one sprite entry.
The image is scaled to the nearest multiple of 8 in both dimensions,
then split into tiles and written as rows of 0/1 characters.

Usage:
    python tools/img-to-sprites.py image.png                  # auto output
    python tools/img-to-sprites.py image.png -o sprites.txt   # specific output
    python tools/img-to-sprites.py image.png --start 4        # write from sprite index 4
    python tools/img-to-sprites.py image.png --bg 101,255,0   # specify background colour
    python tools/img-to-sprites.py image.png --invert         # swap foreground/background
    python tools/img-to-sprites.py image.png --threshold 180  # brightness cut-off (0-255)
"""

import argparse
import sys
from pathlib import Path

TOTAL_SPRITES = 128
SPRITE_W      = 8
SPRITE_H      = 8

BLANK_SPRITE  = ["00000000"] * SPRITE_H


def classify_pixel(r, g, b, a, bg_rgb, threshold, invert):
    """Return 1 (white) or 0 (black) for one RGBA pixel."""
    # Transparent pixels → background colour
    if a < 64:
        return 1 if invert else 0

    # If a background colour is specified, match it
    if bg_rgb is not None:
        br, bg, bb = bg_rgb
        if abs(r - br) < 40 and abs(g - bg) < 40 and abs(b - bb) < 40:
            return 1 if invert else 0

    # Fall back to brightness threshold
    brightness = (r + g + b) / 3
    lit = brightness > threshold
    return (0 if lit else 1) if invert else (1 if lit else 0)


def image_to_tiles(img, bg_rgb, threshold, invert):
    """Convert a PIL Image to a list of 8×8 tile pixel grids (list of 8-char strings)."""
    from PIL import Image as _Image

    # Round dimensions down to nearest 8
    tw = (img.width  // SPRITE_W) * SPRITE_W
    th = (img.height // SPRITE_H) * SPRITE_H
    if tw == 0 or th == 0:
        sys.exit("Image is smaller than one 8×8 sprite.")
    img = img.crop((0, 0, tw, th)).convert("RGBA")

    tiles = []
    for ty in range(th // SPRITE_H):
        for tx in range(tw // SPRITE_W):
            rows = []
            for py in range(SPRITE_H):
                row = ""
                for px in range(SPRITE_W):
                    sx, sy = tx * SPRITE_W + px, ty * SPRITE_H + py
                    row += str(classify_pixel(*img.getpixel((sx, sy)),
                                             bg_rgb, threshold, invert))
                rows.append(row)
            tiles.append(rows)
    return tiles, tw // SPRITE_W, th // SPRITE_H


def write_sprites_txt(tiles, start_index, output_path):
    """Write a full 128-sprite sprites.txt, inserting tiles at start_index."""
    if start_index + len(tiles) > TOTAL_SPRITES:
        print(f"Warning: image needs {len(tiles)} tiles but only "
              f"{TOTAL_SPRITES - start_index} slots available from index {start_index}. "
              f"Truncating.", file=sys.stderr)
        tiles = tiles[:TOTAL_SPRITES - start_index]

    # If output already exists, load the current sprite data so we only overwrite
    # the tiles we're replacing and preserve the rest.
    existing = [list(BLANK_SPRITE) for _ in range(TOTAL_SPRITES)]
    if output_path.exists():
        raw = output_path.read_text().split("\n\n")
        for i, block in enumerate(raw[:TOTAL_SPRITES]):
            rows = [r for r in block.strip().splitlines() if r]
            if len(rows) == SPRITE_H:
                existing[i] = rows

    # Splice in the new tiles
    for i, tile in enumerate(tiles):
        existing[start_index + i] = tile

    lines = []
    for i, sprite in enumerate(existing):
        lines.append("\n".join(sprite))
        if i < TOTAL_SPRITES - 1:
            lines.append("")  # blank separator
    output_path.write_text("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Convert image to GLYPHBOX sprites.txt")
    parser.add_argument("image",                    help="Input image (PNG/JPG/GIF)")
    parser.add_argument("-o", "--output",           help="Output sprites.txt path (default: ./sprites.txt)")
    parser.add_argument("--start",  type=int, default=0,
                        help="Sprite index to start writing at (default: 0)")
    parser.add_argument("--bg",     default=None,
                        help="Background colour to treat as black, e.g. '101,255,0'")
    parser.add_argument("--threshold", type=int, default=180,
                        help="Brightness threshold 0-255 (default: 180). "
                             "Pixels brighter than this become white.")
    parser.add_argument("--invert", action="store_true",
                        help="Swap foreground and background (dark image on light BG)")
    parser.add_argument("--preview", action="store_true",
                        help="Print an ASCII preview of the conversion and exit")
    args = parser.parse_args()

    try:
        from PIL import Image
    except ImportError:
        sys.exit("Missing dependency: pip install pillow")

    img = Image.open(args.image)
    print(f"Input:  {args.image}  ({img.width}×{img.height}  {img.mode})")

    bg_rgb = None
    if args.bg:
        try:
            parts = [int(v.strip()) for v in args.bg.split(",")]
            if len(parts) != 3:
                raise ValueError
            bg_rgb = tuple(parts)
        except ValueError:
            sys.exit("--bg must be three comma-separated integers, e.g. '101,255,0'")

    tiles, cols, rows = image_to_tiles(img, bg_rgb, args.threshold, args.invert)
    print(f"Tiles:  {cols}×{rows} = {len(tiles)} sprites  (starting at index {args.start})")

    if args.preview:
        for ty in range(rows):
            for py in range(SPRITE_H):
                line = ""
                for tx in range(cols):
                    tile = tiles[ty * cols + tx]
                    line += tile[py].replace("1", "█").replace("0", "·") + " "
                print(line)
            print()
        return

    out = Path(args.output) if args.output else Path("sprites.txt")
    write_sprites_txt(tiles, args.start, out)
    print(f"Output: {out}")


if __name__ == "__main__":
    main()
