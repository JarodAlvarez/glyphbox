/**
 * scanner.js — Aztec scanning for GLYPHBOX Web Emulator
 *
 * Uses zxing-wasm (C++ ZXing compiled to WebAssembly) for Aztec decoding.
 * This is the same ZXing C++ codebase used by zxingcpp on the Pi/Mac,
 * so reliability should match the native scanner.
 *
 * Payload format (matches qr-encode.py):
 *   byte[0]  index  (0-based chunk index)
 *   byte[1]  total  (number of cards in set)
 *   byte[2]  flags  (0x01 = zlib-compressed)
 *   byte[3+] chunk data
 *
 * GlyphboxScanner global — called by main.c EM_ASM():
 *   GlyphboxScanner.start()          — open the camera (the console shows its scan screen)
 *   GlyphboxScanner.stop()           — stop scanning
 *   GlyphboxScanner.showScanButton() — kept for older pages; no-op without a button
 *
 * Progress goes to the console through web_scan_status(total, cur, mask), the
 * same status the Pi scanner sends, so the console draws the scan screen,
 * plays the ready chime and the per-card ding, and fills its card pips.
 * The page only needs a camera preview and, optionally, a one-line status.
 */

/* global pako, Module */

/* zxing-wasm is ESM-only; import it dynamically then expose the global */
let _readBarcodes = null;

import("https://cdn.jsdelivr.net/npm/zxing-wasm@1.3.5/dist/es/full/index.js")
  .then(mod => {
    _readBarcodes = mod.readBarcodesFromImageData;
    console.log("GLYPHBOX: zxing-wasm loaded");
  })
  .catch(err => console.error("GLYPHBOX: failed to load zxing-wasm", err));

const GlyphboxScanner = (() => {
  /* ── State ────────────────────────────────────────────────────────────── */
  let stream   = null;
  let scanning = false;
  let rafId    = null;
  let attemptCount = 0;

  const chunks    = new Map();
  let totalChunks = null;

  /* ── DOM refs ─────────────────────────────────────────────────────────── */
  let overlay, video, canvas, ctx, statusEl, btnClose, btnScan;

  /* ── Payload parsing ─────────────────────────────────────────────────── */
  const FLAG_ZLIB = 0x01;

  function parseChunk(bytes) {
    if (bytes.length < 4) return null;
    return {
      index:   bytes[0],
      total:   bytes[1],
      flags:   bytes[2],
      payload: bytes.slice(3),
    };
  }

  /* ── Assembly ────────────────────────────────────────────────────────── */
  function tryAssemble() {
    if (totalChunks === null || chunks.size < totalChunks) return null;
    for (let i = 0; i < totalChunks; i++) if (!chunks.has(i)) return null;

    let total = 0;
    for (let i = 0; i < totalChunks; i++) total += chunks.get(i).payload.length;

    const combined = new Uint8Array(total);
    let offset = 0;
    for (let i = 0; i < totalChunks; i++) {
      const p = chunks.get(i).payload;
      combined.set(p, offset);
      offset += p.length;
    }

    if (chunks.get(0).flags & FLAG_ZLIB) {
      try { return pako.inflate(combined); }
      catch (e) {
        setStatus("Those cards didn't fit together. Scan them again.");
        console.error("GLYPHBOX pako:", e);
        return null;
      }
    }
    return combined;
  }

  /* Tell the console what's been read so far (see web_scan_status in main.c) */
  function report(total, cur, mask) {
    if (typeof Module !== "undefined" && Module._web_scan_status)
      Module.ccall("web_scan_status", null, ["number","number","number"], [total, cur, mask]);
  }
  function readMask() {
    let m = 0;
    for (const i of chunks.keys()) m |= (1 << i);
    return m;
  }

  function deliverCart(cartBytes) {
    setStatus("All cards read. Starting the game.");
    /* A page can take the cart itself (the web runtime can't run LuaJIT
       bytecode, so the site's Play page swaps in published source). */
    if (window.GlyphboxPlay && window.GlyphboxPlay.onCart(cartBytes)) { hideOverlay(); return; }
    const ptr = Module._malloc(cartBytes.length);
    Module.HEAPU8.set(cartBytes, ptr);
    Module.ccall("web_load_cart", null, ["number","number"], [ptr, cartBytes.length]);
    Module._free(ptr);
    hideOverlay();
  }

  /* ── Result handling ─────────────────────────────────────────────────── */
  function handleBytes(bytes) {
    const chunk = parseChunk(bytes);
    if (!chunk) { setStatus("That isn't a GLYPHBOX card."); return; }

    if (totalChunks === null) totalChunks = chunk.total;

    if (!chunks.has(chunk.index)) {
      chunks.set(chunk.index, chunk);
      report(totalChunks, chunk.index, readMask());
      const remaining = totalChunks - chunks.size;
      setStatus(remaining > 0
        ? `Card ${chunk.index + 1} of ${chunk.total} read. ${remaining} to go.`
        : "All cards read.");
    }

    if (chunks.size === totalChunks) {
      stopStream();
      const cart = tryAssemble();
      if (cart) deliverCart(cart);
      else resetState();
    }
  }

  /* ── Decode loop ─────────────────────────────────────────────────────── */
  async function decodeFrame() {
    if (!scanning) return;

    if (_readBarcodes && video.readyState === video.HAVE_ENOUGH_DATA) {
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);

      try {
        const results = await _readBarcodes(imageData, {
          formats:   ["Aztec"],
          tryHarder: true,
        });

        for (const r of results) {
          if (r.isValid) handleBytes(r.bytes);  /* raw Uint8Array — no encoding issues */
        }

        if (results.length === 0) attemptCount++;
      } catch (e) {
        console.warn("GLYPHBOX decode error:", e);
      }
    }

    rafId = requestAnimationFrame(decodeFrame);
  }

  function stopStream() {
    if (rafId) { cancelAnimationFrame(rafId); rafId = null; }
    if (stream) { stream.getTracks().forEach(t => t.stop()); stream = null; }
    scanning = false;
  }

  /* ── UI helpers ──────────────────────────────────────────────────────── */
  function setStatus(msg) { if (statusEl) statusEl.textContent = msg; }

  function showOverlay() {
    if (!overlay) return;
    overlay.style.display = "flex";
    overlay.setAttribute("aria-hidden", "false");
  }

  function hideOverlay() {
    if (!overlay) return;
    overlay.style.display = "none";
    overlay.setAttribute("aria-hidden", "true");
  }

  function resetState() {
    chunks.clear();
    totalChunks  = null;
    attemptCount = 0;
    setStatus("Hold a card's code up to the camera.");
  }

  /* ── Init ────────────────────────────────────────────────────────────── */
  function init() {
    overlay    = document.getElementById("gb-scanner-overlay");
    video      = document.getElementById("gb-scanner-video");
    canvas     = document.getElementById("gb-scanner-canvas");
    statusEl   = document.getElementById("gb-scanner-status");
    btnClose   = document.getElementById("gb-scanner-close");
    btnScan    = document.getElementById("gb-scan-btn");
    ctx        = canvas ? canvas.getContext("2d") : null;

    if (btnClose) {
      btnClose.addEventListener("click", () => {
        stopStream(); resetState(); hideOverlay();
        if (typeof Module !== "undefined" && Module.ccall)
          Module.ccall("web_load_cart", null, ["number","number"], [0, 0]);
      });
    }
    if (btnScan) btnScan.addEventListener("click", () => start());
  }

  /* ── Public API ──────────────────────────────────────────────────────── */
  function waitForDecoder() {
    return new Promise(resolve => {
      if (_readBarcodes) { resolve(); return; }
      const id = setInterval(() => {
        if (_readBarcodes) { clearInterval(id); resolve(); }
      }, 200);
    });
  }

  async function start() {
    if (scanning) return;
    resetState();
    showOverlay();

    /* Open camera immediately so the viewfinder appears right away */
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" }, width: { ideal: 1280 }, height: { ideal: 720 } }
      });
      video.srcObject = stream;
      await video.play();
      canvas.width  = video.videoWidth  || 640;
      canvas.height = video.videoHeight || 480;
    } catch (err) {
      setStatus("No camera: " + err.message);
      if (typeof Module !== "undefined" && Module.ccall)
        Module.ccall("web_load_cart", null, ["number","number"], [0, 0]);   /* back to the splash */
      return;
    }

    /* Wait for zxing-wasm WASM to finish downloading if needed */
    if (!_readBarcodes) {
      setStatus("Getting the decoder ready.");
      await waitForDecoder();
    }

    report(0, 255, 0);   /* camera is up: the console plays its ready chime */
    setStatus("Hold a card's code up to the camera.");
    scanning = true;
    decodeFrame();
  }

  function stop() { stopStream(); hideOverlay(); resetState(); }
  function showScanButton() { if (btnScan) btnScan.style.display = "flex"; }

  if (document.readyState === "loading")
    document.addEventListener("DOMContentLoaded", init);
  else
    init();

  return { start, stop, showScanButton };
})();

/* Make the global accessible to non-module scripts (main.c EM_ASM calls) */
window.GlyphboxScanner = GlyphboxScanner;
