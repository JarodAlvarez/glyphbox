#!/usr/bin/env python3
"""
card-print.py — Print-and-cut credit-card game cards for GLYPHBOX.

Produces a PDF laid out on A4 or US Letter paper, with crop marks, ready for
cutting to ISO ID-1 (85.6 × 54 mm) credit-card dimensions.  The PDF contains
two sets of pages: rear faces first (Aztec codes), then front faces (title
design), so you can print each set separately, cut, and optionally laminate
the pairs back-to-back.

Usage:
    python3 tools/card-print.py cartridges/hello.gbcart -o cards/hello-print.pdf
    python3 tools/card-print.py cartridges/sw.gbcart   -o cards/sw-print.pdf --paper letter
    python3 tools/card-print.py cartridges/sw.gbcart   -o cards/sw-rear.pdf  --rear-only
"""

import argparse
import os
import sys
import zlib
import tempfile
import hashlib
from pathlib import Path

# ── Card dimensions (ISO ID-1) ────────────────────────────────────────────────
CARD_W_MM = 85.6
CARD_H_MM = 54.0

# ── Layout ────────────────────────────────────────────────────────────────────
MARGIN_MM   = 5.0    # page edge margin
GAP_MM      = 3.0    # gap between cards on the page
MARK_MM     = 3.0    # crop-mark arm length
MARK_GAP_MM = 1.0    # gap between card edge and start of crop mark

# ── Card interior ─────────────────────────────────────────────────────────────
BORDER_MM    = 1.0   # inset border
TITLE_H_MM   = 7.0   # title/label strip height at the top of rear face
ACCENT_W_MM  = 8.0   # left accent bar width on front face
ACCENT_H_MM  = 8.0   # bottom accent bar height on front face

# ── Encoding ──────────────────────────────────────────────────────────────────
TARGET_CHUNK_BYTES = 1200   # must match qr-encode.py

# ── Paper sizes (mm) ──────────────────────────────────────────────────────────
PAPER = {
    "a4":     (210.0, 297.0),
    "letter": (215.9, 279.4),
}

# ── Accent colour palette (hashed from title) ─────────────────────────────────
# Each entry is (R, G, B) 0–1 floats — deep, saturated colours on dark cards.
_PALETTE = [
    (0.85, 0.15, 0.15),   # red
    (0.15, 0.45, 0.85),   # blue
    (0.15, 0.70, 0.30),   # green
    (0.85, 0.55, 0.10),   # amber
    (0.65, 0.15, 0.80),   # purple
    (0.15, 0.70, 0.75),   # teal
    (0.85, 0.35, 0.60),   # pink
]


def _accent_colour(title: str):
    idx = int(hashlib.md5(title.encode()).hexdigest(), 16) % len(_PALETTE)
    return _PALETTE[idx]


# ── Dependency check ──────────────────────────────────────────────────────────

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
        sys.exit("Missing dependencies — run:\n"
                 f"  pip install {' '.join(missing)}")


# ── Aztec encoding ────────────────────────────────────────────────────────────

def _encode_aztec(payload: bytes, out_png: str) -> None:
    from aztec_code_generator import AztecCode
    try:
        AztecCode(payload, ec_percent=23).save(out_png, module_size=8)
    except Exception as e:
        sys.exit(
            f"Aztec encode failed: {e}\n"
            f"Payload: {len(payload):,} bytes (max ~3,067).\n"
            "Reduce TARGET_CHUNK_BYTES or shrink the cartridge."
        )


# ── Cart reading ──────────────────────────────────────────────────────────────

def _read_cart(cart_path: str):
    """
    Read a .gbcart file and return (title, payloads).
    Payloads is a list of bytes objects, one per card, in the same format
    the decoder expects: [index, total, 0x01, ...zlib-chunk...].
    """
    data = Path(cart_path).read_bytes()
    if data[:4] != b"GBC1":
        sys.exit(f"Not a valid GLYPHBOX cartridge (missing GBC1 magic): {cart_path}")

    # Title: null-terminated ASCII at bytes 4–19
    title = data[4:20].split(b"\x00")[0].decode("ascii", errors="replace").strip()
    if not title:
        title = Path(cart_path).stem.upper()

    compressed = zlib.compress(data, level=9)

    n = 1
    while len(compressed) > n * TARGET_CHUNK_BYTES:
        n *= 2

    q      = len(compressed) // n
    chunks = [compressed[i * q : (i + 1) * q] for i in range(n - 1)]
    chunks.append(compressed[(n - 1) * q :])

    payloads = [bytes([i, n, 0x01]) + chunks[i] for i in range(n)]
    return title, payloads


# ── PDF construction ──────────────────────────────────────────────────────────

def _build_pdf(pngs: list, title: str, total: int,
               out_path: str, paper: str, rear_only: bool) -> None:
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib.units import mm
    from reportlab.lib import colors

    PW_MM, PH_MM = PAPER[paper]   # page dimensions in mm

    # ── Grid layout ──────────────────────────────────────────────────────────
    # Fit as many cards as possible with MARGIN_MM page border and GAP_MM gaps.
    cols = max(1, int((PW_MM - MARGIN_MM) // (CARD_W_MM + GAP_MM)))
    rows = max(1, int((PH_MM - MARGIN_MM) // (CARD_H_MM + GAP_MM)))

    # Centre the grid on the page
    grid_w = cols * CARD_W_MM + (cols - 1) * GAP_MM
    grid_h = rows * CARD_H_MM + (rows - 1) * GAP_MM
    x0_mm  = (PW_MM - grid_w) / 2   # left edge of leftmost column
    y0_mm  = (PH_MM - grid_h) / 2   # bottom edge of bottom row
                                      # (reportlab origin = bottom-left)

    accent = _accent_colour(title)

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    c = rl_canvas.Canvas(out_path, pagesize=(PW_MM * mm, PH_MM * mm))

    def _new_page_if_needed(card_idx_on_page):
        """Start a fresh page when the current page's grid is full."""
        if card_idx_on_page > 0 and card_idx_on_page % (cols * rows) == 0:
            c.showPage()

    def _card_origin(card_idx_on_page):
        """Bottom-left corner of a card slot (in mm, reportlab coords)."""
        slot  = card_idx_on_page % (cols * rows)
        col   = slot % cols
        row   = slot // cols
        # row 0 = top row visually → highest y value
        visual_row = (rows - 1) - row
        x = x0_mm + col * (CARD_W_MM + GAP_MM)
        y = y0_mm + visual_row * (CARD_H_MM + GAP_MM)
        return x, y

    def _crop_marks(cx, cy):
        """Draw L-shaped crop marks at all four corners of a card."""
        c.setStrokeColorRGB(0.5, 0.5, 0.5)
        c.setLineWidth(0.25)
        g = MARK_GAP_MM
        m = MARK_MM
        W, H = CARD_W_MM, CARD_H_MM
        # Bottom-left
        c.line((cx - g - m) * mm, cy * mm,         (cx - g) * mm, cy * mm)
        c.line(cx * mm,           (cy - g - m) * mm, cx * mm,     (cy - g) * mm)
        # Bottom-right
        c.line((cx + W + g) * mm, cy * mm,         (cx + W + g + m) * mm, cy * mm)
        c.line((cx + W) * mm,     (cy - g - m) * mm, (cx + W) * mm, (cy - g) * mm)
        # Top-left
        c.line((cx - g - m) * mm, (cy + H) * mm,   (cx - g) * mm, (cy + H) * mm)
        c.line(cx * mm,           (cy + H + g) * mm, cx * mm, (cy + H + g + m) * mm)
        # Top-right
        c.line((cx + W + g) * mm, (cy + H) * mm,   (cx + W + g + m) * mm, (cy + H) * mm)
        c.line((cx + W) * mm,     (cy + H + g) * mm, (cx + W) * mm, (cy + H + g + m) * mm)

    # ── REAR faces ────────────────────────────────────────────────────────────
    print("Building rear faces (Aztec codes)…")
    for i, png in enumerate(pngs):
        _new_page_if_needed(i)
        cx, cy = _card_origin(i)
        W, H   = CARD_W_MM, CARD_H_MM

        _crop_marks(cx, cy)

        # White card background
        c.setFillColorRGB(1, 1, 1)
        c.rect(cx * mm, cy * mm, W * mm, H * mm, stroke=0, fill=1)

        # Thin border
        c.setStrokeColorRGB(0.2, 0.2, 0.2)
        c.setLineWidth(0.5)
        b = BORDER_MM
        c.rect((cx + b) * mm, (cy + b) * mm,
               (W - 2 * b) * mm, (H - 2 * b) * mm, stroke=1, fill=0)

        # Top strip: game title (left) + card N/total (right)
        strip_y = cy + H - b - TITLE_H_MM
        c.setFillColorRGB(0.08, 0.08, 0.08)
        c.rect((cx + b) * mm, strip_y * mm,
               (W - 2 * b) * mm, TITLE_H_MM * mm, stroke=0, fill=1)

        c.setFillColorRGB(1, 1, 1)
        c.setFont("Helvetica-Bold", 5.5)
        label_y = strip_y + (TITLE_H_MM - 5.5 / 2.835) / 2   # vertically centred
        c.drawString((cx + b + 1.5) * mm, label_y * mm, title.upper())
        card_label = f"CARD {i + 1} / {total}"
        c.drawRightString((cx + W - b - 1.5) * mm, label_y * mm, card_label)

        # Aztec code — centred in the remaining space below the strip
        avail_y  = cy + b
        avail_h  = strip_y - cy - b
        avail_w  = W - 2 * b
        code_sz  = min(avail_w, avail_h) - 2   # 1mm breathing room each side
        code_x   = cx + b + (avail_w - code_sz) / 2
        code_y   = avail_y + (avail_h - code_sz) / 2
        c.drawImage(png,
                    code_x * mm, code_y * mm,
                    code_sz * mm, code_sz * mm,
                    preserveAspectRatio=True, mask="auto")

        # Bottom accent strip (colour bar under code)
        acc_h = 1.5
        c.setFillColorRGB(*accent)
        c.rect((cx + b) * mm, (cy + b) * mm,
               (W - 2 * b) * mm, acc_h * mm, stroke=0, fill=1)

    c.showPage()

    # ── FRONT faces ───────────────────────────────────────────────────────────
    if not rear_only:
        print("Building front faces (title design)…")
        for i in range(total):
            _new_page_if_needed(i)
            cx, cy = _card_origin(i)
            W, H   = CARD_W_MM, CARD_H_MM

            _crop_marks(cx, cy)

            # Dark card background
            c.setFillColorRGB(0.08, 0.08, 0.08)
            c.rect(cx * mm, cy * mm, W * mm, H * mm, stroke=0, fill=1)

            # Left accent bar
            c.setFillColorRGB(*accent)
            c.rect(cx * mm, cy * mm,
                   ACCENT_W_MM * mm, H * mm, stroke=0, fill=1)

            # Bottom accent bar (starts after left bar)
            c.rect((cx + ACCENT_W_MM) * mm, cy * mm,
                   (W - ACCENT_W_MM) * mm, ACCENT_H_MM * mm, stroke=0, fill=1)

            # "GLYPHBOX" micro-label top-right
            c.setFillColorRGB(0.55, 0.55, 0.55)
            c.setFont("Helvetica", 4.5)
            c.drawRightString((cx + W - 2) * mm, (cy + H - 6) * mm, "GLYPHBOX")

            # Game title — centred in the main area
            inner_x = cx + ACCENT_W_MM + 2
            inner_w = W - ACCENT_W_MM - 4
            inner_y = cy + ACCENT_H_MM + 2
            inner_h = H - ACCENT_H_MM - 4

            c.setFillColorRGB(1, 1, 1)
            font_size = min(18, inner_w / max(1, len(title)) * 2.5 * 2.835)
            font_size = max(8, font_size)
            c.setFont("Helvetica-Bold", font_size)
            title_y = inner_y + (inner_h - font_size / 2.835) / 2
            c.drawCentredString(
                (inner_x + inner_w / 2) * mm, title_y * mm, title.upper()
            )

            # Card number bottom-right (above bottom accent bar)
            c.setFillColorRGB(0.08, 0.08, 0.08)
            c.setFont("Helvetica-Bold", 5)
            if total > 1:
                c.drawRightString(
                    (cx + W - 2) * mm,
                    (cy + ACCENT_H_MM + 1.5) * mm,
                    f"{i + 1}/{total}"
                )

        c.showPage()

    c.save()


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Generate print-and-cut credit-card-sized GLYPHBOX game cards."
    )
    parser.add_argument("cart",  help=".gbcart input file")
    parser.add_argument("-o", "--output", required=True,
                        help="Output PDF path")
    parser.add_argument("--paper", choices=["a4", "letter"], default="a4",
                        help="Paper size (default: a4)")
    parser.add_argument("--rear-only", action="store_true",
                        help="Generate only rear faces with Aztec codes "
                             "(skip decorative front faces)")
    args = parser.parse_args()

    _check_deps()

    title, payloads = _read_cart(args.cart)
    n = len(payloads)

    cols = max(1, int((PAPER[args.paper][0] - MARGIN_MM) // (CARD_W_MM + GAP_MM)))
    rows = max(1, int((PAPER[args.paper][1] - MARGIN_MM) // (CARD_H_MM + GAP_MM)))
    per_page = cols * rows
    rear_pages  = (n + per_page - 1) // per_page
    front_pages = 0 if args.rear_only else rear_pages
    total_pages = rear_pages + front_pages

    print(f"Cart:   {args.cart}  ({n} card{'s' if n > 1 else ''})")
    print(f"Title:  {title}")
    print(f"Paper:  {args.paper.upper()}  —  {cols}×{rows} cards/page  "
          f"({per_page} per page)")
    print(f"Pages:  {rear_pages} rear + {front_pages} front = {total_pages} total")

    with tempfile.TemporaryDirectory() as tmp:
        pngs = [os.path.join(tmp, f"card_{i+1:02d}.png") for i in range(n)]
        print("Encoding Aztec codes…")
        for payload, png in zip(payloads, pngs):
            _encode_aztec(payload, png)
        _build_pdf(pngs, title, n, args.output, args.paper, args.rear_only)

    faces = "rear faces only" if args.rear_only else "rear + front faces"
    print(f"\nPDF written: {args.output}  ({faces})")
    print(f"\nTo use:")
    print(f"  1. Print rear pages on plain paper (or card stock)")
    if not args.rear_only:
        print(f"  2. Print front pages on the reverse side (duplex) or a second sheet")
    print(f"  3. Cut along the crop marks — each card is {CARD_W_MM}×{CARD_H_MM}mm")
    if not args.rear_only:
        print(f"  4. Optionally laminate front and rear back-to-back")


if __name__ == "__main__":
    main()
