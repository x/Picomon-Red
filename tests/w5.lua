local L=dofile("../tests/lib.lua")
local M=L.M
return {
 -- beat brock with a strong team (the win-text crash), switching to the 2nd mon first
 L.start("Gym1",4,2,{},"mk(7,60,split'55,0,0,0'),mk(4,60,split'52,0,0,0')"), {"wait",3}, {"lua","P[1].n='sq' P[2].n='ch'"},
 {"press","x"}, {"until","bat and A.m","x",3000}, {"lua","printh('LEAD '..P[1].s)"},
 {"until","not bat","x",20000}, L.pos("after_brock"), {"lua","printh('BADGE1 '..tostr(F["..L.F.BADGE1.."])..' lead '..P[1].s)"},
 -- pokecenter heal animation
 L.go("ViridianPokecenter",3,3), {"lua","lr={1,5,5}"}, {"wait",3}, {"hold","up",4}, {"wait",4},{"press","x"}, {"wait",40},{"shot","h1_heal"},
 {"until","not busy","x",3000}, L.pos("healed"),
 -- dead door (viridian mart at 29,19): walking up into it must not move us onto it
 L.go("ViridianCity",29,21), {"wait",3}, {"hold","up",40}, {"wait",10}, L.pos("mart_door"),
}
