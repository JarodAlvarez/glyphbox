---
title: A game
order: 3
---

# A game

Now a falling dot, so there's something to catch. This is the core of **Catch**, the game these lessons build:

```lua run
function _init()
  px = 56
  drop()
  score = 0
end

function drop()
  dx = 4 + rnd(120)     -- rnd(n) is a whole number from 0 to n-1
  dy = 10
end

function _update()
  if btn(BTN_L) then px = px - 3 end
  if btn(BTN_R) then px = px + 3 end
  px = clamp(px, 0, 112)

  dy = dy + 1.5
  if dy > 114 and dy < 120 and dx > px and dx < px + 16 then
    score = score + 1
    drop()
  elseif dy > 128 then
    drop()
  end
end

function _draw()
  cls(0)
  print(score, 2, 2, 1)
  circf(dx, dy, 3, 1)
  rectf(px, 116, 16, 4, 1)
end
```

A few new ideas:

- **Your own functions.** `drop()` puts the dot back at the top. Any time you'd write the same lines twice, make a function instead.
- **Collision.** The dot is caught when it's at the paddle's height (`dy` between 114 and 120) and inside its width (`dx` between `px` and `px + 16`).
- **Numbers on screen.** `print(score, 2, 2, 1)` works with a number as well as text.

**Try it:** make the dot speed up each time you catch one. Hint: use a variable instead of `1.5`.

## Missing

A game needs a way to lose. Count the misses, and stop after three:

```lua run
function _init()
  px, score, misses = 56, 0, 0
  drop()
end

function drop() dx, dy = 4 + rnd(120), 10 end

function _update()
  if misses >= 3 then return end
  if btn(BTN_L) then px = px - 3 end
  if btn(BTN_R) then px = px + 3 end
  px = clamp(px, 0, 112)
  dy = dy + 1.5 + score * 0.1
  if dy > 114 and dy < 120 and dx > px and dx < px + 16 then
    score = score + 1 drop()
  elseif dy > 128 then
    misses = misses + 1 drop()
  end
end

function _draw()
  cls(0)
  print(score, 2, 2, 1)
  for i = 1, 3 - misses do circf(120 - i * 8, 5, 2, 1) end
  if misses >= 3 then print("GAME OVER", 37, 56, 1) return end
  circf(dx, dy, 3, 1)
  rectf(px, 116, 16, 4, 1)
end
```

`return` ends a function early: once the game's over, `_update` stops moving things and `_draw` shows GAME OVER.

Next: sound.
