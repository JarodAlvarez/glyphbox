#!/usr/bin/env python3
"""
qr-encode.py — encodes a .gbcart file to a multi-card PDF set.

The cart is zlib-compressed then split into N equal chunks where N is the
smallest power of 2 that keeps each chunk ≤ TARGET_CHUNK_BYTES.  Each chunk
becomes one physical card (A6, 105×148mm) with a single large Aztec code.

Payload per code:
  byte[0] : index       (0 … N-1)
  byte[1] : total       (N — total cards in this set)
  byte[2] : flags       (0x01 = zlib-compressed whole cart)
  byte[3+]: chunk data

Card tiers (powers of 2, based on TARGET_CHUNK_BYTES=1200):
  1 card  — ≤  1,200 bytes compressed
  2 cards — ≤  2,400 bytes compressed
  4 cards — ≤  4,800 bytes compressed
  8 cards — ≤  9,600 bytes compressed

Each card has a front (title + disc number) and a rear (Aztec code).
The PDF contains 2×N pages interleaved: front₁, rear₁, front₂, rear₂, …

Usage:
    python tools/qr-encode.py cartridges/sw.gbcart -o cards/sw-card.pdf
"""

import argparse
import os
import sys
import tempfile
from pathlib import Path

# ── Target density ─────────────────────────────────────────────────────────────
# Maximum compressed bytes per card.  Lower values → less dense Aztec codes →
# more reliable scanning on wide-angle / fisheye cameras (e.g. imx708_wide).
#
# 1200 bytes: ~40 modules/side — reliable for standard-FOV cameras (e.g.
#             Arducam 75D AF, Pi Camera Module 3) at 6–12 inch scan distance.
#  400 bytes: use this if scanning with a wide-angle / fisheye lens where
#             barrel distortion limits effective code density.
TARGET_CHUNK_BYTES = 1200

# ── A6 card dimensions ────────────────────────────────────────────────────────
CARD_W_MM      = 105.0    # A6 width  (mm)
CARD_H_MM      = 148.0    # A6 height (mm)
MARGIN_MM      =   5.0    # outer margin
TITLE_H_MM     =   8.0    # top strip  — game title
DISC_H_MM      =   8.0    # bottom strip — "CARD N / TOTAL"
TRI_SZ_MM      =   5.0    # corner-chamfer orientation triangle leg

TITLE_FONT_PT  =   7      # game title size (pt)
DISC_FONT_PT   =   6      # card N/total label size (pt)
FRONT_TITLE_PT =  18      # large title on card front

# ── Single-code geometry ──────────────────────────────────────────────────────
# The code is square, fills the full available width, and is centred
# vertically in the remaining space between the title and disc strips.
CODE_SZ_MM = CARD_W_MM - 2 * MARGIN_MM                                   # 95.0 mm
_AVAIL_H   = CARD_H_MM - 2 * MARGIN_MM - TITLE_H_MM - DISC_H_MM         # 122.0 mm
_CODE_X    = MARGIN_MM                                                    #  5.0 mm from left
_CODE_Y    = MARGIN_MM + DISC_H_MM + (_AVAIL_H - CODE_SZ_MM) / 2        # 26.5 mm from bottom


def _check_deps():
    missing = []
    try:
        from aztec_code_generator import AztecCode   # noqa: F401
    except ImportError:
        missing.append("aztec-code-generator")
    try:
        from reportlab.pdfgen import canvas          # noqa: F401
        from reportlab.lib.units import mm           # noqa: F401
    except ImportError:
        missing.append("reportlab")
    if missing:
        sys.exit("Missing Python dependencies — run:\n"
                 f"  pip install {' '.join(missing)}")


def _encode_aztec(payload: bytes, out_png: str) -> None:
    """Encode binary payload as an Aztec code PNG at 5 % error correction."""
    from aztec_code_generator import AztecCode
    try:
        AztecCode(payload, ec_percent=5).save(out_png, module_size=4)
    except Exception as e:
        sys.exit(
            f"Aztec encode failed: {e}\n"
            f"Payload size: {len(payload):,} bytes (Aztec max ~3,067 bytes).\n"
            "Try increasing TARGET_CHUNK_BYTES or reducing the cartridge size."
        )


def encode_cart(cart_path: str, output_path: str) -> None:
    import zlib as _zlib

    data = Path(cart_path).read_bytes()

    # Title: null-terminated ASCII at bytes 4–19 of the cart header
    title = data[4:20].split(b"\x00")[0].decode("ascii", errors="replace").strip()

    # Compress the whole cart
    compressed = _zlib.compress(data, level=9)

    # Choose N: smallest power of 2 where each chunk fits within the target
    n = 1
    while len(compressed) > n * TARGET_CHUNK_BYTES:
        n *= 2

    # Split into N chunks (last chunk absorbs the remainder)
    q      = len(compressed) // n
    chunks = [compressed[i * q : (i + 1) * q] for i in range(n - 1)]
    chunks.append(compressed[(n - 1) * q :])

    # Payload layout: [index_byte, total_byte, flags_byte, ...chunk_data...]
    payloads = [bytes([i, n, 0x01]) + chunks[i] for i in range(n)]

    # ── Summary ────────────────────────────────────────────────────────────
    tier_name = {1: "single", 2: "2-card", 4: "4-card", 8: "8-card"}.get(n, f"{n}-card")
    print(f"Cart:    {cart_path}  ({len(data):,} bytes  →  {len(compressed):,} bytes compressed)")
    print(f"Title:   {title or '(none)'}")
    print(f"Tier:    {tier_name} set  ({n} card{'s' if n > 1 else ''})")
    for i, p in enumerate(payloads):
        print(f"  Card {i + 1:>2}/{n}: {len(p):,} bytes payload  "
              f"({len(chunks[i]):,} bytes data)")

    with tempfile.TemporaryDirectory() as tmp:
        pngs = [os.path.join(tmp, f"card_{i + 1:02d}.png") for i in range(n)]

        print("Encoding Aztec codes…")
        for payload, png in zip(payloads, pngs):
            _encode_aztec(payload, png)

        _build_pdf(pngs, title, n, output_path)

    print(f"\nPDF written: {output_path}  ({n} card{'s' if n > 1 else ''},"
          f" {n * 2} pages)")


def _build_pdf(pngs: list, title: str, total: int, out_path: str) -> None:
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib.units import mm
    from reportlab.lib import colors

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)

    W, H = CARD_W_MM, CARD_H_MM
    c = rl_canvas.Canvas(out_path, pagesize=(W * mm, H * mm))

    display_title = title or "GLYPHBOX"

    for i, png in enumerate(pngs):
        disc_label = f"CARD  {i + 1}  /  {total}"

        # ── Card front ───────────────────────────────────────────────────
        c.setFillColor(colors.white)
        c.rect(0, 0, W * mm, H * mm, fill=1, stroke=0)

        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", FRONT_TITLE_PT)
        c.drawCentredString(W / 2 * mm, (H / 2 + 6) * mm, display_title)

        c.setFont("Helvetica", DISC_FONT_PT + 2)
        c.drawCentredString(W / 2 * mm, (H / 2 - 4) * mm, disc_label)

        # Small "GLYPHBOX" watermark at bottom
        c.setFont("Helvetica", 5)
        c.setFillColorRGB(0.6, 0.6, 0.6)
        c.drawCentredString(W / 2 * mm, MARGIN_MM * mm, "GLYPHBOX")

        c.showPage()

        # ── Card rear ────────────────────────────────────────────────────
        c.setFillColor(colors.white)
        c.rect(0, 0, W * mm, H * mm, fill=1, stroke=0)

        # Aztec code — single large square, centred
        c.drawImage(png, _CODE_X * mm, _CODE_Y * mm,
                    CODE_SZ_MM * mm, CODE_SZ_MM * mm)

        # Title strip (top)
        c.setFont("Helvetica-Bold", TITLE_FONT_PT)
        c.setFillColor(colors.black)
        title_y = (H - MARGIN_MM - TITLE_H_MM * 0.45) * mm
        c.drawCentredString(W / 2 * mm, title_y, display_title)

        # Disc label strip (bottom)
        c.setFont("Helvetica", DISC_FONT_PT)
        c.setFillColor(colors.black)
        disc_y = (MARGIN_MM + DISC_H_MM * 0.45) * mm
        c.drawCentredString(W / 2 * mm, disc_y, disc_label)

        # Corner chamfer triangle — bottom-right, marks correct orientation
        path = c.beginPath()
        path.moveTo(W * mm,                   0)
        path.lineTo((W - TRI_SZ_MM) * mm,     0)
        path.lineTo(W * mm,          TRI_SZ_MM * mm)
        path.close()
        c.setFillColor(colors.black)
        c.drawPath(path, fill=1, stroke=0)

        c.showPage()

    c.save()


def main():
    parser = argparse.ArgumentParser(
        description="Encode a .gbcart file into a multi-card A6 PDF set."
    )
    parser.add_argument("cart",           help="Input .gbcart file")
    parser.add_argument("-o", "--output", required=True, help="Output PDF path")
    args = parser.parse_args()

    _check_deps()
    encode_cart(args.cart, args.output)


if __name__ == "__main__":
    main()
