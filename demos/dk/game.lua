function _init()
  -- Player (Mario) state
  px, py = 12, 112   -- Start at the bottom left of the screen
  vx, vy = 0, 0      -- Velocity
  flip = false       -- Which way Mario is facing
  grounded = false   -- Is he touching the floor?
end

function _update()
  -- 1. Horizontal Movement
  vx = 0
  if btn(BTN_L) then 
    vx = -1.5 
    flip = true      -- Face left
  end
  if btn(BTN_R) then 
    vx = 1.5 
    flip = false     -- Face right
  end

  -- 2. Gravity
  vy = vy + 0.25     -- Pull Mario down every frame

  -- 3. Apply Velocity
  px = px + vx
  py = py + vy

  -- 4. Screen Boundaries
  px = clamp(px, 0, 120)

  -- 5. Pixel-Perfect Floor Collision
  -- Check the pixel directly under the center of Mario's feet
  local foot_x = flr(px + 4)
  local foot_y = flr(py + 8)
  
  grounded = false
  -- Only check for floor collision if we are falling (vy >= 0)
  if vy >= 0 then
    if pget(foot_x, foot_y) == 1 then
      grounded = true
      vy = 0
      py = foot_y - 8  -- Snap perfectly to the top of the girder
    end
  end

  -- 6. Jumping
  if btnp(BTN_A) and grounded then
    vy = -3.5          -- Upward impulse
    grounded = false
  end
end

function _draw()
  -- 1. Clear the screen to black
  cls(0)
  
  -- 2. Draw the entire level map (Girders and Ladders)
  map(0, 0, 0, 0, 16, 16)
  
  -- 3. Draw Mario (Sprite ID 3)
  -- The 'flip' boolean automatically mirrors the sprite left/right
  spr(3, flr(px), flr(py), flip, false)
end