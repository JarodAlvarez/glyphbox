local W,H,SZ=10,20,6
local OX,OY=3,4
local LPTS={0,10,30,60,100}
local ADUR=20

-- piece rotations: P[id][rot] = flat {x1,y1,x2,y2,x3,y3,x4,y4}
local P={
  {{0,0,1,0,2,0,3,0},{0,0,0,1,0,2,0,3}},
  {{0,0,1,0,0,1,1,1}},
  {{1,0,0,1,1,1,2,1},{0,0,0,1,1,1,0,2},{0,0,1,0,2,0,1,1},{1,0,0,1,1,1,1,2}},
  {{1,0,2,0,0,1,1,1},{0,0,0,1,1,1,1,2}},
  {{0,0,1,0,1,1,2,1},{1,0,0,1,1,1,0,2}},
  {{2,0,0,1,1,1,2,1},{0,0,0,1,0,2,1,2},{0,0,1,0,2,0,0,1},{0,0,1,0,1,1,1,2}},
  {{0,0,0,1,1,1,2,1},{0,0,1,0,0,1,0,2},{0,0,1,0,2,0,2,1},{1,0,1,1,0,2,1,2}},
}

local bd,pid,gx,gy,gr,nid
local sc,lv,lns,sp,tm,go
local arows,aset,at  -- line-clear animation state

local function blks(id,r)
  local t=P[id][((r-1)%#P[id])+1]
  local b={}
  for i=1,8,2 do b[#b+1]={t[i],t[i+1]} end
  return b
end

local function fit(id,x,y,r)
  for _,b in ipairs(blks(id,r)) do
    local bx,by=x+b[1],y+b[2]
    if bx<1 or bx>W or by>H then return false end
    if by>=1 and bd[by][bx]~=0 then return false end
  end
  return true
end

local function nrow()
  local r={}; for x=1,W do r[x]=0 end; return r
end

local function spawn(id)
  pid,gx,gy,gr=id,4,0,1
  go=not fit(id,4,0,1)
end

local function do_clear()
  local n=#arows
  for i=n,1,-1 do table.remove(bd,arows[i]) end
  for i=1,n do table.insert(bd,1,nrow()) end
  lns=lns+n
  sc=sc+LPTS[n+1]*(lv+1)
  lv=flr(sc/500)
  sp=mid(4,30-lv*3,30)
  arows,aset={},{}
  spawn(nid); nid=rnd(7)+1
end

local function lock()
  for _,b in ipairs(blks(pid,gr)) do
    local bx,by=gx+b[1],gy+b[2]
    if by>=1 then bd[by][bx]=1 end
  end
  arows,aset,at={},{},0
  for y=1,H do
    local full=true
    for x=1,W do if bd[y][x]==0 then full=false; break end end
    if full then arows[#arows+1]=y; aset[y]=true end
  end
  if #arows==0 then do_clear() end
end

function _init()
  bd={}
  for y=1,H do bd[y]=nrow() end
  sc,lv,lns,sp,tm,go=0,0,0,30,0,false
  arows,aset,at={},{},0
  nid=rnd(7)+1; spawn(rnd(7)+1)
end

local dr={}
local function held(b)
  if btnp(b) then dr[b]=0; return true end
  if btn(b) then
    dr[b]=(dr[b] or 0)+1
    return dr[b]>10 and dr[b]%4==0
  end
  dr[b]=0; return false
end

function _update()
  if go then if btnp(BTN_A) then _init() end; return end
  if #arows>0 then at=at+1; if at>=ADUR then do_clear() end; return end
  if held(BTN_L) and fit(pid,gx-1,gy,gr) then gx=gx-1 end
  if held(BTN_R) and fit(pid,gx+1,gy,gr) then gx=gx+1 end
  if btnp(BTN_U) then
    while fit(pid,gx,gy+1,gr) do gy=gy+1 end
    lock(); tm=0; return
  end
  if btnp(BTN_A) then
    local nr=gr%#P[pid]+1
    if fit(pid,gx,gy,nr) then gr=nr
    elseif fit(pid,gx-1,gy,nr) then gx=gx-1; gr=nr
    elseif fit(pid,gx+1,gy,nr) then gx=gx+1; gr=nr end
  end
  tm=tm+1
  if tm>=(btn(BTN_D) and 2 or sp) then
    tm=0
    if fit(pid,gx,gy+1,gr) then gy=gy+1 else lock() end
  end
end

local function cell(x,y)
  return OX+(x-1)*SZ, OY+(y-1)*SZ
end

function _draw()
  cls(0)
  rect(OX-1,OY-1,W*SZ+2,H*SZ+2,1)
  for y=1,H do for x=1,W do
    local v=aset[y] and (at%4<2 and 1 or 0) or bd[y][x]
    if v~=0 then
      local px,py=cell(x,y); rectf(px,py,SZ-1,SZ-1,1)
    end
  end end
  if not go and #arows==0 then
    for _,b in ipairs(blks(pid,gr)) do
      local bx,by=gx+b[1],gy+b[2]
      if by>=1 then
        local px,py=cell(bx,by); rectf(px,py,SZ-1,SZ-1,1)
      end
    end
  end
  local ux=OX+W*SZ+5
  print("SCR",ux,OY,1)
  print(sc,ux,OY+8,1)
  print("LV",ux,OY+20,1)
  print(lv,ux,OY+28,1)
  print("LNS",ux,OY+40,1)
  print(lns,ux,OY+48,1)
  print("NXT",ux,OY+60,1)
  for _,b in ipairs(blks(nid,1)) do
    rectf(ux+b[1]*5,OY+70+b[2]*5,4,4,1)
  end
  if go then
    rectf(14,52,100,32,0); rect(14,52,100,32,1)
    print("GAME OVER",22,60,1)
    print("A:RESTART",22,70,1)
  end
end
