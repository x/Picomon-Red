#!/usr/bin/env python3
"""Build the PICO-8 cart (cart/pokered.p8 and cart/pokered.p8.png) from the extracted ROM data (build/pokered),
data/, config/ and src/game.lua."""
import os, json, re, sys, functools
from PIL import Image
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'build', 'pokered')  # tools/extract.py output
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')  # game facts the build needs


def data(name):
    return json.load(open(os.path.join(DATA, name + '.json')))
import content

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.join(HERE, '..')
OUT = os.path.join(PROJ, 'cart')
os.makedirs(OUT, exist_ok=True)

# ------------------------------------------------------------- resources
RES = {}  # id -> bytes


GFX, ROMRES, BINRES = set(), set(), set()  # 4bpp images (stored as 2bpp on the cart), other resources kept in rom


class G(bytes):
    """marks 4bpp image data"""


def res(i, data):
    if isinstance(data, G):
        GFX.add(i)
    if isinstance(data, str):
        data = data.encode('latin-1')
    assert i not in RES, i
    assert len(data) <= 32767, (i, len(data))
    RES[i] = bytes(data)
    return i


_auto = [6000]


def nums(lst):
    """ints -> comma-separated text, read with split() by nums() in game.lua"""
    return ','.join(str(n) for n in lst).encode()


STS = ['PSN', 'BRN', 'PAR', 'SLP', 'FRZ']
_seen = {}


def autores(data):
    """new resource id, reusing an identical earlier resource"""
    if isinstance(data, str):
        data = data.encode('latin-1')
    key = (bytes(data), isinstance(data, G))
    if key not in _seen:
        _auto[0] += 1
        _seen[key] = res(_auto[0], data)
    return _seen[key]


# ------------------------------------------------------------- palettes
P8 = [(0, 0, 0), (29, 43, 83), (126, 37, 83), (0, 135, 81), (171, 82, 54), (95, 87, 79), (194, 195, 199),
      (255, 241, 232), (255, 0, 77), (255, 163, 0), (255, 236, 39), (0, 228, 54), (41, 173, 255), (131, 118, 156),
      (255, 119, 168), (255, 204, 170)]
P8X = [(0x29, 0x18, 0x14), (0x11, 0x1d, 0x35), (0x42, 0x21, 0x36), (0x12, 0x53, 0x59), (0x74, 0x2f, 0x29),
       (0x49, 0x33, 0x3b), (0xa2, 0x88, 0x79), (0xf3, 0xef, 0x7d), (0xbe, 0x12, 0x50), (0xff, 0x6c, 0x24),
       (0xa8, 0xe7, 0x2e), (0x00, 0xb5, 0x43), (0x06, 0x5a, 0xb5), (0x75, 0x46, 0x65), (0xff, 0x6e, 0x59),
       (0xff, 0x9d, 0x81)]
SGB = data('palettes')  # palette name -> 4 pico-8 colours

# ------------------------------------------------------------- gfx helpers


def shade(v):  # png gray -> gb shade 0(white)..3(black)
    return 3 - (v + 42) // 85


def img(path):
    im = Image.open(os.path.join(ROOT, path)).convert('L')
    w, h = im.size
    px = im.load()
    return [[shade(px[x, y]) for x in range(w)] for y in range(h)]


SEL12 = [int((i + .5) * 16 / 12) for i in range(12)]  # 16 -> 12 nearest: drops 1, 5, 9, 13
TRIM12 = [1 + int((i + .5) * 14 / 12) for i in range(12)]  # people: trim the outer columns, 14 -> 12 (symmetric)
SQOF = {}  # tileset -> {block: its 4 square ids}
GFXEDITS = {}  # config/gfx_edits.json from the editor: {"squares": {png: {"tl,tr,bl,br": [144]}}, "sprites": {...}}
for _p in ('config/gfx_edits.json',):
    if os.path.exists(os.path.join(PROJ, _p)):
        GFXEDITS = json.load(open(os.path.join(PROJ, _p)))


def shrink(rows, smooth=True):
    """16x16 frames (stacked) -> 12x12 from the middle 14 columns: smooth (person12) or plain nearest"""
    if not smooth:
        return [[rows[f * 16 + y][x] for x in TRIM12] for f in range(len(rows) // 16) for y in SEL12]
    return [r for f in range(len(rows) // 16) for r in person12(rows[f * 16:f * 16 + 16])]


def person12(rows, T=.625):
    """a 16x16 character frame -> 12x12 over source columns 1..14: Scale3x, then per output pixel a weighted vote
    over its window (black weighted up a little); a colour covering >= T of it wins, else the window's centre"""
    big = scale3x(rows)
    out = []
    for oy in range(12):
        row = []
        for ox in range(12):
            a, b = (1 + ox * 14 / 12) * 3, (1 + (ox + 1) * 14 / 12) * 3
            c = [0.0] * 4
            for y in range(oy * 4, oy * 4 + 4):
                for x in range(int(a), int(b + .999)):
                    c[big[y][x]] += max(0, min(b, x + 1) - max(a, x))
            c[3] += .5
            m = max(c)
            row.append(max(k for k in range(4) if c[k] == m) if m >= T * (b - a) * 4 else big[oy * 4 + 2][int((a + b) / 2)])
        out.append(row)
    return out


def pack4(rows):
    """pixel rows -> pico-8 4bpp bytes (low nibble = left pixel)"""
    out = bytearray()
    for r in rows:
        for x in range(0, len(r), 2):
            out.append(r[x] | (r[x + 1] << 4))
    return G(out)


def pad_pic(rows, size=56):
    """bottom-center a pic in a size x size box (like the GB does)"""
    h, w = len(rows), len(rows[0])
    ox = (size - w) // 2 + ((size - w) // 2) % 1
    ox = ((size // 8 - w // 8) + 1) // 2 * 8
    oy = size - h
    out = [[0] * size for _ in range(size)]
    for y in range(h):
        for x in range(w):
            out[oy + y][ox + x] = rows[y][x]
    return out


# ------------------------------------------------------------- text encoding
CHR = {'é': 'e', '♂': 'M', '♀': 'F', '¥': '$', '×': 'x', '…': '.', '▶': '>', '▼': '\x83',
       '“': '"', '”': '"', '‘': "'", '’': "'", '&': '+', '%': '%'}
TAGS = {'<PLAYER>': 'RED', '<RIVAL>': 'BLUE', '<PKMN>': 'PKMN', '<……>': '..', '<PC>': 'PC',
        '<TM>': 'TM', '<TRAINER>': 'TRAINER', '<ROCKET>': 'ROCKET', '#': 'POKe', '<USER>': '\x03',
        '<TARGET>': '\x03', '<LV>': 'L', '<DOT>': '.', '<ED>': 'ED', '<COLON>': ':'}


def enc(s):
    s = s.split('@')[0]
    for k, v in TAGS.items():
        s = s.replace(k, v)
    out = ''
    for ch in s:
        out += CHR.get(ch, ch)
    for ch in out:
        if ord(ch) > 0x88 or (ord(ch) >= 0x7f and ord(ch) < 0x80):
            print('warn: odd char', repr(ch), repr(s))
    return out.lower()  # lowercase codes draw as normal capitals in the default font


TEXTID = {}
_tid = [1000]


MUSICSTART = []  # first pattern of each song in the music bank (res 7)
CUSTOMBST = {}  # blockset name -> extra 16-byte blocks appended after its own (world.py)
WORLD = {}  # map -> final blocks/conns, filled by world.build_maps (for tools/worldmap.py)


def text(label_or_str):
    """dialogue is left out for room: every text is the same empty string (script 't' ops on it are dropped)"""
    if '' not in TEXTID:
        _tid[0] += 1
        TEXTID[''] = res(_tid[0], '')
    return TEXTID['']


# ------------------------------------------------------------- constants
POKEDATA = data('pokemon')  # all 151: dex number, name, palette, types, stats, default learnset
DEX = {n: p['dex'] for n, p in POKEDATA.items()}

# ------------------------------------------------------------- species
import config, rpp
SPECIES = list(config.POKEMON)


def species_file(name):
    m = {'NIDORAN_F': 'nidoranf', 'NIDORAN_M': 'nidoranm', 'MR_MIME': 'mrmime', 'FARFETCHD': 'farfetchd'}
    return m.get(name, name.lower())


PALNAMES = {n: p['pal'] for n, p in POKEDATA.items()}

MOVEC = rpp.MOVEID  # move ids are Red++ ids from here on
SP = {}
for name in SPECIES:
    st = rpp.STATS[name]
    ev = config.POKEMON[name].get('evolves')
    SP[name] = dict(dex=DEX[name], stats=st['stats'], types=st['types'], catch=st['catch'], bexp=st['bexp'],
                    growth=st['growth'], evl=ev[1] if ev else 0, evt=DEX[ev[0]] if ev else 0,
                    learn=[tuple(x) for x in config.POKEMON[name]['learnset']])

# ------------------------------------------------------------- moves
STAT = {'ATTACK': 1, 'DEFENSE': 2, 'SPEED': 3, 'SPECIAL': 4, 'ACCURACY': 5, 'EVASION': 6}


def move_effect(e):
    """pokered effect -> (kind,p1,p2,chance) -- see game.lua 'effects'"""
    m = re.match(r'(ATTACK|DEFENSE|SPEED|SPECIAL|ACCURACY|EVASION)_(UP|DOWN)(1|2)_EFFECT', e)
    if m:
        d = int(m.group(3)) * (1 if m.group(2) == 'UP' else -1)
        return (2 if d > 0 else 1, STAT[m.group(1)], d, 100)
    m = re.match(r'(ATTACK|DEFENSE|SPEED|SPECIAL|ACCURACY)_DOWN_SIDE_EFFECT', e)
    if m:
        return (1, STAT[m.group(1)], -1, 33)
    table = {
        'POISON_SIDE_EFFECT1': (3, 'PSN', 0, 20), 'POISON_SIDE_EFFECT2': (3, 'PSN', 0, 40),
        'BURN_SIDE_EFFECT1': (3, 'BRN', 0, 10), 'BURN_SIDE_EFFECT2': (3, 'BRN', 0, 30),
        'PARALYZE_SIDE_EFFECT1': (3, 'PAR', 0, 10), 'PARALYZE_SIDE_EFFECT2': (3, 'PAR', 0, 30),
        'FREEZE_SIDE_EFFECT': (3, 'FRZ', 0, 10), 'FREEZE_SIDE_EFFECT2': (3, 'FRZ', 0, 30),
        'FIRE_FANG_EFFECT': (3, 'BRN', 0, 10), 'ICE_FANG_EFFECT': (3, 'FRZ', 0, 10),
        'THUNDER_FANG_EFFECT': (3, 'PAR', 0, 10), 'POISON_FANG_EFFECT': (3, 'PSN', 0, 30),
        'SWIFT_EFFECT': (16, 0, 0, 0), 'HYPER_BEAM_EFFECT': (17, 0, 0, 0),
        'POISON_EFFECT': (3, 'PSN', 0, 100), 'PARALYZE_EFFECT': (3, 'PAR', 0, 100),
        'SLEEP_EFFECT': (3, 'SLP', 0, 100),
        'CONFUSION_SIDE_EFFECT': (4, 0, 0, 10), 'CONFUSION_EFFECT': (4, 0, 0, 100),
        'FLINCH_SIDE_EFFECT1': (5, 0, 0, 10), 'FLINCH_SIDE_EFFECT2': (5, 0, 0, 30),
        # multi-hit, drain and recoil are plain hits (multi-hit power is scaled up in build_tables)
        'LEECH_SEED_EFFECT': (7, 0, 0, 0),
        'BIDE_EFFECT': (11, 0, 0, 0), 'SWITCH_AND_TELEPORT_EFFECT': (12, 0, 0, 0),
        'FOCUS_ENERGY_EFFECT': (13, 0, 0, 0), 'SPECIAL_DAMAGE_EFFECT': (19, 0, 0, 0),
    }
    return table.get(e, (0, 0, 0, 0))


HIGHCRIT = {'KARATE_CHOP', 'RAZOR_LEAF', 'CRABHAMMER', 'SLASH', 'CROSS_CHOP'}

# ------------------------------------------------------------- items
ITEMS = [  # name, label, price, kind, param, shown from badge, hidden from badge   (kind: 1 ball 2 heal 3 cure)
    ('POKE_BALL', 'BALL', 200, 1, 12, 0, 0), ('POTION', 'POTION', 300, 2, 20, 0, 3),
    ('SUPER_POTION', 'SUPER POTION', 700, 2, 50, 3, 6), ('MAX_POTION', 'MAX POTION', 2500, 2, 999, 6, 0),
    ('ANTIDOTE', 'ANTIDOTE', 100, 3, 'PSN', 0, 0), ('PARLYZ_HEAL', 'PARLYZ HEAL', 200, 3, 'PAR', 0, 0),
    ('BURN_HEAL', 'BURN HEAL', 250, 3, 'BRN', 0, 0), ('AWAKENING', 'AWAKENING', 200, 3, 'SLP', 0, 0),
]
ITEMID = {k: i + 1 for i, (k, *_) in enumerate(ITEMS)}

# ------------------------------------------------------------- trainers
PICRES = {}


def scale2x(r):
    """EPX / Scale2x (RotSprite's upscaler): 2x, rounding diagonal edges"""
    h, w = len(r), len(r[0])
    g = lambda y, x: r[min(max(y, 0), h - 1)][min(max(x, 0), w - 1)]
    o = [[0] * (2 * w) for _ in range(2 * h)]
    for y in range(h):
        for x in range(w):
            p, a, b, c, d = g(y, x), g(y - 1, x), g(y, x + 1), g(y, x - 1), g(y + 1, x)
            o[2 * y][2 * x] = a if c == a and c != d and a != b else p
            o[2 * y][2 * x + 1] = b if a == b and a != c and b != d else p
            o[2 * y + 1][2 * x] = c if d == c and d != b and c != a else p
            o[2 * y + 1][2 * x + 1] = d if b == d and b != a and d != c else p
    return o


PICK = 1.3  # contrast boost when snapping a smoothed pic back to the 4 shades


def halve_smooth(rows):
    """RotSprite-style halving: Scale2x three times (8x), area-average down to half size, push the shade away
    from mid-grey by PICK, snap to the 4 shades"""
    for _ in range(3):
        rows = scale2x(rows)
    h, w = len(rows) // 16, len(rows[0]) // 16
    im = Image.new('L', (w * 16, h * 16))
    im.putdata([c * 85 for r in rows for c in r])
    im = im.resize((w, h), Image.BOX)
    return [[min(3, max(0, int(1.5 + (im.getpixel((x, y)) / 85 - 1.5) * PICK + .5))) for x in range(w)] for y in range(h)]


def scale3x(r):
    """Scale3x / AdvMAME3x: 3x, rounding diagonal edges"""
    h, w = len(r), len(r[0])
    g = lambda y, x: r[min(max(y, 0), h - 1)][min(max(x, 0), w - 1)]
    o = [[0] * (3 * w) for _ in range(3 * h)]
    for y in range(h):
        for x in range(w):
            A, B, C, D, E, F, G_, H, I = [g(y + dy, x + dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1)]
            db, bf = D == B and D != H and B != F, B == F and B != D and F != H
            dh, hf = D == H and D != B and H != F, H == F and D != H and B != F
            e = [D if db else E, B if (db and E != C) or (bf and E != A) else E, F if bf else E,
                 D if (db and E != G_) or (dh and E != A) else E, E, F if (bf and E != I) or (hf and E != C) else E,
                 D if dh else E, H if (dh and E != I) or (hf and E != G_) else E, F if hf else E]
            for k in range(9):
                o[3 * y + k // 3][3 * x + k % 3] = e[k]
    return o


def square12(rows, w=.5, T=10):
    """a 16x16 overworld square -> 12x12. Scale3x to 48, then per 4x4 block: a colour filling >= T of it
    (black weighted +2) or else the block's centre sample. Kept only if it changes the square's balance of
    shades (vs the original, weighted by w) plus its pixel error no more than plain nearest (SEL12) does."""
    big = scale3x(rows)

    def pick(p):
        c = [p.count(k) + 2 * (k == 3) for k in range(4)]
        return max(k for k in range(4) if c[k] == max(c)) if max(c) >= T else p[5]  # ties -> darker
    hyb = [[pick([big[4 * y + j][4 * x + i] for j in range(4) for i in range(4)]) for x in range(12)] for y in range(12)]
    near = [[rows[y][x] for x in SEL12] for y in SEL12]
    hist = lambda r: [sum(row.count(k) for row in r) / (len(r) * len(r[0])) for k in range(4)]
    ho = hist(rows)
    score = lambda c: (sum(big[y][x] != c[y // 4][x // 4] for y in range(48) for x in range(48)) / 2304
                       + w * sum(abs(a - b) for a, b in zip(hist(c), ho)))
    return hyb if score(hyb) <= score(near) else near


def pic_res(path, size=56):
    """pokemon/trainer pic: padded to 56x56, then halved (smoothly, see halve_smooth) to 28x28, drawn at 2x"""
    if path not in PICRES:
        PICRES[path] = autores(pack4(halve_smooth(pad_pic(img(path), size))))
    return PICRES[path]


def moves_at(name, lv):
    ms = []
    for l, m in SP[name]['learn']:
        if l <= lv and m not in ms:
            ms.append(m)
    return ms[-4:]


def party_res(idx):
    """story trainer battle (the lab rival): pic, then (level, species, 4 moves)..."""
    mons = config.TRAINERS['rival'][idx]
    f = [pic_res('gfx/trainers/rival1.png')]
    for lv, sp in mons:
        ms = moves_at(sp, lv)
        f += [lv, DEX[sp]] + [MOVEC[m] for m in ms] + [0] * (4 - len(ms))
        TRAINERMOVES.update(ms)
    r = autores(nums(f))
    BINRES.add(r)
    return r


# ------------------------------------------------------------- tilesets
TSNAMES = {'OVERWORLD': 'overworld', 'REDS_HOUSE_1': 'reds_house', 'REDS_HOUSE_2': 'reds_house', 'MART': 'pokecenter',
           'POKECENTER': 'pokecenter', 'FOREST': 'forest', 'DOJO': 'gym', 'GYM': 'gym', 'HOUSE': 'house',
           'FOREST_GATE': 'gate', 'MUSEUM': 'gate', 'GATE': 'gate', 'LAB': 'lab'}
TILESETS = data('tilesets')
TSCOLL, TSHEAD = TILESETS['collision'], TILESETS['headers']
CAMEL = {'OVERWORLD': 'Overworld', 'REDS_HOUSE_1': 'RedsHouse1', 'REDS_HOUSE_2': 'RedsHouse2', 'MART': 'Mart',
         'POKECENTER': 'Pokecenter', 'FOREST': 'Forest', 'DOJO': 'Dojo', 'GYM': 'Gym', 'HOUSE': 'House',
         'FOREST_GATE': 'ForestGate', 'MUSEUM': 'Museum', 'GATE': 'Gate', 'LAB': 'Lab'}
WARPTILES = {'OVERWORLD': [0x1b, 0x58], 'FOREST_GATE': [0x3b, 0x1a, 0x1c], 'MUSEUM': [0x3b, 0x1a, 0x1c],
             'GATE': [0x3b, 0x1a, 0x1c], 'REDS_HOUSE_1': [0x1a, 0x1c], 'REDS_HOUSE_2': [0x1a, 0x1c],
             'MART': [0x5e], 'POKECENTER': [0x5e], 'FOREST': [0x5a, 0x5c, 0x3a], 'DOJO': [0x4a], 'GYM': [],
             'HOUSE': [0x54, 0x5c, 0x32], 'LAB': []}
DOORTILES = {'OVERWORLD': [0x1b, 0x58], 'FOREST': [0x3a]}
LEDGES = {0x37: 0x10, 0x36: 0x10, 0x27: 0x20, 0x0d: 0x40, 0x1d: 0x40}
TSRES = {}


@functools.lru_cache(None)
def tileset_bst(png):
    """blockset bytes as the game uses them: the .bst + custom blocks, bushes as trees, no bedroom windows"""
    bst = open(os.path.join(ROOT, 'gfx/blocksets/%s.bst' % png), 'rb').read() + CUSTOMBST.get(png, b'')
    if png == 'overworld':  # uncuttable bushes (Route 2, Cerulean) drawn as ordinary trees
        bst = bytes({0x2d: 0x40, 0x2e: 0x41, 0x3d: 0x50, 0x3e: 0x51}.get(x, x) for x in bst)
    if png == 'reds_house':  # bedroom windows -> plain wall
        bst = bytes(0 if x in (0x24, 0x25, 0x34, 0x35) else x for x in bst)
    return bst


def block_keys(png, b, bst=None):
    """a block's 4 squares (tl, tr, bl, br) as keys: "t0,t1,t2,t3" (its 2x2 tiles) or "new:..." (drawn in the
    editor). gfx_edits.json "blocks" can recompose a block or define a new block id."""
    ov = GFXEDITS.get('blocks', {}).get(png, {}).get(str(b))
    if ov:
        return list(ov)
    bst = bst or tileset_bst(png)
    return [','.join(str(bst[b * 16 + (r * 2 + rr) * 4 + c * 2 + cc]) for rr in (0, 1) for cc in (0, 1))
            for r in (0, 1) for c in (0, 1)]


@functools.lru_cache(None)
def tile_flags(ts):
    """per tile: 1 walkable, 2 tall grass, 4 warp, 8 door, 16/32/64 ledge down/left/right, 128 counter"""
    fl = bytearray(256)
    for t in TSCOLL[CAMEL[ts]]:
        fl[t] |= 1
    h = TSHEAD[CAMEL[ts]]
    if h['grass'] >= 0:
        fl[h['grass']] |= 2
    for t in WARPTILES.get(ts, []):
        fl[t] |= 4
    for t in DOORTILES.get(ts, []):
        fl[t] |= 8
    if ts == 'OVERWORLD':
        for t, b in LEDGES.items():
            fl[t] |= b
    for t in h['counters']:
        fl[t] |= 0x80
    return fl


def square_flags(ts, key):
    """a square's flags: from its bottom-left tile, or set by hand (gfx_edits.json "flags")"""
    ov = GFXEDITS.get('flags', {}).get(TSNAMES[ts], {}).get(key)
    if ov is not None:
        return ov
    return 1 if key.startswith('new:') else tile_flags(ts)[int(key.split(',')[2])]


def tileset_res(ts):
    if ts in TSRES:
        return TSRES[ts]
    png = TSNAMES[ts]
    bst = tileset_bst(png)
    blocks = sorted(USEDBLK[png])
    BLKMAP[ts] = {b: i for i, b in enumerate(blocks)}
    # the overworld is drawn in 12x12 squares: a square = 2x2 tiles (16x16) shrunk with nearest-neighbour;
    # a block = 2x2 squares. Flags per square come from its bottom-left tile (or gfx_edits.json).
    src = img('gfx/tilesets/%s.png' % png)
    px = lambda t, x, y: src[t // 16 * 8 + y][t % 16 * 8 + x] if t // 16 * 8 + y < len(src) else 0
    sq, bmap = {}, bytearray()
    for b in blocks:
        for key in block_keys(png, b, bst):
            bmap.append(sq.setdefault(key, len(sq)))
    SQOF[ts] = {b: tuple(bmap[i * 4:i * 4 + 4]) for i, b in enumerate(blocks)}
    rows = []
    edits = GFXEDITS.get('squares', {}).get(png, {})
    for key in sq:
        e = edits.get(key)  # hand-drawn in the editor (gfx_edits.json)
        assert e or not key.startswith('new:'), ('square has no pixels', png, key)
        t = None if e else [int(v) for v in key.split(',')]
        sq12 = square12([[px(t[(y // 8) * 2 + x // 8], x % 8, y % 8) for x in range(16)] for y in range(16)]) if not e else None
        for i in range(12):
            rows.append(e[i * 12:i * 12 + 12] if e else sq12[i])
    gfx = autores(pack4(rows))
    flags = autores(bytes(square_flags(ts, key) for key in sq))
    blk = autores(bytes(bmap))
    ROMRES.add(blk)
    TSRES[ts] = (gfx, flags, blk, len(sq))
    return TSRES[ts]


# ------------------------------------------------------------- overworld sprites
SPRRES = {}


def sprite_res(spconst):
    if spconst not in SPRRES:
        name = spconst[7:].lower()
        rows = img('gfx/sprites/%s.png' % name)
        if spconst == 'SPRITE_SEEL':  # only ever seen sitting still: one frame
            rows = rows[:16]
        small = shrink(rows)
        for f, e in GFXEDITS.get('sprites', {}).get(spconst, {}).items():  # hand-drawn frames (gfx_edits.json)
            small[int(f) * 12:int(f) * 12 + 12] = [e[i * 12:i * 12 + 12] for i in range(12)]
        SPRRES[spconst] = (autores(pack4(small)), len(rows) // 16)
    return SPRRES[spconst]


# ------------------------------------------------------------- maps
MAPS = ['PalletTown', 'RedsHouse1F', 'RedsHouse2F', 'BluesHouse', 'OaksLab', 'Route1', 'ViridianCity',
        'ViridianPokecenter', 'ViridianMart', 'ViridianSchoolHouse', 'ViridianNicknameHouse', 'Route22',
        'Route2', 'ViridianForestSouthGate', 'ViridianForest', 'ViridianForestNorthGate', 'PewterCity',
        'PewterGym', 'PewterPokecenter', 'PewterMart', 'PewterNidoranHouse', 'PewterSpeechHouse']
MAPID = {m: i + 1 for i, m in enumerate(MAPS)}


MAPDATA = data('maps')  # the maps the game uses: header, objects, text pointers, trainer headers
CONST2MAP = MAPDATA['consts']


def const_to_map(c):
    return CONST2MAP.get(c)


MAPINFO = {}


def load_mapinfo(m):
    if m not in MAPINFO:  # a copy: world.py adjusts sizes and borders
        MAPINFO[m] = json.loads(json.dumps({k: v for k, v in MAPDATA['maps'][m].items() if k not in ('texts', 'trainers')}))
    return MAPINFO[m]


# ------------------------------------------------------------- script compiler
FLAGS = content.FLAGS
_sid = [3000]
SCRIPTS = {}


def compile_script(src, ctx):
    """content DSL -> 'op,a,b;op,...' . lines; labels end with ':'"""
    cmds, labels = [], {}
    for raw in src.strip().split('\n'):
        l = raw.strip()
        if not l or l.startswith('--'):
            continue
        if l.endswith(':'):
            labels[l[:-1]] = len(cmds) + 1
            continue
        op, *a = [x.strip() for x in re.split(r'\s+', l, maxsplit=1)[0:1]] + (
            [x.strip() for x in re.split(r'\s+', l, maxsplit=1)[1].split(',')] if ' ' in l else [])
        for k, v in enumerate(a):
            if v.startswith('=') or v.startswith('~='):
                a = a[:k] + [','.join(a[k:])]
                break
        c = [op] + [ctx_value(x, ctx) for x in a]
        if op in 'vu' or op == 't' and not RES.get(c[1], b'x'):  # species names / music / cut dialogue
            continue
        cmds.append(c)
    for c in cmds:  # sugar: g/x/c compile to j/s
        if c[0] == 'g':
            c[:] = ['j', 0, c[1]]
        elif c[0] == 'x':
            c[:] = ['j', 0, 999]
        elif c[0] == 'c':
            c[:] = ['s', -c[1]]
    for c in cmds:
        for i in range(1, len(c)):
            if isinstance(c[i], str) and c[i].startswith('@'):
                c[i] = labels[c[i][1:]]
    return ';'.join(','.join([c[0]] + [str(v) for v in c[1:]]) for c in cmds).encode()  # split() in runs()


DIRS = {'down': 1, 'up': 2, 'left': 3, 'right': 4, 'player': 5}


def ctx_value(x, ctx):
    if x.startswith('@'):
        return x
    if x[:1] in '_=~':
        return text(x)
    if x in FLAGS:
        return FLAGS[x]
    if x.startswith('!') and x[1:] in FLAGS:
        return -FLAGS[x[1:]]
    if x in DIRS:
        return DIRS[x]
    if x in ITEMID:
        return ITEMID[x]
    if x in DEX:
        return DEX[x]
    if x in MAPID:
        return MAPID[x]
    if x.startswith('party:'):
        p = x[6:].split('/')
        return party_res(int(p[1]))
    if x in ctx:
        return ctx[x]
    return int(x)


def script(src, ctx=None):
    s = compile_script(src, ctx or {})
    if s in SCRIPTS:
        return SCRIPTS[s]
    _sid[0] += 1
    SCRIPTS[s] = res(_sid[0], s)
    BINRES.add(_sid[0])
    return _sid[0]


# ------------------------------------------------------------- build maps




USEDBLK, BLKMAP = {}, {}


# ------------------------------------------------------------- font


# ------------------------------------------------------------- tables
TRAINERMOVES, OWNABLE = set(), set()  # moves trainers use (filled by world.py); species you can own


def build_tables():
    # ownable: the starters, wild species and everything they evolve into
    OWNABLE.update(config.ownable())
    fought = config.fought()
    # species: numbers in 1, names in 16 (same field positions as before, name at [2])
    ents, names = [], []
    for name in SPECIES:
        s = SP[name]
        f = species_file(name)
        front = pic_res('gfx/pokemon/front/%s.png' % f) if name in fought else 0
        back = autores(pack4([r[::2] for r in img('gfx/pokemon/back/%sb.png' % f)[::2]])) if name in OWNABLE else 0
        pal = SGB[PALNAMES[name]]
        learn = []
        for lv, m in (s['learn'] if name in OWNABLE else []):  # trainer-only species get their moves passed in
            learn += [lv, MOVEC[m]]
        e = [s['dex']] + s['types'] + s['stats'] + [s['catch'], s['bexp'], s['growth'], s['evl'], s['evt'], front, back,
                                                     pal[1], pal[2]] + learn
        ents.append(nums(e))
        names.append(NAMES[name])
    res(1, b';'.join(ents))  # tab() in game.lua
    res(16, '|'.join(names))
    # moves: numbers in 2, names in 17
    ents, names = [], []
    used = TRAINERMOVES | {m for n in OWNABLE for _, m in SP[n]['learn']}
    for m in sorted(used, key=lambda k: MOVEC[k]):
        mv = rpp.MOVES[MOVEC[m]]
        k, p1, p2, ch = move_effect(mv['eff'])
        if m in HIGHCRIT:
            k = 10
        if m == 'QUICK_ATTACK':
            k = 15
        if k == 3:
            p1 = STS.index(p1) + 1
        pw = mv['pow'] * {'TWO_TO_FIVE_ATTACKS_EFFECT': 3, 'ATTACK_TWICE_EFFECT': 2, 'TWINEEDLE_EFFECT': 2}.get(mv['eff'], 1)
        e = [mv['id'], pw, mv['type'], mv['acc'], mv['pp'], k, p1, p2, ch, mv['cat']]
        ents.append(nums(e))
        names.append(enc(mv['name'].upper()))
    res(2, b';'.join(ents))  # tab() in game.lua
    res(17, '|'.join(names))
    # items
    ents = []
    for i, (_, n, p, k, prm, show, hide) in enumerate(ITEMS):
        e = [i + 1, k, STS.index(prm) + 1 if isinstance(prm, str) else prm,
             FLAGS['BADGE%d' % show] if show else 0, FLAGS['BADGE%d' % hide] if hide else 0]
        ents.append(nums(e))
    res(3, b';'.join(ents))  # tab() in game.lua
    res(18, '|'.join(enc(n) for _, n, *_ in ITEMS))
    # type chart (Red++: adds STEEL, DARK, FAIRY)
    tc = []
    mtypes = {rpp.MOVES[MOVEC[m]]['type'] for m in used}
    stypes = {t for n in SPECIES for t in SP[n]['types']}
    for at, de, mult in rpp.TYPECHART:
        if at in mtypes and de in stypes:  # rows that can never apply are left out
            tc += [at, de, mult]
    names = [''] * 29
    for k, v in rpp.TYPES.items():
        if v < 29 and k != 'UNK_TYPE':
            names[v] = k.lower()
    res(4, nums(tc))
    res(14, ','.join(names))


NAMES = {}


def load_names():
    for n, p in POKEDATA.items():
        NAMES[n] = enc(p['name'])


# ------------------------------------------------------------- misc gfx

def build_misc():
    # sheet A rows 48..63: shock emote(16x16), balls icons (32x8), font_battle_extra (HP bar bits) not needed
    res(6, pack4(shrink(img('gfx/emotes/shock.png'), False)))
    pass  # (system texts are gone with the dialogue)


    res(13, nums(SGB['PAL_MEWMON']))
    import music
    # two banks swapped in by map (header field 11): battle first in both, so both songs start at the same pattern.
    # 7: the title theme (title screen, routes); 8: the city theme (towns). Title: intro + one 384-row section (loops)
    b, starts = music.bank(['wildbattle', 'titlescreen'], ROOT, maxrows={'titlescreen': 492})
    b2, starts2 = music.bank(['wildbattle', 'cities1'], ROOT)
    assert starts == starts2, (starts, starts2)
    res(7, b)
    res(8, b2)
    MUSICSTART[:] = starts


# ------------------------------------------------------------- cart writing
def p8_sections(data):
    """0x4300 bytes of rom -> .p8 __gfx__/__gff__/__map__/__sfx__/__music__ text"""
    d = bytearray(data) + bytearray(0x4300 - len(data))
    out = []
    gfx = []
    for y in range(128):
        row = d[y * 64:(y + 1) * 64]
        gfx.append(''.join('%x%x' % (b & 15, b >> 4) for b in row))
    out.append('__gfx__\n' + '\n'.join(gfx))
    out.append('__gff__\n' + '\n'.join(d[0x3000 + i * 128:0x3000 + (i + 1) * 128].hex() for i in range(2)))
    out.append('__map__\n' + '\n'.join(d[0x2000 + i * 128:0x2000 + (i + 1) * 128].hex() for i in range(32)))
    sfx = []
    for i in range(64):
        b = d[0x3200 + i * 68:0x3200 + (i + 1) * 68]
        hdr = '%02x%02x%02x%02x' % (b[64], b[65], b[66], b[67])
        notes = ''
        for n in range(32):
            v = b[n * 2] | (b[n * 2 + 1] << 8)
            pitch = v & 63
            inst = (v >> 6) & 7
            vol = (v >> 9) & 7
            eff = (v >> 12) & 7
            custom = (v >> 15) & 1
            notes += '%02x%x%x%x' % (pitch, inst | (custom << 3), vol, eff)
        sfx.append(hdr + notes)
    out.append('__sfx__\n' + '\n'.join(sfx))
    mus = []
    for i in range(64):
        b = d[0x3100 + i * 4:0x3100 + i * 4 + 4]
        flags = ((b[0] >> 7) & 1) | (((b[1] >> 7) & 1) << 1) | (((b[2] >> 7) & 1) << 2) | (((b[3] >> 7) & 1) << 3)
        mus.append('%02x %s' % (flags, ''.join('%02x' % (x & 0x7f) for x in b)))
    out.append('__music__\n' + '\n'.join(mus))
    return '\n'.join(out)


# ------------------------------------------------------------- single cart


def to2bpp(b):
    """4bpp pixel bytes (values 0..3) -> 4 pixels per byte"""
    out = bytearray()
    for k in range(0, len(b), 2):
        out.append((b[k] & 3) | (b[k] >> 4 & 3) << 2 | (b[k + 1] & 3) << 4 | (b[k + 1] >> 4 & 3) << 6)
    return bytes(out)


CSALPHA = [chr(c) for c in range(32, 127) if c not in (34, 92)] + [chr(c) for c in range(128, 256)]  # 221
ROMDATA = 0x3200 + 57 * 68  # rom bytes for data; sfx 57..63 (the sound effects) stay


def csenc(b):
    """bytes -> 2 chars per 15 bits (high digit first), decoded at the top of game.lua"""
    bits = ''.join(format(x, '08b') for x in b)
    bits += '0' * (-len(bits) % 15)
    out = []
    for i in range(0, len(bits), 15):
        v = int(bits[i:i + 15], 2)
        out += [CSALPHA[v // 221], CSALPHA[v % 221]]
    return ''.join(out)


def testcode(code):
    """the real-pico-8 test cart: drop '-- notest{ ... -- notest}' regions, enable '-- test: ' lines"""
    code = re.sub(r'-- notest\{.*?-- notest\}\n', '', code, flags=re.S)
    return re.sub(r'(?m)^-- test: ', '', code)


RENAME = ('say dirto fade side bst hurt stats sendp hpto warp lgfx emote runs stage inflict box cdir appr trig bagm dspr '
          'fpic pmenu pmove nextp fight free hpb hud tab ldq lrn conf act yn ex dp cp np oob dr pb pm ld grp').split()


def rename(code):
    """shorten our own function names (not fields, strings or names the tests use) to free 1-2 letter names"""
    parts = re.split(r'("(?:[^"\\\n]|\\.)*")', code)
    body = ''.join(p for i, p in enumerate(parts) if i % 2 == 0)
    used = set(re.findall(r'[A-Za-z_]\w*', body))
    names = [n for n in RENAME if re.search(r'(?<![\w.:])%s\b' % n, body)]
    names.sort(key=lambda n: -len(re.findall(r'(?<![\w.:])%s\b' % n, body)) * len(n))
    free = [c for c in [chr(x) for x in range(65, 91)] + [a + b for a in 'abcdefghijklmnopqrstuvwxyz'
                                                           for b in 'abcdefghijklmnopqrstuvwxyz0123456789']
            if c not in used and c not in ('do', 'if', 'in', 'or')]
    table = dict(zip(names, free))
    for i in range(0, len(parts), 2):
        parts[i] = re.sub(r'(?<![\w.:])([A-Za-z_]\w*)\b', lambda m: table.get(m.group(1), m.group(1)), parts[i])
    return ''.join(parts)


def minify(code):
    """drop comments, indentation and blank lines (strings never contain '--' here)"""
    out = []
    for l in code.split('\n'):
        i = l.find('--')
        if i >= 0 and l[:i].count('"') % 2 == 0:
            l = l[:i]
        l = l.strip()
        if l:
            out.append(l)
    return '\n'.join(out)


P8SCII = {int(k): bytes.fromhex(v) for k, v in json.load(open(os.path.join(HERE, 'p8scii.json'))).items()}


def p8text(s):
    """.p8 files are utf-8: chars 128..255 are written as pico-8's own glyphs (tools/p8scii.json, captured
    from printh), never as raw bytes that could pair up into a different utf-8 character"""
    return b''.join(P8SCII[ord(c)] if ord(c) >= 128 else c.encode('latin-1') for c in s)


def write_single(code_lua):
    import lzr
    tp = pic_res('gfx/title/player.png')  # title red
    order = ','.join(str(DEX[n]) for n in SPECIES if n in config.fought())  # title screen picks from these
    ids = [i for i in sorted(RES) if not 200 <= i < 300]
    streams = b''
    other, parts = [i for i in ids if i not in GFX], [[i for i in ids if i in GFX], []]
    for i in other:  # pico-8 numbers stop at 32767: no decoded stream may be longer
        if sum(len(RES[j]) + 4 for j in parts[-1]) + len(RES[i]) + 4 + 2 > 32000:
            parts.append([])
        parts[-1].append(i)
    for part in parts:
        d = bytearray(len(part).to_bytes(2, 'little'))
        for i in part:
            d += i.to_bytes(2, 'little') + len(RES[i]).to_bytes(2, 'little') if i not in GFX else \
                i.to_bytes(2, 'little') + len(to2bpp(RES[i])).to_bytes(2, 'little')
        d += b''.join(to2bpp(RES[i]) if i in GFX else RES[i] for i in part)
        assert len(d) < 32768, ('stream too long for pico-8 numbers', len(d))
        c = lzr.compress_best(bytes(d))  # adaptive rANS, optimal parse (checks its own decode)
        streams += c
    sfx = open(os.path.join(HERE, 'sfx.bin'), 'rb').read()
    rom = bytearray(0x4300)
    rom[ROMDATA:0x3200 + 64 * 68] = sfx[0x100 + 57 * 68:0x100 + 64 * 68]
    rom[:min(len(streams), ROMDATA)] = streams[:ROMDATA]
    cs = csenc(streams[ROMDATA:])
    with open(os.path.join(PROJ, 'tests', 'mapids.lua'), 'w') as f:
        f.write('return {%s}\n' % ','.join('%s=%d' % kv for kv in MAPID.items()) + '-- flags\n')
    with open(os.path.join(PROJ, 'tests', 'flags.lua'), 'w') as f:
        f.write('return {%s}\n' % ','.join('%s=%d' % (k, v) for k, v in FLAGS.items() if re.match(r'^[A-Z_][A-Z0-9_]*$', k)))
    code = '-- picomon red\n-- a red demake\n' + rename(minify(code_lua)).replace('$START', str(MAPID['RedsHouse2F'])).replace('$TP', str(tp)).replace('$NS', str(len(parts))).replace('$TO', order).replace('$AM', str(MUSICSTART[1])).replace('$DATA', cs)
    import label
    with open(os.path.join(OUT, 'pokered.p8'), 'wb') as f:
        f.write(p8text('pico-8 cartridge // http://www.pico-8.com\nversion 42\n__lua__\n' + code + '\n' + p8_sections(rom) +
                       '\n__label__\n' + '\n'.join(label.label_lines()) + '\n'))
    tcode = rename(minify(testcode(code_lua))).replace('$START', '1').replace('$TP', str(tp)).replace('$NS', str(len(parts))).replace('$TO', order).replace('$AM', str(MUSICSTART[1])).replace('$DATA', cs)
    with open(os.path.join(OUT, 'pokered_test.p8'), 'wb') as f:
        f.write(p8text('pico-8 cartridge // http://www.pico-8.com\nversion 42\n__lua__\n' + tcode + '\n' + p8_sections(rom) + '\n'))
    print('data %d bytes compressed: %d in rom, %d in code (%d chars)' % (
        len(streams), min(len(streams), ROMDATA), max(0, len(streams) - ROMDATA), len(cs)))


def main():
    load_names()
    config.check(sys.modules[__name__])
    import world, music
    world.build_maps(sys.modules[__name__])
    assert max(FLAGS.values()) < 256, 'the save keeps 255 flags'
    build_tables()
    build_misc()
    open(os.path.join(HERE, 'sfx.bin'), 'wb').write(bytes(0x100 + 57 * 68) + music.sfx_bank()[:7 * 68])  # no 'item get'
    code = open(os.path.join(PROJ, 'src', 'game.lua')).read()
    write_single(code)
    # the cartridge image (cart/pokered.p8.png, with the label) and the size check, both by shrinko8:
    # its token count matches PICO-8's; its compressed size is exact for the .p8.png it writes
    import subprocess
    r = subprocess.run([sys.executable, '-m', 'shrinko.shrinko8', 'pokered.p8', 'pokered.p8.png', '--count'],
                       cwd=OUT, capture_output=True, text=True)
    n = {k: int(v) for k, v in re.findall(r'(tokens|compressed): (\d+)', r.stdout)}
    if len(n) < 2:
        raise SystemExit('shrinko8 failed:\n' + r.stdout + r.stderr)
    if n['tokens'] > 8192 or n['compressed'] > 15616:
        raise SystemExit('cart does not fit: %d / 8192 tokens, %d / 15616 compressed code' % (n['tokens'], n['compressed']))
    print('cart/pokered.p8.png: %d / 8192 tokens, %d / 15616 compressed code' % (n['tokens'], n['compressed']))
    try:  # keep the web editor (editor/index.html) in step with the build
        import export_editor
        export_editor.export(sys.modules[__name__])
    except Exception as e:
        print('editor export failed:', e)


if __name__ == '__main__':
    main()
