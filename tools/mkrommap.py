#!/usr/bin/env python3
"""Developer tool: regenerate tools/rommap.json from a built pokered checkout (make red), then check that
extract.py reproduces every pokered file it covers. Users never need this.
usage: mkrommap.py /path/to/pokered rom.gb"""
import sys, os, re, json, glob, hashlib, tempfile
from PIL import Image
import extract

PK, ROMF = sys.argv[1], sys.argv[2]
rom = open(ROMF, 'rb').read()
sym = {}
for l in open(os.path.join(PK, 'pokered.sym')):
    m = re.match(r'([0-9a-f]+):([0-9a-f]+) (\S+)', l)
    if m:
        b, a = int(m.group(1), 16), int(m.group(2), 16)
        sym[m.group(3)] = a if b == 0 else b * 0x4000 + a - 0x4000


def find(data, path):
    o = rom.find(data)
    assert o >= 0, path
    return o


files = {}
for p in sorted(glob.glob(os.path.join(PK, 'gfx/blocksets/*.bst')) + glob.glob(os.path.join(PK, 'maps/*.blk'))):
    d = open(p, 'rb').read()
    files[os.path.relpath(p, PK)] = {'fmt': 'bin', 'off': find(d, p), 'len': len(d)}
for pat in ('gfx/tilesets/*.png', 'gfx/sprites/*.png', 'gfx/emotes/*.png', 'gfx/font/*.png',
            'gfx/trainers/*.png', 'gfx/title/*.png', 'gfx/player/*.png', 'gfx/pokemon/front/*.png', 'gfx/pokemon/back/*.png'):
    for p in sorted(glob.glob(os.path.join(PK, pat))):
        b = p[:-4]
        w, h = Image.open(p).size
        if os.path.exists(b + '.pic'):
            files[os.path.relpath(p, PK)] = {'fmt': 'pic', 'off': find(open(b + '.pic', 'rb').read(), p)}
        else:
            fmt = '1bpp' if os.path.exists(b + '.1bpp') else '2bpp'
            d = open(b + '.' + fmt, 'rb').read()
            if d and rom.find(d) >= 0:
                files[os.path.relpath(p, PK)] = {'fmt': fmt, 'off': rom.find(d), 'len': len(d), 'w': w, 'h': h}
            else:
                print('  not in rom:', os.path.relpath(p, PK))
music = {}
for p in sorted(glob.glob(os.path.join(PK, 'audio/music/*.asm'))):
    labels = re.findall(r'^(Music_\w+?)_Ch(\d)::', open(p).read(), re.M)
    music[os.path.basename(p)[:-4]] = {'label': labels[0][0], 'ch': {c: sym['%s_Ch%s' % (n, c)] for n, c in labels}}
rm = {'sha1': hashlib.sha1(rom).hexdigest(), 'files': files, 'music': music}
json.dump(rm, open(os.path.join(extract.HERE, 'rommap.json'), 'w'), indent=0, sort_keys=True)
print('rommap.json: %d files, %d songs' % (len(files), len(music)))

# check: extraction == pokered
tmp = tempfile.mkdtemp()
os.makedirs(os.path.join(tmp, 'audio/music'))
extract.extract(rom, tmp, rm)
bad = 0
for path, e in files.items():
    a, b = os.path.join(PK, path), os.path.join(tmp, path)
    if e['fmt'] == 'bin':
        ok = open(a, 'rb').read() == open(b, 'rb').read()
    else:
        sh = lambda f: [3 - (v + 42) // 85 for v in Image.open(f).convert('L').get_flattened_data()]
        ok = Image.open(a).size == Image.open(b).size and sh(a) == sh(b)
    if not ok:
        bad += 1
        print('  MISMATCH', path)
import music as M
for name in music:
    a, b = os.path.join(PK, 'audio/music/%s.asm' % name), os.path.join(tmp, 'audio/music/%s.asm' % name)
    try:
        want = M.convert(a)
    except Exception:  # music.py can't read the original either (cross-channel calls)
        continue
    ok = want == M.convert(b)
    if not ok:
        bad += 1
        print('  MISMATCH music', name)
print('check:', 'all match' if not bad else '%d mismatches' % bad)
