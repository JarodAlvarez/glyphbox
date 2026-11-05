-- SUNSET RUN
-- Arcade-style pseudo-3D racer. A gas, DOWN brake, LEFT/RIGHT steer.
-- Reach each checkpoint before the clock runs out. Every stage ends in a
-- fork: keep left or right to pick the next one. 5 levels, 15 stages,
-- 5 goals. Written tersely so the cart prints on <= 8 cards; integer API
-- args are floored because the web build's Lua 5.4 rejects fractions.

local F,max,min=flr,math.max,math.min
local SL,RW,CH,DP,HY,ND,V,SP,FZ,PZ=20,50,60,64,58,60,12,130,70,64
local NM={"COAST","DESERT","CITY","FOREST","ALPS"}
local TT={0,1,3,2,4,1,3,0,2,4,4,2,3,1,0}
-- per theme: sky, grass masks for the two bands, roadside kinds, hill height, spacing
local TH={{1,5,1,"p",20,6,0,5,1},{1,15,5,"c",8,7,12,23,2},{0,5,1,"b",15,3,14,4,4},
 {1,5,0,"t",35,4,5,6,6},{1,15,10,"t",55,5,24,50,6}}
-- shapes: x,y,w,h,colour rects (+79 per byte), 2 world units per cell
local SH={p=[[OERYOP<RXOR4RWOK1WROT1XROH3SSO[3SSOQ.TRO]],
c=[[N;RcOI@QVOIETQOSBQUOQFSQO]],
r=[[HJ]TOJGXRO]],
b=[[E!c}OH%STPR%STPH/STPR/STPH9STPR9STP]],
t=[[NJQTOHB]WOJ;YVOL5UUON1QSO]],
n=[[NJQTOHB]WOJ;YVOL5UUON1QSOHB]PPJ;YPPL5UPP]],
s=[[NHQVOH>]YOJ@QQPLBQQPJDQQPO@QQPQBQQPODQQP]],
C=[[GG_UOID[ROGLSROSLSROIHRPPRHRPPKEWPP]],
T=[[F7acOGKSSOSKSSON8PaPHIRPPSIRPP]]}
local CAR={
"      .......   ",
"      .......   ",
"   .............",
"   .############",
"....############",
"..##############",
".###############",
".##.............",
".##.######......",
".##.............",
".############.##",
".############...",
"................",
"..#..#..        ",
"........        ",
"..#..#..        ",
"........        "}
-- Splash Wave: lead per 16th (- holds), bass root per half bar
local MEL="C-H-----G---E-G-G-A------------- -M-----L---J-L- -G------------- ----------HJ---H---G----------BC-@------------- -A-------------A------CE---H-G-G-E---C-@-------@------BC---G-E- -F-------------"
local BAS="++&&&&-----((()))($$$$''"

local st,lv,L,th,C,OK,OX,rs
local gs,fc,pos,px,v,tm,sc,hi,cr,gh,bgx,ex,mt,eo,ft=0,0,0,0,0,0,0,0,0,0,0,0,0,-1,0
local msg,ofr=""
local tr,WX,SX,SY,SS,SC,SA,SB,BG={},{},{},{},{},{},{},{},{}

local function nm(s) return NM[TT[s+1]+1] end
local function R(n) rs=rs*16807%2147483647 return rs%n end
local function fx(n,w,d) sfx(1,n,6,w,d) ft=d end

local function gen(s)
  st,lv=s,0
  while (lv+1)*(lv+2)/2<=s do lv=lv+1 end
  th=TH[TT[s+1]+1]
  L,C,OK,OX,rs=640+lv*40,{},{},{},s*977+13
  local i,e=ND,L-FZ-40
  while e-i>10 do
    local n=min(20+R(50),e-i)
    local c=R(3)<1 and 0 or (R(2)*2-1)*(.3+R(7)/10)*(.6+lv*.12)
    for j=0,n-1 do C[i+j]=c*sin(j/n/2) end
    i=i+n
  end
  for j=s>0 and ND+2 or 8,L-1 do
    local k=th[4]
    if j%th[6]==0 then
      k=R(#k)+1
      OK[j],OX[j]=th[4]:sub(k,k),(R(2)*2-1)*(65+R(9)*5)
    end
  end
end

local function Yg(i)
  return th[5]*clamp(min(i-ND,L-FZ-40-i)/40,0,1)*(sin(i/83)+.5*sin(i/37))
end

-- road centres for segment i: main, second (fork or fading old branch)
local function off(i)
  if lv<4 and i>=L-FZ then
    local e=min(1,(i-L+FZ)/42)
    e=SP*e*e*(3-2*e)
    return -e,e
  end
  if gh~=0 and i<40 then return 0,gh*(2*SP+i*i) end
  return 0,false
end

local function bx(x,y,w,h,c,cl)
  local a,b,t,u=F(x),F(x+w),F(y),F(y+h)
  a,t=max(a,0),max(t,0)
  b,u=min(max(b,a+1),128),min(max(u,t+1),cl or 128)
  if b>a and u>t then rectf(a,t,b-a,u-t,c) end
end

local function ob(d,X,Y,s,m,cl)
  if s>.12 then
    for q=0,1 do
      for j=1,#d,5 do
        local x,y,w,h,c=d:byte(j,j+4)
        x,y,w,h,c=x-79,y-79,w-79,h-79,c-79
        if m then x=-x-w end
        if q>0 then bx(X+x*s,Y+y*s,w*s,h*s,c,cl)
        elseif c<1 and s>.4 then bx(X+x*s-1,Y+y*s-1,w*s+2,h*s+2,1,cl) end
      end
    end
  end
end

local function rd(x,w,y,b)
  bx(x-w*1.15,y,w*2.3,1,b)
  bx(x-w,y,w*2,1,0)
  if b>0 then bx(x-w*.37,y,w/15,1,1) bx(x+w*.3,y,w/15,1,1) end
end

local function arch(n,o)
  local p=SS[n]
  bx(SX[n]+o*p-RW*1.4*p,SY[n]-RW*1.7*p,RW*2.8*p,8*p,1,SC[n])
end

local function big(s,x,y,k)
  local g,W=BG[s],#s*6
  if not g then
    g={}
    rectf(0,0,128,8,0) print(s,0,0,1)
    for j=0,W*7 do
      if pget(j%W,F(j/W))>0 then g[#g+1]=j end
    end
    BG[s]=g
  end
  for q=0,1 do for _,j in ipairs(g) do
    rectf(x+j%W*k-1+q,y+F(j/W)*k-1+q,k+2-q*2,k+2-q*2,q)
  end end
end

local function scene()
  local t,sk=TT[st+1],th[1]
  rectf(0,0,128,HY,sk) rectf(0,HY,128,70,0)
  local o=F(bgx)
  if t==0 then
    local x=(100-F(o/4))%200-36
    circf(x,HY-13,13,0)
    for k=0,3 do rectf(x-14,HY-9+k*3,29,k+1,1) end
  end
  for x=0,127 do
    local h=F(th[7]*abs((x+o)/th[8]%2-1)+th[9]*sin((x+o)/97))
    if h>0 then rectf(x,HY-h,1,h,1-sk) end
  end
  local b=F(pos/SL)
  local k=(pos+PZ)/SL
  local pb=F(k)
  local cy=Yg(pb)+(Yg(pb+1)-Yg(pb))*(k-pb)+CH
  local x,dx=0,-(C[b] or 0)*1.5*(pos/SL-b)
  for n=0,ND+1 do WX[n]=x x=x+dx dx=dx+(C[b+n] or 0)*1.5 end
  k=k-b
  pb=F(k)
  local xa=WX[pb]+(WX[pb+1]-WX[pb])*(k-pb)+px*RW
  for n=1,ND+1 do
    local i=b+n
    local p=DP/(i*SL-pos)
    SX[n],SY[n],SS[n]=64+(WX[n]-xa)*p,HY+(cy-Yg(i))*p,p
    SA[n],SB[n]=off(i)
  end
  local my=128
  for n=1,ND do
    local Y1,Y2,b1=SY[n],SY[n+1],SB[n]
    SC[n]=my
    if Y2<my and Y2<Y1 then
      local bd,b2=F((b+n)/3)%2,SB[n+1] or b1
      for y=max(-F(-Y2),0),min(-F(-min(Y1,my))-1,127) do
        local t=(y-Y2)/(Y1-Y2)
        local X,p=SX[n+1]+(SX[n]-SX[n+1])*t,SS[n+1]+(SS[n]-SS[n+1])*t
        rectf(0,y,128,1,F(th[2+bd]/2^(y%4))%2)
        rd(X+(SA[n+1]+(SA[n]-SA[n+1])*t)*p,RW*p,y,bd)
        if b1 then rd(X+(b2+(b1-b2)*t)*p,RW*p,y,bd) end
        my=min(my,y)
      end
    end
  end
  for n=ND,1,-1 do
    local i,p,a=b+n,SS[n],SA[n]
    local w=OX[i]
    if w then ob(SH[OK[i]],SX[n]+(w+(w>0 and -a or a))*p,SY[n],p*2,w>0,SC[n]) end
    if lv<4 and i==L+10 then arch(n,a) arch(n,SB[n]) end
    if i==(st>0 and 10 or 6) then arch(n,0) end
    if lv>3 and i==L then arch(n,0) end
    for _,c in ipairs(tr) do
      local f=c.z/SL-i
      if f>=0 and f<1 then
        local q=p+(SS[n+1]-p)*f
        ob(SH[c.k],SX[n]+(SX[n+1]-SX[n])*f+(c.x+(c.x<0 and a or SB[n] or a))*q,SY[n]+(SY[n+1]-SY[n])*f,q*2,false,SC[n])
      end
    end
  end
end

local function start()
  gs,sc,tm,cr,v,px,pos,gh,ex,bgx,msg,mt=1,0,62,0,0,0,0,0,1,0,"GO!",30
  fx(72,0,15)
  gen(0)
  for _,c in ipairs(tr) do c.z=-1e6 end
end

function _init()
  hi=tonumber(load(0)) or 0
  for j=1,8 do tr[j]={z=-1e6,v=0} end
  gen(0)
end

function _update()
  fc=fc+1
  mt,ft=mt-1,ft-1
  if gs<1 then
    pos,px=(pos+8)%((L-FZ-60)*SL),0
    bgx=bgx+(C[F(pos/SL)+3] or 0)
    if btnp(4) and fc>15 then start() end
  else
    local pb=F((pos+PZ)/SL)
    local c,w=C[pb] or 0,OX[pb]
    local a,b=off(pb)
    local wx=px*RW
    local d,nc=abs(wx-a),a
    if b and abs(wx-b)<d then d,nc=abs(wx-b),b end
    ofr=d>RW+6
    if gs<2 and cr<1 then
      v=v+(btn(4) and .11*(1-v/V)+.02 or btn(1) and -.3 or -.04)-(ofr and v>5 and .25 or 0)
      px=px+((btn(3) and 1 or 0)-(btn(2) and 1 or 0))*min(1,v/4)*.05
      tm=tm-1/30
      if tm<10 and fc%30<1 then fx(84,0,4) end
      if tm<=0 then tm,gs,msg=0,2,"GAME OVER" fx(36,1,30) end
      sc=sc+F(ofr and v or v*3)
      if w and v>2 and abs(w+(w>0 and -a or a)-wx)<26 then cr=45 fx(24,2,25) end
    else
      v=v-(cr>0 and .4 or .1)
    end
    if cr>0 then cr=cr-1 if cr<1 then px=nc/RW end end
    v=clamp(v,0,V)
    px=clamp(px-c*(v/V)^2*.045,-5,5)
    pos=pos+v
    bgx=bgx+c*v*.12
    for j,t in ipairs(tr) do
      t.z=t.z+t.v
      if t.z<pos-40 or t.z>pos+1800 then
        local z=pos+1200-rnd(100)
        t.z,t.x,t.v,t.k=-1e6,(rnd(3)-1)*33,4+rnd(5),rnd(4)<1 and "T" or "C"
        if j<=2+lv and gs<2 and z<(L-FZ-20)*SL then t.z=z end
      end
      if gs<2 and cr<1 and abs(t.z-pos-PZ)<14 and abs(t.x+(t.x<0 and a or b or a)-wx)<24 then
        v,px,t.z=min(v,t.v*.5),px+(wx>t.x and .3 or -.3),t.z+30
        fx(40,2,8)
      end
    end
    if gs>1 then
    elseif ex<1 and pb>=10 then
      ex,tm,mt,msg=1,tm+52-lv*2,60,"CHECKPOINT"
      fx(76,0,20)
    elseif lv<4 and pb>L-110 and mt<1 then
      msg,mt="<"..nm(st+lv+1).."  "..nm(st+lv+2)..">",9
    end
    if gs<2 and pb>=L then
      if lv<4 then
        local s=wx<0 and -1 or 1
        px,pos,gh,ex,mt=px-s*SP/RW,pos-L*SL,-s,0,60
        gen(st+lv+1+(s+1)/2)
        msg=nm(st)
        for _,t in ipairs(tr) do t.z=-1e6 end
      else
        gs,msg,sc=3,"GOAL "..nm(st),sc+F(tm)*2000
        fx(84,0,30)
      end
      if sc>hi then hi=sc save(0,""..hi) end
    end
    if gs>1 and v<.1 and btnp(4) then gs,pos,mt=0,0,0 gen(0) end
  end
  local q=F(fc*.35)
  if q~=eo and gs<2 then
    eo=q
    local s,n=q%192+1,1
    local ch=MEL:byte(s)
    if s%2>0 then sfx(0,BAS:byte(F(s/8-.1)+1)+(s%4>2 and 12 or 0),4,1,4) end
    if ft<1 and ch>45 then
      while MEL:byte(s+n)==45 do n=n+1 end
      sfx(1,ch,3,1,F(n*2.86)-1)
    end
  end
end

function _draw()
  scene()
  if gs>0 then
    local d=cr>0 and F(cr/3)%3-1 or gs<2 and (btn(2) and -1 or btn(3) and 1 or 0) or 0
    local y=109+(cr>0 and rnd(2) or 0)
    for r=1,17 do
      local s=CAR[r]
      for x=1,32 do
        local ch=s:byte(x<17 and x or 33-x)
        if ch>32 then pset(47+x+d*(r<7 and 2 or r<12 and 1 or 0),y+r,ch>40 and 1 or 0) end
      end
    end
  end
  rectf(0,0,128,9,0)
  print(sc,1,1,1)
  if gs<1 then
    big("SUNSET",29,18,2) big("RUN",47,36,2)
    hint(40,80) print("START",59,80,1)
    print("HI "..hi,55-#(""..hi)*3,90,1)
  else
    print(F(v*24).."KM",98,1,1)
    local t=F(min(tm,99))
    big(""..F(t/10),52,2,2) big(""..t%10,64,2,2)
    if mt>0 or gs>1 then
      rectf(62-#msg*3,31,#msg*6+3,9,0) print(msg,64-#msg*3,32,1)
    end
  end
end
