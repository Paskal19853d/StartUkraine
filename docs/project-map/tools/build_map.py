# Генератор інтерактивної карти проєкту «Зоряна Памʼять» (docs/project-map/).
# Лише ЧИТАЄ код проєкту: Python — через ast, JavaScript — власним лексером (jsscan.py), HTML — html.parser.
# Результат: data/graph.json, mermaid/*.mmd, index.html (дані вбудовано, щоб працювало з file://).
#   python docs/project-map/tools/build_map.py
import ast, io, json, os, re, sys, html, time
from html.parser import HTMLParser
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(OUT))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True      # без __pycache__ у tools/
from jsscan import mask_js, find_functions, calls_in, match_brace, KEYWORDS  # noqa: E402

def rd(path):
    with io.open(os.path.join(ROOT, path), encoding='utf-8', errors='replace') as f:
        return f.read()

def line_of(text, pos, _cache={}):
    key = id(text)
    idx = _cache.get(key)
    if idx is None:
        idx = [0]
        for m in re.finditer('\n', text):
            idx.append(m.end())
        _cache[key] = idx
    lo, hi = 0, len(idx) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if idx[mid] <= pos:
            lo = mid
        else:
            hi = mid - 1
    return lo + 1

# ─────────────────────────── граф ───────────────────────────
NODES = {}
EDGES = {}

def node(nid, type_, label, **kw):
    n = NODES.get(nid)
    if n is None:
        n = {'id': nid, 'type': type_, 'label': label}
        NODES[nid] = n
    for k, v in kw.items():
        if v not in (None, '', [], {}):
            n[k] = v
    return n

def edge(s, t, rel, status='code', file=None, line=None, note=None):
    if s == t or s not in NODES or t not in NODES:
        return
    k = (s, t, rel)
    e = EDGES.get(k)
    if e is None:
        e = {'s': s, 't': t, 'rel': rel, 'status': status}
        if file:
            e['file'] = file
        if line:
            e['line'] = line
        if note:
            e['note'] = note
        EDGES[k] = e
    elif status == 'code' and e['status'] != 'code':
        e['status'] = 'code'
    return e

# ─────────────────── довідники з документації ───────────────────
def parse_claude_routes():
    """CLAUDE.md: таблиці | METHOD | `/path` | опис | → {(METHOD, norm_path): опис}"""
    d = {}
    for ln in rd('CLAUDE.md').splitlines():
        m = re.match(r'\|\s*([A-Z/ ]+?)\s*\|\s*`([^`]+)`\s*\|\s*(.+?)\s*\|\s*$', ln)
        if not m:
            continue
        meths = [x.strip() for x in m.group(1).split('/') if x.strip()]
        path = m.group(2).split('?')[0].strip()
        for p in [x.strip() for x in path.split(',')]:
            for me in meths:
                d[(me, norm_path(p))] = m.group(3)
    return d

def norm_path(p):
    p = p.split('?')[0]
    return re.sub(r'\{[^}]+\}', '{}', p).rstrip('/') or '/'

# ─────────────────────────── BACKEND (ast) ───────────────────────────
PY_FILES = ['Paskal.py', 'lang_engine.py', 'seo_utils.py']
PY_TOOLS = ['setup_awards.py', 'setup_gsc_sa.py', 'place_cities.py', 'seed_test_data.py', 'migrate_awards_category.py', 'gunicorn.conf.py']

SQL_PATTERNS = [
    (re.compile(r'\bDELETE\s+FROM\s+`?(\w+)`?', re.I), 'deletes'),
    (re.compile(r'\bINSERT\s+(?:IGNORE\s+)?INTO\s+`?(\w+)`?', re.I), 'writes'),
    (re.compile(r'\bREPLACE\s+INTO\s+`?(\w+)`?', re.I), 'writes'),
    (re.compile(r'\bUPDATE\s+`?(\w+)`?\s+(?:\w+\s+)?SET\b', re.I), 'writes'),
    (re.compile(r'\bCREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?`?(\w+)`?', re.I), 'creates'),
    (re.compile(r'\bALTER\s+TABLE\s+`?(\w+)`?', re.I), 'creates'),
    (re.compile(r'\bFROM\s+`?(\w+)`?', re.I), 'reads'),
    (re.compile(r'\bJOIN\s+`?(\w+)`?', re.I), 'reads'),
]

def collect_tables():
    """Таблиці: CREATE TABLE у коді + дамп БД (структура, без даних)."""
    tables = {}
    for f in PY_FILES:
        src = rd(f)
        for m in re.finditer(r'CREATE TABLE IF NOT EXISTS\s+`?(\w+)`?\s*\(', src):
            name = m.group(1)
            d, k = 0, m.end() - 1          # збалансовані дужки: VARCHAR(100) усередині не обриває список полів
            while k < len(src):
                if src[k] == '(':
                    d += 1
                elif src[k] == ')':
                    d -= 1
                    if d == 0:
                        break
                k += 1
            body = re.sub(r'"\s*\n\s*"', '\n', src[m.end():k]).replace('"', '\n')
            cols = parse_cols(body)
            t = tables.setdefault(name, {'cols': [], 'src': None, 'line': None})
            if not t['cols']:
                t['cols'] = cols
            t['src'] = f
            t['line'] = line_of(src, m.start())
    dump = rd('zoryana_pamyat.sql')
    for m in re.finditer(r'CREATE TABLE `(\w+)` \((.*?)\n\) ENGINE', dump, re.S):
        name = m.group(1)
        t = tables.setdefault(name, {'cols': [], 'src': None, 'line': None})
        dump_cols = parse_cols(m.group(2))
        if len(dump_cols) >= len(t['cols']):     # у дампі — повна структура (з колонками, доданими ALTER TABLE)
            t['cols'] = dump_cols
        t['in_dump'] = True
    # індекси / ключі з дампу
    for m in re.finditer(r'ALTER TABLE `(\w+)`\n(.*?);', dump, re.S):
        name = m.group(1)
        if name in tables:
            keys = re.findall(r'ADD (PRIMARY KEY|UNIQUE KEY `\w+`|KEY `\w+`|FULLTEXT KEY `\w+`) \(([^)]*)\)', m.group(2))
            if keys:
                tables[name]['keys'] = [f"{k[0]} ({k[1].replace('`', '')})" for k in keys]
    return tables

def parse_cols(body):
    cols = []
    for ln in body.split('\n'):
        ln = ln.strip().rstrip(',')
        m = re.match(r'`?(\w+)`?\s+([A-Za-z]+(?:\([^)]*\))?)', ln)
        sql_type = m and re.match(r'(?i)(tiny|small|medium|big)?int|varchar|char|text|longtext|mediumtext|double|float|decimal|date|datetime|timestamp|time|json|enum|blob|bool', m.group(2))
        if m and (sql_type or m.group(1).upper() not in ('PRIMARY', 'UNIQUE', 'INDEX', 'KEY', 'FULLTEXT', 'FOREIGN', 'CONSTRAINT', 'CHECK')) and sql_type:
            cols.append(f"{m.group(1)} {m.group(2)}")
    return cols

COLS = {}              # таблиця → [поля]
def column_nodes(TABLES):
    """Поля таблиць — окремі блоки: тип і ключі (PRIMARY / UNIQUE / INDEX / FULLTEXT з дампу); таблиця «містить» поле."""
    for name, t in TABLES.items():
        flags = defaultdict(list)
        for k in t.get('keys') or []:
            m = re.match(r'(PRIMARY KEY|UNIQUE KEY|FULLTEXT KEY|KEY)\b[^(]*\(([^)]*)\)', k)
            if not m:
                continue
            kind = {'PRIMARY KEY': 'PK', 'UNIQUE KEY': 'UNIQUE', 'FULLTEXT KEY': 'FULLTEXT', 'KEY': 'INDEX'}[m.group(1)]
            for c in m.group(2).split(','):
                c = re.sub(r'\(\d+\)', '', c).strip()
                if c and kind not in flags[c]:
                    flags[c].append(kind)
        COLS[name] = []
        for c in t['cols']:
            cn, _, ctype = c.partition(' ')
            COLS[name].append(cn)
            node(f'col:{name}.{cn}', 'column', cn, table=name, ctype=ctype, ckey=flags.get(cn), file=t.get('src'), line=t.get('line'))
            edge('tbl:' + name, f'col:{name}.{cn}', 'contains')

SQL_KW = re.compile(r'\b(SELECT|INSERT|UPDATE|DELETE|REPLACE|ALTER)\b')
def sql_columns(fid, s, f, ln, tset):
    """Поля в SQL-запиті: INSERT (…) / UPDATE … SET / ON DUPLICATE KEY UPDATE — змінює; ALTER TABLE … ADD — створює; решта згадок — читає.
    Поле, що є в кількох таблицях запиту (JOIN без однозначності), — припущення."""
    if not SQL_KW.search(s) or re.search(r'\bCREATE\s+TABLE\b', s, re.I):
        return
    clean = re.sub(r"'(?:[^'\\]|\\.)*'", "''", s)                  # значення в лапках — не поля
    tabs = []
    for rx, _ in SQL_PATTERNS:
        for m in rx.finditer(clean):
            if m.group(1) in tset and m.group(1) in COLS and m.group(1) not in tabs:
                tabs.append(m.group(1))
    if not tabs:
        return
    writes, creates = set(), set()
    for m in re.finditer(r'\b(?:INSERT|REPLACE)\s+(?:IGNORE\s+)?INTO\s+`?(\w+)`?\s*\(([^)]*)\)', clean, re.I):
        writes |= {(m.group(1), c) for c in re.findall(r'`?(\w+)`?', m.group(2))}
        d = re.search(r'ON\s+DUPLICATE\s+KEY\s+UPDATE\b(.*)$', clean[m.end():], re.I | re.S)
        if d:
            writes |= {(m.group(1), c) for c in re.findall(r'`?(\w+)`?\s*=', d.group(1))}
    for m in re.finditer(r'\bUPDATE\s+`?(\w+)`?\s+(?:\w+\s+)?SET\b(.*?)(?=\bWHERE\b|\bORDER\s+BY\b|\bLIMIT\b|$)', clean, re.I | re.S):
        for part in re.split(r',(?![^()]*\))', m.group(2)):         # «a=%s, b=IF(x=1,…)» — левая часть каждого присваивания
            c = re.match(r'\s*(?:\w+\.)?`?(\w+)`?\s*=', part)
            if c:
                writes.add((m.group(1), c.group(1)))
    for m in re.finditer(r'\bALTER\s+TABLE\s+`?(\w+)`?\s+ADD\s+(?:COLUMN\s+)?(?:IF\s+NOT\s+EXISTS\s+)?`?(\w+)`?', clean, re.I):
        if m.group(2).upper() not in ('INDEX', 'KEY', 'UNIQUE', 'PRIMARY', 'FULLTEXT', 'CONSTRAINT', 'FOREIGN'):
            creates.add((m.group(1), m.group(2)))
    body = re.sub(r'\b(?:FROM|JOIN|INTO|UPDATE|TABLE)\s+`?\w+`?', ' ', clean, flags=re.I)   # имена таблиц — не поля
    owners = defaultdict(list)
    for t in tabs:
        for c in COLS[t]:
            owners[c].append(t)
    for c, ts in owners.items():
        hit = re.search(r'(?<![\w])(?:\w+\.)?`?%s`?(?![\w(])' % re.escape(c), body)
        for t in ts:
            cid = f'col:{t}.{c}'
            if (t, c) in creates:
                edge(fid, cid, 'creates', file=f, line=ln, note='ALTER TABLE … ADD')
            elif (t, c) in writes:
                edge(fid, cid, 'writes', file=f, line=ln, note='поле в SQL-запросе')
            elif hit:
                if len(ts) > 1:
                    edge(fid, cid, 'reads', status='assumed', file=f, line=ln, note='поле с таким именем есть в нескольких таблицах запроса')
                else:
                    edge(fid, cid, 'reads', file=f, line=ln, note='поле в SQL-запросе')

def const_strings(node):
    """Усі рядкові константи всередині вузла (f-рядки — з X замість виразів)."""
    out = []
    for sub in ast.walk(node):
        if isinstance(sub, ast.JoinedStr):
            parts = []
            for v in sub.values:
                if isinstance(v, ast.Constant) and isinstance(v.value, str):
                    parts.append(v.value)
                else:
                    parts.append('X')
            out.append((''.join(parts), getattr(sub, 'lineno', None)))
        elif isinstance(sub, ast.Constant) and isinstance(sub.value, str):
            out.append((sub.value, getattr(sub, 'lineno', None)))
    return out

def py_comment_above(lines, lineno):
    res = []
    k = lineno - 2
    while k >= 0 and lines[k].strip().startswith('#'):
        res.insert(0, lines[k].strip().lstrip('#').strip())
        k -= 1
    return ' '.join(res)[:400]

def doc_of(fn, lines):
    ds = ast.get_docstring(fn)
    if ds:
        return ds.strip().split('\n')[0][:400]
    c = py_comment_above(lines, fn.lineno - len(fn.decorator_list))
    if c:
        return c
    # перший коментар у тілі
    k = fn.body[0].lineno - 1 if fn.body else fn.lineno
    for j in range(fn.lineno, min(len(lines), k + 3)):
        s = lines[j].strip()
        if s.startswith('#'):
            return s.lstrip('#').strip()[:300]
    return ''

ROUTES = []            # {'method','path','fn','id'}
PY_FUNCS = {}          # 'file:name' → info
PY_BY_NAME = {}        # name → id (Paskal першим)

def backend():
    claude = parse_claude_routes()
    TABLES = collect_tables()
    for name, t in TABLES.items():
        node('tbl:' + name, 'table', name, file=t.get('src'), line=t.get('line'), cols=t['cols'], keys=t.get('keys'),
             desc=TABLE_DESC.get(name, ''),
             note=None if t.get('src') else 'Таблица есть в дампе БД (zoryana_pamyat.sql), но init_db() её не создаёт — создана миграцией или вручную')
    column_nodes(TABLES)
    infos = []
    for f in PY_FILES + PY_TOOLS:
        if not os.path.exists(os.path.join(ROOT, f)):
            continue
        src = rd(f)
        lines = src.split('\n')
        tree = ast.parse(src)
        # константи модуля: імʼя → env / URL / рядки
        mod_env, mod_urls, mod_strs = defaultdict(set), defaultdict(set), defaultdict(set)
        for st in tree.body:
            if isinstance(st, (ast.Assign, ast.AnnAssign)):
                tg = st.targets if isinstance(st, ast.Assign) else [st.target]
                names = [t.id for t in tg if isinstance(t, ast.Name)]
                if not names or st.value is None:
                    continue
                envs = env_reads(st.value)
                strs = [s for s, _ in const_strings(st.value)]
                for nm in names:
                    mod_env[nm] |= set(envs)
                    for s in strs:
                        mod_strs[nm].add(s)
                        for u in re.findall(r'https?://[^\s"\'{}<>]+', s):
                            mod_urls[nm].add(u)
        # функції (верхній рівень + методи + вкладені)
        def walk_funcs(body, prefix=''):
            for st in body:
                if isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    yield prefix + st.name, st
                    yield from walk_funcs(st.body, prefix + st.name + '.')
                elif isinstance(st, ast.ClassDef):
                    yield from walk_funcs(st.body, prefix + st.name + '.')
        for qname, fn in walk_funcs(tree.body):
            fid = f'py:{f}:{qname}'
            kind = 'tool' if f in PY_TOOLS else 'pyfn'
            dec_routes = []
            special = None
            for d in fn.decorator_list:
                if isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute) and isinstance(d.func.value, ast.Name) and d.func.value.id == 'app':
                    meth = d.func.attr.upper()
                    arg = d.args[0].value if d.args and isinstance(d.args[0], ast.Constant) else ''
                    if meth in ('GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'WEBSOCKET'):
                        dec_routes.append((meth if meth != 'WEBSOCKET' else 'WS', arg))
                    elif meth == 'MIDDLEWARE':
                        special = 'middleware'
                    elif meth == 'ON_EVENT':
                        special = 'event:' + arg
            desc = doc_of(fn, lines)
            n = node(fid, 'bgtask' if special and special.startswith('event') else ('middleware' if special == 'middleware' else kind),
                     qname if not special else (('Middleware: ' if special == 'middleware' else f'Событие {arg}: ') + qname),
                     file=f, line=fn.lineno, end=getattr(fn, 'end_lineno', None), desc=desc, lang='python')
            PY_FUNCS[fid] = {'node': fn, 'file': f, 'lines': lines, 'mod_env': mod_env, 'mod_urls': mod_urls, 'mod_strs': mod_strs, 'qname': qname}
            if '.' not in qname:
                PY_BY_NAME.setdefault((f, qname), fid)
                if f == 'Paskal.py' or qname not in [k[1] for k in PY_BY_NAME if k[0] == 'Paskal.py']:
                    PY_BY_NAME.setdefault(('*', qname), fid)
            for meth, path in dec_routes:
                rid = f'route:{meth} {path}'
                rdesc = claude.get((meth, norm_path(path))) or claude.get(('GET' if meth == 'WS' else meth, norm_path(path))) or desc
                node(rid, 'route', f'{meth} {path}', method=meth, path=path, file=f, line=fn.lineno, desc=rdesc, handler=qname)
                ROUTES.append({'method': meth, 'path': path, 'id': rid, 'fn': fid,
                               'rx': re.compile('^' + re.sub(r'\\\{[^}]+\\\}', r'[^/]+', re.escape(path)) + '$')})
                edge(rid, fid, 'handles', file=f, line=fn.lineno)
            infos.append((fid, fn, f, lines, mod_env, mod_urls, mod_strs))
    # статичні монтування
    src = rd('Paskal.py')
    for m in re.finditer(r'app\.mount\("([^"]+)",\s*StaticFiles\(directory="([^"]+)"(, html=True)?\)', src):
        rid = f'route:STATIC {m.group(1)}'
        node(rid, 'route', f'STATIC {m.group(1)}', method='STATIC', path=m.group(1), file='Paskal.py', line=line_of(src, m.start()),
             desc=f'Статические файлы из каталога {m.group(2)}/' + (' (с index.html)' if m.group(3) else ''))
        ROUTES.append({'method': 'STATIC', 'path': m.group(1), 'id': rid, 'fn': None, 'rx': re.compile('^' + re.escape(m.group(1)) + '(/.*)?$')})
    return TABLES, infos

def env_reads(node_):
    res = []
    for sub in ast.walk(node_):
        if isinstance(sub, ast.Call):
            fn = sub.func
            nm = ast.unparse(fn) if hasattr(ast, 'unparse') else ''
            if nm in ('os.getenv', 'os.environ.get', 'getenv', 'environ.get') and sub.args and isinstance(sub.args[0], ast.Constant):
                res.append(sub.args[0].value)
        elif isinstance(sub, ast.Subscript):
            if ast.unparse(sub.value) == 'os.environ' and isinstance(sub.slice, ast.Constant):
                res.append(sub.slice.value)
    return res

TABLE_DESC = {
    'memorials': 'Основная таблица: записи погибших (ФИО, даты, место, фото, позиция на карте, тариф, slug, одобрение)',
    'users': 'Аккаунты: email, пароль (bcrypt), ФИО, ник, роль admin/moder/user, бан',
    'colors': 'Все настройки сайта (ключ → значение): цвета, модули, переключатели админки',
    'likes_log': 'Защита от повторных «Звёзд памяти» (лайков) по отпечатку браузера',
    'map_labels': 'Подписи областей на карте Украины',
    'cities': 'Города на карте Украины',
    'search_logs': 'Аналитика поиска',
    'partners': '«Друзья и партнёры» — рекламные блоки на сайте',
    'pricing_leads': 'Заявки на тарифы со страницы /pricing/',
    'gift_categories': '«Подарки погибшему»: категории',
    'gifts': '«Подарки погибшему»: каталог',
    'gift_i18n': '«Подарки погибшему»: тексты каталога на языках',
    'memorial_gifts': '«Подарки погибшему»: размещения и заказы (оплата LiqPay)',
    'ghost_faces': '«Призраки в дыму»: SVG-силуэты',
    'ad_video_views': '«Видео-попап»: когда посетителю показано видео',
    'memorial_awards': 'Награды конкретного погибшего',
    'awards_catalog': 'Каталог всех наград',
    'bot_visits': 'Визиты поисковых ботов',
    'daily_stats': 'Статистика за день',
    'hourly_stats': 'Статистика за час (люди/боты)',
    'minute_silence_settings': '«Минута молчания»: настройки',
    'seo_index_log': 'Журнал отправок в Google Indexing API',
    'seo_broken_links': 'Битые ссылки на фото',
    'seo_score_history': 'История SEO-баллов',
    'chat_messages': 'Микро-чат: сообщения',
    'chat_reports': 'Микро-чат: жалобы',
    'chat_banned_words': 'Микро-чат: запрещённые слова',
    'chat_bot_phrases': 'Микро-чат: фразы ботов',
    'i18n_translations': 'Переводы интерфейса (ключ → текст на языке)',
    'languages': 'Языки интерфейса',
    'portfolio_thanks': 'Страница портфолио: благодарности',
    'user_nickname_aliases': 'Старые ники пользователей (переадресация профиля)',
    'legacy_accounts': '«Наследие памяти»: аккаунты',
    'legacy_content': '«Наследие памяти»: содержимое',
    'legacy_logs': '«Наследие памяти»: журнал',
    'legacy_requests': '«Наследие памяти»: запросы доверенных лиц',
    'legacy_trusted': '«Наследие памяти»: доверенные лица',
    'legacy_trusted_contacts': '«Наследие памяти»: контакты доверенных лиц',
}

# ─────────────────────────── НАЛАШТУВАННЯ (таблиця colors) ───────────────────────────
SECRET_RX = re.compile(r'pass(?!_len)|secret|token|private|apikey|api_key', re.I)      # reg_min_pass_len — просто число
SETTINGS = {}   # key → {'default', 'label', 'seed_line'}

def collect_settings():
    src = rd('Paskal.py')
    tree = ast.parse(src)
    for fn in ast.walk(tree):
        if isinstance(fn, ast.FunctionDef) and fn.name == 'init_db':
            for st in ast.walk(fn):
                if isinstance(st, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'defaults' for t in st.targets) and isinstance(st.value, ast.List):
                    for el in st.value.elts:
                        if isinstance(el, ast.Tuple) and len(el.elts) >= 2 and all(isinstance(x, ast.Constant) for x in el.elts[:2]):
                            k = el.elts[0].value
                            lbl = el.elts[2].value if len(el.elts) > 2 and isinstance(el.elts[2], ast.Constant) else ''
                            dflt = el.elts[1].value
                            SETTINGS[k] = {'default': '••• (секрет, не показан)' if SECRET_RX.search(k) else str(dflt)[:120],
                                           'label': lbl, 'seed_line': el.lineno, 'src': 'seed'}
    d = rd('zoryana_pamyat.sql')
    m = re.search(r"INSERT INTO `colors` \(`key`, `value`, `label`\) VALUES\n(.*?);\n", d, re.S)
    if m:
        for k, lbl in re.findall(r"^\('([^']+)',\s*'(?:[^'\\]|\\.|'')*',\s*'((?:[^'\\]|\\.|'')*)'\)", m.group(1), re.M):
            s = SETTINGS.setdefault(k, {'default': None, 'label': '', 'src': 'dump'})
            if not s.get('label') and lbl:
                s['label'] = lbl.replace("''", "'")
            s['in_dump'] = True
    a = rd('admin.html')
    not_settings = {'descr_full', 'descr_any'}      # поля записів у формах адмінки, не налаштування
    for k in re.findall(r"onClrChange\(\s*'([a-z][a-z0-9_]+)'", a) + re.findall(r"\{\s*key\s*:\s*'([a-z][a-z0-9_]+)'", a) + \
            re.findall(r"\bkey\s*:\s*'([a-z][a-z0-9_]+)'\s*,\s*(?:value|min|grp)", a):
        if '_' in k and not k.endswith('_') and k not in not_settings:
            SETTINGS.setdefault(k, {'default': None, 'label': '', 'src': 'admin'})
    for k, s in SETTINGS.items():
        node('set:' + k, 'setting', k, desc=s.get('label') or '', default=s.get('default'),
             file='Paskal.py' if s.get('seed_line') else None, line=s.get('seed_line'),
             origin={'seed': 'засевается init_db()', 'dump': 'есть в БД (дамп), в коде не засевается', 'admin': 'только в коде админки'}[s['src']],
             note=('Секретное значение: в публичном /api/colors заменено на smtp_pass_set' if k == 'smtp_pass' else None))

SHORT_OK = re.compile(r'[a-z]+_[a-z0-9_]+$')

def backend_edges(TABLES, infos):
    tset = set(TABLES)
    for fid, fn, f, lines, mod_env, mod_urls, mod_strs in infos:
        info = PY_FUNCS[fid]
        rl = []
        names_used = set()
        nested = set()
        for c in ast.walk(fn):
            if c is not fn and isinstance(c, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for cc in ast.walk(c):
                    nested.add(id(cc))
        for sub in ast.walk(fn):
            if id(sub) in nested:
                continue
            if isinstance(sub, ast.ImportFrom) and sub.module in ('lang_engine', 'seo_utils'):
                for al in sub.names:
                    tgt = PY_BY_NAME.get((sub.module + '.py', al.name))
                    if tgt:
                        info.setdefault('imports', {})[al.asname or al.name] = tgt
        for sub in ast.walk(fn):
            if id(sub) in nested:
                continue
            if isinstance(sub, ast.Call):
                fnm = sub.func
                if isinstance(fnm, ast.Attribute):
                    full = ast.unparse(fnm)
                    if full == '_rl.check' and sub.args:
                        k = sub.args[0]
                        key = ''.join(v.value if isinstance(v, ast.Constant) else '{…}' for v in k.values) if isinstance(k, ast.JoinedStr) else (k.value if isinstance(k, ast.Constant) else '?')
                        lim = '/'.join(ast.unparse(a) for a in sub.args[1:3])
                        rl.append(f'{key} → {lim} с')
                    if full == 'threading.Thread':
                        for kw in sub.keywords:
                            if kw.arg == 'target' and isinstance(kw.value, ast.Name):
                                tgt = resolve_py(f, kw.value.id, fid, info)
                                if tgt:
                                    NODES[tgt]['type'] = 'bgtask'
                                    edge(fid, tgt, 'starts', file=f, line=sub.lineno, note='threading.Thread — фоновый поток')
                    if full in ('asyncio.create_task', 'asyncio.ensure_future') and sub.args and isinstance(sub.args[0], ast.Call) and isinstance(sub.args[0].func, ast.Name):
                        tgt = resolve_py(f, sub.args[0].func.id, fid, info)
                        if tgt:
                            NODES[tgt]['type'] = 'bgtask'
                            edge(fid, tgt, 'starts', file=f, line=sub.lineno, note='asyncio-задача')
                    if full.startswith('smtplib.'):
                        edge(fid, 'ext:smtp', 'request', file=f, line=sub.lineno, note=full)
                    if full.startswith('_redis.') or full in ('redis.from_url', 'redis.Redis'):
                        edge(fid, 'infra:redis', 'depends', file=f, line=sub.lineno, note=full)
                    if full in ('pymysql.connect',):
                        edge(fid, 'infra:mysql', 'depends', file=f, line=sub.lineno, note=full)
                    if full == 'urllib.request.urlopen':
                        NODES[fid]['http_out'] = True
                elif isinstance(fnm, ast.Name):
                    if fnm.id == 'PooledDB':
                        edge(fid, 'infra:mysql', 'depends', file=f, line=sub.lineno, note='PooledDB (пул соединений)')
                    tgt = resolve_py(f, fnm.id, fid, info)
                    if tgt:
                        edge(fid, tgt, 'calls', file=f, line=sub.lineno)
            elif isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load):
                names_used.add((sub.id, sub.lineno))
        if rl:
            NODES[fid]['ratelimit'] = rl
        for nm, ln in sorted(names_used, key=lambda x: x[1]):
            tgt = resolve_py(f, nm, fid, info)
            if tgt and tgt != fid and (fid, tgt, 'calls') not in EDGES:
                edge(fid, tgt, 'calls', file=f, line=ln, note='ссылка на функцию (колбэк)')
            for ev in mod_env.get(nm, ()):
                env_node(ev)
                edge(fid, 'env:' + ev, 'reads', file=f, line=ln, note=f'через константу {nm}')
            for u in mod_urls.get(nm, ()):
                ext_link(fid, u, f, ln, via=nm)
            for s in mod_strs.get(nm, ()):
                if s in SETTINGS and SHORT_OK.match(s):
                    edge(fid, 'set:' + s, 'reads', file=f, line=ln, note=f'через константу {nm}')
        for ev in env_reads(fn):
            env_node(ev)
            edge(fid, 'env:' + ev, 'reads', file=f, line=fn.lineno)
        strs = [(s, ln) for s, ln in const_strings(fn)]
        writes_colors = False
        for s, ln in strs:
            if re.search(r'\b(SELECT|INSERT|UPDATE|DELETE|REPLACE|CREATE|ALTER)\b', s, re.I):
                for rx, rel in SQL_PATTERNS:
                    for m in rx.finditer(s):
                        t = m.group(1)
                        if t in tset:
                            edge(fid, 'tbl:' + t, rel, file=f, line=ln)
                            if t == 'colors' and rel in ('writes', 'deletes'):
                                writes_colors = True
                sql_columns(fid, s, f, ln, tset)
            if re.search(r'\bcolors\b', s) and re.search(r'\b(SELECT|INSERT|UPDATE|DELETE)\b', s, re.I):
                for tok in re.findall(r"'([a-z][a-z0-9_]+)'", s):
                    if tok in SETTINGS:
                        edge(fid, 'set:' + tok, 'writes' if re.search(r'\b(UPDATE|INSERT)\b', s, re.I) else 'reads', file=f, line=ln, note='ключ в SQL-запросе')
            for m in re.finditer(r"LIKE\s+'([a-z_]+)%'", s):
                for k in SETTINGS:
                    if k.startswith(m.group(1)):
                        edge(fid, 'set:' + k, 'reads', file=f, line=ln, note=f"SQL LIKE '{m.group(1)}%'")
            for u in re.findall(r'https?://[^\s"\'<>]+', s):
                ext_link(fid, u, f, ln)
            if re.fullmatch(r'[\w\-/]*\.html', s) and ('page:' + s) in NODES:
                edge(fid, 'page:' + s, 'serves', file=f, line=ln)
        # ключі, що передаються параметрами в INSERT/UPDATE colors → змінює; решта — читає
        write_lits = set()
        for sub in ast.walk(fn):
            if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) and sub.func.attr in ('execute', 'executemany') and sub.args:
                sql = ' '.join(x for x, _ in const_strings(sub.args[0]))
                if re.search(r'\b(INSERT|UPDATE|REPLACE)\b', sql, re.I) and re.search(r'\bcolors\b', sql):
                    for a_ in sub.args[1:]:
                        for x, _ in const_strings(a_):
                            write_lits.add(x)
        batch = info['qname'] == 'update_colors_batch'
        for s, ln in strs:
            if s in SETTINGS and (SHORT_OK.match(s) or len(s) > 7):
                if batch:
                    edge(fid, 'set:' + s, 'writes', file=f, line=ln, note='проверка значения при сохранении (PUT /api/admin/colors/batch)')
                elif info['qname'] == 'init_db':
                    edge(fid, 'set:' + s, 'writes', file=f, line=ln, note='засев значения по умолчанию (INSERT IGNORE)')
                else:
                    edge(fid, 'set:' + s, 'writes' if s in write_lits else 'reads', file=f, line=ln)


def resolve_py(f, name, fid=None, info=None):
    if fid:
        cand = fid + '.' + name
        if cand in NODES:
            return cand
    if info and name in info.get('imports', {}):
        return info['imports'][name]
    t = PY_BY_NAME.get((f, name))
    if t:
        return t
    return None


def env_node(name):
    node('env:' + name, 'env', name, desc=ENV_DESC.get(name, 'Переменная окружения (.env)'), note='Значение не показано')

ENV_DESC = {
    'DB_HOST': 'MySQL — хост', 'DB_USER': 'MySQL — пользователь', 'DB_PASS': 'MySQL — пароль (секрет)', 'DB_NAME': 'MySQL — база',
    'DB_PORT': 'MySQL — порт', 'REDIS_URL': 'Redis — адрес (необязательно)', 'GOOGLE_CLIENT_ID': 'Google OAuth — ID клиента',
    'GOOGLE_CLIENT_SECRET': 'Google OAuth — секрет', 'OAUTH_REDIRECT_BASE': 'Google OAuth — база адреса возврата',
    'SECRET_KEY': 'Секретный ключ приложения', 'LIQPAY_PUBLIC_KEY': 'LiqPay — публичный ключ мерчанта',
    'LIQPAY_PRIVATE_KEY': 'LiqPay — приватный ключ (подпись)', 'LIQPAY_SANDBOX': 'LiqPay — тестовый режим (1/0)',
    'SITE_BASE_URL': 'Публичный адрес сайта (sitemap, OAuth, LiqPay result/server_url)', 'ALLOWED_ORIGINS': 'CORS — разрешённые источники',
    'ENVIRONMENT': 'production → cookie с флагом Secure', 'ADMIN_NOTIFY_EMAIL': 'Куда отправлять уведомления админу',
    'GOOGLE_INDEXING_KEY_FILE': 'Google Indexing API — файл сервисного аккаунта',
}

# ─────────────────────────── ЗОВНІШНІ СЕРВІСИ Й ІНФРАСТРУКТУРА ───────────────────────────
EXT = {
    # id: (назва, призначення, протокол, авторизація, що перестане працювати, чи працює сайт без нього)
    'google_oauth': ('Google OAuth 2.0', 'Вход и регистрация через Google', 'HTTPS (OAuth 2.0: authorize → token → userinfo)',
                     'GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET в .env', 'Вход через Google (сайт, админка, возврат на мемориал, покупка подарков — нужен вход). Вход по email и паролю работает', True),
    'google_indexing': ('Google Indexing API', 'Уведомление Google о новых и изменённых страницах мемориалов', 'HTTPS JSON (сервисный аккаунт)',
                        'GOOGLE_INDEXING_KEY_FILE в .env', 'Только кнопка «Ping Google» в SEO-разделе админки; сайт работает', True),
    'google_search': ('Google (ping / проверка)', 'Обращение к google.com (ping sitemap / проверка)', 'HTTP(S) GET', '—', 'Только соответствующая служебная функция', True),
    'liqpay': ('LiqPay (ПриватБанк)', 'Оплата «Подарков погибшему»: checkout, callback, проверка статуса', 'HTTPS: форма POST на checkout; API /api/request (action=status); callback server_url',
               'LIQPAY_PUBLIC_KEY / LIQPAY_PRIVATE_KEY (подпись sha1)', 'Покупка подарков и сверка оплат; уже положенные подарки показываются', True),
    'nbu': ('НБУ API (bank.gov.ua)', 'Курс USD/UAH для модуля «Стоимость проекта»', 'HTTPS JSON GET, тайм-аут 10 с, раз в 23 ч', 'без ключа',
            'Обновление курса в «Стоимости проекта» (остаётся последний сохранённый)', True),
    'youtube': ('YouTube', 'Видео погибших и видео-попап: встраивание (iframe youtube-nocookie), превью, проверка ссылок', 'HTTPS (iframe, превью)', 'без ключа',
                'Просмотр видео в карточке и попапе; остальной сайт работает', True),
    'smtp': ('SMTP-сервер почты', 'Письма: код подтверждения регистрации, уведомления админу (заявки, оплаченные подарки), тест SMTP', 'SMTP / SMTPS (smtplib), тайм-аут 15 с',
             'smtp_host / smtp_user / smtp_pass в таблице colors (настройки админки)', 'Регистрация с подтверждением email, уведомления админу; заявки и оплаты сохраняются в БД', True),
    'google_analytics': ('Google Analytics 4 (gtag)', 'Аналитика посещений', 'HTTPS script (googletagmanager)', 'Measurement ID в страницах / настройке google_analytics_id',
                         'Только статистика GA; сайт работает (CSP частично блокирует doubleclick)', True),
    'google_fonts': ('Google Fonts', 'Шрифты (Cinzel для табличек тарифа, PT Serif / Roboto Condensed на doc-страницах, Unbounded / Manrope на промо)', 'HTTPS CSS / woff2', '—',
                     'Шрифты заменятся системными', True),
    'jsdelivr': ('CDN jsDelivr', 'Chart.js и SheetJS (xlsx) в админке', 'HTTPS script', '—', 'Графики статистики и экспорт/импорт Excel в админке', True),
    'carto': ('CARTO basemaps', 'Тайлы карты «Світ» и карт выбора точки (адрес — настройка worldmap_tile_url, с ключом)', 'HTTPS тайлы {z}/{x}/{y}', 'ключ CARTO в настройке worldmap_tile_url',
              'Подложка карты «Світ» (звёзды и управление работают; без ключа — «API KEY REQUIRED»)', True),
    'osm': ('Тайлы OpenStreetMap', 'Запасная подложка карт в админке (_admTileLayer) и пресет', 'HTTPS тайлы', '—', 'Запасная подложка', True),
    'wikimedia': ('Wikimedia Commons', 'Разовая загрузка изображений наград (setup_awards.py)', 'HTTPS GET', '—', 'Только утилита setup_awards.py; сайт использует локальные img/awards', True),
    'monobank': ('Monobank (банка)', 'Ссылка «Кофе админу» / донат', 'HTTPS ссылка', '—', 'Только переход по ссылке', True),
    'social': ('Соцсети (Facebook, X, Instagram, YouTube, Telegram, TikTok, LinkedIn, Viber)', 'Ссылки в соцпанели (адреса из настроек social_*_url) и «поделиться»', 'HTTPS ссылка', '—', 'Только переходы', True),
    'tiles_other': ('Прочие внешние ресурсы', 'Ссылки и ресурсы, не относящиеся к известным сервисам (Google Console, imgur и т. п.)', 'HTTPS', '—', '—', True),
}
DOMAIN_MAP = [
    (r'accounts\.google\.com|oauth2\.googleapis\.com|googleapis\.com/oauth2|googleapis\.com/userinfo', 'google_oauth'),
    (r'indexing\.googleapis\.com|googleapis\.com/auth/indexing', 'google_indexing'),
    (r'liqpay\.ua', 'liqpay'), (r'bank\.gov\.ua', 'nbu'),
    (r'youtube\.com|youtube-nocookie\.com|youtu\.be|ytimg\.com', 'youtube'),
    (r'googletagmanager\.com|analytics\.google\.com|google-analytics\.com|doubleclick\.net', 'google_analytics'),
    (r'fonts\.googleapis\.com|fonts\.gstatic\.com', 'google_fonts'),
    (r'cdn\.jsdelivr\.net|cdnjs\.cloudflare\.com|unpkg\.com', 'jsdelivr'),
    (r'cartocdn\.com|carto\.com', 'carto'), (r'openstreetmap\.org', 'osm'),
    (r'wikimedia\.org|wikipedia\.org', 'wikimedia'), (r'monobank\.ua', 'monobank'),
    (r'facebook\.com|twitter\.com|x\.com/|instagram\.com|t\.me|telegram|tiktok\.com|linkedin\.com|viber', 'social'),
    (r'www\.google\.com', 'google_search'),
]
IGNORE_DOMAINS = re.compile(r'schema\.org|sitemaps\.org|w3\.org|127\.0\.0\.1|localhost|^https?://user|example\.com|your-domain|xmlns|purl\.org|ogp\.me|https?://$')

def ext_service_for(url):
    if IGNORE_DOMAINS.search(url):
        return None
    for rx, sid in DOMAIN_MAP:
        if re.search(rx, url):
            return sid
    return 'tiles_other'

def ext_link(fid, url, f, ln, via=None, rel=None):
    if len(url) < 12 or '...' in url or '…' in url or not re.match(r'https?://[a-z0-9]', url, re.I):
        return
    sid = ext_service_for(url)
    if not sid:
        return
    eid = 'ext:' + sid
    if eid not in NODES:
        return
    if fid in NODES and NODES[fid]['type'] in ('pyfn', 'route', 'bgtask', 'middleware', 'tool'):
        r = rel or 'request'
    else:
        r = rel or 'depends'
    dom = re.sub(r'^https?://([^/]+).*', r'\1', url)
    edge(fid, eid, r, file=f, line=ln, note=(dom + (f' (через {via})' if via else '')))

def externals_and_infra():
    for sid, (name, purpose, proto, auth, fail, optional) in EXT.items():
        node('ext:' + sid, 'external', name, desc=purpose, proto=proto, auth=auth, fail=fail,
             optional='Сайт работает без него (частично)' if optional else 'Без него сайт не работает')
    infra = {
        'mysql': ('MySQL / MariaDB (zoryana_pamyat)', 'Основное хранилище: все записи, пользователи, настройки, переводы, подарки', 'Paskal.py get_db() — PooledDB(pymysql), maxconnections 50',
                  'Без БД не работает почти всё: карта (точки), карточки, поиск, вход, админка, настройки (сайт отвечает 500 на /api/*)'),
        'redis': ('Redis (кеш, необязательный)', 'Кеш ответов API (people, map_points, colors, SSR, sitemap…)', 'Paskal.py _get_redis() / cache_get / cache_set',
                  'Ничего не ломается: кеш отключается, все запросы идут в MySQL (выше нагрузка)'),
        'sessions': ('Сессии в памяти процесса (_sessions)', 'Сессии входа: cookie admin_session → пользователь', 'Paskal.py _sessions (dict + threading.Lock)',
                     'После перезапуска процесса все выходят из системы; при нескольких воркерах сессии не общие'),
        'fs': ('Файловая система сервера', 'Загруженные файлы (img/…: фото, логотипы, превью, подарки, призраки, награды), логи logs/security.log', 'open() / os.* в Paskal.py; StaticFiles',
               'Загрузка файлов, отдача статики'),
        'nginx': ('Nginx (zoryna-nginx.conf)', 'Обратный прокси, HTTPS, статика, WebSocket /ws/, страницы ошибок', 'proxy_pass → 127.0.0.1:8000', 'Сайт недоступен снаружи'),
        'uvicorn': ('Uvicorn / systemd (zoryna.service)', 'Процесс приложения: python -m uvicorn Paskal:app --port 8000 (один процесс)', 'zoryna.service ExecStart',
                    'Сайт полностью недоступен (502 от Nginx)'),
        'gunicorn': ('Gunicorn (gunicorn.conf.py)', 'Альтернативный запуск с несколькими воркерами (в zoryna.service не используется)', 'gunicorn.conf.py', '—'),
        'prometheus': ('Prometheus / Grafana', 'Сбор метрик с /metrics (prometheus.yml), дашборд grafana-dashboard.json', 'HTTP-опрос каждые 10 с', 'Только мониторинг'),
        'browser': ('Хранилище браузера (localStorage / cookie)', 'Язык, режим карты, отметки «видел», тур, подарки, свеча…', 'localStorage, document.cookie', 'Сбрасываются настройки посетителя'),
        'websocket': ('WebSocket /ws/online', 'Счётчик «онлайн» и события присутствия', 'WS через Nginx location /ws/', 'Счётчик «онлайн»; сайт работает'),
    }
    for iid, (name, purpose, impl, fail) in infra.items():
        node('infra:' + iid, 'infra', name, desc=purpose, impl=impl, fail=fail)
    edge('infra:nginx', 'infra:uvicorn', 'request', file='zoryna-nginx.conf', note='proxy_pass zoryna_backend')
    edge('infra:uvicorn', 'infra:mysql', 'depends', file='Paskal.py', line=94, note='get_db()')
    edge('infra:uvicorn', 'infra:redis', 'depends', status='code', file='Paskal.py', line=110, note='необязательно')
    edge('infra:uvicorn', 'infra:sessions', 'depends', file='Paskal.py')
    edge('infra:prometheus', 'route:GET /metrics', 'request', file='prometheus.yml', note='опрос каждые 10 с')
    edge('infra:nginx', 'infra:websocket', 'request', file='zoryna-nginx.conf', note='location /ws/')


def py_extra_infra():
    """Файли, сесії, кеш — з ast функцій бекенду."""
    for fid, info in PY_FUNCS.items():
        fn = info['node']
        f = info['file']
        for sub in ast.walk(fn):
            if isinstance(sub, ast.Call):
                nm = ast.unparse(sub.func)
                if nm == 'open' and len(sub.args) > 1 and isinstance(sub.args[1], ast.Constant) and any(ch in str(sub.args[1].value) for ch in 'wa'):
                    edge(fid, 'infra:fs', 'writes', file=f, line=sub.lineno, note='запись файла')
                elif nm in ('os.remove', 'os.unlink', 'shutil.rmtree'):
                    edge(fid, 'infra:fs', 'deletes', file=f, line=sub.lineno, note=nm)
                elif nm in ('shutil.copyfileobj', 'shutil.copy', 'shutil.move'):
                    edge(fid, 'infra:fs', 'writes', file=f, line=sub.lineno, note=nm)
            elif isinstance(sub, ast.Name) and sub.id == '_sessions':
                edge(fid, 'infra:sessions', 'depends', file=f, line=sub.lineno)

# ─────────────────────────── СТОРІНКИ Й ФРОНТЕНД ───────────────────────────
PAGES = [
    # файл, назва, призначення
    ('index.html', 'Главная (ПК и телефон)', 'Интерактивная карта Украины / «Світ», звёзды погибших, поиск, боковая карточка, вход, «Добавить запись», чат, дым, призраки'),
    ('mobile.html', 'Версия для планшетов (/mobile)', 'Та же карта с нижней навигацией и листом карточки'),
    ('admin.html', 'Админ-панель (/admin)', 'Управление записями, модерацией, пользователями, настройками и модулями'),
    ('card.html', 'Страница мемориала (card?slug=)', 'Полная карточка погибшего, свеча памяти, награды, «Подарки погибшему»'),
    ('profile.html', 'Профиль пользователя (/user/{nickname})', 'Публичный профиль, «Наследие памяти»'),
    ('templates/memorial.html', 'SSR-страница мемориала (/memorial/{slug})', 'Серверный HTML для Google и шеринга; переадресация на карту'),
    ('faq.html', 'FAQ', 'Документ-страница'), ('rules.html', 'Правила', 'Документ-страница'), ('terms.html', 'Условия использования', 'Документ-страница'),
    ('how-to-add.html', 'Как добавить погибшего', 'Инструкция'), ('privacy-policy.html', 'Политика конфиденциальности', 'Документ-страница'),
    ('pricing/index.html', 'Тарифы (/pricing/)', 'Тарифные планы и форма заявки'), ('promo/index.html', 'Промо (/promo/)', 'Лендинг'),
    ('portfolio/index.html', 'Портфолио (/portfolio/)', 'Страница автора, благодарности'), ('update_v/uddate_history.html', 'История обновлений (/update_v/…)', 'Публичный журнал версий'),
    ('offline.html', 'Офлайн-страница', 'Показывается без сети'), ('404.html', 'Ошибка 404', 'Nginx / приложение'), ('403.html', 'Ошибка 403', ''),
    ('429.html', 'Ошибка 429', 'Превышен лимит запросов'), ('500.html', 'Ошибка 500', ''), ('ud.html', 'ud.html (служебная)', 'Назначение автоматически не определено'),
    ('load-test.html', 'Нагрузочный тест (служебная)', 'Инструмент разработчика'),
]
VENDOR = {'js/leaflet.js': ('lib:leaflet', 'Leaflet 1.9.4 (карты)'), 'js/dat.gui.min.js': ('lib:datgui', 'dat.GUI (панель настроек дыма)'),
          'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js': ('lib:chartjs', 'Chart.js 4.4 (графики админки)'),
          'https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js': ('lib:xlsx', 'SheetJS xlsx (Excel в админке)')}

def register_pages():
    for f, name, purpose in PAGES:
        if os.path.exists(os.path.join(ROOT, f)):
            node('page:' + f, 'page', name, file=f, line=1, desc=purpose)
    for (_, (lid, lname)) in VENDOR.items():
        node(lid, 'lib', lname, desc='Сторонняя библиотека')
    # статичні монтування → сторінки
    for r in ROUTES:
        if r['method'] == 'STATIC':
            idx = r['path'].strip('/') + '/index.html'
            if 'page:' + idx in NODES:
                edge(r['id'], 'page:' + idx, 'serves', file='Paskal.py', line=NODES[r['id']].get('line'))
            if r['path'] == '/update_v':
                edge(r['id'], 'page:update_v/uddate_history.html', 'serves', file='Paskal.py', line=NODES[r['id']].get('line'))


class UIParser(HTMLParser):
    INTERACTIVE = {'button', 'a', 'input', 'select', 'textarea', 'form', 'summary'}

    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.text = text
        self.stack = []        # [tag, id, classes, line, elem_record]
        self.elems = []
        self.ids = {}           # id → (line, group)
        self.recent = ''
        self.sec_titles = {}
        self.cur_title = None

    VOID = {'input', 'img', 'br', 'hr', 'meta', 'link', 'source', 'area', 'base', 'col', 'embed', 'param', 'track', 'wbr'}

    def group(self):
        for t in self.stack:
            if t[1] and t[1].startswith('sec-'):
                return t[1]
        for t in self.stack:          # найзовнішній з id
            if t[1] and t[0] not in ('html', 'body'):
                return t[1]
        return None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        line = self.getpos()[0]
        eid = a.get('id')
        rec = None
        has_on = any(k.startswith('on') for k in a)
        if (tag in self.INTERACTIVE or has_on or a.get('role') == 'button') and not (tag == 'input' and a.get('type') == 'hidden'):
            rec = {'tag': tag, 'attrs': a, 'line': line, 'group': None, 'text': '', 'recent': self.recent.strip()[-70:]}
            self.elems.append(rec)
        if eid:
            self.ids[eid] = (line, None)
        self.stack.append([tag, eid, a.get('class', ''), line, rec])
        if rec is not None:
            rec['group'] = self.group()
        if eid:
            self.ids[eid] = (line, self.group())
        if 'sec-title' in (a.get('class') or ''):
            self.cur_title = self.group()
            self.sec_titles.setdefault(self.cur_title, '')
        if tag in self.VOID:
            self.stack.pop()

    def handle_endtag(self, tag):
        for k in range(len(self.stack) - 1, -1, -1):
            if self.stack[k][0] == tag:
                if 'sec-title' in (self.stack[k][2] or ''):
                    self.cur_title = None
                del self.stack[k:]
                break

    def handle_data(self, data):
        if self.stack and self.stack[-1][0] in ('script', 'style'):
            return
        s = ' '.join(data.split())
        if not s:
            return
        self.recent = (self.recent + ' ' + s)[-200:]
        for t in self.stack:
            if t[4] is not None and len(t[4]['text']) < 80:
                t[4]['text'] = (t[4]['text'] + ' ' + s).strip()
        if self.cur_title is not None and len(self.sec_titles[self.cur_title]) < 60:
            self.sec_titles[self.cur_title] = (self.sec_titles[self.cur_title] + ' ' + s).strip()


def strip_tpl(s):
    """${…} (з вкладеними дужками) → X"""
    out = []
    i = 0
    while i < len(s):
        if s.startswith('${', i):
            d = 0
            j = i + 1
            while j < len(s):
                if s[j] == '{':
                    d += 1
                elif s[j] == '}':
                    d -= 1
                    if d == 0:
                        break
                j += 1
            out.append('X')
            i = j + 1
        else:
            out.append(s[i])
            i += 1
    return ''.join(out)

def js_url_paths(lit_text):
    """→ [(нормалізований шлях, позиція, чи закінчувався на /)] для рядка/шаблону з /api/… або /ws/…"""
    res = []
    t = strip_tpl(lit_text)
    for m in re.finditer(r'(/(?:api|ws)\b[^\s\'"`<>?#]*)', t):
        p = m.group(1)
        slash = p.endswith('/')
        p = p.rstrip('/') or '/'
        res.append((p, m.start(), slash))
    return res

def match_route(path, method):
    cands = [r for r in ROUTES if r['method'] not in ('STATIC',) and r['rx'].match(path)]
    exact = [r for r in cands if r['method'] == method]
    if exact:
        return exact, 'code'
    if cands:
        return cands, 'assumed'
    return [], None


def frontend():
    page_files = [p for p, _, _ in PAGES if os.path.exists(os.path.join(ROOT, p))]
    file_cache = {}

    def scan_file(fname, code, base):
        key = (fname, base)
        if key in file_cache:
            return file_cache[key]
        masked, lits = mask_js(code)
        funcs = find_functions(masked)
        # вкладеність
        for fn in funcs:
            fn['parent'] = None
            best = None
            for g in funcs:
                if g is fn:
                    continue
                if g['body_start'] < fn['start'] and fn['body_end'] <= g['body_end']:
                    if best is None or g['body_start'] > best['body_start']:
                        best = g
            fn['parent'] = best
        # анонімні обробники подій: X.addEventListener('evt', fn) / X.onclick = fn / map.on('evt', fn)
        anon = []
        for m in re.finditer(r'([\w$.\]\)]+)\s*\.\s*addEventListener\s*\(\s*', masked):
            lit = next((l for l in lits if l[0] == m.end()), None)
            if not lit:
                continue
            k = lit[1]
            mm = re.compile(r'\s*,\s*(?:async\s*)?').match(masked, k)
            if not mm:
                continue
            from jsscan import _body_after
            span = _body_after(masked, mm.end())
            if span:
                tgt = m.group(1)[-40:]
                anon.append({'name': f'{tgt}:{lit[2]}', 'start': m.start(), 'body_start': span[0], 'body_end': span[1], 'kind': 'listener', 'event': lit[2], 'target': tgt})
        for m in re.finditer(r'([\w$.\]\)]+)\.on(\w+)\s*=\s*(?:async\s*)?', masked):
            from jsscan import _body_after
            if m.group(2) in ('load', 'error') and 'Image' in masked[max(0, m.start() - 80):m.start()]:
                pass
            span = _body_after(masked, m.end())
            if span and (masked[m.end():m.end() + 8].startswith('function') or masked[m.end()] in '(' or re.match(r'[\w$]+\s*=>', masked[m.end():m.end() + 30])):
                anon.append({'name': f'{m.group(1)[-40:]}.on{m.group(2)}', 'start': m.start(), 'body_start': span[0], 'body_end': span[1], 'kind': 'listener', 'event': m.group(2), 'target': m.group(1)})
        for fn in anon:
            fn['parent'] = None
            best = None
            for g in funcs:
                if g['body_start'] < fn['start'] and fn['body_end'] <= g['body_end']:
                    if best is None or g['body_start'] > best['body_start']:
                        best = g
            fn['parent'] = best
        allf = funcs + anon
        for fn in allf:
            nm = fn['name']
            p = fn['parent']
            chain = []
            while p is not None:
                chain.insert(0, p['name'])
                p = p['parent']
            fn['qual'] = '>'.join(chain + [nm])
            fn['abs_line'] = line_of(FILE_TEXT[fname], base + fn['start'])
            fn['id'] = f'js:{fname}#{fn["qual"]}' + (f'@{fn["abs_line"]}' if fn['kind'] == 'listener' else '')
        # константи верхнього рівня → рядки (для налаштувань)
        consts = {}
        for m in re.finditer(r'(?m)^\s*(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=', masked):
            if any(f2['body_start'] < m.start() < f2['body_end'] for f2 in funcs):
                continue
            end = masked.find(';\n', m.end())
            end = len(masked) if end < 0 else end
            if end - m.end() > 20000:
                end = m.end() + 20000
            consts[m.group(1)] = [l[2] for l in lits if m.end() <= l[0] < end]
        res = {'masked': masked, 'lits': lits, 'funcs': allf, 'consts': consts, 'code': code, 'base': base}
        file_cache[key] = res
        return res

    FILE_TEXT.clear()
    dyn_count = defaultdict(int)
    js_seen = set()
    for pf in page_files:
        text = rd(pf)
        FILE_TEXT[pf] = text
        pid = 'page:' + pf
        # скрипти сторінки
        scripts = []
        for m in re.finditer(r'<script\b([^>]*)>(.*?)</script>', text, re.S | re.I):
            attrs = m.group(1)
            sm = re.search(r'\bsrc\s*=\s*["\']([^"\']+)["\']', attrs)
            if sm:
                src = sm.group(1).split('?')[0]
                if src.startswith('http'):
                    if src in VENDOR:
                        edge(pid, VENDOR[src][0], 'loads', file=pf, line=line_of(text, m.start()))
                        ext_link(VENDOR[src][0], src, pf, line_of(text, m.start()), rel='loads')
                    else:
                        node_ext_page(pid, src, pf, line_of(text, m.start()), 'loads')
                    continue
                rel = src.lstrip('/')
                if not os.path.exists(os.path.join(ROOT, rel)):
                    rel2 = os.path.normpath(os.path.join(os.path.dirname(pf), src)).replace('\\', '/')
                    rel = rel2 if os.path.exists(os.path.join(ROOT, rel2)) else rel
                if rel in VENDOR:
                    edge(pid, VENDOR[rel][0], 'loads', file=pf, line=line_of(text, m.start()))
                    continue
                if os.path.exists(os.path.join(ROOT, rel)):
                    if rel not in FILE_TEXT:
                        FILE_TEXT[rel] = rd(rel)
                    scripts.append((rel, FILE_TEXT[rel], 0))
                    node('jsfile:' + rel, 'jsfile', rel, file=rel, line=1, desc='Подключённый JS-файл')
                    edge(pid, 'jsfile:' + rel, 'loads', file=pf, line=line_of(text, m.start()))
                else:
                    NODES[pid].setdefault('missing', []).append(src)
            else:
                if 'application/ld+json' in attrs or 'text/template' in attrs:
                    continue
                scripts.append((pf, m.group(2), m.start(2)))
        for m in re.finditer(r'<link\b[^>]*href\s*=\s*["\'](https?://[^"\']+)["\']', text, re.I):
            node_ext_page(pid, m.group(1), pf, line_of(text, m.start()), 'loads')
        for m in re.finditer(r'<iframe\b[^>]*src\s*=\s*["\'](https?://[^"\']+)["\']', text, re.I):
            node_ext_page(pid, m.group(1), pf, line_of(text, m.start()), 'depends')
        scanned = [scan_file(f, code, base) for f, code, base in scripts]
        # глобальна таблиця імен сторінки
        gmap = {}
        for sc, (f, _, _) in zip(scanned, scripts):
            for fn in sc['funcs']:
                # window.X = function… глобальна навіть усередині обгортки (function(){ … })()
                if (fn['parent'] is None or fn['kind'] == 'window') and fn['kind'] != 'listener':
                    if fn['name'] not in gmap or f == pf:
                        gmap[fn['name']] = fn['id']
        for sc, (f, _, _) in zip(scanned, scripts):
            text_f = FILE_TEXT[f]
            for fn in sc['funcs']:
                if fn['id'] in js_seen:
                    continue
                desc = js_comment_above(text_f, sc['base'] + fn['start'])
                ntype = 'jsfn'
                label = fn['qual'].split('>')[-1] if fn['kind'] != 'listener' else f"⚡ {fn['target']} «{fn['event']}»"
                node(fn['id'], ntype, label, file=f, line=fn['abs_line'], desc=desc, lang='js',
                     kind={'listener': 'обработчик события', 'method': 'метод объекта', 'window': 'глобальная (window.*)'}.get(fn['kind'], 'функция'),
                     parent=(fn['parent']['id'] if fn['parent'] else None))
                if fn['parent']:
                    edge(fn['parent']['id'], fn['id'], 'calls', file=f, line=fn['abs_line'], note='вложенная функция / обработчик, зарегистрированный здесь')
        # (init) — код верхнього рівня кожного скрипту
        for sc, (f, code, base) in zip(scanned, scripts):
            iid = f'js:{f}#(init)' if f != pf else f'js:{pf}#(init@{line_of(FILE_TEXT[f], base)})'
            node(iid, 'jsinit', f'(загрузка) {os.path.basename(f)}' + ('' if f != pf else f' :{line_of(FILE_TEXT[f], base)}'),
                 file=f, line=line_of(FILE_TEXT[f], base), desc='Код верхнего уровня: выполняется при загрузке страницы')
            edge(pid, iid, 'starts', file=f, line=line_of(FILE_TEXT[f], base), note='выполняется при загрузке')
        # аналіз тіл
        for sc, (f, code, base) in zip(scanned, scripts):
            text_f = FILE_TEXT[f]
            masked, lits = sc['masked'], sc['lits']
            funcs = sorted(sc['funcs'], key=lambda x: x['body_start'])
            local_names = defaultdict(dict)     # parent_id → name → id
            for fn in funcs:
                if fn['parent']:
                    local_names[fn['parent']['id']][fn['name']] = fn['id']
            iid = f'js:{f}#(init)' if f != pf else f'js:{pf}#(init@{line_of(text_f, base)})'

            def owner(pos):
                best = None
                for fn in funcs:
                    if fn['body_start'] <= pos <= fn['body_end']:
                        if best is None or fn['body_start'] >= best['body_start']:
                            best = fn
                return best

            def resolve(name, own):
                o = own
                while o is not None:
                    if name in local_names.get(o['id'], {}):
                        return local_names[o['id']][name]
                    o = o['parent']
                if name in local_names.get(None, {}):
                    return local_names[None][name]
                return gmap.get(name)

            if f != pf and f in js_seen:
                continue
            for name, off, kind in calls_in(masked):
                own = owner(off)
                src_id = own['id'] if own else iid
                tgt = resolve(name, own)
                if tgt and tgt != src_id:
                    edge(src_id, tgt, 'calls', file=f, line=line_of(text_f, base + off), note=('ссылка (колбэк)' if kind == 'ref' else None))
            # рядки / шаблони
            fn_keycount = defaultdict(int)
            for (ls, le, lt, lk) in lits:
                if lt in SETTINGS:
                    o = owner(ls)
                    if o:
                        fn_keycount[o['id']] += 1
            for (ls, le, lt, lk) in lits:
                own = owner(ls)
                src_id = own['id'] if own else iid
                ln = line_of(text_f, base + ls)
                admin_writer = f in ADMIN_FILES and own is not None and re.search(r'colors/batch|onClrChange|_autoSaveToDb', code[own['body_start']:own['body_end']])
                many_keys = f in ADMIN_FILES and own is not None and fn_keycount.get(own['id'], 0) >= 3
                if lt in SETTINGS and (many_keys or SHORT_OK.match(lt) or len(lt) > 7 or re.search(r"(?:\bc|getC|gc|g|_stN|COLORS)\(\s*$|COLORS\[\s*$|key\s*:\s*$|onClrChange\(\s*$", code[max(0, ls - 20):ls])):
                    edge(src_id, 'set:' + lt, 'writes' if admin_writer else 'reads', file=f, line=ln)
                else:
                    # динамічні ключі: 'social_' + id / `social_${id}_url`
                    pat = None
                    st_ = strip_tpl(lt) if lk == 'tpl' else lt
                    if re.fullmatch(r'[a-z]+_(?:[a-z0-9]+_)*', st_) and re.match(r'\s*\+', code[le:le + 4]):
                        pat = re.escape(st_) + r'[a-z0-9_]+'
                    elif lk == 'tpl' and re.fullmatch(r'[a-z0-9_]*X[a-z0-9_X]*', st_) and len(st_.replace('X', '')) >= 5:
                        pat = re.escape(st_).replace('X', '[a-z0-9]+')
                    if pat:
                        for k in SETTINGS:
                            if re.fullmatch(pat, k):
                                edge(src_id, 'set:' + k, 'writes' if admin_writer else 'reads', status='assumed', file=f, line=ln, note=f'динамический ключ «{st_}…»')
                for path, p, slash in js_url_paths(lt):
                    after = code[le:le + 400]
                    cut = after.find('fetch(')
                    if cut > 0:
                        after = after[:cut]
                    # метод: 'POST' або обраний у коді — method: id != null ? 'PUT' : 'POST' (пробуємо кожен)
                    mm = re.search(r"(?<![\w$])method\s*:\s*([^,}\n]+)", after[:300])
                    methods = [x.upper() for x in re.findall(r"['\"]([A-Za-z]+)['\"]", mm.group(1))] if mm else []
                    methods = list(dict.fromkeys(methods)) or ['GET']
                    ctx_before = code[max(0, ls - 40):ls]
                    if 'WebSocket' in ctx_before or path.startswith('/ws/'):
                        methods = ['WS']
                    if 'sendBeacon' in ctx_before:
                        methods = ['POST']
                    cands = [path]
                    if slash:      # '/api/x/' + id + '/y' — склеюємо з наступним літералом
                        nl_ = next((l for l in lits if le < l[0] < le + 80 and l[2].startswith('/')), None)
                        if nl_:
                            cands.insert(0, path + '/X' + strip_tpl(nl_[2]).split('?')[0].rstrip('/'))
                        cands.insert(1 if nl_ else 0, path + '/X')
                    rs, st = [], None
                    for cp in cands:
                        for meth in methods:
                            r_, s_ = match_route(cp, meth)
                            rs += r_
                            st = st or (s_ if r_ else None)
                        if rs:
                            path = cp
                            break
                    method = '/'.join(methods)
                    for r in rs:
                        edge(src_id, r['id'], 'request', status=st, file=f, line=ln, note=f'{method} {path}')
                    if not rs and path.startswith('/api/'):
                        NODES[src_id].setdefault('unmatched_api', []).append(f'{method} {path}')
                for u in re.findall(r'https?://[^\s\'"`<>${}]+', lt):
                    ext_link(src_id, u, f, ln)
                # динамічні елементи інтерфейсу в шаблонах
                if lk == 'tpl' or '<' in lt:
                    for tm in re.finditer(r'<(button|a|input|select|textarea|label|div|span|td|tr|li|img|i|svg|summary)\b((?:[^<>"\']|"[^"]*"|\'[^\']*\')*)>', lt):
                        tag, attrs = tm.group(1), tm.group(2)
                        ons = re.findall(r'\b(on\w+)\s*=\s*"([^"]*)"', attrs) + re.findall(r"\b(on\w+)\s*=\s*'([^']*)'", attrs)
                        if not ons and tag not in ('button', 'a', 'input', 'select', 'textarea'):
                            continue
                        if tag == 'input' and re.search(r'type\s*=\s*["\']hidden', attrs):
                            continue
                        dyn_count[src_id] += 1
                        did = f'dyn:{src_id}#{dyn_count[src_id]}'
                        label = dyn_label(tag, attrs, lt[tm.end():tm.end() + 160])
                        node(did, 'uidyn', label, file=f, line=ln, tag=tag, desc=f'Элемент, который рисует {NODES[src_id]["label"]}()',
                             page=pf)
                        edge(src_id, did, 'renders', file=f, line=ln)
                        for ev, hcode in ons:
                            hm, _ = mask_js(re.sub(r'\$\{[^}]*\}', '0', html.unescape(hcode)))
                            for name, _, kind in calls_in(hm):
                                tgt = resolve(name, None) or gmap.get(name)
                                if tgt:
                                    edge(did, tgt, 'triggers', file=f, line=ln, note=ev)
                            for k in re.findall(r"'([a-z][a-z0-9_]+)'", hcode):
                                if k in SETTINGS:
                                    edge(did, 'set:' + k, 'writes' if 'onClrChange' in hcode else 'reads', file=f, line=ln)
                        hm2 = re.search(r'\bhref\s*=\s*["\']([^"\']+)', attrs)
                        if hm2:
                            link_target(did, hm2.group(1), f, ln)
            # константи → налаштування
            for name, strs in sc['consts'].items():
                keys = [s for s in strs if s in SETTINGS and (SHORT_OK.match(s) or len(s) > 7)]
                if not keys:
                    continue
                for m in re.finditer(r'(?<![\w$.])' + re.escape(name) + r'(?![\w$])', masked):
                    own = owner(m.start())
                    if not own:
                        continue
                    wr = f in ADMIN_FILES and re.search(r'colors/batch|onClrChange', code[own['body_start']:own['body_end']])
                    for k in keys:
                        edge(own['id'], 'set:' + k, 'writes' if wr else 'reads', file=f, line=line_of(text_f, base + m.start()), note=f'через {name}')
            # властивості-налаштування: d.card_gifts_enabled, S.recent_days …
            for m in re.finditer(r'\.([a-z][a-z0-9]*_[a-z0-9_]+)\b', masked):
                if m.group(1) in SETTINGS:
                    own = owner(m.start())
                    edge(own['id'] if own else iid, 'set:' + m.group(1), 'reads', file=f, line=line_of(text_f, base + m.start()), note='свойство объекта настроек')
            # localStorage / BroadcastChannel
            for m in re.finditer(r'localStorage\s*\.\s*(getItem|setItem|removeItem)\s*\(', masked):
                lit = next((l for l in lits if l[0] >= m.end() and l[0] - m.end() < 4), None)
                if lit:
                    sid = 'ls:' + lit[2]
                    node(sid, 'storage', 'localStorage: ' + lit[2], desc='Ключ в хранилище браузера посетителя')
                    edge(sid, 'infra:browser', 'stored', file=f, line=line_of(text_f, base + m.start()))
                    own = owner(m.start())
                    edge(own['id'] if own else iid, sid, 'reads' if m.group(1) == 'getItem' else 'writes', file=f, line=line_of(text_f, base + m.start()))
            for m in re.finditer(r'BroadcastChannel\s*\(', masked):
                lit = next((l for l in lits if l[0] >= m.end() and l[0] - m.end() < 4), None)
                if lit:
                    sid = 'bc:' + lit[2]
                    node(sid, 'channel', 'BroadcastChannel: ' + lit[2], desc='Канал между вкладками одного браузера (админка → сайт вживую)')
                    own = owner(m.start())
                    edge(own['id'] if own else iid, sid, 'depends', file=f, line=line_of(text_f, base + m.start()))
            # getElementById('x') → елементи інтерфейсу (заповнюється пізніше)
            for m in re.finditer(r'getElementById\s*\(', masked):
                lit = next((l for l in lits if l[0] >= m.end() and l[0] - m.end() < 4), None)
                if lit:
                    own = owner(m.start())
                    after = masked[lit[1]:lit[1] + 120]
                    PENDING_IDS.append((pf, lit[2], own['id'] if own else iid, f, line_of(text_f, base + m.start()), after))
            if f != pf:
                js_seen.add(f)
        js_seen.update(fn['id'] for sc in scanned for fn in sc['funcs'])
        # статична розмітка
        ui = UIParser(text)
        try:
            ui.feed(text)
        except Exception as e:
            NODES[pid]['note'] = f'HTML разобран частично: {e}'
        PAGE_IDS[pf] = ui.ids
        groups_made = set()
        for el in ui.elems:
            a = el['attrs']
            grp = el['group']
            gid = f'grp:{pf}#{grp}' if grp else f'grp:{pf}#(сторінка)'
            if gid not in groups_made:
                glabel = (ui.sec_titles.get(grp) or ('#' + grp if grp else '(без контейнера)'))
                node(gid, 'uigroup', glabel, file=pf, line=ui.ids.get(grp, (None,))[0] if grp else None, page=pf,
                     desc=('Раздел админки ' if grp and grp.startswith('sec-') else 'Блок интерфейса ') + (grp or ''))
                edge(pid, gid, 'contains', file=pf)
                groups_made.add(gid)
            eid = f'ui:{pf}#L{el["line"]}:{el["tag"]}' + (f'#{a["id"]}' if a.get('id') else '')
            label = ui_label(el)
            node(eid, 'ui', label, file=pf, line=el['line'], tag=el['tag'], page=pf, group=gid,
                 desc=('Тип: ' + ui_kind(el)) + (f' · id={a["id"]}' if a.get('id') else ''))
            edge(gid, eid, 'contains', file=pf, line=el['line'])
            if a.get('id'):
                UI_BY_ID[(pf, a['id'])] = eid
            for k, v in a.items():
                if k.startswith('on') and v:
                    hm, _ = mask_js(v)
                    for name, _, kind in calls_in(hm):
                        tgt = gmap.get(name)
                        if tgt:
                            edge(eid, tgt, 'triggers', file=pf, line=el['line'], note=k)
                    for kk in re.findall(r"'([a-z][a-z0-9_]+)'", v):
                        if kk in SETTINGS:
                            edge(eid, 'set:' + kk, 'writes' if 'onClrChange' in v else 'reads', file=pf, line=el['line'])
                    for path, _, _ in js_url_paths(v):
                        rs, st = match_route(path, 'GET')
                        for r in rs:
                            edge(eid, r['id'], 'request', status=st, file=pf, line=el['line'])
            if a.get('href'):
                link_target(eid, a['href'], pf, el['line'])
            if el['tag'] == 'form' and a.get('action'):
                link_target(eid, a['action'], pf, el['line'])
        # контейнери груп (для привʼязки динамічних елементів)
        for gidr, (ln, grp) in ui.ids.items():
            GROUP_OF_ID[(pf, gidr)] = grp
        # showSec у адмінці: розділ → функції завантаження
        if pf == 'admin.html':
            sm = re.search(r'function showSec\(id\)\s*\{', text)
            if sm:
                body_end = match_brace(text, sm.end() - 1)
                body = text[sm.end():body_end]
                for mm in re.finditer(r"if\s*\(\s*id\s*===\s*'(\w+)'\s*\)\s*(\{[^{}]*\}|[^;\n]+;)", body):
                    sec = 'sec-' + mm.group(1)
                    gid = f'grp:{pf}#{sec}'
                    if gid not in NODES:
                        continue
                    hm, _ = mask_js(mm.group(2))
                    for name, _, _ in calls_in(hm):
                        tgt = gmap.get(name)
                        if tgt:
                            edge(gid, tgt, 'calls', file=pf, line=line_of(text, sm.end() + mm.start()), note='при открытии раздела (showSec)')
                            NODES[tgt].setdefault('groups', []).append(gid)


ADMIN_FILES = {'admin.html', 'js/chat-admin.js', 'js/admin-sounds.js', 'js/admin-mem.js'}
FILE_TEXT = {}
PENDING_IDS = []
PAGE_IDS = {}
UI_BY_ID = {}
GROUP_OF_ID = {}

def js_comment_above(text, pos):
    ls = text.rfind('\n', 0, pos) + 1
    k = ls - 1
    res = []
    for _ in range(8):
        prev_ls = text.rfind('\n', 0, k) + 1
        ln = text[prev_ls:k].strip()
        if ln.startswith('//'):
            res.insert(0, ln.lstrip('/').strip())
        elif ln.endswith('*/') or ln.startswith('*') or ln.startswith('/*'):
            res.insert(0, ln.strip('/*').strip())
            if ln.startswith('/*'):
                break
        else:
            break
        k = prev_ls - 1
        if k <= 0:
            break
    return ' '.join(x for x in res if x)[:400]

def ui_kind(el):
    t, a = el['tag'], el['attrs']
    if t == 'input':
        ty = (a.get('type') or 'text').lower()
        return {'checkbox': 'переключатель (checkbox)', 'radio': 'переключатель (radio)', 'range': 'ползунок', 'file': 'загрузка файла',
                'color': 'выбор цвета', 'number': 'числовое поле', 'submit': 'кнопка'}.get(ty, f'поле ({ty})')
    return {'button': 'кнопка', 'a': 'ссылка', 'select': 'список', 'textarea': 'текстовое поле', 'form': 'форма', 'summary': 'раскрытие'}.get(t, f'элемент <{t}> с обработчиком')

def ui_label(el):
    a = el['attrs']
    for k in ('aria-label', 'title', 'placeholder', 'data-hint', 'alt'):
        if a.get(k):
            return clean(a[k])
    if el['text'].strip():
        return clean(el['text'])
    if a.get('value') and el['tag'] == 'input' and a.get('type') in ('submit', 'button'):
        return clean(a['value'])
    if a.get('data-i18n'):
        return a['data-i18n']
    if el['recent'] and el['tag'] in ('input', 'select', 'textarea'):
        return clean(el['recent'][-50:]) + ' ▸ ' + ui_kind(el)
    if a.get('id'):
        return '#' + a['id']
    return f'<{el["tag"]}>'

def dyn_label(tag, attrs, after):
    for k in ('title', 'aria-label', 'placeholder', 'data-hint'):
        m = re.search(r'\b' + k + r'\s*=\s*"([^"]*)"', attrs)
        if m and m.group(1).strip():
            return clean(re.sub(r'\$\{[^}]*\}', '…', m.group(1)))
    txt = re.sub(r'<[^>]*>', ' ', after.split('</' + tag)[0])
    txt = re.sub(r'\$\{[^}]*\}', '…', txt)
    txt = clean(txt)
    if txt and txt != '…':
        return txt
    m = re.search(r'\bon\w+\s*=\s*"([^"(]*)', attrs)
    return f'<{tag}> {m.group(1)}()' if m else f'<{tag}>'

def clean(s):
    s = html.unescape(s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s[:60] + ('…' if len(s) > 60 else '')

def link_target(src, href, f, ln):
    href = href.strip()
    if not href or href.startswith(('#', 'javascript:', 'mailto:', 'tel:', '${')):
        return
    if href.startswith('http'):
        ext_link(src, href, f, ln, rel='navigates')
        return
    p = strip_tpl(href).split('?')[0].split('#')[0]
    cand = [p.lstrip('/'), p.lstrip('/') + 'index.html', p.lstrip('/') + '/index.html']
    for c in cand:
        if 'page:' + c in NODES:
            edge(src, 'page:' + c, 'navigates', file=f, line=ln)
            return
    rs, st = match_route(p.rstrip('/') or '/', 'GET')
    for r in rs:
        edge(src, r['id'], 'navigates', status=st, file=f, line=ln)

def node_ext_page(pid, url, f, ln, rel):
    ext_link(pid, url, f, ln, rel=rel)

def resolve_pending_ids():
    """getElementById('x') у функціях → зв'язок з елементом інтерфейсу / групою"""
    for pf, eid, src_id, f, ln, after in PENDING_IDS:
        tgt = UI_BY_ID.get((pf, eid))
        rel = 'updates'
        if tgt:
            edge(src_id, tgt, rel, file=f, line=ln, note='#' + eid)
            NODES[src_id].setdefault('groups', [])
            g = NODES[tgt].get('group')
            if g and g not in NODES[src_id]['groups']:
                NODES[src_id]['groups'].append(g)
            continue
        grp = GROUP_OF_ID.get((pf, eid))
        if grp:
            gid = f'grp:{pf}#{grp}'
            if gid in NODES:
                NODES[src_id].setdefault('groups', [])
                if gid not in NODES[src_id]['groups']:
                    NODES[src_id]['groups'].append(gid)
                if re.match(r'\s*\)?\s*\??\.\s*(innerHTML|insertAdjacentHTML|appendChild|textContent)', after):
                    edge(src_id, gid, 'updates', file=f, line=ln, note='#' + eid)
    # функції, які викликаються з елементів групи
    for e in list(EDGES.values()):
        if e['rel'] == 'triggers':
            g = NODES[e['s']].get('group') or (NODES[e['s']].get('page') and None)
            if g:
                gl = NODES[e['t']].setdefault('groups', [])
                if g not in gl:
                    gl.append(g)
    # динамічні елементи → група функції-рендерера
    for e in list(EDGES.values()):
        if e['rel'] == 'renders':
            gl = NODES[e['s']].get('groups') or []
            if gl:
                NODES[e['t']]['group'] = gl[0]

# ─────────────────────────── ЗБИРАННЯ ───────────────────────────
REL_RU = {
    'calls': 'вызывает', 'handles': 'вызывает (обработчик)', 'request': 'отправляет запрос', 'reads': 'читает', 'writes': 'изменяет',
    'deletes': 'удаляет', 'creates': 'создаёт (DDL)', 'depends': 'зависит от', 'triggers': 'вызывает (событие)', 'renders': 'рисует',
    'contains': 'содержит', 'navigates': 'переходит', 'serves': 'отдаёт страницу', 'starts': 'запускает', 'stored': 'хранится в',
    'loads': 'загружает', 'updates': 'обновляет интерфейс',
}

DOMAINS = [
    ('gifts', 'Подарки погибшему', r'gift|liqpay'), ('seo', 'SEO, sitemap, SSR', r'seo|sitemap|robots|indexing|slug|ssr|memorial_page|_build_memorial'),
    ('chat', 'Микро-чат и онлайн', r'chat|ws_online|_ping|online|bot_phrase|banned'), ('legacy', 'Наследие памяти', r'legacy'),
    ('auth', 'Вход, регистрация, сессии, пользователи', r'auth|login|logout|register|oauth|session|password|_user|users|nick|profile|require_|ban|verify|email_code'),
    ('memorials', 'Записи погибших, карта, поиск, лайки', r'memorial|people|person|map_points|search|like|award|approve|pending|tier|recent|import|export|csv'),
    ('settings', 'Настройки (colors), устройства, техработы', r'color|setting|device|maintenance|tour|addmode|add_person_mode'),
    ('geo', 'Города, подписи карты', r'city|cities|label'), ('partners', 'Партнёры', r'partner'), ('ghosts', 'Призраки в дыму', r'ghost'),
    ('silence', 'Минута молчания', r'silence|minute'), ('ads', 'Видео-попап', r'ad_video|adv'), ('pricing', 'Тарифы и заявки', r'pricing'),
    ('portfolio', 'Портфолио', r'portfolio'), ('i18n', 'Переводы', r'i18n|lang'),
    ('stats', 'Статистика, мониторинг, боты', r'stat|visit|bot|metric|health|cpu|ram|track|hourly|daily|server'),
    ('cost', 'Стоимость проекта, курс', r'currency|proj|cost|rate'), ('mail', 'Почта (SMTP)', r'mail|smtp'),
    ('files', 'Загрузка файлов', r'upload|file|img|image|logo|photo'), ('card', 'Страница мемориала card.html', r'card'),
    ('infra', 'Инфраструктура: БД, кеш, лимиты, безопасность', r'db|cache|redis|init|_rl|rate|sec_log|sanitize|valid|security|headers|startup|shutdown|middleware|cors|ip'),
]

def domain_of(text):
    t = text.lower()
    for key, _, rx in DOMAINS:
        if re.search(rx, t):
            return key
    return 'other'

def finalize():
    # маршрути, яких немає в бекенді, але до яких звертається фронтенд
    for nid, n in list(NODES.items()):
        if n.get('file') == 'mobile-mock.js':      # локальна заглушка API для розробки — шаблони адрес, не запити
            continue
        for u in n.get('unmatched_api', []):
            meth, path = u.split(' ', 1)
            rid = f'route:MISSING {meth} {path}'
            node(rid, 'route', f'{meth} {path}', method=meth, path=path, missing=True,
                 desc='Frontend обращается к этому адресу, но в Paskal.py такого маршрута нет → ответ 404')
            edge(nid, rid, 'request', status='code', file=n.get('file'), line=n.get('line'), note='маршрут не найден')
    # домени (для рівня «Функції»)
    for r in ROUTES:
        if r['fn']:
            NODES[r['id']]['domain'] = domain_of(r['path'] + ' ' + NODES[r['fn']]['label'])
            NODES[r['fn']].setdefault('domain', NODES[r['id']]['domain'])
        else:
            NODES[r['id']]['domain'] = 'infra'
    for nid, n in NODES.items():
        if n['type'] in ('pyfn', 'bgtask', 'middleware', 'tool') and 'domain' not in n:
            n['domain'] = domain_of(n['label'] + ' ' + (n.get('desc') or '')[:60])
        if n['type'] == 'route' and 'domain' not in n:
            n['domain'] = domain_of(n.get('path', ''))
    # роль / доступ: виклики require_* → вузли ролей
    roles = {
        'role:admin': ('Роль admin', 'Администратор: полный доступ (require_admin)'),
        'role:moder': ('Роль moder', 'Модератор: модерация и записи (require_moder пропускает admin и moder)'),
        'role:user': ('Пользователь (вход)', 'Любой пользователь с сессией (_get_optional_user / проверка сессии)'),
        'role:anon': ('Аноним', 'Публичные маршруты без входа'),
    }
    for rid, (lbl, d) in roles.items():
        node(rid, 'role', lbl, desc=d)
    req = {n: NODES[n] for n in NODES if NODES[n]['type'] in ('pyfn',) and NODES[n]['label'] in ('require_admin', 'require_moder', '_get_optional_user', '_get_optional_user_id')}
    for nid, n in req.items():
        r = {'require_admin': 'role:admin', 'require_moder': 'role:moder'}.get(n['label'], 'role:user')
        edge(nid, r, 'depends', file=n.get('file'), line=n.get('line'), note='проверка роли')
    # маршрут → роль (через обробник)
    for r in ROUTES:
        if not r['fn']:
            continue
        callees = {e['t'] for e in EDGES.values() if e['s'] == r['fn'] and e['rel'] == 'calls'}
        roles_hit = []
        for c in callees:
            lbl = NODES[c]['label']
            if lbl == 'require_admin':
                roles_hit.append('admin')
            elif lbl == 'require_moder':
                roles_hit.append('moder')
            elif lbl in ('_get_optional_user', '_get_optional_user_id', '_session_user', 'get_current_user', '_require_user'):
                roles_hit.append('user?')
        NODES[r['id']]['auth'] = ', '.join(sorted(set(roles_hit))) if roles_hit else 'публичный'
        fn = NODES[r['fn']]
        if fn.get('ratelimit'):
            NODES[r['id']]['ratelimit'] = fn['ratelimit']
    INC_IDX.clear(); OUT_IDX.clear()
    for e in EDGES.values():
        INC_IDX.setdefault(e['t'], []).append(e)
        OUT_IDX.setdefault(e['s'], []).append(e)
    # ступені
    deg_in, deg_out = defaultdict(int), defaultdict(int)
    for e in EDGES.values():
        deg_out[e['s']] += 1
        deg_in[e['t']] += 1
    for nid, n in NODES.items():
        n['din'] = deg_in[nid]
        n['dout'] = deg_out[nid]
    # невикористані функції (немає жодного вхідного зв'язку)
    for nid, n in NODES.items():
        if n['type'] in ('jsfn', 'pyfn') and deg_in[nid] == 0 and not n['label'].startswith(('⚡',)):
            n['unused'] = True
    # налаштування без читачів / без адмінки
    for nid, n in NODES.items():
        if n['type'] != 'setting':
            continue
        ins = [e for e in EDGES.values() if e['t'] == nid]
        readers = [e for e in ins if e['rel'] == 'reads' and (NODES[e['s']].get('file') or '') not in ADMIN_FILES]
        writers = [e for e in ins if e['rel'] == 'writes']
        admin_refs = [e for e in ins if (NODES[e['s']].get('file') or '') in ADMIN_FILES]
        # керування через окремий маршрут адмінки (напр. /api/admin/maintenance): бекенд змінює ключ, маршрут викликає admin.html
        for e in ins:
            if e['rel'] == 'writes' and NODES[e['s']]['type'] == 'pyfn' and not NODES[e['s']]['label'] == 'init_db':
                for r in [x['s'] for x in EDGES.values() if x['t'] == e['s'] and x['rel'] == 'handles']:
                    if any((NODES[x['s']].get('file') or '') in ADMIN_FILES for x in EDGES.values() if x['t'] == r and x['rel'] == 'request'):
                        admin_refs.append(e)
        admin_readers = [e for e in ins if e['rel'] == 'reads' and (NODES[e['s']].get('file') or '') in ADMIN_FILES]
        n['readers'] = len(readers)
        n['writers'] = len(writers)
        flags = []
        if not readers and n['label'].startswith('admin_') and admin_readers:
            n['info'] = 'Настройка самой админки — её читает admin.html'
        elif not readers and not admin_readers:
            flags.append('чтение этого ключа в коде не найдено (возможно, не используется)')
        elif not readers:
            flags.append('читается только админкой — на сайте и в backend использование не найдено')
        if not admin_refs:
            flags.append('в админке не найден элемент управления (меняется только через БД)')
        if flags:
            n['warn'] = '; '.join(flags)
        # де редагується (розділ адмінки): розділи елементів, що запускають функцію-записувача, і розділ, що її завантажує
        secs = set()
        for e in admin_refs:
            w_ = NODES[e['s']]
            if w_['type'] == 'pyfn':
                # окремий маршрут адмінки: функція backend ← маршрут ← запит з JS адмінки → розділ цієї JS-функції
                # (загальний PUT /api/admin/colors/batch пропускаємо: його викликають майже всі розділи)
                if w_['label'] in ('update_colors_batch', 'init_db'):
                    continue
                for h in INC_IDX.get(e['s'], ()):
                    if h['rel'] != 'handles':
                        continue
                    for rq in INC_IDX.get(h['s'], ()):
                        if rq['rel'] == 'request' and (NODES[rq['s']].get('file') or '') in ADMIN_FILES:
                            secs |= admin_sections_of(rq['s'])
            else:
                secs |= admin_sections_of(e['s'])
        if secs:
            n['sections'] = sorted(secs)

_SEC_CACHE = {}
def admin_sections_of(nid, depth=0):
    """Розділи адмінки, з яких реально запускається функція (елемент у розділі → функція; showSec → функція)."""
    if nid in _SEC_CACHE:
        return _SEC_CACHE[nid]
    n = NODES[nid]
    res = set()
    if n['type'] in ('ui', 'uidyn'):
        if n.get('group') and '#sec-' in n['group']:
            res.add(n['group'])
    else:
        for e in INC_IDX.get(nid, ()):
            s = NODES[e['s']]
            if e['rel'] == 'triggers' and s.get('group') and '#sec-' in s['group']:
                res.add(s['group'])
            elif e['rel'] == 'calls' and s['type'] == 'uigroup' and '#sec-' in s['id']:
                res.add(s['id'])
        if n['type'] == 'jsfn':
            for e in OUT_IDX.get(nid, ()):
                if e['rel'] == 'renders' and NODES[e['t']].get('group') and '#sec-' in NODES[e['t']]['group']:
                    res.add(NODES[e['t']]['group'])
        if not res and depth < 2:
            for e in INC_IDX.get(nid, ()):
                if e['rel'] == 'calls' and NODES[e['s']]['type'] == 'jsfn' and (NODES[e['s']].get('file') in ADMIN_FILES):
                    res |= admin_sections_of(e['s'], depth + 1)
    if len(res) > 5:          # загальна функція (використовується всюди) — розділ не визначаємо
        res = set()
    _SEC_CACHE[nid] = res
    return res

INC_IDX, OUT_IDX = {}, {}

def mermaid_out(stats):
    """Редаговані вихідники діаграм у Mermaid (docs/project-map/mermaid/)."""
    os.makedirs(os.path.join(OUT, 'mermaid'), exist_ok=True)
    def w(name, txt):
        with io.open(os.path.join(OUT, 'mermaid', name), 'w', encoding='utf-8', newline='\n') as f:
            f.write(txt)
    def mid(x):
        return re.sub(r'\W', '_', x)
    def lab(x, n=48):
        x = str(x).replace('"', "'").replace('\n', ' ')
        return x[:n] + ('…' if len(x) > n else '')
    # 1. общая архитектура
    w('01_overview.mmd', """flowchart LR
  subgraph USERS[Пользователи]
    V[Посетитель]
    A[Админ / модератор]
  end
  subgraph FRONT[Frontend — страницы]
    IDX[index.html — карта]
    MOB[mobile.html — планшет]
    CARD[card.html — мемориал]
    PROF[profile.html — профиль]
    ADM[admin.html — админка]
    DOCS[faq / rules / terms / how-to-add / pricing / promo / portfolio]
  end
  subgraph BACK[Backend Paskal.py — FastAPI]
    MW["middleware: security_headers, track_visits, техработы"]
    API["/api/* — маршруты API"]
    SSR["/memorial/{slug} — SSR и sitemap"]
    WS[("WebSocket /ws/online")]
    BG[["фоновые потоки: _cpu_ram_loop, _bot_loop, _currency_rate_loop"]]
  end
  subgraph DATA[Данные]
    DB[(MySQL zoryana_pamyat)]
    RD[(Redis — кеш, необязательный)]
    SES[(сессии в памяти)]
    FS[(файлы img/)]
  end
  subgraph EXT[Внешние сервисы]
    GO[Google OAuth]
    LP[LiqPay]
    NBU[НБУ курс]
    SMTP[SMTP]
    YT[YouTube]
    CARTO[CARTO тайлы]
    GI[Google Indexing]
    GA[Google Analytics]
    CDN[CDN: jsDelivr, Google Fonts]
  end
  V -->|открывает| IDX & MOB & CARD & PROF & DOCS
  A -->|открывает| ADM
  IDX & MOB & CARD & PROF & ADM -->|отправляет запрос| API
  IDX -->|WebSocket| WS
  ADM -->|BroadcastChannel вживую| IDX
  API -->|читает / изменяет| DB
  API -->|кеш| RD
  API -->|проверяет сессию| SES
  API -->|загрузка файлов| FS
  API -->|OAuth| GO
  API -->|оплата, подпись| LP
  API -->|письма| SMTP
  BG -->|курс| NBU
  API -->|ping| GI
  IDX -->|тайлы «Світ»| CARTO
  CARD & IDX -->|iframe| YT
  ADM -->|Chart.js, xlsx| CDN
""")
    # 2. ER-диаграмма (связи по полям *_id — предположение: FOREIGN KEY в БД нет)
    lines = ['erDiagram']
    for nid, n in NODES.items():
        if n['type'] == 'table':
            lines.append(f'  {n["label"]} {{')
            for c in (n.get('cols') or [])[:45]:
                nm, _, ty = c.partition(' ')
                ty = re.sub(r'[^A-Za-z0-9_]', '_', ty or 'x')[:20]
                lines.append(f'    {ty} {nm}')
            lines.append('  }')
    for s_, t_, l_ in ER_LINKS:
        lines.append(f'  {s_} ||--o{{ {t_} : "{l_}"')
    w('02_database_er.mmd', '\n'.join(lines) + '\n')
    # 3. админка: разделы → настройки
    lines = ['flowchart LR']
    for n in NODES.values():
        if n['type'] == 'uigroup' and n.get('page') == 'admin.html' and '#sec-' in n['id']:
            lines.append(f'  {mid(n["id"])}["{lab(n["label"], 40)}"]')
    for n in NODES.values():
        if n['type'] == 'setting' and n.get('sections'):
            lines.append(f'  {mid(n["id"])}{{{{"{lab(n["label"])}"}}}}')
            for g in n['sections']:
                lines.append(f'  {mid(g)} -->|изменяет| {mid(n["id"])}')
    w('03_admin_settings.mmd', '\n'.join(lines) + '\n')
    # 4. внешние сервисы
    lines = ['flowchart LR']
    for n in NODES.values():
        if n['type'] == 'external':
            lines.append(f'  {mid(n["id"])}(["{lab(n["label"])}"])')
    seen = set()
    for e in EDGES.values():
        if NODES[e['t']]['type'] == 'external' and NODES[e['s']]['type'] in ('pyfn', 'bgtask', 'route', 'jsfn', 'page', 'lib'):
            if (e['s'], e['t']) in seen:
                continue
            seen.add((e['s'], e['t']))
            lines.append(f'  {mid(e["s"])}["{lab(NODES[e["s"]]["label"], 40)}"] -->|{REL_RU[e["rel"]]}| {mid(e["t"])}')
    w('04_external_services.mmd', '\n'.join(lines) + '\n')
    # 5. авторизация
    w('05_auth.mmd', """sequenceDiagram
  autonumber
  participant B as Браузер
  participant S as Paskal.py
  participant G as Google OAuth
  participant M as MySQL users
  participant Ss as _sessions (память)
  B->>S: POST /api/auth/login {email, password}
  S->>S: _rl.check (лимит) + _is_locked (5 неудач → 15 мин)
  S->>M: SELECT users WHERE email
  S->>S: bcrypt.checkpw
  S->>Ss: secrets.token_hex(32) → пользователь
  S-->>B: Set-Cookie admin_session (7 дней)
  B->>S: GET /api/auth/google?next=…
  S-->>B: 302 → accounts.google.com
  B->>G: согласие пользователя
  G-->>B: 302 /api/auth/google/callback?code
  B->>S: callback (code, state)
  S->>G: обмен code → token, затем userinfo
  S->>M: _oauth_login_or_create (users)
  S->>Ss: новая сессия
  S-->>B: 302 → / | /admin | /card?slug=…&oauth=success
  B->>S: любой /api/admin/* (cookie)
  S->>Ss: require_admin / require_moder → роль
  S-->>B: 200 или 401/403
""")
    # 6. фоновые процессы
    lines = ['flowchart LR']
    for e in EDGES.values():
        if e['rel'] == 'starts' and NODES[e['s']]['type'] in ('bgtask', 'pyfn', 'route'):
            lines.append(f'  {mid(e["s"])}["{lab(NODES[e["s"]]["label"], 40)}"] -->|запускает| {mid(e["t"])}[["{lab(NODES[e["t"]]["label"], 40)}"]]')
    w('06_background.mmd', '\n'.join(lines) + '\n')
    # 7. страницы → группы API
    lines = ['flowchart LR']
    agg = defaultdict(int)
    for e in EDGES.values():
        if e['rel'] != 'request' or NODES[e['t']]['type'] != 'route':
            continue
        s_ = NODES[e['s']]
        pf = s_.get('page') or s_.get('file')
        if pf:
            agg[(pf, NODES[e['t']].get('domain', 'other'))] += 1
    dl = {k: l for k, l, _ in DOMAINS}
    for (pf, d), c in sorted(agg.items()):
        lines.append(f'  {mid("p_" + pf)}["{lab(pf)}"] -->|запросы: {c}| {mid("d_" + d)}["API · {lab(dl.get(d, d))}"]')
    w('07_pages_api.mmd', '\n'.join(lines) + '\n')

# Логічні звʼязки таблиць (за полями *_id; у БД зовнішніх ключів немає — позначені як припущення)
ER_LINKS = [
    ('memorials', 'likes_log', 'memorial_id'), ('memorials', 'memorial_awards', 'memorial_id'), ('memorials', 'memorial_gifts', 'memorial_id'),
    ('gifts', 'memorial_gifts', 'gift_id'), ('users', 'memorial_gifts', 'user_id'), ('gift_categories', 'gifts', 'category_id'),
    ('gifts', 'gift_i18n', 'entity_id (gift)'), ('users', 'chat_messages', 'user_id'), ('chat_messages', 'chat_reports', 'message_id'),
    ('users', 'legacy_accounts', 'user_id'), ('users', 'user_nickname_aliases', 'user_id'), ('memorials', 'pricing_leads', 'memorial_id'),
    ('memorials', 'seo_broken_links', 'memorial_id'), ('memorials', 'seo_index_log', 'memorial_id'), ('languages', 'i18n_translations', 'lang'),
    ('users', 'memorials', 'created_by_uid'), ('awards_catalog', 'memorial_awards', 'img_file'),
]

def main():
    t0 = time.time()
    TABLES, infos = backend()
    collect_settings()
    register_pages()
    externals_and_infra()
    backend_edges(TABLES, infos)
    py_extra_infra()
    frontend()
    resolve_pending_ids()
    for s, t, lbl in ER_LINKS:
        if 'tbl:' + s in NODES and 'tbl:' + t in NODES:
            edge('tbl:' + t, 'tbl:' + s, 'depends', status='assumed', note=f'поле {lbl} (без FOREIGN KEY в БД)')
            cc = lbl.split()[0]                     # поле → поле: user_id → users.id, lang → languages.<ключ>
            pk = [c for c in COLS.get(s, []) if 'PK' in (NODES.get(f'col:{s}.{c}', {}).get('ckey') or [])]
            pc = 'id' if cc.endswith('_id') and 'id' in COLS.get(s, []) else cc if cc in COLS.get(s, []) else (pk[0] if len(pk) == 1 else None)
            if pc:
                edge(f'col:{t}.{cc}', f'col:{s}.{pc}', 'depends', status='assumed', note=f'{t}.{cc} → {s}.{pc} (без FOREIGN KEY в БД)')
    for k in SETTINGS:
        edge('set:' + k, 'tbl:colors', 'stored', file='Paskal.py', line=SETTINGS[k].get('seed_line'))
    named = {e['t'] for e in EDGES.values() if e['rel'] != 'contains'} | {e['s'] for e in EDGES.values()}
    for n in NODES.values():                    # поле не названо ни в одном SQL-запросе — SELECT * или запрос собирается динамически
        if n['type'] == 'column' and n['id'] not in named:
            n['nosql'] = True
            n['info'] = 'Поле не названо ни в одном SQL-запросе кода: читается через SELECT * или имя подставляется динамически (f-строка) — проверить вручную.'
    finalize()
    counts = defaultdict(int)
    for n in NODES.values():
        counts[n['type']] += 1
    rel_counts = defaultdict(int)
    for e in EDGES.values():
        rel_counts[e['rel']] += 1
    stats = {'nodes': len(NODES), 'edges': len(EDGES), 'by_type': dict(counts), 'by_rel': dict(rel_counts),
             'routes': len([r for r in ROUTES if r['method'] != 'STATIC']), 'generated': time.strftime('%Y-%m-%d %H:%M'), 'seconds': round(time.time() - t0, 1)}
    # персональні дані не потрапляють у карту: e-mail у підписах (mailto, тексти сторінок) — замінено
    email_rx = re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}')
    keep = {'id', 's', 't', 'file', 'page', 'group', 'parent', 'domain', 'type', 'rel', 'status'}
    def _mask(v):
        if isinstance(v, str):
            return email_rx.sub('e-mail', v)
        if isinstance(v, list):
            return [_mask(x) for x in v]
        return v
    for o in list(NODES.values()) + list(EDGES.values()):
        for k in list(o.keys()):
            if k not in keep:
                o[k] = _mask(o[k])
    os.makedirs(os.path.join(OUT, 'data'), exist_ok=True)
    data = {'nodes': list(NODES.values()), 'edges': list(EDGES.values()), 'stats': stats, 'rel_ru': REL_RU,
            'domains': [[k, lbl] for k, lbl, _ in DOMAINS] + [['other', 'Прочее']], 'root': ROOT.replace('\\', '/')}
    with io.open(os.path.join(OUT, 'data', 'graph.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
    mermaid_out(stats)
    tpl_path = os.path.join(HERE, 'viewer_template.html')
    if os.path.exists(tpl_path):
        tpl = io.open(tpl_path, encoding='utf-8').read()
        blob = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
        with io.open(os.path.join(OUT, 'index.html'), 'w', encoding='utf-8', newline='\n') as f:
            f.write(tpl.replace('/*__GRAPH_DATA__*/null', blob))
    print(json.dumps(stats, ensure_ascii=False, indent=1))

if __name__ == '__main__':
    main()
