local L=dofile("../tests/lib.lua")
return {
 L.start("PalletTown",10,4), {"wait",3},
 {"hold","up",60}, {"until","cm=="..L.M.OaksLab.." and not busy","x",4000}, L.pos("lab"),{"shot","o1_lab"},
 L.walk("down",1),{"wait",4},L.walk("right",1),{"wait",4},{"hold","up",2},{"wait",4},{"press","x"},
 {"until","#UI>0","x",400},{"shot","o2_pick"},{"press","x"},
 {"until","not busy","x",2000}, L.pos("picked"),
 L.walk("left",1),{"wait",4},L.walk("down",2),{"wait",10},
 {"until","bat","x",2000},{"wait",60},{"shot","o3_battle"},{"lua","printh('MUS battle '..stat(54)..' bank '..peek(0x3100)..','..peek(0x3101))"},
 {"until","B.m and B.m.hp<1","x",8000},{"wait",90},{"lua","printh('MUS victory '..stat(54))"},
 {"until","not bat","x",8000},{"until","not busy","x",2000}, L.pos("after"),{"lua","printh('MUS after '..stat(54))"},{"shot","o4_after"},
}
