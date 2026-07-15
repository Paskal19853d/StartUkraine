/**
 * i18n.js — клієнтська локалізація Зоряна Пам'ять
 * Завантажує словник з /api/i18n/{lang}, застосовує до DOM.
 * window.LANG.t(key, vars?) — функція перекладу.
 */

window.LANG = (() => {
    let _dict = {};
    let _current = 'uk';

    // ── Визначити поточну мову ──────────────────────────
    function _detectLang() {
        const cookie = document.cookie.split(';').map(c => c.trim())
            .find(c => c.startsWith('lang='));
        if (cookie) return cookie.split('=')[1].trim().slice(0, 5);
        const nav = (navigator.language || navigator.userLanguage || 'uk').split('-')[0].toLowerCase();
        return nav === 'en' ? 'en' : 'uk';
    }

    // ── Функція перекладу ────────────────────────────────
    function t(key, vars) {
        let val = _dict[key];
        if (val === undefined) return key;
        if (vars) {
            Object.entries(vars).forEach(([k, v]) => {
                val = val.replaceAll('{' + k + '}', v);
            });
        }
        return val;
    }

    // ── Застосувати переклади до DOM ─────────────────────
    function applyI18n(root) {
        root = root || document;

        // data-i18n → textContent (тільки якщо немає дочірніх елементів)
        root.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.getAttribute('data-i18n');
            const val = t(key);
            if (val === undefined || val === key) return;
            // Якщо є дочірні елементи — замінюємо тільки перший текстовий вузол
            const hasChildElements = el.children.length > 0;
            if (hasChildElements) {
                // знаходимо або створюємо перший Text node
                for (const node of el.childNodes) {
                    if (node.nodeType === 3) { // TEXT_NODE
                        node.textContent = val;
                        return;
                    }
                }
            } else {
                el.textContent = val;
            }
        });

        // data-i18n-html → innerHTML (для жирного тексту, посилань)
        root.querySelectorAll('[data-i18n-html]').forEach(el => {
            const key = el.getAttribute('data-i18n-html');
            const val = t(key);
            if (val !== key) el.innerHTML = val;
        });

        // data-i18n-placeholder → placeholder
        root.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
            const key = el.getAttribute('data-i18n-placeholder');
            const val = t(key);
            if (val !== key) el.placeholder = val;
        });

        // data-i18n-hint → data-hint (для .zp-hint)
        root.querySelectorAll('[data-i18n-hint]').forEach(el => {
            const key = el.getAttribute('data-i18n-hint');
            const val = t(key);
            if (val !== key) el.setAttribute('data-hint', val);
        });

        // data-i18n-aria → aria-label
        root.querySelectorAll('[data-i18n-aria]').forEach(el => {
            const key = el.getAttribute('data-i18n-aria');
            const val = t(key);
            if (val !== key) el.setAttribute('aria-label', val);
        });

        // data-i18n-title → title
        root.querySelectorAll('[data-i18n-title]').forEach(el => {
            const key = el.getAttribute('data-i18n-title');
            const val = t(key);
            if (val !== key) el.setAttribute('title', val);
        });

        // data-i18n-label → label (для <optgroup label="...">)
        root.querySelectorAll('[data-i18n-label]').forEach(el => {
            const key = el.getAttribute('data-i18n-label');
            const val = t(key);
            if (val !== key) el.setAttribute('label', val);
        });
    }

    // ── Завантажити словник з сервера ────────────────────
    async function load(lang) {
        lang = lang || _detectLang();
        _current = lang;
        try {
            const res = await fetch(`/api/i18n/${lang}`, { credentials: 'same-origin' });
            if (!res.ok) throw new Error('HTTP ' + res.status);
            const data = await res.json();
            _dict = data.t || {};
        } catch (e) {
            console.warn('[i18n] load failed, using empty dict:', e);
            _dict = {};
        }
        applyI18n();
        document.documentElement.setAttribute('lang', lang);
        document.documentElement.setAttribute('data-lang', lang);
    }

    // ── Переключити мову ──────────────────────────────────
    async function switchLang(lang) {
        console.log('[i18n] switchLang', lang, 'current:', _current);
        if (lang === _current) return;
        // Зберегти в cookie (1 рік)
        document.cookie = `lang=${lang};path=/;max-age=31536000;SameSite=Lax`;
        await load(lang);
        console.log('[i18n] dict keys after load:', Object.keys(_dict).length, 'sample:', Object.entries(_dict).slice(0,3));
        _updateToggleUI(lang);
        // Синхронізувати між вкладками
        try {
            new BroadcastChannel('zoryana_lang').postMessage({ lang });
        } catch (_) {}
    }

    // ── Слухати перемикання з інших вкладок ───────────────
    try {
        const bc = new BroadcastChannel('zoryana_lang');
        bc.onmessage = e => {
            if (e.data && e.data.lang && e.data.lang !== _current) {
                load(e.data.lang);
                _updateToggleUI(e.data.lang);
            }
        };
    } catch (_) {}

    // ── Оновити UI перемикача ─────────────────────────────
    function _updateToggleUI(lang) {
        // Делегуємо сторінці — вона має свою _langToggleUpdateUI
        if (typeof _langToggleUpdateUI === 'function') {
            _langToggleUpdateUI(lang);
        } else {
            const toggle = document.getElementById('lang-toggle');
            if (!toggle) return;
            toggle.classList.toggle('lang-en', lang === 'en');
        }
        const toggle = document.getElementById('lang-toggle');
        if (toggle) toggle.setAttribute('data-hint', lang === 'en' ? 'Switch to Ukrainian / Перемкнути на українську' : 'Switch to English / Перемкнути на англійську');
    }

    // ── Публічний API ─────────────────────────────────────
    return {
        get current() { return _current; },
        get dict()    { return _dict; },
        t,
        load,
        switchLang,
        applyI18n,
    };
})();
