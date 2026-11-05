local D={ {}, {-17,-15,-10,-6,6,10,15,17}, {-9,-7,7,9}, {-8,8,-1,1}, {-8,8,-1,1,-9,-7,7,9}, {-8,8,-1,1,-9,-7,7,9} }
local V={10,30,30,50,90,900}

function _init()
  B={}
  local s="4235632411111111000000000000000000000000000000001111111142356324"
  for i=1,64 do local v=s:byte(i)-48 B[i]=i<17 and -v or v end
  T,C,S,H,G,M,U=1,36,0,0,0,{},0
end

function MVS(p)
  local m,v={},B[p]
  if v==0 then return m end
  local c,t,x=v>0 and 1 or -1,abs(v),(p-1)%8
  local function A(d,cx)
    if d>0 and d<65 and abs((d-1)%8-cx)<3 then
      local b=B[d] if b*c<=0 then table.insert(m,d) return b==0 end
    end
  end
  if t==1 then
    local d=c==1 and -8 or 8
    if B[p+d]==0 then
      table.insert(m,p+d)
      if (c==1 and p>48 or c==-1 and p<17) and B[p+d*2]==0 then table.insert(m,p+d*2) end
    end
    for _,o in ipairs({d-1,d+1}) do
      local d2=p+o
      if d2>0 and d2<65 and abs((d2-1)%8-x)<2 and B[d2]*c<0 then table.insert(m,d2) end
    end
  elseif t==2 or t==6 then
    for _,o in ipairs(D[t]) do A(p+o,x) end
    if t==6 and not M[p] then
      local function K(r,e1,e2,e3,d) if B[r]==c*4 and not M[r] and B[e1]==0 and B[e2]==0 and B[e3]==0 then table.insert(m,d) end end
      if c==1 and p==61 then K(64,62,63,63,63) K(57,58,59,60,59) elseif c==-1 and p==5 then K(8,6,7,7,7) K(1,2,3,4,3) end
    end
  else
    for _,o in ipairs(D[t]) do
      local cur,cx=p,x
      while A(cur+o,cx) do cur=cur+o cx=(cur-1)%8 end
    end
  end
  return m
end

function IC(c)
  local k=0 for i=1,64 do if B[i]==c*6 then k=i break end end
  for i=1,64 do if B[i]*c<0 then for _,m in ipairs(MVS(i)) do if m==k then return true end end end end
end

function LGL(p)
  local m,v,c={},B[p],B[p]>0 and 1 or -1
  for _,d in ipairs(MVS(p)) do
    local cap=B[d] B[d],B[p]=v,0
    if not IC(c) then table.insert(m,d) end
    B[p],B[d]=v,cap
  end
  return m
end

function MV(s,d)
  M[s]=true
  if abs(B[s])==6 and abs(d-s)==2 then
    if d==63 then B[62],B[64],M[64]=B[64],0,true end
    if d==59 then B[60],B[57],M[57]=B[57],0,true end
    if d==7 then B[6],B[8],M[8]=B[8],0,true end
    if d==3 then B[4],B[1],M[1]=B[1],0,true end
  end
  A={p=B[s],d=d,s=s,x=((s-1)%8)*16+4,y=flr((s-1)/8)*16+4,X=((d-1)%8)*16+4,Y=flr((d-1)/8)*16+4,t=0,f=0,c=B[d]~=0}
  B[d],B[s]=B[s],0
end

function _update()
  if G~=0 then if btnp(4) then _init() end return end
  if U>0 then
    if btnp(0) and U>1 then U=U-1 end
    if btnp(1) and U<3 then U=U+1 end
    if btnp(4) then G,U=(U==2 and -1 or (U==3 and 2 or 0)),0 end return
  end
  if btn(4) then H=H+1 if H==45 then U=1 end else H=0 end
  
  if A then
    local f=A.f
    if A.c then
      if f==0 then sfx(0,60,6,0,3) elseif f==3 then sfx(0,64,6,0,3) elseif f==6 then sfx(0,67,6,0,3) elseif f==9 then sfx(0,72,6,0,6) end
    else if f==0 then sfx(0,55,4,1,4) end end
    A.f=f+1 A.t=A.t+(A.c and .08 or .15)
    if A.t>=1 then A=nil end return
  end

  if not R then
    local n=0 for i=1,64 do if B[i]*T>0 then n=n+#LGL(i) end end
    if n==0 then G=IC(T) and -T or 2 return end
  end

  if T==1 then
    if btnp(0) and C>8 then C=C-8 end
    if btnp(1) and C<57 then C=C+8 end
    if btnp(2) and (C-1)%8>0 then C=C-1 end
    if btnp(3) and (C-1)%8<7 then C=C+1 end
    if btnp(4) then
      if S==0 then if B[C]>0 then S=C end else
        local k=false for _,m in ipairs(LGL(S)) do if m==C then k=true break end end
        if k then MV(S,C) S,T=0,-1 else S=B[C]>0 and C or 0 end
      end
    end
  else
    if not R then
      AI={} for i=1,64 do if B[i]<0 then for _,d in ipairs(LGL(i)) do table.insert(AI,{s=i,d=d,v=9999}) end end end
      R,I,O=true,1,nil
    else
      if I<=#AI then
        local m=AI[I]
        local cp,mw=B[m.d],-9999
        B[m.d],B[m.s]=B[m.s],0
        for i=1,64 do
          if B[i]>0 then
            for _,wd in ipairs(MVS(i)) do
              local wc=B[wd] B[wd],B[i]=B[i],0
              local sc=0 for j=1,64 do local p=B[j] if p~=0 then sc=sc+(p>0 and V[p] or -V[abs(p)]) end end
              if sc>mw then mw=sc end
              B[i],B[wd]=B[wd],wc
            end
          end
        end
        B[m.s],B[m.d]=B[m.d],cp
        m.v=mw+(rnd(10)/100.0) if not O or m.v<O.v then O=m end I=I+1
      else if O then MV(O.s,O.d) end T,R=1,false end
    end
  end
end

function _draw()
  cls(0)
  for i=0,63 do
    local x,y=i%8,flr(i/8)
    if (x+y)%2==0 then rectf(x*16,y*16,16,16,1) end
    local p=B[i+1]
    if p~=0 and (not A or i+1~=A.d) then
      local px,py=x*16+4,y*16+4
      rectf(px-1,py-1,10,10,0) spr((p>0 and p-1 or -p+5),px,py)
    end
  end
  if S~=0 then local x,y=((S-1)%8)*16,flr((S-1)/8)*16 rect(x,y,16,16,1) rect(x+2,y+2,12,12,1) end
  if not A then
    if frame()%30<15 then local x,y=((C-1)%8)*16,flr((C-1)/8)*16 rect(x,y,16,16,1) rect(x+1,y+1,14,14,0) end
  else
    local x,y=flr(A.x+(A.X-A.x)*A.t),flr(A.y+(A.Y-A.y)*A.t)
    rectf(x-1,y-1,10,10,0) spr((A.p>0 and A.p-1 or -A.p+5),x,y)
  end
  if T==-1 and not A and G==0 then
    local s={"|","/","-","\\"} rectf(0,114,40,14,0) rect(0,114,40,14,1) print("AI "..s[flr(frame()/4)%4+1],4,118,1)
  end
  if U>0 then
    rectf(32,36,64,56,0) rect(32,36,64,56,1)
    print("PAUSE",54,42,1) print("RESUME",48,56,1) print("RESIGN",48,68,1) print("DRAW",48,80,1) print(">",40,44+(U*12),1)
  end
  if G~=0 then
    rectf(20,50,88,28,0) rect(20,50,88,28,1)
    print((G==1 and "WHITE WINS!" or (G==-1 and "BLACK WINS!" or "STALEMATE!")),32,56,1) hint(34,68) print("RESTART",53,68,1)
  end
end