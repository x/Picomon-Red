local L=dofile("../tests/lib.lua")
return {
 L.start("ViridianPokecenter",3,3,{},"mk(7,20),mk(4,20)"), {"wait",3}, {"lua","lr={1,5,5} P[1].hp=1"}, {"hold","up",4}, {"wait",4},
 {"press","x"}, {"wait",10},{"lua","printh('busy '..tostr(busy)..' ui '..#UI..' hp '..P[1].hp)"},{"shot","h0"},
 {"wait",20},{"shot","h1_heal"},{"wait",60},{"shot","h2_heal"},
 {"until","not busy","",3000}, {"lua","printh('hp '..P[1].hp..'/'..P[1][1])"},
}
