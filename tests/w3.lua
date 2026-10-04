local L=dofile("../tests/lib.lua")
local M,F=L.M,L.F
return {
 L.start("Route6",10,9), {"wait",3}, {"hold","up",30}, {"wait",60}, L.pos("gate_fwd"),
 {"hold","down",30}, {"wait",60}, L.pos("gate_back"),
 L.go("CeruleanCity",27,13,{"BADGE2"}), {"wait",3}, {"hold","up",30}, {"wait",60}, L.pos("house_fwd"),
 {"hold","down",20}, {"wait",60}, L.pos("house_back"),
 L.go("CeruleanCity",27,14), {"wait",3}, {"hold","up",30}, {"wait",30}, L.pos("house_blocked"),
 L.go("ViridianPokecenter",3,6), {"wait",10}, {"shot","g4_center"},
 L.go("RedsHouse2F",3,5), {"wait",10}, {"shot","g5_bedroom"},
 L.go("ViridianCity",32,10), {"wait",10}, {"shot","g6_gymdoor"},
 L.go("PalletTown",4,15), {"wait",10}, {"shot","g7_shore"},
 L.go("PalletTown",10,4), {"wait",3},
 {"hold","up",60}, {"until","cm=="..M.PalletTown.." and pl.x==12 and pl.y==12","x",3000}, L.pos("belowdoor"),
 {"until","cm=="..M.OaksLab,"",600}, L.pos("inlab"),
}
