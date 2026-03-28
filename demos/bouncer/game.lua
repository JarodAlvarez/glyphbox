function _init()
  x, y, vx, vy = 64, 64, 2.1, 1.7
  inv = false
end

function _update()
  x = x + vx
  y = y + vy
  if x < 4   then x = 4;   vx = -vx end
  if x > 123 then x = 123; vx = -vx end
  if y < 4   then y = 4;   vy = -vy end
  if y > 123 then y = 123; vy = -vy end
  if btnp(BTN_A) then inv = not inv end
end

function _draw()
  if inv then
    cls(1)
    circf(x, y, 4, 0)
  else
    cls(0)
    circf(x, y, 4, 1)
    print("hello",x + 4,y + 4,1)
  end
end
