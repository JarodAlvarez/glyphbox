---
title: Sprites
order: 5
---

# Sprites

A sprite is an 8 × 8 picture. A cart holds 128 of them, numbered 0 to 127, and `spr(n, x, y)` draws one. Only the white pixels are drawn, so sprites can overlap each other.

In the [Playground](../playground/), the **SPRITES** tab is a sprite editor: click a sprite on the sheet, then click or drag on the big grid to draw. In your own project, sprites live in `sprites.txt`.

Sprites are much cheaper than drawing with code. `spr()` is one call however detailed the picture is, and the sprite sheet costs very little of the card budget. So draw your art there, not with `pset` and `rectf`.

Here sprite 0 is a smiley, built into the examples:

```lua run
function _draw()
  cls(0)
  for i = 0, 7 do
    spr(0, 8 + i * 14, 40 + (i % 2) * 10)
  end
  spr(0, 60, 90, true, false)   -- flipped across
  spr(0, 76, 90, false, true)   -- flipped down
end
```

## The finished game

Here's **Catch** with everything from the lessons: a title screen, sound, a smiley to catch, and a best score that's saved between plays with `save` and `load`.

```lua run
function _init()
  best = tonumber(load(0) or "0")
  state = "title"
end

function start()
  px, score, misses, state = 56, 0, 0, "play"
  drop()
end

function drop() dx, dy = 4 + rnd(116), 8 end

function _update()
  if state ~= "play" then
    if btnp(BTN_A) then start() end
    return
  end
  if btn(BTN_L) then px = px - 3 end
  if btn(BTN_R) then px = px + 3 end
  px = clamp(px, 0, 112)
  dy = dy + 1.5 + score * 0.1
  if dy > 110 and dy < 118 and dx + 8 > px and dx < px + 16 then
    score = score + 1 drop()
    sfx(0, 72 + score % 12, 6, 0, 3)
  elseif dy > 128 then
    misses = misses + 1 drop()
    sfx(1, 36, 6, 2, 10)
    if misses >= 3 then
      state = "over"
      if score > best then best = score save(0, tostring(best)) end
    end
  end
end

function centre(s, y) print(s, 64 - (#s * 6 - 1) / 2, y, 1) end

function _draw()
  cls(0)
  if state == "title" then
    centre("CATCH", 40)
    hint(40, 70) print("START", 59, 70, 1)
    centre("BEST " .. best, 96)
    return
  end
  print(score, 2, 2, 1)
  for i = 1, 3 - misses do circf(120 - i * 8, 5, 2, 1) end
  if state == "over" then
    centre("GAME OVER", 50)
    hint(40, 70) print("AGAIN", 59, 70, 1)
    return
  end
  spr(0, dx, dy)
  rectf(px, 118, 16, 4, 1)
end
```

The game keeps track of which screen it's on in `state`: `"title"`, `"play"` or `"over"`.

Next: putting it on cards.
