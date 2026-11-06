---
title: On cards
order: 6
---

# On cards

A finished game gets built into a **cart**, and the cart is printed onto **cards** that the console reads through its slot.

## From the Playground

1. In the [Playground](../playground/), choose **DOWNLOAD → GAME.LUA** and **SPRITES.TXT**.
2. Put both files in a folder, for example `catch/`.
3. Add `meta.toml`:

```
title   = "CATCH"
author  = "ME"
version = 1
```

## Build and print

Install the [devkit](https://github.com/JarodAlvarez/glyphbox/tree/main/devkit), then:

```bash
cd catch
glyph run                              # try it in the emulator; it reloads when you save
glyph build                            # make catch.gbcart and count its cards
glyph print catch.gbcart -o cards.pdf  # cards to print and cut out
```

`glyph build` tells you how many cards the game needs:

```
catch.gbcart  3,197 B  →  2 / 8 cards
  ■■□□□□□□  5,440 B left of 6,400
```

A game can use up to **8 cards**, and Catch needs 2. Bigger games need more cards, so [Carts and cards](../docs/carts.html) explains what takes up space and how to trim it.

## Play it

- **On a console:** press the action button on the splash screen and slide each card into the slot, in any order.
- **In a browser:** open [Play](../play/), choose **SCAN CARDS** and hold each card up to your camera.

Either way, the console shows each card as it's read and starts the game when it has them all.

## Where next

- The [API reference](../docs/api.html) lists everything the console can do.
- The [games](https://github.com/JarodAlvarez/glyphbox/tree/main/games) come with their full source: Sunset Run, Glyph Golf, Chess, Tennis and Runner.
