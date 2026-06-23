/* ── Мікро-чат (публічний) — chat.js ── */
(function () {
  'use strict';

  var _mcLastTs = 0;
  var _mcPollTimer = null;
  var _mcSending = false;

  function _esc(s) {
    return String(s || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function _fmtTime(ts) {
    var d = new Date(ts);
    var h = d.getHours().toString().padStart(2, '0');
    var m = d.getMinutes().toString().padStart(2, '0');
    return h + ':' + m;
  }

  // Повертає відображуване ім'я
  function _mcDisplayName(m) {
    if (m.role === 'guest') {
      var guestNum = m.id ? String(m.id).slice(-3).replace(/^0+/, '') || m.id : '?';
      return 'Гість#' + guestNum;
    }
    if (m.is_bot) return m.bot_name || 'Бот';
    if (m.nickname) return '@' + m.nickname;
    return '?';
  }

  // Генерує унікальний колір для користувача з його user_id
  var _nickColorCache = {};
  function _mcNickColor(userId) {
    if (_nickColorCache[userId]) return _nickColorCache[userId];
    var palette = [
      '#64b5f6', '#81c784', '#ffb74d', '#f06292', '#ba68c8',
      '#4db6ac', '#fff176', '#ff8a65', '#90caf9', '#a5d6a7',
      '#ce93d8', '#80cbc4'
    ];
    var idx = Math.abs(userId || 0) % palette.length;
    _nickColorCache[userId] = palette[idx];
    return palette[idx];
  }

  // Генерує fingerprint браузера (для анонімів) — мінімум 8 символів
  function _mcFingerprint() {
    var raw = [
      navigator.userAgent,
      screen.width + 'x' + screen.height,
      new Date().getTimezoneOffset(),
      navigator.language || '',
      navigator.hardwareConcurrency || 0,
      screen.colorDepth || 0
    ].join('|');
    var h1 = 0, h2 = 0x9e3779b9;
    for (var i = 0; i < raw.length; i++) {
      var c = raw.charCodeAt(i);
      h1 = Math.imul(31, h1) + c | 0;
      h2 = Math.imul(1540483477, h2 ^ c) | 0;
    }
    var fp = Math.abs(h1).toString(36) + Math.abs(h2).toString(36);
    // Гарантуємо мінімум 8 символів
    while (fp.length < 8) fp = '0' + fp;
    return fp;
  }

  function _mcUpdateAuthState() {
    var u = window.curUser;
    if (!u) {
      try { u = JSON.parse(localStorage.getItem('mu') || 'null'); } catch (e) { u = null; }
    }
    var row = document.getElementById('mc-input-row');
    var hint = document.getElementById('mc-auth-hint');
    if (!row) return;
    // Поле вводу — завжди видиме (авторизовані і гості можуть писати)
    row.style.display = 'flex';
    if (hint) hint.style.display = u ? 'none' : 'block';
  }

  function _mcAppend(msgs) {
    var box = document.getElementById('mc-messages');
    if (!box) return;
    var atBottom = box.scrollTop + box.clientHeight >= box.scrollHeight - 8;
    msgs.forEach(function (m) {
      if (!m || !m.id) return;
      // Не додавати дублікати (id вже є в DOM)
      if (box.querySelector('.mc-msg[data-id="' + parseInt(m.id, 10) + '"]')) return;
      if (m.created_at > _mcLastTs) _mcLastTs = m.created_at;
      var displayName = _mcDisplayName(m);
      var nickColor;
      if (m.role === 'admin') {
        nickColor = '#ff4444';
      } else if (m.role === 'moder') {
        nickColor = '#4caf50';
      } else if (m.role === 'guest') {
        nickColor = '#778899';
      } else {
        nickColor = _mcNickColor(m.user_id);
      }
      var div = document.createElement('div');
      div.className = 'mc-msg';
      div.dataset.id = m.id;
      var safeId = parseInt(m.id, 10) || 0;
      div.innerHTML =
        '<span class="mc-msg-nick" style="color:' + nickColor + '">' + _esc(displayName) + ':</span>' +
        '<span class="mc-msg-text">' + _esc(m.message) + '</span>' +
        '<span class="mc-msg-time">' + _fmtTime(m.created_at) + '</span>' +
        '<span class="mc-msg-report" title="Поскаржитись" onclick="window._mcReport(' + safeId + ')">⚑</span>';
      box.appendChild(div);
      // Гостьові повідомлення зникають з UI через 2 хвилини
      if (m.role === 'guest') {
        var removeAt = m.created_at + 120000;
        var delay = Math.max(0, removeAt - Date.now());
        var capturedDiv = div;
        setTimeout(function () {
          if (capturedDiv.parentNode) capturedDiv.parentNode.removeChild(capturedDiv);
        }, delay);
      }
    });
    if (atBottom) box.scrollTop = box.scrollHeight;
  }

  function _mcSystemMsg(text) {
    var box = document.getElementById('mc-messages');
    if (!box) return;
    var div = document.createElement('div');
    div.className = 'mc-msg-system';
    div.textContent = text;
    box.appendChild(div);
    box.scrollTop = box.scrollHeight;
  }

  // Видаляє повідомлення з DOM за id
  function _mcRemoveFromDom(msgId) {
    var el = document.querySelector('.mc-msg[data-id="' + parseInt(msgId, 10) + '"]');
    if (el && el.parentNode) el.parentNode.removeChild(el);
  }

  // Викликається з WebSocket broadcast (index.html)
  window._mcOnDelete = function (msgId) { _mcRemoveFromDom(msgId); };

  async function _mcPoll() {
    try {
      var r = await fetch('/api/chat/messages?since=' + _mcLastTs, { credentials: 'include' });
      if (!r.ok) return;
      var d = await r.json();
      if (d.disabled) return;
      if (d.messages && d.messages.length) _mcAppend(d.messages);
      // Видаляємо з DOM повідомлення що були видалені адміном
      if (d.deleted && d.deleted.length) {
        d.deleted.forEach(function (id) { _mcRemoveFromDom(id); });
      }
    } catch (e) { /* мережева помилка — ігноруємо */ }
  }

  async function _mcSend() {
    if (_mcSending) return;
    var u = window.curUser;
    if (!u) { try { u = JSON.parse(localStorage.getItem('mu') || 'null'); } catch (e) { u = null; } }
    var isGuest = !u;
    var inp = document.getElementById('mc-input');
    var btn = document.getElementById('mc-send');
    if (!inp) return;
    var text = inp.value.trim();
    if (!text) return;
    if (text.length > 100) {
      if (window.showN) window.showN('Максимум 100 символів', true);
      return;
    }
    if (/https?:\/\/|www\.|\.com|\.ua|\.org|\.net/i.test(text)) {
      if (window.showN) window.showN('Посилання заборонені в чаті', true);
      return;
    }
    _mcSending = true;
    if (btn) btn.disabled = true;
    inp.value = '';
    try {
      var payload = { message: text };
      if (isGuest) payload.fp = _mcFingerprint();
      var r = await fetch('/api/chat/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(payload)
      });
      var d = {};
      try { d = await r.json(); } catch (_) {}
      if (!r.ok || !d.ok) {
        inp.value = text;
        var errMsg = d.detail || (r.status === 429 ? 'Занадто часто. Зачекайте.' : r.status === 403 ? 'Чат вимкнений' : 'Помилка відправки');
        if (window.showN) window.showN(errMsg, true);
      } else {
        if (d.msg && d.msg.id) {
          _mcAppend([d.msg]);
        }
        // Завжди прокручуємо і оновлюємо після відправки
        var box = document.getElementById('mc-messages');
        if (box) box.scrollTop = box.scrollHeight;
        // Негайний poll щоб підтвердити і підтягнути будь-які нові повідомлення
        setTimeout(_mcPoll, 300);
      }
    } catch (e) {
      inp.value = text;
      if (window.showN) window.showN('Помилка мережі', true);
    } finally {
      _mcSending = false;
      if (btn) btn.disabled = false;
      if (inp) inp.focus();
    }
  }

  window._mcReport = async function (msgId) {
    var safeId = parseInt(msgId, 10);
    if (!safeId || safeId <= 0) return;
    var _u = window.curUser;
    if (!_u) { try { _u = JSON.parse(localStorage.getItem('mu') || 'null'); } catch (e) { _u = null; } }
    if (!_u) {
      if (window.showN) window.showN('Потрібна авторизація', true);
      return;
    }
    try {
      var r = await fetch('/api/chat/report/' + safeId, { method: 'POST', credentials: 'include' });
      var d = await r.json();
      if (d.ok) {
        if (window.showN) window.showN('Скаргу надіслано');
        var el = document.querySelector('.mc-msg[data-id="' + msgId + '"] .mc-msg-report');
        if (el) el.style.color = '#e05070';
      }
    } catch (e) { /* ignore */ }
  };

  function _mcToggle(e) {
    if (e && e.target && e.target.id === 'mc-toggle') {
      // кнопка — не зупиняємо, але це обробляється нижче
    }
    var mc = document.getElementById('micro-chat');
    if (!mc) return;
    var collapsed = mc.classList.toggle('mc-collapsed');
    localStorage.setItem('mc_collapsed', collapsed ? '1' : '0');
    var btn = document.getElementById('mc-toggle');
    if (btn) btn.textContent = collapsed ? '+' : '−';
  }

  window._mcInit = function () {
    var colors = window.COLORS || {};
    var enabled = (colors.chat_enabled && colors.chat_enabled.value !== undefined
      ? colors.chat_enabled.value : '1') !== '0';
    var mc = document.getElementById('micro-chat');
    if (!mc) return;
    if (!enabled) { mc.classList.add('mc-hidden'); return; }
    mc.classList.remove('mc-hidden');

    // Стан згорнуто
    if (localStorage.getItem('mc_collapsed') === '1') {
      mc.classList.add('mc-collapsed');
      var btn = document.getElementById('mc-toggle');
      if (btn) btn.textContent = '+';
    }

    _mcUpdateAuthState();

    // Заголовок — toggle по кліку
    var header = document.getElementById('mc-header');
    if (header) header.addEventListener('click', _mcToggle);

    // Кнопка надіслати
    var sendBtn = document.getElementById('mc-send');
    if (sendBtn) sendBtn.addEventListener('click', _mcSend);

    // Enter у полі вводу + лічильник символів
    var inp = document.getElementById('mc-input');
    var charsEl = document.getElementById('mc-chars');
    if (inp) {
      inp.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); _mcSend(); }
      });
      inp.addEventListener('input', function () {
        var len = inp.value.length;
        if (charsEl) {
          charsEl.style.display = len > 0 ? '' : 'none';
          charsEl.textContent = len + '/100';
          charsEl.style.color = len >= 90 ? '#e05070' : len >= 70 ? '#ffb74d' : '#2a4a5a';
        }
      });
    }

    // Завантажуємо початкову історію
    _mcPoll();

    // Polling
    var interval = parseInt(
      (colors.chat_poll_interval && colors.chat_poll_interval.value) || '4000'
    );
    if (isNaN(interval) || interval < 1000) interval = 4000;
    _mcPollTimer = setInterval(_mcPoll, interval);
  };

  // Оновлення стану авторизації — викликається з updateAuthUI()
  window._mcUpdateAuthState = _mcUpdateAuthState;
})();
