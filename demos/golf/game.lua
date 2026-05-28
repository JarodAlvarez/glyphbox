-- GLYPHBOX Golf  (C) Gureedo 2026
local S_T=0 local S_OVR=1 local S_PR=2 local S_LD=3 local S_HS=4 local S_END=5
local PA=0 local PP=1 local PSW=2 local PFL=3
local CL={{"DRV",100,3},{"IRN",62,2},{"PUT",22,1}}
local DX={0,1,1,1,0,-1,-1,-1}
local DY={-1,-1,0,1,1,1,0,-1}
-- holes: {ball_x,ball_y,hole_px,hole_py,par, {tile,tx,ty,tw,th}...}
-- tx/ty/tw/th in tile units (8px each), hole_px/py in pixels
local HO={
  -- hole 1 par 4: dogleg right — narrow vert shaft, wide arm, green top-right
  {6,13,92,12,4,
   {1,6,3,2,11},{1,6,3,6,3},{4,8,4,2,1},{2,10,0,3,3}},
  -- hole 2 par 3: straight corridor, wide water crossing, bunker on green approach
  {6,13,52,12,3,
   {1,5,3,3,2},{3,4,5,6,2},{1,5,7,3,6},{4,5,10,2,2},{2,5,0,3,3}},
  -- hole 3 par 5: dogleg left — long vert, wide arm left, water+sand on arm
  {9,13,20,12,5,
   {1,9,3,2,11},{1,1,3,9,3},{3,5,4,2,2},{4,1,3,2,1},{2,1,0,3,3}},
}
local st,hi,strk,sc
local bx,by,ad,ci,wx,wy
local pw,pd,sf,fvx,fvy,ft,fto,lt,lmsg,psub

function sth(idx)
  hi=idx  strk=0
  local h=HO[idx]
  bx=h[1]*8+4  by=h[2]*8+4
  ad=0  ci=1
  local wd=rnd(8)
  wx=DX[wd+1]*0.5  wy=DY[wd+1]*0.5
  for y=0,15 do for x=0,15 do mset(x,y,0) end end
  for i=6,#h do
    local s=h[i]
    local t,tx,ty,tw,th=s[1],s[2],s[3],s[4],s[5]
    for ry=ty,ty+th-1 do for rx=tx,tx+tw-1 do
      mset(rx,ry,t)
    end end
  end
  st=S_OVR
end

function cshot()
  strk=strk+1
  local d=pw/100*CL[ci][2]
  fvx=clamp(bx+DX[ad+1]*d+wx*d*0.4,4,123)-bx
  fvy=clamp(by+DY[ad+1]*d+wy*d*0.4,4,123)-by
  fto=mid(16,flr(d*.65),999)  ft=0
end

function doland()
  local ox,oy=bx,by
  bx=clamp(bx+fvx,4,123)  by=clamp(by+fvy,4,123)
  local tp=mget(flr(bx/8),flr(by/8))
  if tp==3 then
    bx=ox  by=oy  strk=strk+1  lmsg="SPLASH +1"
  else
    local h=HO[hi]
    local dx=bx-h[3]  local dy=by-h[4]
    if dx*dx+dy*dy<=36 then
      sc[hi]=strk  lmsg="HOLE OUT!"  lt=80  st=S_HS  return
    end
    lmsg=tp==2 and "GREEN" or tp==1 and "LANDED" or "ROUGH +1"
    if tp~=1 and tp~=2 then strk=strk+1 end
  end
  lt=50  st=S_LD
end

function dhole()
  cls(0)  map(0,0,0,0,16,16)
  local adx,ady=DX[ad+1],DY[ad+1]
  for t=1,14 do
    local lx=bx+adx*t  local ly=by+ady*t
    pset(lx,ly,1-pget(lx,ly))
  end
  local hx,hy=HO[hi][3],HO[hi][4]
  line(hx,hy,hx,hy-8,0)  rectf(hx+1,hy-8,5,3,0)
  rectf(bx-2,by-2,5,5,0)
  rectf(bx-1,by-1,3,3,1)
  rectf(0,112,128,16,0)
  local wn=wx*wx+wy*wy<0.01 and "CLM"
    or wx>0 and "E" or wx<0 and "W" or wy>0 and "S" or "N"
  print("H"..hi.." P"..HO[hi][5].." S:"..strk,2,114,1)
  print(CL[ci][1].." W:"..wn,2,121,1)
end

function dpersp()
  cls(0)
  for y=65,127 do
    local t=(y-65)/62
    line(flr(54-t*46),y,flr(74+t*46),y,1)
  end
  line(0,65,127,65,1)
  line(64,50,64,65,1)  rectf(65,50,4,3,1)
  local gf=6
  if psub==PSW then gf=sf<8 and 7 or 8 end
  rectf(60,108,8,8,0)  spr(gf,60,108)
  if psub==PFL then
    local ly=flr(108-sin(ft/fto*0.5)*56)
    rectf(62,ly-1,4,4,0)  rectf(63,ly,2,2,1)
  end
  print("H"..hi.." S:"..strk.." "..CL[ci][1],2,2,1)
end

function _init()
  sc={}  st=S_T
end

function _update()
  if st==S_T then
    if btnp(4) then sc={}  sth(1) end
  elseif st==S_OVR then
    if btnp(2) then ad=(ad-1+8)%8 end
    if btnp(3) then ad=(ad+1)%8 end
    if btnp(0) then ci=ci==1 and 3 or ci-1 end
    if btnp(1) then ci=ci==3 and 1 or ci+1 end
    if btnp(4) then
      st=S_PR  pw=0  pd=1
      psub=ci==3 and PP or PA
    end
  elseif st==S_PR then
    if psub==PA then
      if btnp(4) then psub=PP end
    elseif psub==PP then
      pw=pw+pd*CL[ci][3]
      if pw>=100 then pw=100  pd=-1
      elseif pw<=0 then pw=0  pd=1 end
      if btnp(4) then
        cshot()
        if ci==3 then psub=PFL
        else sf=0  psub=PSW end
      end
    elseif psub==PSW then
      sf=sf+1
      if sf>=16 then psub=PFL end
    elseif psub==PFL then
      ft=ft+1
      if ci==3 then bx=bx+fvx/fto  by=by+fvy/fto end
      if ft>=fto then
        if ci==3 then fvx=0  fvy=0 end
        doland()
      end
    end
  elseif st==S_LD then
    lt=lt-1
    if lt<=0 then st=S_OVR end
  elseif st==S_HS then
    lt=lt-1
    if btnp(4) then lt=1 end
    if lt<=0 then
      if hi<3 then sth(hi+1) else st=S_END end
    end
  elseif st==S_END then
    if btnp(4) then sc={}  sth(1) end
  end
end

function _draw()
  if st==S_T then
    cls(0)
    print("GOLF",48,28,1)
    print("LR:AIM UD:CLUB A:GO",4,86,1)
  elseif st==S_OVR then
    dhole()
  elseif st==S_PR then
    if ci==3 then dhole()
    else dpersp() end
    if psub==PP or psub==PSW then
      rectf(2,120,124,7,0)  rect(2,120,124,7,1)
      rectf(3,121,flr(pw/100*120)+2,5,1)
    end
  elseif st==S_LD then
    dhole()
    rectf(0,50,128,24,0)
    print(lmsg,34,56,1)
    print("STR:"..strk,46,66,1)
  elseif st==S_HS then
    cls(0)
    local h=HO[hi]
    print("HOLE "..hi,44,20,1)
    print("PAR "..h[5].."  GOT "..strk,22,40,1)
    local r=strk-h[5]
    print(r==0 and "PAR" or (r<0 and r.." UNDER" or "+"..r),32,56,1)
    print("A:NEXT",44,100,1)
  elseif st==S_END then
    cls(0)
    print("FINAL SCORE",28,8,1)
    local tot=0
    for i=1,3 do
      local s=sc[i] or 0  tot=tot+s
      local r=s-HO[i][5]
      print("H"..i.." "..s.." "..(r<0 and r or "+"..r),18,28+i*14,1)
    end
    print("TOT:"..tot,40,76,1)
    print("A:PLAY AGAIN",28,110,1)
  end
end
