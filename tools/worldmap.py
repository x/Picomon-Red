#!/usr/bin/env python3
"""Render the overworld (towns + routes) as one PNG, drawn the way the cart draws it: 12x12 squares, 4 shades
mapped through each map's palette. usage: worldmap.py out.png [--map NAME] [--scale N]"""
import sys
from PIL import Image
out = sys.argv[1] if len(sys.argv) > 1 else 'world.png'
one = sys.argv[sys.argv.index('--map') + 1] if '--map' in sys.argv else None
scale = int(sys.argv[sys.argv.index('--scale') + 1]) if '--scale' in sys.argv else 1
sys.argv = sys.argv[:1]
import build as B

B.main()
W = B.WORLD
id2m = {v: k for k, v in B.MAPID.items()}
pos = {'PalletTown': (0, 0)}
todo = ['PalletTown']
while todo:  # place maps by their connections (block units)
    m = todo.pop()
    x, y = pos[m]
    for i in range(0, len(W[m]['conns']), 3):
        d, n, o = W[m]['conns'][i:i + 3]
        n = id2m[n]
        if n not in pos:
            pos[n] = {2: (x + o, y - W[n]['h']), 1: (x + o, y + W[m]['h']), 3: (x - W[n]['w'], y + o),
                      4: (x + W[m]['w'], y + o)}[d]
            todo.append(n)
if one:
    pos = {one: (0, 0)}
else:
    pos['CinnabarIsland'] = (pos['PalletTown'][0], pos['PalletTown'][1] + W['PalletTown']['h'] + 4)  # by ferry
x0, y0 = min(p[0] for p in pos.values()), min(p[1] for p in pos.values())
x1 = max(p[0] + W[m]['w'] for m, p in pos.items())
y1 = max(p[1] + W[m]['h'] for m, p in pos.items())
im = Image.new('RGB', ((x1 - x0) * 24, (y1 - y0) * 24), B.P8[12])
rgb = lambda c: B.P8[c] if c < 16 else B.P8X[c - 128]
squares = {}


def square(png, key):
    """12x12 shades of a square, as the cart has it (hand-drawn in gfx_edits.json, or shrunk by square12)"""
    if (png, key) not in squares:
        e = B.GFXEDITS.get('squares', {}).get(png, {}).get(key)
        if e:
            squares[png, key] = [e[i * 12:i * 12 + 12] for i in range(12)]
        else:
            src, t = B.img('gfx/tilesets/%s.png' % png), [int(v) for v in key.split(',')]
            px = lambda q, x, y: src[q // 16 * 8 + y][q % 16 * 8 + x] if q // 16 * 8 + y < len(src) else 0
            squares[png, key] = B.square12([[px(t[(y // 8) * 2 + x // 8], x % 8, y % 8) for x in range(16)]
                                            for y in range(16)])
    return squares[png, key]


for m, (bx, by) in pos.items():
    w = W[m]
    png = B.TSNAMES[w['ts']]
    cols = [(255, 241, 232), rgb(w['pal'][1]), rgb(w['pal'][2]), (0, 0, 0)]
    for k, b in enumerate(w['blocks']):
        for q, key in enumerate(B.block_keys(png, b)):
            ox, oy = (bx - x0 + k % w['w']) * 24 + q % 2 * 12, (by - y0 + k // w['w']) * 24 + q // 2 * 12
            for y, row in enumerate(square(png, key)):
                for x, c in enumerate(row):
                    im.putpixel((ox + x, oy + y), cols[c])
if scale > 1:
    im = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
im.save(out)
print(out, im.size)
