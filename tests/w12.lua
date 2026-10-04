local L=dofile("../tests/lib.lua")
return {
 L.start("Route10",8,18), {"wait",3}, {"hold","up",30}, {"wait",40}, L.pos("rock_tunnel"), {"shot","rt"},
 L.go("Route5",17,28), {"wait",3}, {"hold","up",30}, {"wait",40}, L.pos("under56"),
 L.go("Route7",5,14), {"wait",3}, {"hold","up",30}, {"wait",40}, L.pos("under78_nobadge"),
 L.go("Route7",5,14,{"BADGE3"}), {"wait",3}, {"hold","up",30}, {"wait",40}, L.pos("under78_badge"), {"shot","r8"},
 L.go("LavenderTown",10,10), {"wait",5}, {"shot","lav"},
}
