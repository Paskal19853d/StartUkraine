/* ── Адмін-панель: Мікро-чат ── chat-admin.js ── */
(function () {
  'use strict';

  /* ─── стан ─────────────────────────────────── */
  var _activeTab  = 'msgs';

  /* ─── перемикання вкладок ─────────────────── */
  window.chatTab = function (name) {
    _activeTab = name;
    /* пани */
    document.querySelectorAll('.chat-tab-pane').forEach(function (el) {
      var show = el.id === 'chat-tab-' + name;
      el.style.display = show ? '' : 'none';
      el.classList.toggle('active', show);
    });
    /* кнопки — визначаємо по позиції */
    var btns = document.querySelectorAll('#chat-tabs .tab-btn');
    var order = ['msgs', 'reports', 'words', 'settings'];
    btns.forEach(function (btn, i) {
      btn.classList.toggle('active', order[i] === name);
    });
    if (name === 'msgs')     chatLoadMsgs();
    if (name === 'reports')  chatLoadReports();
    if (name === 'words')    chatLoadWords();
    if (name === 'settings') chatLoadSettings();
  };

  /* ─── повідомлення ────────────────────────── */
  window.chatLoadMsgs = function () {
    var showDel = document.getElementById('chat-show-deleted');
    var deleted = showDel && showDel.checked ? '&deleted=1' : '';
    var container = document.getElementById('chat-msgs-list');
    if (!container) return;
    container.innerHTML = '<div class="chat-adm-empty">Завантаження…</div>';

    fetch('/api/admin/chat/messages?limit=100' + deleted)
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var items = d.messages || [];
        if (!items.length) {
          container.innerHTML = '<div class="chat-adm-empty">Немає повідомлень</div>';
          return;
        }
        var html = '<table class="chat-adm-table">'
          + '<thead><tr><th>ID</th><th>Юзер</th><th>Повідомлення</th><th>Час</th><th></th></tr></thead><tbody>';
        items.forEach(function (m) {
          var delStyle = m.is_deleted ? 'opacity:.45' : '';
          var userLabel = m.is_bot
            ? '<span style="color:#7a7ab0">' + _esc(m.bot_name || 'Бот') + '</span> <span style="font-size:9px;color:#555;background:rgba(120,120,180,.15);border-radius:3px;padding:1px 4px">бот</span>'
            : '<span style="color:var(--accent)">' + _esc(m.nickname || m.name || '?') + '</span>';
          html += '<tr id="cmsg-' + m.id + '" style="' + delStyle + '">'
            + '<td style="width:40px;color:var(--muted)">' + m.id + '</td>'
            + '<td style="white-space:nowrap">' + userLabel + '</td>'
            + '<td style="word-break:break-word">' + _esc(m.message) + '</td>'
            + '<td style="color:var(--muted);font-size:10px;white-space:nowrap">' + _fmtTs(m.created_at) + '</td>'
            + '<td style="width:60px">'
            + (m.is_deleted
              ? '<span style="color:var(--muted);font-size:10px">видалено</span>'
              : '<button class="btn btn-r" style="font-size:11px;padding:3px 8px" onclick="chatDeleteMsg(' + m.id + ')">'
                + '<svg class="adm-ico"><use href="#ico-trash"/></svg></button>')
            + '</td></tr>';
        });
        html += '</tbody></table>';
        container.innerHTML = html;
      })
      .catch(function () {
        container.innerHTML = '<div class="chat-adm-empty">Помилка завантаження</div>';
      });
  };

  window.chatDeleteMsg = function (id) {
    if (!confirm('Видалити повідомлення #' + id + '?')) return;
    fetch('/api/admin/chat/' + id, { method: 'DELETE' })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (d.ok) {
          if (window.showN) window.showN('Повідомлення видалено');
          chatLoadMsgs();
        } else {
          if (window.showN) window.showN(d.detail || 'Помилка', true);
        }
      });
  };

  /* ─── скарги ──────────────────────────────── */
  window.chatLoadReports = function () {
    var container = document.getElementById('chat-reports-list');
    if (!container) return;
    container.innerHTML = '<div class="chat-adm-empty">Завантаження…</div>';

    fetch('/api/admin/chat/reports')
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var items = d.reports || [];
        /* Оновити лічильник у вкладці */
        var repCnt = document.getElementById('chat-rep-cnt');
        if (repCnt) repCnt.textContent = items.length ? ' (' + items.length + ')' : '';

        if (!items.length) {
          container.innerHTML = '<div class="chat-adm-empty">Скарг немає</div>';
          return;
        }
        var html = '<table class="chat-adm-table">'
          + '<thead><tr><th>ID</th><th>Повідомлення</th><th>Хто скаржиться</th><th>Час</th><th></th></tr></thead><tbody>';
        items.forEach(function (rep) {
          html += '<tr>'
            + '<td style="width:40px;color:var(--muted)">' + rep.id + '</td>'
            + '<td><span style="color:var(--muted)">#' + rep.msg_id + '</span> '
            + '<em style="color:var(--text2)">' + _esc(rep.message || '—') + '</em></td>'
            + '<td style="color:var(--accent)">' + _esc(rep.reporter_nick || '?') + '</td>'
            + '<td style="color:var(--muted);font-size:10px;white-space:nowrap">' + _fmtTs(rep.created_at) + '</td>'
            + '<td><button class="btn btn-r" style="font-size:11px;padding:3px 8px" onclick="chatDeleteMsg(' + rep.msg_id + ')">'
            + '<svg class="adm-ico"><use href="#ico-trash"/></svg> Видалити</button></td></tr>';
        });
        html += '</tbody></table>';
        container.innerHTML = html;
      })
      .catch(function () {
        container.innerHTML = '<div class="chat-adm-empty">Помилка завантаження</div>';
      });
  };

  /* ─── заборонені слова ────────────────────── */
  window.chatLoadWords = function () {
    var container = document.getElementById('chat-words-list');
    if (!container) return;
    container.innerHTML = '<div class="chat-adm-empty">Завантаження…</div>';

    fetch('/api/admin/chat/banned-words')
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var items = d.words || [];
        if (!items.length) {
          container.innerHTML = '<div class="chat-adm-empty">Список порожній. Додайте перше слово.</div>';
          return;
        }
        var html = '<table class="chat-adm-table">'
          + '<thead><tr><th>Слово / фраза</th><th>Категорія</th><th></th></tr></thead><tbody>';
        items.forEach(function (w) {
          html += '<tr id="cw-' + w.id + '">'
            + '<td style="font-weight:600">' + _esc(w.word) + '</td>'
            + '<td><span class="chat-word-cat">' + _esc(w.category) + '</span></td>'
            + '<td style="width:50px"><button class="btn btn-r" style="font-size:11px;padding:3px 8px" onclick="chatDeleteWord(' + w.id + ')">'
            + '<svg class="adm-ico"><use href="#ico-trash"/></svg></button></td></tr>';
        });
        html += '</tbody></table>';
        container.innerHTML = html;
      })
      .catch(function () {
        container.innerHTML = '<div class="chat-adm-empty">Помилка завантаження</div>';
      });
  };

  window.chatAddWord = function () {
    var inp = document.getElementById('chat-word-inp');
    var sel = document.getElementById('chat-word-cat');
    if (!inp) return;
    var word = inp.value.trim().toLowerCase();
    if (!word) { if (window.showN) window.showN('Введіть слово', true); return; }
    var cat = sel ? sel.value : 'profanity';

    fetch('/api/admin/chat/banned-words', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ word: word, category: cat })
    })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (d.ok) {
          inp.value = '';
          if (window.showN) window.showN('Слово додано');
          chatLoadWords();
        } else {
          if (window.showN) window.showN(d.detail || 'Помилка', true);
        }
      });
  };

  /* читання файлу в textarea */
  window.chatImportFileRead = function () {
    var file = document.getElementById('chat-import-file').files[0];
    if (!file) return;
    if (file.size > 512 * 1024) {
      if (window.showN) window.showN('Файл занадто великий (макс. 512 КБ)', true);
      return;
    }
    var reader = new FileReader();
    reader.onload = function (e) {
      var ta = document.getElementById('chat-import-text');
      if (ta) ta.value = e.target.result;
      var status = document.getElementById('chat-import-status');
      if (status) status.textContent = 'Файл завантажено: ' + file.name;
    };
    reader.readAsText(file, 'UTF-8');
  };

  /* відправка імпорту на сервер */
  window.chatImportWords = function () {
    var ta  = document.getElementById('chat-import-text');
    var cat = document.getElementById('chat-import-cat');
    var status = document.getElementById('chat-import-status');
    if (!ta || !ta.value.trim()) {
      if (window.showN) window.showN('Вставте або завантажте список слів', true);
      return;
    }
    if (status) status.textContent = 'Імпортую…';

    fetch('/api/admin/chat/banned-words/import', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: ta.value, category: cat ? cat.value : 'profanity' })
    })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (d.ok) {
          var msg = 'Додано ' + d.added + ' з ' + d.total + ' слів';
          if (status) status.textContent = msg;
          if (window.showN) window.showN(msg);
          ta.value = '';
          var fi = document.getElementById('chat-import-file');
          if (fi) fi.value = '';
          chatLoadWords();
        } else {
          if (status) status.textContent = '';
          if (window.showN) window.showN(d.detail || 'Помилка', true);
        }
      })
      .catch(function () {
        if (status) status.textContent = '';
        if (window.showN) window.showN('Помилка мережі', true);
      });
  };

  window.chatDeleteWord = function (id) {
    fetch('/api/admin/chat/banned-words/' + id, { method: 'DELETE' })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (d.ok) {
          var row = document.getElementById('cw-' + id);
          if (row) row.remove();
          if (window.showN) window.showN('Видалено');
        } else {
          if (window.showN) window.showN(d.detail || 'Помилка', true);
        }
      });
  };

  /* ─── налаштування ────────────────────────── */
  window.chatLoadSettings = function () {
    fetch('/api/colors')
      .then(function (r) { return r.json(); })
      .then(function (colors) {
        var en  = document.getElementById('chat-cfg-enabled');
        var cnt = document.getElementById('chat-cfg-count');
        var itv = document.getElementById('chat-cfg-interval');
        if (en)  en.checked = ((colors.chat_enabled || {}).value || '1') !== '0';
        if (cnt) cnt.value  = (colors.chat_history_count || {}).value || '50';
        if (itv) itv.value  = (colors.chat_poll_interval || {}).value || '4000';
      });
    botsLoad();
  };

  /* ─── чат-боти ────────────────────────────── */
  window.botsLoad = function () {
    fetch('/api/admin/chat/bots')
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var tog = document.getElementById('bots-enabled-tog');
        if (tog) tog.checked = !!d.enabled;
        var cntEl = document.getElementById('bots-online-count');
        if (cntEl) cntEl.textContent = d.bot_online_count || 0;
        var list = document.getElementById('bots-phrases-list');
        if (!list) return;
        var phrases = d.phrases || [];
        if (!phrases.length) {
          list.innerHTML = '<div style="font-size:12px;color:var(--muted);padding:6px 0">Фраз немає</div>';
          return;
        }
        list.innerHTML = phrases.map(function (p) {
          return '<div style="display:flex;align-items:center;gap:6px;padding:4px 6px;background:var(--surface3);border-radius:5px;border:1px solid var(--border)">'
            + '<span style="flex:1;font-size:12px;color:' + (p.is_active ? 'var(--text1)' : 'var(--muted)') + '">' + _esc(p.phrase) + '</span>'
            + '<button class="btn" style="font-size:10px;padding:2px 7px;min-width:0" onclick="botsTogglePhrase(' + p.id + ')" title="' + (p.is_active ? 'Вимкнути' : 'Увімкнути') + '">'
            + (p.is_active ? '<svg class="adm-ico"><use href="#ico-check"/></svg>' : '<svg class="adm-ico"><use href="#ico-cross"/></svg>') + '</button>'
            + '<button class="btn btn-r" style="font-size:10px;padding:2px 7px;min-width:0" onclick="botsDeletePhrase(' + p.id + ')">'
            + '<svg class="adm-ico"><use href="#ico-trash"/></svg></button>'
            + '</div>';
        }).join('');
      })
      .catch(function () {});
  };

  window.botsSetEnabled = function (enabled) {
    fetch('/api/admin/chat/bots/config', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled: enabled })
    })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (window.showN) window.showN(d.ok ? (enabled ? 'Ботів увімкнено' : 'Ботів вимкнено') : 'Помилка', !d.ok);
      });
  };

  window.botsAddPhrase = function () {
    var inp = document.getElementById('bots-new-phrase');
    if (!inp) return;
    var phrase = inp.value.trim();
    if (!phrase) { if (window.showN) window.showN('Введіть фразу', true); return; }
    fetch('/api/admin/chat/bots/phrase', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phrase: phrase, category: 'general' })
    })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (d.ok) {
          inp.value = '';
          if (window.showN) window.showN('Фразу додано');
          botsLoad();
        } else {
          if (window.showN) window.showN(d.detail || 'Помилка', true);
        }
      });
  };

  window.botsDeletePhrase = function (id) {
    if (!confirm('Видалити фразу?')) return;
    fetch('/api/admin/chat/bots/phrase/' + id, { method: 'DELETE' })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (d.ok) { if (window.showN) window.showN('Видалено'); botsLoad(); }
        else { if (window.showN) window.showN(d.detail || 'Помилка', true); }
      });
  };

  window.botsTogglePhrase = function (id) {
    fetch('/api/admin/chat/bots/phrase/' + id + '/toggle', { method: 'PUT' })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (d.ok) botsLoad();
        else { if (window.showN) window.showN(d.detail || 'Помилка', true); }
      });
  };

  window.chatSaveCfg = function (key, value) {
    fetch('/api/admin/color', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ key: key, value: String(value) })
    })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (window.showN) window.showN(d.ok ? 'Збережено' : (d.detail || 'Помилка'), !d.ok);
      });
  };

  /* ─── авто-ініціалізація при відкритті секції */
  var _origShowSec = window.showSec;
  window.showSec = function (sec) {
    if (typeof _origShowSec === 'function') _origShowSec(sec);
    if (sec === 'chat') {
      chatTab(_activeTab || 'msgs');
      /* Бейдж скарг у навбарі */
      fetch('/api/admin/chat/reports')
        .then(function (r) { return r.json(); })
        .then(function (d) {
          var nb = document.getElementById('chat-nb');
          if (!nb) return;
          var cnt = (d.reports || []).length;
          nb.textContent = cnt;
          nb.style.display = cnt ? '' : 'none';
        })
        .catch(function () {});
    }
  };

  /* ─── утиліти ─────────────────────────────── */
  function _esc(s) {
    return String(s || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function _fmtTs(ts) {
    if (!ts) return '—';
    var d = new Date(Number(ts));
    return d.toLocaleDateString('uk-UA') + ' '
      + d.getHours().toString().padStart(2, '0') + ':'
      + d.getMinutes().toString().padStart(2, '0');
  }

})();
