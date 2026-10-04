#!/usr/bin/env python3
"""Pull the graphics, maps and music out of a Pokemon Red ROM into the pokered layout tools/build.py reads.
usage: extract.py rom.gb outdir
Where everything lives in the ROM is in tools/rommap.json (made by tools/mkrommap.py)."""
import sys, os, json, hashlib
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
NOTE = ['C_', 'C#', 'D_', 'D#', 'E_', 'F_', 'F#', 'G_', 'G#', 'A_', 'A#', 'B_']


def to_png(px, w, h, path):
    im = Image.new('L', (w, h))
    im.putdata([255 - 85 * c for c in px])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path)


def tiles(data, w, h, bpp):
    """gb tiles (row-major over the image) -> w*h color indices; missing (trimmed) tiles are white"""
    px = [0] * (w * h)
    tb = 8 * bpp
    for t in range(min(len(data) // tb, w // 8 * (h // 8))):
        tx, ty = t % (w // 8) * 8, t // (w // 8) * 8
        for y in range(8):
            if bpp == 1:
                lo, hi = data[t * 8 + y], 0
            else:
                lo, hi = data[t * 16 + y * 2], data[t * 16 + y * 2 + 1]
            for x in range(8):
                c = (lo >> (7 - x) & 1) | (hi >> (7 - x) & 1) << 1
                px[(ty + y) * w + tx + x] = c * 3 if bpp == 1 else c
    return px


def pic(rom, off):
    """gen 1 compressed picture -> (w, h, color indices)"""
    pos = [off * 8]

    def bit():
        b = rom[pos[0] >> 3] >> (7 - (pos[0] & 7)) & 1
        pos[0] += 1
        return b

    def num(k):
        v = 0
        for _ in range(k):
            v = v << 1 | bit()
        return v
    tw, th = num(4), num(4)
    W, H = tw * 8, th * 8
    n = W * H // 2  # 2-pixel groups per plane

    def plane():
        g, rle = [], not bit()
        while len(g) < n:
            if rle:
                i = 0
                while bit():
                    i += 1
                g += [0] * ((2 << i) - 1 + num(i + 1))
            else:
                while len(g) < n:
                    v = num(2)
                    if not v:
                        break
                    g.append(v)
            rle = not rle
        p = [0] * (W * H)  # groups run down 2-pixel-wide columns
        for k, v in enumerate(g[:n]):
            x, y = k // H * 2, k % H
            p[y * W + x], p[y * W + x + 1] = v >> 1, v & 1
        return p

    def delta(p):
        for y in range(H):
            s = 0
            for x in range(W):
                s ^= p[y * W + x]
                p[y * W + x] = s
    order = bit()
    first = plane()
    mode = bit()
    if mode:
        mode += bit()
    second = plane()
    a, b = (first, second) if order == 0 else (second, first)  # a = low bitplane
    r1, r2 = (a, b) if order == 0 else (b, a)
    if mode == 0:
        delta(a)
        delta(b)
    else:
        if mode == 2:
            delta(r2)
        delta(r1)
        for i in range(W * H):
            r2[i] ^= r1[i]
    return W, H, [lo | hi << 1 for lo, hi in zip(a, b)]


def song(rom, name, chans):
    """audio bytecode -> pokered music macros (the subset tools/music.py reads)"""
    out = []
    for ch, start in sorted(chans.items(), key=lambda c: int(c[0])):
        ch = int(ch)
        base = start - (start - 0x4000) % 0x4000 if start >= 0x4000 else 0
        ins, targets, todo = {}, set(), [start]
        while todo:
            pc = todo.pop()
            while pc not in ins:
                b, at = rom[pc], pc
                if b in (0xfd, 0xfe):
                    k = 1 if b == 0xfd else 2
                    t = base + rom[pc + k] + rom[pc + k + 1] * 256 - 0x4000
                    targets.add(t)
                    todo.append(t)
                    if b == 0xfd:
                        ins[at] = 'sound_call .L%x' % t
                    else:
                        ins[at] = 'sound_loop %d, .L%x' % (rom[pc + 1], t)
                    pc += k + 2
                    if b == 0xfe and rom[at + 1] == 0:
                        break
                    continue
                if b == 0xff:
                    ins[at] = 'sound_ret'
                    break
                if b < 0xb0 or (b < 0xc0 and ch != 4):
                    s, pc = 'note %s, %d' % (NOTE[b >> 4], (b & 15) + 1), pc + 1
                elif b < 0xc0:
                    s, pc = 'drum_note %d, %d' % (rom[pc + 1], (b & 15) + 1), pc + 2
                elif b < 0xd0:
                    s, pc = 'rest %d' % ((b & 15) + 1), pc + 1
                elif b < 0xe0:
                    if ch == 4:
                        s, pc = 'drum_speed %d' % (b & 15), pc + 1
                    else:
                        v, f = rom[pc + 1] >> 4, rom[pc + 1] & 15
                        if ch != 3 and f >= 8:
                            f = -(f & 7)
                        s, pc = 'note_type %d, %d, %d' % (b & 15, v, f), pc + 2
                elif b < 0xe8:
                    s, pc = 'octave %d' % (8 - (b & 7)), pc + 1
                else:
                    a, c = rom[pc + 1], rom[pc + 2]
                    s, k = {0xe8: lambda: ('toggle_perfect_pitch', 1), 0xea: lambda: ('vibrato %d, %d, %d' % (a, c >> 4, c & 15), 3),
                            0xeb: lambda: ('pitch_slide %d, %d, %s' % (a + 1, 8 - (c >> 4), NOTE[c & 15]), 3),
                            0xec: lambda: ('duty_cycle %d' % a, 2), 0xed: lambda: ('tempo %d' % (a * 256 + c), 3),
                            0xee: lambda: ('stereo_panning %d, %d' % (a >> 4, a & 15), 2),
                            0xef: lambda: ('unknownmusic0xef %d' % a, 2), 0xf0: lambda: ('volume %d, %d' % (a >> 4, a & 15), 2),
                            0xf8: lambda: ('execute_music', 1),
                            0xfc: lambda: ('duty_cycle_pattern %d, %d, %d, %d' % (a >> 6, a >> 4 & 3, a >> 2 & 3, a & 3), 2)}[b]()
                    pc = at + k
                ins[at] = s
        out.append('%s_Ch%d::' % (name, ch))
        for at in sorted(ins):
            if at in targets:
                out.append('.L%x:' % at)
            out.append('\t' + ins[at])
        out.append('')
    return '\n'.join(out)


def extract(rom, out, rm):
    for path, e in rm['files'].items():
        dst = os.path.join(out, path)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if e['fmt'] == 'bin':
            open(dst, 'wb').write(rom[e['off']:e['off'] + e['len']])
        elif e['fmt'] == 'pic':
            w, h, px = pic(rom, e['off'])
            to_png(px, w, h, dst)
        else:
            bpp = 1 if e['fmt'] == '1bpp' else 2
            to_png(tiles(rom[e['off']:e['off'] + e['len']], e['w'], e['h'], bpp), e['w'], e['h'], dst)
    for name, s in rm['music'].items():
        open(os.path.join(out, 'audio/music/%s.asm' % name), 'w').write(song(rom, s['label'], s['ch']))


if __name__ == '__main__':
    rom = open(sys.argv[1], 'rb').read()
    rm = json.load(open(os.path.join(HERE, 'rommap.json')))
    if hashlib.sha1(rom).hexdigest() != rm['sha1']:
        sys.exit('%s is not Pokemon Red (USA, Europe): sha1 %s, expected %s'
                 % (sys.argv[1], hashlib.sha1(rom).hexdigest(), rm['sha1']))
    os.makedirs(os.path.join(sys.argv[2], 'audio/music'), exist_ok=True)
    extract(rom, sys.argv[2], rm)
    print('extracted %d files + %d songs' % (len(rm['files']), len(rm['music'])))
