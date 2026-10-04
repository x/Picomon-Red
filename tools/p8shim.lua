-- minimal pico-8 api for headless testing under luajit
local io, os, string, table, math = io, os, string, table, math
local ffi = require "ffi"
local bit = require "bit"
local M = ffi.new("uint8_t[65536]")
local ROM = ffi.new("uint8_t[17152]")
local CARTDIR = os.getenv("P8_CARTDIR") or "."
local OUTDIR = os.getenv("P8_OUTDIR") or "."
local FRAME = 0

local function readfile(p)
  local f = io.open(p, "rb"); if not f then return nil end
  local s = f:read("*a"); f:close(); return s
end

-- ---------------------------------------------------------------- math
flr = math.floor
function ceil(x) return -flr(-(x or 0)) end
abs = math.abs
function min(a, b) return math.min(a or 0, b or 0) end
function max(a, b) return math.max(a or 0, b or 0) end
function mid(a, b, c) a, b, c = a or 0, b or 0, c or 0
  if a > b then a, b = b, a end
  return math.max(a, math.min(b, c))
end
function sgn(x) return (x or 0) < 0 and -1 or 1 end
function sin(x) return -math.sin((x or 0) * 2 * math.pi) end
function cos(x) return math.cos((x or 0) * 2 * math.pi) end
function sqrt(x) return math.sqrt(x or 0) end
function atan2(dx, dy) return (math.atan2(-dy, dx) / (2 * math.pi)) % 1 end
math.randomseed(tonumber(os.getenv("P8_SEED") or "1"))
function rnd(x)
  if type(x) == "table" then if #x == 0 then return nil end return x[math.random(#x)] end
  return math.random() * (x or 1)
end
function srand(x) math.randomseed(x) end
local function fx(v) return bit.tobit(flr((v or 0) * 65536 + 0.5)) end
local function unfx(v) return v / 65536 end
function p8idiv(a, b) if b == 0 then return 32767 end return flr(a / b) end
function p8band(a, b) return unfx(bit.band(fx(a), fx(b))) end
function p8bor(a, b) return unfx(bit.bor(fx(a), fx(b))) end
function p8bxor(a, b) return unfx(bit.bxor(fx(a), fx(b))) end
function p8shl(a, b) return unfx(bit.lshift(fx(a), b)) end
function p8shr(a, b) return unfx(bit.arshift(fx(a), b)) end
function p8lshr(a, b) return unfx(bit.rshift(fx(a), b)) end
function p8bnot(a) return unfx(bit.bnot(fx(a))) end
band, bor, bxor, shl, shr = p8band, p8bor, p8bxor, p8shl, p8shr

-- ---------------------------------------------------------------- tables / strings
function add(t, v, i) if i then table.insert(t, i, v) else t[#t + 1] = v end return v end
function del(t, v) for i = 1, #t do if t[i] == v then table.remove(t, i) return v end end end
function deli(t, i) return table.remove(t, i or #t) end
function count(t, v) if v == nil then return #t end local n = 0 for i = 1, #t do if t[i] == v then n = n + 1 end end return n end
function all(t)
  if not t then return function() end end
  local i, n = 0, #t
  return function()
    i = i + 1
    while i <= #t and t[i] == nil do i = i + 1 end
    return t[i]
  end
end
function foreach(t, f) for v in all(t) do f(v) end end
unpack = unpack or table.unpack
function sub(s, i, j) return string.sub(tostring(s), i or 1, j or -1) end
function chr(...)
  local a = { ... }
  for k = 1, #a do a[k] = string.char(flr(a[k] or 0) % 256) end
  return table.concat(a)
end
function ord(s, i, n)
  i = i or 1
  if n then return string.byte(s, i, i + n - 1) end
  return string.byte(s, i)
end
function tostr(v, h)
  if type(v) == "number" then
    if h then return string.format("0x%04x.%04x", flr(v) % 65536, flr((v % 1) * 65536)) end
    if v == flr(v) then return string.format("%d", v) end
    return string.format("%.4f", v):gsub("0+$", "")
  end
  return tostring(v)
end
function tonum(s) return tonumber(s) end
function split(s, sep, conv)
  sep = sep or ","
  if conv == nil then conv = true end
  local out = {}
  if type(sep) == "number" then
    for i = 1, #s, sep do out[#out + 1] = s:sub(i, i + sep - 1) end
  else
    local st = 1
    while true do
      local a = (sep == "") and nil or string.find(s, sep, st, true)
      local piece = a and s:sub(st, a - 1) or s:sub(st)
      if conv and piece ~= "" and tonumber(piece) then piece = tonumber(piece) end
      out[#out + 1] = piece
      if not a then break end
      st = a + #sep
    end
  end
  return out
end
function printh(s) io.stdout:write(tostring(s), "\n") io.stdout:flush() end
function stat(n) return 0 end
function t() return FRAME / 60 end
time = t
cocreate, coresume, costatus, yield = coroutine.create, coroutine.resume, coroutine.status, coroutine.yield
function menuitem() end
function extcmd() end
function flip() end
function sfx(n) if os.getenv("P8_SFXLOG") then printh("sfx " .. tostring(n)) end end
function music(n) if os.getenv("P8_SFXLOG") then printh("music " .. tostring(n)) end end

-- ---------------------------------------------------------------- memory
function peek(a, n)
  a = flr(a)
  if n then
    local r = {}
    for i = 0, n - 1 do r[i + 1] = M[(a + i) % 65536] end
    return unpack(r)
  end
  return M[a % 65536]
end
function peek2(a) local v = M[a % 65536] + M[(a + 1) % 65536] * 256 if v >= 32768 then v = v - 65536 end return v end
function peek4(a) return (M[a % 65536] + M[(a + 1) % 65536] * 256) / 65536 + M[(a + 2) % 65536] + M[(a + 3) % 65536] * 256 end
local CARTDATA
function poke(a, ...)
  a = flr(a)
  local args = { ... }
  for i = 1, select("#", ...) do
    M[(a + i - 1) % 65536] = flr(args[i] or 0) % 256
  end
end
function poke2(a, v) v = flr(v) poke(a, v % 256, flr(v / 256) % 256) end
function poke4(a, v) local i = fx(v) poke(a, bit.band(i, 255), bit.band(bit.rshift(i, 8), 255), bit.band(bit.rshift(i, 16), 255), bit.band(bit.rshift(i, 24), 255)) end
function memcpy(d, s, n) local tmp = {} for i = 0, n - 1 do tmp[i] = M[(s + i) % 65536] end for i = 0, n - 1 do M[(d + i) % 65536] = tmp[i] end end
function memset(d, v, n) for i = 0, n - 1 do M[(d + i) % 65536] = v end end
local BINS = {}
function reload(d, s, n, f)
  d, s, n = d or 0, s or 0, n or 0x4300
  if f then
    local b = BINS[f]
    if not b then b = readfile(CARTDIR .. "/" .. f .. ".bin") BINS[f] = b end
    assert(b, "missing cart " .. f)
    for i = 0, n - 1 do M[(d + i) % 65536] = b:byte(s + i + 1) or 0 end
  else
    for i = 0, n - 1 do M[(d + i) % 65536] = ROM[s + i] end
  end
  return n
end
function cstore() end
function cartdata(id)
  CARTDATA = OUTDIR .. "/cartdata.bin"
  local b = readfile(CARTDATA)
  if b then for i = 0, 255 do M[0x5e00 + i] = b:byte(i + 1) or 0 end end
end
function savecart()
  if not CARTDATA then return end
  local f = io.open(CARTDATA, "wb")
  local t = {} for i = 0, 255 do t[i + 1] = string.char(M[0x5e00 + i]) end
  f:write(table.concat(t)) f:close()
end
function loadrom(path)
  local b = readfile(path)
  for i = 0, 0x42ff do ROM[i] = b:byte(i + 1) or 0 end
  for i = 0, 0x42ff do M[i] = ROM[i] end
end

-- ---------------------------------------------------------------- graphics
local DP, SPAL, PT = {}, {}, {}
local camx, camy, FP, FPT = 0, 0, 0, false
local function resetpal()
  for i = 0, 15 do DP[i] = i SPAL[i] = i PT[i] = (i == 0) end
end
resetpal()
function pal(a, b, p)
  if a == nil then resetpal() return end
  if type(a) == "table" then
    for k, v in pairs(a) do pal(k, v, b) end
    return
  end
  if p == 1 then SPAL[flr(a) % 16] = flr(b) else DP[flr(a) % 16] = flr(b) % 16 end
end
function palt(c, t)
  if c == nil then for i = 0, 15 do PT[i] = (i == 0) end return end
  PT[flr(c) % 16] = t and true or false
end
function camera(x, y) camx, camy = flr(x or 0), flr(y or 0) end
function clip() end
function fillp(p)
  p = p or 0
  FPT = (p % 1) >= 0.5 - 1e-6 and (p % 1) > 0
  FP = flr(p) % 65536
end
local function rawset_px(x, y, c)
  if x < 0 or y < 0 or x > 127 or y > 127 then return end
  local a = 0x6000 + y * 64 + flr(x / 2)
  if x % 2 == 0 then M[a] = bit.bor(bit.band(M[a], 0xf0), c) else M[a] = bit.bor(bit.band(M[a], 0x0f), c * 16) end
end
local function px(x, y, c)
  x, y = flr(x - camx), flr(y - camy)
  if FP ~= 0 then
    local b = bit.band(bit.rshift(FP, 15 - ((y % 4) * 4 + (x % 4))), 1)
    if b == 1 then if FPT then return end end
  end
  rawset_px(x, y, DP[flr(c) % 16])
end
function pset(x, y, c) px(x, y, c or 6) end
function pget(x, y)
  if x < 0 or y < 0 or x > 127 or y > 127 then return 0 end
  local v = M[0x6000 + y * 64 + flr(x / 2)]
  return x % 2 == 0 and v % 16 or flr(v / 16)
end
function cls(c) local v = (flr(c or 0) % 16) * 17 for i = 0x6000, 0x7fff do M[i] = v end camx, camy = 0, 0 end
function rectfill(x0, y0, x1, y1, c)
  if x0 > x1 then x0, x1 = x1, x0 end
  if y0 > y1 then y0, y1 = y1, y0 end
  for y = flr(y0), flr(y1) do for x = flr(x0), flr(x1) do px(x, y, c) end end
end
function rect(x0, y0, x1, y1, c)
  if x0 > x1 then x0, x1 = x1, x0 end
  if y0 > y1 then y0, y1 = y1, y0 end
  for x = x0, x1 do px(x, y0, c) px(x, y1, c) end
  for y = y0, y1 do px(x0, y, c) px(x1, y, c) end
end
local LX, LY = 0, 0
function line(x0, y0, x1, y1, c)
  if x1 == nil then x0, y0, x1, y1, c = LX, LY, x0, y0, y1 end  -- line(x1, y1): continue from the last end point
  LX, LY = x1, y1
  c = c or DCOL DCOL = c  -- a colour argument becomes the current draw colour
  local n = math.max(abs(x1 - x0), abs(y1 - y0))
  for i = 0, n do local t = n == 0 and 0 or i / n px(x0 + (x1 - x0) * t + .5, y0 + (y1 - y0) * t + .5, c) end
end
function circfill(x, y, r, c) for dy = -r, r do for dx = -r, r do if dx * dx + dy * dy <= r * r + r then px(x + dx, y + dy, c) end end end end
function sget(x, y)
  if x < 0 or y < 0 or x > 127 or y > 127 then return 0 end
  local base = M[0x5f54] >= 0x80 and M[0x5f54] * 256 or 0  -- sprite sheet remapped to upper memory
  local v = M[base + y * 64 + flr(x / 2)]
  return x % 2 == 0 and v % 16 or flr(v / 16)
end
function sset(x, y, c)
  local a = y * 64 + flr(x / 2)
  if x % 2 == 0 then M[a] = bit.bor(bit.band(M[a], 0xf0), c) else M[a] = bit.bor(bit.band(M[a], 0x0f), c * 16) end
end
function sspr(sx, sy, sw, sh, dx, dy, dw, dh, fx_, fy_)
  dw, dh = dw or sw, dh or sh
  sx, sy, dx, dy = flr(sx), flr(sy), flr(dx), flr(dy)
  for y = 0, dh - 1 do
    for x = 0, dw - 1 do
      local u = flr(x * sw / dw)
      local v = flr(y * sh / dh)
      if fx_ then u = sw - 1 - u end
      if fy_ then v = sh - 1 - v end
      local c = sget(sx + u, sy + v)
      if not PT[c] then px(dx + x, dy + y, c) end
    end
  end
end
function spr(n, x, y, w, h, fx_, fy_)
  w, h = w or 1, h or 1
  sspr((n % 16) * 8, flr(n / 16) * 8, w * 8, h * 8, x, y, w * 8, h * 8, fx_, fy_)
end
function fget(n, f)
  local v = M[0x3000 + flr(n) % 256]
  if f then return bit.band(v, bit.lshift(1, f)) ~= 0 end
  return v
end
function fset(n, f, v) if v == nil then M[0x3000 + n] = f else local m = bit.lshift(1, f) M[0x3000 + n] = v and bit.bor(M[0x3000 + n], m) or bit.band(M[0x3000 + n], bit.bnot(m)) end end
local function mapinfo()
  local a = M[0x5f56]
  local w = M[0x5f57]
  if w == 0 then w = 256 end
  if a == 0 then a = 0x20 end
  return a * 256, w
end
function mget(x, y)
  local base, w = mapinfo()
  x, y = flr(x), flr(y)
  if x < 0 or y < 0 or x >= w then return 0 end
  local a = base + y * w + x
  if a > 0xffff then return 0 end
  return M[a]
end
function mset(x, y, v)
  local base, w = mapinfo()
  x, y = flr(x), flr(y)
  if x < 0 or y < 0 or x >= w then return end
  local a = base + y * w + x
  if a <= 0xffff then M[a] = flr(v) % 256 end
end
function map(cx, cy, sx, sy, w, h)
  cx, cy, sx, sy, w, h = flr(cx or 0), flr(cy or 0), flr(sx or 0), flr(sy or 0), w or 128, h or 32
  for j = 0, h - 1 do
    for i = 0, w - 1 do
      local t = mget(cx + i, cy + j)
      if t ~= 0 or bit.band(M[0x5f36], 8) ~= 0 then spr(t, sx + i * 8, sy + j * 8) end
    end
  end
end
-- pico-8 default font, captured from the real binary (rows of bits, lsb = left)
DEFFONT = {[16]={7,7,7,7,7,0},[17]={0,7,7,7,0,0},[18]={0,7,5,7,0,0},[19]={0,5,2,5,0,0},[20]={0,5,0,5,0,0},[21]={0,5,5,5,0,0},[22]={4,6,7,6,4,0},[23]={1,3,7,3,1,0},[24]={7,1,1,1,0,0},[25]={0,4,4,4,7,0},[26]={5,7,2,7,2,0},[27]={0,0,2,0,0,0},[28]={0,0,0,1,2,0},[29]={0,0,0,3,3,0},[30]={5,5,0,0,0,0},[31]={2,5,2,0,0,0},[32]={0,0,0,0,0,0},[33]={2,2,2,0,2,0},[34]={5,5,0,0,0,0},[35]={5,7,5,7,5,0},[36]={7,3,6,7,2,0},[37]={5,4,2,1,5,0},[38]={3,3,6,5,7,0},[39]={2,1,0,0,0,0},[40]={2,1,1,1,2,0},[41]={2,4,4,4,2,0},[42]={5,2,7,2,5,0},[43]={0,2,7,2,0,0},[44]={0,0,0,2,1,0},[45]={0,0,7,0,0,0},[46]={0,0,0,0,2,0},[47]={4,2,2,2,1,0},[48]={7,5,5,5,7,0},[49]={3,2,2,2,7,0},[50]={7,4,7,1,7,0},[51]={7,4,6,4,7,0},[52]={5,5,7,4,4,0},[53]={7,1,7,4,7,0},[54]={1,1,7,5,7,0},[55]={7,4,4,4,4,0},[56]={7,5,7,5,7,0},[57]={7,5,7,4,4,0},[58]={0,2,0,2,0,0},[59]={0,2,0,2,1,0},[60]={4,2,1,2,4,0},[61]={0,7,0,7,0,0},[62]={1,2,4,2,1,0},[63]={7,4,6,0,2,0},[64]={2,5,5,1,6,0},[65]={0,6,5,7,5,0},[66]={0,3,3,5,7,0},[67]={0,6,1,1,6,0},[68]={0,3,5,5,3,0},[69]={0,7,3,1,6,0},[70]={0,7,3,1,1,0},[71]={0,6,1,5,7,0},[72]={0,5,5,7,5,0},[73]={0,7,2,2,7,0},[74]={0,7,2,2,3,0},[75]={0,5,3,5,5,0},[76]={0,1,1,1,6,0},[77]={0,7,7,5,5,0},[78]={0,3,5,5,5,0},[79]={0,6,5,5,3,0},[80]={0,6,5,7,1,0},[81]={0,2,5,3,6,0},[82]={0,3,5,3,5,0},[83]={0,6,1,4,3,0},[84]={0,7,2,2,2,0},[85]={0,5,5,5,6,0},[86]={0,5,5,7,2,0},[87]={0,5,5,7,7,0},[88]={0,5,2,2,5,0},[89]={0,5,7,4,3,0},[90]={0,7,4,1,7,0},[91]={3,1,1,1,3,0},[92]={1,2,2,2,4,0},[93]={6,4,4,4,6,0},[94]={2,5,0,0,0,0},[95]={0,0,0,0,7,0},[96]={2,4,0,0,0,0},[97]={7,5,7,5,5,0},[98]={7,5,3,5,7,0},[99]={6,1,1,1,6,0},[100]={3,5,5,5,7,0},[101]={7,1,3,1,7,0},[102]={7,1,3,1,1,0},[103]={6,1,1,5,7,0},[104]={5,5,7,5,5,0},[105]={7,2,2,2,7,0},[106]={7,2,2,2,3,0},[107]={5,5,3,5,5,0},[108]={1,1,1,1,7,0},[109]={7,7,5,5,5,0},[110]={3,5,5,5,5,0},[111]={6,5,5,5,3,0},[112]={7,5,7,1,1,0},[113]={2,5,5,3,6,0},[114]={7,5,3,5,5,0},[115]={6,1,7,4,3,0},[116]={7,2,2,2,2,0},[117]={5,5,5,5,6,0},[118]={5,5,5,7,2,0},[119]={5,5,5,7,7,0},[120]={5,5,2,5,5,0},[121]={5,5,7,4,7,0},[122]={7,4,2,1,7,0},[123]={6,2,3,2,6,0},[124]={2,2,2,2,2,0},[125]={3,2,6,2,3,0},[126]={0,4,7,1,0,0},[127]={0,2,5,2,0,0},[128]={127,127,127,127,127,0},[129]={85,42,85,42,85,0},[130]={65,127,93,93,62,0},[131]={62,99,99,119,62,0},[132]={17,68,17,68,17,0},[133]={4,60,28,30,16,0},[134]={28,46,62,62,28,0},[135]={54,62,62,28,8,0},[136]={28,54,119,54,28,0},[137]={28,28,62,28,20,0},[138]={28,62,127,42,58,0},[139]={62,103,99,103,62,0},[140]={127,93,127,65,127,0},[141]={56,8,8,14,14,0},[142]={62,99,107,99,62,0},[143]={8,28,62,28,8,0},[144]={0,0,85,0,0,0},[145]={62,115,99,115,62,0},[146]={8,28,127,62,34,0},[147]={62,28,8,28,62,0},[148]={62,119,99,99,62,0},[149]={0,5,82,32,0,0},[150]={0,17,42,68,0,0},[151]={62,107,119,107,62,0},[152]={127,0,127,0,127,0},[153]={85,85,85,85,85,0},[154]={14,4,30,45,38,0},[155]={17,33,33,37,2,0},[156]={12,30,32,32,28,0},[157]={8,30,8,36,26,0},[158]={78,4,62,69,38,0},[159]={34,95,18,18,10,0},[160]={30,8,60,17,6,0},[161]={16,12,2,12,16,0},[162]={34,122,34,34,18,0},[163]={30,32,0,2,60,0},[164]={8,60,16,2,12,0},[165]={2,2,2,34,28,0},[166]={8,62,8,12,8,0},[167]={18,63,18,2,28,0},[168]={60,16,126,4,56,0},[169]={2,7,50,2,50,0},[170]={15,2,14,16,28,0},[171]={62,64,64,32,24,0},[172]={62,16,8,8,16,0},[173]={8,56,4,2,60,0},[174]={50,7,18,120,24,0},[175]={122,66,2,10,114,0},[176]={9,62,75,109,102,0},[177]={26,39,34,115,50,0},[178]={60,74,73,73,70,0},[179]={18,58,18,58,26,0},[180]={35,98,34,34,28,0},[181]={12,0,8,42,77,0},[182]={0,12,18,33,64,0},[183]={125,121,17,61,93,0},[184]={62,60,8,30,46,0},[185]={6,36,126,38,16,0},[186]={36,78,4,70,60,0},[187]={10,60,90,70,48,0},[188]={30,4,30,68,56,0},[189]={20,62,36,8,8,0},[190]={58,86,82,48,8,0},[191]={4,28,4,30,6,0},[192]={8,2,62,32,28,0},[193]={34,34,38,32,24,0},[194]={62,24,36,114,48,0},[195]={4,54,44,38,100,0},[196]={62,24,36,66,48,0},[197]={26,39,34,35,18,0},[198]={14,100,28,40,120,0},[199]={4,2,6,43,25,0},[200]={0,0,14,16,8,0},[201]={0,10,31,18,4,0},[202]={0,4,15,21,13,0},[203]={0,4,12,6,14,0},[204]={62,32,20,4,2,0},[205]={48,8,14,8,8,0},[206]={8,62,34,32,24,0},[207]={62,8,8,8,62,0},[208]={16,126,24,20,18,0},[209]={4,62,36,34,50,0},[210]={8,62,8,62,8,0},[211]={60,36,34,16,8,0},[212]={4,124,18,16,8,0},[213]={62,32,32,32,62,0},[214]={36,126,36,32,16,0},[215]={6,32,38,16,12,0},[216]={62,32,16,24,38,0},[217]={4,62,36,4,56,0},[218]={34,36,32,16,12,0},[219]={62,34,45,48,12,0},[220]={28,8,62,8,4,0},[221]={42,42,32,16,12,0},[222]={28,0,62,8,4,0},[223]={4,4,28,36,4,0},[224]={8,62,8,8,4,0},[225]={0,28,0,0,62,0},[226]={62,32,40,16,44,0},[227]={8,62,48,94,8,0},[228]={32,32,32,16,14,0},[229]={16,36,36,68,66,0},[230]={2,30,2,2,28,0},[231]={62,32,32,16,12,0},[232]={12,18,33,64,0,0},[233]={8,62,8,42,42,0},[234]={62,32,20,8,16,0},[235]={60,0,62,0,30,0},[236]={8,4,36,66,126,0},[237]={64,40,16,104,6,0},[238]={30,4,30,4,60,0},[239]={4,62,36,4,4,0},[240]={28,16,16,16,62,0},[241]={30,16,30,16,30,0},[242]={62,0,62,32,24,0},[243]={36,36,36,32,16,0},[244]={20,20,20,84,50,0},[245]={2,2,34,18,14,0},[246]={62,34,34,34,62,0},[247]={62,34,32,16,12,0},[248]={62,32,60,32,24,0},[249]={6,32,32,16,14,0},[250]={0,21,16,8,6,0},[251]={0,4,30,20,4,0},[252]={0,0,12,8,30,0},[253]={0,28,24,16,28,0},[254]={8,4,99,16,8,0},[255]={8,16,99,4,8,0}}
function color(c) DCOL = c end
function print(s, x, y, c)
  c = c or DCOL
  s = tostring(s)
  x, y = flr(x or 0), flr(y or 0)
  local x0 = x
  local custom = bit.band(M[0x5f58], 0x81) == 0x81
  local h = custom and M[0x5602] or 6
  local skip = 0
  for i = 1, #s do
    local ch = s:byte(i)
    if skip > 0 then skip = skip - 1 ch = 0 end
    if ch == 6 then skip = 1 end
    if ch == 10 then
      x, y = x0, y + h
    elseif ch >= 16 then
      if custom then
        local w = ch < 128 and M[0x5600] or M[0x5601]
        local yo = 0
        if bit.band(M[0x5605], 1) == 1 then
          local nb = M[0x5608 + flr((ch - 16) / 2)]
          if (ch - 16) % 2 == 1 then nb = flr(nb / 16) else nb = nb % 16 end
          local adj = nb % 8
          if adj >= 4 then adj = adj - 8 end
          w = w + adj
          if nb >= 8 then yo = -1 end
        end
        for r = 0, 7 do
          local row = M[0x5600 + ch * 8 + r]
          for b = 0, 7 do
            if bit.band(row, bit.lshift(1, b)) ~= 0 then px(x + b, y + r + yo, c or 6) end
          end
        end
        x = x + w
      else
        local g = DEFFONT[ch]
        for r = 0, 5 do
          for b = 0, 7 do
            if g and bit.band(g[r + 1], bit.lshift(1, b)) ~= 0 then px(x + b, y + r, c or 6) end
          end
        end
        x = x + (ch < 128 and 4 or 8)
      end
    end
  end
  return x
end

-- ---------------------------------------------------------------- input
local BTN, PREV, HELD = {}, {}, {}
function btn(i) return BTN[i] or false end
function btnp(i)
  if i == nil then local v = 0 for k = 0, 5 do if btnp(k) then v = v + 2 ^ k end end return v end
  if BTN[i] and not PREV[i] then return true end
  if BTN[i] and HELD[i] and HELD[i] > 30 and (HELD[i] - 30) % 8 == 0 then return true end
  return false
end

-- ---------------------------------------------------------------- frame driver
local RGB = {
  [0] = {0, 0, 0}, {29, 43, 83}, {126, 37, 83}, {0, 135, 81}, {171, 82, 54}, {95, 87, 79}, {194, 195, 199},
  {255, 241, 232}, {255, 0, 77}, {255, 163, 0}, {255, 236, 39}, {0, 228, 54}, {41, 173, 255}, {131, 118, 156},
  {255, 119, 168}, {255, 204, 170},
}
for i, c in ipairs({{0x29, 0x18, 0x14}, {0x11, 0x1d, 0x35}, {0x42, 0x21, 0x36}, {0x12, 0x53, 0x59}, {0x74, 0x2f, 0x29},
  {0x49, 0x33, 0x3b}, {0xa2, 0x88, 0x79}, {0xf3, 0xef, 0x7d}, {0xbe, 0x12, 0x50}, {0xff, 0x6c, 0x24},
  {0xa8, 0xe7, 0x2e}, {0x00, 0xb5, 0x43}, {0x06, 0x5a, 0xb5}, {0x75, 0x46, 0x65}, {0xff, 0x6e, 0x59}, {0xff, 0x9d, 0x81}}) do RGB[127 + i] = c end
function screenshot(name)
  local f = io.open(OUTDIR .. "/" .. name .. ".ppm", "wb")
  f:write("P6 128 128 255\n")
  local t = {}
  for y = 0, 127 do
    for x = 0, 127 do
      local c = pget(x, y)
      local rgb = RGB[SPAL[c]] or RGB[SPAL[c] % 16]
      t[#t + 1] = string.char(rgb[1], rgb[2], rgb[3])
    end
  end
  f:write(table.concat(t)) f:close()
  printh("shot " .. name .. " frame " .. FRAME)
end

local NAMES = { left = 0, right = 1, up = 2, down = 3, z = 4, x = 5, b = 4, a = 5 }
function frame(btns)
  for i = 0, 5 do PREV[i] = BTN[i] BTN[i] = false end
  for _, b in ipairs(btns or {}) do BTN[NAMES[b] or b] = true end
  for i = 0, 5 do HELD[i] = BTN[i] and (HELD[i] or 0) + 1 or 0 end
  FRAME = FRAME + 1
  if _update60 then _update60() elseif _update then _update() end
  if _draw then _draw() end
end

-- test script commands
function run_script(cmds)
  for _, c in ipairs(cmds) do
    local op = c[1]
    if op == "wait" then for i = 1, c[2] do frame() end
    elseif op == "press" then  -- c[2]: a button name, or a list pressed together
      local bs = type(c[2]) == "table" and c[2] or { c[2] }
      for i = 1, (c[3] or 1) do frame(bs) frame() frame() frame() end
    elseif op == "hold" then for i = 1, c[3] do frame({ c[2] }) end
    elseif op == "shot" then screenshot(c[2])
    elseif op == "lua" then assert(loadstring(c[2]))()
    elseif op == "until" then
      local f = assert(loadstring("return " .. c[2]))
      local n = 0
      while not f() do
        frame(c[3] and { c[3] } or nil)
        if c[3] then frame() end
        n = n + 1
        if n > (c[4] or 20000) then printh("TIMEOUT until " .. c[2]) break end
      end
    end
  end
  savecart()
end
