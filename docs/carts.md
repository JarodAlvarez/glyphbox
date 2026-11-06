---
title: Carts and cards
order: 2
---

# Carts and cards

A GLYPHBOX game is a folder of text files. The devkit compiles it into a **cart** (a `.gbcart` file), and the cart prints onto **cards**: credit-card-sized pieces of paper, each holding part of the cart as an Aztec code. The console reads the cards with a camera in its slot and puts them back together.

## A game folder

```
mygame/
  game.lua      the code: _init(), _update(), _draw()
  meta.toml     title, author and version
  sprites.txt   128 sprites of 8 × 8 pixels
  tilemap.txt   the 16 × 16 tile map
  sfx.txt       16 sound patterns
  music.txt     4 music patterns
```

Only `game.lua` is required. `glyph new mygame` creates all of them.

### meta.toml

```
title   = "MY GAME"
author  = "ME"
version = 1
```

The title can be up to **16 characters** and the author up to **8**. Both show on the console's CART LOADED screen: titles of 10 characters or fewer appear at double size.

### sprites.txt

128 sprites, one after another, with a blank line between each. A sprite is 8 lines of 8 characters, where `1` is white and `0` is transparent:

```
00111100
01000010
10100101
10000001
10100101
10011001
01000010
00111100
```

You don't have to type these. The Playground's sprite editor saves `sprites.txt`, and `glyph sprites art.png` converts a black-and-white image.

### tilemap.txt

16 lines of 16 sprite numbers separated by spaces.

## Building and printing

```bash
glyph build                        # mygame.gbcart, with its card count
glyph print mygame.gbcart -o cards.pdf
glyph print mygame.gbcart -o cards.pdf --paper letter
```

The PDF has the card fronts and backs on separate pages, with crop marks. Print it (double-sided if you can) and cut along the marks. Each card is 85.6 × 54 mm, the size of a bank card.

## The card budget

A game must fit on **8 cards or fewer**. Every card is something a player has to scan, so the limit keeps loading quick.

How it's counted:

1. The devkit compiles `game.lua` to LuaJIT bytecode and packs it with the sprites, map and sound into the cart.
2. The whole cart is compressed.
3. Each card holds **800 bytes** of the compressed cart, and the count goes **1, 2, 4 or 8**: it doubles each time it runs out of room.

So 8 cards means the compressed cart must be **6,400 bytes or less**, and going one byte over 3,200 jumps from 4 cards straight to 8. `glyph build` shows exactly where you are:

```
mygame.gbcart  6,890 B  →  8 / 8 cards
  ■■■■■■■■  2,188 B left of 6,400
```

The Playground shows an estimate as you type.

### What costs space

- **Code is the expensive part.** Bytecode compresses less well than the source it came from, so roughly every 1 KB of compressed source costs 1.4 KB of cart.
- **Sprites and the tile map are cheap.** Empty sprites cost almost nothing, and one `spr()` call draws any amount of detail. Moving art out of drawing code into sprites is the best saving there is.
- **Data in strings is cheap.** A level written as a string such as `"#..#..##"` and read with `s:byte(i)` costs far less than the same level built in a table of numbers.
- **Repeated code is costly.** Turn anything you write twice into a function.

### Trimming a game that's over

1. Run `glyph build` after each change, so you can see what each one saves.
2. Move art and level data into sprites, the tile map and strings.
3. Merge similar functions, and use loops instead of copy-pasted lines.
4. Shorter names for local variables and functions help a little, because names that cross functions are kept in the bytecode.
5. Keep about 100 bytes of headroom, so a last small fix doesn't push you up a card.

## The cart file format

You don't need this to make games, but it's here for tool writers. A `.gbcart` is little-endian:

| Offset | Size | Contents |
|---|---|---|
| `0x00` | 4 | Magic `GBC1` |
| `0x04` | 16 | Title, ASCII, padded with zero bytes |
| `0x14` | 8 | Author, ASCII, padded with zero bytes |
| `0x1C` | 2 | Version |
| `0x1E` | 2 | Flags: `0x0002` means the code is compressed |
| `0x20` | 2 | Compressed code length `n` |
| `0x22` | 2 | Uncompressed code length |
| `0x24` | `n` | zlib-compressed LuaJIT 2.1 bytecode (stripped, 64-bit) |
| | 1024 | Sprites: 128 × 8 rows, 1 byte per row, leftmost pixel in the top bit |
| | 512 | Tile map: 16 × 16 cells, 2 bytes each |
| | 512 | Sound patterns |
| | 256 | Music patterns |
| end − 4 | 4 | CRC-32 of everything before it |

The sections after the code don't have fixed offsets, because the code length varies.

Each card's Aztec code holds 3 header bytes, then its slice of the zlib-compressed cart: the card number (from 0), the number of cards, and a flags byte (`0x01`, zlib). Cards can be scanned in any order.
