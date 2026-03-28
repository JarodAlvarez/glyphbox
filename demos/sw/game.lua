-- STAR WARS: ARCADE PORT
-- Phase 34g: Unified Speed & Wave 4 Cap

ss,sh,sc,wv,tl,flsh=0,8,0,1,0,0
start_wv=1
cx,cy,mx,my,gi,gc=64,64,0,0,1,0
st,ls,en,fb,ex={},{},{},{},{}
lx,ly={-64,-64,64,64},{-64,64,64,-64}
dx,dy,dz,pt=0,-20,600,0
tr_z,ex_z,mu_i,mu_t=0,0,1,0

local intro = {
    67,67,67,0,0,0,67,0,0,0,0,0,0,0,
    74,0,0,0,0,0,0,0,72,0,71,0,69,0,
    79,0,0,0,0,0,0,0,74,0,0,0,0,0,0,0,
    72,0,71,0,69,0,79,0,0,0,0,0,0,0,
    74,0,0,0,0,0,0,0,72,0,71,0,72,0,
    69,0,0,0,0,0,0,0
}

function L(a,b,c,d,cl) line(a,b,c,d,cl or 1) end
function add(t,v) t[#t+1]=v end
function rm(t,i) table.remove(t,i) end
function all(t) local i=0 return function() i=i+1 return t[i] end end
function clamp(v, min, max) return v < min and min or (v > max and max or v) end

function n_en(typ,z)
    if typ==1 then 
        add(en,{t=1,x=rnd(300)-150,y=rnd(300)-150,z=z,tx=rnd(160)-80,ty=rnd(160)-80,a=true})
    elseif typ==2 then 
        add(en,{t=2,x=rnd(240)-120,y=40,z=z,ft=rnd(40)+30,a=true})
    elseif typ==3 then 
        add(en,{t=3,x=(rnd(100)>50 and 45 or -45),y=rnd(10)+30,z=z,ft=rnd(40)+30,a=true})
    elseif typ==4 then
        local initial_fire = rnd(30) + math.max(20, 45 - wv * 5)
        add(en,{t=4,x=rnd(200)-100,y=40,z=z,ft=initial_fire,a=true}) 
    elseif typ==5 then
        add(en,{t=5,x=0,y=rnd(40)-20,z=z,a=true})
    end
end

function _init()
    ss,sc,wv,sh,flsh=0,0,1,8,0
    start_wv=1
    st={}
    for i=1,40 do add(st,{x=rnd(300)-150,y=rnd(300)-150,z=rnd(100)+1}) end
end

function init_wv()
    ss,tl,flsh=1,10+wv*2,0
    en,fb,ls,ex,dx,dy,dz,tr_z,ex_z={},{},{},{},0,-20,600,0,0
    mu_i,mu_t=1,0
    for i=1,3 do n_en(1,60+i*30) end
end

function init_trench()
    ss,en,tr_z=3,{},0
    for i=1,4 do n_en(3,100+i*60) end
    if wv >= 2 then
        for i=1,2 do n_en(5,200+i*150) end 
    end
end

function pj(x,y,z) 
    if z<=0 then return -1,-1 end
    return flr(((x-mx)/z)*100+64),flr(((y-my)/z)*100+64)
end

function upd_lasers()
    for i=#ls,1,-1 do
        local l,hit=ls[i],false
        l.z=l.z+15 
        local td=l.z/100
        local hcx,hcy=l.sx+(l.tx-l.sx)*td,l.sy+(l.ty-l.sy)*td

        for e in all(en) do 
            if e.a and e.t ~= 5 and abs(l.z-e.z)<30 then
                local sx,sy=pj(e.x,e.y,e.z)
                if e.t==4 then
                    local _,ty=pj(e.x,-40,e.z)
                    if ty and abs(sx-l.tx)<25 and l.ty<sy and l.ty>ty then
                        e.a,hit,e.ex=false,true,12 
                        sc=sc+200 sfx(1,60,7,2,15) break
                    end
                else
                    local hw = e.t==1 and 10 or 16
                    if abs(sx-l.tx)<hw and abs(sy-l.ty)<hw then
                        e.a,hit,e.ex=false,true,12 
                        sc=sc+(e.t==1 and 100 or 200)
                        sfx(1,e.t==1 and 40 or 60,7,2,15) break
                    end
                end
            end
        end
        
        if ss==3 and ex_z>0 and abs(l.z-ex_z)<25 then
            local px,py=pj(0,40,ex_z)
            if abs(px-l.tx)<15 and abs(py-l.ty)<15 then
                sc,ss,pt,dz=sc+250000,4,0,600 hit=true
                en,fb,ls={},{},{} break
            end
        end

        if not hit then
            for j=#fb,1,-1 do
                local f=fb[j]
                if abs(l.z-f.z)<30 then
                    local p=f.z/f.sz
                    local sx,sy=f.tx+(f.sx-f.tx)*p,f.ty+(f.sy-f.ty)*p
                    if abs(sx-l.tx)<16 and abs(sy-l.ty)<16 then
                        hit,sc=true,sc+33
                        sfx(1,55,6,2,8) rm(fb,j) break
                    end
                end
            end
        end
        if hit or l.z>=100 then rm(ls,i) end
    end
end

function _update()
    if ss==0 then 
        if btnp(2) then start_wv=clamp(start_wv-1, 1, 3) end
        if btnp(3) then start_wv=clamp(start_wv+1, 1, 3) end
        if btnp(4) then wv=start_wv init_wv() end
        return 
    end
    
    if ss==5 then if btnp(4) then _init() end return end
    if flsh>0 then flsh=flsh-1 end

    if ss==1 and wv==1 and mu_i<=#intro then
        if mu_t%3==0 then
            if intro[mu_i]>0 then sfx(0,intro[mu_i],5,1,8) end
            mu_i=mu_i+1
        end
        mu_t=mu_t+1
    end

    if ss==4 then
        pt=pt+1
        if pt==30 then
            for j=1,80 do add(ex,{x=0,y=0,z=600,vx=rnd(16)-8,vy=rnd(16)-8,vz=-rnd(4)-2}) end
            sfx(1,30,7,2,30)
        elseif pt>30 then
            for p in all(ex) do
                p.x,p.y,p.z=p.x+p.vx,p.y+p.vy,p.z+p.vz
                p.vx,p.vy,p.vz=p.vx*0.98,p.vy*0.98,p.vz*0.98 
            end
        end
        if pt>150 then wv=wv+1 if sh<8 then sh=sh+1 end init_wv() end
        return
    end

    -- GLOBAL SCROLL SPEED (Capped at Wave 4)
    local spd = 2 + clamp(wv-1, 0, 3)

    if dz>140 then dz=dz-0.8 end

    if btn(2) then cx=clamp(cx-3,10,118) end if btn(3) then cx=clamp(cx+3,10,118) end
    if btn(0) then cy=clamp(cy-3,10,118) end if btn(1) then cy=clamp(cy+3,10,118) end
    mx,my=(cx-64)*0.4,(cy-64)*0.4

    for s in all(st) do 
        s.z=s.z-spd
        if s.z<=0 then s.x,s.y,s.z=rnd(300)-150+mx,rnd(300)-150+my,100 end
    end

    if gc>0 then gc=gc-1 end
    if btn(4) and gc<=0 then
        add(ls,{sx=64+lx[gi],sy=64+ly[gi],tx=cx,ty=cy,z=1})
        sfx(1,85,5,0,4) gi=gi%4+1 gc=4
    end

    upd_lasers()

    local e_alv=0
    for e in all(en) do
        if e.a or (e.ex and e.ex>0) then
            e_alv=e_alv+1
            
            -- UNIFIED SPEED: All objects sync perfectly with the ground
            e.z=e.z-(e.t==1 and 1.5 or spd) 
            
            if e.z<=0 then 
                e.a,e.ex=false,0 
                if ss==2 and (e.t==4 or (e.t==2 and wv>=3)) then 
                    e.x,e.z,e.a=rnd(200)-100,600,true 
                end 
            end
            
            if e.a then
                if e.t==1 then e.x,e.y=e.x+(e.tx-e.x)*0.02,e.y+(e.ty-e.y)*0.02 end
                local sx,sy=pj(e.x,e.y,e.z)
                
                if e.t==1 then
                    if e.z>60 and e.z<120 and rnd(200)<3 and #fb<4 and sx>0 and sx<128 and sy>0 and sy<128 then
                        add(fb,{sx=sx,sy=sy,tx=cx,ty=cy,z=e.z,sz=e.z}) sfx(1,45,4,1,5)
                    end
                elseif e.t>=2 and e.t<=4 then
                    e.ft=e.ft-1
                    if e.ft<=0 and #fb<4 and e.z>40 and e.z<200 then
                        local fsy = sy
                        if e.t==4 then local _,ty=pj(e.x,-40,e.z) if ty then fsy=ty end end
                        add(fb,{sx=sx,sy=fsy,tx=cx,ty=cy,z=e.z,sz=e.z})
                        sfx(1,45,4,1,5)
                        
                        if e.t==4 then e.ft = rnd(30) + math.max(20, 45 - wv * 5)
                        else e.ft = rnd(40) + 30 end
                    end
                end

                if e.t==4 and e.z>0 and e.z<8 then
                    if abs(e.x-mx)<15 then 
                        sh=sh-1 sfx(1,20,7,2,20) flsh=6 e.a,e.ex=false,12 
                        if sh<0 then ss=5 end
                    end
                elseif e.t==5 and e.z>0 and e.z<8 then
                    if abs(e.y-my)<12 then 
                        sh=sh-1 sfx(1,20,7,2,20) flsh=6 e.a=false 
                        if sh<0 then ss=5 end
                    end
                end
            else
                e.ex=e.ex-1
            end
        else
            if e.t==1 and tl>0 then 
                tl=tl-1
                e.x,e.y,e.z,e.tx,e.ty,e.a=rnd(300)-150,rnd(300)-150,150,rnd(160)-80,rnd(160)-80,true
            elseif e.t==3 and tr_z<500 then
                e.z,e.x,e.ft,e.a=600,(rnd(100)>50 and 45 or -45),rnd(40)+30,true
            elseif e.t==5 and tr_z<450 then
                e.z,e.x,e.y,e.a=600,0,rnd(40)-20,true
            end
        end
    end
    
    if ss==1 and e_alv==0 and tl<=0 then 
        tr_z = 0
        if wv==1 then 
            init_trench()
        elseif wv==2 then
            ss,en=2,{} for i=1,8 do n_en(2,150+i*60) end 
        else
            ss,en=2,{} 
            for i=1,8 do n_en(4,100+i*60) end
            for i=1,3 do n_en(2,150+i*120) end 
        end
    elseif ss==2 then
        if wv==2 and e_alv==0 then
            init_trench()
        elseif wv>=3 then
            tr_z = tr_z + 1
            if tr_z > 500 then init_trench() end
        end
    elseif ss==3 then
        tr_z=tr_z+1
        if tr_z>600 and ex_z<=0 then ex_z=300 end
        if ex_z>0 then 
            ex_z=ex_z-spd -- Sync the exhaust port too!
            if ex_z<=0 then tr_z=0 end 
        end
    end

    for i=#fb,1,-1 do
        local f=fb[i]
        f.z=f.z-(spd+1) -- Fireballs are always slightly faster than scenery
        if f.z<=0 then
            sh=sh-1 sfx(1,20,7,2,20) flsh=6 rm(fb,i) 
            if sh<0 then ss=5 end
        end
    end
end

function _draw()
    cls(0)
    
    if ss==0 then
        print("STAR WARS",40,30,1)
        print("THE ARCADE GAME",20,45,1)
        print("< START WAVE: "..start_wv.." >", 16, 70, 1)
        if frame()%30 < 15 then print("PRESS A",44,90,1) end
        return
    end

    if ss==5 then 
        print("THE FORCE WILL BE",10,50,1) 
        print("WITH YOU, ALWAYS",10,60,1) 
        if frame()%30 < 15 then print("PRESS A",44,80,1) end
        return 
    end

    -- GLOBAL SCROLL SPEED FOR RENDER
    local spd = 2 + clamp(wv-1, 0, 3)

    if ss==1 or ss==4 then
        for s in all(st) do
            local sx,sy=pj(s.x,s.y,s.z)
            if sx>=0 then pset(sx,sy,1) end
        end
    end

    if ss==1 or (ss==4 and pt<30) then 
        local sx,sy=pj(dx,dy,dz)
        if sx>-50 and sx<170 then
            local r=flr(2500/dz) circ(sx,sy,r,1) L(sx-r,sy,sx+r,sy)
            circ(sx-flr(r/2),sy-flr(r/3),flr(r/4),1)
        end
    elseif ss==4 then
        for p in all(ex) do
            local px,py=pj(p.x,p.y,p.z)
            if px>=0 then pset(px,py,flr(frame()%2)+1) end 
        end
    elseif ss==2 then 
        local h_y=64-my L(0,flr(h_y),127,flr(h_y))
    elseif ss==3 then 
        local flx,fby=pj(-40,40,600) local frx,fty=pj(40,-40,600)
        local nlx,nby=pj(-40,40,2) local nrx,nty=pj(40,-40,2)
        
        L(flx,fty,flx,fby) L(frx,fty,frx,fby) L(flx,fby,frx,fby) 
        L(nlx,nty,flx,fty) L(nrx,nty,frx,fty)
        L(nlx,nby,flx,fby) L(nrx,nby,frx,fby) 
        
        -- SYNCHRONIZED TRENCH LINES:
        local pd=(frame() * spd) % 30
        for i=0,20 do
            local z=30+i*30-pd
            if z>0 and z<=600 then 
                local sl,sy=pj(-40,40,z)
                local sr,ty=pj(40,-40,z)
                L(sl,sy,sr,sy) 
                L(sl,sy,sl,ty) L(sr,sy,sr,ty) 
            end
        end

        if ex_z>0 then 
            local px,py=pj(0,40,ex_z)
            if px>=0 then 
                local r=clamp(flr(150/ex_z),2,20)
                rect(px-r,py-r/2,r*2,r,1)
            end
        end
    end

    for e in all(en) do
        local sx,sy=pj(e.x,e.y,e.z)
        if sx>=0 then
            if e.a then
                local w,r=flr(200/e.z),flr(80/e.z)
                if e.t==1 then 
                    circ(sx,sy,r,1) L(sx-r,sy,sx+r,sy)
                    L(sx-w,sy-w,sx-w,sy+w) L(sx+w,sy-w,sx+w,sy+w)
                elseif e.t==2 or e.t==3 then 
                    local tw=flr(w*0.5)
                    L(sx-w,sy,sx+w,sy) L(sx-tw,sy-r,sx+tw,sy-r)
                    L(sx-w,sy,sx-tw,sy-r) L(sx+w,sy,sx+tw,sy-r)
                    L(sx,sy,sx,sy-r) circ(sx,sy-r,flr(tw*0.8),1)
                elseif e.t==4 then
                    local _,ty=pj(e.x,-40,e.z)
                    if ty then
                        local tw=flr(100/e.z)
                        L(sx-tw,sy,sx+tw,sy) L(sx-tw,sy,sx-tw,ty) L(sx+tw,sy,sx+tw,ty)
                        L(sx-tw,ty,sx+tw,ty) L(sx,sy,sx,ty) 
                        local th=flr(40/e.z)
                        rect(sx-tw,ty-th,tw*2,th,1)
                    end
                elseif e.t==5 then
                    local lx, ly = pj(-40, e.y, e.z)
                    local rx, ry = pj(40, e.y, e.z)
                    if ly and ry then
                        local th = clamp(flr(30/e.z), 1, 6)
                        rect(lx, ly-th, rx-lx, th*2, 1)
                        local steps = 6
                        local step_w = (rx-lx)/steps
                        for i=0, steps do L(lx+i*step_w, ly-th, lx+i*step_w, ly+th) end
                    end
                end
            elseif e.ex and e.ex>0 then
                local esy = sy
                if e.t==4 then local _,ty=pj(e.x,-40,e.z) if ty then esy=(sy+ty)/2 end end
                local r=(12-e.ex)*(80/e.z)
                circ(sx,esy,r,1) L(sx-r,esy-r,sx+r,esy+r) L(sx+r,esy-r,sx-r,esy+r)
            end
        end
    end

    for f in all(fb) do
        local p=f.z/f.sz
        local sx,sy=f.tx+(f.sx-f.tx)*p,f.ty+(f.sy-f.ty)*p
        local r = clamp(flr(150/f.z),1,8)
        L(sx-r,sy,sx+r,sy) L(sx,sy-r,sx,sy+r)
        local d = flr(r*0.7)
        L(sx-d,sy-d,sx+d,sy+d) L(sx-d,sy+d,sx+d,sy-d)
    end

    for l in all(ls) do
        local ht,tt=l.z/100,clamp((l.z-25)/100,0,1)
        L(flr(l.sx+(l.tx-l.sx)*tt),flr(l.sy+(l.ty-l.sy)*tt),flr(l.sx+(l.tx-l.sx)*ht),flr(l.sy+(l.ty-l.sy)*ht))
    end

    local g=3+flr((frame()%8)/4)
    rect(cx-g,cy-g,g*2,g*2,1) pset(cx,cy,1) 
    print("SCORE",2,2,1) print(sc,2,10,1)
    print("WAVE "..wv,92,2,1)
    L(44,2,54,10) L(54,10,74,10) L(74,10,84,2)
    print(sh,62,14,1) print("SHIELD",48,22,1)

    if flsh>0 and flsh%2==0 then rectf(0,0,127,127,1) end
end