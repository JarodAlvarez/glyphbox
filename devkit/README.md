# GLYPHBOX devkit

`glyph` is the command-line devkit for GLYPHBOX games.

```bash
pip install "git+https://github.com/JarodAlvarez/glyphbox#subdirectory=devkit"
```

It also needs **LuaJIT** on your PATH, which compiles your Lua into the cart (`brew install luajit` or `apt install luajit`). `glyph run` also needs the GLYPHBOX emulator from [Releases](https://github.com/JarodAlvarez/glyphbox/releases).

| Command | What it does |
|---|---|
| `glyph new mygame` | Start a project from the template |
| `glyph run` | Build, open the emulator, and rebuild and relaunch every time you save |
| `glyph build` | Build `mygame.gbcart` and show its card count (fails above 8 cards) |
| `glyph print mygame.gbcart -o cards.pdf` | Make a print-and-cut card PDF (`--paper letter`, `--rear-only`) |
| `glyph sprites art.png` | Convert a 1-bit image into `sprites.txt` |
| `glyph tokens` | Count Lua tokens. A complexity signal, not a limit |

## A project

```
mygame/
  game.lua      _init(), _update() and _draw()
  meta.toml     title (16 chars max), author (8), version
  sprites.txt   128 tiles, 8 × 8, written as 0s and 1s
  tilemap.txt   16 × 16 tile indices
  sfx.txt       16 sound patterns
  music.txt     4 music patterns
```

**Card budget:** a game prints to 1, 2, 4 or 8 cards, at 800 bytes of compressed cart per card. Eight cards (6,400 B) is the limit. `glyph build` shows where you are.

Want to try GLYPHBOX without installing anything? Use the [browser playground](https://jarodalvarez.github.io/glyphbox/playground/).

The devkit is MIT licensed. See [LICENSE.md](../LICENSE.md).
