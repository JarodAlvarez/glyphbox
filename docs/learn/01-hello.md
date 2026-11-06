---
title: Hello, screen
order: 1
---

# Hello, screen

A GLYPHBOX game is a Lua program with three functions in it. The console calls `_init()` once when the game starts, then `_update()` and `_draw()` 30 times every second, for as long as the game runs.

Here's the smallest game there is. Press **RUN** and it appears on the console to the right.

```lua run
function _draw()
  cls(0)
  print("HELLO, GLYPHBOX", 20, 60, 1)
end
```

`cls(0)` clears the screen to black, and `print` draws text. The numbers after the text are where it goes, `x` across and `y` down, then the colour: `1` for white or `0` for black. The screen is 128 pixels each way, and `0, 0` is the top-left corner.

**Try it:** change the text, move it to the top of the screen, then draw a box around it with `rect(x, y, w, h, 1)`.

## Drawing shapes

The screen is black and white, so every drawing call ends with a colour: `0` or `1`.

```lua run
function _draw()
  cls(0)
  rectf(10, 10, 40, 30, 1)    -- filled rectangle
  rect(60, 10, 40, 30, 1)     -- outline
  circf(30, 80, 15, 1)        -- filled circle
  circ(80, 80, 15, 1)         -- outline
  line(0, 120, 127, 100, 1)   -- line
end
```

Lines starting with `--` are comments: the console ignores them.

## Making it move

Anything you keep between frames goes in a variable. Set it up in `_init()`, change it in `_update()` and draw it in `_draw()`:

```lua run
function _init()
  x = 0
end

function _update()
  x = x + 1
  if x > 127 then x = 0 end
end

function _draw()
  cls(0)
  circf(x, 64, 6, 1)
end
```

Without the `cls(0)` the ball would leave a trail, because the screen keeps whatever was drawn last frame. Delete that line to see it.

Next: making the ball follow the buttons.
