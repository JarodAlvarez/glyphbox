local s1,s2,tp,ch,x,y,u,v,z,w=0,0,0,1,0,0,0,0,0,0
local cb,tm,ih,st,an,pw=1,0,false,6,0,0
local pd,ac,ad,wx,wy,wd=3.5,0,0,0,0,"--"
local sl,ox,oy,pn,hx,hy=0,0,0,nil,0,0

local C={"DRV",.029,2.6,1,.97,"IRN",.016,3.3,1.5,.91,"WDG",.01,3.9,2,.85,"PTR",.015,0,0,.97}
local TC="G.:SWTH "
local TF={.98,.95,.85,.6,1,1,1,.95}
local BS="20T8.6T12.4T3.3G2.8T3.1G1H1G2.8T3.3G2.8T8.8T8.8T3.1S4.8T8.8T8.8T3.1S4.8T8.8T8.8T3.1 4.36T,20T6.2G8T6.1G1H8T6.2G8T3.1S4.8T8.8T8W8T8W8T8.8T8.8T3.1S4.8T8.8T8.8T3.1 4.36T,20T8.6T12.4T2.8W2.4T2.1W6G1W2.4T2.1W2G1H3G1W2.4T2.1W6G1W2.4T2.8W2.4T12.4T12.4T5.1S6.4T12.4T12.4T6.1 5.34T,20T3.3G2.8T3.1G1H1G2.8T3.3G2.8T8W8T8W8T3.1S4.8T3.1S4.8T8.8T8.8T8W8T8W8T8.8T3.1 4.36T"
local BC,EC,EP,PC,PP,BP,STR,SN={},{},{},{},{},{3,4,3,5},0,{"-2","-1","PAR","+1","+2"}

local mc,ms,ma,ab,ss,sr,sg=math.cos,math.sin,math.atan2,math.abs,string.sub,string.rep,string.gmatch
local ti,tn,fl,mg,rf,re=table.insert,tonumber,flr,mget,rectf,rect
local li,cf,ci,pt,sp,ps=line,circf,circ,print,spr,pset
local fr,rn,ld,sv,bp,bt,cm=frame,rnd,load,save,btnp,btn,clamp

local function r_exp()
  EC,EP={},{}
  for i=1,3 do
    local d=ld(i)
    if d and d~="" then ti(EP,tn(ss(d,1,1))) ti(EC,ss(d,2)) end
  end
end

local function l_hol(idx)
  if idx>#PP then st=7 return end
  local s=""
  for n,c in sg(PC[idx],"(%d+)([^%d])") do s=s..sr(c,tn(n)) end
  for j=0,15 do
    for i=0,15 do
      local c=ss(s,j*16+i+1,j*16+i+1)
      local t=string.find(TC,c,1,true) or 8
      mset(i,j,t-1)
      if t==8 then x,y=i*8,j*8 ox,oy=x,y
      elseif t==7 then hx,hy=i*8+4,j*8+4 end
    end
  end
  s1,ih,st=0,false,0
  wx,wy=(rn(5)-2)*.12,(rn(5)-2)*.12
  sl=(rn(5)-2)*.008
  if wx==0 and wy==0 then wd="--" elseif ab(wx)>ab(wy) then wd=wx>0 and"E"or"W" else wd=wy>0 and"S"or"N" end
end

local function t_pen(r) s1=s1+1; u=0; v=0; z=0; w=0; x=ox; y=oy; pn=r; st=4 end

local function u_flt()
  local px,py=x,y
  x=x+u; y=y+v
  local air=z>0
  local idx=(cb-1)*5

  if air then
    z=z+w; w=w-.22
    u=u+(wx*C[idx+4]*.04); v=v+(wy*C[idx+4]*.04)
  else z,w=0,0 end

  if x<0 or x>127 or y<0 or y>127 then t_pen("OB") return end

  local tx,ty=fl(x/8),fl(y/8)
  local t=mg(tx,ty)

  if air then
    if t==5 and z<12 then x,y,u,v=px,py,-u*.4,-v*.4 end
  else
    if t==4 then t_pen("SPLASH") return
    elseif t==5 then
      if mg(tx-1,ty)==5 and mg(tx+1,ty)==5 and mg(tx,ty-1)==5 and mg(tx,ty+1)==5 then
        t_pen("LOST")
      else
        x,y,u,v=px,py,-u*.6,-v*.6
        if ab(u)<.1 and ab(v)<.1 then
          local nx,ny=tx,ty
          for d=-1,1,2 do
            if mg(tx+d,ty)~=5 then nx=tx+d end
            if mg(tx,ty+d)~=5 then ny=ty+d end
          end
          x,y,u,v=nx*8+4,ny*8+4,0,0
        end
      end
      return
    elseif t==6 then
      local dx,dy=x-hx,y-hy
      if dx*dx+dy*dy<4 then
        if u*u+v*v<.2025 then ih,u,v,st=true,0,0,4 return else x,y,u,v=px,py,-v*.6,u*.6 end
      end
    end
    local tf=TF[t+1] or .95
    u=u*tf*C[idx+5]; v=v*tf*C[idx+5]
  end

  if not air and u*u+v*v<.01 then
    u,v=0,0
    if t==0 or t==6 then
      ox,oy=x,y
      x,y=cm(64+(x-hx)*5,12,116),cm(30+(y-hy)*5,12,116)
      an,st=ma(30-y,64-x),8
    else st=4 end
  end
end

function _init()
  local sc=ld(0)
  if sc then s2=tn(sc)or 0 end
  for c in sg(BS,"[^,]+") do ti(BC,c) end
  r_exp(); STR,st=0,6
end

function _update()
  if st==6 then
    if bp(2) or bp(3) then STR=1-STR end
    if bp(0) then st=11 end
    if bp(4) then
      if not(STR==1 and #EC==0) then
        PC=STR==0 and BC or EC
        PP=STR==0 and BP or EP
        ch=1; l_hol(ch); st=0
      end
    end
  elseif st==0 then
    if bt(2) then an=an-.04 end
    if bt(3) then an=an+.04 end
    if bp(0) then cb=cb-1 end
    if bp(1) then cb=cb+1 end
    cb=(cb-1)%4+1
    if bp(4) then st,pw,pd=1,0,3.5 end
  elseif st==1 or st==2 then
    if st==1 then
      pw=pw+pd
      if pw>100 or pw<0 then pd=-pd end
      if bp(1) then st=0 end
      if bp(4) then st,ac,ad=2,30,-3.5 end
    else
      ac=ac+ad
      if ac<-30 or ac>30 then ad=-ad end
      if bp(1) then st=0 end
      if bp(4) then
        s1=s1+1; ox=x; oy=y; pn=nil
        local i=(cb-1)*5
        local f=pw*C[i+2]
        u,v,w=f*mc(an-(ac/30)*.55),f*ms(an-(ac/30)*.55),(pw/100)*C[i+3]
        z,st,tm=0.1,5,20
        sfx(0,0)
      end
    end
  elseif st==5 then
    tm=tm-1; if tm<=0 then st=3 end
  elseif st==3 then u_flt()
  elseif st==4 then
    if bp(4) then
      if ih then
        s2=s2+s1; tp=tp+PP[ch]
        sv(0,tostring(s2))
        ch=ch+1; l_hol(ch)
      else st=0 end
    end
  elseif st==8 then
    if bt(2) then an=an-.02 end
    if bt(3) then an=an+.02 end
    if bp(4) then st,pw,pd=9,0,2.5 end
  elseif st==9 then
    pw=pw+pd; if pw>100 or pw<0 then pd=-pd end
    if bp(4) then
      s1=s1+1
      local f=(pw/100)*5.5
      u,v,st=f*mc(an),f*ms(an),10
      sfx(0,0)
    end
  elseif st==10 then
    local sq=u*u+v*v
    if sq>.12 then u=u+sl end
    x,y,u,v=x+u,y+v,u*.91,v*.91
    if x<8 or x>120 then u,x=-u*.4,cm(x,8,120) end
    if y<8 or y>120 then v,y=-v*.4,cm(y,8,120) end
    local dx,dy=x-64,y-30
    local dq=dx*dx+dy*dy
    sq=u*u+v*v
    if dq<25 then
      if sq<1.5 then ih,u,v,st=true,0,0,4 return
      elseif sq<4.5 then
        local al=ma(dy,dx)
        x,y=64+mc(al)*7,30+ms(al)*7
        u,v=mc(al)*.12,ms(al)*.12
      end
    end
    if sq<.05 then
      u,v=0,0
      if dq<30.25 then ih,st=true,4 return end
      local mx,my=hx+(x-64)/5,hy+(y-30)/5
      local mt=mg(fl(mx/8),fl(my/8))
      if mt==0 or mt==6 then an,st=ma(30-y,64-x),8 else x,y,st=mx,my,4 end
    end
  elseif st==11 then
    if bp(4) then scan_begin() st=12 end
    if bp(1) then st=6 end
    if bp(2) then sv(1,"") sv(2,"") sv(3,"") r_exp() STR,st=0,6 end
  elseif st==12 then
    local d=scan_poll()
    if d==false then st=6
    elseif type(d)=="table" then
      for i=1,3 do if d[i] and d[i]~="" then sv(i,d[i]) end end
      r_exp() st=6
    end
  elseif st==7 then
    if bp(4) then ch,s2,tp=1,0,0 sv(0,"0") l_hol(1) st=6 end
  end
end

local function pc(t,y) pt(t,64-(#t*3),y,1) end

function _draw()
  cls(0)
  local sd=st
  if sd==6 then
    pc("GLYPH GOLF",38)
    local ts=STR==0 and"BASE"or"EXP"
    if STR==1 and #EC==0 then ts="EMPTY" end
    pc("< "..ts.." >",58)
    if fr()%30<20 then hint(43,78) pt("PLAY",62,78,1) end
    pc("U:EXP",98)
  elseif sd==0 then
    map(0,0,0,0,16,16)
    ps(fl(x),fl(y),1)
    sp(1,fl(x)-4,fl(y)-fl(z)-4)
    rf(0,0,128,10,0)
    pt("H:"..ch.." P:"..PP[ch],2,2,1)
    pt(C[(cb-1)*5+1],54,2,1)
    pt("W:"..wd,88,2,1)
    li(fl(x),fl(y),fl(x+mc(an)*14),fl(y+ms(an)*14),1)
  elseif sd==1 or sd==2 or sd==5 then
    li(0,70,127,70,1)

    local dh,dt,dhz,ht,rx,ry=-1,-1,-1,0,x,y
    local dx,dy=mc(an)*8,ms(an)*8
    for i=1,20 do
      rx=rx+dx; ry=ry+dy
      local tx,ty=fl(rx/8),fl(ry/8)
      if tx<0 or tx>15 or ty<0 or ty>15 then break end
      local t=mg(tx,ty)
      if t==5 and dt==-1 and i<=5 then dt=i*8
      elseif t==6 and dh==-1 then dh=i*8
      elseif(t==3 or t==4)and dhz==-1 then dhz=i*8 ht=t end
    end

    if dhz>0 then
      local sc=cm(30/dhz,.2,2.5)
      local w_h,hy=24*sc,70+15*sc
      if ht==3 then
        re(64-w_h,hy,w_h*2,3*sc,1)
        ps(64-w_h/2,hy+1.5*sc,1)
        ps(64+w_h/2,hy+1.5*sc,1)
      elseif ht==4 then
        li(64-w_h*.8,hy,64+w_h*.8,hy,1)
        li(64-w_h*1.3,hy+3*sc,64+w_h*1.3,hy+3*sc,1)
      end
    end

    if dt>0 then
      local sc=cm(50/dt,1,4)
      rf(64-3*sc,70-16*sc,6*sc,16*sc,0)
      re(64-3*sc,70-16*sc,6*sc,16*sc,1)
      cf(64,70-21*sc,10*sc,0)
      ci(64,70-21*sc,10*sc,1)
    end

    if dh>0 then
      local sc=cm(30/dh,.1,2)
      local fy=70-20*sc
      li(64,70,64,fy,1)
      li(64,fy,64+10*sc,fy+3*sc,1)
      li(64+10*sc,fy+3*sc,64,fy+6*sc,1)
    end

    local g=0
    if sd==1 or sd==2 then g=fl(cm(pw,0,99)/34)
    elseif sd==5 then g=3+fl((20-tm)/7) end

    sp(8+g*2,40,88)
    sp(9+g*2,40,96)

    local anim="\46\98\60\112\36\94\24\80\34\82\46\68\46\98\62\112\54\90\68\76\48\80\34\72"
    local b=g*4+1
    local hx2,hy2,cx,cy=string.byte(anim,b,b+3)
    li(44,92,hx2,hy2,1)
    li(hx2,hy2,cx,cy,1)

    if sd==1 or sd==2 then cf(60,112,1,1)
    elseif sd==5 then
      local n=1.0-(tm/20)
      local bf=60+4*n-ac*n*.5
      if n<.5 then cf(bf,112-42*n,2,1) else ps(fl(bf),fl(112-42*n),1) end
    end

    if sd<5 then
      rf(0,112,128,16,0)
      re(10,115,108,8,1)
      li(64,114,64,124,1)
      if sd==1 then li(10+pw,115,10+pw,123,1)
      elseif sd==2 then rf(10,115,pw,8,1) li(64+ac,114,64+ac,124,1) end
      if fr()%45<35 then pt("D:CANCEL",24,15,1) end
      pt(C[(cb-1)*5+1],10,106,1)
    end
  elseif sd>=8 and sd<=10 then
    re(6,6,122,122,1)
    local tlt=sl*350
    for gy=20,110,18 do li(8,fl(gy-tlt),120,fl(gy+tlt),1) end
    ci(64,30,5,1)
    cf(64,30,4,0)
    li(64,30,64,14,1)
    li(64,14,72,18,1)
    li(72,18,64,22,1)
    cf(fl(x),fl(y),2,1)
    if sd==8 then
      li(fl(x),fl(y),fl(x+mc(an)*26),fl(y+ms(an)*26),1)
      pt("AIM",58,112,1)
    elseif sd==9 then
      rf(20,112,88,8,0) re(20,112,88,8,1) rf(20,112,pw*.88,8,1)
    end
  elseif sd==3 or sd==4 then
    map(0,0,0,0,16,16)
    ps(fl(x),fl(y),1)
    sp(1,fl(x)-4,fl(y)-fl(z)-4)
    if sd==4 then
      rf(20,44,88,38,0)
      re(20,44,88,38,1)
      if ih then
        pt("HOLE!",50,48,1)
        local diff=s1-PP[ch]
        pt(SN[diff+3] or(s1.." STRK"),24,58,1)
      elseif pn then pt(pn.."!",44,52,1)
      else pt("STOPPED",36,52,1) end
      pt("STRK: "..s1,24,68,1)
    end
  elseif sd==11 then
    re(8,24,112,80,1)
    pt("EXP MANAGER",34,30,1)
    hint(14,52) pt("SCAN",33,52,1)
    pt("L:DELETE",14,68,1)
    pt("D:TITLE",14,84,1)
  elseif sd==12 then
    re(10,40,108,48,1)
    pt("SCANNING...",14,54,1)
    if fr()%30<15 then pt(".",94,54,1) end
  elseif sd==7 then
    re(4,4,120,120,1)
    pt("SUMMARY",46,16,1)
    li(12,26,116,26,1)
    pt("PAR: "..tp,16,40,1)
    pt("STROKES: "..s2,16,54,1)
    local d=s2-tp
    pt("SCORE: "..(d>0 and"+"or"")..(d==0 and"0"or d),16,74,1)
    li(12,92,116,92,1)
    hint(34,104) pt("RESTART",53,104,1)
  end
end