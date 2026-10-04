local L=dofile("../tests/lib.lua")
return { L.start("Route22",8,7,{"BADGE8"}), {"wait",3}, {"lua","local s='' for v in all(TR) do s=s..v..',' end printh('TR '..s..' WP '..#WP..' tfl85 '..tfl(8,5)..' tfl84 '..tfl(8,4))"} }
