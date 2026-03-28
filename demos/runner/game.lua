STATE_PLAY = 0
STATE_DEAD = 1
STATE_IDLE = 2

function _init()
  px, py  = 60, 82
  vy      = 0
  on_gnd  = true
  spawn_t = 0
  obs     = {}          -- fixed: was obx {}
  score   = 0
  state   = STATE_IDLE
end

function _update()
  if state == STATE_DEAD or state == STATE_IDLE then
    if btnp(BTN_A) then _init() state = STATE_PLAY end
    return   -- skip all physics/spawning while dead
  end
  vy = vy + 0.5
  py = py + vy
  if py >= 82 then
    py     = 82
    vy     = 0
    on_gnd = true
  else
    on_gnd = false
  end

  if btnp(BTN_A) and on_gnd then
    vy = -6
  end

  spawn_t = spawn_t - 1
  if spawn_t <= 0 then
    obs[#obs + 1] = {x=128, speed=4}
    spawn_t = rnd(60) + 40
  end

  local i = 1
  while i <= #obs do
    obs[i].x = obs[i].x - obs[i].speed
    if obs[i].x < -8 then
      table.remove(obs, i)
    else
      i = i + 1
    end
  end

  score = score + 1     -- fixed: moved outside the while loop
end

function _draw()
  cls(0)
  local anim_f = flr(frame() / 3) % 6
  line(0, 90, 127, 90, 1)

  for i = 1, #obs do    -- fixed: was "for i in obs do"
    rectf(obs[i].x, 82, 8, 8, 1)
  end

  if pget(px,   py)   == 1 or pget(px+7, py)   == 1 or
     pget(px,   py+7) == 1 or pget(px+7, py+7) == 1 then
    state = STATE_DEAD
  end

  spr(anim_f, px, py)
  print("SCORE:"..score, 2, 2, 1)

  if state == STATE_DEAD then
    rectf(24, 44, 80, 36, 0)   -- clear a box so text is readable
    rect(24, 44, 80, 36, 1)    -- border
    print("GAME OVER",  36, 50, 1)
    print("SCORE:"..score, 36, 60, 1)
    print("action:RETRY", 30, 70, 1)
  end

  if state == STATE_IDLE then
    print("RUNNER",  45, 50, 1)
    print("glyphbox 2026", 20, 118, 1)
  end
end
