local L=dofile("../tests/lib.lua")
return {
 L.start("RedsHouse2F",3,6,{},"mk(7,5),mk(4,5),mk(1,5)"), {"wait",3}, {"lua","P[1].n='a' P[2].n='b' P[3].n='c'"},
 {"hold","up",3}, {"press","x"}, {"until","not busy","",300},
 {"lua","for p in all(P) do printh('SNES '..p.n..' species '..p.s..' lv '..p.l..' moves '..MV[p.mv[1]][2]..', '..MV[p.mv[2]][2]) end"},
}
