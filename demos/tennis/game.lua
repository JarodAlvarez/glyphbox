function ep(w)
  if w==1 then sp=sp+1 else sa=sa+1 end
  if (sp>=7 or sa>=7) and abs(sp-sa)>=2 then 
    st=3 sfx(1,100-w*40,20,3,6) 
  else 
    st=2 sfx(1,40,12,2,6) 
  end
end

-- Math pre-calculated to remove local variables entirely
function prj(x,d)
  return 10+d*.22+(x-10)*(1-d*.00402), 112-d*.88, 1-d*.0072
end

function _init()
  st,sp,sa,px,pd,ax,ad,at=-1,0,0,80,10,64,96,96
  bx,bd,bh,vx,vd,vh=80,10,0,0,0,0
  bc,bs,lh,hc,ac=0,2,0,0,0
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
  px,pd = clamp(px,14,113),clamp(pd,2,48)
  
  if st~=1 then
    if btnp(4) then
      if st==3 then _init() return end 
      local sv=(sp+sa+1)%4<2
      if st==2 then
        st,px,ax,pd,ad,at,bx = 0,64,64,10,96,96,(sp+sa)%2==0 and 80 or 48
        if sv then px,bd=bx,10 else ax,bd=bx,96 end
      else
        st,bc,bs,hc,ac,bh,vh = 1,0,2,20,20,0,2.8
        local dir=bx>64 and -1.2 or 1.2
        if sv then bd,vd,vx,lh=pd,2.5,dir,0 else bd,vd,vx,lh=ad,-1.85,dir,1 end
      end
    end
    return
  end
  
  if hc>0 then hc=hc-1 end
  if ac>0 then ac=ac-1 end
  bx,bd,bh,vh = bx+vx, bd+vd, bh+vh, vh-0.22
  
  if bh<=0 then
    bh=0
    if bx<10 or bx>117 or bd<0 or bd>100 then ep(2-(bc==0 and lh or bs)) return end
    
    local sd=bd<62 and 0 or 1
    if sd==bs then bc=bc+1 else bc,bs=1,sd end
    if bc>=2 then ep(sd==0 and 2 or 1) return end
    
    vh=-vh*0.62
    if vh<0.4 then vh=0 end
    sfx(0,18,2,0,3)
  end
  
  if bd>=61 and bd<=64 and bh<5 then ep(vd>0 and 2 or 1) return end
  
  -- Folded hit detection logic
  if bh<14 then
    if hc==0 and bd<62 and abs(bx-px)<16 and abs(bd-pd)<10 then
      vx=(64-px)*0.025
      if btn(2) then vx=vx-1.8 elseif btn(3) then vx=vx+1.8 end
      -- Dialed back player power to keep shots inside the baseline
      if btn(0) then vd,vh = 2.1+abs(vd)*0.2, 1.8
      elseif btn(1) then vd,vh = 1.1+abs(vd)*0.1, 4.2
      else vd,vh = 1.6+abs(vd)*0.3, 2.6 end
      lh,hc,bc = 0,18,0 sfx(0,30,4,1,5)
    -- AI Volley fix: Must bounce (bc>0) UNLESS rushing the net (ad<80)
    elseif ac==0 and bd>62 and abs(bx-ax)<14 and abs(bd-ad)<10 and (bc>0 or ad<80) then
      vx,vd,vh = (28+rnd(72)-bx)*0.05, -(1.5+rnd(12)*0.1), 1.4+rnd(12)*0.1
      lh,ac,bc = 1,18,0 sfx(0,30,4,1,5)
      at=rnd()>.2 and 96 or 65
    end
  end
  
  local ax_tgt, ad_tgt = 64, at
  if vd>0 then 
    ax_tgt=bx+vx*((ad-bd)/vd)
    if bd>45 then ad_tgt=bd+vd*14 end
  end
  
  -- Nested clamping to save bytecode jumps
  ax,ad = clamp(clamp(ax_tgt,14,113), ax-2.4, ax+2.4), clamp(clamp(ad_tgt,65,at), ad-1, ad+1)
end

function _draw()
  cls(0)
  
  if st==-1 then
    print("TIEBREAK 10is", 26, 50, 1)
    print("Gureedo 2026", 26, 110, 1)
    if frame()%60<40 then print("PRESS A", 44, 65, 1) end
    return
  end

  line(10,112,32,24,1) line(117,112,96,24,1) 
  line(10,112,117,112,1) line(32,24,96,24,1) 
  line(64,112,64,24,1) 
  line(17,84,110,84,1) 
  line(28,39,99,39,1)  
  rectf(16,57,96,3,1)
  
  local a_st, asx, asy = ac>0 and 2 or 0, prj(ax, ad)
  spr(a_st, asx-4, asy-16)
  spr(a_st+1, asx-4, asy-8)

  local p_st, psx, psy = hc>0 and 2 or 0, prj(px, pd)
  spr(p_st, psx-4, psy-16)
  spr(p_st+1, psx-4, psy-8)

  local sx, sy, s = prj(bx, bd)
  pset(sx,sy,1) pset(sx+1,sy,1)
  circf(sx,sy-bh*s*1.5, s*2<1 and 1 or s*2, 1)
  
  print(sp.."-"..sa,52,2,1)
  
  if st==0 then
    print((sp+sa+1)%4<2 and "P1 SERVE" or "AI SERVE", 40, 10, 1)
  elseif st>1 then 
    print(st==2 and "POINT!" or (sp>sa and "YOU WIN!" or "AI WINS!"), 40, 10, 1) 
    print("PRESS A", 44, 115, 1)
  end
end