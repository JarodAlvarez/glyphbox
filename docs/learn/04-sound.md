---
title: Sound
order: 4
---

# Sound

`sfx(channel, note, volume, wave, frames)` plays a note. There are two channels, 0 and 1, so two sounds can play at once.

```lua run
function _update()
  if btnp(BTN_L) then sfx(0, 60, 6, 0, 8) end   -- square wave
  if btnp(BTN_R) then sfx(0, 67, 6, 1, 8) end   -- triangle wave
  if btnp(BTN_D) then sfx(1, 40, 5, 2, 6) end   -- noise
  if btnp(BTN_U) then sfx(0, 72, 6, 0, 3) sfx(1, 76, 6, 0, 3) end  -- both channels
end

function _draw()
  cls(0)
  print("LEFT  SQUARE", 28, 40, 1)
  print("RIGHT TRIANGLE", 28, 52, 1)
  print("DOWN  NOISE", 28, 64, 1)
  print("UP    CHORD", 28, 76, 1)
end
```

| Argument | Meaning |
|---|---|
| `note` | `60` is middle C, and each step up or down is a semitone (`72` is an octave above) |
| volume | `0` to `7` |
| wave | `0` square, `1` triangle, `2` noise |
| frames | How long it plays, at 30 frames a second |

Click the console first: browsers only play sound after you've interacted with the page.

## Sound in Catch

A short blip on a catch, and a low buzz on a miss. Put these inside `_update()` in Catch:

```lua
score = score + 1 drop()
sfx(0, 72 + score % 12, 6, 0, 3)     -- rises with the score
```

```lua
misses = misses + 1 drop()
sfx(1, 36, 6, 2, 10)                 -- noise
```

Next: sprites, for something better to catch than a circle.
