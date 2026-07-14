"""
lang_engine.py — i18n движок для Зоряна Пам'ять
Читає переклади з MySQL (таблиці languages + i18n_translations).
Кешує секції через functools.lru_cache + Redis (якщо доступний).
"""
import time
import json
from functools import lru_cache
from typing import Optional

_FALLBACK_LANG = "uk"
_CACHE_TTL = 300  # секунди, для Redis


def _get_pool():
    """Імпортуємо пул ліниво щоб уникнути circular import."""
    from Paskal import get_db, cache_get, cache_set
    return get_db, cache_get, cache_set


# ── Завантаження секції (кешується в пам'яті) ─────────────
@lru_cache(maxsize=256)
def _load_section_cached(lang: str, section: str) -> str:
    """Повертає JSON-рядок {key: value} для lang+section. lru_cache кешує в пам'яті."""
    get_db, cache_get, cache_set = _get_pool()
    redis_key = f"i18n:{lang}:{section}"
    cached = cache_get(redis_key)
    if cached:
        return cached
    db = get_db()
    try:
        with db.cursor() as c:
            c.execute(
                "SELECT `key`, value FROM i18n_translations "
                "WHERE lang=%s AND section=%s",
                (lang, section)
            )
            rows = c.fetchall()
        result = {r["key"]: r["value"] for r in rows}
        serialized = json.dumps(result, ensure_ascii=False)
        cache_set(redis_key, serialized, ttl=_CACHE_TTL)
        return serialized
    finally:
        db.close()


def _load_section(lang: str, section: str) -> dict:
    return json.loads(_load_section_cached(lang, section))


# ── Публічна функція перекладу ────────────────────────────
def t(key: str, lang: str = _FALLBACK_LANG, section: str = "ui", vars: Optional[dict] = None) -> str:
    """
    Повертає переклад для key в lang.
    Якщо не знайдено — fallback до uk.
    vars: dict для підстановки {name} → значення.
    """
    data = _load_section(lang, section)
    value = data.get(key)

    if value is None and lang != _FALLBACK_LANG:
        fallback_data = _load_section(_FALLBACK_LANG, section)
        value = fallback_data.get(key)

    if value is None:
        return key  # повертаємо ключ якщо переклад відсутній

    if vars:
        for k, v in vars.items():
            value = value.replace("{" + k + "}", str(v))

    return value


# ── Завантаження всього словника для мови ─────────────────
def get_all(lang: str, sections: Optional[list] = None) -> dict:
    """
    Повертає весь словник перекладів для lang.
    sections: список секцій; якщо None — завантажує всі з БД.
    """
    get_db, cache_get, cache_set = _get_pool()

    if sections is None:
        redis_key = f"i18n_all:{lang}"
        cached = cache_get(redis_key)
        if cached:
            return json.loads(cached)
        db = get_db()
        try:
            with db.cursor() as c:
                # Один запит: всі ключі мови + uk fallback для відсутніх
                if lang != _FALLBACK_LANG:
                    c.execute(
                        "SELECT lang, `key`, value FROM i18n_translations "
                        "WHERE lang IN (%s, %s) ORDER BY lang",
                        (lang, _FALLBACK_LANG)
                    )
                else:
                    c.execute(
                        "SELECT lang, `key`, value FROM i18n_translations WHERE lang=%s",
                        (lang,)
                    )
                rows = c.fetchall()

            # Спочатку uk (fallback), потім перекриваємо lang
            result = {}
            uk_rows = {r["key"]: r["value"] for r in rows if r["lang"] == _FALLBACK_LANG}
            lang_rows = {r["key"]: r["value"] for r in rows if r["lang"] == lang}
            result.update(uk_rows)    # спочатку uk
            result.update(lang_rows)  # потім перекриваємо lang

            serialized = json.dumps(result, ensure_ascii=False)
            cache_set(redis_key, serialized, ttl=_CACHE_TTL)
            return result
        finally:
            db.close()
    else:
        result = {}
        for sec in sections:
            result.update(_load_section(lang, sec))
        # Fallback uk для відсутніх ключів
        if lang != _FALLBACK_LANG:
            for sec in sections:
                uk_data = _load_section(_FALLBACK_LANG, sec)
                for k, v in uk_data.items():
                    if k not in result:
                        result[k] = v
        return result


# ── Отримати мову з запиту ────────────────────────────────
def get_lang(request) -> str:
    """
    Пріоритет: cookie 'lang' → Accept-Language → 'uk'.
    """
    cookie_lang = request.cookies.get("lang", "").strip().lower()[:5]
    if cookie_lang and len(cookie_lang) == 2:
        return cookie_lang

    accept = request.headers.get("accept-language", "")
    if accept:
        code = accept.split(",")[0].strip().split("-")[0].lower()
        if len(code) == 2:
            return code

    return _FALLBACK_LANG


# ── Інвалідація кешу ──────────────────────────────────────
def invalidate_cache(lang: Optional[str] = None, section: Optional[str] = None):
    """Скидає lru_cache і Redis ключі для lang/section (або всі)."""
    _load_section_cached.cache_clear()

    get_db, cache_get, cache_set = _get_pool()
    try:
        from Paskal import _redis
        if _redis:
            if lang and section:
                _redis.delete(f"i18n:{lang}:{section}")
                _redis.delete(f"i18n_all:{lang}")
            elif lang:
                for key in _redis.scan_iter(f"i18n*{lang}*"):
                    _redis.delete(key)
            else:
                for key in _redis.scan_iter("i18n*"):
                    _redis.delete(key)
    except Exception:
        pass


# ── Список активних мов (кешується 60с) ───────────────────
_langs_cache: dict = {"data": None, "ts": 0.0}


def get_languages() -> list:
    """Повертає список активних мов з БД (кешується 60с у пам'яті)."""
    now = time.time()
    if _langs_cache["data"] is not None and now - _langs_cache["ts"] < 60:
        return _langs_cache["data"]

    get_db, _, _ = _get_pool()
    db = get_db()
    try:
        with db.cursor() as c:
            c.execute(
                "SELECT code, name, flag, direction, is_default "
                "FROM languages WHERE is_active=1 ORDER BY sort_order, code"
            )
            rows = c.fetchall()
        result = [dict(r) for r in rows]
        _langs_cache["data"] = result
        _langs_cache["ts"] = now
        return result
    finally:
        db.close()
