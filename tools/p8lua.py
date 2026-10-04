"""Transpile PICO-8 Lua dialect -> plain Lua 5.1 (LuaJIT) for the test harness.

Handles: compound assignment, !=, \\ (int div), bitwise ops (& | ^^ << >> ~),
@ % $ peek prefixes, shorthand if/while, hex/binary fractional numbers."""
import re, sys

KW = {'and', 'break', 'do', 'else', 'elseif', 'end', 'false', 'for', 'function', 'goto', 'if', 'in', 'local',
      'nil', 'not', 'or', 'repeat', 'return', 'then', 'true', 'until', 'while'}
OPS = ['...', '..=', '>>>=', '<<=', '>>=', '^^=', '>>>', '..', '==', '~=', '!=', '<=', '>=', '+=', '-=', '*=', '/=',
       '\\=', '%=', '^=', '&=', '|=', '<<', '>>', '^^', '::', '+', '-', '*', '/', '\\', '%', '^', '#', '<', '>', '=',
       '(', ')', '{', '}', '[', ']', ';', ':', ',', '.', '@', '$', '&', '|', '~', '?']


class Tok:
    def __init__(s, k, v, line):
        s.k, s.v, s.line = k, v, line

    def __repr__(s):
        return '%s:%r@%d' % (s.k, s.v, s.line)


def p8num(t):
    t = t.lower()
    if t.startswith('0x'):
        a, _, b = t[2:].partition('.')
        v = int(a or '0', 16) + (int(b, 16) / 16 ** len(b) if b else 0)
    elif t.startswith('0b'):
        a, _, b = t[2:].partition('.')
        v = int(a or '0', 2) + (int(b, 2) / 2 ** len(b) if b else 0)
    else:
        v = float(t)
    if v >= 32768:
        v -= 65536
    return repr(v) if v != int(v) else str(int(v))


def lex(src):
    toks, i, line = [], 0, 1
    n = len(src)
    while i < n:
        c = src[i]
        if c == '\n':
            line += 1
            i += 1
            continue
        if c in ' \t\r':
            i += 1
            continue
        if src.startswith('--', i):
            if src.startswith('--[[', i):
                j = src.index(']]', i)
                line += src[i:j].count('\n')
                i = j + 2
            else:
                while i < n and src[i] != '\n':
                    i += 1
            continue
        if src.startswith('//', i):
            while i < n and src[i] != '\n':
                i += 1
            continue
        if c in '"\'':
            j = i + 1
            while src[j] != c:
                if src[j] == '\\':
                    j += 1
                j += 1
            lit = src[i:j + 1]
            for a, b in (('\\^', '\\6'), ('\\#', '\\2'), ('\\-', '\\3'), ('\\|', '\\4'), ('\\+', '\\5'), ('\\*', '\\1')):
                lit = lit.replace(a, b)
            toks.append(Tok('str', lit, line))
            i = j + 1
            continue
        if src.startswith('[[', i):
            j = src.index(']]', i)
            toks.append(Tok('str', src[i:j + 2], line))
            line += src[i:j].count('\n')
            i = j + 2
            continue
        m = re.match(r'0[xX][0-9a-fA-F]*(\.[0-9a-fA-F]*)?|0[bB][01]*(\.[01]*)?|\d+(\.\d*)?([eE][-+]?\d+)?|\.\d+', src[i:])
        if m and m.group(0):
            toks.append(Tok('num', p8num(m.group(0)), line))
            i += len(m.group(0))
            continue
        m = re.match(r'[A-Za-z_][A-Za-z_0-9]*', src[i:])
        if m:
            w = m.group(0)
            toks.append(Tok('kw' if w in KW else 'name', w, line))
            i += len(w)
            continue
        for op in OPS:
            if src.startswith(op, i):
                toks.append(Tok('op', op, line))
                i += len(op)
                break
        else:
            raise SyntaxError('bad char %r line %d' % (c, line))
    toks.append(Tok('eof', None, line + 1))
    return toks


BIN = {  # op: (prec, right_assoc)
    'or': (1, 0), 'and': (2, 0),
    '<': (3, 0), '>': (3, 0), '<=': (3, 0), '>=': (3, 0), '~=': (3, 0), '!=': (3, 0), '==': (3, 0),
    '|': (4, 0), '^^': (5, 0), '&': (6, 0), '<<': (7, 0), '>>': (7, 0), '>>>': (7, 0),
    '..': (8, 1), '+': (9, 0), '-': (9, 0), '*': (10, 0), '/': (10, 0), '\\': (10, 0), '%': (10, 0),
    '^': (12, 1),
}
UNARY_PREC = 11
FN = {'\\': 'p8idiv', '&': 'p8band', '|': 'p8bor', '^^': 'p8bxor', '<<': 'p8shl', '>>': 'p8shr', '>>>': 'p8lshr'}


class P:
    def __init__(s, toks):
        s.t, s.i = toks, 0

    def peek(s, k=0):
        return s.t[s.i + k]

    def nxt(s):
        t = s.t[s.i]
        s.i += 1
        return t

    def isop(s, v, k=0):
        t = s.peek(k)
        return t.k in ('op', 'kw') and t.v == v

    def expect(s, v):
        t = s.nxt()
        if t.v != v:
            raise SyntaxError('expected %r got %r line %d' % (v, t.v, t.line))
        return t

    # ---------------- expressions
    def expr(s, lim=0):
        t = s.peek()
        if t.v in ('not', '-', '#', '~', '@', '%', '$') and t.k in ('op', 'kw'):
            s.nxt()
            e = s.expr(UNARY_PREC)
            if t.v == 'not':
                left = '(not %s)' % e
            elif t.v == '~':
                left = 'p8bnot(%s)' % e
            elif t.v == '@':
                left = 'peek(%s)' % e
            elif t.v == '%':
                left = 'peek2(%s)' % e
            elif t.v == '$':
                left = 'peek4(%s)' % e
            else:
                left = '(%s%s)' % (t.v if t.v != '-' else '- ', e)
        else:
            left = s.simple()
        while True:
            t = s.peek()
            if t.k not in ('op', 'kw') or t.v not in BIN:
                break
            prec, ra = BIN[t.v]
            if prec <= lim:
                break
            s.nxt()
            right = s.expr(prec - 1 if ra else prec)
            op = t.v
            if op in FN:
                left = '%s(%s,%s)' % (FN[op], left, right)
            else:
                left = '(%s %s %s)' % (left, '~=' if op == '!=' else op, right)
        return left

    def simple(s):
        t = s.peek()
        if t.k == 'num' or t.k == 'str':
            s.nxt()
            return t.v
        if t.k == 'kw' and t.v in ('nil', 'true', 'false'):
            s.nxt()
            return t.v
        if t.k == 'op' and t.v == '...':
            s.nxt()
            return '...'
        if t.k == 'kw' and t.v == 'function':
            s.nxt()
            return 'function' + s.funcbody()
        if t.k == 'op' and t.v == '{':
            return s.suffix(s.table())
        return s.primary()

    def table(s):
        s.expect('{')
        out = []
        while not s.isop('}'):
            if s.isop('['):
                s.nxt()
                k = s.expr()
                s.expect(']')
                s.expect('=')
                out.append('[%s]=%s' % (k, s.expr()))
            elif s.peek().k == 'name' and s.isop('=', 1):
                k = s.nxt().v
                s.nxt()
                out.append('%s=%s' % (k, s.expr()))
            else:
                out.append(s.expr())
            if s.isop(',') or s.isop(';'):
                s.nxt()
        s.expect('}')
        return '{' + ','.join(out) + '}'

    def primary(s):
        t = s.nxt()
        if t.k == 'name':
            e = t.v
        elif t.v == '(':
            e = '(' + s.expr() + ')'
            s.expect(')')
        else:
            raise SyntaxError('unexpected %r line %d' % (t.v, t.line))
        return s.suffix(e)

    def suffix(s, e):
        while True:
            t = s.peek()
            if t.k == 'op' and t.v == '.':
                s.nxt()
                e += '.' + s.nxt().v
            elif t.k == 'op' and t.v == '[':
                s.nxt()
                e += '[' + s.expr() + ']'
                s.expect(']')
            elif t.k == 'op' and t.v == ':':
                s.nxt()
                e += ':' + s.nxt().v + s.args()
            elif t.k == 'op' and t.v == '(' and t.line == s.t[s.i - 1].line:
                e += s.args()
            elif t.k == 'str':
                s.nxt()
                e += '(' + t.v + ')'
            elif t.k == 'op' and t.v == '{':
                e += '(' + s.table() + ')'
            else:
                return e

    def args(s):
        if s.peek().k == 'str':
            return '(' + s.nxt().v + ')'
        if s.isop('{'):
            return '(' + s.table() + ')'
        s.expect('(')
        a = []
        while not s.isop(')'):
            a.append(s.expr())
            if s.isop(','):
                s.nxt()
        s.expect(')')
        return '(' + ','.join(a) + ')'

    def funcbody(s):
        s.expect('(')
        a = []
        while not s.isop(')'):
            a.append(s.nxt().v)
            if s.isop(','):
                s.nxt()
        s.expect(')')
        b = s.block(('end',))
        s.expect('end')
        return '(' + ','.join(a) + ')\n' + b + '\nend'

    # ---------------- statements
    def block(s, stops, line=None):
        out = []
        while True:
            t = s.peek()
            if t.k == 'eof' or (t.k == 'kw' and t.v in stops):
                break
            if line is not None and t.line != line:
                break
            st = s.stat()
            if st:
                out.append(st)
        return '\n'.join(out)

    def stat(s):
        t = s.peek()
        if t.k == 'op' and t.v == ';':
            s.nxt()
            return ''
        if t.k == 'op' and t.v == '::':
            s.nxt()
            n = s.nxt().v
            s.expect('::')
            return '::%s::' % n
        if t.k == 'op' and t.v == '?':
            s.nxt()
            a = [s.expr()]
            while s.isop(','):
                s.nxt()
                a.append(s.expr())
            return 'print(%s)' % ','.join(a)
        if t.k == 'kw':
            v = t.v
            if v == 'break':
                s.nxt()
                return 'do break end'
            if v == 'goto':
                s.nxt()
                return 'goto ' + s.nxt().v
            if v == 'do':
                s.nxt()
                b = s.block(('end',))
                s.expect('end')
                return 'do\n' + b + '\nend'
            if v == 'while':
                s.nxt()
                c = s.expr()
                if s.isop('do'):
                    s.nxt()
                    b = s.block(('end',))
                    s.expect('end')
                else:
                    b = s.block((), t.line)
                return 'while %s do\n%s\nend' % (c, b)
            if v == 'repeat':
                s.nxt()
                b = s.block(('until',))
                s.expect('until')
                return 'repeat\n%s\nuntil %s' % (b, s.expr())
            if v == 'if':
                return s.ifstat()
            if v == 'for':
                s.nxt()
                n1 = s.nxt().v
                if s.isop('='):
                    s.nxt()
                    a = [s.expr()]
                    while s.isop(','):
                        s.nxt()
                        a.append(s.expr())
                    head = 'for %s=%s' % (n1, ','.join(a))
                else:
                    names = [n1]
                    while s.isop(','):
                        s.nxt()
                        names.append(s.nxt().v)
                    s.expect('in')
                    a = [s.expr()]
                    while s.isop(','):
                        s.nxt()
                        a.append(s.expr())
                    head = 'for %s in %s' % (','.join(names), ','.join(a))
                s.expect('do')
                b = s.block(('end',))
                s.expect('end')
                return head + ' do\n' + b + '\nend'
            if v == 'function':
                s.nxt()
                n = s.nxt().v
                while s.isop('.') or s.isop(':'):
                    n += s.nxt().v + s.nxt().v
                return 'function ' + n + s.funcbody()
            if v == 'local':
                s.nxt()
                if s.isop('function'):
                    s.nxt()
                    n = s.nxt().v
                    return 'local function ' + n + s.funcbody()
                names = [s.nxt().v]
                while s.isop(','):
                    s.nxt()
                    names.append(s.nxt().v)
                if s.isop('='):
                    s.nxt()
                    a = [s.expr()]
                    while s.isop(','):
                        s.nxt()
                        a.append(s.expr())
                    return 'local %s=%s' % (','.join(names), ','.join(a))
                return 'local ' + ','.join(names)
            if v == 'return':
                s.nxt()
                if s.peek().k == 'eof' or (s.peek().k == 'kw' and s.peek().v in ('end', 'else', 'elseif', 'until')) \
                        or s.isop(';') or s.peek().line != t.line:
                    return 'do return end'
                a = [s.expr()]
                while s.isop(','):
                    s.nxt()
                    a.append(s.expr())
                return 'do return %s end' % ','.join(a)
        # assignment or call
        e = s.suffix_start()
        if s.isop(',') or s.isop('='):
            lhs = [e]
            while s.isop(','):
                s.nxt()
                lhs.append(s.suffix_start())
            s.expect('=')
            a = [s.expr()]
            while s.isop(','):
                s.nxt()
                a.append(s.expr())
            return '%s=%s' % (','.join(lhs), ','.join(a))
        t = s.peek()
        if t.k == 'op' and t.v.endswith('=') and t.v not in ('==', '~=', '!=', '<=', '>='):
            s.nxt()
            op = t.v[:-1]
            r = s.expr()
            if op in FN:
                return '%s=%s(%s,%s)' % (e, FN[op], e, r)
            return '%s=%s %s (%s)' % (e, e, op, r)
        return e

    def suffix_start(s):
        t = s.nxt()
        if t.k == 'name':
            e = t.v
        elif t.v == '(':
            e = '(' + s.expr() + ')'
            s.expect(')')
        else:
            raise SyntaxError('bad statement start %r line %d' % (t.v, t.line))
        return s.suffix(e)

    def ifstat(s):
        t = s.expect('if')
        # shorthand: if (cond) stmt  -- no 'then' after the parenthesised condition
        if s.isop('('):
            save = s.i
            depth, j = 0, s.i
            while True:
                tk = s.t[j]
                if tk.v == '(' and tk.k == 'op':
                    depth += 1
                elif tk.v == ')' and tk.k == 'op':
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            nt = s.t[j + 1]
            if not (nt.k == 'kw' and nt.v in ('then', 'and', 'or')) and not (nt.k == 'op' and nt.v in BIN) and \
                    not (nt.k == 'op' and nt.v in ('.', '[', ':', '(')):
                s.nxt()
                c = s.expr()
                s.expect(')')
                b = s.block(('else', 'elseif', 'end'), t.line)
                eb = ''
                if s.isop('else') and s.peek().line == t.line:
                    s.nxt()
                    eb = '\nelse\n' + s.block(('end',), t.line)
                return 'if %s then\n%s%s\nend' % (c, b, eb)
            s.i = save
        c = s.expr()
        s.expect('then')
        out = 'if %s then\n%s' % (c, s.block(('elseif', 'else', 'end')))
        while s.isop('elseif'):
            s.nxt()
            c = s.expr()
            s.expect('then')
            out += '\nelseif %s then\n%s' % (c, s.block(('elseif', 'else', 'end')))
        if s.isop('else'):
            s.nxt()
            out += '\nelse\n' + s.block(('end',))
        s.expect('end')
        return out + '\nend'


def transpile(src):
    p = P(lex(src))
    return p.block(())


if __name__ == '__main__':
    print(transpile(open(sys.argv[1]).read()))
