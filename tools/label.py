#!/usr/bin/env python3
"""The cart label (the picture on the .p8.png cartridge): Charizard on classic red with the PiCoMoN logo on top,
after the Pokemon Red box art. label_lines() -> the 128 rows of the .p8 __label__ section; run this file to
preview it as label.png."""
import os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.join(HERE, '..')
P8 = [(0, 0, 0), (29, 43, 83), (126, 37, 83), (0, 135, 81), (171, 82, 54), (95, 87, 79), (194, 195, 199),
      (255, 241, 232), (255, 0, 77), (255, 163, 0), (255, 236, 39), (0, 228, 54), (41, 173, 255), (131, 118, 156),
      (255, 119, 168), (255, 204, 170)]
P8X = [(0x29, 0x18, 0x14), (0x11, 0x1d, 0x35), (0x42, 0x21, 0x36), (0x12, 0x53, 0x59), (0x74, 0x2f, 0x29),
       (0x49, 0x33, 0x3b), (0xa2, 0x88, 0x79), (0xf3, 0xef, 0x7d), (0xbe, 0x12, 0x50), (0xff, 0x6c, 0x24),
       (0xa8, 0xe7, 0x2e), (0x00, 0xb5, 0x43), (0x06, 0x5a, 0xb5), (0x75, 0x46, 0x65), (0xff, 0x6e, 0x59),
       (0xff, 0x9d, 0x81)]
RGB = P8 + P8X  # label colours 0..31 (16..31 = the extended palette)
YELLOW, BLUE, BLACK, WHITE = 10, 28, 0, 7  # 28 = extended 140 'true blue'
STRIPE = 20  # width of the silver band on the left


def logo(width=124, chunk=2):
    """the PiCoMoN logo, drawn at 1/chunk resolution and blown back up so its pixels match the low-res art.
    Shrinking keeps the outline: a cell that is partly outline/shadow stays dark."""
    im = Image.open(os.path.join(PROJ, 'assets', 'logo.png')).convert('RGBA')
    im = im.crop(im.getbbox())
    w = width // chunk
    h = round(im.height * w / im.width)
    cw, chh = im.width / w, im.height / h
    cands = {YELLOW: RGB[YELLOW], BLUE: (58, 94, 168), BLACK: (0, 0, 0), WHITE: (255, 255, 255)}
    small = {}
    for y in range(h):
        for x in range(w):
            box = im.crop((int(x * cw), int(y * chh), max(int(x * cw) + 1, int((x + 1) * cw)),
                           max(int(y * chh) + 1, int((y + 1) * chh))))
            px = [p for p in box.get_flattened_data() if p[3] >= 110]
            if len(px) < box.width * box.height * .35:
                continue
            near = lambda p: min(cands, key=lambda c: sum((u - v) ** 2 for u, v in zip(cands[c], p[:3])))
            kinds = [near(p) for p in px]
            dark = [k for k in kinds if k in (BLUE, BLACK)]
            if len(dark) >= len(kinds) * .65:  # mostly-outline cells stay outline
                small[x, y] = max(set(dark), key=dark.count)
            else:
                small[x, y] = max(set(kinds), key=kinds.count)
    out = {(x * chunk + i, y * chunk + j): c for (x, y), c in small.items() for i in range(chunk) for j in range(chunk)}
    return out, w * chunk, h * chunk


def charizard(scale=4):
    """the game's own low-res Charizard (28x28: every other pixel of the 56x56 art), blown up. The background
    around him is found on the full art (the low-res outline has gaps) and sampled the same way."""
    src = Image.open(os.path.join(PROJ, 'build', 'pokered', 'gfx', 'pokemon', 'front', 'charizard.png')).convert('L')
    W, H = src.size
    full = [[3 - src.getpixel((x, y)) * 4 // 256 for x in range(W)] for y in range(H)]  # 0 light..3 black
    outside, todo = set(), [(x, y) for x in range(W) for y in (0, H - 1)] + [(x, y) for y in range(H) for x in (0, W - 1)]
    while todo:
        x, y = todo.pop()
        if (x, y) in outside or not (0 <= x < W and 0 <= y < H) or full[y][x]:
            continue
        outside.add((x, y))
        todo += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    col = {0: 15, 1: 9, 2: 4, 3: BLACK}  # peach belly, orange body, brown shading, black outline
    out = {}
    for y in range(28 * scale):
        for x in range(28 * scale):
            sx, sy = x // scale * 2, y // scale * 2
            if (sx, sy) not in outside:
                out[x, y] = col[full[sy][sx]]
    return out, 28 * scale, 28 * scale


def swirl(x, y, cx=78, cy=78):
    """a spiral of red shades behind him"""
    import math
    a = math.atan2(y - cy, x - cx) / (2 * math.pi)
    r = math.hypot(x - cx, y - cy)
    band = int((a * 4 + r / 14) * 1) % 4
    return [24, 8, 30, 8][band]  # deep red, red, salmon, red


def label():
    px = [[swirl(x, y) for x in range(128)] for y in range(128)]
    for y in range(128):  # the silver stripe down the left, like the Game Boy box
        for x in range(STRIPE):
            px[y][x] = 6  # solid silver
    cz, w, h = charizard()
    ox, oy = 12, 128 - h + 10  # bigger than the label: over the stripe and off the edges
    for (x, y), c in cz.items():
        if 0 <= ox + x < 128 and 0 <= oy + y < 128:
            px[oy + y][ox + x] = c
    lg, w, h = logo(width=108)
    ox, oy = (128 - w) // 2, 5  # centred on the label
    for (x, y), c in lg.items():
        px[oy + y][ox + x] = c
    return px


def label_lines():
    return [''.join('0123456789abcdefghijklmnopqrstuv'[c] for c in row) for row in label()]


if __name__ == '__main__':
    im = Image.new('RGB', (128, 128))
    for y, row in enumerate(label()):
        for x, c in enumerate(row):
            im.putpixel((x, y), RGB[c])
    im.resize((512, 512), Image.NEAREST).save(os.path.join(PROJ, 'label.png'))
    print('wrote label.png')
