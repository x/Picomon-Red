-- io(1) then io() restores flags, position and the party (species, level, exp, moves); loading heals it
local L=dofile("../tests/lib.lua")
local snap="local t={cm,pl.x,pl.y,rm} for k in pairs(F) do add(t,'f'..k) end for p in all(P) do add(t,p.s..':'..p.l..':'..flr(p.x*256)..':'..p.n) for j=1,4 do add(t,p.mv[j]) end end return table.concat(t,' ')"
return {
 L.start("PalletTown",10,4,{},"mk(4,36),mk(1,12),mk(16,7)"), {"wait",30},
 {"lua","F[3]=true F[200]=true P[1].hp=7 P[1].st='psn' P[2].pp[1]=3 P[3].x+=0.5 S0=(function() "..snap.." end)() io(1)"},
 {"lua","P={} F={} cm=0 pl.x=0 io() S1=(function() "..snap.." end)() local h=P[1].hp==P[1][1] and not P[1].st and P[2].pp[1]>3 printh((S0==S1 and h) and 'SAVE OK' or 'SAVE MISMATCH '..tostring(h)..'\\n'..S0..'\\n'..S1)"},
}
