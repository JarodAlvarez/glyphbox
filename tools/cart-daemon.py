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


# ── Aztec scanning (adapted from qr-decode.py) ────────────────────────────────

def scan_for_halves(pil_img) -> dict:
    """
    Scan a PIL Image for GLYPHBOX Aztec codes.

    Returns a dict:  half-index (0 or 1) → (flags_byte, payload_bytes)

    Uses the same two-pass binarisation strategy as qr-decode.py:
      Pass 1 — zxing-cpp native LocalAverage binariser (good for live camera).
      Pass 2 — Hard 128 threshold (fixes anti-aliased rendered/printed codes).
    """
    zxingcpp = _require("zxingcpp", "zxing-cpp")
    halves: dict = {}

    def _extract(results) -> None:
        for r in results:
            if not r.valid or len(r.bytes) < 3:
                continue
            idx   = r.bytes[0]   # 0x00 = Code A, 0x01 = Code B
            flags = r.bytes[1]   # 0x01 = zlib compressed
            if idx in (0, 1) and idx not in halves:
                halves[idx] = (flags, r.bytes[2:])
                label = "A" if idx == 0 else "B"
                log.info("  Code %s found: %d bytes", label, len(r.bytes[2:]))

    _extract(zxingcpp.read_barcodes(pil_img))

    if len(halves) < 2:
        bw = pil_img.convert("L").point(lambda v: 0 if v < 128 else 255, "1").convert("RGB")
        _extract(zxingcpp.read_barcodes(bw))

    return halves


def assemble_cart(halves: dict) -> Optional[bytes]:
    """
    Combine Code A + Code B into a raw .gbcart binary.
    Returns None on decompression error or magic mismatch.
    """
    if 0 not in halves or 1 not in halves:
        return None

    flags_a, data_a = halves[0]
    _,       data_b = halves[1]
    combined = data_a + data_b

    if flags_a & 0x01:
        try:
            combined = zlib.decompress(combined)
            log.info("Decompressed: %d → %d bytes", len(data_a) + len(data_b), len(combined))
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
                    other = "B" if idx == 0 else "A"
                    if (1 - idx) not in halves:
                        label = "A" if idx == 0 else "B"
                        log.info("Code %s captured — waiting for Code %s…", label, other)

            if len(halves) == 2:
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
