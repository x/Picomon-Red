-- pkmn red for pico-8, single cart
-- all game data is generated from the pokered disassembly by tools/build.py:
-- the data is two lz77 + adaptive binary rans streams (tools/lzr.py): rom 0..0x4123, then the CS string (15 bits per 2 chars)
R,F,UI,P,so={},{},{},{},0
cartdata"picomon_red"
CS="$DATA"

memcpy(0x8000,0,0x4124)
local d,b,n,ip,bb,bn=0xc124,0,0,0x8000,0,0
for i=1,#CS,2 do
 local v=0
 for c in all{ord(CS,i,2)} do v=v*221+c-(c<34 and 32 or c<92 and 33 or c<127 and 34 or 35) end
 for k=14,0,-1 do b=b*2+(v>>k&1) n+=1 if(n>7) poke(d,b) d+=1 b,n=0,0 end
end
CS=nil
local function bit() if(bn<1) bb,bn=@ip,8 ip+=1
 bn-=1 return bb>>bn&1 end
local function bits(k) local v=0 for i=1,k do v=v*2+bit() end return v end
-- adaptive binary rANS (tools/lzr.py): 12-bit probabilities, state x in [2^14, 2^15)
local M,x={}
local function ab(c)
 local p,b=M[c] or 2048,0
 local q,r=x\4096,x%4096
 if r<p then x=p*q+r M[c]=p+(4096-p)\16 else b=1 x=(4096-p)*q+r-p M[c]=p-p\16 end
 while(x<16384) x=x*2+bit()
 return b
end
-- a number >= 1: unary bit length, then mantissa bits (tree contexts for the top bits)
local function num(c)
 local k,v=0,1
 while(ab(c+k)>0) k+=1
 for i=k-1,0,-1 do v=v*2+ab(v<64 and c+32+k*64+v or c+2048+k*32+i) end
 return v
end
-- decode each stream (gfx, then the rest in parts under 32k: literals, matches, rep matches), then read its resource directory: count, then id/len per entry
for _=1,$NS do
 bn,M=0,{}
 local o,n,lc,s,d={[0]=0},bits(8)+bits(8)*256,bits(8),0,0
 x=bits(16)
 while #o<n do
  if ab(1+s)<1 then
   local v,h=1,o[#o]\(1<<8-lc)
   while(v<256) v=v*2+ab(4096+h*256+v)
   add(o,v-256) s=0
  else
   s=1+ab(4+s)
   local l=num(8192)+2
   if(s<2) d=num(16384)
   for i=1,l do add(o,o[#o-d+1]) end
  end
 end
 local q=3+(o[1]+o[2]*256)*4
 for p=3,q-1,4 do
  local l,s=o[p+2]+o[p+3]*256,""
  for j=q,q+l-1,200 do s..=chr(unpack(o,j,min(j+199,q+l-1))) end
  R[o[p]+o[p+1]*256]=s q+=l
 end
end

-- copy a 2bpp image resource to 4bpp memory: rows of w pixels/2 bytes, stride 64
function ld(r,a,w,o,n)
 local s=R[r] w=(w or 64)/2 o=o or 0
 for i=0,(n or #s\w)-1 do
  for j=0,w-1 do
   local b=ord(s,(o+i)*w+j+1)
   poke(a+i*64+j*2,b&3|b<<2&48,b>>4&3|b>>2&48)
  end
 end
end
-- copy a resource verbatim
function rw(r,a) poke(a,ord(R[r],1,#R[r])) end
poke(0x5f36,8)
bk=7 rw(bk,0x3100) -- music bank: battle + the title theme (8: battle + the city theme)

-- number lists: comma-separated text (see nums() in build.py)
function nums(r) return split(R[r]) end
-- table of records: ';'-separated (id, fields...); names (resource n) go in at [2]
function tab(r,n)
 local t,k,nm={},1,split(R[n],"|",false)
 for s in all(split(R[r],";",false)) do
  local e=split(s)
  add(e,nm[k],2) t[e[1]]=e k+=1
 end
 return t
end
SP,MV,IT,TC,TN,PC=tab(1,16),tab(2,17),tab(3,18),nums(4),split(R[14]),nums(13)
-- battle-in spiral: 8x8 cells clockwise from the corner, inward (legs of 16,15,15,14,14..1,1 cells)
SPI={}
local c=-1
for k=0,30 do for j=1,16-k/2 do c+=split"1,16,-1,-16"[k%4+1] add(SPI,c) end end
DX,DY,BD=split"0,0,-1,1",split"1,-1,0,0",split"3,4,2,1"
SM=split"25,28,33,40,50,66,100,150,200,250,300,350,400"
STS=split"psn,brn,par,slp,frz"

function cp(a,b) pal({[0]=7,a,b,0}) end
-- display palette slots s,s+1 from t[i],t[i+1]
function dp(s,t,i) i=i or 17 pal(s,t[i],1) pal(s+1,t[i+1],1) end
-- front pic of species table t into the sheet at 0,0
function fpic(t) ld(t[15],0,14) dp(3,t) end
function np() pal({[0]=0,1,2,3}) end
function wt(e) L1=nil repeat yield() until e.o<1 end
function wait(n) for i=1,n do yield() end end
function bt() return btnp(4) or btnp(5) end

-- ============================================================ text & menus
function box(x,y,w,h)
 rectfill(x,y,x+w-1,y+h-1,7)
 rect(x+1,y+1,x+w-2,y+h-2,0)
end

function wb()
 arw=1
 repeat yield() until bt()
 arw=nil sfx(57)
end

function say(s)
 for pg in all(split(s,"|",false)) do
  if pg!="" then
   L1,L2="",""
   local L=split(pg,"\n",false) -- lines are broken by hand / by build.py (4px font: they all fit)
   for k,ln in ipairs(L) do
    if(k>2) wb() L1,L2=L2,""
    for i=1,#ln do
     if(k<2) L1=sub(ln,1,i) else L2=sub(ln,1,i)
     if(not btn(5)) yield()
    end
   end
   wb()
  end
 end
end

-- it: labels; c: cursor; f2: extra drawer; sp: row height; cols: columns
function menu(it,x,y,w,c,f2,sp,cols)
 c,sp,cols=c or 1,sp or 12,cols or 1
 local cw=(w-8)\cols
 local f=function()
  box(x,y,w,(#it+cols-1)\cols*sp+8)
  if(f2) f2(c)
  for i,s in ipairs(it) do print(s,x+10+(i-1)%cols*cw,y+(i-1)\cols*sp+5,0) end
  ?">",x+3+(c-1)%cols*cw,y+(c-1)\cols*sp+5,0
 end
 add(UI,f)
 repeat
  yield()
  local b=btnp()
  c+=(b>>1&1)-(b&1)+((b>>3&1)-(b>>2&1))*cols
  c=(c-1)%#it+1
 until bt()
 del(UI,f) sfx(57)
 return btnp(5) and c,c
end

function yn() return menu(split"yes,no",88,48,40)==1 end

-- ============================================================ map
function vis(e) local c=e.cd return c==0 or (c>0)==(F[abs(c)]==true) end
function tfl(x,y) return fget(mget(x+6,y+6)) end
function oob(x,y) return x<0 or y<0 or x>=mw*2 or y>=mh*2 end
function cdir(x,y)
 local d=y<0 and 2 or y>=mh*2 and 1 or x<0 and 3 or 4
 for i=1,#CN-2,3 do if(CN[i]==d) return i end
end

-- the overworld is a grid of 12x12 squares (a block is 2x2 of them), 6 squares of border round the map
function pb(x,y,v)
 if x>=0 and y>=0 and x<mw+6 and y<mh+6 then
  for i=0,3 do mset(x*2+i%2,y*2+i\2,sq(ord(BS,v*4+i+1))) end
 end
end

-- sprite-sheet slot (10 per row) for tileset square q, loaded the first time the map uses it
function sq(q)
 if(not SL[q]) SL[q]=ns ldq(q,ns) ns+=1
 return SL[q]
end
function ldq(q,s) ld(H[3],s\10*768+s%10*6,6,q*12,12) poke(0x3000+s,ord(R[H[4]],q+1)) end
function pm(b,w,h,x0,y0) for i=0,w*h-1 do pb(x0+i%w,y0+i\w,ord(b,i+1)) end end

-- tileset + sprite gfx for the current map
-- squares in the sprite sheet; 12x12 character frames (and the '!') in a second sheet at 0x8000.
-- (the map lives at 0xa000: a sheet remap is ignored if it overlaps the map's memory)
function lgfx()
 memset(0,0,0x2000) memset(0x8000,0,0x2000)
 for q,s in pairs(SL) do ldq(q,s) end
 SB,NF={},{}
 local s=0
 for i,r in ipairs(SR) do
  SB[i],NF[i]=s,#R[r]\36
  for f=0,NF[i]-1 do ld(r,0x8000+s\10*768+s%10*6,6,f*12,12) s+=1 end
 end
 ld(6,0x9b36,6)
 pal(1,H[8],1) pal(2,H[9],1)
end

-- a map's resource: header, connections, warps, objects, triggers, sprites (';'-separated number lists)
function grp(m) local G={} for s in all(split(R[100+m],";",false)) do add(G,split(s)) end return G end

function lmap(m)
 cm=m
 H,CN,WP,O,TR,SR=unpack(grp(m))
 mw,mh,BS,SL,ns=H[1],H[2],R[H[5]],{},0
 if(H[11]>0 and H[11]!=bk) bk=H[11] rw(bk,0x3100) music($AM)
 poke(0x5f56,0xa0) poke(0x5f57,mw*2+12)
 lgfx()
 for i=0,(mw+6)*(mh+6)-1 do pb(i%(mw+6),i\(mw+6),H[7]) end
 for i=1,#CN-2,3 do
  local d,o,h=CN[i],CN[i+2],grp(CN[i+1])[1]
  pm(R[h[6]],h[1],h[2],d<3 and o+3 or d<4 and 3-h[1] or mw+3,d<2 and mh+3 or d<3 and 3-h[2] or o+3)
 end
 pm(R[H[6]],mw,mh,3,3)
 E={}
 for i=1,#O-8,9 do
  local e={o=0,k=0}
  for k,f in ipairs(split"s,x,y,mv,d,sc,cd,sg,tf") do e[f]=O[i+k-1] end
  e.hx,e.hy=e.x,e.y
  add(E,e)
 end
end

function px(e) return e.x*12-DX[e.d]*e.o*.75 end
function py(e) return e.y*12-DY[e.d]*e.o*.75 end
function dirto(a,b) return b.x<a.x and 3 or b.x>a.x and 4 or b.y<a.y and 2 or 1 end

-- a door square leads somewhere (warp or trigger); doors to cut interiors are solid
function dr(x,y)
 for i=1,#WP,5 do if(WP[i]==x and WP[i+1]==y) return 1 end
 for i=1,#TR,4 do if(TR[i]==x and TR[i+1]==y and vis{cd=TR[i+2]}) return 1 end
end

function free(x,y)
 if(oob(x,y) and not cdir(x,y) or tfl(x,y)&1<1 or tfl(x,y)&8>0 and not dr(x,y)) return
 for e in all(E) do if(e.s>0 and vis(e) and e.x==x and e.y==y) return end
 return pl.x!=x or pl.y!=y
end

function step(e,d,ign)
 e.d=d
 local x,y=e.x+DX[d],e.y+DY[d]
 if(ign or free(x,y)) e.x,e.y,e.o=x,y,16 e.k+=1 return true
end

function appr(e)
 while abs(e.y-pl.y)>1 do step(e,e.y<pl.y and 1 or 2,1) wt(e) end
 while abs(e.x-pl.x)+abs(e.y-pl.y)>1 do step(e,e.x<pl.x and 4 or 3,1) wt(e) end
 e.d,pl.d=dirto(e,pl),dirto(pl,e)
end

function emote(e) emo=e sfx(58) wait(40) emo=nil end

function fade(o)
 L1=nil
 for i=1,4 do fd=o>0 and i or 4-i yield() yield() end
end

-- m=0: go back through the door you came in by (shared center/gym rooms)
function warp(m,x,y)
 if m<1 then m,x,y=unpack(lr) else lr={cm,pl.x,pl.y} end
 sfx(59) fade(1)
 lmap(m) pl.x,pl.y,pl.o=x,y,0
 fade(0)
 if(tfl(x,y)&8>0) step(pl,1,1) wt(pl)
 trig(254,0)
end

function trig(x,y)
 for i=1,#TR-3,4 do
  if((TR[i]==x or TR[i]==255) and TR[i+1]==y and vis{cd=TR[i+2]}) runs(TR[i+3]) return 1
 end
end

function arrive()
 pl.j=nil
 if oob(pl.x,pl.y) then
  local i=cdir(pl.x,pl.y)
  local d,o,x,y=CN[i],CN[i+2],pl.x,pl.y
  lmap(CN[i+1])
  pl.x=d<3 and x-o*2 or d<4 and mw*2-1 or 0
  pl.y=d<2 and 0 or d<3 and mh*2-1 or y-o*2
  return
 end
 for i=1,#WP-4,5 do
  if(WP[i]==pl.x and WP[i+1]==pl.y and (tfl(pl.x,pl.y)&4>0 or WP[i+2]==cm)) warp(unpack(WP,i+2,i+4)) return
 end
 if(trig(pl.x,pl.y)) return
 for e in all(E) do
  local dx,dy=pl.x-e.x,pl.y-e.y
  if e.sg>0 and not F[e.tf] and vis(e) and dx*dy==0 and abs(dx+dy)<=e.sg and dirto(e,pl)==e.d then
   busy=1 emote(e) appr(e) runs(e.sc,e) return
  end
 end
 if tfl(pl.x,pl.y)&2>0 and H[10]>0 then
  local w,r,i=nums(H[10]),rnd(256),1
  if rnd(256)<w[1] then
   for c in all(split"51,102,141,166,191,216,229,242,253") do
    if(r<c) break
    i+=1
   end
   battle{mk(w[i*2+1],w[i*2])}
  end
 end
end

function talk()
 local d=pl.d
 for k=1,2 do
  for e in all(E) do
   if vis(e) and e.x==pl.x+DX[d]*k and e.y==pl.y+DY[d]*k then
    if(e.s>0) e.d=dirto(e,pl)
    runs(e.sc,e) return
   end
  end
  if(tfl(pl.x+DX[d],pl.y+DY[d])&128<1) return
 end
end

-- ============================================================ scripts
-- ops: see tools/content.py
-- a trainer object's script field is its party: fight it once (its flag marks a win)
function runs(id,e)
 busy,ab=1
 if(e and e.tf>0) F[e.tf]=F[e.tf] or fight(id) busy=nil return
 local S,pc={},1
 for c in all(split(R[id],";",false)) do add(S,split(c)) end
 while pc<=#S and not ab do
  local a=S[pc]
  local o,x,y,z=unpack(a)
  local e=x==0 and pl or E[x]
  pc+=1
  if o=="t" then say(R[x])
  elseif o=="f" then e.d=y
  elseif o=="m" then for i=1,z do step(e,y,1) wt(e) end
  elseif o=="X" or o=="Y" then
   local k=o=="X" and "x" or "y"
   while e[k]!=y do
    local b={x=e.x,y=e.y}
    step(e,k=="x" and (e.x<y and 4 or 3) or (e.y<y and 1 or 2),1)
    if(z>0) step(pl,dirto(pl,b),1)
    wt(e)
   end
  elseif o=="a" then appr(e)
  elseif o=="s" then F[abs(x)]=x>0 or nil
  elseif o=="j" then if(vis{cd=x}) pc=y
  elseif o=="q" then if(({pl.x,pl.y})[x+1]==y) pc=z
  elseif o=="y" then if(not yn()) pc=x
  elseif o=="b" then fight(x,z)
  elseif o=="p" then addmon(mk(x,y))
  elseif o=="P" then
   if x>0 then
    fz=1 memcpy(0xc000,0x6000,8192)
    fpic(SP[x])
    pic=function() box(36,16,64,64) cp(3,4) sspr(0,0,28,28,40,20,56,56) end
    add(UI,pic)
   else del(UI,pic) fz=nil lgfx() end
  elseif o=="h" then heal()
  elseif o=="L" then for i,p in ipairs(P) do local s=p.s while(SP[s][13]>0) s=SP[s][14]
 P[i]=mk(s,100) end -- the bedroom snes (test shortcut): fully evolved, level 100
  elseif o=="w" then warp(x,y,z)
  elseif o=="e" then emote(e)
  elseif o=="z" then
   if x<2 then
    -- one white dot per pkmn on the healing machine's screen (room pixels 20..28,13..22), then they blink
-- notest{
    local n=0
    local f=function() for i=1,n do local x,y=20+(i-1)%3*3+58-px(pl),(i>3 and 19 or 15)+58-py(pl) rectfill(x,y,x+1,y+1,7) end end
    add(UI,f)
    for i=1,#P do n=i sfx(61) wait(12) end
    sfx(62) for i=1,8 do n=i%2*#P wait(8) end
    del(UI,f) heal() rm,rx,ry=unpack(lr)
-- notest}
-- test: heal() rm,rx,ry=unpack(lr)
   end
   if(x>1) say"you have become the\npokemon champion!|thank you for\nplaying!" repeat yield() until nil
  end
 end
 busy,L1=nil
end

-- ============================================================ items

function heal()
 for p in all(P) do p.hp,p.st=p[1] for i=1,4 do if(p.mv[i]>0) p.pp[i]=MV[p.mv[i]][6] end end
 sfx(62) wait(60)
end

-- items are unlimited; potions upgrade with badges (fields 5/6: shown from / hidden from flag); no balls outside battle
function bagm()
 local ids,it={},{}
 for i=1,#IT do
  local t=IT[i]
  if((bat or t[3]>1) and (t[5]<1 or F[t[5]]) and not (t[6]>0 and F[t[6]])) add(ids,i) add(it,t[2])
 end
 return ids[menu(it,8,0,120) or 0]
end

-- use item i in battle; returns 1 if a turn was used, 2 if caught
function use(i,c)
 local t=IT[i]
 local k=t[3]
 if(k<2) return catch()
 c=c or party()
 if(not c) return
 local p=P[c]
 local nm=p.n
 if k==2 and p.hp>0 and p.hp<p[1] then
  local h=min(p[1]-p.hp,t[4])
  hpto(p,p.hp+h) say(nm.."\nrecovered by "..h.."!")
 elseif k==3 and p.st==STS[t[4]] then
  p.st=nil sfx(62) say(nm.."\nis cured!")
 else say"it won't have any\neffect." return end
 return 1
end

-- ============================================================ pkmn
function xpl(g,n)
 local c=n*n/256*n
 return max(0,({c,0,0,1.2*c-n*n/256*15+(100*n-140)/256,.8*c,1.25*c})[g+1])
end

function stats(p)
 local t=SP[p.s]
 for i=1,5 do p[i]=flr((t[i+4]+8)*p.l/50)+(i<2 and p.l+10 or 5) end
end

function mk(s,l,mv)
 local p,t={s=s,l=l,n=SP[s][2],mv={},pp={}},SP[s]
 if not mv then
  mv={}
  for i=19,#t-1,2 do if(t[i]<=l and count(mv,t[i+1])<1) add(mv,t[i+1]) end
  while(#mv>4) deli(mv,1)
  -- an attacking move in the first slot (there is no move reordering)
  for i=2,#mv do if(MV[mv[1]][3]<1 and MV[mv[i]][3]>0) add(mv,deli(mv,i),1)
  end
 end
 for i=1,4 do p.mv[i]=mv[i] or 0 p.pp[i]=p.mv[i]>0 and MV[p.mv[i]][6] or 0 end
 stats(p)
 p.hp,p.x=p[1],xpl(t[12],l)
 return p
end

-- with a full party, release one to make room (there is no PC)
function addmon(p)
 if #P>5 then
  say("your party is full!|release a pkmn\nto make room for\n"..p.n.."?")
  local c=yn() and party()
  if(not c) say(p.n.." was released.") return
  say("bye bye, "..P[c].n.."!")
  P[c]=p return
 end
 add(P,p)
end

function learn(p,m)
 local nm,mn=p.n,MV[m][2]
 for i=1,4 do
  if(p.mv[i]==m) return
  if(p.mv[i]<1) p.mv[i],p.pp[i]=m,MV[m][6] sfx(63) say(nm.." learned\n"..mn.."!") return
 end
 say(nm.." is\ntrying to learn\n"..mn.."!|but, "..nm.."\ncan't learn more\nthan 4 moves!|delete an older\nmove to make room\nfor "..mn.."?")
 if yn() then
  local it={}
  for i=1,4 do it[i]=MV[p.mv[i]][2] end
  local c=menu(it,24,40,104)
  if(c) say("1, 2 and... poof!|"..nm.." forgot\n"..it[c].."!|and...") p.mv[c],p.pp[c]=m,MV[m][6] sfx(63) say(nm.." learned\n"..mn.."!") return
 end
 say(nm.."\ndid not learn\n"..mn.."!")
end

-- learn level-up moves for p's current level
function lrn(p)
 local t=SP[p.s]
 for i=19,#t-1,2 do if(t[i]==p.l) learn(p,t[i+1]) end
end

function hpto(p,v)
 while p.hp!=v do p.hp+=sgn(v-p.hp) yield() end
end

-- p: the player's side
function hud(m,x,y,p)
 ?m.n,p and 126-print(m.n,0,-9) or x,y,0
 ?"l"..m.l.." "..(m.st or ""),x+(p and 32 or 18),y+8,0
 hpb(m,p and x or x+6,y+16)
 if p then
  ?m.hp.."/"..m[1],x+30,y+23,0
  line(125,y+12,125,y+30,0) line(x+8,y+30)
 else
  line(x-3,y+10,x-3,y+24,0) line(x+66,y+24)
 end
end


function hpb(p,x,y)
 local w=p.hp/p[1]*48
 ?"hp:",x,y-1,0
 rect(x+14,y,x+63,y+4,0)
 if(p.hp>0) rectfill(x+15,y+1,x+14+w,y+3,w>24 and 11 or w>10 and 10 or 8)
end

-- the start menu's pkmn: the party. A on a pkmn: give it an item, or switch its place
function pmenu()
 local c=party()
 while c do
  local k=menu(split"item,switch",72,0,56)
  if k==1 then local i=bagm() if(i) use(i,c)
  elseif k==2 then local d=party(c) if(d) P[c],P[d]=P[d],P[c]
  end
  c=party(c)
 end
end

-- party list; returns index
function party(c)
 L1=nil
 local it={}
 for p in all(P) do add(it,"") end
 return menu(it,0,0,128,c,function()
  rectfill(0,0,127,127,7)
  for i,p in ipairs(P) do
   local y=i*20-14
   ?p.n,10,y,0
   ?"l"..p.l,98,y,0
   ?p.st or "",74,y+8,0
   hpb(p,10,y+8) print(p.hp.."/"..p[1],92,y+8,0)
  end
 end,20)
end

-- ============================================================ battle
function fight(r,lt)
 local t,L=nums(r),{}
 for i=2,#t-5,6 do add(L,mk(t[i+1],t[i],{unpack(t,i+2,i+5)})) end
 return battle(L,t,lt)
end

function sname(s) return (s.e and "enemy " or "")..s.m.n end

function bst(s,i)
 local m=s.m
 local v=m[i]*(SM[s.st[i-1]+7]/100)
 if(i==4 and m.st=="par") v/=4
 if(i==2 and m.st=="brn") v/=2
 return max(1,v)
end

function te(t,m)
 local e,s=1,SP[m.s]
 for i=1,#TC-2,3 do if(TC[i]==t and (TC[i+1]==s[3] or TC[i+1]==s[4])) e*=TC[i+2]/10 end
 return e
end

function hurt(s,x)
 sfx(60)
 for i=1,6 do s.v=i%2<1 wait(3) end
 hpto(s.m,max(0,s.m.hp-flr(x)))
end

SN=split"attack,defense,speed,special,accuracy,evade"
function stage(s,i,v,q)
 local o=s.st[i]
 s.st[i]=mid(-6,o+v,6)
 if s.st[i]==o then if(not q) say"nothing happened!"
 else say(sname(s).."'s\n"..SN[i]..(abs(v)>1 and " greatly" or "")..(v>0 and " rose!" or " fell!")) end
end

function inflict(s,i,f)
 local t=SP[s.m.s]
 if s.m.st or i<2 and (t[3]==3 or t[4]==3) then if(f) say"but it failed!" return end
 s.m.st,s.m.sl=STS[i],rnd(7)\1+1
 say(sname(s)..split("\nwas poisoned!|\nwas burned!|'s\nparalyzed! it may\nnot attack!|\nfell asleep!|\nwas frozen solid!","|")[i])
end

-- side a uses move slot k on side d
function conf(s,f)
 if(s.cf) if(f) say"but it failed!"
 if(not s.cf) s.cf=1 say(sname(s).."\nbecame confused!")
end

function act(a,d,k)
 local nm,m=sname(a),a.m
 local function ns(s) say(nm..s) end
 local M=MV[m.mv[k]]
 if(a.rc) a.rc=nil ns"\nmust recharge!" return
 if m.st=="slp" then
  m.sl-=1
  if(m.sl<1) m.st=nil ns"\nwoke up!" else ns"\nis fast asleep!"
  return
 end
 if m.st=="frz" then
  if(rnd()<.2) m.st=nil ns"\nthawed out!" else ns"\nis frozen solid!" return
 end
 if(a.fl) a.fl=nil ns"\nflinched!" return
 -- confused: a quarter chance each turn to snap out of it, otherwise half the time it hurts itself
 if a.cf then
  a.cf=rnd()<.75 or nil
  if(a.cf and rnd()<.5) ns" is\nconfused!|it hurt itself!" hurt(a,m[1]\8) return
 end
 if(m.st=="par" and rnd()<.25) ns"'s\nfully paralyzed!" return
 m.pp[k]-=1
 ns("\nused "..M[2].."!")
 local dn,_,_,pw,ty,ac,_,kd,p1,p2,ch,ct=sname(d),unpack(M)
 if(kd==2) stage(a,p1,p2) return
 if(kd!=16 and rnd(100)>=ac*(SM[a.st[5]+7]/100)*(SM[7-d.st[6]]/100)) ns"'s\nattack missed!" return
 if(kd==7) d.sd=1 say(dn.."\nwas seeded!") return
 -- side effects: q set = a damaging move's secondary effect, r set = a status move (says if it failed)
 local function fx(q,r)
  if(kd==1) stage(d,p1,p2,q)
  if(kd==3) inflict(d,p1,r)
  if(kd==4) conf(d,r)
  if(kd==5 and q) d.fl=1
 end
 if(pw<1) fx(nil,1) return
 local e=te(ty,d.m)
 if(e==0) say("it doesn't affect\n"..dn.."!") return
 local A,D,c=ct>0 and 5 or 2,ct>0 and 5 or 3,rnd(256)<SP[m.s][8]/2*(kd==10 and 8 or 1)
 hurt(d,max(1,flr((flr(m.l*(c and .8 or .4)+2)*pw/50*((c and m[A] or bst(a,A))/(c and d.m[D] or bst(d,D)))+2)*((ty==SP[m.s][3] or ty==SP[m.s][4]) and 1.5 or 1)*e*((217+rnd(39))/255))))
 if(c) say"critical hit!"
 if(e>1) say"it's super\neffective!"
 if(e<1) say"it's not very\neffective..."
 if(kd==17 and d.m.hp>0) a.rc=1
 if(d.m.hp>0 and rnd(100)<ch) fx(1)
end

function ai()
 local m,ok=B.m,{}
 for i=1,4 do
  if(m.mv[i]>0 and m.pp[i]>0) add(ok,i)
 end
 return rnd(ok) or 1
end

function side(s,m)
 s.m,s.st,s.sd,s.fl,s.cf,s.rc=m,split"0,0,0,0,0,0"
 s.v,s.h=1,1
 local t=SP[m.s]
 if s.e then
  fpic(t)
 else
  ld(t[16],16,8) dp(5,t)
 end
 sfx(61) wait(20)
end

function sendp(c)
 A.v,A.i=nil,c
 say("go! "..P[c].n.."!")
 side(A,P[c])
end

function pmove()
 local it={}
 for i=1,4 do it[i]=A.m.mv[i]>0 and MV[A.m.mv[i]][2] or "-" end
 local c=menu(it,32,88,96,1,function(c)
  local v=A.m.mv[c]
  if v>0 then
   box(0,56,64,32)
   ?"type/\n "..TN[MV[v][4]+1].."\n    "..A.m.pp[c].."/"..MV[v][6],5,61,0
  end
 end,8)
 if(c and A.m.pp[c]<1) say"no pp left for\nthis move!" return
 return c and A.m.mv[c]>0 and c
end

function catch()
 local m=B.m
 local s,r=m.st and (m.st=="slp" and 25 or 12) or 0,rnd(256)\1
 say"red used\nball!"
 if(TT) say"the trainer\nblocked the ball!|don't be a thief!" return 1
 B.v=nil
 if r<s or r-s<=SP[m.s][10] and rnd(256)<=min(255,m[1]*21.25/max(1,m.hp\4)) then
  sfx(63) say"all right!\npkmn caught!"
  addmon(m)
  return 2
 end
 B.v=1 say"darn! the pkmn\nbroke free!"
 return 1
end

-- choose the next pkmn after a faint; nil when the whole party is down
function nextp(c)
 for p in all(P) do
  if p.hp>0 then
   repeat c=party(A.i%#P+1) until c and P[c].hp>0
   sendp(c) return 1
  end
 end
end

function battle(L,T,lt)
 busy,TT=1,T
 music(0)
 local ei,res=1
 for i=0,6 do fd=i%2*4 wait(4) end
 fz=1 memcpy(0xc000,0x6000,8192)
 for i=1,256,4 do sp=i yield() end
 fz,sp,so=nil,nil,72
 bat,A,B=1,{st={}},{e=1,st={}}
 memset(0,0,0x2000)
 dp(5,PC,2)
 if T then ld(T[1],0,14) dp(3,PC,2) B.v=1 else side(B,L[1]) end
 for i=1,24 do so-=3 yield() end
 if T then
  wb() side(B,L[1])
 else say"a wild pkmn\nappeared!" end
 for i,p in ipairs(P) do if(p.hp>0) sendp(i) break end
 while true do
  local k
  ::menu::
  L1=nil
  if not k then
   local c=menu(split"fight,pkmn,item,run",48,88,80,1,nil,16,2)
   if c==1 then k=pmove()
   elseif c==2 then
    local c=party(A.i)
    if(c and c!=A.i and P[c].hp>0) say(A.m.n.."\nenough!|come back!") sendp(c) k=0
   elseif c==3 then
    local i=bagm()
    k=i and use(i)
    if(k==2) res=1 goto done
    k=k and 0
   elseif c==4 then
    if(TT) say"no! there's no\nrunning from a\ntrainer battle!" goto menu
    if(rnd()<.75) sfx(59) say"got away safely!" res=1 goto done
    say"can't escape!" k=0
   end
   if(not k) goto menu
  end
  local ek=ai()
  local qa,qb=k>0 and MV[A.m.mv[k]][7]==15,MV[B.m.mv[ek]][7]==15
  local o={{A,B,k},{B,A,ek}}
  if(k<1 or qb and not qa or qa==qb and bst(B,4)+rnd(.5)>bst(A,4)+rnd(.5)) o={o[2],o[1]}
  for t in all(o) do
   local a,d,s=unpack(t)
   if(s>0 and a.m.hp>0 and d.m.hp>0) act(a,d,s)
  end
  for s in all{A,B} do
   local m=s.m
   local x=max(1,m[1]\16)
   if m.hp>0 then
    if(m.st=="psn" or m.st=="brn") say(sname(s).."'s\nhurt by "..(m.st=="psn" and "poison!" or "the burn!")) hurt(s,x)
    if(s.sd and m.hp>0) say("leech seed saps\n"..sname(s).."!") hurt(s,x)
   end
  end
  if B.m.hp<1 then
   sfx(58) B.v,B.h=nil
   say(sname(B).."\nfainted!")
   local p,g=A.m,flr(SP[B.m.s][11]*B.m.l/7*(T and 2.25 or 1.5))
   if p.hp>0 then
    say(p.n.." gained\n"..g.." exp. points!")
    p.x+=g/256
    while p.l<100 and p.x>=xpl(SP[p.s][12],p.l+1) do
     p.l+=1 p.lu=1
     local o=p[1]
     stats(p) p.hp+=p[1]-o
     sfx(63) say(p.n.." grew\nto level "..p.l.."!")
     lrn(p)
    end
   end
   ei+=1
   if not L[ei] then
    if T then
     ld(T[1],0,14) dp(3,PC,2) B.v=1
    end
    res=1 goto done
   end
   side(B,L[ei])
  end
  if A.m.hp<1 then
   sfx(58) A.v,A.h=nil
   say(sname(A).."\nfainted!")
   if(not nextp()) goto done
  end
 end
 ::done::
 if not res then
  if lt and lt>0 then heal()
  else
   say"red is out of\nuseable pkmn!|red blacked\nout!"
   bat,ab=nil,1 heal() warp(rm,rx,ry)
  end
 end
 for p in all(P) do
  local t=SP[p.s]
  if p.lu and t[13]>0 and p.l>=t[13] then
   B.v,B.h=nil
   side(A,p) A.h=nil
   say("what? "..p.n.."\nis evolving!")
   local o=p.n
   p.s=t[14] p.n=SP[p.s][2] side(A,p) A.h=nil
   local h=p[1]
   stats(p) p.hp+=p[1]-h
   sfx(63) say(o.." evolved\ninto "..p.n.."!")
   lrn(p)
  end
  p.lu=nil
 end
 fade(1) bat=nil lgfx() fade(0) music($AM)
 busy=nil
 return res
end

-- ============================================================ main
-- save (w) or load the game: cartdata 0x5e00 = 1, position, respawn, flags (bits), party (species, level, exp, moves;
-- loading heals it)
function io(w)
 local a=0x5e00
 local function f(v,n)
  local p,g=poke,peek
  if(n) p,g=poke4,peek4
  if(w) p(a,v or 0) else v=g(a)
  a+=n or 1 return v
 end
 if(f(1)<1) return
 lr=lr or {}
 cm,rm,rx,ry,pl.x,pl.y,lr[1],lr[2],lr[3]=f(cm),f(rm),f(rx),f(ry),f(pl.x),f(pl.y),f(lr[1]),f(lr[2]),f(lr[3])
 for i=1,255,8 do
  local b=0
  for j=0,7 do if(F[i+j]) b|=1<<j end
  b=f(b) for j=0,7 do F[i+j]=b>>j&1>0 or nil end
 end
 for i=1,f(#P) do
  local q=P[i] or {mv={}}
  local p=mk(f(q.s),f(q.l),{f(q.mv[1]),f(q.mv[2]),f(q.mv[3]),f(q.mv[4])})
  p.x=f(q.x,4)
  if(not w) P[i]=p
 end
 return 1
end

-- notest{
-- title: the logo, red, and pkmn sliding in beside him to the title theme; then continue or a new game
function intro()
 music($AM) dp(5,PC,2) ld($TP,16,14)
 local i,x,o=0,0,split"$TO" -- pkmn with a front pic (build.py), shown at random
 UI={function()
  ?"\^w\^t\^o0ffpicomon",36,8,8
  ?"red version",42,22,0
  ?"press \151",48,116,0
  cp(3,4) sspr(0,0,28,28,x,44,56,56)
  cp(5,6) sspr(32,0,28,28,14,44,56,56)
 end}
 repeat
  local p=i%300
  if(p<1) fpic(SP[rnd(o)])
  -- slide in from the right, stay, slide off left behind red
  x=p<17 and 126-p*4 or p>284 and 58-(p-284)*8 or 58
  i+=1 yield()
 until bt()
 local k=@0x5e00>0 and menu(split"continue,new game",28,60,72)
 UI={} fade(1)
 if k==1 then io() lmap(cm) else rm,rx,ry=1,5,5 lmap($START) end
 fade(0)
end
-- notest}

function main()
 intro()
 while true do
  yield()
  if pl.o<1 then
   if mvd then mvd=nil arrive()
   elseif btnp(4) then
    local k=menu(split"pkmn,save",80,0,48)
    if(k==1) pmenu()
    if(k==2) io(1) say"red saved\nthe game!"
   elseif btnp(5) then talk()
   else
    for b=0,3 do
     if btn(b) then
      local d=BD[b+1]
      local x,y=pl.x+DX[d],pl.y+DY[d]
      if tfl(x,y)&({16,0,32,64})[d]>0 then
       pl.d,pl.x,pl.y,pl.o,pl.j,mvd=d,x+DX[d],y+DY[d],32,1,1 sfx(61)
      elseif step(pl,d) then mvd=1
      else
       pl.d=d
       for i=1,#WP-4,5 do
        if(WP[i]==pl.x and WP[i+1]==pl.y and oob(x,y)) warp(unpack(WP,i+2,i+4))
       end
      end
      break
     end
    end
   end
  end
 end
end

pl={s=1,x=3,y=6,d=2,o=0,k=0}
co=cocreate(main)

function _update60()
 for e in all(E) do if(e.o>0) e.o-=1 end
 if(pl.o>0) pl.o-=1
 if not busy and E then
  for e in all(E) do
   if e.mv>0 and e.o<1 and vis(e) and rnd(100)<1 then
    local d=rnd{1,2,3,4}
    if(abs(e.x+DX[d]-e.hx)<3 and abs(e.y+DY[d]-e.hy)<3) step(e,d) else e.d=d
   end
  end
 end
 assert(coresume(co))
end

function dspr(e)
 local n=NF[e.s]
 local f,fl=min(e.d,3)-1,e.d>3
 if e.o>8 and n>1 then
  if(e.d<3) f+=3 fl=e.k%2>0 else f=5
 end
 if(n<2) f,fl=0
 local s=SB[e.s]+f
 sspr(s%10*12,s\10*12,12,12,px(e),py(e)-3-(e.j and sin(e.o/64)*-5 or 0),12,12,fl)
end

function _draw()
 cls(7)
 if fz then memcpy(0x6000,0xc000,8192)
 elseif bat then
  if(B.v) cp(3,4) sspr(0,0,28,28,72-so,0,56,56)
  if(A.v) cp(5,6) sspr(32,0,16,16,4+so,40,48,48)
  np()
  if(B.h) hud(B.m,6,2)
  if(A.h) hud(A.m,58,56,1)
 elseif E then
  local ox,oy=px(pl)-58,py(pl)-58
  camera(ox,oy)
  cp(1,2)
  for y=oy\12,oy\12+11 do for x=ox\12,ox\12+11 do local v=mget(x+6,y+6) sspr(v%10*12,v\10*12,12,12,x*12,y*12) end end
  poke(0x5f54,0x80)
  for e in all(E) do if(e.s>0 and vis(e)) dspr(e) end
  dspr(pl)
  if(emo) sspr(108,108,12,12,px(emo),py(emo)-15)
  poke(0x5f54,0)
  camera()
 end
 np()
 for f in all(UI) do f() np() end
 if L1 then
  box(0,88,128,40)
  ?L1,6,96,0
  ?L2,6,112,0
  if(arw) print("\131",118,118,0)
 end
 if sp then
  for j=1,sp do local c=SPI[j] rectfill(c%16*8,c\16*8,c%16*8+7,c\16*8+7,0) end
 end
 if(fd and fd>0) fillp(({0x7bde.8,0xa5a5.8,0x8421.8,0})[fd]) rectfill(0,0,127,127,7) fillp()
end
