#!/usr/bin/env python3
"""Run a test script against the REAL pico-8 binary in headless mode (-x).
The test file is expanded with luajit (same format as run.py), then compiled into a
driver appended to the game code. Screenshots are printed with printh and saved as PNGs."""
import os, sys, subprocess, re, json
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
CART = os.path.join(HERE, '..', 'cart')
PICO = '/Applications/PICO-8.app/Contents/MacOS/pico8'
SCR = os.environ.get('P8_SCRATCH', '/private/tmp/claude-501/-Users-devon-src-pico-pokemon/beb79ff6-c266-42ee-8a53-cdd4620c9f3f/scratchpad/real')
os.makedirs(SCR, exist_ok=True)
P8 = [(0, 0, 0), (29, 43, 83), (126, 37, 83), (0, 135, 81), (171, 82, 54), (95, 87, 79), (194, 195, 199),
      (255, 241, 232), (255, 0, 77), (255, 163, 0), (255, 236, 39), (0, 228, 54), (41, 173, 255), (131, 118, 156),
      (255, 119, 168), (255, 204, 170)]
P8X = [(0x29, 0x18, 0x14), (0x11, 0x1d, 0x35), (0x42, 0x21, 0x36), (0x12, 0x53, 0x59), (0x74, 0x2f, 0x29),
       (0x49, 0x33, 0x3b), (0xa2, 0x88, 0x79), (0xf3, 0xef, 0x7d), (0xbe, 0x12, 0x50), (0xff, 0x6c, 0x24),
       (0xa8, 0xe7, 0x2e), (0x00, 0xb5, 0x43), (0x06, 0x5a, 0xb5), (0x75, 0x46, 0x65), (0xff, 0x6e, 0x59),
       (0xff, 0x9d, 0x81)]

DRIVER = r'''
-->8
-- test driver (headless)
_b,_pb={},{}
function _P(t) printh(t.." map "..cm.." "..pl.x..","..pl.y.." busy "..tostr(busy).." party "..#P) end
function btn(i) return _b[i] end
function btnp(i)
 if not i then local v=0 for k=0,5 do if _b[k] and not _pb[k] then v+=1<<k end end return v end
 return _b[i] and not _pb[i]
end
function _fr(k)
 for i=0,5 do _pb[i]=_b[i] _b[i]=k==i end
 _update60() _draw()
end
for c in all(split(_T,";",false)) do
 local o,a,b,n=unpack(split(c))
 if(o=="w") for i=1,a do _fr() end
 if(o=="p") _fr(a) _fr() _fr() _fr()
 if(o=="h") for i=1,b do _fr(a) end
 if(o=="l") _L[a]()
 if o=="u" then
  n=0
  while not _L[a]() and n<20000 do _fr(b) _fr() n+=1 end
  printh('N '..n)
 end
 if o=="s" then
  printh("SHOT "..a)
  local p="" for i=0,15 do p..=@(0x5f10+i).."," end
  printh("PAL "..p)
  for y=0,127 do
   local s=""
   for x=0,63,4 do s..=tostr($(0x6000+y*64+x),1) end
   printh("ROW "..s)
  end
 end
end
printh("DONE")
'''


def expand(test):
    """use luajit to evaluate the test file into a json command list"""
    lua = '''
local cmds=dofile(%r)
local function esc(s) return '"'..s:gsub('\\\\','\\\\\\\\'):gsub('"','\\\\"'):gsub('\\n','\\\\n')..'"' end
local out={}
for _,c in ipairs(cmds) do
  local t={}
  for i,v in ipairs(c) do t[#t+1]=type(v)=="number" and tostring(v) or esc(v) end
  out[#out+1]="["..table.concat(t,",").."]"
end
io.write("["..table.concat(out,",").."]")
''' % os.path.abspath(test)
    r = subprocess.run(['luajit', '-e', lua], capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(test)))
    if r.returncode:
        raise SystemExit(r.stderr)
    return json.loads(r.stdout)


def main():
    cmds = expand(sys.argv[1])
    BTN = {'left': 0, 'right': 1, 'up': 2, 'down': 3, 'z': 4, 'x': 5}
    t, L = [], []
    for c in cmds:
        o = c[0]
        if o == 'lua':
            m = re.match(r"printh\('(\w+) map '", c[1])
            f = 'function() _P"%s" end' % m.group(1) if m else 'function() %s end' % c[1]
            if f not in L:
                L.append(f)
            t.append('l,%d' % (L.index(f) + 1))
        elif o == 'until':
            f = 'function() return %s end' % c[1].replace('~=', '!=')
            if f not in L:
                L.append(f)
            t.append('u,%d,%s' % (L.index(f) + 1, BTN.get(c[2], -1) if len(c) > 2 else -1))
        elif o == 'wait':
            t.append('w,%d' % c[1])
        elif o == 'press':
            t += ['p,%d' % BTN[c[1]]] * (c[2] if len(c) > 2 else 1)
        elif o == 'hold':
            t.append('h,%d,%d' % (BTN[c[1]], c[2]))
        elif o == 'shot':
            t.append('s,' + c[1])
    src = open(os.path.join(CART, os.environ.get('P8_CART', 'pokered_test.p8')), encoding='latin-1').read()
    head, rest = src.split('__lua__\n', 1)
    code, data = rest.split('\n__gfx__', 1)
    code = code.replace('co=cocreate(main)', 'co=cocreate(main)\n_T="' + ';'.join(t) + '"\n_L={' + ',\n'.join(L) + '}')
    out = head + '__lua__\n' + code + DRIVER + '\n__gfx__' + data
    path = os.path.join(CART, '_test.p8')
    open(path, 'w', encoding='latin-1').write(out)
    if os.environ.get('P8_KEEP'):
        return
    p = subprocess.Popen([PICO, '-x', path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=CART,
                         encoding='latin-1')
    lines = []
    for l in p.stdout:
        lines.append(l.rstrip('\n'))
        if l.startswith('DONE') or 'program too large' in l or 'runtime error' in l:
            if 'runtime error' in l:
                for _ in range(4):
                    lines.append(p.stdout.readline().rstrip('\n'))
            break
    p.kill()
    os.remove(path)
    name, pal, rows = None, None, []

    def flush():
        if name and len(rows) == 128:
            im = Image.new('RGB', (128, 128))
            px = im.load()
            for y, rw in enumerate(rows):
                for x in range(128):
                    c = pal[int(rw[x], 16)]
                    px[x, y] = P8X[c - 128] if c >= 128 else P8[c % 16]
            im.resize((256, 256), Image.NEAREST).save(os.path.join(SCR, name + '.png'))
    for l in lines:
        if l.startswith('SHOT '):
            flush()
            name, rows = l[5:].strip(), []
        elif l.startswith('PAL '):
            pal = [int(float(v)) for v in l[4:].strip(',').split(',')]
        elif l.startswith('ROW '):
            hx = ''
            for w in re.findall(r'0x([0-9a-f]{4})\.([0-9a-f]{4})', l):
                v = bytes.fromhex(w[1])[::-1] + bytes.fromhex(w[0])[::-1]  # b0 b1 b2 b3
                hx += ''.join('%x%x' % (b & 15, b >> 4) for b in v)
            rows.append(hx)
        elif l.strip():
            print(l)
    flush()


if __name__ == '__main__':
    main()
