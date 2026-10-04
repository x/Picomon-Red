local L=dofile("../tests/lib.lua")
return {
 L.start("Gym1",4,5), {"wait",5}, {"shot","gy1"},
 L.go("Gym2",4,5), {"wait",5}, {"shot","gy2"},
 L.go("Gym3",4,5), {"wait",5}, {"shot","gy3"},
 L.go("Gym4",4,5), {"wait",5}, {"shot","gy4"},
 L.go("Gym5",4,5), {"wait",5}, {"shot","gy5"},
 L.go("Gym6",4,5), {"wait",5}, {"shot","gy6"},
 L.go("Gym7",4,5), {"wait",5}, {"shot","gy7"},
 L.go("Gym8",4,5), {"wait",5}, {"shot","gy8"},
}
