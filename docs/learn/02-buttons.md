---
title: Buttons
order: 2
---

# Buttons

The controller has a D-pad and one action button. `btn(b)` is `true` while a button is held down:

```lua run
function _init()
  x = 60
end

function _update()
  if btn(BTN_L) then x = x - 3 end
  if btn(BTN_R) then x = x + 3 end
  x = clamp(x, 0, 112)
end

function _draw()
  cls(0)
  rectf(x, 116, 16, 4, 1)
  print("LEFT AND RIGHT", 22, 4, 1)
end
```

Click the console screen first, so it gets your key presses. On a keyboard the D-pad is the arrow keys (or W A S D) and the action button is **Z** or **Space**.

`clamp(x, 0, 112)` keeps the paddle on screen: the paddle is 16 pixels wide and the screen 128, so its left edge can go from 0 to 112.

## Pressing, not holding

`btn` is true for every frame a button is down. For things that should happen once per press, like jumping or firing, use `btnp`. It's true only on the frame the button goes down:

```lua run
function _init()
  count = 0
end

function _update()
  if btnp(BTN_A) then count = count + 1 end
end

function _draw()
  cls(0)
  print("PRESSES: " .. count, 34, 56, 1)
  hint(36, 72) print("PRESS", 55, 72, 1)
end
```

`..` joins text and numbers together. `hint(x, y)` draws the action-button picture the console uses on its own screens. The buttons have no letters on them, so use `hint` rather than writing "PRESS A".

| Constant | Button |
|---|---|
| `BTN_U`, `BTN_D`, `BTN_L`, `BTN_R` | D-pad |
| `BTN_A` | Action |

Next: something to catch.
