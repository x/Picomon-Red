local L=dofile("../tests/lib.lua")
return {
 L.start("ViridianCity",1,16), {"wait",3}, {"hold","left",40}, {"wait",20}, L.pos("to_route22"), {"shot","r22"},
 L.go("Route22",8,7), {"wait",3}, {"hold","up",30}, {"wait",20}, L.pos("door_nobadge"),
 L.go("Route22",8,7,{"BADGE8"}), {"wait",3}, {"hold","up",30}, {"wait",40}, L.pos("door_badge8"),
}
