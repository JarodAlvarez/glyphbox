-- GLYPH-MAN: The Arcade Perfect Edition
local ms = "1111111111111111122222211222222112112121121211211311212222121131122222211222222112112111111211211222222222222221111121100112111100002100001200001111211111121111122222222222222112112111111211211231222112221321112111211211121112222222222222211111111111111111"

-- The Classic Intro (MIDI Notes, 0 = Rest)
local intro = {
  71,0,83,0,78,0,75,0,83,78,75,0,0,0,
  72,0,84,0,79,0,76,0,84,79,76,0,0,0,
  71,0,83,0,78,0,75,0,83,78,75,0,0,0,
  75,76,77,0,77,78,79,0,79,80,81,0,83,0,0,0
}

function _init()
  sc, lv, st = 0, 3, 0
  load_maze()
  reset_board()
end

function load_maze()
  m, dots = {}, 0
  for i=1, 256 do
    local v = tonumber(string.sub(ms, i, i))
    m[i] = v
    if v > 1 then dots = dots + 1 end
  end
end

function reset_board()
  p = { x=56, y=80, dx=0, dy=0, nx=0, ny=0, f=false, v=false, s=0 }
  gs = {
    { x=56, y=64, dx=0, dy=0, st="wait", t=30, id=2, tp="chase" },
    { x=64, y=64, dx=0, dy=0, st="wait", t=90, id=2, tp="ambush" },
    { x=56, y=56, dx=0, dy=0, st="wait", t=150, id=2, tp="random" },
    { x=64, y=56, dx=0, dy=0, st="wait", t=210, id=2, tp="corner" }
  }
  pm, ready_t = 0, 0
end

function can(tx, ty)
  if ty == 9 and (tx < 1 or tx > 16) then return true end
  if ty<1 or ty>16 or tx<1 or tx>16 then return false end
  return m[(ty-1)*16 + tx] ~= 1
end

function _update()
  -- STATE 0: Play Intro Music Sequencer
  if st == 0 then
    if ready_t % 2 == 0 then
      local idx = (ready_t / 2) + 1
      if intro[idx] then
        if intro[idx] > 0 then sfx(0, intro[idx], 5, 0, 4) end
      else
        st = 1 -- Auto-start game when song finishes
      end
    end
    ready_t = ready_t + 1
    if btnp(BTN_A) then st = 1; sfx(0,0) end -- Press A to skip intro
    return
  elseif st ~= 1 then
    if btnp(BTN_A) then 
      if st == 3 then _init()
      elseif lv > 0 then st = 1; reset_board() 
      else _init() end
    end
    return
  end

  -- Background Audio: Siren & Scared Ghosts
  local s_spd = pm > 0 and 15 or mid(4, flr(dots / 10), 15)
  if frame() % s_spd == 0 then
    if pm > 0 then sfx(0, 50, 3, 1, s_spd) -- Spooky hum when ghosts are scared
    else sfx(0, (frame()%(s_spd*2) == 0) and 47 or 48, 4, 1, s_spd) end -- Siren
  end

  -- Input Handling
  if btn(BTN_R) then p.nx,p.ny,p.f,p.v,p.s = 1,0,false,false,0
  elseif btn(BTN_L) then p.nx,p.ny,p.f,p.v,p.s = -1,0,true,false,0
  elseif btn(BTN_U) then p.nx,p.ny,p.f,p.v,p.s = 0,-1,false,true,7
  elseif btn(BTN_D) then p.nx,p.ny,p.f,p.v,p.s = 0,1,false,false,7 end

  -- Wrap & Move
  if p.x < -8 then p.x = 120 elseif p.x > 120 then p.x = -8 end

  if p.x%8==0 and p.y%8==0 then
    local tx, ty = p.x/8+1, p.y/8+1
    if can(tx+p.nx, ty+p.ny) then p.dx, p.dy = p.nx, p.ny end
    if not can(tx+p.dx, ty+p.dy) then p.dx, p.dy = 0, 0 end
    
    local idx = (ty-1)*16 + tx
    if tx >= 1 and tx <= 16 and m[idx] > 1 then
      sc = sc + (m[idx]==3 and 50 or 10)
      if m[idx]==3 then pm=150 end
      m[idx], dots = 0, dots-1
      sfx(1, 70, 2, 0, 3) -- Eating sound on Ch 1
      if dots == 0 then st = 3; sfx(0,0) end
    end
  end
  p.x, p.y = p.x+p.dx, p.y+p.dy
  if pm > 0 then pm = pm - 1 end

  -- Ghost AI
  for _, g in ipairs(gs) do
    if g.st == "wait" then
      g.t = g.t - 1
      if g.t <= 0 then g.st = "exit" end
    elseif g.st == "exit" then
      if g.y > 56 then g.y = g.y - 1 else g.st = "chase" end
    else
      if frame() % (pm > 0 and 2 or 4) ~= 0 then
        if g.x < -8 then g.x = 120 elseif g.x > 120 then g.x = -8 end
        if g.x%8==0 and g.y%8==0 then
          local tx, ty = g.x/8+1, g.y/8+1
          local txr, tyr = p.x/8+1, p.y/8+1
          
          if g.tp == "ambush" then txr = txr + p.dx*4; tyr = tyr + p.dy*4
          elseif g.tp == "random" then txr = txr + rnd(16)-8; tyr = tyr + rnd(16)-8
          elseif g.tp == "corner" then txr, tyr = 1, 1 end
          
          local dx, dy = txr > tx and 1 or -1, tyr > ty and 1 or -1
          if pm > 0 then dx, dy = -dx, -dy end
          
          if dy ~= 0 and can(tx, ty+dy) then g.dx, g.dy = 0, dy
          elseif dx ~= 0 and can(tx+dx, ty) then g.dx, g.dy = dx, 0
          elseif can(tx+g.dx, ty+g.dy) then 
          elseif can(tx-g.dy, ty+g.dx) then g.dx, g.dy = -g.dy, g.dx
          else g.dx, g.dy = g.dy, -g.dx end
        end
        g.x, g.y = g.x+g.dx, g.y+g.dy
      end
    end

    if abs(p.x-g.x)<4 and abs(p.y-g.y)<4 then
      if pm > 0 then g.x, g.y, g.st, g.t, sc = 56, 64, "wait", 60, sc+200
      else lv=lv-1; st=2; sfx(0,0); sfx(1, 40, 5, 2, 20) end
    end
  end
end

function _draw()
  cls(0)
  for i=1, 256 do
    local t = m[i]
    if t > 0 then
      local x, y = ((i-1)%16)*8, flr((i-1)/16)*8 + 8
      spr(t==1 and 6 or (t==2 and 4 or 5), x, y)
    end
  end
  spr((frame()%10<5 and p.s or p.s+1), p.x, p.y+8, p.f, p.v)
  for _, g in ipairs(gs) do spr(pm > 0 and 3 or g.id, g.x, g.y+8) end
  print("SC:"..sc.." L:"..lv, 2, 1, 1)
  if st ~= 1 then
    rectf(40, 60, 48, 15, 0)
  end
  if st==0 then print("READY!", 50, 64, 1)
  elseif st==2 then print("DIED! Z", 50, 64, 1)
  elseif st==3 then print("WINNER!", 45, 64, 1) end
end