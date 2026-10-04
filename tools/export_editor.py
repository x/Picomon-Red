#!/usr/bin/env python3
"""Export the CURRENT built overworld + every used tileset (blocks, 12x12 squares, flags) + people sprites for editor/index.html.
Writes editor/data.js and editor/blocks.png (block atlas, 32x32 per block, 16 per row, overworld blockset
plus custom blocks, with the game's bush->tree tile remap).
usage: cd tools && python3 export_editor.py        (runs the build without writing the cart)
from the build, after main():  import export_editor; export_editor.export(B)"""
import os, sys, json


def _place(W, id2m):
    """block positions from connections, Cinnabar below Pallet (ferry), unreachable maps in a row at the bottom"""
    pos, todo = {'PalletTown': (0, 0)}, ['PalletTown']
    while todo:
        m = todo.pop()
        x, y = pos[m]
        for i in range(0, len(W[m]['conns']), 3):
            d, n, o = W[m]['conns'][i:i + 3]
            n = id2m[n]
            if n in pos or n not in W:
                continue
            pos[n] = {2: (x + o, y - W[n]['h']), 1: (x + o, y + W[m]['h']), 3: (x - W[n]['w'], y + o),
                      4: (x + W[m]['w'], y + o)}[d]
            todo.append(n)
    if 'CinnabarIsland' in W:
        pos['CinnabarIsland'] = (pos['PalletTown'][0], pos['PalletTown'][1] + W['PalletTown']['h'] + 4)
    x = min(p[0] for p in pos.values())
    y = max(p[1] + W[m]['h'] for m, p in pos.items()) + 4
    for m in W:
        if m not in pos:
            pos[m] = (x, y)
            x += W[m]['w'] + 2
    x0 = min(p[0] for p in pos.values())
    y0 = min(p[1] for p in pos.values())
    return {m: (p[0] - x0, p[1] - y0) for m, p in pos.items()}


def _saved(B, name):
    for p in ('config/' + name,):  # where world.py / build.py read them
        f = os.path.join(B.PROJ, p)
        if os.path.exists(f):
            return json.load(open(f))
    return None


def _tileset(B, png, ts):
    """{ts, nbase, blocks: [[4 square keys]], squares: {key: {px: 144 shades, fl: flags}}} (unedited)"""
    raw = open(os.path.join(B.ROOT, 'gfx/blocksets/%s.bst' % png), 'rb').read()
    bst, fl = B.tileset_bst(png), B.tile_flags(ts)
    t = B.img('gfx/tilesets/%s.png' % png)
    px = lambda tile, x, y: t[tile // 16 * 8 + y][tile % 16 * 8 + x] if tile // 16 * 8 + y < len(t) else 0
    blocks, sqs = [], {}
    for b in range(len(bst) // 16):
        q = []
        for r in (0, 1):
            for c in (0, 1):
                key = tuple(bst[b * 16 + (r * 2 + rr) * 4 + c * 2 + cc] for rr in (0, 1) for cc in (0, 1))
                k = ','.join(map(str, key))
                if k not in sqs:
                    sqs[k] = dict(px=sum(B.square12([[px(key[(y // 8) * 2 + x // 8], x % 8, y % 8) for x in range(16)]
                                                     for y in range(16)]), []),
                                  fl=fl[key[2]])
                q.append(k)
        blocks.append(q)
    return dict(ts=ts, nbase=len(raw) // 16, blocks=blocks, squares=sqs)


def export(B):
    """call after B.main(): reads B.WORLD / B.SPRRES, writes editor/data.js + editor/blocks.png"""
    from PIL import Image
    import world
    out = os.path.join(B.PROJ, 'editor')
    W = {m: B.WORLD[m] for m in world.TOWNS + world.ROUTES if m in B.WORLD}  # B.WORLD also has indoor maps
    assert all(W[m]['ts'] == 'OVERWORLD' for m in W), 'editor only handles the overworld tileset'
    png = 'overworld'
    raw = open(os.path.join(B.ROOT, 'gfx/blocksets/%s.bst' % png), 'rb').read()
    bst = B.tileset_bst(png)  # .bst + custom blocks, as tileset_res draws it (without gfx_edits.json)
    n = len(bst) // 16
    assert n <= 256
    t = B.img('gfx/tilesets/%s.png' % png)
    px = lambda tile, x, y: t[tile // 16 * 8 + y][tile % 16 * 8 + x] if tile // 16 * 8 + y < len(t) else 0

    # block atlas (16x16 px per tile pair, 32x32 per block)
    im = Image.new('L', (16 * 32, (n + 15) // 16 * 32), 0)
    ip = im.load()
    gray = [255, 170, 85, 0]
    for k in range(n):
        for i in range(16):
            for yy in range(8):
                for xx in range(8):
                    ip[k % 16 * 32 + i % 4 * 8 + xx, k // 16 * 32 + i // 4 * 8 + yy] = gray[px(bst[k * 16 + i], xx, yy)]
    im.save(os.path.join(out, 'blocks.png'))

    # every tileset the game uses: blocks as 4 square keys (tl,tr,bl,br), squares as SEL12 pixels + flags
    pngs = {}
    for ts in sorted(B.TSRES):  # flags differ per tileset constant: prefer the one named like the png
        if B.TSNAMES[ts] not in pngs or ts.lower() == B.TSNAMES[ts]:
            pngs[B.TSNAMES[ts]] = ts
    tilesets = {p: _tileset(B, p, ts) for p, ts in sorted(pngs.items())}
    ow = tilesets[png]
    sqs = [dict(key=k, px=v['px']) for k, v in ow['squares'].items()]  # legacy fields (index based)
    sqid = {k: i for i, k in enumerate(ow['squares'])}
    blksq = [[sqid[k] for k in q] for q in ow['blocks']]

    id2m = {v: k for k, v in B.MAPID.items()}
    pos = _place(W, id2m)
    user = (_saved(B, 'world_edits.json') or {}).get('maps', {})
    maps, used = {}, set()
    for m in W:
        w, h, blk = W[m]['w'], W[m]['h'], list(W[m]['blocks'])
        info = B.load_mapinfo(m)
        border = 67 if m == 'PalletTown' else world.TREES if m == 'ViridianForest' else info['border']  # as world.py
        # original pokered blocks for "Reset map": widened maps keep the built extra east column
        orig = list(open(os.path.join(B.ROOT, 'maps/%s.blk' % m), 'rb').read())
        if info['ts'] != 'OVERWORLD':  # Viridian Forest: rebuilt from overworld blocks, no compatible original
            orig = blk
        elif info['w'] != w:
            ow = info['w']
            orig = sum((orig[r * ow:r * ow + ow] + blk[r * w + ow:r * w + w] for r in range(h)), [])
        assert len(blk) == len(orig) == w * h, m
        used |= set(blk) | {border}
        maps[m] = dict(x=pos[m][0], y=pos[m][1], w=w, h=h, border=border, blocks=blk, orig=orig,
                       origw=info['w'], user=m in user)

    sprites = {}
    for c in sorted(B.SPRRES):
        rows = B.shrink(B.img('gfx/sprites/%s.png' % c[7:].lower()))
        sprites[c] = [sum(rows[f * 12:f * 12 + 12], []) for f in range(len(rows) // 12)]

    data = dict(block=32, nblocks=n, nbase=len(raw) // 16, used=sorted(used), maps=maps, tileset=png,
                squares=sqs, blksq=blksq, tilesets=tilesets, sprites=sprites, gfxfile=_saved(B, 'gfx_edits.json'))
    with open(os.path.join(out, 'data.js'), 'w') as f:
        f.write('const DATA = %s;\n' % json.dumps(data, separators=(',', ':')))
    print('editor: wrote data.js (%d maps, %d blocks, %d sprites, tilesets %s) + blocks.png' % (
        len(maps), n, len(sprites), ' '.join('%s:%d/%d' % (p, len(v['blocks']), len(v['squares']))
                                              for p, v in tilesets.items())))


if __name__ == '__main__':
    sys.argv = sys.argv[:1]
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import build as B
    B.write_single = lambda code: None
    B.main()
    export(B)
