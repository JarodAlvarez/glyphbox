-- SEGA TRILOGY ARCADE: RAIL DEMO
-- Phase 42: Quad-Lasers, Collision & Explosions

local score = 12800
local shield = 100.0
local ticks = 0

-- Camera & Player variables
local cx, cy = 64, 64       
local cam_x, cam_y = 0, 0   
local cam_roll, target_roll = 0.0, 0.0
local lock_on = false

-- Laser Gun Variables (X-Wing Quad Cannons)
local gi, gc = 1, 0
local gx = {0, 127, 127, 0} -- Top-L, Bot-R, Top-R, Bot-L
local gy = {0, 127, 0, 127}

local st, en, ls = {}, {}, {}
local current_msg = "MISSION 1: YAVIN"
local msg_timer = 120

-- The Choreographed Script
local timeline = {
    {t = 50,  cmd = "spawn", val = "V_FORM", x = 0,   y = -20, path = 1}, 
    {t = 150, cmd = "bank",  val = 0.4},   
    {t = 160, cmd = "msg",   val = "EVASIVE ACTION"},
    {t = 180, cmd = "spawn", val = "SWOOP",  x = 80,  y = -60, path = 2}, 
    {t = 300, cmd = "bank",  val = -0.4},  
    {t = 330, cmd = "spawn", val = "V_FORM", x = -60, y = 10,  path = 1},
    {t = 450, cmd = "bank",  val = 0.0},   
    {t = 500, cmd = "msg",   val = "APPROACHING DEATH STAR"}
}
local script_ptr = 1

function L(a,b,c,d,cl) line(a,b,c,d,cl or 1) end
function clamp(v, min, max) return v < min and min or (v > max and max or v) end
function all(t) local i=0 return function() i=i+1 return t[i] end end
function add(t,v) t[#t+1]=v end
function rm(t,i) table.remove(t,i) end

function pj(x, y, z) 
    if z <= 0 then return -1, -1 end
    local dx, dy = x - cam_x, y - cam_y
    local rx = dx * math.cos(cam_roll) - dy * math.sin(cam_roll)
    local ry = dx * math.sin(cam_roll) + dy * math.cos(cam_roll)
    return flr((rx / z) * 100 + 64), flr((ry / z) * 100 + 64)
end

function draw_sega_hud()
    rect(2, 2, 124, 12, 1) rectf(3, 3, 32, 10, 1) 
    print("SCORE", 5, 5, 0) print(string.format("%08d", score), 40, 5, 1)

    local rx, ry = 112, 108
    print(string.format("%03d", math.floor(shield)), rx-24, ry-2, 1)
    L(40, ry+2, rx-26, ry+2)
    rectf(40, ry-4, 34, 9, 1) print("SHIELD", 44, ry-3, 0)

    local r_out, r_in_base, segments, gap = 15, 7, 5, 0.15 
    local total_arc, start_ang = math.pi * 1.5, -math.pi * 0.75 
    
    for i = 1, segments do
        local a1 = start_ang + (i-1)*(total_arc/segments)
        local a2 = start_ang + i*(total_arc/segments) - gap
        local seg_min = 100 - i*20
        
        if shield > seg_min then
            local health = clamp((shield - seg_min) / 20, 0, 1)
            local inner_r = r_out - (r_out - r_in_base) * health
            for a = a1, a2, 0.05 do
                L(rx + math.cos(a)*inner_r, ry + math.sin(a)*inner_r, 
                  rx + math.cos(a)*r_out, ry + math.sin(a)*r_out)
            end
        end
    end
end

function spawn_squad(form_type, bx, by, path_type)
    if form_type == "V_FORM" then
        add(en, {a=true, bx=bx, by=by, z=300, path=path_type})
        add(en, {a=true, bx=bx-40, by=by-20, z=330, path=path_type})
        add(en, {a=true, bx=bx+40, by=by-20, z=330, path=path_type})
    elseif form_type == "SWOOP" then
        add(en, {a=true, bx=bx, by=by, z=300, path=path_type})
        add(en, {a=true, bx=bx+30, by=by-20, z=320, path=path_type})
    end
end

function _init()
    shield, score, ticks, script_ptr = 100, 12800, 0, 1
    st, en, ls = {}, {}, {}
    for i=1, 60 do add(st, {x=rnd(800)-400, y=rnd(800)-400, z=rnd(200)+1}) end
end

function upd_lasers()
    for i=#ls, 1, -1 do
        local l, hit = ls[i], false
        l.z = l.z + 20 -- Fast laser speed
        
        -- Check collisions with enemies
        for e in all(en) do 
            if e.a and math.abs(l.z - e.z) < 25 then
                local sx, sy = pj(e.x, e.y, e.z)
                -- Compare crosshair projection to enemy projection
                if sx > 0 and math.abs(sx - l.tx) < 20 and math.abs(sy - l.ty) < 20 then
                    e.a, e.ex, hit = false, 15, true 
                    score = score + 250
                    sfx(1, 40, 7, 2, 10) -- Explosion SFX
                    break
                end
            end
        end
        
        -- Remove if it hits something or flies too far
        if hit or l.z >= 200 then rm(ls, i) end
    end
end

function _update()
    ticks = ticks + 1
    
    -- Aiming and Panning
    if btn(2) then cx=clamp(cx-3, 10, 118) end 
    if btn(3) then cx=clamp(cx+3, 10, 118) end
    if btn(0) then cy=clamp(cy-3, 10, 118) end 
    if btn(1) then cy=clamp(cy+3, 10, 118) end
    cam_x, cam_y = (cx - 64) * 0.8, (cy - 64) * 0.8

    -- Firing Logic
    if gc > 0 then gc = gc - 1 end
    if btn(4) and gc <= 0 then
        add(ls, {sx=gx[gi], sy=gy[gi], tx=cx, ty=cy, z=1})
        sfx(1, 85, 5, 0, 4) -- Laser SFX
        gi = (gi % 4) + 1   -- Cycle the 4 corners
        gc = 5              -- Cooldown
    end

    upd_lasers()

    -- Process Script
    if script_ptr <= #timeline then
        local evt = timeline[script_ptr]
        if ticks >= evt.t then
            if evt.cmd == "msg" then
                current_msg, msg_timer = evt.val, 90
            elseif evt.cmd == "bank" then
                target_roll = evt.val
            elseif evt.cmd == "spawn" then
                spawn_squad(evt.val, evt.x, evt.y, evt.path)
            end
            script_ptr = script_ptr + 1
        end
    end
    cam_roll = cam_roll + (target_roll - cam_roll) * 0.05

    -- Background Stars
    for s in all(st) do
        s.z = s.z - 2
        if s.z <= 0 then s.x, s.y, s.z = rnd(800)-400, rnd(800)-400, 200 end
    end
    
    -- Enemy Flight Paths & Explosions
    lock_on = false
    for e in all(en) do
        if e.a then
            e.z = e.z - 2.5 
            
            if e.path == 1 then
                e.x, e.y = e.bx, e.by
            elseif e.path == 2 then
                e.x = e.bx + math.sin(e.z / 30) * 80
                e.y = e.by + (300 - e.z) * 0.3 
            end
            
            if e.z <= 0 then e.a = false end 
            
            -- Lock-On
            local sx, sy = pj(e.x, e.y, e.z)
            if sx > 0 and math.abs(sx - cx) < 20 and math.abs(sy - cy) < 20 then lock_on = true end
        elseif e.ex and e.ex > 0 then
            e.ex = e.ex - 1 -- Tick down the explosion timer
            e.z = e.z - 2.5 -- Debris keeps moving forward
        end
    end
    
    if msg_timer > 0 then msg_timer = msg_timer - 1 end
end

function _draw()
    cls(0)
    
    for s in all(st) do
        local sx, sy = pj(s.x, s.y, s.z)
        if sx > 0 and sx < 128 and sy > 0 and sy < 128 then pset(sx, sy, 1) end
    end
    
    -- Draw Enemies & Explosions
    for e in all(en) do
        local sx, sy = pj(e.x, e.y, e.z)
        if sx > -20 and sx < 148 then
            if e.a then
                local w, h, r = flr(180/e.z), flr(250/e.z), flr(80/e.z)
                circ(sx, sy, r, 1)
                L(sx-w, sy, sx+w, sy)
                rect(sx-w-1, sy-h, 2, h*2, 1)
                rect(sx+w-1, sy-h, 2, h*2, 1)
                local tip = flr(w*0.3)
                L(sx-w, sy-h, sx-w+tip, sy-h-tip) L(sx-w, sy+h, sx-w+tip, sy+h+tip)
                L(sx+w, sy-h, sx+w-tip, sy-h-tip) L(sx+w, sy+h, sx+w-tip, sy+h+tip)
            elseif e.ex and e.ex > 0 then
                -- Geometric Sega-style Explosion
                local er = (15 - e.ex) * flr(80/e.z)
                circ(sx, sy, er, 1)
                -- Debris lines
                for a = 0, 5 do
                    local ang = a + (e.ex * 0.2) -- Spins as it expands
                    L(sx, sy, sx + math.cos(ang)*er*1.5, sy + math.sin(ang)*er*1.5)
                end
            end
        end
    end
    
    -- Draw Lasers (Thickened for Model 3 hardware feel)
    for l in all(ls) do
        local pt, ph = math.max(0, l.z - 30) / 100, l.z / 100
        local tx, ty = l.sx + (l.tx - l.sx) * pt, l.sy + (l.ty - l.sy) * pt
        local hx, hy = l.sx + (l.tx - l.sx) * ph, l.sy + (l.ty - l.sy) * ph
        L(tx, ty, hx, hy)
        L(tx+1, ty, hx+1, hy) -- Double thick line
    end
    
    -- Dynamic Reticle
    local g = 5 + flr((frame()%8)/4)
    circ(cx, cy, g, 1)
    L(cx-2, cy, cx+2, cy) L(cx, cy-2, cx, cy+2)
    
    if lock_on then
        rect(cx-12, cy-12, 24, 24, 1)
        L(cx-12, cy-12, cx-8, cy-8) L(cx+12, cy+12, cx+8, cy+8)
        L(cx+12, cy-12, cx+8, cy-8) L(cx-12, cy+12, cx-8, cy+8)
    end
    
    draw_sega_hud()
    
    if msg_timer > 0 and msg_timer % 10 > 3 then
        print(current_msg, 64 - (#current_msg * 2), 64, 1)
    end
end