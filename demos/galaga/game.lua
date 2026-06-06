-- Galaga for GLYPHBOX
-- spr0=ship spr1=bee spr2=butterfly spr3=boss spr4=explosion

COLS=5 ROWS=4 N=20

function nw()
  et,ea={},{}
  for i=1,N do
    local r=flr((i-1)/COLS)
    et[i]=r==0 and 3 or r<3 and 2 or 1
    ea[i]=true
  end
  fox,fdir=0,1
  fspd=0.4+wave*0.08
  dcd=clamp(100-wave*10,40,100)
  dvr,dvex,dvey,dvvx,dvvy,dvph=0,0,0,0,0,0
  dtimer=0
  xp={} pb={} eb={}
end

function epos(i)
  local c=(i-1)%COLS
  local r=flr((i-1)/COLS)
  return 32+c*14+fox, 10+r*12
end

function _init()
  score,lives,wave=0,3,1
  px=60
  gs=0
  nw()
end

function alive()
  for i=1,N do if ea[i] then return true end end
  return false
end

function hit_player()
  if gs~=1 then return end
  xp[#xp+1]={x=px,y=114,t=15}
  lives=lives-1
  sfx(1,12,7,2,5)
  px=60 pb={}
  if lives<=0 then gs=2 end
end

function _update()
  if gs~=1 then
    if btnp(BTN_A) then
      if gs==2 then _init() end
      gs=1
    end
    return
  end

  if btn(BTN_L) and px>1   then px=px-2 end
  if btn(BTN_R) and px<119 then px=px+2 end

  if btnp(BTN_A) and #pb<3 then
    pb[#pb+1]={x=px+3,y=114}
    sfx(0,48,7,0,1)
  end

  -- Player bullets: move + hit
  local i=1
  while i<=#pb do
    pb[i].y=pb[i].y-4
    if pb[i].y<0 then table.remove(pb,i)
    else
      local hit=false
      for j=1,N do
        if ea[j] then
          local hx,hy=epos(j)
          if j==dvr then hx=dvex hy=dvey end
          if pb[i].x>=hx and pb[i].x<=hx+7 and pb[i].y>=hy and pb[i].y<=hy+7 then
            ea[j]=false
            if j==dvr then dvr=0 end
            xp[#xp+1]={x=hx,y=hy,t=10}
            score=score+(et[j]==3 and 400 or et[j]==2 and 160 or 100)
            sfx(1,24,7,2,3)
            hit=true break
          end
        end
      end
      if hit then table.remove(pb,i) else i=i+1 end
    end
  end

  -- Formation oscillation
  fox=fox+fdir*fspd
  if fox>18 then fdir=-1 elseif fox<-18 then fdir=1 end

  -- Spawn diver
  dtimer=dtimer+1
  if dvr==0 and dtimer>dcd then
    local k,t=0,0
    repeat k=rnd(N)+1 t=t+1 until ea[k] or t>20
    if ea[k] then
      local ex0,ey0=epos(k)
      dvr=k dvex=ex0 dvey=ey0 dtimer=0 dvph=0
      local dx=(px+3)-ex0
      local d=((dx*dx+(128-ey0)^2)^0.5)
      dvvx=dx/d*2.2 dvvy=(128-ey0)/d*2.2
    end
  end

  if dvr>0 then
    if dvph==0 then
      -- Dive toward player with wobble
      dvex=dvex+dvvx+sin(frame()/40)*1.5
      dvey=dvey+dvvy
      if dvex+7>=px and dvex<=px+7 and dvey+7>=114 and dvey<=121 then
        ea[dvr]=false dvr=0
        hit_player()
      elseif dvey>95 then
        -- Switch to return, fire at player
        dvph=1
        if #eb<3 then
          local bdx=(px+3)-dvex
          local bdy=114-dvey
          local bd=((bdx*bdx+bdy*bdy)^0.5)
          if bd>0 then
            eb[#eb+1]={x=dvex+3,y=dvey+4,vx=bdx/bd*1.5,vy=bdy/bd*1.5}
          end
        end
      end
    else
      -- Return to formation slot
      local tx,ty=epos(dvr)
      local dx=tx-dvex
      local dy=ty-dvey
      local d=((dx*dx+dy*dy)^0.5)
      if d<5 then
        dvr=0
      else
        dvvx=dx/d*2.5 dvvy=dy/d*2.5
        dvex=dvex+dvvx dvey=dvey+dvvy
      end
    end
  end

  -- Enemy bullets: move + hit player
  local j=1
  while j<=#eb do
    eb[j].x=eb[j].x+eb[j].vx
    eb[j].y=eb[j].y+eb[j].vy
    if eb[j].y>128 or eb[j].x<0 or eb[j].x>128 then
      table.remove(eb,j)
    elseif eb[j].x+2>=px and eb[j].x<=px+7 and eb[j].y+2>=114 and eb[j].y<=121 then
      table.remove(eb,j)
      hit_player()
    else
      j=j+1
    end
  end

  -- Explosions
  local m=1
  while m<=#xp do
    xp[m].t=xp[m].t-1
    if xp[m].t<=0 then table.remove(xp,m) else m=m+1 end
  end

  if not alive() then wave=wave+1 nw() end
end

function _draw()
  cls(0)

  if gs==0 then
    print("GALAGA",   42, 50, 1)
    print("A:START",  40, 64, 1)
    print("L/R:MOVE", 32, 76, 1)
    print("GUREEDO",  40,118, 1)
    return
  end

  for i=1,N do
    if ea[i] then
      local ex,ey=epos(i)
      if i==dvr then ex=dvex ey=dvey end
      spr(et[i],ex,ey)
    end
  end

  -- Player bullets (tall thin white rect)
  for i=1,#pb do rectf(pb[i].x,pb[i].y,2,4,1) end

  -- Enemy bullets (small square)
  for i=1,#eb do rectf(eb[i].x,eb[i].y,3,3,1) end

  spr(0,px,114)

  for i=1,#xp do spr(4,xp[i].x,xp[i].y) end

  print("SC:"..score, 2,  1, 1)
  print("W"..wave,   58,  1, 1)
  for i=1,lives do rectf(126-i*8,1,6,6,1) end

  if gs==2 then
    rectf(20,46,88,36,0)
    rect( 20,46,88,36,1)
    print("GAME OVER",36,52,1)
    print("SC:"..score,40,62,1)
    print("A:RETRY",  40,72,1)
  end
end
