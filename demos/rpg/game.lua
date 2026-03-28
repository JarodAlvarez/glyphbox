-- GLYPH-CRYPT: Optimized Spawning Build
function _init()
  s,st=2,0 -- state: 0:PLAY, 1:UPG, 2:TITLE, 3:TRANS
end

-- Wall Check (W)
function W(x,y)
  if x<8 or x>112 or y<8 or y>112 then return 1 end
  for i=0,7,7 do for j=0,7,7 do
    if w[(flr((x+i)/8)*16)+flr((y+j)/8)] then return 1 end
  end end
end

function fc()
  local x,y repeat x,y=flr(rnd(13)+1)*8,flr(rnd(13)+1)*8 until not W(x,y)
  return x,y
end

function nf()
  at,it,es,os,w=0,0,0,{},{}
  for i=1,20 do
    local x,y=flr(rnd(14)+1)*8,flr(rnd(14)+1)*8
    if abs(x-64)>16 or abs(y-64)>16 then w[(x/8*16)+(y/8)]=1 end
  end
  px,py=fc()
  g,s,st=1,3,0
  
  -- Optimized Spawning: Manhattan Distance for better safety (48px = 6 tiles)
  if fl%5==0 then
    local x,y repeat x,y=fc() until abs(x-px)+abs(y-py)>48
    os[1]={t=3,x=x,y=y,h=15+fl,s=.6,b=1,r=60}
  else
    for i=1,2+fl do
      local x,y repeat x,y=fc() until abs(x-px)+abs(y-py)>48
      os[#os+1]={t=3,x=x,y=y,h=2,s=.4}
    end
  end
end

function _update()
  if s==2 then if btnp(4) then hp,mhp,fl,sk,ad=10,10,1,0,12 nf() end return end
  if hp<=0 then if btnp(4) then _init() end return end
  st=st+1
  if s==3 then if st>45 then s,st=0,0 end return end
  if s==1 then
    if st>30 then
      if btnp(2) then mhp,s,st=mhp+5,0,0 hp=mhp fl=fl+1 nf() end
      if btnp(3) then ad,s,st=ad+4,0,0 fl=fl+1 nf() end
    end
    return
  end
  if sk>0 then sk=sk-1 end
  local x,y=0,0
  if btn(0) then y=-1.1 g=0 end
  if btn(1) then y=1.1 g=1 end
  if btn(2) then x=-1.1 g=2 end
  if btn(3) then x=1.1 g=3 end
  if not W(px+x,py) then px=px+x end
  if not W(px,py+y) then py=py+y end
  if btnp(4) and at<=0 then at=ad sfx(0,40,5,0,4) end
  if at>0 then at=at-1 end
  if it>0 then it=it-1 end
  for i=#os,1,-1 do
    local e=os[i]
    if e.b and e.r>0 then e.r=e.r-1
    else
      local p,d=e.s,abs(e.x-px)+abs(e.y-py)
      if e.b then
        if d<12 then p=-.2 end
        if frame()%120<20 then p=1.3 end
      end
      local x,y=e.x<px and p or -p,e.y<py and p or -p
      if not W(e.x+x,e.y) then e.x=e.x+x end
      if not W(e.x,e.y+y) then e.y=e.y+y end
    end
    if at>ad/2 then
      local x,y=px,py
      if g==0 then y=y-10 elseif g==1 then y=y+10
      elseif g==2 then x=x-10 else x=x+10 end
      if abs(e.x-x)<8 and abs(e.y-y)<8 then
        e.h=e.h-1 sk,e.r=4,15
        if e.h<=0 then
          if e.b then s,st=1,0 else table.remove(os,i) end
          sfx(1,20,7,2,10)
        end
      end
    end
    if abs(e.x-px)<6 and abs(e.y-py)<6 and it<=0 then
      hp=hp-1 it,e.r=30,45 sfx(1,10,7,2,6) invert()
    end
  end
  
  -- Consistently applied to the level exit
  if #os==0 and es==0 and s==0 then 
    es=1 repeat ex,ey=fc() until abs(ex-px)+abs(ey-py)>48 
  end
  if es==1 and abs(px-ex)<6 and abs(py-ey)<6 then fl=fl+1 nf() end
end

function _draw()
  cls(0)
  if s==2 then
    print("GLYPH-CRYPT",31,40,1)
    if (frame()%30)<20 then print("PRESS [A]",40,80,1) end
    return
  end
  local x,y=0,0
  if sk>0 then x,y=rnd(4)-2,rnd(4)-2 end
  if s==1 then
    print("DEFEATED!",38,40,1)
    if st>30 then print("[L] HP+5 [R] ATK+4",18,70,1)
    else rectf(50,75,(st/30)*28,2,1) end
    return
  end
  map(0,0,x,y,16,16)
  for k,_ in pairs(w) do
    spr(0,(flr(k/16)*8)+x,(k%16*8)+y)
  end
  for _,e in ipairs(os) do
    spr(3,e.x+x,e.y+y)
    if e.b then rect(e.x-2+x,e.y-2+y,12,12,1) end
  end
  if es==1 then spr(5,ex+x,ey+y) end
  if it%4<2 then spr(2,px+x,py+y,g==2) end
  if at>0 then
    local ax,ay=px,py
    if g==0 then ay=ay-8 elseif g==1 then ay=ay+8
    elseif g==2 then ax=ax-6 else ax=ax+6 end
    circ(ax+4+x,ay+4+y,5,1)
  end
  if s==3 then
    rectf(36,54,56,14,0) rect(36,54,56,14,1)
    print("FLOOR "..fl,42,58,1)
  end
  rectf(0,120,128,8,1)
  print("F:"..fl.." H:"..hp.."/"..mhp,2,121,0)
  if hp<=0 then print("DEAD. [A] RETRY",35,60,1) end
end