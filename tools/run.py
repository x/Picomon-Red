#!/usr/bin/env python3
"""Run the built cart headlessly under LuaJIT with tools/p8shim.lua.
usage: run.py TESTFILE.lua   (TESTFILE returns a list of commands, see p8shim.run_script)"""
import json, os, sys, subprocess, glob, re
from PIL import Image
import p8lua

HERE = os.path.dirname(os.path.abspath(__file__))
CART = os.path.join(HERE, '..', 'cart')
SCR = os.environ.get('P8_SCRATCH', '/private/tmp/claude-501/-Users-devon-src-pico-pokemon/beb79ff6-c266-42ee-8a53-cdd4620c9f3f/scratchpad/run')
os.makedirs(SCR, exist_ok=True)


_GLYPHS = sorted(((bytes.fromhex(v), int(k)) for k, v in json.load(open(os.path.join(os.path.dirname(
    os.path.abspath(__file__)), 'p8scii.json'))).items()), key=lambda g: -len(g[0]))


def p8read(path):
    """a .p8 file as pico-8 sees it: utf-8 glyphs back to chars 128..255"""
    b, out, i = open(path, 'rb').read(), [], 0
    while i < len(b):
        if b[i] >= 0x80:
            g = next((c for (q, c) in _GLYPHS if b.startswith(q, i)), None)
            if g is not None:
                out.append(chr(g))
                i += len(next(q for (q, c) in _GLYPHS if c == g))
                continue
        out.append(chr(b[i]))
        i += 1
    return ''.join(out)


def sections(path):
    out, cur = {}, None
    for l in p8read(path).split('\n'):
        if re.match(r'^__\w+__$', l):
            cur = l.strip('_')
            out[cur] = []
        elif cur:
            out[cur].append(l)
    return out


def rom(path):
    s = sections(path)
    d = bytearray(0x4300)
    for y, l in enumerate(s.get('gfx', [])[:128]):
        for x in range(0, min(len(l), 128), 2):
            d[y * 64 + x // 2] = int(l[x], 16) | (int(l[x + 1], 16) << 4)
    for i, l in enumerate(s.get('gff', [])[:2]):
        b = bytes.fromhex(l)
        d[0x3000 + i * 128:0x3000 + i * 128 + len(b)] = b
    for i, l in enumerate(s.get('map', [])[:32]):
        b = bytes.fromhex(l)
        d[0x2000 + i * 128:0x2000 + i * 128 + len(b)] = b
    for i, l in enumerate(s.get('sfx', [])[:64]):
        if len(l) < 168:
            continue
        hdr = bytes.fromhex(l[:8])
        base = 0x3200 + i * 68
        for n in range(32):
            q = l[8 + n * 5:13 + n * 5]
            pitch, w, vol, eff = int(q[0:2], 16), int(q[2], 16), int(q[3], 16), int(q[4], 16)
            v = pitch | ((w & 7) << 6) | (vol << 9) | (eff << 12) | ((w >> 3) << 15)
            d[base + n * 2] = v & 255
            d[base + n * 2 + 1] = v >> 8
        d[base + 64:base + 68] = hdr
    for i, l in enumerate(s.get('music', [])[:64]):
        if not l.strip():
            continue
        f, ch = l.split()
        f = int(f, 16)
        b = bytes.fromhex(ch)
        for k in range(4):
            d[0x3100 + i * 4 + k] = b[k] | (((f >> k) & 1) << 7)
    return bytes(d), '\n'.join(s.get('lua', []))


def main():
    test = sys.argv[1]
    for p in glob.glob(os.path.join(CART, 'pkr*.p8')):
        b, _ = rom(p)
        open(os.path.join(SCR, os.path.basename(p)[:-3] + '.p8.bin'), 'wb').write(b)
    b, code = rom(os.path.join(CART, 'pokered.p8'))
    open(os.path.join(SCR, 'main.bin'), 'wb').write(b)
    lua = p8lua.transpile(code)
    open(os.path.join(SCR, 'game.lua'), 'w', encoding='latin-1').write(lua)
    runner = '''
dofile(%r)
loadrom(%r)
local ok, err = xpcall(function() dofile(%r) end, debug.traceback)
if not ok then printh("LOAD ERROR "..err) os.exit(1) end
local cmds = dofile(%r)
local ok, err = xpcall(function() run_script(cmds) end, debug.traceback)
if not ok then printh("RUN ERROR "..err) screenshot("crash") end
''' % (os.path.join(HERE, 'p8shim.lua'), os.path.join(SCR, 'main.bin'), os.path.join(SCR, 'game.lua'),
       os.path.abspath(test))
    open(os.path.join(SCR, 'runner.lua'), 'w').write(runner)
    for f in glob.glob(os.path.join(SCR, '*.ppm')):
        os.remove(f)
    env = dict(os.environ, P8_CARTDIR=SCR, P8_OUTDIR=SCR)
    r = subprocess.run(['luajit', os.path.join(SCR, 'runner.lua')], env=env, capture_output=True, text=True,
                       encoding='latin-1')
    sys.stdout.write(r.stdout[-6000:])
    sys.stderr.write(r.stderr[-4000:])
    for f in sorted(glob.glob(os.path.join(SCR, '*.ppm'))):
        im = Image.open(f)
        im.resize((256, 256), Image.NEAREST).save(f[:-4] + '.png')


if __name__ == '__main__':
    main()
