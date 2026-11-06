---
title: API reference
order: 1
---

# API reference

Every function a GLYPHBOX game can call. Games are Lua (LuaJIT 2.1 on the console), with `math`, `string` and `table` available. `io`, `os`, `require`, `load`, `debug` and the other system libraries are removed.

## The game loop

A game defines three functions. The console calls them for you.

| Function | When it runs |
|---|---|
| `_init()` | Once, when the cart loads |
| `_update()` | 30 times a second, before drawing. Move things here |
| `_draw()` | 30 times a second, after `_update()`. Draw here |

The console runs at a fixed **30 frames per second**. Anything you draw stays on screen until you draw over it, so most games start `_draw()` with `cls(0)`.

```lua run
function _init()
  t = 0
end

function _update()
  t = t + 1
end

function _draw()
  cls(0)
  print("FRAME " .. t, 40, 60, 1)
end
```

## The screen

The screen is **128 × 128 pixels** and every pixel is black (`0`) or white (`1`). `(0, 0)` is the top-left corner and `(127, 127)` the bottom-right. Positions are whole numbers, and fractions are rounded down.

| Function | What it does |
|---|---|
| `cls(c)` | Fill the screen with colour `c` (0 or 1). `cls()` clears to black |
| `pset(x, y, c)` | Set one pixel |
| `pget(x, y)` | Read one pixel: `0` or `1` |
| `line(x0, y0, x1, y1, c)` | Line between two points |
| `rect(x, y, w, h, c)` | 1-pixel outline of a `w` × `h` rectangle |
| `rectf(x, y, w, h, c)` | Filled rectangle |
| `circ(x, y, r, c)` | 1-pixel outline of a circle of radius `r` |
| `circf(x, y, r, c)` | Filled circle |
| `invert()` | Swap black and white on the whole screen |

For thick outlines, draw a filled rectangle and cut out the middle: `rectf(x, y, w, h, 1)` then `rectf(x + 2, y + 2, w - 4, h - 4, 0)`.

```lua run
function _draw()
  cls(0)
  rect(4, 4, 120, 120, 1)
  rectf(20, 20, 30, 20, 1)
  circ(90, 40, 14, 1)
  circf(90, 40, 6, 1)
  line(20, 100, 108, 70, 1)
  for i = 0, 10 do pset(20 + i * 8, 110, 1) end
end
```

## Text

| Function | What it does |
|---|---|
| `print(s, x, y, c)` | Draw text with its top-left corner at `x, y` |

The font is 5 × 7 pixels. Each character takes 6 pixels across, so a string is `#s * 6 - 1` pixels wide, and a line of text is 7 pixels tall. All printable ASCII characters are available. Numbers can be passed straight in: `print(score, 2, 2, 1)`. Join text with `..`, for example `"HI " .. score`.

To centre a string: `print(s, 64 - (#s * 6 - 1) / 2, y, 1)`.

## Button hints

| Function | What it does |
|---|---|
| `hint(x, y, [c])` | Draw the action-button graphic (15 × 7) used on the console's own screens |

Use it instead of writing "PRESS A", since the controller's buttons have no letters on them. Put the label 19 pixels to the right: `hint(40, 80) print("START", 59, 80, 1)`.

## Sprites

A cart has **128 sprites**, numbered 0 to 127. Each is 8 × 8 pixels, kept in `sprites.txt`. Sprites draw only their white pixels, so the black parts are transparent.

| Function | What it does |
|---|---|
| `spr(id, x, y)` | Draw sprite `id` with its top-left corner at `x, y` |
| `spr(id, x, y, fx, fy)` | Same, flipped across (`fx`) and/or down (`fy`) when those are `true` |

Drawing a sprite costs one function call, however detailed it is. Art in the sprite sheet costs far less of your card budget than drawing the same thing with code.

## The tile map

A cart has one **16 × 16 tile map** (`tilemap.txt`). Each cell holds a sprite number, which is exactly enough to cover the screen with 8 × 8 tiles.

| Function | What it does |
|---|---|
| `map(cx, cy, x, y, w, h)` | Draw `w` × `h` cells, starting at cell `cx, cy`, at screen position `x, y` |
| `mget(cx, cy)` | Read the sprite number in a cell |
| `mset(cx, cy, id)` | Change a cell while the game runs. The change isn't saved to the cart |

`map(0, 0, 0, 0, 16, 16)` draws the whole map over the whole screen.

## Buttons

| Function | What it does |
|---|---|
| `btn(b)` | `true` while button `b` is held |
| `btnp(b)` | `true` only on the frame the button goes down |
| `btnr(b)` | `true` only on the frame the button comes up |

| Constant | Button | Keyboard (emulator) |
|---|---|---|
| `BTN_U` | Up | Arrow up / W |
| `BTN_D` | Down | Arrow down / S |
| `BTN_L` | Left | Arrow left / A |
| `BTN_R` | Right | Arrow right / D |
| `BTN_A` | Action | Z / Space |

The menu button is the console's own (volume, exit), so games never see it.

```lua run
function _init() x, y = 60, 60 end

function _update()
  if btn(BTN_L) then x = x - 2 end
  if btn(BTN_R) then x = x + 2 end
  if btn(BTN_U) then y = y - 2 end
  if btn(BTN_D) then y = y + 2 end
end

function _draw()
  cls(0)
  circf(x, y, 4, 1)
  print("USE THE ARROWS", 22, 4, 1)
end
```

## Sound

The console has **two sound channels** for games (0 and 1), plus one of its own for system sounds.

| Function | What it does |
|---|---|
| `sfx(ch, note, [vol], [wave], [dur])` | Play a note on channel `ch` |
| `sfx(ch, 0)` | Stop channel `ch` |

| Argument | Meaning |
|---|---|
| `note` | Pitch as a MIDI note number: `60` is middle C, `69` is A (440 Hz), and each step is a semitone |
| `vol` | Volume `0` to `7` (default `7`) |
| `wave` | `0` square, `1` triangle, `2` noise (default `0`) |
| `dur` | Length in frames, 30 per second. Default `-1` holds the note until you stop it or play another |

A new note on a channel replaces the one playing there.

```lua run
function _update()
  if btnp(BTN_A) then sfx(0, 60 + rnd(12), 6, 0, 6) end
  if btnp(BTN_D) then sfx(1, 40, 5, 2, 4) end
end

function _draw()
  cls(0)
  hint(30, 56) print("BEEP", 49, 56, 1)
  print("DOWN: NOISE", 30, 70, 1)
end
```

> **Not working yet:** `sfx_pat(id)` and `music(id)` / `music(-1)` are meant to play the patterns in `sfx.txt` and `music.txt`, but the console doesn't sequence them properly yet. A pattern plays only its last note. Use `sfx()` for now.

## Numbers and time

| Function | What it does |
|---|---|
| `rnd(n)` | Random whole number from `0` to `n - 1` |
| `flr(n)` | Round down to a whole number |
| `abs(n)` | Absolute value |
| `mid(a, b, c)` | The middle one of three values |
| `clamp(v, lo, hi)` | `v` limited to the range `lo` to `hi` |
| `sin(t)`, `cos(t)` | Sine and cosine, where `t` is in **turns**: `1` is a full circle, so `sin(0.25)` is `1` |
| `frame()` | Frames since the cart loaded |
| `time()` | Seconds since the console started |

All of Lua's `math` library is available too, such as `math.floor`, `math.sqrt` and `math.atan2`. Unlike `sin()`, `math.sin` uses radians.

```lua run
function _draw()
  cls(0)
  local t = frame() / 60
  for i = 0, 7 do
    local a = t + i / 8
    circf(64 + cos(a) * 40, 64 + sin(a) * 40, 4, 1)
  end
end
```

## Saving

Each cart has **4 save slots** (0 to 3) of up to **64 bytes**. Saves belong to one cart: two different carts never see each other's saves.

| Function | What it does |
|---|---|
| `save(slot, s)` | Store string `s` in a slot. Longer than 64 bytes is cut off |
| `load(slot)` | The saved string, or `nil` if the slot is empty |

Save numbers as text and read them back with `tonumber`:

```lua
function _init()
  best = tonumber(load(0) or "0")
end

function game_over(score)
  if score > best then best = score save(0, tostring(best)) end
end
```

## Expansion carts

A game can scan another cart while it's running, to load extra levels for example. Only the console can do this, and on the web both functions do nothing.

| Function | What it does |
|---|---|
| `scan_begin()` | Turn on the card scanner |
| `scan_poll()` | `nil` while scanning, `false` if it failed, or a table of the scanned cart's save data |

The scanned cart runs only its `_init()`, and the `save(slot, s)` calls it makes come back as the table: `result[1]`, `result[2]` and so on. A minimal expansion cart:

```lua
function _init()
  save(1, "LEVEL DATA ONE")
  save(2, "LEVEL DATA TWO")
end
```

## Cart data

| Function | What it does |
|---|---|
| `peek(addr)` | Read one byte of the cart's compiled code, or `nil` past the end |

## Limits

| Thing | Limit |
|---|---|
| Screen | 128 × 128, 1-bit |
| Frame rate | 30 fps |
| Sprites | 128 of 8 × 8 |
| Tile map | 16 × 16 |
| Sound | 2 channels |
| Save data | 4 slots × 64 bytes |
| Cart size | 8 cards. See [Carts and cards](carts.html) |
