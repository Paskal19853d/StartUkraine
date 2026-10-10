# Лексер JavaScript для карти проєкту (лише читання коду).
# Маскує рядки, шаблони, коментарі й регулярні вирази пробілами (довжина й переводи рядків зберігаються),
# щоб шукати функції, виклики й дужки по «чистому» коду; літерали повертає окремо з позиціями.
import re

KEYWORDS = set('''if for while switch catch function return typeof new delete void throw case do else in of
instanceof await yield async class const let var import export default super this try finally with
debugger break continue extends static get set'''.split())
REGEX_PREV = set('(,=:[!&|?{};+-*%<>~^')
REGEX_KW = {'return', 'typeof', 'case', 'do', 'else', 'in', 'of', 'new', 'delete', 'void', 'throw', 'await', 'yield'}


def mask_js(src):
    """→ (masked, literals): literals = [(start, end, text, kind)], kind: 'str' | 'tpl'."""
    n = len(src)
    out = list(src)
    lits = []
    ctx = []          # стек шаблонів: {'start', 'edepth'} ; edepth=None — у тексті шаблону
    depth = 0
    i = 0
    prev = ''         # останній значущий символ коду
    prev_word = ''

    def blank(a, b):
        for k in range(a, min(b, n)):
            if out[k] != '\n':
                out[k] = ' '

    while i < n:
        if ctx and ctx[-1]['edepth'] is None:          # текст шаблону
            c = src[i]
            if c == '\\':
                blank(i, i + 2); i += 2; continue
            if c == '`':
                t = ctx.pop()
                blank(i, i + 1)
                lits.append((t['start'], i + 1, src[t['start'] + 1:i], 'tpl'))
                i += 1; prev = 'L'; prev_word = ''
                continue
            if c == '$' and i + 1 < n and src[i + 1] == '{':
                blank(i, i + 1)
                ctx[-1]['edepth'] = depth
                depth += 1
                i += 2; prev = '{'; prev_word = ''
                continue
            blank(i, i + 1); i += 1
            continue
        c = src[i]
        if c == '/' and i + 1 < n and src[i + 1] == '/':
            j = src.find('\n', i)
            j = n if j < 0 else j
            blank(i, j); i = j; continue
        if c == '/' and i + 1 < n and src[i + 1] == '*':
            j = src.find('*/', i + 2)
            j = n if j < 0 else j + 2
            blank(i, j); i = j; continue
        if c in '"\'':
            j = i + 1
            while j < n and src[j] != c:
                if src[j] == '\\':
                    j += 2; continue
                if src[j] == '\n':
                    break
                j += 1
            lits.append((i, j + 1, src[i + 1:j], 'str'))
            blank(i, j + 1); i = j + 1; prev = 'L'; prev_word = ''
            continue
        if c == '`':
            ctx.append({'start': i, 'edepth': None})
            blank(i, i + 1); i += 1
            continue
        if c == '/':
            if prev == '' or prev in REGEX_PREV or prev_word in REGEX_KW:
                j = i + 1; in_cls = False
                while j < n:
                    ch = src[j]
                    if ch == '\\':
                        j += 2; continue
                    if ch == '\n':
                        break
                    if ch == '[':
                        in_cls = True
                    elif ch == ']':
                        in_cls = False
                    elif ch == '/' and not in_cls:
                        break
                    j += 1
                j += 1
                while j < n and (src[j].isalpha()):
                    j += 1
                blank(i, j); i = j; prev = 'L'; prev_word = ''
                continue
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if ctx and ctx[-1]['edepth'] is not None and depth == ctx[-1]['edepth']:
                ctx[-1]['edepth'] = None
                out[i] = '}'
                i += 1
                continue
        if c.isalnum() or c in '_$':
            j = i
            while j < n and (src[j].isalnum() or src[j] in '_$'):
                j += 1
            prev_word = src[i:j]; prev = 'w'
            i = j
            continue
        if not c.isspace():
            prev = c; prev_word = ''
        i += 1
    return ''.join(out), lits


def match_brace(masked, i, open_ch='{', close_ch='}'):
    """i — позиція відкривальної дужки → позиція закривальної (або len)."""
    d = 0
    n = len(masked)
    k = i
    while k < n:
        ch = masked[k]
        if ch == open_ch:
            d += 1
        elif ch == close_ch:
            d -= 1
            if d == 0:
                return k
        k += 1
    return n


IDENT = r'[A-Za-z_$][\w$]*'
RE_FUNC_DECL = re.compile(r'\b(?:async\s+)?function\s*\*?\s*(' + IDENT + r')\s*\(')
RE_ASSIGN = re.compile(r'\b(?:const|let|var)\s+(' + IDENT + r')\s*=\s*(?:async\s*)?(?=function\b|\(|' + IDENT + r'\s*=>)')
RE_WIN = re.compile(r'(?<![\w$.])(?:window|self|globalThis)\.(' + IDENT + r')\s*=\s*(?:async\s*)?(?=function\b|\(|' + IDENT + r'\s*=>)')
RE_OBJFN = re.compile(r'(?<![\w$.])(' + IDENT + r')\.(' + IDENT + r')\s*=\s*(?:async\s*)?(?=function\b|\([^()]*\)\s*=>)')
RE_OBJLIT = re.compile(r'(?:(?:const|let|var)\s+|(?<![\w$.])window\.)(' + IDENT + r')\s*=\s*\{')
RE_METHOD = re.compile(r'(?m)^[ \t]*(?:async\s+)?(' + IDENT + r')\s*\(([^()]*)\)\s*\{')
RE_KEYFN = re.compile(r'(?<![\w$.])(' + IDENT + r')\s*:\s*(?:async\s*)?(?=function\b|\([^()]*\)\s*=>|' + IDENT + r'\s*=>)')


def _body_after(masked, pos):
    """pos — початок виразу-функції (function… / (args)=> / x=>) → (body_start, body_end)."""
    n = len(masked)
    m = re.compile(r'function\s*\*?\s*[\w$]*\s*\(').match(masked, pos)
    if m:
        p_end = match_brace(masked, m.end() - 1, '(', ')')
        k = p_end + 1
        while k < n and masked[k].isspace():
            k += 1
        if k < n and masked[k] == '{':
            return k, match_brace(masked, k)
        return None
    k = pos
    if masked[k] == '(':
        k = match_brace(masked, k, '(', ')') + 1
    else:
        m2 = re.compile(IDENT).match(masked, k)
        if not m2:
            return None
        k = m2.end()
    m3 = re.compile(r'\s*=>\s*').match(masked, k)
    if not m3:
        return None
    k = m3.end()
    if k < n and masked[k] == '{':
        return k, match_brace(masked, k)
    # тіло-вираз — до кінця інструкції на тому ж рівні дужок
    d = 0; j = k
    while j < n:
        ch = masked[j]
        if ch in '([{':
            d += 1
        elif ch in ')]}':
            if d == 0:
                break
            d -= 1
        elif ch in ';\n,' and d == 0:
            break
        j += 1
    return k, j


def find_functions(masked):
    """→ список {name, start(def), body_start, body_end, kind}."""
    funcs = []
    seen = set()

    def add(name, defpos, span, kind):
        if not span or name in KEYWORDS:
            return
        # одне тіло — одна функція (window.X = function… інакше знаходився б ще й як «метод» window.X)
        if span[0] in seen:
            return
        seen.add(span[0])
        funcs.append({'name': name, 'start': defpos, 'body_start': span[0], 'body_end': span[1], 'kind': kind})

    for m in RE_FUNC_DECL.finditer(masked):
        p_end = match_brace(masked, m.end() - 1, '(', ')')
        k = p_end + 1
        while k < len(masked) and masked[k].isspace():
            k += 1
        if k < len(masked) and masked[k] == '{':
            add(m.group(1), m.start(), (k, match_brace(masked, k)), 'function')
    for rx, kind in ((RE_ASSIGN, 'const'), (RE_WIN, 'window')):
        for m in rx.finditer(masked):
            add(m.group(1), m.start(), _body_after(masked, m.end()), kind)
    for m in RE_OBJFN.finditer(masked):
        if m.group(1) in ('this', 'e', 'el', 'ev', 'event', 'window', 'self'):
            continue
        add(m.group(1) + '.' + m.group(2), m.start(), _body_after(masked, m.end()), 'method')
    # методи обʼєктів-модулів: NAME = { method() {…}, key: function(){…} }
    for m in RE_OBJLIT.finditer(masked):
        obj = m.group(1)
        o_start = m.end() - 1
        o_end = match_brace(masked, o_start)
        body = masked[o_start:o_end]
        if len(body) < 40:
            continue
        # лише члени першого рівня
        lvl = [0] * (len(body) + 1)
        d = 0
        for idx, ch in enumerate(body):
            lvl[idx] = d
            if ch in '{([':
                d += 1
            elif ch in '})]':
                d -= 1
        for mm in RE_METHOD.finditer(body):
            if mm.group(1) in KEYWORDS or lvl[mm.start(1)] != 1:
                continue
            bs = o_start + body.index('{', mm.end(2))
            add(obj + '.' + mm.group(1), o_start + mm.start(1), (bs, match_brace(masked, bs)), 'method')
        for mm in RE_KEYFN.finditer(body):
            if mm.group(1) in KEYWORDS or lvl[mm.start(1)] != 1:
                continue
            add(obj + '.' + mm.group(1), o_start + mm.start(1), _body_after(masked, o_start + mm.end()), 'method')
    funcs.sort(key=lambda f: f['body_start'])
    return funcs


RE_CALL = re.compile(r'(?<![\w$.])(' + IDENT + r')\s*\(')
RE_WINCALL = re.compile(r'(?<![\w$.])(?:window|self)\.(' + IDENT + r')\s*\(')
RE_QCALL = re.compile(r'(?<![\w$.])(' + IDENT + r')\.(' + IDENT + r')\s*\(')
RE_REF = re.compile(r'(?:[(,:=]|\bthen\(|\bforEach\(|\bmap\()\s*(' + IDENT + r')\s*(?=[,)};\n])')


def calls_in(masked_seg):
    """→ [(name, offset, kind)] kind: call | qcall | ref"""
    res = []
    for m in RE_CALL.finditer(masked_seg):
        nm = m.group(1)
        if nm in KEYWORDS:
            continue
        pre = masked_seg[max(0, m.start() - 12):m.start()]
        if re.search(r'function\s*\*?\s*$', pre) or re.search(r'\bnew\s+$', pre):
            continue
        res.append((nm, m.start(1), 'call'))
    for m in RE_WINCALL.finditer(masked_seg):
        res.append((m.group(1), m.start(1), 'call'))
    for m in RE_QCALL.finditer(masked_seg):
        res.append((m.group(1) + '.' + m.group(2), m.start(1), 'qcall'))
    for m in RE_REF.finditer(masked_seg):
        nm = m.group(1)
        if len(nm) >= 3 and nm not in KEYWORDS:
            res.append((nm, m.start(1), 'ref'))
    return res
