# GLYPHBOX — Claude Code Context

This document gives a new Claude Code session complete working context for the GLYPHBOX fantasy console project. Read this before touching any code.

---

## What This Project Is

GLYPHBOX is a software-defined fantasy game console with physical cartridges. Games are written in Lua, built into `.gbcart` binary files, encoded as Aztec codes, and printed on credit-card-sized cards. The physical console (Raspberry Pi) reads cards through its camera. There is also a web emulator and a macOS desktop build.

**Owner:** Gureedo / Jarod Alvarez  
**Copyright:** (C) Gureedo 2026

---

## Console Specifications (Hard Constraints — Do Not Change)

| Property | Value |
|---|---|
| Display | 128 × 128 pixels, 1-bit monochrome (black=0, white=1) |
| Input | D-pad (U/D/L/R) + 1 action button (BTN_A) |
| Audio | 2 cart channels (square/triangle/noise) + 1 system jingle channel |
| Sprites | 8×8 tiles, 1-bit, 128 max per cartridge |
| Tile map | 16×16 tile indices |
| Cartridge format | `.gbcart` binary (magic `GBC1`) |
| Scripting | LuaJIT / Lua 5.4, sandboxed |
| Frame rate | 30 fps hard cap |
| Host | C99 + SDL2 |

### Game Size Limits

The token count is **advisory only** — `tools/token-count.py` exits non-zero when over 2,048 tokens as a design-complexity signal, but `cart-builder.py` never calls it and the runtime has no concept of tokens. Games can and do exceed 2,048 tokens (Star Wars: 4,820 tokens).

The real hard limit is **card count ≤ 8**. Every extra card a player must scan is UX friction; 8 is the practical ceiling for a good experience. Always check card count after building:

```bash
python3 tools/card-print.py cartridges/mygame.gbcart -o /dev/null
# reports: "Cart: mygame.gbcart  (N cards)"
```

The underlying technical ceiling is 65,535 bytes of compressed bytecode (a uint16 range check in `cart-builder.py`) — far larger than any realistic game.

---

## Directory Layout

```
glyphbox/
  src/              C source — the console runtime
  tools/            Python toolchain
  demos/            Lua game source trees (one dir per game)
  cartridges/       Compiled .gbcart files
  cards/            Printed card PDFs
  web/              Emscripten build (CMakeLists.txt, shell.html, scanner.js, style.css)
  docs/             GitHub Pages deployment (web emulator)
  build/            Desktop build output (git-ignored)
  build-web/        Web/WASM build output (git-ignored)
  GLYPHBOX-Software-Guide-ClaudeCode.md   Original v0.2 spec (historical reference)
```

---

## Build Commands

### Desktop (macOS)
```bash
cmake -B build -DPLATFORM=DESKTOP -DCMAKE_BUILD_TYPE=Debug
cmake --build build -j4

# Run with a cart:
./build/glyphbox cartridges/bouncer.gbcart

# Run bare (shows startup animation then splash):
./build/glyphbox
```

### Raspberry Pi (run these ON the Pi)
```bash
cmake -B build -DPLATFORM=PI_HDMI
cmake --build build -j4
./build/glyphbox
```

### Web / WASM (requires Emscripten emsdk active)
```bash
cd web/
cmake -B ../build-web -DCMAKE_TOOLCHAIN_FILE=$EMSDK/upstream/emscripten/cmake/Modules/Platform/Emscripten.cmake
cmake --build ../build-web -j4
# Output: build-web/glyphbox.html + .js + .wasm
# Copy to docs/ for GitHub Pages deploy
```

### Incremental rebuild (fastest)
```bash
cmake --build build -j4
```

---

## Syncing to the Pi

The Pi pulls from GitHub. Workflow:

**Mac (push changes):**
```bash
git add <files>
git commit -m "Description"
git push
```

**Pi (pull and rebuild):**
```bash
git fetch origin
git reset --hard origin/main   # use this, not git pull — avoids divergent branch errors
cmake --build build -j4
```

---

## Console State Machine

Defined in `src/main.c`. States in order:

```c
typedef enum {
    STATE_STARTUP,      // Boot animation + ascending chime (plays once at launch)
    STATE_SPLASH,       // Logo screen, "A: SCAN CARD" prompt
    STATE_SCANNING,     // Camera/QR active, waiting for card
    STATE_CART_LOADED,  // Cart loaded, jingle playing, brief hold
    STATE_RUNNING       // Lua _update/_draw loop active
} ConsoleState;
```

- `g_state` initialises to `STATE_STARTUP` — the startup animation plays automatically on bare launch.
- Passing a cart path as argv[1] skips to `STATE_CART_LOADED` directly.
- ESC during `STATE_STARTUP` skips to `STATE_SPLASH`.
- ESC during `STATE_RUNNING` unloads the cart and returns to `STATE_SPLASH`.
- Reset combo (defined in `input.c`) also returns to `STATE_SPLASH` from `STATE_RUNNING`.

---

## Source Files — What Each Does

| File | Role |
|---|---|
| `src/main.c` | SDL2 init, state machine, `draw_splash()`, `draw_startup()`, `draw_cart_loaded()`, `game_loop_tick()` |
| `src/renderer.c/.h` | 1-bit 128×128 framebuffer, SDL2 blit, all drawing primitives |
| `src/audio.c/.h` | SDL2 audio callback, 2 cart channels + jingle/startup channel, pattern playback |
| `src/input.c/.h` | 5-button state (cur/prev frames), keyboard + gamepad mapping |
| `src/cart.c/.h` | `.gbcart` parser, CRC32 validation, save slot file I/O |
| `src/lua_api.c/.h` | LuaJIT VM, sandbox, full API registration, `_init`/`_update`/`_draw` calls |
| `src/runtime.c/.h` | Frame counter and misc shared state |
| `src/font.h` | 5×7 bitmap font, ASCII 32–126, static C array |

---

## Renderer API (C layer — also exposed to Lua)

```c
renderer_cls(c)                     // clear framebuffer; c=0 black, c=1 white
renderer_pset(x, y, c)              // set pixel
renderer_pget(x, y)                 // read pixel → 0 or 1
renderer_line(x0, y0, x1, y1, c)   // Bresenham line
renderer_rect(x, y, w, h, c)       // 1px outline rectangle
renderer_rectf(x, y, w, h, c)      // filled rectangle
renderer_circ(x, y, r, c)          // 1px outline circle
renderer_circf(x, y, r, c)         // filled circle
renderer_spr(id, x, y, fx, fy)     // blit 8×8 sprite; fx/fy = flip booleans
renderer_map(cx, cy, x, y, w, h)   // blit tile map region
renderer_mset(x, y, tile)          // write tile index to in-memory tilemap (does not persist)
renderer_mget(x, y)                // read tile index from in-memory tilemap → int
renderer_print(str, x, y, c)       // 5×7 bitmap text
renderer_invert()                   // XOR entire framebuffer (toggle black/white)
```

**Coordinate system:** origin (0,0) top-left. Centre of screen = (64, 64). All coords are integers.

**Thick shapes:** use fill+cutout pairs:
```c
renderer_rectf(x,    y,    W,   H,   1);  // outer fill
renderer_rectf(x+t,  y+t,  W-2t, H-2t, 0);  // cutout (t = thickness in px)
```

---

## Audio System

Three independent channels mixed in the SDL2 callback:

| Channel | Variable | Purpose |
|---|---|---|
| Cart ch 0 | `ch[0]` | Square/triangle/noise — Lua `sfx()` ch=0 |
| Cart ch 1 | `ch[1]` | Square/triangle/noise — Lua `sfx()` ch=1 |
| System | `jingle_ch` | Startup chime + cart-load jingle (dedicated, not accessible from Lua) |

Wave types: `0` = square, `1` = triangle, `2` = noise.

**Jingle** (`audio_jingle_play()`) — ascending fanfare played when a cart loads. Uses `JINGLE_SEQ[]`.  
**Startup chime** (`audio_startup_play()`) — ascending chime synced to logo reveal animation. Uses `STARTUP_SEQ[]`. Playing jingle cancels startup chime if still active.

`audio_frame_tick()` — must be called once per frame from the main loop to advance both the startup and jingle sequencers and the cart music/sfx pattern playback.

---

## Startup Animation (`draw_startup`)

Logo elements reveal in sync with `STARTUP_SEQ` note boundaries (frame offsets at 30fps):

| Frame | Event |
|---|---|
| 0–5 | Black screen (C3 bass hit) |
| 6 | Outer ring appears (C4) |
| 11 | Inner ring appears (G4) |
| 16 | Centre square appears (C5) |
| 21 | Dot row appears (E5) |
| 26 | Wordmark appears + 2-frame invert flash (G5 held) |
| 44+ | Resolve note, fade to splash |

After `audio_startup_active()` returns false and `startup_frame > 30`, transitions to `STATE_SPLASH`.

---

## Logo / Splash Layout

All logo drawing is at 128×128 resolution. Logo is centred horizontally. Key coordinates:

```c
// Outer ring (40×40, top-left at 44,28)
renderer_rectf(44, 28, 40, 40, 1);
renderer_rectf(48, 32, 32, 32, 0);   // 4px thick

// Inner ring (24×24, top-left at 52,36)
renderer_rectf(52, 36, 24, 24, 1);
renderer_rectf(56, 40, 16, 16, 0);   // 4px thick

// Centre square (8×8)
renderer_rectf(60, 44,  8,  8, 1);

// 5 dots: 4×4px, x=44,52,60,68,76 (step=8), y=74
for (int i = 0; i < 5; i++)
    renderer_rectf(44 + i * 8, 74, 4, 4, 1);

// Wordmark
renderer_print("GLYPHBOX", 40, 82, 1);
```

---

## Cartridge Format (.gbcart)

Two format versions exist. The builder uses **v0.4 compressed** by default; v0.2 legacy is only produced with `--no-compress`.

### v0.4 Compressed (default)

```
Offset            Size       Content
0x0000            4          Magic: GBC1 (0x47 0x42 0x43 0x31)
0x0004            16         Title (null-padded, max 16 chars)
0x0014            8          Author (null-padded, max 8 chars)
0x001C            2          Version (uint16 LE)
0x001E            2          Flags (uint16 LE) — bit 0x0002 set
0x0020            2          stored_len: compressed bytecode size (uint16 LE)
0x0022            2          raw_len: decompressed bytecode size (uint16 LE)
0x0024            stored_len zlib-compressed LuaJIT bytecode
0x0024+stored_len 1024       Sprite sheet (128 tiles × 8×8 × 1bpp)
…+1024            512        Tile map (16×16 × uint16 LE tile indices)
…+512             512        SFX patterns (16 × 32 bytes)
…+512             256        Music patterns (4 × 64 bytes)
EOF-4             4          CRC32 of all preceding bytes (uint32 LE)
```

Because the compressed bytecode is variable-length, **the sprite sheet and later sections do not have fixed offsets**. Do not assume `0x1020` for the sprite sheet.

### v0.2 Legacy (--no-compress only)

```
Offset   Size    Content
0x0000   4       Magic: GBC1
0x0004   16      Title
0x0014   8       Author
0x001C   2       Version (uint16 LE)
0x001E   2       Flags (uint16 LE) — 0x0000
0x0020   4       Bytecode length prefix (uint32 LE)
0x0024   ≤4092   Raw LuaJIT bytecode (zero-padded to fill slot)
0x1020   1024    Sprite sheet
0x1420   512     Tile map
0x1620   512     SFX patterns
0x1820   256     Music patterns
0x1920   4       CRC32
```

This format enforces a hard 4,092-byte bytecode ceiling (checked in `cart-builder.py`). Fixed offsets apply only here.

Save files: `~/.glyphbox/saves/<CRC32HEX>_<slot>.bin` (4 slots, 64 bytes each). Directories created automatically on first save.

---

## Python Toolchain

```bash
# Build a cartridge from a demo directory
python3 tools/cart-builder.py demos/bouncer/ -o cartridges/bouncer.gbcart

# Check token count (advisory — signals design complexity, not a hard limit)
python3 tools/token-count.py demos/bouncer/game.lua

# Generate print-ready card PDF (ISO ID-1 = 85.6×54mm = actual cut size ~7.5×5cm on printer)
python3 tools/card-print.py cartridges/bouncer.gbcart -o cards/bouncer-print.pdf
python3 tools/card-print.py cartridges/bouncer.gbcart -o cards/bouncer-print.pdf --paper letter
python3 tools/card-print.py cartridges/bouncer.gbcart -o cards/bouncer-rear.pdf --rear-only

# Decode Aztec codes from a card PDF back to .gbcart (test utility)
python3 tools/qr-decode.py cards/bouncer-print.pdf -o /tmp/test.gbcart
```

**TARGET_CHUNK_BYTES** in `card-print.py` is set to **800** bytes per Aztec code. This is the reliable sweet spot — do not raise it. Hello cart = 2 cards, tennis = 4 cards.

**Card insert direction:** Insert arrow is printed on the left edge of the card, pointing left (toward the console slot).

---

## Lua API (available in game cartridges)

**Graphics**
```lua
cls(c)                      -- clear screen (0=black, 1=white)
pset(x, y, c)               -- set pixel
pget(x, y)                  -- get pixel → 0 or 1
line(x0, y0, x1, y1, c)
rect(x, y, w, h, c)         -- outline
rectf(x, y, w, h, c)        -- filled
circ(x, y, r, c)            -- outline
circf(x, y, r, c)           -- filled
spr(id, x, y)               -- blit sprite (no flip)
spr(id, x, y, fx, fy)       -- blit sprite with flip
map(cx, cy, x, y, w, h)     -- blit tile region
mset(x, y, tile)            -- write tile index to tilemap (0–15 coords, runtime only)
mget(x, y)                  -- read tile index from tilemap → integer
print(s, x, y, c)           -- draw text (5×7 font)
invert()                    -- flip entire framebuffer
```

**Input**
```lua
btn(b)     -- 1 if button held
btnp(b)    -- 1 on first frame pressed
btnr(b)    -- 1 on first frame released

-- Button constants:
BTN_U=0  BTN_D=1  BTN_L=2  BTN_R=3  BTN_A=4
```

**Audio**
```lua
sfx(ch, note, vol, wave, dur)   -- play note on channel 0 or 1
sfx(ch, 0)                      -- stop channel
sfx_pat(id)                     -- play SFX pattern (0–15)
music(id)                       -- play music pattern (0–3, loops)
music(-1)                       -- stop music
```

**Math / Utility**
```lua
rnd(n)           -- random integer 0..n-1
mid(a, b, c)     -- median of three values
clamp(v, lo, hi)
flr(n)           -- floor to integer
abs(n)
sin(t)           -- t in turns (0..1), not radians
cos(t)
time()           -- seconds since launch (float)
frame()          -- frame counter (integer, 30fps)
```

**Cart memory**
```lua
peek(addr)             -- read byte from cart ROM
save(slot, data)       -- write string to save slot (0–3)
load(slot)             -- read save slot → string or nil
```

**Expansion scanning** *(native/Pi only — no-op on PLATFORM_WEB)*
```lua
scan_begin()           -- start the camera scanner mid-game
scan_poll()            -- nil = still scanning
                       -- false = scan failed or no data captured
                       -- table = expansion data, keyed by slot index
                       --   e.g. result[1], result[2], result[3]
```

`scan_poll()` loads the scanned cart into a temporary sandboxed VM, runs its `_init()` with a mock `save()` interceptor, and returns whatever that `_init()` wrote to slots 0–3 as a Lua table. The running game is never interrupted — the game controls its own scanning UI.

**Expansion cart contract** — an expansion cart is a normal `.gbcart` whose `_init()` only calls `save()` to write data payloads (≤ 64 bytes each, slots 0–3). When scanned mid-game via `scan_poll()`, only `_init()` executes; `_update()` and `_draw()` are ignored. When run standalone (scanned normally at the splash screen) the full game loop runs as usual, allowing the expansion cart to show a confirmation screen.

```lua
-- Minimal expansion cart _init():
function _init()
  save(1, "3"..HOLE_RLE_A)
  save(2, "4"..HOLE_RLE_B)
  save(3, "5"..HOLE_RLE_C)
end
```

**Game loop contract**
```lua
function _init()   end   -- called once on cart load
function _update() end   -- called every frame (30fps)
function _draw()   end   -- called every frame after _update
```

**Sandbox:** `io`, `os`, `package`, `require`, `dofile`, `load`, `loadfile`, `debug`, `collectgarbage` are all removed. `math`, `table`, `string` are fully available.

---

## Platform Guards

Three build targets, controlled by `#define`:

| Define | Set when | Use for |
|---|---|---|
| `PLATFORM_WEB` | Emscripten build | No POSIX fork/exec; JS drives scanning; `emscripten_set_main_loop` |
| `PLATFORM_PI_HDMI` | Pi build | Fullscreen window; picamera2 scanning via subprocess |
| *(neither)* | Desktop build | Webcam or file-arg cart loading |

**Critical rule:** Never add `<unistd.h>`, `<sys/wait.h>`, `<fcntl.h>`, or `fork()`/`exec()` calls outside of `#ifndef PLATFORM_WEB` guards. The WASM build will fail silently or with confusing linker errors.

**Web-specific:** `web_load_cart(const uint8_t *data, int len)` is the `EMSCRIPTEN_KEEPALIVE` entry point called from JavaScript after the Aztec scanner assembles all chunks. `len == 0` is a cancel signal → returns to `STATE_SPLASH`.

---

## Web Scanner (docs/ + web/)

- `scanner.js` — uses **zxing-wasm** (C++ ZXing compiled to WASM via ESM import). Reads `r.bytes` (raw `Uint8Array`) to avoid encoding corruption of bytes > 127.
- Payload format per Aztec chunk: `bytes[0]=chunk_index, bytes[1]=total_chunks, bytes[2]=flags(0x01=zlib), bytes[3+]=data`
- Assembly: concatenate chunks in order → `pako.inflate()` → call `web_load_cart`
- Deployed to GitHub Pages via `docs/` folder at: `https://jarodalvarez.github.io/glyphbox/`

---

## Current Cartridge Roster

| File | Demo |
|---|---|
| `hello.gbcart` | Hello world, baseline scan test |
| `bouncer.gbcart` | Bouncing ball, invert toggle |
| `runner.gbcart` | Side-scroller, obstacle dodge, score |
| `dungeon.gbcart` | Top-down dungeon, D-pad, save/load |
| `pac.gbcart` | Pac-Man style |
| `tennis.gbcart` | Pong/tennis (~1398 tokens, 4 cards to print) |
| `sw.gbcart` | Star Wars (~4820 tokens, 8 cards to print — current ceiling) |
| `bukobuko.gbcart` | RPS game |
| `rpg.gbcart` | RPG |
| `dk.gbcart` | Donkey Kong style |
| `sta.gbcart` | Space shooter |
| `putt.gbcart` | Golf — 4 holes, real ball physics, putting sub-game, expansion-ready |

---

## Common Mistakes to Avoid

1. **Don't raise `TARGET_CHUNK_BYTES` above 800** in `card-print.py` — dense Aztec codes fail to scan reliably on the Pi camera.
2. **Don't use `git pull` on the Pi** — use `git fetch origin && git reset --hard origin/main` to avoid divergent branch errors.
3. **Don't add POSIX headers outside `#ifndef PLATFORM_WEB`** — breaks the Emscripten build.
4. **Don't use `renderer_rect` for thick outlines** — it draws 1px. Use fill+cutout pairs with `renderer_rectf`.
5. **Token count is advisory, card count is the real limit** — `token-count.py` signals design complexity but is never called by the build pipeline. After building, run `card-print.py` and confirm the game prints to ≤ 8 cards. Star Wars is the current ceiling at 8 cards.
6. **`mkdir` on macOS/Linux only creates one level** — `~/.glyphbox/saves/` requires creating `~/.glyphbox` first (already handled in `cart.c`).
7. **`audio_frame_tick()` must be called every frame** — jingle and startup chime sequencers only advance when this is called.
8. **`sin()`/`cos()` in Lua use turns (0.0–1.0), not radians** — this is intentional and differs from standard Lua.
9. **Save slots are scoped per-cart by CRC32** — two different `.gbcart` files never share save slots, even with identical metadata. Use the expansion scan mechanic (`scan_begin`/`scan_poll`) to pass data between carts at runtime.
10. **`scan_begin()`/`scan_poll()` are no-ops on `PLATFORM_WEB`** — the web build has no mid-game scanning path. Games that use expansion scanning should gate that UI behind a platform check or gracefully handle `scan_poll()` always returning `false`.
