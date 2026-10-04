-- shared helpers for world tests
local M=dofile("../tests/mapids.lua")
local F=dofile("../tests/flags.lua")
local L={M=M,F=F}
function L.pos(t) return {"lua","printh('"..t.." map '..cm..' '..pl.x..','..pl.y..' d'..pl.d..' busy '..tostring(busy)..' party '..#P)"} end
-- start a game at map m (name), position, with flags and party (lua expr)
function L.start(m,x,y,flags,party)
  local f="" for _,k in ipairs(flags or {}) do f=f.."F["..F[k].."]=true " end
  return {"lua","intro=function() rm,rx,ry,PN,RN=1,5,5,'RED','BLUE' "..f.." P={"..(party or "").."} pl.x,pl.y,pl.d="..x..","..y..",2 lmap("..M[m]..") end"}
end
-- teleport mid-test (only while no script is running)
function L.go(m,x,y,flags)
  local f="" for _,k in ipairs(flags or {}) do f=f.."F["..F[k].."]=true " end
  return {"lua","F={} "..f.." pl.x,pl.y,pl.d,pl.o="..x..","..y..",2,0 lmap("..M[m]..")"}
end
function L.walk(d,n) return {"hold",d,17*(n or 1)} end
return L
