local L=dofile("../tests/lib.lua")
return { L.start("PalletTown",10,4), {"wait",3},
 {"lua","for s in all{1,4,7,16,19,25} do local p=mk(s,5) local o='' for m in all(p.mv) do if m>0 then o=o..MV[m][2]..',' end end printh('S'..s..' '..o) end"} }
