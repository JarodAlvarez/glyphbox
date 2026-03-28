function _init()
  x, y = 10, 20
  inv = 0
end

function _update()
  if btn(BTN_L) then x = x - 2 end
  if btn(BTN_R) then x = x + 2 end
  if btn(BTN_U) then y = y - 2 end
  if btn(BTN_D) then y = y + 2 end
  if btn(BTN_A) then inv = inv + 1 end
end

function _draw()
  cls(0)
  --map(0, 0, 0, 0, 16, 16)
  print("Hello Buko", 0, 0, 1)
  -- Drawing the 32x32 image at (x, y)
  -- Row 1
  spr(0, x + 0,  y + 0)
  spr(1, x + 8,  y + 0)
  spr(2, x + 16, y + 0)
  spr(3, x + 24, y + 0)

  -- Row 2
  spr(4, x + 0,  y + 8)
  spr(5, x + 8,  y + 8)
  spr(6, x + 16, y + 8)
  spr(7, x + 24, y + 8)

  -- Row 3
  spr(8,  x + 0,  y + 16)
  spr(9,  x + 8,  y + 16)
  spr(10, x + 16, y + 16)
  spr(11, x + 24, y + 16)

  -- Row 4 (Background/Empty space below feet)
  spr(12, x + 0,  y + 24)
  spr(13, x + 8,  y + 24)
  spr(14, x + 16, y + 24)
  spr(15, x + 24, y + 24)
  if (inv % 2) == 1 then
    invert()
  end
end
