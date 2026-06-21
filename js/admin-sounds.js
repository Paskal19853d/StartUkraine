/* ── Звукові сповіщення адмін-панелі ── admin-sounds.js ── */
(function () {
  'use strict';

  var _LS_KEY  = 'adm_sounds';
  var _enabled = { join: false, leave: false, chat: false };

  /* ── Web Audio API (основний метод) ── */
  var _ctx = null;
  var _ctxReady = false;

  function _getCtx() {
    if (!_ctx) {
      try { _ctx = new (window.AudioContext || window.webkitAudioContext)(); } catch (e) {}
    }
    return _ctx;
  }

  /* Розблоковуємо при будь-якому кліку */
  document.addEventListener('click', function _unlock() {
    var ctx = _getCtx();
    if (ctx && ctx.state === 'suspended') {
      ctx.resume().then(function () { _ctxReady = true; });
    } else if (ctx) {
      _ctxReady = true;
    }
  }, true);

  function _beep(ctx, freq, dur, type, vol, t) {
    try {
      var osc = ctx.createOscillator();
      var g   = ctx.createGain();
      osc.connect(g);
      g.connect(ctx.destination);
      osc.type = type || 'sine';
      osc.frequency.setValueAtTime(freq, t);
      g.gain.setValueAtTime(vol || 0.15, t);
      g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
      osc.start(t);
      osc.stop(t + dur + 0.05);
    } catch (e) {}
  }

  function _playJoin(ctx) {
    var t = ctx.currentTime;
    _beep(ctx, 880,  0.13, 'sine', 0.16, t);
    _beep(ctx, 1047, 0.20, 'sine', 0.16, t + 0.15);
  }

  function _playLeave(ctx) {
    var t = ctx.currentTime;
    _beep(ctx, 1047, 0.14, 'sine', 0.18, t);
    _beep(ctx, 784,  0.14, 'sine', 0.15, t + 0.17);
    _beep(ctx, 523,  0.28, 'sine', 0.13, t + 0.34);
  }

  function _playChat(ctx) {
    var t = ctx.currentTime;
    _beep(ctx, 1200, 0.07, 'square', 0.09, t);
    _beep(ctx, 1200, 0.07, 'square', 0.09, t + 0.11);
    _beep(ctx, 1500, 0.11, 'square', 0.11, t + 0.23);
  }

  function _doPlayCtx(type) {
    var ctx = _getCtx();
    if (!ctx) return false;
    if (ctx.state === 'suspended') return false; /* не розблоковано */
    if (type === 'join')  _playJoin(ctx);
    if (type === 'leave') _playLeave(ctx);
    if (type === 'chat')  _playChat(ctx);
    return true;
  }

  /* ── Запасний метод: програмно генерований WAV через data URI ── */
  /* Короткий 440 Гц синус 0.15с, 8bit 8000Hz mono */
  function _makeWav(freqs) {
    /* freqs = [{hz, ms}] */
    var rate   = 8000;
    var bits   = 8;
    var total  = freqs.reduce(function (s, f) { return s + Math.round(rate * f.ms / 1000); }, 0);
    var buf    = new Uint8Array(44 + total);
    var view   = new DataView(buf.buffer);
    /* WAV header */
    var w = function (off, val, len) {
      for (var i = 0; i < len; i++) view.setUint8(off + i, (val >> (8 * i)) & 0xff);
    };
    var str = function (off, s) { for (var i = 0; i < s.length; i++) buf[off + i] = s.charCodeAt(i); };
    str(0, 'RIFF'); w(4, 36 + total, 4); str(8, 'WAVE');
    str(12, 'fmt '); w(16, 16, 4); w(20, 1, 2); w(22, 1, 2);
    w(24, rate, 4); w(28, rate, 4); w(32, 1, 2); w(34, bits, 2);
    str(36, 'data'); w(40, total, 4);
    var off = 44;
    freqs.forEach(function (f) {
      var samples = Math.round(rate * f.ms / 1000);
      for (var i = 0; i < samples; i++) {
        var envelope = i < 200 ? i / 200 : Math.max(0, 1 - (i - 200) / (samples - 200));
        buf[off++] = Math.round(127 + 80 * envelope * Math.sin(2 * Math.PI * f.hz * i / rate));
      }
    });
    /* base64 */
    var bin = '';
    buf.forEach(function (b) { bin += String.fromCharCode(b); });
    return 'data:audio/wav;base64,' + btoa(bin);
  }

  var _wavCache = {};
  function _getWav(type) {
    if (_wavCache[type]) return _wavCache[type];
    var freqs;
    if (type === 'join')  freqs = [{hz: 880, ms: 120}, {hz: 1047, ms: 180}];
    if (type === 'leave') freqs = [{hz: 1047, ms: 120}, {hz: 784, ms: 120}, {hz: 523, ms: 240}];
    if (type === 'chat')  freqs = [{hz: 1200, ms: 70}, {hz: 1200, ms: 70}, {hz: 1500, ms: 110}];
    _wavCache[type] = _makeWav(freqs);
    return _wavCache[type];
  }

  function _doPlayWav(type) {
    try {
      var a = new Audio(_getWav(type));
      a.volume = 0.5;
      a.play().catch(function () {});
    } catch (e) {}
  }

  /* ── Головна функція відтворення ── */
  function _doPlay(type) {
    /* Спочатку пробуємо Web Audio (краща якість) */
    if (!_doPlayCtx(type)) {
      /* Fallback: WAV через Audio element — працює без user gesture */
      _doPlayWav(type);
    }
  }

  /* ── prefsз localStorage ── */
  function _loadPrefs() {
    try {
      var parsed = JSON.parse(localStorage.getItem(_LS_KEY) || '{}');
      Object.keys(_enabled).forEach(function (k) {
        if (parsed[k] !== undefined) _enabled[k] = !!parsed[k];
      });
    } catch (e) {}
    _syncCheckboxes();
  }

  function _savePrefs() {
    try { localStorage.setItem(_LS_KEY, JSON.stringify(_enabled)); } catch (e) {}
  }

  function _syncCheckboxes() {
    Object.keys(_enabled).forEach(function (k) {
      var el = document.getElementById('snd-' + k);
      if (el) el.checked = _enabled[k];
    });
  }

  /* ── Публічне API ── */

  /* З WS — з перевіркою enabled */
  window._admSound = function (type) {
    if (!_enabled[type]) return;
    _doPlay(type);
  };

  /* Кнопка "Тест" — завжди */
  window._admSoundTest = function (type) {
    _doPlay(type);
  };

  /* Чекбокс onchange — розблоковує ctx при першому кліку */
  window._admSoundToggle = function (type, val) {
    _enabled[type] = !!val;
    _savePrefs();
    var ctx = _getCtx();
    if (ctx && ctx.state === 'suspended') {
      ctx.resume().then(function () { _ctxReady = true; });
    }
  };

  /* ── Ініціалізація ── */
  _loadPrefs();

  /* Синхронізація чекбоксів при відкритті секції */
  var _syncTimer   = null;
  var _origShowSec = window.showSec;
  window.showSec = function (sec) {
    if (typeof _origShowSec === 'function') _origShowSec.call(this, sec);
    if (sec === 'chat') {
      if (_syncTimer) clearTimeout(_syncTimer);
      _syncTimer = setTimeout(_syncCheckboxes, 80);
    }
  };

  /* Прибираємо стару плашку якщо є */
  var bar = document.getElementById('snd-unlock-bar');
  if (bar) bar.style.display = 'none';

})();
