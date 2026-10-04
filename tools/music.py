"""Convert pokered music (audio/music/*.asm) into PICO-8 sfx + music patterns.

Each song becomes resource 200+id: 256 bytes of music patterns followed by up to
MAXSFX sfx (68 bytes each), copied to 0x3100 at runtime. SFX 56..63 are reserved
for sound effects (written into the main cart by build.py via sfx.bin)."""
import os, re
from math import gcd
from functools import reduce

MAXSFX = 57  # sfx 0..56 for music (the game's sound effects are 57..63)
FPS = 59.7275
TICK = 183 / 22050  # seconds per pico-8 sfx speed unit
NOTES = {'C_': 0, 'C#': 1, 'D_': 2, 'D#': 3, 'E_': 4, 'F_': 5, 'F#': 6, 'G_': 7, 'G#': 8, 'A_': 9, 'A#': 10, 'B_': 11}
# drum id -> (noise pitch, volume) ; pokered noise "drumkit" ids
DRUMS = {1: (34, 4), 2: (32, 4), 3: (30, 4), 4: (28, 4), 5: (30, 3), 6: (52, 2), 7: (48, 2), 8: (33, 4), 9: (31, 4),
         10: (29, 4), 11: (27, 4), 12: (44, 3), 13: (42, 3), 14: (40, 3), 15: (24, 3), 16: (50, 2), 17: (22, 3),
         18: (20, 3), 19: (18, 3)}


def parse(path):
    """-> {channel: [(cmd, args)]}, labels {(ch, name): index}"""
    chans, cur, labels = {}, None, {}
    for raw in open(path).read().split('\n'):
        l = raw.split(';')[0].rstrip()
        if not l.strip():
            continue
        m = re.match(r'^(Music_\w+?)_Ch(\d)(\w*)::', l)
        if m:
            if m.group(3):  # alternate entry point: ignore
                continue
            cur = int(m.group(2))
            chans[cur] = []
            continue
        m = re.match(r'^\s*(\.?\w+):', l)
        if m and cur is not None and not l.strip().split()[0] in ('note',):
            labels[(cur, m.group(1))] = len(chans[cur])
            continue
        if cur is None:
            continue
        t = l.strip().split(None, 1)
        a = [x.strip() for x in t[1].split(',')] if len(t) > 1 else []
        chans[cur].append((t[0], a))
    return chans, labels


def run_channel(ch, cmds, labels, tempo0):
    """interpret one channel -> events [(t, dur, pitch|None, gbvol, fade, wave)], loop_t, end_t, tempo"""
    ev = []
    t = 0.0
    tempo = tempo0
    octave, speed, vol, fade, duty = 4, 12, 12, 0, 2
    dspeed = 12
    stack, counters = [], {}
    pc = 0
    loop_t = None
    visited_loop = False
    steps = 0
    while pc < len(cmds) and steps < 20000:
        steps += 1
        c, a = cmds[pc]
        pc += 1
        if c == 'tempo':
            tempo = int(a[0])
        elif c == 'octave':
            octave = int(a[0])
        elif c == 'note_type':
            speed, vol, fade = int(a[0]), int(a[1]), int(a[2])
        elif c == 'drum_speed':
            dspeed = int(a[0])
        elif c == 'duty_cycle':
            duty = int(a[0])
        elif c in ('note', 'rest', 'drum_note'):
            if c == 'note':
                ln, sp = int(a[1]), speed
                p = octave * 12 - 12 + NOTES[a[0]]
            elif c == 'rest':
                ln, sp, p = int(a[0]), (dspeed if ch == 4 else speed), None
            else:
                ln, sp, p = int(a[1]), dspeed, ('drum', int(a[0]))
            d = ln * sp * tempo / 256.0
            ev.append((t, d, p, vol, fade, duty, ln * sp))
            t += d
        elif c == 'sound_call':
            stack.append(pc)
            pc = labels[(ch, a[0])]
        elif c == 'sound_ret':
            if not stack:
                break
            pc = stack.pop()
        elif c == 'sound_loop':
            n, lab = int(a[0]), a[1]
            if n == 0:
                loop_t = None
                # loop start = time when the label was first reached
                target = labels[(ch, lab)]
                break_out = True
                ev_loop_index = target
                return ev, ('label', target), t, tempo
            key = pc
            counters[key] = counters.get(key, n) - 1
            if counters[key] > 0:
                pc = labels[(ch, lab)]
            else:
                del counters[key]
    return ev, None, t, tempo


def label_time(ch, cmds, labels, target, tempo0):
    """time at which the channel first reaches command index `target`"""
    t, tempo, speed, dspeed = 0.0, tempo0, 12, 12
    stack, counters, pc, steps = [], {}, 0, 0
    while pc < len(cmds) and steps < 20000:
        if pc == target:
            return t
        steps += 1
        c, a = cmds[pc]
        pc += 1
        if c == 'tempo':
            tempo = int(a[0])
        elif c == 'note_type':
            speed = int(a[0])
        elif c == 'drum_speed':
            dspeed = int(a[0])
        elif c == 'note':
            t += int(a[1]) * speed * tempo / 256.0
        elif c == 'rest':
            t += int(a[0]) * (dspeed if ch == 4 else speed) * tempo / 256.0
        elif c == 'drum_note':
            t += int(a[1]) * dspeed * tempo / 256.0
        elif c == 'sound_call':
            stack.append(pc)
            pc = labels[(ch, a[0])]
        elif c == 'sound_ret':
            if not stack:
                break
            pc = stack.pop()
        elif c == 'sound_loop':
            n = int(a[0])
            if n == 0:
                break
            counters[pc] = counters.get(pc, n) - 1
            if counters[pc] > 0:
                pc = labels[(ch, a[1])]
            else:
                del counters[pc]
    return t


def note_word(pitch, wave, vol, eff):
    return pitch | (wave << 6) | (vol << 9) | (eff << 12)


# per-song arrangement: 'lores' (the overworld: square lead, phaser bass, 2-step grid) or 'classic' (the battle and
# victory themes as first arranged: duty-matched lead, triangle bass an octave down at half speed)
LORES = {'titlescreen', 'cities1'}


def convert(path):
    classic = os.path.basename(path)[:-4] not in LORES
    chans, labels = parse(path)
    tempo0 = 160
    for c, a in chans.get(1, []):
        if c == 'tempo':
            tempo0 = int(a[0])
            break
    data = {}
    units = []
    loop_start = None
    end = 0
    for ch in sorted(chans):
        ev, loop, t_end, _ = run_channel(ch, chans[ch], labels, tempo0)
        lt = label_time(ch, chans[ch], labels, loop[1], tempo0) if loop else None
        data[ch] = (ev, lt, t_end)
        units += [e[6] for e in ev]
        end = max(end, t_end)
        if lt is not None:
            loop_start = lt if loop_start is None else min(loop_start, lt)
    g = reduce(gcd, units) if units else 12
    row = g * tempo0 / 256.0  # frames per row
    total = end
    # coarsen the grid while it is too long (accept quantisation error)
    while total / row > 1800 and g < 96:
        g *= 2
        row = g * tempo0 / 256.0
    nrows = int(round(total / row))
    lrow = int(round(loop_start / row)) if loop_start is not None else None
    speed = max(1, int(round(row / FPS / TICK)))
    tracks = {}
    for ch, (ev, lt, t_end) in data.items():
        rows = [0] * nrows  # 16-bit note words, 0 = silence
        for (t, d, p, vol, fade, duty, _) in ev:
            if p is None:
                continue
            r0 = int(round(t / row))
            r1 = max(r0 + 1, int(round((t + d) / row)))
            for r in range(r0, min(r1, nrows)):
                ft = (r - r0) * row
                if isinstance(p, tuple):  # drum: one hit
                    if r == r0:
                        pitch, v = DRUMS.get(p[1], (30, 3))
                        rows[r] = note_word(pitch, 6, v, 5)
                    continue
                if ch == 3:
                    gv = {0: 0, 1: 6, 2: 4, 3: 2}.get(vol, 4)
                    pitch = p - 12 if classic else p
                    wave = 0 if classic else 7  # triangle / phaser bass
                else:
                    gvol = vol
                    if fade > 0 and fade < 8:
                        gvol = max(0, vol - int(ft / (fade * FPS / 64)))
                    gv = int(round(gvol * 5 / 15))
                    if gvol > 0:
                        gv = max(1, gv)
                    pitch = p
                    wave = (3 if duty == 2 else 4) if classic else 3  # square lead (picked in music_audition.p8)
                while pitch > 63:
                    pitch -= 12
                while pitch < 0:
                    pitch += 12
                if gv > 0:
                    rows[r] = note_word(pitch, wave, min(7, gv), 0)
        tracks[ch] = rows
    return tracks, nrows, lrow, speed


def sfx_bank():
    """hand-made sound effects for slots 56..63 (main cart)"""
    def sfx(notes, speed):
        b = bytearray(68)
        for i, (p, w, v, e) in enumerate(notes):
            n = note_word(p, w, v, e)
            b[i * 2] = n & 255
            b[i * 2 + 1] = n >> 8
        b[64], b[65] = 1, speed
        return b
    bank = bytearray()
    bank += sfx([(48, 3, 4, 0), (48, 3, 2, 5)], 3)                                      # 56 menu select
    bank += sfx([(36, 3, 5, 0), (43, 3, 5, 0), (48, 3, 5, 0), (55, 3, 4, 5)], 2)          # 57 '!' / faint / bump
    bank += sfx([(20, 6, 4, 0), (24, 6, 3, 0), (28, 6, 2, 0), (32, 6, 1, 5)], 3)          # 58 door / run
    bank += sfx([(30, 6, 6, 3), (24, 6, 5, 5), (18, 6, 3, 5)], 3)                         # 59 hit
    bank += sfx([(40, 4, 4, 1), (46, 4, 3, 5)], 3)                                        # 60 jump / ball
    bank += sfx([(36, 3, 4, 0), (40, 3, 4, 0), (43, 3, 4, 0), (48, 3, 4, 0), (43, 3, 3, 0), (48, 3, 4, 0),
                 (52, 3, 4, 0), (55, 3, 3, 5)], 6)                                         # 61 heal
    bank += sfx([(43, 3, 4, 0), (43, 3, 4, 0), (47, 3, 4, 0), (50, 3, 4, 0), (55, 3, 4, 0), (55, 3, 3, 5)], 5)  # 62 level up
    bank += sfx([(48, 3, 4, 0), (52, 3, 4, 0), (55, 3, 4, 0), (60, 3, 4, 0), (60, 3, 3, 5)], 5)  # 63 item get
    return bytes(bank)


def simplify(ch, rows, name=''):
    """our own simpler arrangements. lores: lead and bass on a 2-step grid, each block playing its main note (rests
    ignored), so the bass stays on the beat with the lead. classic: the bass moves at half speed and the lead drops
    one-step grace notes between two equal notes"""
    rows = list(rows)
    if name in LORES:
        for r in range(0, len(rows), 2):
            blk = [w for w in rows[r:r + 2] if w]
            v = max(blk, key=blk.count) if blk else 0
            rows[r:r + 2] = [v] * len(rows[r:r + 2])
    elif ch == 3:
        for r in range(1, len(rows), 2):
            rows[r] = rows[r - 1]
    else:
        for r in range(1, len(rows) - 1):
            if rows[r - 1] and rows[r - 1] == rows[r + 1] and rows[r] != rows[r - 1]:
                rows[r] = rows[r - 1]
    return rows


def bank(names, root, keep=(2, 3), maxrows=None):
    """simplified renditions (lead + bass) of several songs in one music bank for 0x3100:
    256 bytes of patterns + shared sfx. Returns (bytes, first pattern of each song)."""
    allsfx, idx, mus, starts = [], {}, bytearray([0x41, 0x42, 0x43, 0x44] * 64), []
    p = 0
    for name in names:
        tracks, nrows, lrow, speed = convert(os.path.join(root, 'audio/music/%s.asm' % name))
        tracks = {c: simplify(c, t, name) for c, t in tracks.items() if c in keep}
        nrows = min(nrows, (maxrows or {}).get(name, nrows))
        cuts = sorted(set([0, nrows] + ([lrow] if lrow else [])))
        bounds = [(r, min(b, r + 32)) for a, b in zip(cuts, cuts[1:]) for r in range(a, b, 32)]
        loop = True
        starts.append(p)
        for i, (a, b) in enumerate(bounds):
            pat = []
            for ch in keep:
                key = (tuple(tracks[ch][a:b]), speed)
                if key not in idx:
                    idx[key] = len(allsfx)
                    allsfx.append(key)
                pat.append(idx[key])
            pat += [0x40 | (3 + k) for k in range(4 - len(keep))]  # unused channels off
            if loop and a == (lrow or 0):
                pat[0] |= 0x80
            if i == len(bounds) - 1:
                pat[1 if loop else 2] |= 0x80
            mus[p * 4:p * 4 + 4] = bytes(pat)
            p += 1
    assert len(allsfx) <= MAXSFX and p <= 64, (len(allsfx), p)
    out = bytearray(mus)
    for words, speed in allsfx:
        b = bytearray(68)
        for i, w in enumerate(words):
            b[i * 2], b[i * 2 + 1] = w & 255, w >> 8
        b[64], b[65], b[66] = 1, speed, len(words) if len(words) < 32 else 0
        out += b
    return bytes(out), starts
