(function () {
  'use strict';

  var _curData = null; // збережені дані профілю

  function escH(s) {
    return String(s || '')
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function plural(n, one, few, many) {
    var m = n % 100;
    if (m >= 11 && m <= 14) return many;
    var r = n % 10;
    if (r === 1) return one;
    if (r >= 2 && r <= 4) return few;
    return many;
  }

  function fmtNum(n) {
    n = parseInt(n, 10) || 0;
    if (n >= 1000) return (n / 1000).toFixed(1).replace('.0', '') + 'k';
    return String(n);
  }

  function showError(msg, showLogin) {
    document.getElementById('loading-screen').style.display = 'none';
    var es = document.getElementById('error-screen');
    es.style.display = 'flex';
    document.getElementById('error-msg').textContent = msg;
    if (showLogin) {
      var lnk = document.getElementById('error-login-link');
      if (lnk) lnk.style.display = 'inline';
    }
  }

  function starSVG() {
    return '<svg viewBox="0 0 24 24" fill="currentColor">' +
      '<path d="M12 2l2.7 7.5H22l-6.4 4.7 2.4 7.4L12 17.3l-6 4.3 2.4-7.4L2 9.5h7.3z"/></svg>';
  }

  function cardHTML(m) {
    var name = [m.last, m.first, m.mid].filter(Boolean).join(' ') || '—';
    var href = m.slug ? '/memorial/' + m.slug : '/card?id=' + m.id;
    var photo = m.photo
      ? '<img class="mem-photo" src="' + escH(m.photo) + '" alt="' + escH(name) +
        '" loading="lazy" onerror="this.onerror=null;this.src=\'/img/foto_false.png\'">'
      : '<div class="mem-photo-ph">' + starSVG() + '</div>';
    var death = m.death ? '<span class="mem-death">' + escH(m.death) + '</span>' : '<span></span>';
    var likes = m.likes ? '<span class="mem-likes">&#9733; ' + m.likes + '</span>' : '';
    return '<a class="mem-card" href="' + href + '">' +
      photo +
      '<div class="mem-info">' +
        '<div class="mem-name">' + escH(name) + '</div>' +
        '<div class="mem-foot">' + death + likes + '</div>' +
      '</div></a>';
  }

  function buildInfoTab(d) {
    var roleMap = { admin: 'Адміністратор', moder: 'Модератор', user: 'Учасник' };
    var rows = [
      ['@', '@' + escH(d.nickname), 'Нікнейм'],
      ['&#9733;', roleMap[d.role] || d.role, 'Роль']
    ];
    if (d.created) {
      var dt = new Date(d.created * 1000);
      rows.push(['&#128197;', dt.toLocaleDateString('uk-UA'), 'Дата реєстрації']);
    }
    var cnt = d.count || 0;
    rows.push(['&#11088;', String(cnt) + ' ' + plural(cnt, 'меморіал', 'меморіали', 'меморіалів'), 'Меморіалів додано']);
    if (d.email) rows.push(['&#9993;', escH(d.email), 'Email']);
    if (d.phone) rows.push(['&#128222;', escH(d.phone), 'Телефон']);
    return rows.map(function (row) {
      return '<div class="info-row">' +
        '<span class="info-icon">' + row[0] + '</span>' +
        '<div><div class="info-val">' + row[1] + '</div>' +
        '<div class="info-lbl">' + row[2] + '</div></div></div>';
    }).join('');
  }

  var _TAB_TITLES = {
    memorials: 'Меморіали',
    settings:  'Налаштування',
    legacy:    'Спадщина',
    info:      'Інформація'
  };

  window.switchTab = function (id, btn) {
    // Panels
    document.querySelectorAll('.tab-panel').forEach(function (p) { p.classList.remove('active'); });
    var panel = document.getElementById('tab-' + id);
    if (panel) panel.classList.add('active');

    // Nav buttons (sidebar) + tab bar buttons (header) — both have data-tab
    document.querySelectorAll('.x-nav-btn, .x-tab-btn').forEach(function (b) {
      b.classList.toggle('active', b.dataset.tab === id);
    });

    // Content title
    var titleEl = document.getElementById('x-content-title');
    if (titleEl) titleEl.textContent = _TAB_TITLES[id] || '';
  };

  window.copyProfileLink = function () {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(location.href)
        .then(function () { settMsg('Посилання скопійовано', 'ok'); })
        .catch(function () { prompt('Скопійуй посилання:', location.href); });
    } else {
      prompt('Скопійуй посилання:', location.href);
    }
  };

  /* ── Settings tab logic ── */

  window.settNickInput = function (el) {
    var v = el.value;
    var hint = document.getElementById('hint-sett-nick');
    if (!hint) return;
    if (!v) { hint.textContent = 'Укр/латинські літери, цифри, _ . -'; hint.className = 'sett-field-hint'; return; }
    var re = /^[а-яА-ЯіІїЇєЄґҐa-zA-Z0-9_.\-]{2,50}$/u;
    if (!re.test(v)) {
      hint.textContent = '2–50 символів, лише літери, цифри, _ . -';
      hint.className = 'sett-field-hint err';
    } else {
      hint.textContent = 'Виглядає добре';
      hint.className = 'sett-field-hint ok';
    }
  };

  window.settPassStrength = function (val) {
    var fill = document.getElementById('sett-pass-fill');
    var hint = document.getElementById('sett-pass-hint');
    if (!fill || !hint) return;
    if (!val) { fill.style.width = '0'; hint.textContent = ''; return; }
    var score = 0;
    if (val.length >= 10) score++;
    if (/[A-Z]/.test(val)) score++;
    if (/[a-z]/.test(val)) score++;
    if (/\d/.test(val)) score++;
    if (/[^A-Za-z\d]/.test(val)) score++;
    var colors = ['#e05050','#e05050','#e08830','#c8a020','#4a9e6a'];
    var labels = ['Дуже слабкий','Слабкий','Середній','Хороший','Відмінний'];
    fill.style.width = (score * 20) + '%';
    fill.style.background = colors[score - 1] || '#e05050';
    hint.textContent = labels[score - 1] || '';
    hint.className = score >= 3 ? 'sett-field-hint ok' : 'sett-field-hint err';
  };

  function settMsg(text, type) {
    var el = document.getElementById('sett-save-msg');
    if (!el) return;
    el.textContent = text;
    el.className = 'sett-save-msg ' + (type || '');
    if (type === 'ok') setTimeout(function () { el.textContent = ''; el.className = 'sett-save-msg'; }, 3000);
  }

  window.settSave = async function () {
    var nick = (document.getElementById('sett-nick').value || '').trim();
    var email = (document.getElementById('sett-email').value || '').trim();
    var email2 = (document.getElementById('sett-email2').value || '').trim();
    var phone = (document.getElementById('sett-phone').value || '').trim();
    var oldpass = document.getElementById('sett-oldpass').value;
    var newpass = document.getElementById('sett-newpass').value;
    var newpass2 = document.getElementById('sett-newpass2').value;

    if (email && email !== email2) { settMsg('Email адреси не збігаються', 'err'); return; }
    if (newpass && newpass !== newpass2) { settMsg('Нові паролі не збігаються', 'err'); return; }
    if (newpass && newpass.length < 10) { settMsg('Новий пароль занадто короткий (мін. 10 символів)', 'err'); return; }

    var body = {};
    if (nick && _curData && nick !== _curData.nickname) body.nickname = nick;
    if (email && _curData && email !== _curData.email) { body.email = email; body.email_confirm = email2; }
    if (_curData && phone !== (_curData.phone || '')) body.phone = phone;
    if (newpass) { body.old_password = oldpass; body.password = newpass; }

    if (!Object.keys(body).length) { settMsg('Нічого не змінено', ''); return; }

    try {
      var r = await fetch('/api/auth/profile', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(body)
      });
      var d = await r.json();
      if (!r.ok || !d.ok) throw new Error(d.detail || 'Помилка збереження');
      // Оновити локальні дані
      if (d.user) {
        _curData.nickname = d.user.nickname || _curData.nickname;
        _curData.email = d.user.email || _curData.email;
        _curData.phone = d.user.phone || _curData.phone;
        // Якщо нік змінився — оновити URL без перезавантаження
        if (body.nickname && body.nickname !== location.pathname.split('/').pop()) {
          history.replaceState(null, '', '/user/' + body.nickname);
        }
      }
      // Очистити поля паролю
      document.getElementById('sett-oldpass').value = '';
      document.getElementById('sett-newpass').value = '';
      document.getElementById('sett-newpass2').value = '';
      settPassStrength('');
      settMsg('Збережено!', 'ok');
    } catch (e) {
      settMsg(e.message || 'Помилка збереження', 'err');
    }
  };

  function fillSettingsTab(d) {
    var fioEl = document.getElementById('sett-fio');
    if (fioEl) fioEl.textContent = d.fio || d.display_name || d.nickname;

    var nickEl = document.getElementById('sett-nick');
    if (nickEl) nickEl.value = d.nickname || '';
    var emailEl = document.getElementById('sett-email');
    if (emailEl) emailEl.value = d.email || '';
    var phoneEl = document.getElementById('sett-phone');
    if (phoneEl) phoneEl.value = d.phone || '';
    // Очистити поля
    ['sett-email2','sett-oldpass','sett-newpass','sett-newpass2'].forEach(function (id) {
      var el = document.getElementById(id); if (el) el.value = '';
    });
  }

  /* ── Перевірка доступності ніку/email (debounced) ── */
  var _availTimers = {};
  function _checkAvail(type, val, statusId, excludeCurrentVal) {
    var el = document.getElementById(statusId);
    if (!el) return;
    val = (val || '').trim();
    if (val.length < 2 || val === excludeCurrentVal) { el.textContent = ''; el.className = 'sett-field-hint'; return; }
    el.textContent = '…'; el.className = 'sett-field-hint';
    clearTimeout(_availTimers[statusId]);
    _availTimers[statusId] = setTimeout(function () {
      fetch('/api/auth/check-availability?type=' + type + '&value=' + encodeURIComponent(val), { credentials: 'include' })
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (d) {
          if (!d || d.available === null) { el.textContent = ''; el.className = 'sett-field-hint'; return; }
          if (d.available) { el.textContent = '✓ Вільний'; el.className = 'sett-field-hint ok'; }
          else { el.textContent = '✗ Вже зайнятий'; el.className = 'sett-field-hint err'; }
        })
        .catch(function () { el.textContent = ''; el.className = 'sett-field-hint'; });
    }, 600);
  }

  window.settCheckNickAvail = function (val) {
    _checkAvail('nick', val, 'sett-nick-avail', _curData && _curData.nickname);
  };

  window.settCheckEmailAvail = function (val) {
    _checkAvail('email', val, 'sett-email-avail', _curData && _curData.email);
  };

  window.settCheckEmail2 = function (val) {
    var el = document.getElementById('hint-sett-email2');
    if (!el) return;
    var ref = (document.getElementById('sett-email') || {}).value || '';
    if (!val) { el.textContent = ''; el.className = 'sett-field-hint'; return; }
    if (val === ref) { el.textContent = '✓ Збігаються'; el.className = 'sett-field-hint ok'; }
    else { el.textContent = '✗ Не збігаються'; el.className = 'sett-field-hint err'; }
  };

  window.settCheckPhone = function (el) {
    var hint = document.getElementById('hint-sett-phone');
    if (!hint) return;
    var raw = el.value;
    var digits = raw.replace(/\D/g, '');
    if (!raw) { hint.textContent = 'Лише українські номери (+380)'; hint.className = 'sett-field-hint'; return; }
    var ok = /^(\+?380|0)\d{9}$/.test(digits.length === 12 ? '+' + digits : raw.replace(/\s/g,''));
    if (ok) { hint.textContent = '✓ Вірний формат'; hint.className = 'sett-field-hint ok'; }
    else { hint.textContent = 'Формат: 0671234567 або +380671234567'; hint.className = 'sett-field-hint err'; }
  };

  /* ── Legacy tab logic ── */

  var _legacyData = null; // статус модуля

  function legacyMsg(id, text, type) {
    var el = document.getElementById(id);
    if (!el) return;
    el.textContent = text;
    el.className = 'sett-save-msg ' + (type || '');
    if (type === 'ok') setTimeout(function () { el.textContent = ''; el.className = 'sett-save-msg'; }, 3500);
  }

  window.legacyPhotoPreview = function (url) {
    var box = document.getElementById('legacy-photo-preview');
    if (!box) return;
    if (!url) { box.innerHTML = ''; return; }
    box.innerHTML = '<img src="' + escH(url) + '" onerror="this.style.display=\'none\'">';
  };

  window.legacyCount = function (el, counterId, max) {
    var cnt = document.getElementById(counterId);
    if (cnt) cnt.textContent = el.value.length + '/' + max;
  };

  function fillLegacyContent(c) {
    var setV = function (id, v) { var el = document.getElementById(id); if (el) el.value = v || ''; };
    var setCb = function (id, v) { var el = document.getElementById(id); if (el) el.checked = !!v; };
    setV('legacy-photo', c.memory_photo);
    legacyPhotoPreview(c.memory_photo || '');
    setV('legacy-epitaph', c.epitaph);
    var ec = document.getElementById('legacy-epitaph');
    if (ec) legacyCount(ec, 'legacy-epitaph-cnt', 300);
    setV('legacy-bio', c.biography);
    setV('legacy-final', c.final_message);
    setV('legacy-video', c.video_url);
    setV('legacy-wishes', c.wishes);
    setV('legacy-advice', c.family_advice);
    setV('legacy-achieve', c.achievements);
    setV('legacy-instr', c.instructions);
    setCb('leg-pub-all',    c.publish_all);
    setCb('leg-bio-edit',   c.allow_bio_edit);
    setCb('leg-memories',   c.allow_memories);
    setCb('leg-photos',     c.allow_new_photos);
    setCb('leg-lock-after', c.lock_after_memorial);
    // will lock status
    var wStatus = document.getElementById('legacy-will-status');
    var wForm   = document.getElementById('legacy-will-form');
    var wUnlock = document.getElementById('legacy-unlock-form');
    if (c.will_locked) {
      var dt = c.will_locked_at ? new Date(c.will_locked_at * 1000).toLocaleDateString('uk-UA') : '';
      if (wStatus) wStatus.innerHTML =
        '<div class="legacy-will-locked-info">&#128274; Воля зафіксована' + (dt ? ' — ' + dt : '') + '</div>';
      if (wForm)   wForm.style.display = 'none';
      if (wUnlock) wUnlock.style.display = 'block';
    } else {
      if (wStatus) wStatus.textContent = '';
      if (wForm)   wForm.style.display = 'block';
      if (wUnlock) wUnlock.style.display = 'none';
    }
  }

  function initLegacyTab(status) {
    _legacyData = status;
    var inactive     = document.getElementById('legacy-inactive');
    var activeBlock  = document.getElementById('legacy-active-content');
    var inviteBanner = document.getElementById('legacy-invite-banner');
    var deathCard    = document.getElementById('legacy-death-card');

    // Модуль вимкнено адміністратором — не показувати вкладку взагалі
    if (!status.enabled) {
      if (activeBlock) activeBlock.style.display = 'none';
      return;
    }

    // Модуль увімкнено — показуємо кнопки вкладки
    var navLeg = document.getElementById('nav-legacy');
    var xtLeg  = document.getElementById('xtab-legacy');
    if (navLeg) navLeg.style.display = 'flex';
    if (xtLeg)  xtLeg.style.display  = 'block';

    // Запрошення стати довіреною особою (для поточного юзера як trusted)
    if (status.pending_invite) {
      var inv = status.pending_invite;
      var ownerName = [inv.first_name, inv.last_name].filter(Boolean).join(' ') || '@' + inv.owner_nick;
      var desc = document.getElementById('legacy-invite-desc');
      if (desc) desc.textContent = ownerName + ' запрошує вас стати своєю довіреною особою в системі «Спадщина пам\'яті».';
      if (inviteBanner) inviteBanner.style.display = 'block';
    }

    // Форма завжди доступна — показуємо активний вміст
    if (inactive) inactive.style.display = 'none';
    if (activeBlock) activeBlock.style.display = 'block';

    // Блок статусу публікації (оплати)
    renderLegacyPayStatus(status);

    // Блок довіреної особи
    loadLegacyTrusted();

    // Контент
    fetch('/api/legacy/content', { credentials: 'include' })
      .then(function (r) { return r.json(); })
      .then(fillLegacyContent)
      .catch(function () {});

    // Кнопка "Повідомити про смерть" — якщо поточний юзер є підтвердженою довіреною особою
    if (deathCard && status.is_trusted_confirmed) {
      deathCard.style.display = 'block';
    }
  }

  function renderLegacyPayStatus(status) {
    var el = document.getElementById('legacy-pay-status');
    if (!el) return;
    if (status.published) {
      el.innerHTML = '<div class="legacy-pay-active">&#10003; Публікацію активовано — меморіальна картка буде опублікована після підтвердження</div>';
    } else {
      var price = (status.price || '82') + ' ' + (status.currency || 'USD');
      el.innerHTML =
        '<div class="legacy-pay-pending">' +
          '<div class="legacy-pay-title">Публікацію не оплачено</div>' +
          '<div class="legacy-pay-desc">Заповніть і збережіть спадок, а потім активуйте публікацію меморіальної картки за ' + escH(price) + '.</div>' +
          '<button class="sett-save-btn legacy-buy-btn" onclick="legacyActivate()" style="max-width:260px;margin-top:10px">Активувати публікацію — ' + escH(price) + '</button>' +
          '<div class="sett-save-msg" id="legacy-buy-msg"></div>' +
        '</div>';
    }
  }

  function loadLegacyTrusted() {
    var info = document.getElementById('legacy-trusted-info');
    if (!info) return;
    fetch('/api/legacy/trusted', { credentials: 'include' })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (!d || !d.trusted_user_id) {
          info.innerHTML =
            '<span style="color:var(--muted)">Довірену особу не призначено</span>' +
            ' <button class="btn-legacy-confirm" style="margin-left:8px" onclick="legacyShowTrustedForm()">' +
            'Призначити</button>';
        } else {
          var statusMap = { pending: 'Очікує підтвердження', confirmed: 'Підтверджено', rejected: 'Відхилено' };
          var sColor = d.status === 'confirmed' ? '#4a9e6a' : d.status === 'rejected' ? 'var(--r)' : '#c8a020';
          info.innerHTML =
            '<div>Довірена особа: <strong>@' + escH(d.nickname) + '</strong>' +
            ' — <span style="color:' + sColor + '">' + (statusMap[d.status] || d.status) + '</span></div>' +
            '<button class="btn-legacy-reject" style="margin-top:8px;font-size:.8rem" onclick="legacyRemoveTrusted()">Відкликати</button>' +
            ' <button class="btn-legacy-confirm" style="margin-top:8px;font-size:.8rem;margin-left:6px" onclick="legacyShowTrustedForm()">Змінити</button>';
        }
      })
      .catch(function () {
        info.textContent = 'Помилка завантаження';
      });
  }

  window.legacyShowTrustedForm = function () {
    var f = document.getElementById('legacy-trusted-form');
    if (f) f.style.display = 'flex';
  };

  window.legacySetTrusted = async function () {
    var nick = (document.getElementById('legacy-trusted-nick').value || '').trim();
    if (!nick) { legacyMsg('legacy-trusted-msg', 'Вкажіть нікнейм', 'err'); return; }
    try {
      var r = await fetch('/api/legacy/trusted', {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nickname: nick })
      });
      var d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Помилка');
      legacyMsg('legacy-trusted-msg', 'Запрошення надіслано!', 'ok');
      document.getElementById('legacy-trusted-form').style.display = 'none';
      document.getElementById('legacy-trusted-nick').value = '';
      loadLegacyTrusted();
    } catch (e) {
      legacyMsg('legacy-trusted-msg', e.message, 'err');
    }
  };

  window.legacyRemoveTrusted = async function () {
    if (!confirm('Відкликати довірену особу?')) return;
    try {
      var r = await fetch('/api/legacy/trusted', { method: 'DELETE', credentials: 'include' });
      var d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Помилка');
      loadLegacyTrusted();
    } catch (e) {
      legacyMsg('legacy-trusted-msg', e.message, 'err');
    }
  };

  window.legacyRespondInvite = async function (action) {
    try {
      var r = await fetch('/api/legacy/trusted/respond', {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: action })
      });
      var d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Помилка');
      var banner = document.getElementById('legacy-invite-banner');
      if (banner) banner.style.display = 'none';
      legacyMsg('legacy-invite-msg',
        action === 'confirm' ? 'Ви підтвердили запрошення!' : 'Запрошення відхилено', 'ok');
      // Якщо підтвердили — показати кнопку повідомити про смерть
      if (action === 'confirm') {
        var dc = document.getElementById('legacy-death-card');
        if (dc) dc.style.display = 'block';
      }
    } catch (e) {
      legacyMsg('legacy-invite-msg', e.message, 'err');
    }
  };

  window.legacySaveContent = async function () {
    var gv = function (id) { var el = document.getElementById(id); return el ? el.value : ''; };
    var gc = function (id) { var el = document.getElementById(id); return el ? (el.checked ? 1 : 0) : 0; };
    var btn = document.getElementById('legacy-save-btn');
    if (btn) btn.disabled = true;
    try {
      var body = {
        memory_photo:        gv('legacy-photo'),
        epitaph:             gv('legacy-epitaph'),
        biography:           gv('legacy-bio'),
        final_message:       gv('legacy-final'),
        video_url:           gv('legacy-video'),
        wishes:              gv('legacy-wishes'),
        family_advice:       gv('legacy-advice'),
        achievements:        gv('legacy-achieve'),
        instructions:        gv('legacy-instr'),
        publish_all:         gc('leg-pub-all'),
        allow_bio_edit:      gc('leg-bio-edit'),
        allow_memories:      gc('leg-memories'),
        allow_new_photos:    gc('leg-photos'),
        lock_after_memorial: gc('leg-lock-after'),
      };
      var r = await fetch('/api/legacy/content', {
        method: 'PUT', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      var d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Помилка збереження');
      legacyMsg('legacy-save-msg', 'Збережено!', 'ok');
    } catch (e) {
      legacyMsg('legacy-save-msg', e.message, 'err');
    } finally {
      if (btn) btn.disabled = false;
    }
  };

  window.legacyLockWill = async function (unlock) {
    var passId = unlock ? 'legacy-unlock-pass' : 'legacy-will-pass';
    var pass = (document.getElementById(passId) || {}).value || '';
    if (!pass) { legacyMsg('legacy-will-msg', 'Введіть пароль', 'err'); return; }
    try {
      var url = unlock ? '/api/legacy/unlock-will' : '/api/legacy/lock-will';
      var r = await fetch(url, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password: pass })
      });
      var d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Помилка');
      document.getElementById(passId).value = '';
      // Оновити стан
      var wForm   = document.getElementById('legacy-will-form');
      var wUnlock = document.getElementById('legacy-unlock-form');
      var wStatus = document.getElementById('legacy-will-status');
      if (unlock) {
        if (wStatus) wStatus.innerHTML = '';
        if (wForm)   wForm.style.display = 'block';
        if (wUnlock) wUnlock.style.display = 'none';
        legacyMsg('legacy-will-msg', 'Розблоковано', 'ok');
      } else {
        var now = new Date().toLocaleDateString('uk-UA');
        if (wStatus) wStatus.innerHTML =
          '<div class="legacy-will-locked-info">&#128274; Воля зафіксована — ' + now + '</div>';
        if (wForm)   wForm.style.display = 'none';
        if (wUnlock) wUnlock.style.display = 'block';
        legacyMsg('legacy-will-msg', 'Волю зафіксовано', 'ok');
      }
    } catch (e) {
      legacyMsg('legacy-will-msg', e.message, 'err');
    }
  };

  window.legacyActivate = async function () {
    legacyMsg('legacy-buy-msg', 'Зверніться до адміністратора для активації модуля.', '');
  };

  window.legacyReportDeath = async function () {
    var date    = (document.getElementById('legacy-death-date') || {}).value || '';
    var comment = (document.getElementById('legacy-death-comment') || {}).value || '';
    if (!date) { legacyMsg('legacy-death-msg', 'Вкажіть дату відходу', 'err'); return; }
    try {
      var r = await fetch('/api/legacy/report-death', {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ death_date: date, comment: comment })
      });
      var d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Помилка');
      legacyMsg('legacy-death-msg', 'Заявку подано. Модератор розгляне її найближчим часом.', 'ok');
      document.getElementById('legacy-death-date').value = '';
      document.getElementById('legacy-death-comment').value = '';
    } catch (e) {
      legacyMsg('legacy-death-msg', e.message, 'err');
    }
  };

  function loadLegacyStatus() {
    fetch('/api/legacy/status', { credentials: 'include' })
      .then(function (r) { return (r.ok && r.status !== 401) ? r.json() : null; })
      .then(function (s) { if (s) initLegacyTab(s); })
      .catch(function () {});
  }

  function fillProfile(d) {
    _curData = d;
    document.title = (d.display_name || '@' + d.nickname) + ' — Зоряна Памʼять';

    var initials = (d.display_name || d.nickname || '?')
      .split(' ').slice(0, 2).map(function (w) { return w[0] || ''; }).join('').toUpperCase() || '?';
    document.getElementById('prof-avatar').textContent = initials;
    document.getElementById('prof-name').textContent = d.display_name || d.nickname;
    document.getElementById('prof-nick').textContent = '@' + d.nickname;

    // Role badge — показувати для admin/moder
    var roleEl = document.getElementById('prof-role');
    var roleMap = { admin: 'Адмін', moder: 'Модератор' };
    if (d.role && roleMap[d.role]) {
      roleEl.textContent = roleMap[d.role];
      roleEl.className = 'role-tag ' + d.role;
      roleEl.style.display = 'inline-block';
    }

    // Дата реєстрації
    if (d.created) {
      var dt = new Date(d.created * 1000);
      var months = ['січня','лютого','березня','квітня','травня','червня',
                    'липня','серпня','вересня','жовтня','листопада','грудня'];
      var sinceEl = document.getElementById('prof-since');
      if (sinceEl) sinceEl.textContent = 'з ' + dt.getDate() + ' ' + months[dt.getMonth()] + ' ' + dt.getFullYear();
      var sinceRow = document.getElementById('prof-since-row');
      if (sinceRow) sinceRow.style.display = 'flex';
    }

    var mems = d.memorials || [];
    var totalLikes = mems.reduce(function (s, m) { return s + (m.likes || 0); }, 0);
    var daysSince = d.created ? Math.floor((Date.now() / 1000 - d.created) / 86400) : 0;

    document.getElementById('stat-memorials').textContent = fmtNum(d.count || 0);
    document.getElementById('stat-likes').textContent = fmtNum(totalLikes);
    document.getElementById('stat-days').textContent = fmtNum(daysSince);

    var grid = document.getElementById('mem-grid');
    var lbl  = document.getElementById('sec-label-count');
    if (!mems.length) {
      lbl.textContent = '';
      grid.innerHTML = '<div class="empty-state"><div class="empty-star"></div>Меморіалів ще немає</div>';
    } else {
      var cnt = d.count || 0;
      lbl.textContent = cnt + ' ' + plural(cnt, 'меморіал', 'меморіали', 'меморіалів');
      grid.innerHTML = mems.map(cardHTML).join('');
    }

    document.getElementById('info-section').innerHTML = buildInfoTab(d);

    // Показати кнопки Settings (профіль завжди власний)
    var navSett = document.getElementById('nav-settings');
    var xtSett  = document.getElementById('xtab-settings');
    if (navSett) navSett.style.display = 'flex';
    if (xtSett)  xtSett.style.display  = 'block';
    // Legacy-кнопки показуються тільки з initLegacyTab (якщо модуль увімкнено)

    fillSettingsTab(d);
    loadLegacyStatus();

    document.getElementById('loading-screen').style.display = 'none';
    document.getElementById('page-content').style.display = 'block';

    // Встановлюємо curUser для чату (авторизований юзер)
    window.curUser = { nickname: d.nickname, role: d.role || 'user', name: d.display_name };

    // Ініціалізуємо чат після показу сторінки
    if (typeof _mcInit === 'function') _mcInit();
  }

  // Init
  (function init() {
    var nick = location.pathname.split('/').filter(Boolean).pop() || '';
    if (!nick) { showError('Нікнейм не вказано', false); return; }

    fetch('/api/user/' + encodeURIComponent(nick), { credentials: 'include' })
      .then(function (r) {
        if (r.status === 401) throw new Error('auth');
        if (r.status === 403) throw new Error('forbidden');
        if (r.status === 404) throw new Error('not_found');
        if (!r.ok) throw new Error('server_error');
        return r.json();
      })
      .then(fillProfile)
      .catch(function (e) {
        if (e.message === 'auth' || e.message === 'forbidden') {
          showError('Це приватний профіль. Увійдіть у свій акаунт.', true);
        } else if (e.message === 'not_found') {
          showError('Такого користувача не існує або його заблоковано.', false);
        } else {
          showError('Помилка завантаження. Спробуйте пізніше.', false);
        }
      });
  })();

})();
