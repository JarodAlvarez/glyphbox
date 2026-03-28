# GLYPHBOX — Web Emulator

A WebAssembly build of the GLYPHBOX fantasy console runtime that runs in any
modern mobile or desktop browser.  Cartridges are loaded by scanning the
printed card set with your device's camera.

---

## How it works

```
printed Aztec cards  →  phone/webcam (ZXing-js)  →  pako inflate
                    →  Emscripten Module.ccall("web_load_cart")
                    →  SDL2/WASM runtime  →  Lua cartridge
```

- **ZXing-js** decodes Aztec codes from the live camera feed, one card at a time.
- Each code carries a 3-byte header `[index, total, flags]` followed by a
  zlib-compressed slice of the cartridge binary.
- Once all slices are collected they are concatenated and inflated with **pako**
  to reconstruct the original `.gbcart`.
- The assembled binary is handed to the C runtime via `web_load_cart()`.

---

## Prerequisites

| Tool | Install |
|------|---------|
| Emscripten SDK ≥ 3.1 | `brew install emscripten` or [emsdk](https://emscripten.org/docs/getting_started/downloads.html) |
| CMake ≥ 3.20 | `brew install cmake` |
| Python 3 | system |

### Lua 5.4 source (one-time setup)

The web build uses standard Lua 5.4 instead of LuaJIT because LuaJIT's JIT
compiler is x86/ARM assembly and cannot be compiled to WebAssembly.

```bash
# Run from the repo root
curl -L https://www.lua.org/ftp/lua-5.4.7.tar.gz | tar xz -C web/
mv web/lua-5.4.7/src web/lua54
rm -rf web/lua-5.4.7
```

---

## Building

```bash
# From the repo root
emcmake cmake -B build-web web/ -DCMAKE_BUILD_TYPE=Release
cmake --build build-web -j4
```

Output files in `build-web/`:

| File | Purpose |
|------|---------|
| `glyphbox.html` | Entry point (generated from `web/shell.html`) |
| `glyphbox.js`   | Emscripten JS glue |
| `glyphbox.wasm` | Compiled C runtime |

The HTML file references `style.css` and `scanner.js` from the source tree,
so copy those alongside the build output when deploying:

```bash
cp web/style.css web/scanner.js build-web/
```

---

## Local testing

Browsers block `getUserMedia` on plain `http://`, so you need either:

**Option A — Python HTTPS server** (quick):
```bash
cd build-web
python3 -m http.server 8080
# Then open http://localhost:8080/glyphbox.html
# Camera works on localhost even without HTTPS
```

**Option B — ngrok tunnel** (test on real mobile):
```bash
cd build-web && python3 -m http.server 8080
ngrok http 8080
# Use the https:// ngrok URL on your phone
```

---

## Deploying to GitHub Pages

1. Build as above.
2. Copy the four files into a `gh-pages` branch or `docs/` folder:

```bash
mkdir -p docs/web
cp build-web/glyphbox.{html,js,wasm} web/style.css web/scanner.js docs/web/
# Rename the HTML to index.html so GitHub Pages serves it at the root
cp docs/web/glyphbox.html docs/web/index.html
```

3. In your GitHub repo → Settings → Pages, set source to `docs/web/`.

The site will be live at `https://<user>.github.io/<repo>/web/` within a
few minutes and costs nothing.

> **Note**: GitHub Pages serves files with correct WASM MIME type
> (`application/wasm`) as of mid-2020, so no `.htaccess` is needed.

---

## Scanning tips

- **Light**: bright, diffuse light works best. Avoid glare on the card.
- **Distance**: hold the card 15–25 cm from the camera.
- **Angle**: keep the card roughly parallel to the camera lens.
- **Multi-card sets**: scan each card in any order; the app tracks which
  chunks have been received and prompts you until the set is complete.
- **Re-scan**: if a card is rejected, flip it slightly and try again.
  Aztec codes are robust to moderate rotation and perspective distortion.

---

## Architecture notes

### Why Lua 5.4 instead of LuaJIT?

LuaJIT's JIT engine is x86/ARM machine code and cannot be compiled to
WebAssembly.  The standard Lua 5.4 C interpreter compiles cleanly with
Emscripten.  The GLYPHBOX Lua API uses only standard Lua 5.1-compatible
features so cartridges run identically on native (LuaJIT) and web (Lua 5.4).

### Why not ship a separate index.html?

`shell.html` is Emscripten's HTML template — it contains the `{{{ SCRIPT }}}`
placeholder that `emcc` replaces with the generated JS bundle.  The output
`glyphbox.html` is fully self-contained and **is** the index page; rename it
to `index.html` when deploying.

### PLATFORM_WEB guards

All POSIX-specific code in `src/main.c` (fork, exec, FIFO, signals) is
wrapped in `#ifndef PLATFORM_WEB` / `#endif` blocks.  The web build uses:
- `emscripten_set_main_loop()` instead of `while(running)`
- `EMSCRIPTEN_KEEPALIVE void web_load_cart(uint8_t *, int)` as the JS→C cart
  delivery channel
- `EM_ASM(GlyphboxScanner.start())` to open the JS scanner overlay
