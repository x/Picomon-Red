"""The single-cart world: Pallet -> Elite Four with gate warps, shared gym/center rooms and badge gating.
build_maps(B) is called from build.py (B is the build module)."""
import os, re
import config

TOWNS = ['PalletTown', 'ViridianCity', 'PewterCity', 'CeruleanCity', 'SaffronCity', 'VermilionCity', 'CeladonCity',
         'FuchsiaCity', 'CinnabarIsland', 'LavenderTown']
ROUTES = ['Route1', 'Route2', 'Route3', 'Route4', 'Route5', 'Route6', 'Route7', 'Route16', 'Route17', 'Route18',
          'ViridianForest', 'Route8', 'Route9', 'Route10', 'Route22']
CENTER = 'ViridianPokecenter'
KEEPOPEN = {'ViridianCity': (7 * 20, 8 * 20)}  # Viridian's west road to Route 22 (the way to the Elite Four)
NOTRAINER = {('Route4', 63, 3)}  # a Lv31 Lass on the ledge right after badge 1 (a trap at that point)
GYMLAYOUT = 'PewterGym'
E4LAYOUT, E4IN = 'LoreleisRoom', (4, 10)  # every Elite Four room is Lorelei's; you walk in at its bottom door
# ...drawn with blocks already in the cart: gym floor, carpet for the platform, gym statues, Brock's top wall
E4SKIN = {}  # Lorelei's own tiles
E4DOOR = [(4, 1), (5, 1)]  # step up to the door once its member is beaten
# every gym shares Brock's room. Its middle obstacles (blocks 11, 18, 19, 6, 7) are re-tiled per leader: each solid
# square becomes the leader's theme square, so the walls stay exactly where Brock's are (you still have to pass the
# gym trainer). Theme squares are gym-tileset squares (tile ids tl,tr,bl,br).
GYMTHEME = {'Gym2': (20, 20, 20, 20),   # Misty: pool water
            'Gym3': (11, 12, 27, 28),   # Lt. Surge: trash cans
            'Gym4': (44, 45, 46, 47),   # Erika: trees
            'Gym5': (31, 31, 31, 31),   # Koga: his invisible walls (they look like floor)
            'Gym6': (52, 67, 82, 83),   # Sabrina: bookshelves
            'Gym8': (2, 56, 18, 19)}    # Giovanni: statues
GYMSKIN = {}  # gym -> {Brock's block: its themed custom block}, filled by gym_themes()


def gym_themes(B):
    bst = open(os.path.join(B.ROOT, 'gfx/blocksets/gym.bst'), 'rb').read()
    base = len(bst) // 16 + len(B.CUSTOMBST.get('gym', b'')) // 16
    new = []
    for gym, sq in GYMTHEME.items():
        GYMSKIN[gym] = {}
        for b in (11, 18, 19, 6, 7):
            t = list(bst[b * 16:b * 16 + 16])
            for r in (0, 1):
                for c in (0, 1):
                    key = ','.join(str(t[(r * 2 + rr) * 4 + c * 2 + cc]) for rr in (0, 1) for cc in (0, 1))
                    if not B.tile_flags('GYM')[int(key.split(',')[2])] & 1:  # a solid square of the boulder block
                        for i, v in enumerate(sq):
                            t[(r * 2 + i // 2) * 4 + c * 2 + i % 2] = v
            if bytes(t) not in new:
                new.append(bytes(t))
            GYMSKIN[gym][b] = base + new.index(bytes(t))
    B.CUSTOMBST['gym'] = B.CUSTOMBST.get('gym', b'') + b''.join(new)
# town, gym map (for its first trainer), leader, pic, sprite, team
GYMS = [
    ('PewterCity', 'PewterGym', 'BROCK', 'brock', 'SPRITE_COOLTRAINER_M'),
    ('CeruleanCity', 'CeruleanGym', 'MISTY', 'misty', 'SPRITE_COOLTRAINER_F'),
    ('VermilionCity', 'VermilionGym', 'LT.SURGE', 'lt.surge', 'SPRITE_COOLTRAINER_M'),
    ('CeladonCity', 'CeladonGym', 'ERIKA', 'erika', 'SPRITE_COOLTRAINER_F'),
    ('FuchsiaCity', 'FuchsiaGym', 'KOGA', 'koga', 'SPRITE_COOLTRAINER_M'),
    ('SaffronCity', 'SaffronGym', 'SABRINA', 'sabrina', 'SPRITE_COOLTRAINER_F'),
    ('CinnabarIsland', 'CinnabarGym', 'BLAINE', 'blaine', 'SPRITE_COOLTRAINER_M'),
    ('ViridianCity', 'ViridianGym', 'GIOVANNI', 'giovanni', 'SPRITE_COOLTRAINER_M'),
]
ELITE = [
    ('LORELEI', 'lorelei', 'SPRITE_COOLTRAINER_F'),
    ('BRUNO', 'bruno', 'SPRITE_COOLTRAINER_M'),
    ('AGATHA', 'agatha', 'SPRITE_COOLTRAINER_F'),
    ('LANCE', 'lance', 'SPRITE_COOLTRAINER_M'),
]
# map edges closed by a line of trainers until a badge is won
EDGE_GATES = [('PewterCity', 'E', 1), ('CeruleanCity', 'E', 2), ('SaffronCity', 'W', 3), ('CeladonCity', 'W', 4)]
E4GATE = ('Route22', [(8, 5)], 8)  # Route 22's gate house door is the way to the Elite Four (opens with badge 8)
DOOR_GATES = [('SaffronCity', 'SaffronGym', 5), ('ViridianCity', 'ViridianGym', 7)]
# simplified shared pokecenter: pillar, healer, wall / counter / floor / plants, mat, plants
CENTER_BLK = []  # filled by center_blocks()


def center_blocks(B):
    """the shared pokecenter, 16x16 tiles cut from the original 28x16 one: pillar, healer, nurse, a long plain
    counter, the PC in the right corner, two plants, the door mat, one plant. Appended as custom blocks."""
    bst = open(os.path.join(B.ROOT, 'gfx/blocksets/pokecenter.bst'), 'rb').read()
    blk = open(os.path.join(B.ROOT, 'maps/ViridianPokecenter.blk'), 'rb').read()
    o = lambda r, c: bst[blk[(r // 4) * 7 + c // 4] * 16 + (r % 4) * 4 + c % 4]  # original tile at row r, col c
    top = [0, 1, 2, 3, 4, 5, 6, 17, 16, 17, 18, 19, 16, 17, 26, 27]
    g = [[0] * 16 for _ in range(16)]
    for r in range(16):
        for c in range(16):
            if r < 6:
                g[r][c] = o(r, top[c])
            elif r < 12:
                g[r][c] = o(r, 26 + c % 2 if c >= 14 else 8 + c % 2)
            else:
                g[r][c] = o(r, (list(range(12)) + [10, 11, 26, 27])[c])
    n = len(bst) // 16
    B.CUSTOMBST['pokecenter'] = bytes(g[by * 4 + i // 4][bx * 4 + i % 4] for by in range(4) for bx in range(4)
                                      for i in range(16))
    CENTER_BLK[:] = list(range(n, n + 16))
TREES = 15  # overworld block of four trees: seals and tidy fill


COAST = 200  # overworld block: sea with a shoreline along its bottom edge (built by coast_block())


def coast_block(B):
    """the overworld only has shorelines on the sea's top/side edges: flip the top-shore square to make a bottom one"""
    src = B.img('gfx/tilesets/overworld.png')
    top = [int(v) for v in B.block_keys('overworld', 31)[0].split(',')]  # sea square with the shore line on top
    px = sum(B.square12([[src[top[(y // 8) * 2 + x // 8] // 16 * 8 + y % 8][top[(y // 8) * 2 + x // 8] % 16 * 8 + x % 8]
                          for x in range(16)] for y in range(16)]), [])
    flip = [px[(11 - r) * 12 + c] for r in range(12) for c in range(12)]
    g = B.GFXEDITS
    g.setdefault('squares', {}).setdefault('overworld', {})['new:coast_s'] = flip
    g.setdefault('flags', {}).setdefault('overworld', {})['new:coast_s'] = 0
    g.setdefault('blocks', {}).setdefault('overworld', {}).setdefault(str(COAST),
                                                                      ['20,20,20,20'] * 2 + ['new:coast_s'] * 2)


def _rect(w, x0, y0, x1, y1, b, skip=()):
    return {y * w + x: b for y in range(y0, y1 + 1) for x in range(x0, x1 + 1) if (x, y) not in skip}


# map -> {block index: block}: hand edits (15 trees, 67 sea, 31 shore, 107 harbour fence)
EDITS = {
    'VermilionCity': {**_rect(20, 15, 9, 15, 14, 67), **_rect(20, 9, 13, 14, 14, 67), **_rect(20, 9, 16, 9, 17, 67),
                      **_rect(20, 8, 15, 10, 15, 107), **_rect(20, 16, 9, 16, 10, 67), 9 * 20 + 14: 67, 10 * 20 + 14: 67,
                      **_rect(20, 14, 8, 16, 8, 31)},  # no S.S. Anne dock
    'Route2': {4 * 10 + 6: 87},  # Diglett's Cave mouth -> plain rock face
    'CinnabarIsland': _rect(11, 5, 0, 6, 0, COAST),  # a coastline where the road ran north into Route 21
}
# maps edited in the web editor (editor/index.html -> config/world_edits.json)
# (old files hold original-coordinate maps applied before cuts/seals; files with "coords":"final" hold finished
#  maps exactly as the editor shows them, used as-is)
USER, FINAL = {}, {}
for _p in ('config/world_edits.json',):
    _f = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', _p)
    if os.path.exists(_f):
        import json
        _j = json.load(open(_f))
        if _j.get('coords') == 'final':
            FINAL = _j['maps']
        else:
            USER = _j['maps']
# extra block column on the east side of a map (one block per row): Cinnabar's east shore
WIDEN = {'CinnabarIsland': [101] * 7 + [67, 107]}
NOCUT = {'Route2', 'CeruleanCity'}  # their cut trees stay: Route 2's hidden lane, Cerulean's south exit
# houses you walk straight through (front door -> outside the back door and back), closed by a trainer until a badge
HOUSES = [('CeruleanCity', (27, 11), (27, 9), 2)]  # the dig house: the only way to Cerulean's south exit  # its cut trees keep you out of the Diglett's Cave lane until you've come through the forest
# Diglett's Cave as a pass-through (cave door, exit town's east edge, badge needed). Off: its Route 2 door is in
# the cut-only lane that the tidy pass removes. ('Route2', (12, 9), 'VermilionCity', 2) turns it back on.
DIGLETT = None
CAVES = [('Route4', (18, 5), (24, 5)), ('Route10', (8, 17), (8, 53))]  # Mt. Moon, Rock Tunnel: walk straight through
# map links by trigger: (map, squares, destination map, arrival square). Viridian Forest sits between Route 2's
# gate houses (their doors take you straight in/out); the forest is rebuilt from overworld trees/grass/paths.
LINKS = [('Route2', [(3, 43)], 'ViridianForest', (17, 45)), ('Route2', [(3, 11)], 'ViridianForest', (2, 2)),
         ('ViridianForest', [(15, 47), (16, 47), (17, 47), (18, 47)], 'Route2', (3, 44)),
         ('ViridianForest', [(1, 0), (2, 0)], 'Route2', (3, 10)),
         # the underground paths: door to door (Route 7 <-> 8 needs badge 3, like Saffron's west gate)
         ('Route5', [(17, 27)], 'Route6', (17, 14)), ('Route6', [(17, 13)], 'Route5', (17, 28)),
         ('Route7', [(5, 13)], 'Route8', (13, 4), 3), ('Route8', [(13, 3)], 'Route7', (5, 14), 3)]
# boats (the sea routes are cut): south from Pallet's shore <-> Cinnabar's north end; Cinnabar's east shore <->
# Fuchsia's beach (where Route 19 began). Going out needs badge 6.
FERRY = [('PalletTown', [(x, 13) for x in range(4, 8)], 'CinnabarIsland', (11, 3), 6),
         ('CinnabarIsland', [(x, 2) for x in range(10, 14)], 'PalletTown', (5, 12), 0),
         ('FuchsiaCity', [(x, 33) for x in range(16, 24)], 'CinnabarIsland', (18, 8), 6),
         ('CinnabarIsland', [(19, y) for y in range(4, 14)], 'FuchsiaCity', (19, 32), 0)]
TOWNPAL = {'PalletTown': 'PAL_PALLET', 'ViridianCity': 'PAL_VIRIDIAN', 'PewterCity': 'PAL_PEWTER',
           'CeruleanCity': 'PAL_CERULEAN', 'SaffronCity': 'PAL_SAFFRON', 'VermilionCity': 'PAL_VERMILION',
           'CeladonCity': 'PAL_CELADON', 'LavenderTown': 'PAL_LAVENDER', 'FuchsiaCity': 'PAL_FUCHSIA',
           'CinnabarIsland': 'PAL_CINNABAR'}
SPRITES = {'SPRITE_RED', 'SPRITE_BLUE', 'SPRITE_OAK', 'SPRITE_POKE_BALL', 'SPRITE_NURSE', 'SPRITE_FISHER',
           'SPRITE_YOUNGSTER', 'SPRITE_GIRL', 'SPRITE_SEEL'}
# the surfing pokemon waits on the water by each boat shore once the boats run (badge 6): (map, x, y, facing)
SURFERS = [('PalletTown', 5, 15, 2), ('FuchsiaCity', 19, 34, 2), ('CinnabarIsland', 11, 0, 1),
           ('CinnabarIsland', 20, 8, 3)]
FEMALE = {'SPRITE_LITTLE_GIRL', 'SPRITE_BEAUTY', 'SPRITE_BRUNETTE_GIRL', 'SPRITE_MIDDLE_AGED_WOMAN', 'SPRITE_GRANNY',
          'SPRITE_DAISY', 'SPRITE_SWIMMER_F', 'SPRITE_CHANNELER', 'SPRITE_COOLTRAINER_F'}
FEMALE_CLASS = {'LASS', 'JR_TRAINER_F', 'BEAUTY', 'COOLTRAINER_F', 'CHANNELER', 'PSYCHIC_TR'}


def sprite(s):
    return s if s in SPRITES else 'SPRITE_GIRL' if s in FEMALE else 'SPRITE_YOUNGSTER'


def forest_blocks(B):
    """Viridian Forest in overworld blocks: each 16x16 square of a forest block becomes a tree, tall-grass or path
    square of the overworld set. Unique patterns are appended to the overworld blockset as custom blocks."""
    fb = open(os.path.join(B.ROOT, 'gfx/blocksets/forest.bst'), 'rb').read()
    coll, grass = set(B.TSCOLL['Forest']), B.TSHEAD['Forest']['grass']
    quad = {'s': (0x40, 0x41, 0x50, 0x51), 'g': (0x52,) * 4, 'w': (0x2c,) * 4}
    base = len(open(os.path.join(B.ROOT, 'gfx/blocksets/overworld.bst'), 'rb').read()) // 16
    pats, out = [], []
    for b in open(os.path.join(B.ROOT, 'maps/ViridianForest.blk'), 'rb').read():
        p = ''
        for r in (0, 1):
            for c in (0, 1):
                t = fb[b * 16 + (r * 2 + 1) * 4 + c * 2]
                p += 'g' if t == grass else 'w' if t in coll else 's'
        if p not in pats:
            pats.append(p)
        out.append(base + pats.index(p))
    custom = bytearray()
    for p in pats:
        blk = [0] * 16
        for qi, k in enumerate(p):
            r, c = qi // 2, qi % 2
            for i, t in enumerate(quad[k]):
                blk[(r * 2 + i // 2) * 4 + c * 2 + i % 2] = t
        custom += bytes(blk)
    B.CUSTOMBST['overworld'] = B.CUSTOMBST.get('overworld', b'') + bytes(custom)
    return bytes(out)


def build_maps(B):
    import content
    ROOT = B.ROOT
    gyms = ['Gym%d' % i for i in range(1, 9)]
    e4 = ['E4_%d' % i for i in range(1, 6)]
    maps = TOWNS + ROUTES + ['RedsHouse2F', 'OaksLab', CENTER] + gyms + e4
    B.MAPS[:] = maps
    B.MAPID.clear()
    B.MAPID.update({m: i + 1 for i, m in enumerate(maps)})
    for i, f in enumerate(['BADGE%d' % k for k in range(1, 9)] + ['E4_%d' % k for k in range(1, 6)]):
        B.FLAGS[f] = 40 + i
    center_blocks(B)
    gym_themes(B)
    layout = {m: (GYMLAYOUT if m in gyms else E4LAYOUT if m in e4 else m) for m in maps}
    info = {m: dict(B.load_mapinfo(m)) for m in set(layout.values())}
    info['ViridianForest'].update(ts='OVERWORLD', border=TREES)
    FOREST = forest_blocks(B)
    B.tileset_bst.cache_clear()  # custom blocks were added
    coast_block(B)

    info[CENTER]['w'], info[CENTER]['h'] = 4, 4
    info['PalletTown']['border'] = 67  # open sea south of Pallet (Route 21 is cut)
    for m in WIDEN:
        info[m]['w'] += 1
    cut = {}
    ob = open(os.path.join(ROOT, 'gfx/blocksets/overworld.bst'), 'rb').read()
    for a, b in B.TILESETS['cut_trees']:  # only real overworld cut trees (tiles $2d,$2e,$3d,$3e), not cut grass
        if {x for x, y in zip(ob[a * 16:a * 16 + 16], ob[b * 16:b * 16 + 16]) if x != y} <= {45, 46, 61, 62}:
            cut[a] = b

    fill = {}  # map -> unreachable blocks, planted with trees (tidy pass)
    cave = {}  # map -> block index of the diglett's cave mouth (block 6) set into a sealed edge
    seal = {}  # map -> {block index: side} on edges that lead to cut maps

    _base = {}

    def base(m):
        if m not in _base:
            _base[m] = _base_(m)
        return _base[m]

    def _base_(m):
        """blocks after cut trees, widening and hand edits (before seals)"""
        b = bytes(CENTER_BLK) if m == CENTER else FOREST if m == 'ViridianForest' else \
            open(os.path.join(ROOT, 'maps/%s.blk' % m), 'rb').read()
        if m in USER:  # hand-made in editor/index.html, saved as world_edits.json
            b = bytes(USER[m]['blocks'])
        if m in WIDEN:
            w = info[m]['w'] - 1
            b = b''.join(b[r * w:r * w + w] + bytes([WIDEN[m][r]]) for r in range(len(b) // w))
        b = bytes(cut.get(x, x) for x in b) if info[m]['ts'] == 'OVERWORLD' and m not in NOCUT else b
        return bytes((EDITS.get(m, {}) if m not in USER else {}).get(i, x) for i, x in enumerate(b))

    def blocks(m):
        if m in FINAL:
            b = list(FINAL[m]['blocks'])
            for i in KEEPOPEN.get(m, ()):  # roads the game needs, whatever the editor saved
                b[i] = open(os.path.join(ROOT, 'maps/%s.blk' % m), 'rb').read()[i]
            return bytes(b)
        return bytes(6 if i == cave.get(m) else sealblk(m, i) if i in seal.get(m, {}) else x
                     for i, x in enumerate(base(m)))

    def qflag(m, blk, q):
        """flags of square q (0 tl, 1 tr, 2 bl, 3 br) of a block, as the game will have them"""
        return B.square_flags(info[m]['ts'], B.block_keys(B.TSNAMES[info[m]['ts']], blk)[q])

    def sqflag(m, x, y):
        return qflag(m, blocks(m)[(y // 2) * info[m]['w'] + x // 2], (y % 2) * 2 + x % 2)

    def solid(m, blk):
        return not any(qflag(m, blk, q) & 1 for q in range(4))

    def sealblk(m, i):
        """continue the edge: the commonest solid block along the same edge (its tree line, fence or shore)"""
        w, h, b = info[m]['w'], info[m]['h'], base(m)
        side = seal[m][i]
        line = [(by * w + bx) for by in range(h) for bx in range(w)
                if {'N': by == 0, 'S': by == h - 1, 'W': bx == 0, 'E': bx == w - 1}[side]]
        quads = {'N': [(0, 0), (0, 1)], 'S': [(1, 0), (1, 1)], 'W': [(0, 0), (1, 0)], 'E': [(0, 1), (1, 1)]}[side]
        shut = lambda k: not any(qflag(m, k, r * 2 + c) & 1 for r, c in quads)
        wet = lambda k: any('20' in key.split(',') for key in B.block_keys(B.TSNAMES[info[m]['ts']], k))
        sol = [b[j] for j in line if j not in seal[m] and shut(b[j]) and (wet(b[i]) or not wet(b[j]))]
        if sol and sol.count(max(set(sol), key=sol.count)) >= 4:  # a real line (tree edge, fence), not a roof
            return max(set(sol), key=sol.count)
        if info[m]['ts'] == 'OVERWORLD':
            return TREES
        if solid(m, info[m]['border']):
            return info[m]['border']
        cnt = {}
        for n in TOWNS + ROUTES:
            if info[n]['ts'] == info[m]['ts']:
                for x in open(os.path.join(ROOT, 'maps/%s.blk' % n), 'rb').read():
                    cnt[x] = cnt.get(x, 0) + 1
        return max((x for x in cnt if solid(m, x)), key=cnt.get)


    def walkable(m, x, y):
        inf = info[m]
        if not (0 <= x < inf['w'] * 2 and 0 <= y < inf['h'] * 2):
            return False
        return sqflag(m, x, y) & 1 > 0

    def edge(m, side):
        W, H = info[m]['w'] * 2, info[m]['h'] * 2
        pts = {'E': [(W - 1, y) for y in range(H)], 'W': [(0, y) for y in range(H)],
               'S': [(x, H - 1) for x in range(W)], 'N': [(x, 0) for x in range(W)]}[side]
        return [p for p in pts if walkable(m, *p)]

    def step_out(m, door, away=None):
        x, y = door
        if away is not None:
            if abs(away[0] - x) > abs(away[1] - y):
                return (x + (1 if away[0] < x else -1), y)
            return (x, y + (1 if away[1] < y else -1))
        for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            if walkable(m, x + dx, y + dy):
                return (x + dx, y + dy)
        return (x, y + 1)

    def party(pic, mons):
        """battle party resource: pic, then (level, species, 4 moves) per mon"""
        f = [B.pic_res('gfx/trainers/%s.png' % pic)]
        for lv, sp in mons:
            ms = B.moves_at(sp, lv)
            f += [lv, B.DEX[sp]] + [B.MOVEC[m] for m in ms] + [0] * (4 - len(ms))
            B.TRAINERMOVES.update(ms)
        r = B.autores(B.nums(f))
        B.BINRES.add(r)
        return r

    placed = set()

    def trainer_obj(m, o, cls, slot, x=None, y=None, d=None, sight=None):
        """a regular trainer, shown as a Youngster, Bug Catcher or Lass; its team is trainers.json["trainers"]["Map x,y"]"""
        x, y = x if x is not None else int(o[0]), y if y is not None else int(o[1])
        flag = B.FLAGS.setdefault('T_%s_%d_%d' % (m, x, y), max(B.FLAGS.values()) + 1)
        key = '%s %d,%d' % (m, x, y)
        if key not in config.TRAINERS['trainers']:
            raise SystemExit('config errors:\n  trainers.json: no team for the trainer at "%s"' % key)
        placed.add(key)
        kind = 'bugcatcher' if cls == 'BUG_CATCHER' else 'lass' if cls in FEMALE_CLASS else 'youngster'
        sc = party(kind, config.TRAINERS['trainers'][key])  # the engine fights a trainer object's party directly (runs())
        return [slot, x, y, 0,
                d or {'DOWN': 1, 'UP': 2, 'LEFT': 3, 'RIGHT': 4}.get(o[4], 1), sc, 0, sight or 3, flag]

    def span(m, d, dc, off):
        """edge squares of map m that lead into its connection (d, dc, off)"""
        n = B.load_mapinfo(B.const_to_map(dc))
        lo, hi = off * 2, (off + (n['w'] if d in ('north', 'south') else n['h'])) * 2
        return [(x, y) for (x, y) in edge(m, d[0].upper()) if lo <= (x if d in ('north', 'south') else y) < hi]

    for m in TOWNS + ROUTES:  # roads into cut maps or past a connection's end: continue the edge across them
        for side in {d[0].upper() for (d, dc, off) in info[m]['conns']}:
            ok = [q for (d, dc, off) in info[m]['conns'] if d[0].upper() == side and B.const_to_map(dc) in TOWNS + ROUTES
                  for q in span(m, d, dc, off)]
            for x, y in edge(m, side):
                if (x, y) not in ok:
                    seal.setdefault(m, {})[y // 2 * info[m]['w'] + x // 2] = side
            assert set(edge(m, side)) <= set(ok), (m, side, set(edge(m, side)) - set(ok))
            for (d, dc, off) in info[m]['conns']:  # every kept connection still has a way through
                if d[0].upper() == side and B.const_to_map(dc) in TOWNS + ROUTES:
                    assert span(m, d, dc, off), (m, d, 'connection blocked')
    if DIGLETT:
        dt = DIGLETT[2]
        bx = info[dt]['w'] - 1
        rows = sorted(i // info[dt]['w'] for i in seal[dt] if i % info[dt]['w'] == bx)
        by = next(r for r in rows[len(rows) // 2:] if walkable(dt, bx * 2 - 1, r * 2 + 1))
        cave[dt] = by * info[dt]['w'] + bx
        cavedoor = (bx * 2, by * 2 + 1)
    nop = B.script('x')
    reach = {}
    # gate houses become door-to-door warps
    gate_warp = {}
    for m in TOWNS + ROUTES:
        for wi, (x, y, dest, di) in enumerate(info[m]['warps']):
            dm = B.const_to_map(dest)
            if dm and 'Gate' in dm and 'Forest' not in dm:
                gw = B.load_mapinfo(dm)['warps']
                ex, ey = gw[di - 1][:2]
                far = [w for w in gw if w[2] == 'LAST_MAP' and abs(w[0] - ex) + abs(w[1] - ey) > 3]
                if not far:
                    continue
                horiz = abs(far[0][0] - ex) > abs(far[0][1] - ey)
                far.sort(key=lambda w: abs(w[1] - ey) if horiz else abs(w[0] - ex))
                tx, ty = info[m]['warps'][far[0][3] - 1][:2]
                gate_warp[(m, x, y)] = step_out(m, (tx, ty), (x, y))
    for (x, y) in E4GATE[1]:
        gate_warp.pop((E4GATE[0], x, y), None)  # that gate leads to the Elite Four instead

    # tidy pass: flood every town/route from where the player can arrive; blocks whose walkable
    # squares are never reached (item pockets, cut-only lanes, unused shores) become trees
    for m in TOWNS + ROUTES:
        W, H = info[m]['w'] * 2, info[m]['h'] * 2
        seeds = [q for (d, dc, off) in info[m]['conns'] if B.const_to_map(dc) in TOWNS + ROUTES
                 for q in span(m, d, dc, off)]
        seeds += [b for (fm, sq, dest, b, _) in FERRY if dest == m] + [a for (cm, a, b) in CAVES if cm == m]
        seeds += [(5, 5)] if m == 'PalletTown' else []
        seeds += [a for (lm_, sq_, dm_, a, *_) in LINKS if dm_ == m]
        seeds += [(cavedoor[0] - 1, cavedoor[1])] if DIGLETT and m == DIGLETT[2] else []
        links = {}
        for (gm, x, y), t in gate_warp.items():
            if gm == m:
                links.setdefault((x, y), []).append(t)
        for (hm, a, b, _) in HOUSES:
            if hm == m:
                links.setdefault(a, []).append(step_out(m, b, (b[0], b[1] + 1)))
                links.setdefault(b, []).append(step_out(m, a, (a[0], a[1] - 1)))
        for (lm_, sq_, dm_, a, *_) in LINKS:
            if lm_ == m:
                for q in sq_:
                    links.setdefault(q, [])
        for (cm, a, b) in CAVES:
            if cm == m:
                links.setdefault(a, []).append(step_out(m, b))
                links.setdefault(b, []).append(step_out(m, a))
        seen, todo = set(), list(seeds)
        while todo:
            p = todo.pop()
            if p in seen:
                continue
            seen.add(p)
            x, y = p
            for t in links.get(p, []):
                todo.append(t)
            for d, (dx, dy) in ((1, (0, 1)), (2, (0, -1)), (3, (-1, 0)), (4, (1, 0))):
                nx, ny = x + dx, y + dy
                if not (0 <= nx < W and 0 <= ny < H):
                    continue
                if walkable(m, nx, ny):
                    todo.append((nx, ny))
                elif sqflag(m, nx, ny) & {1: 16, 2: 0, 3: 32, 4: 64}[d] and walkable(m, nx + dx, ny + dy):
                    todo.append((nx + dx, ny + dy))
        f = set()
        for i in range(info[m]['w'] * info[m]['h']):
            bx, by = i % info[m]['w'], i // info[m]['w']
            sq = [(bx * 2 + c, by * 2 + r) for r in (0, 1) for c in (0, 1)]
            if any(walkable(m, *q) for q in sq) and not any(q in seen for q in sq):
                f.add(i)
        fill[m] = set()  # the tree fill is off: hand edits look more natural. f = what it would plant
        reach[m] = seen
        for (x, y, dest, di) in info[m]['warps']:  # every door we keep must still be reachable
            dm = B.const_to_map(dest) or ''
            if dm.endswith('Pokecenter') or dm in [g[1] for g in GYMS] or dm in ('RedsHouse1F', 'OaksLab'):
                assert (x, y) in seen or not walkable(m, x, y), (m, x, y, dm)


    # blocks used per blockset
    for m in set(layout.values()):
        u = B.USEDBLK.setdefault(B.TSNAMES[info[m]['ts']], set())
        u.update(blocks(m))
        if m == E4LAYOUT:
            u.difference_update(E4SKIN)  # Lorelei's own blocks are all swapped out
        for sk in list(GYMSKIN.values()) + [E4SKIN]:
            u.update(sk.values()) if B.TSNAMES[info[m]['ts']] == 'gym' else None
        u.add(info[m]['border'])

    for m in maps:
        lm = layout[m]
        inf = info[lm]
        mid = B.MAPID[m]
        gfx, flags, blkset, _ = B.tileset_res(inf['ts'])
        bm = B.BLKMAP[inf['ts']]
        skin = E4SKIN if m in e4 else GYMSKIN.get(m, {})
        blk = B.autores(bytes(bm[skin.get(b, b)] for b in blocks(lm)))
        town = next((g[0] for g in GYMS if 'Gym%d' % (GYMS.index(g) + 1) == m), m)
        pal = B.SGB[TOWNPAL.get(town, 'PAL_ROUTE' if m in ROUTES else 'PAL_PALLET')]
        cx = content.MAPS.get(m, {}) if m in ('PalletTown', 'OaksLab') else {}
        sprites = ['SPRITE_RED']

        def slot(s):
            s = sprite(s)
            if s not in sprites:
                sprites.append(s)
            return sprites.index(s) + 1
        objs, trig, warps = [], [], []
        mdata = B.MAPDATA['maps'][lm]
        theads = mdata['trainers']
        # ---- objects
        if m in ('PalletTown', 'OaksLab'):
            keep = {'PalletTown': [1, 3], 'OaksLab': [1, 2, 3, 4, 5]}[m]
            for oi in keep:
                o = inf['objs'][oi - 1]
                ov = cx.get('obj', {}).get(oi, {})
                cond = ov.get('cond', 0)
                if isinstance(cond, str):
                    cond = -B.FLAGS[cond[1:]] if cond.startswith('!') else B.FLAGS[cond]
                st = mdata['texts'].get(o[5])
                sc = B.script(ov['script'], cx.get('ctx')) if 'script' in ov else B.script('t ' + st)
                mvt = 0 if o[3] == 'STAY' else 1
                d = {'DOWN': 1, 'UP': 2, 'LEFT': 3, 'RIGHT': 4}.get(o[4], 1)
                objs.append([slot(o[2]), int(o[0]), int(o[1]), mvt, d, sc, cond, 0, 0])
        elif m == 'RedsHouse2F':  # the SNES (test shortcut): every badge and a level 100 party
            objs.append([0, 3, 5, 0, 1, B.script('\n'.join(['s BADGE%d' % k for k in range(1, 9)] + ['L'])), 0, 0, 0])
        elif m == CENTER:
            objs.append([slot('SPRITE_NURSE'), 3, 1, 0, 1, B.script('z 1'), 0, 0, 0])
        elif m in gyms:
            gi = gyms.index(m)
            town, gmap, name, pic, spr = GYMS[gi]
            flag = B.FLAGS['BADGE%d' % (gi + 1)]
            p = party(pic, config.TRAINERS['leaders'][name])
            objs.append([slot(spr), 4, 1, 0, 1, B.script('j %d,@a\nb %d,0\ns %d\na:' % (flag, p, flag)), 0, 0, 0])
            gi_ = B.load_mapinfo(gmap)
            t = next(o for o in gi_['objs'][1:] if len(o) > 7 and o[6].startswith('OPP_'))
            objs.append(trainer_obj(m, t, t[6][4:], slot(t[2]), 3, 6, 4, 4))
        elif m in e4:
            ei = e4.index(m)
            flag = B.FLAGS['E4_%d' % (ei + 1)]
            if ei < 4:
                name, pic, spr = ELITE[ei]
                sc = 'j %d,@a\nb %d,0\ns %d\na:' % (flag, party(pic, config.TRAINERS['leaders'][name]), flag)
                s_ = B.script('w %d,%d,%d' % (B.MAPID[e4[ei + 1]], *E4IN))
                for (x, y) in E4DOOR:
                    trig += [x, y, flag, s_]
            else:
                spr = 'SPRITE_BLUE'
                sc = ''
                champ = config.TRAINERS['champion']  # the player's starter flag -> the champion's team
                for k, f in enumerate(champ):
                    sc += 'j %s,@c%d\n' % (f, k)
                for k, f in enumerate(champ):
                    sc += 'c%d:\nb %d,0\ng @w\n' % (k, party('rival1', champ[f]))
                sc += 'w:\nz 2'  # losing blacks out (aborting this script), so getting here means you won
            objs.append([slot(spr), 5, 2, 0, 1, B.script(sc), 0, 0, 0])
        elif m in TOWNS + ROUTES:
            ti = 0
            for o in inf['objs']:
                if len(o) > 7 and o[6].startswith('OPP_') and o[6] != 'OPP_ROCKET':
                    if ti < len(theads):
                        sg = int(theads[ti][1])
                        ti += 1
                        if (int(o[0]), int(o[1])) not in reach[m] or (m, int(o[0]), int(o[1])) in NOTRAINER:
                            continue
                        objs.append(trainer_obj(m, o, o[6][4:], slot(o[2]), sight=sg))
                elif m == 'PalletTown':
                    pass
        for (gm, side, badge) in EDGE_GATES:
            if gm == m:
                for (x, y) in edge(m, side):
                    objs.append([slot('SPRITE_YOUNGSTER'), x, y, 0, {'E': 3, 'W': 4, 'S': 2}[side], nop,
                                 -B.FLAGS['BADGE%d' % badge], 0, 0])
        for (sm, x, y, d) in SURFERS:
            if sm == m:
                objs.append([slot('SPRITE_SEEL'), x, y, 0, d, nop, B.FLAGS['BADGE6'], 0, 0])
        for (gm, gmap, badge) in DOOR_GATES:
            if gm == m:
                for (x, y, dest, di) in inf['warps']:
                    if B.const_to_map(dest) == gmap:
                        objs.append([slot('SPRITE_COOLTRAINER_M'), x, y + 1, 0, 1, nop, -B.FLAGS['BADGE%d' % badge], 0, 0])
        # ---- warps
        if m in TOWNS + ROUTES:
            for (x, y, dest, di) in inf['warps']:
                dm = B.const_to_map(dest) or ''
                if dm.endswith('Pokecenter'):
                    warps.append((x, y, B.MAPID[CENTER], 3, 7))
                elif dm.endswith('Gym') and any(g[1] == dm for g in GYMS):
                    warps.append((x, y, B.MAPID[gyms[[g[1] for g in GYMS].index(dm)]], 4, 13))
                elif dm == 'RedsHouse1F':
                    warps.append((x, y, B.MAPID['RedsHouse2F'], 7, 1))
                elif dm == 'OaksLab':
                    warps.append((x, y, B.MAPID['OaksLab'], 5, 11))
                elif (m, x, y) in gate_warp:
                    warps.append((x, y, mid) + gate_warp[(m, x, y)])
            for cm, a, b in CAVES:
                if cm == m:
                    warps += [a + (mid,) + step_out(m, b), b + (mid,) + step_out(m, a)]
            for hm, a, b, badge in HOUSES:
                if hm == m:
                    warps += [a + (mid,) + step_out(m, b, (b[0], b[1] + 1)), b + (mid,) + step_out(m, a, (a[0], a[1] - 1))]
                    objs.append([slot('SPRITE_YOUNGSTER'), a[0], a[1] + 1, 0, 1, nop, -B.FLAGS['BADGE%d' % badge], 0, 0])
        elif m == 'RedsHouse2F':
            warps = [(7, 1, B.MAPID['PalletTown'], 5, 5)]
        elif m == 'OaksLab':
            warps = [(4, 11, B.MAPID['PalletTown'], 12, 11), (5, 11, B.MAPID['PalletTown'], 12, 11)]
        elif m == CENTER or m in gyms:
            warps = [(x, y, 0, 0, 0) for (x, y, d, i) in inf['warps']]
        # ---- triggers
        for t in cx.get('trig', []):
            x, y, cond, s = t
            cond = (-B.FLAGS[cond[1:]] if cond.startswith('!') else B.FLAGS[cond]) if cond else 0
            trig += [x, y, cond, B.script(s, cx.get('ctx'))]
        for (lm_, sq_, dm_, (ax, ay), *bg) in LINKS:
            if lm_ == m:
                s = B.script('w %d,%d,%d' % (B.MAPID[dm_], ax, ay))
                for (x, y) in sq_:
                    trig += [x, y, B.FLAGS['BADGE%d' % bg[0]] if bg else 0, s]
        for (fm, squares, dest, (dx, dy), badge) in FERRY:
            if fm == m:
                s = B.script('w %d,%d,%d' % (B.MAPID[dest], dx, dy))
                for (x, y) in squares:
                    trig += [x, y, B.FLAGS['BADGE%d' % badge] if badge else 0, s]
        dm, (dx, dy), dt, badge = DIGLETT or (None, (0, 0), None, 0)
        if m == dm:
            objs.append([slot('SPRITE_YOUNGSTER'), dx, dy + 1, 0, 1, nop, -B.FLAGS['BADGE%d' % badge], 0, 0])
            trig += [dx, dy, 0, B.script('w %d,%d,%d' % (B.MAPID[dt], cavedoor[0] - 1, cavedoor[1]))]
        if m == dt:
            trig += [cavedoor[0], cavedoor[1], 0, B.script('w %d,%d,%d' % (B.MAPID[dm], dx, dy + 1))]
        if m == E4GATE[0]:
            s = B.script('w %d,%d,%d' % (B.MAPID[e4[0]], *E4IN))
            for (x, y) in E4GATE[1]:
                trig += [x, y, B.FLAGS['BADGE%d' % E4GATE[2]], s]
        for i in range(0, len(trig), 4):  # every trigger must be standable, or it can never fire
            x, y = trig[i], trig[i + 1]
            bb = blocks(lm)[(y // 2) * inf['w'] + x // 2] if x != 255 else 0
            assert x == 255 or qflag(lm, skin.get(bb, bb), (y % 2) * 2 + x % 2) & 1, (m, 'trigger on a solid square', x, y)
        # ---- connections, wild
        conns = []
        for (d, dc, off) in inf['conns']:
            dm = B.const_to_map(dc)
            if dm in TOWNS + ROUTES:
                conns += [{'north': 2, 'south': 1, 'west': 3, 'east': 4}[d], B.MAPID[dm], off]
        wild = wild_res(B, m) if m in ROUTES else 0
        sprres = [B.sprite_res(s)[0] for s in sprites]
        B.WORLD[m] = dict(blocks=blocks(lm), w=inf['w'], h=inf['h'], ts=inf['ts'], pal=pal, conns=conns, objs=objs,
                          sprites=sprites)
        bank = 8 if m in TOWNS else 7 if m in ROUTES else 0  # music bank (build_misc); 0 = keep playing
        hdr = [inf['w'], inf['h'], gfx, flags, blkset, blk, bm[inf['border']], pal[1], pal[2], wild, bank]
        groups = [hdr, conns, sum((list(w) for w in warps), []), sum(objs, []), trig, sprres]
        assert sprres, (m, 'a map needs a sprite (split("") is {""} in pico-8)')
        B.res(100 + mid, b';'.join(B.nums(g) for g in groups))
        B.BINRES.add(100 + mid)
    stale = set(config.TRAINERS['trainers']) - placed
    if stale:
        raise SystemExit('config errors:\n  trainers.json: no trainer stands at ' + ', '.join(sorted(stale)))
    stale = set(config.WILD) - set(ROUTES)
    if stale:
        raise SystemExit('config errors:\n  wild.json: not a map in the game: ' + ', '.join(sorted(stale)))


def wild_res(B, m):
    """grass encounters from config wild.json: rate, then (level, species) x10"""
    w = config.WILD.get(m)
    if not w:
        return 0
    r = B.autores(B.nums([w['rate']] + [x for lv, sp in w['mons'] for x in (lv, B.DEX[sp])]))
    B.BINRES.add(r)
    return r
