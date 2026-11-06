-- HELLO GLYPHBOX
-- Arrows move the ball. Z or Space plays a note.
-- Run it with:  glyph run

function _init()
  x, y = 64, 64
end

function _update()
  if btn(BTN_L) then x = x - 2 end
  if btn(BTN_R) then x = x + 2 end
  if btn(BTN_U) then y = y - 2 end
  if btn(BTN_D) then y = y + 2 end
  x = clamp(x, 6, 121)
  y = clamp(y, 22, 105)
  if btnp(BTN_A) then sfx(0, 60, 8, 0, 6) end
end

function _draw()
  cls(0)
  print("HELLO GLYPHBOX", 22, 6, 1)
  rect(0, 16, 128, 96, 1)
  circf(x, y, 5, 1)
  spr(0, 4, 116)
  hint(70, 116) print("BEEP", 89, 116, 1)
end
