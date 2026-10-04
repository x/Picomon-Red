local L=dofile("../tests/lib.lua")
return {
 L.start("PalletTown",10,6,{"BADGE3"},"mk(7,20),mk(4,20)"), {"wait",3}, {"lua","P[1].n='sq' P[2].n='ch' P[2].hp=3"},
 {"press",{"z","x"}}, {"until","#UI>0","",200},
 {"press","down"},{"press","x"},{"wait",4},{"press","x"},{"wait",4},{"press","x"},
 {"until","P[2].hp==P[2][1]","x",600},{"lua","printh('HP2 '..P[2].hp..'/'..P[2][1])"},
 {"until","#UI>0 and not L1","x",300},{"shot","m4_back"},
 {"press","x"},{"wait",4},{"press","down"},{"press","x"},{"wait",4},{"press","up"},{"press","x"},{"wait",6},
 {"lua","printh('ORDER '..P[1].n..','..P[2].n)"},{"press","z"},{"wait",10},{"lua","printh('UI '..#UI)"},
}
