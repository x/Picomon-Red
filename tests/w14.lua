local L=dofile("../tests/lib.lua")
local t={
 L.start("RedsHouse2F",3,6,{},"mk(9,5),mk(6,5),mk(3,5)"), {"wait",3}, {"lua","P[1].n='blasty' P[2].n='char' P[3].n='venu'"},
 {"hold","up",3}, {"press","x"}, {"until","not busy","",300},
 L.go("E4_1",4,10,{"BADGE1","BADGE2","BADGE3","BADGE4","BADGE5","BADGE6","BADGE7","BADGE8"}), {"wait",5}, {"shot","e4room"},
 -- before beating Lorelei the door does nothing
 {"lua","pl.x,pl.y,pl.d=4,2,2"}, {"hold","up",30}, {"wait",20}, {"lua","printh('door before win: map '..cm..' at '..pl.x..','..pl.y)"},
}
for i=1,5 do
 t[#t+1]={"until","L2=='pokemon champion!' or not busy","x",3000}
 t[#t+1]={"lua","if L2~='pokemon champion!' then pl.x,pl.y,pl.d=5,3,2 printh('room '..cm) end"}
 t[#t+1]={"until","L2=='pokemon champion!' or bat","x",600}
 t[#t+1]={"until","L2=='pokemon champion!' or not bat","x",60000}
 t[#t+1]={"until","L2=='pokemon champion!' or not busy","x",3000}
 t[#t+1]={"lua","if L2~='pokemon champion!' then pl.x,pl.y,pl.d=4,2,2 end"}
 t[#t+1]={"hold","up",30} t[#t+1]={"wait",40}
end
t[#t+1]={"wait",90} t[#t+1]={"shot","hof"} t[#t+1]={"lua","printh('ENDING '..tostr(L2)..' map '..cm)"}
return t
