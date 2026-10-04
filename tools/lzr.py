"""LZ77 + adaptive binary rANS (an LZMA-style coder small enough to decode in PICO-8 Lua).

Every decision is one bit coded with an adaptive probability (N-bit, updated by >>SH). rANS state x stays in
[L, 2L) with L = 2^15 / 2 so it fits PICO-8's 16-bit integers; renormalisation reads single bits.
Tokens (contexts in brackets):
  is-match [state]; literal: 8-bit tree [prev byte >> (8-lc)]; match: is-rep [state];
  rep: length; else length, distance. Numbers (>=1): unary bit length [kind, k], then mantissa bits
  [kind, k, tree node] for the top bits and [kind, k, bit position] below.
Stream: 2 bytes length, 1 byte lc, initial state (16 bits), then bits. decode() is the reference."""
import math
MINM, MAXM = 3, 3 + 63  # match lengths

N, SH = 12, 4           # probability bits, adaptation shift
P = 1 << N
L = 1 << 14             # rANS state in [L, 2L)
TREE = 64               # mantissa nodes below this get their own context


class Model:
    def __init__(s):
        s.p = {}

    def get(s, c):
        return s.p.get(c, P // 2)

    def upd(s, c, b):
        p = s.get(c)
        s.p[c] = p + ((P - p) >> SH) if b == 0 else p - (p >> SH)


def tokens_to_bits(data, toks, lc):
    """-> [(bit, p0)] in coding order"""
    m, out = Model(), []

    def bit(c, b):
        out.append((b, m.get(c)))
        m.upd(c, b)

    def num(kind, v):
        k = v.bit_length() - 1
        for i in range(k):
            bit((kind, 'u', i), 1)
        bit((kind, 'u', k), 0)
        node = 1
        for i in range(k - 1, -1, -1):
            b = v >> i & 1
            bit((kind, k, node) if node < TREE else (kind, k, 'b', i), b)
            node = node * 2 + b
    st, rep, pos = 0, 0, 0
    for t in toks:
        if t[0] == 'l':
            bit(('m', st), 0)
            ctx = data[pos - 1] >> (8 - lc) if pos and lc else 0
            node = 1
            for i in range(7, -1, -1):
                b = t[1] >> i & 1
                bit(('l', ctx, node), b)
                node = node * 2 + b
            st, pos = 0, pos + 1
        else:
            _, ln, d = t
            bit(('m', st), 1)
            bit(('r', st), int(d == rep))
            num('L', ln - MINM + 1)
            if d != rep:
                num('D', d)
            st, rep, pos = (2 if d == rep else 1), d, pos + ln
    return out


def rans(bits):
    """bitwise rANS, encoded backwards; returns the bit list the decoder reads (state first)"""
    x, out = L, []
    for b, p in reversed(bits):
        f, c = (p, 0) if b == 0 else (P - p, p)
        while x >= (L >> N << 1) * f:
            out.append(x & 1)
            x >>= 1
        x = (x // f << N) + x % f + c
    return [x >> i & 1 for i in range(15, -1, -1)] + out[::-1]


def pack(bitlist):
    b = bytearray()
    for i in range(0, len(bitlist), 8):
        v = 0
        for j in range(8):
            v = v * 2 + (bitlist[i + j] if i + j < len(bitlist) else 0)
        b.append(v)
    return bytes(b)


def compress(data, lc=0, toks=None):
    toks = toks or lz77_opt(data)
    return len(data).to_bytes(2, 'little') + bytes([lc]) + pack(rans(tokens_to_bits(data, toks, lc)))


def decode(blob):
    n, lc = blob[0] | blob[1] << 8, blob[2]
    pos = [3 * 8]

    def rb():
        v = blob[pos[0] >> 3] >> (7 - (pos[0] & 7)) & 1 if pos[0] >> 3 < len(blob) else 0
        pos[0] += 1
        return v
    x = 0
    for _ in range(16):
        x = x * 2 + rb()
    m = Model()

    def bit(c):
        nonlocal x
        p = m.get(c)
        q, r = x >> N, x & (P - 1)
        if r < p:
            b, x = 0, p * q + r
        else:
            b, x = 1, (P - p) * q + r - p
        m.upd(c, b)
        while x < L:
            x = x * 2 + rb()
        return b

    def num(kind):
        k = 0
        while bit((kind, 'u', k)):
            k += 1
        v = 1
        for i in range(k - 1, -1, -1):
            v = v * 2 + bit((kind, k, v) if v < TREE else (kind, k, 'b', i))
        return v
    out, st, rep = bytearray(), 0, 0
    while len(out) < n:
        if not bit(('m', st)):
            ctx = out[-1] >> (8 - lc) if out and lc else 0
            node = 1
            while node < 256:
                node = node * 2 + bit(('l', ctx, node))
            out.append(node - 256)
            st = 0
        else:
            isrep = bit(('r', st))
            ln = num('L') + MINM - 1
            d = rep if isrep else num('D')
            for _ in range(ln):
                out.append(out[-d])
            st, rep = (2 if isrep else 1), d
    return bytes(out)


def stats(data, toks, lc):
    """static cost table from a coding pass: context -> (cost of 0, cost of 1) in bits"""
    m, cnt = Model(), {}
    for (b, p), c in zip(tokens_to_bits(data, toks, lc), contexts(data, toks, lc)):
        n = cnt.setdefault(c, [1, 1])
        n[b] += 1
    return {c: (-math.log2(n[0] / (n[0] + n[1])), -math.log2(n[1] / (n[0] + n[1]))) for c, n in cnt.items()}


def contexts(data, toks, lc):
    """the context of every coded bit, in order (mirrors tokens_to_bits)"""
    out = []
    num = lambda kind, v: out.extend(numctx(kind, v))
    st, rep, pos = 0, 0, 0
    for t in toks:
        if t[0] == 'l':
            out.append(('m', st))
            ctx = data[pos - 1] >> (8 - lc) if pos and lc else 0
            node = 1
            for i in range(7, -1, -1):
                out.append(('l', ctx, node))
                node = node * 2 + (t[1] >> i & 1)
            st, pos = 0, pos + 1
        else:
            _, ln, d = t
            out += [('m', st), ('r', st)]
            num('L', ln - MINM + 1)
            if d != rep:
                num('D', d)
            st, rep, pos = (2 if d == rep else 1), d, pos + ln
    return out


def numctx(kind, v):
    k = v.bit_length() - 1
    c = [(kind, 'u', i) for i in range(k + 1)]
    node = 1
    for i in range(k - 1, -1, -1):
        c.append((kind, k, node) if node < TREE else (kind, k, 'b', i))
        node = node * 2 + (v >> i & 1)
    return c


def numbits(v):
    k = v.bit_length() - 1
    return [1] * k + [0] + [v >> i & 1 for i in range(k - 1, -1, -1)]


def parse(data, cost, lc, window=32767, chain=256):
    """optimal parse under a static cost table, tracking the state and rep distance along the best path"""
    n = len(data)
    C = lambda c, b: cost.get(c, (1.0, 1.0))[b]
    numc = {}

    def ncost(kind, v):
        if (kind, v) not in numc:
            numc[(kind, v)] = sum(C(c, b) for c, b in zip(numctx(kind, v), numbits(v)))
        return numc[(kind, v)]
    heads, INF = {}, float('inf')
    cost_ = [INF] * (n + 1)
    step, st, rep = [None] * (n + 1), [0] * (n + 1), [0] * (n + 1)
    cost_[0] = 0
    for i in range(n):
        key = data[i:i + 3]
        best = {}
        if len(key) == 3:
            for j in reversed(heads.get(key, [])[-chain:]):
                if i - j > window:
                    break
                k = 0
                while k < MAXM and i + k < n and data[j + k] == data[i + k]:
                    k += 1
                c = (i - j).bit_length()
                if k >= MINM and k > best.get(c, (0, 0))[0]:
                    best[c] = (k, i - j)
            heads.setdefault(key, []).append(i)
        c0 = cost_[i]
        if c0 == INF:
            continue
        s, r = st[i], rep[i]
        ctx = data[i - 1] >> (8 - lc) if i and lc else 0
        lit, node = C(('m', s), 0), 1
        for b in range(7, -1, -1):
            bb = data[i] >> b & 1
            lit += C(('l', ctx, node), bb)
            node = node * 2 + bb
        if c0 + lit < cost_[i + 1]:
            cost_[i + 1], step[i + 1], st[i + 1], rep[i + 1] = c0 + lit, ('l', data[i]), 0, r
        cands = list(best.values())
        if r and i >= r:
            k = 0
            while k < MAXM and i + k < n and data[i - r + k] == data[i + k]:
                k += 1
            if k >= MINM:
                cands.append((k, r))
        for k, d in cands:
            isrep = d == r
            base = c0 + C(('m', s), 1) + C(('r', s), int(isrep))
            for ln in range(MINM, k + 1):
                x = base + ncost('L', ln - MINM + 1) + (0 if isrep else ncost('D', d))
                if x < cost_[i + ln]:
                    cost_[i + ln], step[i + ln], st[i + ln], rep[i + ln] = x, ('m', ln, d), 2 if isrep else 1, d
    out, i = [], n
    while i > 0:
        out.append(step[i])
        i -= 1 if step[i][0] == 'l' else step[i][1]
    return out[::-1]


def compress_best(data, passes=4, lcs=(0, 1, 2)):
    best = None
    for lc in lcs:
        toks = lz77_opt(data)
        for _ in range(passes):
            c = compress(data, lc, toks)
            if best is None or len(c) < len(best):
                best = c
            toks = parse(data, stats(data, toks, lc), lc)
        c = compress(data, lc, toks)
        best = c if len(c) < len(best) else best
    assert decode(best) == data
    return best


def dclass(d):
    return (d - 1).bit_length()


def lz77_opt(data, window=32767, chain=256):
    """first parse: shortest path over literals/matches with flat cost estimates (parse() refines it)"""
    n = len(data)
    lc = lambda s: 9 if s < 256 else 7
    dc = lambda d: 5 + max(0, dclass(d) - 1)
    heads = {}
    cands = [None] * n
    for i in range(n):
        key = data[i:i + 3]
        best = {}
        if len(key) == 3:
            for j in reversed(heads.get(key, [])[-chain:]):
                if i - j > window:
                    break
                k = 0
                while k < MAXM and i + k < n and data[j + k] == data[i + k]:
                    k += 1
                c = dclass(i - j)
                if k >= MINM and k > best.get(c, (0, 0))[0]:
                    best[c] = (k, i - j)  # longest match per distance class (shorter ones reuse it)
            heads.setdefault(key, []).append(i)
        cands[i] = list(best.values())
    INF = float('inf')
    cost = [INF] * (n + 1)
    step = [None] * (n + 1)
    cost[0] = 0
    for i in range(n):
        c0 = cost[i]
        if c0 == INF:
            continue
        x = c0 + lc(data[i])
        if x < cost[i + 1]:
            cost[i + 1], step[i + 1] = x, ('l', data[i])
        for (k, d) in cands[i]:
            dcost = dc(d)
            for L in range(MINM, k + 1):
                x = c0 + lc(256 + L - MINM) + dcost
                if x < cost[i + L]:
                    cost[i + L], step[i + L] = x, ('m', L, d)
    out, i = [], n
    while i > 0:
        s = step[i]
        out.append(s)
        i -= 1 if s[0] == 'l' else s[1]
    return out[::-1]
