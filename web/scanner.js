/**
 * scanner.js — ZXing-js Aztec scanning for GLYPHBOX Web Emulator
 *
 * Payload format (matches qr-encode.py):
 *   byte[0]  index  (0-based chunk index)
 *   byte[1]  total  (number of chunks / cards in set)
 *   byte[2]  flags  (0x01 = payload is a zlib-compressed slice of the cart)
 *   byte[3+] chunk data (raw slice of the zlib-compressed whole cart)
 *
 * Assembly:
 *   1. Collect all N chunk data slices in index order
 *   2. Concatenate → one big zlib stream
 *   3. pako.inflate() → original .gbcart bytes
 *   4. Call Module.ccall("web_load_cart", ...) with the raw cart
 *
 * GlyphboxScanner global is called by main.c:
 *   GlyphboxScanner.start()          — open camera overlay
 *   GlyphboxScanner.stop()           — close camera overlay (eject / cancel)
 *   GlyphboxScanner.showScanButton() — re-show the Scan FAB after eject
 */

/* global ZXing, pako, Module */

const GlyphboxScanner = (() => {
  /* ── State ────────────────────────────────────────────────────────────── */
  let reader   = null;   // ZXing MultiFormatReader
  let stream   = null;   // MediaStream from getUserMedia
  let scanning = false;
  let rafId    = null;

  /* Collected chunk data slices keyed by index */
  const chunks    = new Map();
  let totalChunks = null;

  /* ── DOM refs (populated by init()) ──────────────────────────────────── */
  let overlay, video, canvas, ctx, statusEl, progressEl, btnClose, btnScan;

  /* ── Payload parsing ────────────────────────────────────────────────── */
  const FLAG_ZLIB = 0x01;

  function parseChunk(bytes) {
    if (bytes.length < 4) return null;
    const index   = bytes[0];
    const total   = bytes[1];
    const flags   = bytes[2];
    const payload = bytes.slice(3);
    return { index, total, flags, payload };
  }

  /* ── Assembly & delivery ────────────────────────────────────────────── */
  function tryAssemble() {
    if (totalChunks === null || chunks.size < totalChunks) return null;

    /* Check we have every index */
    for (let i = 0; i < totalChunks; i++) {
      if (!chunks.has(i)) return null;
    }

    /* Concatenate chunk slices in order */
    const parts  = [];
    let   total  = 0;
    for (let i = 0; i < totalChunks; i++) {
      const c = chunks.get(i);
      parts.push(c.payload);
      total += c.payload.length;
    }

    const combined = new Uint8Array(total);
    let   offset   = 0;
    for (const p of parts) {
      combined.set(p, offset);
      offset += p.length;
    }

    /* Inflate if zlib-compressed (flag 0x01) */
    const firstChunk = chunks.get(0);
    if (firstChunk.flags & FLAG_ZLIB) {
      try {
        return pako.inflate(combined);
      } catch (e) {
        setStatus("⚠ Decompression failed — try scanning again.");
        console.error("GLYPHBOX pako.inflate error:", e);
        return null;
      }
    }
    return combined;
  }

  function deliverCart(cartBytes) {
    setStatus("✓ Loaded — starting game…");
    const ptr = Module._malloc(cartBytes.length);
    Module.HEAPU8.set(cartBytes, ptr);
    Module.ccall(
      "web_load_cart",
      null,
      ["number", "number"],
      [ptr, cartBytes.length]
    );
    Module._free(ptr);
    hideOverlay();
  }

  /* ── Code handling ──────────────────────────────────────────────────── */
  function handleResult(text) {
    /* ZXing returns Aztec payload as a binary string; convert to bytes */
    const bytes = new Uint8Array(text.length);
    for (let i = 0; i < text.length; i++) bytes[i] = text.charCodeAt(i) & 0xFF;

    const chunk = parseChunk(bytes);
    if (!chunk) {
      setStatus("⚠ Unrecognised code — is this a GLYPHBOX card?");
      return;
    }

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

  /* ── Camera / decode loop ─────────────────────────────────────────────── */
  async function openCamera() {
    const constraints = {
      video: {
        facingMode: { ideal: "environment" },
        width:  { ideal: 1280 },
        height: { ideal: 720 }
      }
    };
    stream = await navigator.mediaDevices.getUserMedia(constraints);
    video.srcObject = stream;
    await video.play();
    canvas.width  = video.videoWidth  || 640;
    canvas.height = video.videoHeight || 480;
  }

  function stopStream() {
    if (rafId) { cancelAnimationFrame(rafId); rafId = null; }
    if (stream) { stream.getTracks().forEach(t => t.stop()); stream = null; }
    scanning = false;
  }

  function decodeFrame() {
    if (!scanning) return;
    if (video.readyState === video.HAVE_ENOUGH_DATA) {
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
      try {
        const lum    = new ZXing.HTMLCanvasElementLuminanceSource(canvas);
        const bitmap = new ZXing.BinaryBitmap(new ZXing.HybridBinarizer(lum));
        const result = reader.decode(bitmap);
        if (result) handleResult(result.getText());
      } catch (e) {
        /* NotFoundException is normal — no code in frame */
        if (e && e.name !== "NotFoundException") {
          console.warn("GLYPHBOX ZXing error:", e);
        }
      }
    }
    rafId = requestAnimationFrame(decodeFrame);
  }

  /* ── Progress UI ──────────────────────────────────────────────────────── */
  function buildProgressPills(n) {
    if (!progressEl) return;
    progressEl.innerHTML = "";
    for (let i = 0; i < n; i++) {
      const pill = document.createElement("div");
      pill.className   = "gb-chunk-pill";
      pill.id          = `gb-pill-${i}`;
      pill.role        = "listitem";
      pill.setAttribute("aria-label", `Card ${i + 1}`);
      progressEl.appendChild(pill);
    }
  }

  function markPill(index) {
    const pill = document.getElementById(`gb-pill-${index}`);
    if (pill) pill.classList.add("done");
  }

  /* ── UI helpers ───────────────────────────────────────────────────────── */
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
    totalChunks = null;
    if (progressEl) progressEl.innerHTML = "";
    setStatus("Point camera at the back of the card…");
  }

  /* ── Initialisation ───────────────────────────────────────────────────── */
  function initReader() {
    if (!window.ZXing) {
      console.error("GLYPHBOX: ZXing not loaded — scanning disabled");
      return;
    }
    const hints = new ZXing.DecodingHintDictionary();
    hints.set(ZXing.DecodeHintType.POSSIBLE_FORMATS, [ZXing.BarcodeFormat.AZTEC]);
    hints.set(ZXing.DecodeHintType.TRY_HARDER, true);
    reader = new ZXing.MultiFormatReader();
    reader.setHints(hints);
  }

  function init() {
    overlay    = document.getElementById("gb-scanner-overlay");
    video      = document.getElementById("gb-scanner-video");
    canvas     = document.getElementById("gb-scanner-canvas");
    statusEl   = document.getElementById("gb-scanner-status");
    progressEl = document.getElementById("gb-chunk-progress");
    btnClose   = document.getElementById("gb-scanner-close");
    btnScan    = document.getElementById("gb-scan-btn");

    ctx = canvas ? canvas.getContext("2d") : null;

    if (btnClose) {
      btnClose.addEventListener("click", () => {
        stopStream();
        resetState();
        hideOverlay();
        /* Notify C that scanning was aborted (len=0 → load_cart returns NULL) */
        if (typeof Module !== "undefined" && Module.ccall) {
          Module.ccall("web_load_cart", null, ["number","number"], [0, 0]);
        }
      });
    }

    if (btnScan) {
      btnScan.addEventListener("click", () => start());
    }

    initReader();
  }

  /* ── Public API ───────────────────────────────────────────────────────── */
  async function start() {
    if (scanning) return;
    resetState();
    showOverlay();

    try {
      await openCamera();
    } catch (err) {
      setStatus("⚠ Camera error: " + err.message);
      console.error("GLYPHBOX camera error:", err);
      return;
    }

    scanning = true;
    decodeFrame();
  }

  function stop() {
    stopStream();
    hideOverlay();
    resetState();
  }

  function showScanButton() {
    if (btnScan) btnScan.style.display = "flex";
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  return { start, stop, showScanButton };
})();
