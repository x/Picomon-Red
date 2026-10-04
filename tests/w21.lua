local L=dofile("../tests/lib.lua")
return {
 L.start("FuchsiaCity",19,31,{"BADGE6"}), {"wait",3}, {"hold","down",40}, {"wait",40}, L.pos("fuchsia_to_cinnabar"),
 {"hold","right",30}, {"wait",40}, L.pos("east_to_fuchsia"),
 L.go("PalletTown",5,12,{"BADGE6"}), {"wait",3}, {"hold","down",20}, {"wait",40}, L.pos("pallet_to_cinnabar"), {"shot","cin_north"},
 {"hold","up",30}, {"wait",40}, L.pos("north_to_pallet"),
 L.go("PalletTown",5,12), {"wait",3}, {"hold","down",20}, {"wait",30}, L.pos("pallet_no_badge"),
}
