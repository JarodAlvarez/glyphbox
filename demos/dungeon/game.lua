-- sl(x,y): returns 1 if screen pixel (x,y) is a solid wall tile
function sl(x,y)
  local tx=flr(x/8) ty=flr(y/8)
  if tx<1 or tx>14 or ty<1 then return 1 end
  if ty>14 then return (tx~=8 or dop==0) and 1 or 0 end
  if tx==3 or tx==4 or tx==11 or tx==12 then
    if ty==3 or ty==4 or ty==10 or ty==11 then return 1 end
  end
  return 0
end

function _init()
  px=64 py=56 fd=0
  -- chests: x={top-left, top-right, bottom-left}, y, open flag
  cx={12,108,12} cy={12,12,108} co={0,0,0}
  nc=0 dm="" dt=0 st=0 dop=0
end

function _update()
  if st==1 then
    if btnp(4) then _init() end
    return
  end
  if dt>0 then dt=dt-1 end
  local dx,dy=0,0
  if btn(0) then dy=-2 fd=1 end
  if btn(1) then dy=2  fd=0 end
  if btn(2) then dx=-2 fd=2 end
  if btn(3) then dx=2  fd=3 end
  if dx~=0 or dy~=0 then
    local nx=px+dx ny=py+dy
    if sl(nx-2,ny-2)==0 and sl(nx+2,ny-2)==0 and
       sl(nx-2,ny+2)==0 and sl(nx+2,ny+2)==0 then
      px=nx py=ny
    end
  end
  if py>118 and dop==1 then st=1 return end
  if btnp(4) then
    for i=1,3 do
      if co[i]==0 and abs(px-cx[i])<12 and abs(py-cy[i])<12 then
        co[i]=1 nc=nc+1
        dm=nc<3 and "CHEST!" or "DOOR OPEN!"
        if nc==3 then dop=1 end
        dt=90 break
      end
    end
  end
end

function _draw()
  cls(0)
  map(0,0,0,0,16,16)
  if dop==0 then spr(8,64,120) end
  for i=1,3 do
    spr(co[i]==1 and 7 or 6, cx[i]-4, cy[i]-4)
  end
  spr(fd+2, px-4, py-4)
  if dt>0 then
    rectf(28,54,72,12,0)
    print(dm,36,58,1)
  end
  if st==1 then
    rectf(16,48,96,24,0)
    print("YOU ESCAPED!",24,54,1)
    print("A:RETRY",42,64,1)
  end
  print(nc.."/3",2,2,1)
end
