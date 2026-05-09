/* ── Модуль «Хвилина мовчання» ───────────────────────── */
const CLOCK_FONTS = {
  'letsgodigital': "'LetsGoDigital', monospace",
  'cristal':       "'Cristal', sans-serif",
  'pockc':         "'POCKC', sans-serif",
  'monospace':     'monospace',
  'courier':       "'Courier New', monospace",
  'unbounded':     "'Unbounded', sans-serif",
  'geologica':     "'Geologica', sans-serif",
  'arial':         "'Arial', sans-serif",
  'georgia':       "'Georgia', serif",
  'times':         "'Times New Roman', serif",
};

const SilenceModule = (function () {
  let _s = {};
  let _active = false;
  let _schedTimer = null;
  let _stopTimer  = null;
  let _clockTimer = null;

  let _audio       = null;   // HTMLAudioElement
  let _audioSrc    = '';     // src завантаженого елементу
  let _primed      = false;  // play+pause вже виконано для _audio?
  let _interacted  = false;  // користувач хоч раз взаємодіяв зі сторінкою?
  let _ctxUnlocked = false;

  let _lastTriggeredMin = '';
  let _bc = null;

  /* ═══════════════ ІНІЦІАЛІЗАЦІЯ ═════════════════════ */
  async function init() {
    _injectFontFaces();
    try {
      const r = await fetch('/api/minute-silence/settings');
      if (!r.ok) return;
      _s = await r.json();
    } catch (e) { return; }
    _ensureAudio();
    _setupInteractionPrime();
    _startClock();
    _listenBroadcast();
    _scheduleCheck();
  }

  /* ═══════════════ ШРИФТИ ════════════════════════════ */
  function _injectFontFaces() {
    if (!window.FontFace) return;
    [
      { name: 'LetsGoDigital', url: '/fonts/Let_s_go_Digital_Regular.ttf' },
      { name: 'Cristal',       url: '/fonts/cristal.ttf' },
      { name: 'POCKC',         url: '/fonts/POCKC___.TTF' },
    ].forEach(function (f) {
      var face = new FontFace(f.name, "url('" + f.url + "') format('truetype')");
      face.load().then(function (l) { document.fonts.add(l); }).catch(function () {});
    });
  }

  /* ═══════════════ АУДІО ═════════════════════════════

     Принцип: браузер дозволяє play() якщо:
       (a) на сторінці вже відбувся user gesture, АБО
       (b) сайт має достатній Media Engagement Score

     Прайм: при першому mousemove/click викликаємо play(vol=0)+pause
     → браузер реєструє, що елемент "використовувався" в контексті
     жесту → наступний play() (під час мовчання) НЕ блокується.

     Якщо все одно заблоковано → кнопка "🔊 Натисніть для звуку".
  */

  /* Створити / оновити аудіо-елемент якщо змінився файл */
  function _ensureAudio() {
    var file = (_s.audio_file || '').trim();
    if (!file) { _audio = null; _audioSrc = ''; _primed = false; return false; }
    var src = '/audio/' + file;
    if (_audio && _audioSrc === src) return true;   // вже актуальний

    if (_audio) { try { _audio.pause(); } catch (e) {} _audio.src = ''; }

    _audio    = new Audio(src);
    _audioSrc = src;
    _primed   = false;
    _audio.loop    = true;
    _audio.preload = 'auto';
    _audio.volume  = parseFloat(_s.audio_volume || '0.7');
    _audio.load();

    /* Якщо користувач вже взаємодіяв — відразу прайм після завантаження */
    if (_interacted) {
      _audio.addEventListener('canplaythrough', function onReady() {
        _audio.removeEventListener('canplaythrough', onReady);
        _doPrime();
      }, { once: true });
    }
    return true;
  }

  /* Play(vol=0) + pause → "активує" елемент для майбутніх play() без жесту */
  function _doPrime() {
    if (_primed || !_audio || !_audio.paused) return;  // не заважати якщо вже грає
    var vol = _audio.volume;
    _audio.volume = 0;
    var p = _audio.play();
    if (p && typeof p.then === 'function') {
      p.then(function () {
        _audio.pause();
        _audio.currentTime = 0;
        _audio.volume = vol;
        _primed = true;
      }).catch(function () {
        _audio.volume = vol;   // не вдалося — нічого, спробуємо знову
      });
    } else {
      try { _audio.pause(); _audio.currentTime = 0; } catch (e) {}
      _audio.volume = vol;
      _primed = true;
    }
  }

  /* AudioContext unlock */
  function _unlockCtx() {
    if (_ctxUnlocked) return;
    try {
      var Ctx = window.AudioContext || window.webkitAudioContext;
      if (!Ctx) return;
      var ctx = new Ctx();
      var buf = ctx.createBuffer(1, 1, 22050);
      var src = ctx.createBufferSource();
      src.buffer = buf; src.connect(ctx.destination); src.start(0);
      setTimeout(function () { ctx.close(); }, 300);
      _ctxUnlocked = true;
    } catch (e) {}
  }

  /* Перша взаємодія → прайм */
  function _setupInteractionPrime() {
    var evs = ['click','touchstart','touchend','keydown','pointerdown','scroll','mousemove'];
    function handler() {
      _interacted = true;
      _unlockCtx();
      _doPrime();
      evs.forEach(function (ev) { document.removeEventListener(ev, handler); });
    }
    evs.forEach(function (ev) { document.addEventListener(ev, handler, { once: true, passive: true }); });
  }

  /* ═══════════════ ВІДТВОРЕННЯ ════════════════════════ */
  function _playAudio() {
    if (!_ensureAudio()) return;
    _audio.volume      = parseFloat(_s.audio_volume || '0.7');
    _audio.currentTime = 0;

    var p = _audio.play();
    if (p && typeof p.then === 'function') {
      p.then(function () {
        _hideTapHint();
      }).catch(function () {
        /* Заблоковано autoplay — показати кнопку і чекати кліку */
        _showTapHint();
        function retry() {
          if (_audio && _active) {
            _audio.play()
              .then(function () { _hideTapHint(); })
              .catch(function () {});
          }
          document.removeEventListener('click',       retry);
          document.removeEventListener('touchstart',  retry);
          document.removeEventListener('keydown',     retry);
          document.removeEventListener('pointerdown', retry);
        }
        document.addEventListener('click',       retry, { once: true });
        document.addEventListener('touchstart',  retry, { once: true });
        document.addEventListener('keydown',     retry, { once: true });
        document.addEventListener('pointerdown', retry, { once: true });
      });
    }
  }

  function _stopAudio() {
    if (_audio) { try { _audio.pause(); } catch (e) {} _audio.currentTime = 0; }
  }

  /* ═══════════════ КНОПКА "НАТИСНІТЬ ДЛЯ ЗВУКУ" ══════ */
  function _showTapHint() {
    var h = document.getElementById('_sl_tap');
    if (!h) {
      h = document.createElement('div');
      h.id = '_sl_tap';
      h.textContent = '🔊 Натисніть для звуку';
      h.style.cssText =
        'position:fixed;bottom:24px;left:50%;transform:translateX(-50%);' +
        'background:rgba(0,0,0,.75);color:#fff;padding:9px 22px;border-radius:24px;' +
        'font-size:15px;cursor:pointer;z-index:10000;user-select:none;' +
        'box-shadow:0 2px 12px rgba(0,0,0,.4);';
      h.onclick = function () {
        if (_audio && _active) {
          _audio.play().then(function () { _hideTapHint(); }).catch(function () {});
        }
      };
      document.body.appendChild(h);
    }
    h.style.display = 'block';
  }

  function _hideTapHint() {
    var h = document.getElementById('_sl_tap');
    if (h) h.style.display = 'none';
  }

  /* ═══════════════ ПЛАНУВАЛЬНИК ═══════════════════════ */
  function _scheduleCheck() {
    if (_schedTimer) clearInterval(_schedTimer);
    _schedTimer = setInterval(_tick, 30000);
    _tick();
  }

  function _tick() {
    if (_active) return;
    if (_s.enabled !== '1') return;
    const now  = new Date(new Date().toLocaleString('en-US', { timeZone: 'Europe/Kyiv' }));
    const hhmm = String(now.getHours()).padStart(2, '0') + ':' + String(now.getMinutes()).padStart(2, '0');
    if (hhmm === _s.time_hhmm && hhmm !== _lastTriggeredMin) {
      _lastTriggeredMin = hhmm;
      _start();
    }
  }

  /* ═══════════════ ЗАПУСК / ЗУПИНКА ══════════════════ */
  function _start() {
    if (_active) return;
    _active = true;
    _applyGrayscale();
    _renderOverlay();
    _playAudio();
    const dur = parseInt(_s.duration_sec || '60', 10) * 1000;
    if (_stopTimer) clearTimeout(_stopTimer);
    _stopTimer = setTimeout(_stop, dur);
  }

  function _stop() {
    _active = false;
    if (_stopTimer) { clearTimeout(_stopTimer); _stopTimer = null; }
    _removeGrayscale();
    _removeOverlay();
    _stopAudio();
    _hideTapHint();
  }

  /* ═══════════════ GRAYSCALE / OVERLAY / CLOCK ════════ */
  function _applyGrayscale() {
    document.body.classList.add('silence-active');
    if (window._fluidConfig) window._fluidConfig.PAUSED = true;
  }

  function _removeGrayscale() {
    document.body.classList.remove('silence-active');
    if (window._fluidConfig) window._fluidConfig.PAUSED = false;
  }
  /* transition: filter 2s ease задано в CSS на body —
     клас видаляється і фільтр плавно повертається до normal */

  function _renderOverlay() {
    let el = document.getElementById('silence-overlay');
    if (!el) {
      el = document.createElement('div');
      el.id = 'silence-overlay';
      document.body.appendChild(el);
    }
    const bg  = _s.overlay_bg_color   || '#000000';
    const col = _s.overlay_text_color || '#ffffff';
    const h   = parseInt(_s.overlay_height || '15', 10);
    el.style.setProperty('--silence-bg',    bg + 'e0');
    el.style.setProperty('--silence-color', col);
    el.style.minHeight = h + 'vh';
    const sub = (_s.overlay_subtext || '').trim();
    el.innerHTML =
      '<div class="silence-title">' + _esc(_s.overlay_text || 'Хвилина мовчання') + '</div>' +
      (sub ? '<div class="silence-sub">' + _esc(sub) + '</div>' : '');
    el.style.transition = '';
    el.style.opacity    = '1';
    el.style.display    = 'flex';
  }

  function _removeOverlay() {
    const el = document.getElementById('silence-overlay');
    if (!el || el.style.display === 'none') return;
    el.style.transition = 'opacity 2s ease';
    el.style.opacity    = '0';
    setTimeout(function () {
      el.style.display    = 'none';
      el.style.opacity    = '';
      el.style.transition = '';
    }, 2000);
  }

  function _startClock() {
    if (_clockTimer) clearInterval(_clockTimer);
    _updateClock();
    _clockTimer = setInterval(_updateClock, 1000);
  }

  function _updateClock() {
    if (_s.clock_enabled !== '1') {
      const el = document.getElementById('kyiv-clock');
      if (el) el.style.display = 'none';
      return;
    }
    let el = document.getElementById('kyiv-clock');
    if (!el) {
      el = document.createElement('div');
      el.id = 'kyiv-clock';
      document.body.appendChild(el);
    }
    const now = new Date(new Date().toLocaleString('en-US', { timeZone: 'Europe/Kyiv' }));
    el.textContent =
      String(now.getHours()).padStart(2, '0') + ':' +
      String(now.getMinutes()).padStart(2, '0') + ':' +
      String(now.getSeconds()).padStart(2, '0');
    const sz   = (_s.clock_font_size || '20') + 'px';
    const font = CLOCK_FONTS[_s.clock_font] || _s.clock_font || 'monospace';
    el.style.fontSize   = sz;
    el.style.fontFamily = font;
    el.style.color      = _s.clock_color || '#ffffff';
    el.style.background = _s.clock_bg   || 'rgba(0,0,0,0.5)';
    el.style.opacity    = _s.clock_opacity || '1';
    el.style.left       = parseInt(_s.clock_x || '10', 10) + 'px';
    el.style.top        = parseInt(_s.clock_y || '10', 10) + 'px';
    el.style.bottom     = '';
    el.style.right      = '';
    el.style.display    = 'block';
  }

  /* ═══════════════ BROADCASTCHANNEL ══════════════════ */
  function _listenBroadcast() {
    try {
      _bc = new BroadcastChannel('zoryana_silence');
      _bc.onmessage = function (e) {
        if (!e.data) return;
        if (e.data.cmd === 'start') {
          _s = Object.assign(_s, e.data.settings || {});
          _ensureAudio();
          _start();
        }
        if (e.data.cmd === 'stop') _stop();
        if (e.data.cmd === 'settings') {
          _s = Object.assign(_s, e.data.settings || {});
          _ensureAudio();
          _updateClock();
        }
      };
    } catch (e) {}
  }

  function _esc(s) {
    return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  return {
    init:        init,
    _primeAudio: function () { _interacted = true; _unlockCtx(); _doPrime(); },
    _start:      _start,
    _stop:       _stop,
  };
})();
