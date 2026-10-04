local L=dofile("../tests/lib.lua")
return {
 L.start("PalletTown",5,12,{"BADGE6"}), {"wait",5}, {"shot","s_pallet"},
 L.go("PalletTown",5,12), {"wait",5}, {"shot","s_pallet_nobadge"},
 L.go("FuchsiaCity",19,32,{"BADGE6"}), {"wait",5}, {"shot","s_fuchsia"},
 L.go("CinnabarIsland",11,3,{"BADGE6"}), {"wait",5}, {"shot","s_cin_n"},
 L.go("CinnabarIsland",18,8,{"BADGE6"}), {"wait",5}, {"shot","s_cin_e"},
}
