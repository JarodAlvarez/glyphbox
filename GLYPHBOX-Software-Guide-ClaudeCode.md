# GLYPHBOX — Software Implementation Guide
### For Claude Code · Prototype v0.2

---

## HOW TO USE THIS DOCUMENT

This document is written to be read by Claude Code in a single session. It contains everything needed to implement the GLYPHBOX fantasy console runtime from scratch — no prior context required.

**Recommended opening prompt:**
```
Read this entire document before writing any code. Then produce a numbered implementation plan covering every file you will create. Wait for approval before starting.
```

**Phased session prompt (more reliable for large projects):**
```
Read this document. Implement Section [N] only. Run the verification test described. Report completion before proceeding.
```

---

## WHAT YOU ARE BUILDING

A software-defined fantasy game console called **GLYPHBOX**. The deliverable is a working desktop simulator — a window on screen that IS the console, keyboard-controlled, capable of loading and running GLYPHBOX game cartridges (`.gbcart` files).

### Console Specifications (Non-Negotiable Constraints)
| Property | Value |
|---|---|
| Display | 128 × 128 pixels, 1-bit monochrome (black or white only) |
| Input | 4-way cardinal D-pad + 1 action button (Atari 2600 model) |
| Audio | 2-channel synthesis (square wave + noise) |
| Code limit | 2,048 Lua tokens per cartridge (enforced at load time) |
| Sprites | 8×8 tiles, 1-bit, max 128 tiles per cartridge |
| Map | 16×16 tile indices, max |
| Cartridge format | `.gbcart` binary, QR-encodable |
| Scripting | Lua 5.4 / LuaJIT, sandboxed |
| Host | C99 + SDL2 |
| Frame rate | 30 fps hard cap |

### Deliverables
1. `glyphbox` — compiled runtime executable
2. `tools/cart-builder.py` — assembles `.gbcart` from source assets
3. `tools/token-count.py` — counts Lua tokens, enforces 2048 limit
4. `tools/qr-encode.py` — encodes `.gbcart` to printable card PDF
5. `demos/bouncer/` — validation demo 1
6. `demos/runner/` — validation demo 2
7. `demos/dungeon/` — validation demo 3

---

## SECTION 01 — TECHNOLOGY STACK

Install all dependencies before writing any code.

| Component | Technology | Install |
|---|---|---|
| C compiler | GCC or Clang, C99 | `xcode-select --install` / `apt install build-essential` |
| Build system | CMake 3.20+ | `brew install cmake` / `apt install cmake` |
| Display + audio + input | SDL2 2.0.20+ | `brew install sdl2` / `apt install libsdl2-dev` |
| Lua engine | LuaJIT 2.1 | `brew install luajit` / `apt install libluajit-5.1-dev` |
| QR decode | ZBar | `brew install zbar` / `apt install libzbar-dev` |
| CRC32 | zlib | Included on most systems; link with `-lz` |
| Python tools | Python 3.10+ | `python.org` |
| Aztec QR encode | aztec-code-generator | `pip install aztec-code-generator` |
| PDF generation | ReportLab + Pillow | `pip install reportlab pillow` |
| QR decode (Python) | pyzbar | `pip install pyzbar` |

---

## SECTION 02 — PROJECT STRUCTURE

Create this exact directory and file layout. All `.c` and `.h` files start as stubs with correct include guards. Do not begin implementation until the full structure exists.

```
glyphbox/
  CMakeLists.txt
  README.md
  src/
    main.c                  # SDL2 init; main loop; 30fps frame timing
    runtime.h
    runtime.c               # top-level console state; orchestrates all modules
    renderer.h
    renderer.c              # 1-bit 128x128 framebuffer; SDL2 blit pipeline
    audio.h
    audio.c                 # 2-channel software synthesizer; SDL2 audio callback
    input.h
    input.c                 # 5-button state machine; SDL2 keyboard mapping
    cart.h
    cart.c                  # .gbcart binary parser; CRC32 validation; save slots
    lua_api.h
    lua_api.c               # LuaJIT VM setup; sandbox; full API registration
    font.h                  # 5x7 1-bit bitmap font as static C uint8_t array
  tools/
    cart-builder.py
    token-count.py
    qr-encode.py
    qr-decode.py            # test utility: decode QR image back to .gbcart
  demos/
    bouncer/
      game.lua
      sprites.txt
      tilemap.txt
      sfx.txt
      music.txt
      meta.toml
    runner/
      (same structure)
    dungeon/
      (same structure)
  cartridges/               # assembled .gbcart output files go here
  cards/                    # generated card PDFs go here
```

### Stub file requirements
- Every `.h` file: include guard `#ifndef GLYPHBOX_X_H` / `#define GLYPHBOX_X_H` / `#endif`
- Every `.c` file: include its own `.h`, plus a one-line comment describing the module's role
- `CMakeLists.txt`: exists but is empty until Section 03

### Verification test
```
ls -R glyphbox/src glyphbox/tools glyphbox/demos
```
All directories and files must exist before proceeding.

---

## SECTION 03 — BUILD SYSTEM (CMakeLists.txt)

Write the complete `CMakeLists.txt` at the project root.

### Requirements
- `cmake_minimum_required(VERSION 3.20)`
- `set(CMAKE_C_STANDARD 99)` and `set(CMAKE_C_STANDARD_REQUIRED ON)`
- Find SDL2 via `find_package(SDL2)` or `pkg_check_modules(SDL2 sdl2)`
- Find LuaJIT via `pkg_check_modules(LUAJIT luajit)`
- Find ZBar via `pkg_check_modules(ZBAR zbar)`
- Compile all `.c` files in `src/`
- Link: SDL2, SDL2main, luajit-5.1, zbar, z (zlib), m (math)
- macOS only: add `-framework CoreAudio -framework AudioUnit -framework CoreFoundation`
- Output executable named `glyphbox`
- Support both `Debug` (`-g`, no optimisation) and `Release` (`-O2`) configurations
- Add a `-DPLATFORM` option: `DESKTOP` (default), `PI_HDMI`, `PI_SPI` — used later for Pi deployment; ignored for now

### Build commands
```bash
cd glyphbox
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Debug
make -j4
```

### Verification test
CMake must configure and `make` must compile without errors, producing the `glyphbox` executable. A run with no arguments should print `GLYPHBOX: no cartridge specified` and exit cleanly.

---

## SECTION 04 — 1-BIT RENDERER (renderer.c / renderer.h)

### Framebuffer

A 2,048-byte static array. Each bit is one pixel. Pixel `(x, y)` is at bit index `y * 128 + x`.

```c
static uint8_t fb[2048];  // 128 * 128 / 8

void renderer_pset(int x, int y, int c) {
    if (x < 0 || x > 127 || y < 0 || y > 127) return;
    int i = y * 128 + x;
    if (c) fb[i >> 3] |=  (1 << (i & 7));
    else   fb[i >> 3] &= ~(1 << (i & 7));
}

int renderer_pget(int x, int y) {
    int i = y * 128 + x;
    return (fb[i >> 3] >> (i & 7)) & 1;
}
```

`cls(c)` maps to `memset(fb, c ? 0xFF : 0x00, 2048)`.
`invert()` maps to `for (int i = 0; i < 2048; i++) fb[i] ^= 0xFF;`

### SDL2 Blit Pipeline

- Create one `SDL_Texture` at init: 128×128, `SDL_PIXELFORMAT_RGBA8888`, `SDL_TEXTUREACCESS_STREAMING`
- Set `SDL_SetHint(SDL_HINT_RENDER_SCALE_QUALITY, "0")` before creating renderer — this enforces nearest-neighbour scaling
- Each frame: `SDL_LockTexture` → expand each bit to `0x000000FF` (black) or `0xFFFFFFFF` (white) → `SDL_UnlockTexture` → `SDL_RenderCopy` to window
- Window size: 512×512 (128 × 4 scale) for desktop

### Drawing Primitives — implement all of these

| Function signature | Algorithm | Notes |
|---|---|---|
| `renderer_line(x0,y0,x1,y1,c)` | Bresenham integer line | No floating point |
| `renderer_rect(x,y,w,h,c)` | Four `renderer_line` calls | Outline only |
| `renderer_rectf(x,y,w,h,c)` | Horizontal span fill | Row-by-row loop calling `renderer_pset` |
| `renderer_circ(x,y,r,c)` | Midpoint circle, 8-point symmetry | Integer only |
| `renderer_circf(x,y,r,c)` | Scanline span fill inside radius | One span per row |
| `renderer_spr(id,x,y,fx,fy)` | 1-bit bitplane blit from sprite array | `fx`/`fy` = horizontal/vertical flip booleans |
| `renderer_map(cx,cy,x,y,w,h)` | Iterate tile indices, call `renderer_spr` per tile | `cx`/`cy` = map tile origin |
| `renderer_print(str,x,y,c)` | 5×7 bitmap font blit | Font data in `font.h` |

### font.h

A static `uint8_t` array of 5×7 glyphs for ASCII characters 32–126. Each glyph is 5 bytes wide × 7 bytes tall, stored row-major. Claude Code should generate this from a standard 5×7 pixel font definition — include at minimum: uppercase A-Z, digits 0-9, space, and common punctuation `!?.,:-/()`.

### renderer_debug_ascii()

A test-only function that prints the framebuffer to stdout as `#` (white) and `.` (black) characters, 128 characters wide. Used for unit testing without a display.

```c
void renderer_debug_ascii(void) {
    for (int y = 0; y < 128; y++) {
        for (int x = 0; x < 128; x++)
            putchar(renderer_pget(x, y) ? '#' : '.');
        putchar('\n');
    }
}
```

### Public API (renderer.h exports)
```c
void renderer_init(SDL_Renderer *r);
void renderer_frame(void);           // blit framebuffer to SDL texture
void renderer_cls(int c);
void renderer_pset(int x, int y, int c);
int  renderer_pget(int x, int y);
void renderer_line(int x0, int y0, int x1, int y1, int c);
void renderer_rect(int x, int y, int w, int h, int c);
void renderer_rectf(int x, int y, int w, int h, int c);
void renderer_circ(int x, int y, int r, int c);
void renderer_circf(int x, int y, int r, int c);
void renderer_spr(int id, int x, int y, int fx, int fy);
void renderer_map(int cx, int cy, int x, int y, int w, int h);
void renderer_print(const char *str, int x, int y, int c);
void renderer_invert(void);
void renderer_set_sprites(const uint8_t *data); // called by cart loader
void renderer_set_tilemap(const uint8_t *data); // called by cart loader
void renderer_debug_ascii(void);
```

### Verification test
Write a temporary `main()` in a test file that calls:
```c
renderer_cls(0);
renderer_circf(64, 64, 30, 1);
renderer_rect(10, 10, 20, 20, 1);
renderer_print("GLYPHBOX", 20, 118, 1);
renderer_debug_ascii();
```
A circle, a rectangle outline, and text must be visible in the ASCII output.

---

## SECTION 05 — AUDIO SYNTHESIZER (audio.c / audio.h)

### SDL2 Audio Spec
```c
SDL_AudioSpec spec = {
    .freq     = 44100,
    .format   = AUDIO_S16SYS,
    .channels = 1,        // mono
    .samples  = 512,
    .callback = audio_callback,
    .userdata = &audio_state
};
```

### Channel State Struct
```c
typedef struct {
    int    note;        // MIDI 0-127; 0 = silent
    int    vol;         // 0-7
    int    wave;        // 0=square  1=triangle  2=noise
    int    dur;         // frames remaining; -1 = hold indefinitely
    int    attack;      // attack in frames
    int    release;     // release in frames
    double phase;       // oscillator phase accumulator 0.0..1.0
    double phase_inc;   // per-sample phase increment = freq / 44100
    int    env_frame;   // envelope position counter
} Channel;

static Channel ch[2];   // ch[0] = tone only; ch[1] = tone or noise
```

### Waveform Generation (inside callback, per sample)

```c
// MIDI note to frequency
double freq = 440.0 * pow(2.0, (note - 69) / 12.0);
double phase_inc = freq / 44100.0;

// Square wave
double sample = (ch[i].phase < 0.5) ? 1.0 : -1.0;

// Triangle wave
double sample = 1.0 - 4.0 * fabs(ch[i].phase - 0.5);

// Noise (channel 1 only)
double sample = (rand() & 1) ? 1.0 : -1.0;  // phase ignored

// Advance phase
ch[i].phase += ch[i].phase_inc;
if (ch[i].phase >= 1.0) ch[i].phase -= 1.0;
```

### Envelope

Apply a linear amplitude envelope inside the callback:
- During attack frames: amplitude ramps from 0 to `vol/7.0`
- During sustain: constant at `vol/7.0`
- During release frames: ramps from `vol/7.0` to 0
- After release: channel goes silent

Scale the raw waveform sample by the envelope amplitude, then scale to int16 range (`* 28000`). Mix both channels by averaging.

### SDL2 Thread Safety

When the main thread modifies channel state (via `audio_sfx()` etc.), it must use:
```c
SDL_LockAudioDevice(audio_device_id);
// ... modify ch[] ...
SDL_UnlockAudioDevice(audio_device_id);
```

### Stored Patterns

The audio module holds storage for:
- 16 SFX patterns — each is an array of up to 32 notes per channel
- 4 music patterns — each loops until stopped

```c
typedef struct { uint8_t note, vol, wave, dur; } NoteEvent;
typedef struct { NoteEvent ch0[32]; NoteEvent ch1[32]; uint8_t len; } SfxPattern;
typedef struct { uint8_t sfx_ids[64]; uint8_t len; } MusicPattern;
```

`audio_set_sfx_data()` and `audio_set_music_data()` are called by the cart loader after parsing.

### Public API (audio.h exports)
```c
void audio_init(void);
void audio_shutdown(void);
void audio_sfx(int ch, int note, int vol, int wave, int dur);
void audio_sfx_pat(int id);
void audio_music(int id);    // -1 = stop
void audio_frame_tick(void); // called each frame to advance pattern playback
void audio_set_sfx_data(const uint8_t *data, size_t len);
void audio_set_music_data(const uint8_t *data, size_t len);
```

### Verification test
In a temporary main, call `audio_init()`, then `audio_sfx(0, 69, 7, 0, 60)` (A4, 440Hz, full volume, square wave, 2 seconds). Run for 2 seconds. You should hear a clear square wave tone.

---

## SECTION 06 — INPUT HANDLER (input.c / input.h)

### Button Indices
```c
#define BTN_U     0    // D-pad up
#define BTN_D     1    // D-pad down
#define BTN_L     2    // D-pad left
#define BTN_R     3    // D-pad right
#define BTN_A     4    // action button
#define BTN_COUNT 5
```

### State Arrays
```c
static uint8_t cur[BTN_COUNT];   // held this frame
static uint8_t prev[BTN_COUNT];  // held last frame
```

### Implementation
```c
void input_update(void) {
    memcpy(prev, cur, BTN_COUNT);
    const uint8_t *ks = SDL_GetKeyboardState(NULL);
    cur[BTN_U] = ks[SDL_SCANCODE_UP]    || ks[SDL_SCANCODE_W];
    cur[BTN_D] = ks[SDL_SCANCODE_DOWN]  || ks[SDL_SCANCODE_S];
    cur[BTN_L] = ks[SDL_SCANCODE_LEFT]  || ks[SDL_SCANCODE_A];
    cur[BTN_R] = ks[SDL_SCANCODE_RIGHT] || ks[SDL_SCANCODE_D];
    cur[BTN_A] = ks[SDL_SCANCODE_Z]     || ks[SDL_SCANCODE_SPACE];
}

int input_btn(int b)  { return cur[b]; }
int input_btnp(int b) { return  cur[b] && !prev[b]; }
int input_btnr(int b) { return !cur[b] &&  prev[b]; }
```

### Public API (input.h exports)
```c
void input_init(void);
void input_update(void);
void input_shutdown(void);
int  input_btn(int b);
int  input_btnp(int b);
int  input_btnr(int b);
```

### Keyboard Mapping Summary
| Button | Primary Key | Alternate Key |
|---|---|---|
| BTN_U | Arrow Up | W |
| BTN_D | Arrow Down | S |
| BTN_L | Arrow Left | A |
| BTN_R | Arrow Right | D |
| BTN_A | Z | Space |

### Verification test
Temporary main: print `"BTN_A PRESSED"` to stdout each frame that `input_btnp(BTN_A)` is true. Confirm Z key triggers exactly once per press, not continuously.

---

## SECTION 07 — LUA BRIDGE & SANDBOX (lua_api.c / lua_api.h)

### VM Setup
```c
lua_State *L = luaL_newstate();

// Load only safe standard libraries
luaopen_base(L);
luaopen_math(L);
luaopen_table(L);
luaopen_string(L);

// Remove all dangerous globals
const char *remove[] = {
    "io", "os", "package", "require", "dofile",
    "load", "loadfile", "loadstring", "debug",
    "collectgarbage", "newproxy", NULL
};
for (int i = 0; remove[i]; i++) {
    lua_pushnil(L);
    lua_setglobal(L, remove[i]);
}
```

### Registering a C Function
```c
static int l_pset(lua_State *L) {
    int x = luaL_checkinteger(L, 1);
    int y = luaL_checkinteger(L, 2);
    int c = luaL_checkinteger(L, 3);
    renderer_pset(x, y, c);
    return 0;  // number of Lua return values
}
// Register:
lua_pushcfunction(L, l_pset);
lua_setglobal(L, "pset");
```

### Complete API Registration Table

Register every function in this table. This is the complete and final GLYPHBOX Lua API surface.

**Graphics**
| Lua name | C implementation calls | Lua return values |
|---|---|---|
| `cls(c)` | `renderer_cls(c)` | 0 |
| `pset(x,y,c)` | `renderer_pset(x,y,c)` | 0 |
| `pget(x,y)` | `renderer_pget(x,y)` | 1 (integer 0 or 1) |
| `line(x0,y0,x1,y1,c)` | `renderer_line(...)` | 0 |
| `rect(x,y,w,h,c)` | `renderer_rect(...)` | 0 |
| `rectf(x,y,w,h,c)` | `renderer_rectf(...)` | 0 |
| `circ(x,y,r,c)` | `renderer_circ(...)` | 0 |
| `circf(x,y,r,c)` | `renderer_circf(...)` | 0 |
| `spr(id,x,y)` | `renderer_spr(id,x,y,0,0)` | 0 |
| `spr(id,x,y,fx,fy)` | `renderer_spr(id,x,y,fx,fy)` | 0 |
| `map(cx,cy,x,y,w,h)` | `renderer_map(...)` | 0 |
| `print(s,x,y,c)` | `renderer_print(...)` | 0 |
| `invert()` | `renderer_invert()` | 0 |

**Input**
| Lua name | C implementation calls | Lua return values |
|---|---|---|
| `btn(b)` | `input_btn(b)` | 1 (integer 0 or 1) |
| `btnp(b)` | `input_btnp(b)` | 1 |
| `btnr(b)` | `input_btnr(b)` | 1 |

**Audio**
| Lua name | C implementation calls | Lua return values |
|---|---|---|
| `sfx(ch,note,vol,wave,dur)` | `audio_sfx(...)` | 0 |
| `sfx(ch,0)` | `audio_sfx(ch,0,0,0,0)` | 0 |
| `sfx_pat(id)` | `audio_sfx_pat(id)` | 0 |
| `music(id)` | `audio_music(id)` | 0 |
| `music(nil)` | `audio_music(-1)` | 0 |

**Math & Utility**
| Lua name | C implementation | Lua return values |
|---|---|---|
| `rnd(n)` | `rand() % n` | 1 |
| `mid(a,b,c)` | return median of three | 1 |
| `clamp(v,lo,hi)` | `v < lo ? lo : v > hi ? hi : v` | 1 |
| `flr(n)` | `floor(n)` (cast to int) | 1 |
| `abs(n)` | `fabs(n)` | 1 |
| `sin(t)` | `sin(t * 2.0 * M_PI)` | 1 |
| `cos(t)` | `cos(t * 2.0 * M_PI)` | 1 |
| `time()` | `SDL_GetTicks() / 1000.0` | 1 (float) |
| `frame()` | runtime frame counter | 1 (integer) |

**Cartridge Memory**
| Lua name | C implementation calls | Lua return values |
|---|---|---|
| `peek(addr)` | read byte from cart ROM | 1 |
| `save(slot, data)` | `cart_save(slot, data, len)` | 0 |
| `load(slot)` | `cart_load_save(slot)` | 1 (string or nil) |

### Button Constants — inject as Lua globals
```c
lua_pushinteger(L, 0); lua_setglobal(L, "BTN_U");
lua_pushinteger(L, 1); lua_setglobal(L, "BTN_D");
lua_pushinteger(L, 2); lua_setglobal(L, "BTN_L");
lua_pushinteger(L, 3); lua_setglobal(L, "BTN_R");
lua_pushinteger(L, 4); lua_setglobal(L, "BTN_A");
```

### Loading and Calling Game Code
```c
// Load compiled Lua bytecode
luaL_loadbuffer(L, bytecode, bytecode_len, cart_title);
lua_pcall(L, 0, 0, 0);   // execute the module (defines _init, _update, _draw)

// Call _init once after loading
lua_getglobal(L, "_init");
if (lua_isfunction(L, -1)) lua_pcall(L, 0, 0, 0);
else lua_pop(L, 1);

// Every frame — call _update then _draw
lua_getglobal(L, "_update");
if (lua_isfunction(L, -1)) lua_pcall(L, 0, 0, 0);
else lua_pop(L, 1);

lua_getglobal(L, "_draw");
if (lua_isfunction(L, -1)) lua_pcall(L, 0, 0, 0);
else lua_pop(L, 1);
```

On any `lua_pcall` error: retrieve the error string with `lua_tostring(L, -1)`, print it to stderr prefixed with the cartridge title, and `lua_pop(L, 1)`.

### Public API (lua_api.h exports)
```c
void lua_api_init(void);
void lua_api_shutdown(void);
int  lua_api_load(const uint8_t *bytecode, size_t len, const char *title);
void lua_api_call_init(void);
void lua_api_call_update(void);
void lua_api_call_draw(void);
void lua_api_set_cart(Cart *cart);  // gives lua_api access to cart ROM for peek()
```

### Verification test
Load this Lua string inline (compile to bytecode first with `luaL_loadstring`, not from file):
```lua
function _draw()
  cls(0)
  circf(64, 64, 30, 1)
  print("HELLO", 44, 60, 0)
end
```
Run for 60 frames. A white circle with black text must appear in the SDL window.

---

## SECTION 08 — CARTRIDGE LOADER (cart.c / cart.h)

### Cart Struct
```c
typedef struct {
    char     title[17];          // null-terminated, max 16 chars
    char     author[9];          // null-terminated, max 8 chars
    uint16_t version;
    uint16_t flags;
    uint8_t *bytecode;           // heap-allocated Lua bytecode
    size_t   bytecode_len;
    uint8_t  sprites[1024];      // 128 tiles × 8×8 × 1bpp
    uint8_t  tilemap[512];       // 16×16 tile indices, 2 bytes each
    uint8_t  sfx_data[512];      // 16 SFX patterns × 32 bytes
    uint8_t  music_data[256];    // 4 music patterns × 64 bytes
    uint32_t crc32;              // stored checksum (last 4 bytes of file)
} Cart;
```

### Binary Format (.gbcart)
```
Offset   Size    Content
0x0000   4       Magic: 0x47 0x42 0x43 0x31 ('GBC1')
0x0004   16      Title (null-padded)
0x0014   8       Author (null-padded)
0x001C   2       Version (uint16 LE)
0x001E   2       Flags (uint16 LE)
0x0020   ≤4096   Lua bytecode
0x1020   1024    Sprite sheet (128 × 8×8 × 1bpp)
0x1420   512     Tile map (16×16 × 2 bytes)
0x1620   512     SFX patterns
0x1820   256     Music patterns
EOF-4    4       CRC32 of all preceding bytes (uint32 LE)
```

### Load Sequence
1. Read entire file into buffer
2. Check bytes 0–3 == `{ 0x47, 0x42, 0x43, 0x31 }`. Fail with clear error if not.
3. Compute `zlib crc32(0, buffer, len - 4)`. Compare to `uint32` at `buffer[len - 4]`. Fail if mismatch.
4. Parse header fields from offsets above into `Cart` struct
5. Copy bytecode: `cart->bytecode_len = 0x1020 - 0x0020 = 4096` max; find actual length from file size
6. `memcpy` sprites, tilemap, sfx_data, music_data from their offsets
7. Return heap-allocated `Cart*`. Caller calls `cart_free()` when done.

### Save Slots
4 save slots, 64 bytes each. Stored as files at:
```
~/.glyphbox/saves/<crc32_hex>_<slot>.bin
```
Create the directory if it does not exist. `cart_save(cart, slot, data, len)` writes the file. `cart_load_save(cart, slot)` reads it and returns a Lua string, or `nil` via the Lua stack if file doesn't exist.

### Public API (cart.h exports)
```c
Cart *cart_load_file(const char *path);
void  cart_free(Cart *cart);
void  cart_save(Cart *cart, int slot, const uint8_t *data, size_t len);
// cart_load_save is called from lua_api.c and pushes result onto Lua stack
void  cart_load_save_lua(lua_State *L, Cart *cart, int slot);
```

### Verification test
Construct a minimal valid `.gbcart` by hand in Python (write magic, 28-byte header of zeros, 4096 bytes of zero bytecode, 1024+512+512+256 bytes of zeros, then CRC32 of all preceding bytes). Load it with `cart_load_file()`. Print title and author. Confirm no errors.

---

## SECTION 09 — MAIN LOOP (main.c / runtime.c)

### main.c responsibilities
1. Parse command-line argument for cartridge path
2. `SDL_Init(SDL_INIT_VIDEO | SDL_INIT_AUDIO)`
3. Create SDL window (512×512, titled "GLYPHBOX")
4. Create SDL renderer (accelerated, vsync off)
5. Call `renderer_init()`, `audio_init()`, `input_init()`, `lua_api_init()`
6. If cart path provided: `cart_load_file()` → `lua_api_set_cart()` → `renderer_set_sprites()` → `renderer_set_tilemap()` → `audio_set_sfx_data()` → `audio_set_music_data()` → `lua_api_load()` → `lua_api_call_init()`
7. Enter main loop
8. On exit: `lua_api_shutdown()`, `audio_shutdown()`, `input_shutdown()`, `SDL_Quit()`

### Main Loop (30fps fixed timestep)
```c
const int TARGET_FPS = 30;
const int FRAME_MS   = 1000 / TARGET_FPS;  // 33ms

uint32_t last = SDL_GetTicks();
while (running) {
    // 1. Process SDL events
    SDL_Event e;
    while (SDL_PollEvent(&e)) {
        if (e.type == SDL_QUIT) running = 0;
        if (e.type == SDL_KEYDOWN && e.key.keysym.sym == SDLK_ESCAPE) running = 0;
    }

    // 2. Update input state
    input_update();

    // 3. Call Lua _update and _draw
    lua_api_call_update();
    lua_api_call_draw();

    // 4. Advance audio pattern playback
    audio_frame_tick();

    // 5. Blit framebuffer to screen
    SDL_RenderClear(sdl_renderer);
    renderer_frame();
    SDL_RenderPresent(sdl_renderer);

    // 6. Cap to 30fps
    uint32_t now = SDL_GetTicks();
    int elapsed = now - last;
    if (elapsed < FRAME_MS) SDL_Delay(FRAME_MS - elapsed);
    last = SDL_GetTicks();

    frame_counter++;
}
```

### Splash Screen
If no cartridge is provided, display a splash screen using the renderer API:
```lua
-- equivalent rendering logic in C using renderer_* functions:
cls(0)
rectf(0, 0, 128, 128, 0)
print("GLYPHBOX", 28, 55, 1)
print("INSERT CARTRIDGE", 8, 70, 1)
```
Animate a blinking cursor using `frame_counter % 30 < 15`.

### Verification test
Run `./glyphbox` with no argument. Splash screen must appear. Run `./glyphbox path/to/bouncer.gbcart`. BOUNCER must launch. Escape key must exit cleanly.

---

## SECTION 10 — PYTHON TOOLCHAIN

### tools/token-count.py

Counts Lua tokens in a source file. A token is any of: keyword, identifier, string literal, number literal, operator, punctuation symbol. Whitespace and comments (`--` line comments, `--[[ ]]` block comments) are excluded.

Lua keywords to count as tokens:
```
and break do else elseif end false for function goto if in
local nil not or repeat return then true until while
```

Output format:
```
Tokens: 1847 / 2048  [OK]
Tokens: 2103 / 2048  [OVER LIMIT — 55 tokens over]
```

Usage: `python tools/token-count.py demos/bouncer/game.lua`

Exit code 0 if within limit, 1 if over.

---

### tools/cart-builder.py

Assembles a `.gbcart` binary from a game project directory.

**Input files expected in project directory:**
- `game.lua` — Lua source code
- `sprites.txt` — 128 blocks of 8 lines of 8 characters (`0` or `1`), separated by blank lines
- `tilemap.txt` — 16 lines of 16 space-separated integers (sprite indices 0–127)
- `sfx.txt` — 16 SFX patterns in plain text format (define your own simple format)
- `music.txt` — 4 music patterns
- `meta.toml` — `title`, `author`, `version` fields

**Assembly steps:**
1. Read `meta.toml` → extract title (max 16 chars), author (max 8 chars), version
2. Compile `game.lua` to LuaJIT bytecode: `subprocess.run(["luajit", "-b", "game.lua", "-"], capture_output=True)`
3. Parse `sprites.txt` → 1024-byte bitplane (pack 8 pixels per byte, MSB first, row-major per tile)
4. Parse `tilemap.txt` → 512 bytes (16×16 × 2 bytes each, little-endian uint16)
5. Parse `sfx.txt` and `music.txt` → 512 and 256 bytes respectively
6. Write binary: magic + header + bytecode (zero-padded to 4096) + sprites + tilemap + sfx + music
7. Compute `zlib.crc32()` of all bytes written so far
8. Append CRC32 as 4-byte little-endian uint32

Usage: `python tools/cart-builder.py demos/bouncer/ -o cartridges/bouncer.gbcart`

---

### tools/qr-encode.py

Encodes a `.gbcart` file into a print-ready PDF card.

**Steps:**
1. Read `.gbcart` file into bytes
2. Split at midpoint: `payload_a = data[:len//2]`, `payload_b = data[len//2:]`
3. Encode each as Aztec code using `aztec_code_generator` library
4. Use `reportlab` to produce a PDF at CR80 dimensions (85.6mm × 54mm) at 600 DPI
5. Card front: blank white
6. Card rear: Code A in upper half (25mm × 25mm), Code B in lower half (25mm × 25mm), title text below Code B in 6pt font, corner chamfer indicator (small triangle in bottom-right corner marking correct insertion orientation)

Usage: `python tools/qr-encode.py cartridges/bouncer.gbcart -o cards/bouncer-card.pdf`

---

## SECTION 11 — DEMO CARTRIDGES

All three demos must build and run without errors before the project is considered complete.

---

### Demo 1: BOUNCER

**Purpose:** Validates game loop, circf, cls, btn/btnp, basic arithmetic. Simplest possible game.

**Complete Lua source:**
```lua
function _init()
  x, y, vx, vy = 64, 64, 2.1, 1.7
  inv = false
end

function _update()
  x = x + vx
  y = y + vy
  if x < 4 or x > 123 then vx = -vx end
  if y < 4 or y > 123 then vy = -vy end
  if btnp(BTN_A) then
    inv = not inv
    invert()
  end
end

function _draw()
  cls(inv and 1 or 0)
  circf(x, y, 4, inv and 0 or 1)
end
```

**meta.toml:**
```toml
title = "BOUNCER"
author = "DEMO"
version = 1
```

**sprites.txt:** 128 blank 8×8 sprites (all zeros)

**tilemap.txt:** 16 lines of `0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0`

**sfx.txt / music.txt:** Empty patterns (all zeros)

**Verification:** Token count must be under 2048. Cart must build. Runtime must show a bouncing ball. BTN_A must invert the display.

---

### Demo 2: RUNNER

**Purpose:** Validates scrolling, pget-based collision, state machine (playing/dead/restart), scoring, print.

**Design:**
- Ground: a solid line at y=110, drawn with `rectf`
- Obstacles: 8×8 white rectangles that spawn at x=127 and scroll left each frame
- Player: 8×8 sprite at x=20, rests on ground
- BTN_A: jumps (applies upward velocity; gravity returns player to ground)
- Collision: check `pget` at player corners each frame; if any pixel is white AND it's an obstacle position, trigger game over
- Score: increments each frame while alive; displayed with `print` at top-left
- State machine: `STATE_PLAY = 0`, `STATE_DEAD = 1`. On death, show "GAME OVER" and score. BTN_A restarts.

---

### Demo 3: DUNGEON

**Purpose:** Validates full D-pad, tile map rendering, sprite sheet, multi-state game, save/load.

**Design:**
- Single-screen top-down room, 16×16 tiles
- Tile 0 = floor (empty), Tile 1 = wall (solid white block), Tile 2 = chest
- Player sprite: simple 8×8 character, 4-directional movement at 2px/frame
- Walls block movement: check tile at destination before moving
- Chest interaction: approach chest, press BTN_A to open. Sets a `found` flag.
- `save(0, ...)` writes the `found` flag when the chest is opened
- `load(0)` is called in `_init()` to restore the flag across sessions
- State machine: `STATE_EXPLORE`, `STATE_DIALOGUE`. In dialogue, D-pad does nothing; BTN_A advances text lines and eventually returns to explore state.

---

## SECTION 12 — BUILD ORDER & VERIFICATION SEQUENCE

Complete each step and verify it passes before starting the next. This order minimises backtracking.

| Step | Action | Pass Condition |
|---|---|---|
| 1 | Create full directory structure and all stubs | `ls` shows all files; C files compile as empty stubs |
| 2 | Write CMakeLists.txt | `cmake ..` configures; `make` compiles with zero errors |
| 3 | Implement renderer.c | `renderer_debug_ascii()` shows circle + rectangle + text in terminal |
| 4 | Implement input.c | `BTN_A PRESSED` prints exactly once per Z keypress |
| 5 | Implement audio.c | A4 square wave plays audibly for 2 seconds at startup |
| 6 | Implement lua_api.c | Inline Lua draws a white circle with black text in SDL window |
| 7 | Implement cart.c | Hand-crafted minimal .gbcart loads without error; title prints correctly |
| 8 | Implement main.c + runtime.c | Splash screen appears; bouncer.gbcart loads and runs |
| 9 | Write tools/token-count.py | Correctly counts BOUNCER source; reports under 2048 |
| 10 | Write tools/cart-builder.py | Assembles bouncer.gbcart; runtime runs it |
| 11 | Write tools/qr-encode.py | Generates bouncer-card.pdf; two Aztec codes visible on rear |
| 12 | Write Demo 2 (RUNNER) | Ball scrolling, jump, game over, restart all function |
| 13 | Write Demo 3 (DUNGEON) | D-pad movement, wall collision, chest interaction, save/load all function |

---

## APPENDIX A — GAME LOOP CONTRACT

Every GLYPHBOX game must define these Lua functions:

```lua
function _init()
  -- Called once when the cartridge loads.
  -- Initialise all game state here.
  -- Do not draw here.
end

function _update()
  -- Called every frame at 30fps.
  -- Read input. Advance game logic.
  -- May also draw if _draw is not defined.
end

function _draw()
  -- Called every frame after _update().
  -- Optional. Render the current frame.
  -- If absent, _update() is expected to handle rendering.
end
```

---

## APPENDIX B — SANDBOX RULES

Game code may ONLY call functions in the GLYPHBOX API table above. The following are removed from the Lua environment and will cause a runtime error if accessed:

```
io  os  package  require  dofile  load  loadfile
loadstring  debug  collectgarbage  newproxy
```

The following standard library modules ARE available in their entirety:
```
math  table  string
```

The following base library functions ARE available:
```
assert  error  ipairs  next  pairs  pcall  rawequal  rawget
rawlen  rawset  select  setmetatable  getmetatable  tonumber
tostring  type  unpack  xpcall
```

---

## APPENDIX C — CARTRIDGE ASSET TEXT FORMATS

### sprites.txt
128 sprites, each 8×8. Sprites separated by a blank line.
```
00000000
01111110
01000010
01000010
01000010
01111110
00000000
00000000

(next sprite)
...
```

### tilemap.txt
16 rows of 16 space-separated integers (sprite indices 0–127).
```
1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
1 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1
1 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1
...
1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
```

### meta.toml
```toml
title   = "MYGAME"      # max 16 characters
author  = "MYNAME"      # max 8 characters
version = 1
```

---

*GLYPHBOX Software Implementation Guide — Prototype v0.2 — For Claude Code*
