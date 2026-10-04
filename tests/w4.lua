local L=dofile("../tests/lib.lua")
return { L.start("PalletTown",10,4), {"wait",10}, {"shot","r_pallet"} }
