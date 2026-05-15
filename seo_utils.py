import re

_UK_TRANSLIT = {
    'а':'a','б':'b','в':'v','г':'h','ґ':'g','д':'d','е':'e','є':'ie',
    'ж':'zh','з':'z','и':'y','і':'i','ї':'i','й':'i','к':'k','л':'l',
    'м':'m','н':'n','о':'o','п':'p','р':'r','с':'s','т':'t','у':'u',
    'ф':'f','х':'kh','ц':'ts','ч':'ch','ш':'sh','щ':'shch','ь':'',
    'ю':'iu','я':'ia',"'":'',"'":'',"'":'',' ':'-',
}

def transliterate_uk(text: str) -> str:
    result = []
    for ch in text.lower():
        result.append(_UK_TRANSLIT.get(ch, ch))
    return ''.join(result)

def make_slug(first: str, last: str, record_id: int) -> str:
    f = transliterate_uk((first or '').strip())
    l = transliterate_uk((last or '').strip())
    raw = f'{f}-{l}-{record_id}'
    raw = re.sub(r'[^a-z0-9\-]', '', raw)
    raw = re.sub(r'-{2,}', '-', raw).strip('-')
    return raw or f'memorial-{record_id}'

def gen_seo_title(row: dict, site_name: str = "Зоряна Пам'ять") -> str:
    full = ' '.join(filter(None, [row.get('last'), row.get('first'), row.get('mid')])).strip()
    if not full:
        full = 'Захисник України'
    return f"{full} — Герой України | {site_name}"

def gen_seo_description(row: dict) -> str:
    parts = []
    full = ' '.join(filter(None, [row.get('last'), row.get('first'), row.get('mid')])).strip()
    if full:
        parts.append(full)
    # Rank + position in one chunk: "Майор, Снайпер"
    rank = (row.get('rank') or '').strip()
    pos  = (row.get('position') or '').strip()
    if rank and pos:
        parts.append(f"{rank}, {pos}")
    elif rank:
        parts.append(rank)
    elif pos:
        parts.append(pos)
    if row.get('unit'):
        parts.append(row['unit'])
    if row.get('grp'):
        parts.append(f"позивний «{row['grp']}»")
    death = str(row.get('death') or '').strip()
    if death:
        parts.append(f"загинув {death}")
    if row.get('loc'):
        parts.append(f"поблизу {row['loc']}")
    elif row.get('bury'):
        parts.append(f"похований: {row['bury']}")
    if row.get('descr'):
        parts.append(row['descr'][:80])
    desc = '. '.join(parts)
    if len(desc) > 160:
        desc = desc[:157] + '...'
    return desc or "Герой України, захисник рідної землі."

def gen_seo_keywords(row: dict) -> str:
    """Generate comma-separated keyword string for <meta name="keywords">."""
    kw = []
    full = ' '.join(filter(None, [row.get('last'), row.get('first'), row.get('mid')])).strip()
    if full:
        kw.append(full)
        lf = ' '.join(filter(None, [row.get('last'), row.get('first')])).strip()
        if lf and lf != full:
            kw.append(lf)
        # Transliterated name for diaspora/foreign-language searches
        translit = transliterate_uk(full).replace('-', ' ').strip()
        if translit and translit != full.lower():
            kw.append(translit)
    if row.get('grp'):
        kw.append(row['grp'])
        kw.append(f"позивний {row['grp']}")
    if row.get('unit'):
        kw.append(row['unit'])
    if row.get('rank'):
        kw.append(row['rank'])
    if row.get('position'):
        kw.append(row['position'])
    if row.get('loc'):
        kw.append(row['loc'])
    if row.get('bury'):
        kw.append(row['bury'])
    # Death year for "died in 20XX" type searches
    death = str(row.get('death') or '').strip()
    if death and len(death) >= 4:
        kw.append(death[:4])
    kw += ["Герой України", "Захисник України", "загиблий захисник",
           "пам'ять героя", "Зоряна Пам'ять"]
    # Deduplicate preserving order
    seen, result = set(), []
    for k in kw:
        kl = k.lower().strip()
        if kl and kl not in seen:
            seen.add(kl)
            result.append(k)
    return ', '.join(result)

def calc_seo_score(row: dict) -> dict:
    """
    Returns SEO quality score (0-100) with grade and actionable tips.
    Used in admin dashboard to identify cards that need improvement.
    """
    score = 0
    issues = []
    tips = []

    # Full name — 10 pts
    has_last  = bool((row.get('last')  or '').strip())
    has_first = bool((row.get('first') or '').strip())
    has_mid   = bool((row.get('mid')   or '').strip())
    if has_last and has_first and has_mid:
        score += 10
    elif has_last and has_first:
        score += 7
        tips.append("Додайте по батькові для повного ПІБ (+3 бали)")
    else:
        issues.append("Неповне ПІБ (прізвище+ім'я обов'язкові)")

    # Photo — 20 pts
    photo = (row.get('photo') or '').strip()
    if photo and len(photo) > 5 and photo != '/img/foto_false.png':
        score += 20
    else:
        issues.append("Відсутнє фото")
        tips.append("Завантажте фото — підвищує CTR у Google на 30-40% (+20 балів)")

    # Description — 20 pts
    descr = (row.get('descr') or '').strip()
    dlen = len(descr)
    if dlen >= 150:
        score += 20
    elif dlen >= 80:
        score += 14
        tips.append(f"Опис {dlen} символів. Доведіть до 150+ для максимального балу (+6)")
    elif dlen >= 30:
        score += 7
        tips.append(f"Опис дуже короткий ({dlen} символів). Рекомендовано 150+ (+13)")
    else:
        issues.append("Опис відсутній або занадто короткий")
        tips.append("Додайте біографічний опис 150+ символів — критично для Google snippet (+20)")

    # Unit — 10 pts
    if (row.get('unit') or '').strip():
        score += 10
    else:
        issues.append("Не вказаний підрозділ")
        tips.append("Вкажіть підрозділ — дозволяє ранжуватись за пошуком по назві підрозділу (+10)")

    # Rank — 10 pts
    if (row.get('rank') or '').strip():
        score += 10
    else:
        tips.append("Вкажіть звання (+10 балів)")

    # Death date — 10 pts
    if (row.get('death') or '').strip():
        score += 10
    else:
        issues.append("Не вказана дата загибелі")
        tips.append("Дата загибелі потрібна для schema.org Person (+10)")

    # Location — 10 pts
    if (row.get('loc') or '').strip():
        score += 10
    else:
        issues.append("Не вказане місце загибелі")
        tips.append("Місце загибелі допомагає у регіональному пошуку (+10)")

    # Birth date — 5 pts
    if (row.get('birth') or '').strip():
        score += 5
    else:
        tips.append("Вкажіть дату народження (+5)")

    # Callsign — 5 pts
    if (row.get('grp') or '').strip():
        score += 5
    else:
        tips.append("Вкажіть позивний — підвищує знаходження за пошуком по позивному (+5)")

    # Position — 5 pts (бонус; ліміт 100 зберігається)
    if (row.get('position') or '').strip():
        score += 5
    else:
        tips.append("Вкажіть посаду (снайпер, оператор БпЛА, водій…) — ніша-ключове слово (+5)")

    score = min(100, score)
    if score >= 85:
        grade = 'A'
    elif score >= 70:
        grade = 'B'
    elif score >= 50:
        grade = 'C'
    else:
        grade = 'D'

    return {
        'score':  score,
        'grade':  grade,
        'issues': issues,
        'tips':   tips,
    }
