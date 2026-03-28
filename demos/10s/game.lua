function ep(w)
  if w==1 then sp=sp+1 else sa=sa+1 end
  if (sp>=7 or sa>=7) and abs(sp-sa)>=2 then st=3 else st=2 end
end

function prj(x,d)
  local t=d*0.01
  return 10+22*t+(x-10)*(1-0.402*t), 112-88*t, 1-t*0.72
end

function _init()
  st=-1 sp=0 sa=0 px=80 pd=10 ax=64 ad=96 at=96
  bx=80 bd=10 bh=0 vx=0 vd=0 vh=0
  bc=0 bs=2 lh=0 hc=0 ac=0
end

function _update()
  if st==-1 then
    if btnp(4) then st=0 end
    return
  end

  if btn(2) then px=px-2.2 end
  if btn(3) then px=px+2.2 end
  if btn(0) then pd=pd+1.76 end
  if btn(1) then pd=pd-1.76 end
  -- Restricted player's max depth to 48 so they can't stand on the net
  px=clamp(px,14,113) pd=clamp(pd,2,48)
  
  if st~=1 then
    if btnp(4) then
      if st==3 then _init() return end 
      local sv=(sp+sa+1)%4<2
      if st==2 then
        st=0 px=64 ax=64 pd=10 ad=96 at=96
        local side=(sp+sa)%2==0 and 80 or 48
        if sv then px=side bx=side bd=10 else ax=side bx=side bd=96 end
      else
        st=1 bc=0 bs=2 hc=20 ac=20 bh=0 vh=2.8
        local dir=bx>64 and -1.2 or 1.2
        if sv then bd=pd vd=2.5 vx=dir lh=0 else bd=ad vd=-1.85 vx=dir lh=1 end
      end
    end
    return
  end
  
  if hc>0 then hc=hc-1 end
  if ac>0 then ac=ac-1 end
  bx=bx+vx bd=bd+vd bh=bh+vh vh=vh-0.22
  
  if bh<=0 then
    bh=0
    if bx<10 or bx>117 or bd<0 or bd>100 then ep(2-(bc==0 and lh or bs)) return end
    
    local sd=bd<62 and 0 or 1
    if sd==bs then bc=bc+1 else bc=1 bs=sd end
    if bc>=2 then ep(sd==0 and 2 or 1) return end
    
    vh=-vh*0.62
    if vh<0.4 then vh=0 end
    sfx(0,18,2,0,3)
  end
  
  if bd>=61 and bd<=64 and bh<5 then ep(vd>0 and 2 or 1) return end
  
  if hc==0 and bd<62 and bh<14 and abs(bx-px)<16 and abs(bd-pd)<10 then
    vx=(64-px)*0.025
    if btn(2) then vx=vx-1.8 elseif btn(3) then vx=vx+1.8 end
    
    if btn(0) then vd=2.4+abs(vd)*0.2 vh=1.8
    elseif btn(1) then vd=1.2+abs(vd)*0.1 vh=4.2
    else vd=1.9+abs(vd)*0.3 vh=2.6 end
    lh=0 hc=18 bc=0 sfx(0,30,4,1,5)
  end
  
  local ax_tgt, ad_tgt = 64, at
  if vd>0 then 
    ax_tgt=clamp(bx+vx*((ad-bd)/vd),14,113)
    if bd>45 then ad_tgt=clamp(bd+vd*14, 65, at) end
  end
  
  ax=clamp(ax_tgt, ax-2.4, ax+2.4)
  -- Slowed down AI vertical movement from 1.5 to 1
  ad=clamp(ad_tgt, ad-1, ad+1)
  
  if ac==0 and bd>62 and bh<14 and abs(bx-ax)<14 and abs(bd-ad)<10 then
    vx=(28+rnd(72)-bx)*0.05 vd=-(1.5+rnd(12)*0.1) vh=1.4+rnd(12)*0.1
    lh=1 ac=18 bc=0 sfx(0,30,4,1,5)
    at=rnd(10)>8 and 65 or 96
  end
end

function _draw()
  cls(0)
  
  if st==-1 then
    print("TIEBREAK 10is!", 26, 50, 1)
    print("Gureedo 2026", 26, 110, 1)
    if frame()%60<40 then print("PRESS A TO START", 18, 65, 1) end
    return
  end

  line(0,112,26,24,1) line(127,112,102,24,1) 
  line(10,112,32,24,1) line(117,112,96,24,1) 
  line(0,112,127,112,1) line(26,24,102,24,1) 
  line(64,112,64,24,1) 
  line(17,84,110,84,1) 
  line(28,39,99,39,1)  
  rectf(16,57,96,3,1)
  
  local a_st = ac>0 and 2 or 0
  local asx, asy = prj(ax, ad)
  spr(a_st, asx-4, asy-16)
  spr(a_st+1, asx-4, asy-8)

  local p_st = hc>0 and 2 or 0
  local psx, psy = prj(px, pd)
  spr(p_st, psx-4, psy-16)
  spr(p_st+1, psx-4, psy-8)

  local sx, sy, s = prj(bx, bd)
  pset(sx,sy,1) pset(sx+1,sy,1)
  local br=s*2 if br<1 then br=1 end
  circf(sx,sy-bh*s*1.5,br,1)
  
  print(sp.."-"..sa,52,2,1)
  
  if st==0 then
    print((sp+sa+1)%4<2 and "P1 SERVE" or "AI SERVE", 40, 10, 1)
  elseif st==2 then 
    print("POINT!", 50, 10, 1) 
    print("A:NEXT", 44, 115, 1)
  elseif st==3 then
    print(sp>sa and "YOU WIN!" or "AI WINS!", 40, 10, 1) 
    print("A:REMATCH", 36, 115, 1)
  end
end