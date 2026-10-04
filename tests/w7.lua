local L=dofile("../tests/lib.lua")
return { L.start("RedsHouse2F",5,5), {"wait",10}, {"shot","b_room"}, {"hold","left",20}, {"shot","b_room2"} }
