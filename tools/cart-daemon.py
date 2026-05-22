#!/usr/bin/env python3
"""
cart-daemon.py — GLYPHBOX Raspberry Pi cartridge daemon.

Continuously captures frames from the Arducam IMX708 via picamera2,
scans for GLYPHBOX Aztec card codes, assembles .gbcart files, and
launches the glyphbox runtime when a valid cartridge is decoded.

Falls back to OpenCV (cv2) if picamera2 is not available (desktop testing).

Usage:
    python tools/cart-daemon.py
    python tools/cart-daemon.py --glyphbox ./build/glyphbox
    python tools/cart-daemon.py --capture-width 2048 --capture-height 1536
    python tools/cart-daemon.py --no-camera --cart cartridges/bouncer.gbcart
"""

import argparse
import hashlib
import logging
import os
import subprocess
import sys
import time
import zlib
from pathlib import Path
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("cart-daemon")

# ── Defaults ──────────────────────────────────────────────────────────────────

_SCAN_INTERVAL   = 0.5   # seconds between capture attempts
_HALVES_TIMEOUT  = 5.0   # seconds to hold a partial scan (one code found) before clearing
_RELOAD_COOLDOWN = 10.0  # seconds before the same cart hash can trigger a re-launch


# ── Dependency helper ─────────────────────────────────────────────────────────

def _require(pkg_import: str, pip_name: str):
    import importlib
    try:
        return importlib.import_module(pkg_import)
    except ImportError:
        sys.exit(f"Missing dependency: pip install {pip_name}")


# ── Camera abstraction ────────────────────────────────────────────────────────

def _open_picamera2(width: int, height: int):
    """Open Arducam IMX708 via picamera2 (Raspberry Pi)."""
    from picamera2 import Picamera2
    import numpy as np

    cam = Picamera2()
    cfg = cam.create_still_configuration(
        main={"size": (width, height), "format": "RGB888"},
        buffer_count=2,
    )
    cam.configure(cfg)
    cam.start()
    time.sleep(1.5)  # allow sensor auto-exposure to settle
    log.info("Camera ready: Arducam IMX708 via picamera2  %dx%d", width, height)

    def capture():
        from PIL import Image
        arr = cam.capture_array()
        return Image.fromarray(arr)

    def close():
        cam.stop()
        cam.close()

    return capture, close


def _open_opencv(device: int, width: int, height: int):
    """Open a webcam via OpenCV (desktop fallback)."""
    import cv2

    cap = cv2.VideoCapture(device)
    if not cap.isOpened():
        sys.exit(f"Cannot open camera device {device}")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    log.info("Camera ready: OpenCV device %d  %dx%d", device, width, height)

    def capture():
        from PIL import Image
        ret, frame = cap.read()
        if not ret:
            return None
        return Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

    def close():
        cap.release()

    return capture, close


def open_camera(device: int, width: int, height: int):
    """Try picamera2 first; fall back to OpenCV."""
    try:
        return _open_picamera2(width, height)
    except ImportError:
        log.info("picamera2 not available — falling back to OpenCV device %d", device)
        return _open_opencv(device, width, height)


# ── Aztec scanning ────────────────────────────────────────────────────────────

_VALID_TOTALS = frozenset({1, 2, 4, 8, 16})


def _is_complete(halves: dict) -> bool:
    total = halves.get(-1, 0)
    return total > 0 and all(i in halves for i in range(total))


def scan_for_halves(pil_img) -> dict:
    """
    Scan a PIL Image for GLYPHBOX Aztec codes (multi-card format).

    Returns a dict:
        -1      → total cards in set (sentinel)
        0…N-1   → (flags_byte, chunk_data_bytes)

    Payload per code (from qr-encode.py):
        byte[0]  chunk index  (0…N-1)
        byte[1]  total cards  (N)
        byte[2]  flags        (0x01 = zlib-compressed)
        byte[3+] chunk data

    Five-pass pipeline matching qr-decode.py camera_mode:
      Pass 1 — zxing-cpp native LocalAverage binariser.
      Pass 2 — contrast-stretched multi-threshold sweep (80–180).
      Pass 3 — unsharp mask sharpening + threshold sweep.
      Pass 4 — CLAHE (local contrast normalisation).
      Pass 5 — adaptive threshold on CLAHE image.
    """
    zxingcpp = _require("zxingcpp", "zxing-cpp")
    halves: dict = {}

    # Build Aztec-only + try_harder hints once
    import inspect
    hints: dict = {}
    try:
        hints["formats"] = zxingcpp.BarcodeFormat.Aztec
    except AttributeError:
        pass
    try:
        sig = inspect.signature(zxingcpp.read_barcodes)
        for key in ("try_rotate", "try_downscale", "try_invert"):
            if key in sig.parameters:
                hints[key] = True
    except (TypeError, ValueError):
        pass

    def _extract(pil) -> None:
        for r in zxingcpp.read_barcodes(pil, **hints):
            if not r.valid or len(r.bytes) < 4:
                continue
            if "aztec" not in str(r.format).lower():
                continue
            idx   = r.bytes[0]
            total = r.bytes[1]
            flags = r.bytes[2]
            data  = r.bytes[3:]
            if total not in _VALID_TOTALS or idx >= total:
                continue
            if -1 not in halves:
                halves[-1] = total
            if idx not in halves:
                halves[idx] = (flags, data)
                log.info("  Card %d/%d found: %d bytes", idx + 1, total, len(data))

    # Pass 1 — native binariser
    _extract(pil_img)
    if _is_complete(halves):
        return halves

    # Pass 2 — contrast-normalised multi-threshold sweep.
    # Stretching min→0/max→255 first makes the sweep lighting-invariant.
    gray_l = pil_img.convert("L")
    lo, hi = gray_l.getextrema()
    if hi > lo:
        gray_l = gray_l.point(lambda v: int((v - lo) * 255 // (hi - lo)))
    for thresh in (80, 100, 120, 140, 160, 180):
        bw = gray_l.point(lambda v, t=thresh: 0 if v < t else 255, "1").convert("RGB")
        _extract(bw)
        if _is_complete(halves):
            return halves

    # Passes 3–5 — camera-specific preprocessing (requires cv2)
    try:
        import cv2
        import numpy as np
        from PIL import Image as _Image

        frame = np.array(pil_img.convert("RGB"))
        gray  = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)

        def _pil(g):
            return _Image.fromarray(cv2.cvtColor(g, cv2.COLOR_GRAY2RGB))

        # Pass 3 — unsharp mask: restores module edges blurred by in-progress AF.
        blurred   = cv2.GaussianBlur(gray, (0, 0), sigmaX=1.5)
        sharpened = cv2.addWeighted(gray, 1.8, blurred, -0.8, 0)
        _extract(_pil(sharpened))
        if _is_complete(halves):
            return halves
        sh_lo, sh_hi = int(sharpened.min()), int(sharpened.max())
        if sh_hi > sh_lo:
            sh_norm = ((sharpened.astype(np.float32) - sh_lo)
                       * 255 / (sh_hi - sh_lo)).astype(np.uint8)
            for thresh in (100, 128, 160):
                bw_arr = np.where(sh_norm >= thresh, np.uint8(255), np.uint8(0))
                _extract(_pil(bw_arr))
                if _is_complete(halves):
                    return halves

        # Pass 4 — CLAHE (local contrast normalisation).
        clahe    = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        _extract(_pil(enhanced))
        if _is_complete(halves):
            return halves

        # Pass 5 — adaptive threshold on CLAHE image.
        adaptive = cv2.adaptiveThreshold(
            enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 25, 5
        )
        _extract(_pil(adaptive))

    except Exception:
        pass

    return halves


def assemble_cart(halves: dict) -> Optional[bytes]:
    """Assemble all N chunks from halves into a raw .gbcart binary."""
    total = halves.get(-1, 0)
    if total == 0 or not all(i in halves for i in range(total)):
        return None

    flags    = halves[0][0]
    raw_size = sum(len(halves[i][1]) for i in range(total))
    combined = b"".join(halves[i][1] for i in range(total))

    if flags & 0x01:
        try:
            combined = zlib.decompress(combined)
            log.info("Decompressed: %d → %d bytes", raw_size, len(combined))
        except zlib.error as e:
            log.error("Decompression failed: %s", e)
            return None

    if combined[:4] != b"GBC1":
        log.warning("Magic mismatch (expected GBC1) — skipping")
        return None

    return combined


# ── Process management ────────────────────────────────────────────────────────

def kill_proc(proc: Optional[subprocess.Popen]) -> None:
    """Gracefully terminate a running glyphbox process."""
    if proc and proc.poll() is None:
        log.info("Terminating previous glyphbox (pid %d)", proc.pid)
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            log.warning("Timeout waiting for glyphbox to exit — killing")
            proc.kill()


def launch_cart(glyphbox_path: str, cart_path: str) -> Optional[subprocess.Popen]:
    """Launch the glyphbox runtime with the given cartridge."""
    if not os.path.isfile(glyphbox_path):
        log.error("glyphbox binary not found: %s", glyphbox_path)
        return None
    log.info("Launching: %s %s", glyphbox_path, cart_path)
    try:
        return subprocess.Popen(
            [glyphbox_path, cart_path],
            start_new_session=True,  # detach so glyphbox outlives the daemon
        )
    except OSError as e:
        log.error("Failed to launch glyphbox: %s", e)
        return None


# ── Daemon loop ───────────────────────────────────────────────────────────────

def run_daemon(args: argparse.Namespace) -> None:
    capture, close_camera = open_camera(
        args.device, args.capture_width, args.capture_height
    )

    cart_dir = Path(args.cart_dir)
    cart_dir.mkdir(parents=True, exist_ok=True)
    cart_path = str(cart_dir / "current.gbcart")

    proc:               Optional[subprocess.Popen] = None
    loaded_hash:        Optional[str]              = None
    loaded_at:          float                      = 0.0
    halves:             dict                       = {}
    halves_last_update: float                      = 0.0

    log.info("GLYPHBOX cart-daemon started")
    log.info("Point the camera at the REAR of the cartridge card")

    try:
        while True:
            now = time.monotonic()

            # Clear stale partial scan (one code found, other never arrived)
            if halves and (now - halves_last_update) > args.halves_timeout:
                log.debug("Partial scan timed out — clearing")
                halves = {}

            frame = capture()
            if frame is None:
                log.warning("Camera read error — retrying")
                time.sleep(args.scan_interval)
                continue

            new = scan_for_halves(frame)
            for idx, val in new.items():
                if idx not in halves:
                    halves[idx] = val
                    halves_last_update = now
                    total = halves.get(-1, 0)
                    if isinstance(idx, int) and idx >= 0 and total > 0:
                        captured = sum(1 for k in halves if isinstance(k, int) and k >= 0)
                        if captured < total:
                            log.info("Card %d/%d scanned — %d remaining",
                                     captured, total, total - captured)

            if _is_complete(halves):
                cart_bytes = assemble_cart(halves)
                halves = {}  # reset regardless of outcome

                if cart_bytes:
                    cart_hash = hashlib.sha256(cart_bytes).hexdigest()[:16]

                    if cart_hash == loaded_hash and (now - loaded_at) < args.reload_cooldown:
                        log.debug("Same cart still loaded — ignoring re-scan")
                    else:
                        Path(cart_path).write_bytes(cart_bytes)
                        log.info("Cart written: %d bytes  hash=%s", len(cart_bytes), cart_hash)
                        kill_proc(proc)
                        proc = launch_cart(args.glyphbox, cart_path)
                        loaded_hash = cart_hash
                        loaded_at   = now

            time.sleep(args.scan_interval)

    except KeyboardInterrupt:
        log.info("Interrupted")
    finally:
        kill_proc(proc)
        close_camera()
        log.info("Daemon stopped")


# ── Direct-load mode (no camera) ─────────────────────────────────────────────

def run_direct(args: argparse.Namespace) -> None:
    """Skip scanning and launch a .gbcart file directly (useful for testing)."""
    if not args.cart:
        sys.exit("--no-camera requires --cart <path>")
    if not os.path.isfile(args.cart):
        sys.exit(f"Cart not found: {args.cart}")
    proc = launch_cart(args.glyphbox, args.cart)
    if proc:
        try:
            proc.wait()
        except KeyboardInterrupt:
            kill_proc(proc)


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="GLYPHBOX Pi daemon: scan Aztec cards and launch the runtime."
    )
    parser.add_argument(
        "--glyphbox",
        default="./build/glyphbox",
        metavar="PATH",
        help="Path to the glyphbox binary (default: ./build/glyphbox)",
    )
    parser.add_argument(
        "--cart-dir",
        default="/tmp",
        metavar="DIR",
        help="Directory for the assembled current.gbcart (default: /tmp)",
    )
    parser.add_argument(
        "--device",
        type=int, default=0,
        help="OpenCV device index for fallback mode (default: 0)",
    )
    parser.add_argument(
        "--capture-width",
        type=int, default=1920,
        help="Camera capture width in pixels (default: 1920)",
    )
    parser.add_argument(
        "--capture-height",
        type=int, default=1080,
        help="Camera capture height in pixels (default: 1080)",
    )
    parser.add_argument(
        "--scan-interval",
        type=float, default=_SCAN_INTERVAL,
        help=f"Seconds between scan attempts (default: {_SCAN_INTERVAL})",
    )
    parser.add_argument(
        "--halves-timeout",
        type=float, default=_HALVES_TIMEOUT,
        help=f"Seconds to hold a partial scan before clearing (default: {_HALVES_TIMEOUT})",
    )
    parser.add_argument(
        "--reload-cooldown",
        type=float, default=_RELOAD_COOLDOWN,
        help=f"Seconds before re-launching the same cart hash (default: {_RELOAD_COOLDOWN})",
    )
    parser.add_argument(
        "--no-camera",
        action="store_true",
        help="Skip camera scanning — launch a cart file directly",
    )
    parser.add_argument(
        "--cart",
        metavar="PATH",
        help="Path to a .gbcart file (used with --no-camera)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.no_camera:
        run_direct(args)
    else:
        run_daemon(args)


if __name__ == "__main__":
    main()
