local L=dofile("../tests/lib.lua")
local M=L.M
return {
 L.start("Route2",3,45), {"wait",3}, {"hold","up",30}, {"wait",40}, L.pos("in_forest"), {"shot","f1"},
 L.go("ViridianForest",2,2), {"wait",3}, {"hold","left",17}, {"hold","up",40}, {"wait",40}, L.pos("out_north"), {"shot","f2"},
 {"hold","down",30}, {"wait",40}, L.pos("back_in"),
}
