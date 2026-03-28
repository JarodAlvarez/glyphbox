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
 *   GlyphboxScanner.start()          — open camera overlay
 *   GlyphboxScanner.stop()           — stop scanning
 *   GlyphboxScanner.showScanButton() — re-show FAB after eject
 */

/* global pako, Module */

/* zxing-wasm is ESM-only; import it dynamically then expose the global */
let _readBarcodes = null;

import("https://cdn.jsdelivr.net/npm/zxing-wasm@1/dist/full/index.js")
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
  let overlay, video, canvas, ctx, statusEl, progressEl, btnClose, btnScan;

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
        setStatus("⚠ Decompression failed — try again.");
        console.error("GLYPHBOX pako:", e);
        return null;
      }
    }
    return combined;
  }

  function deliverCart(cartBytes) {
    setStatus("✓ Loaded — starting game…");
    const ptr = Module._malloc(cartBytes.length);
    Module.HEAPU8.set(cartBytes, ptr);
    Module.ccall("web_load_cart", null, ["number","number"], [ptr, cartBytes.length]);
    Module._free(ptr);
    hideOverlay();
  }

  /* ── Result handling ─────────────────────────────────────────────────── */
  function handleBytes(bytes) {
    const chunk = parseChunk(bytes);
    if (!chunk) { setStatus("⚠ Not a GLYPHBOX card — keep scanning…"); return; }

    if (totalChunks === null) {
      totalChunks = chunk.total;
      buildProgressPills(totalChunks);
    }

    if (!chunks.has(chunk.index)) {
      chunks.set(chunk.index, chunk);
      markPill(chunk.index);
      const remaining = totalChunks - chunks.size;
      setStatus(remaining > 0
        ? `✓ Card ${chunk.index + 1} of ${chunk.total} — ${remaining} more to scan…`
        : "All cards scanned — assembling…");
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

        if (results.length === 0) {
          attemptCount++;
          if (chunks.size === 0 && attemptCount % 20 === 0) {
            const need = totalChunks !== null ? totalChunks : "?";
            setStatus(`Scanning… (${chunks.size} / ${need} cards)  attempt ${attemptCount}`);
          }
        }
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

  /* ── Progress UI ─────────────────────────────────────────────────────── */
  function buildProgressPills(n) {
    if (!progressEl) return;
    progressEl.innerHTML = "";
    for (let i = 0; i < n; i++) {
      const pill = document.createElement("div");
      pill.className = "gb-chunk-pill";
      pill.id        = `gb-pill-${i}`;
      pill.setAttribute("role", "listitem");
      pill.setAttribute("aria-label", `Card ${i + 1}`);
      progressEl.appendChild(pill);
    }
  }

  function markPill(i) {
    const pill = document.getElementById(`gb-pill-${i}`);
    if (pill) pill.classList.add("done");
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
    if (progressEl) progressEl.innerHTML = "";
    setStatus("Point camera at the back of the card…");
  }

  /* ── Init ────────────────────────────────────────────────────────────── */
  function init() {
    overlay    = document.getElementById("gb-scanner-overlay");
    video      = document.getElementById("gb-scanner-video");
    canvas     = document.getElementById("gb-scanner-canvas");
    statusEl   = document.getElementById("gb-scanner-status");
    progressEl = document.getElementById("gb-chunk-progress");
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
  async function start() {
    if (scanning) return;
    resetState();
    showOverlay();

    if (!_readBarcodes) {
      setStatus("⚠ Decoder still loading — please wait a moment and try again.");
      return;
    }

    try {
      stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" }, width: { ideal: 1280 }, height: { ideal: 720 } }
      });
      video.srcObject = stream;
      await video.play();
      canvas.width  = video.videoWidth  || 640;
      canvas.height = video.videoHeight || 480;
    } catch (err) {
      setStatus("⚠ Camera error: " + err.message);
      return;
    }

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
