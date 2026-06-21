/* ═══════════════════════════════════════════════════════════════
   Зоряна Памʼять — mobile.js
   Оболонка мобільної версії: переносить елементи десктопного UI
   у мобільні контейнери та керує листами/шторкою.
   Завантажується ОСТАННІМ — увесь DOM і функції рушія вже доступні.
   ═══════════════════════════════════════════════════════════════ */
(function(){
  'use strict';
  const $ = (id)=>document.getElementById(id);
  const move = (el, host)=>{ if(el && host) host.appendChild(el); };

  /* ── 1. Переносимо елементи десктопного UI у мобільні контейнери ── */
  move($('sw'),         $('m-search-host'));
  move($('smoke-ctrl'), $('m-smoke-host'));
  move($('site-rules'), $('m-info-host'));
  move($('social-bar'), $('m-social-host'));
  move($('btn-coffee'), $('m-coffee-host'));

  // Статистика (3 .tstat) → у шторку
  const statsHost = $('m-stats-host');
  document.querySelectorAll('#topbar .tstat, .tstat').forEach(t=>{
    if(t.closest('#m-stats-host')) return;
    statsHost && statsHost.appendChild(t);
  });

  /* ── 2. Картка акаунта (логін / профіль / вихід) ── */
  function curUserSafe(){ try{ return window.curUser; }catch(e){ return null; } }
  function renderAccount(){
    const host = $('m-acc'); if(!host) return;
    const u = curUserSafe();
    if(u){
      const nick = u.nickname ? ('@'+u.nickname) : '';
      const name = u.name || u.first_name || 'Користувач';
      host.innerHTML =
        '<div class="m-acc-card">'+
          '<div class="m-acc-name">'+escapeHtml(name)+'</div>'+
          (nick ? '<div class="m-acc-sub">'+escapeHtml(nick)+'</div>' : '<div class="m-acc-sub">У мережі</div>')+
          '<div class="m-acc-btns">'+
            '<div class="m-btn m-btn-primary" data-mact="profile">Профіль</div>'+
            '<div class="m-btn m-btn-ghost" data-mact="logout">Вийти</div>'+
          '</div>'+
        '</div>';
    } else {
      host.innerHTML =
        '<div class="m-acc-card">'+
          '<div class="m-acc-name">Вітаємо!</div>'+
          '<div class="m-acc-sub">Увійдіть, щоб ставити зірки памʼяті та додавати записи.</div>'+
          '<div class="m-acc-btns">'+
            '<div class="m-btn m-btn-primary" data-mact="auth">Увійти / Реєстрація</div>'+
          '</div>'+
        '</div>';
    }
  }
  function escapeHtml(s){ const d=document.createElement('div'); d.textContent=s==null?'':String(s); return d.innerHTML; }

  // Делегування кнопок картки акаунта
  const acc = $('m-acc');
  acc && acc.addEventListener('click', e=>{
    const b = e.target.closest('[data-mact]'); if(!b) return;
    const act = b.dataset.mact;
    closeDrawer();
    if(act==='profile' && window.openProfile) openProfile();
    else if(act==='logout' && window.doLogout) doLogout();
    else if(act==='auth' && window.openAuth) openAuth();
  });

  // Обгортаємо updateAuthUI, щоб синхронізувати картку акаунта
  if(typeof window.updateAuthUI === 'function'){
    const _orig = window.updateAuthUI;
    window.updateAuthUI = function(){ try{ _orig.apply(this, arguments); }catch(e){} renderAccount(); };
  }
  renderAccount();

  /* ── 3. Пошуковий лист ── */
  const searchSheet = $('m-search-sheet');
  function openSearch(){
    if(!searchSheet) return;
    closeDrawer();
    searchSheet.classList.add('open');
    setActiveNav('search');
    const si = $('search');
    if(si){ setTimeout(()=>{ si.focus(); }, 320); }
  }
  function closeSearch(){
    if(!searchSheet) return;
    searchSheet.classList.remove('open');
    const si = $('search'); if(si) si.blur();
    if(window.closeDrop) try{ closeDrop(); }catch(e){}
    setActiveNav('map');
  }
  $('m-search-open') && $('m-search-open').addEventListener('click', openSearch);
  $('m-search-cancel') && $('m-search-cancel').addEventListener('click', closeSearch);
  // Тап по результату → закрити лист (даємо оригінальному обробнику відпрацювати)
  const sdrop = $('sdrop');
  sdrop && sdrop.addEventListener('click', e=>{
    if(e.target.closest('.sdi') && !e.target.closest('.sdi-empty') && !e.target.closest('.sdi-loader')){
      setTimeout(closeSearch, 30);
    }
  });

  /* ── 4. Шторка меню ── */
  const drawer = $('m-drawer'), scrim = $('m-drawer-scrim');
  function openDrawer(){ if(drawer){ drawer.classList.add('open'); scrim.classList.add('open'); renderAccount(); } }
  function closeDrawer(){ if(drawer){ drawer.classList.remove('open'); scrim.classList.remove('open'); } }
  $('m-menu-open') && $('m-menu-open').addEventListener('click', openDrawer);
  $('m-drawer-close') && $('m-drawer-close').addEventListener('click', closeDrawer);
  scrim && scrim.addEventListener('click', closeDrawer);

  /* ── 5. Нижня навігація ── */
  function setActiveNav(act){
    document.querySelectorAll('#m-bottomnav .m-nav-item').forEach(it=>{
      it.classList.toggle('is-active', it.dataset.act===act);
    });
  }
  document.querySelectorAll('#m-bottomnav .m-nav-item').forEach(it=>{
    it.addEventListener('click', ()=>{
      const act = it.dataset.act;
      if(act==='map'){ closeSearch(); closeDrawer(); setActiveNav('map'); }
      else if(act==='search'){ openSearch(); }
      else if(act==='add'){ closeSearch(); closeDrawer(); window.onAdd && onAdd(); }
      else if(act==='profile'){ closeSearch(); closeDrawer(); (curUserSafe()? (window.openProfile&&openProfile()) : (window.openAuth&&openAuth())); }
      else if(act==='menu'){ closeSearch(); openDrawer(); }
    });
  });

  /* ── 6. Картка-лист: свайп вниз по фото для закриття ── */
  const card = $('card'), cphoto = $('cphoto');
  if(card && cphoto){
    let sy=0, dy=0, dragging=false;
    cphoto.addEventListener('touchstart', e=>{ sy=e.touches[0].clientY; dy=0; dragging=true; }, {passive:true});
    cphoto.addEventListener('touchmove', e=>{
      if(!dragging) return;
      dy = e.touches[0].clientY - sy;
      if(dy>0){ card.style.transform='translateY('+dy+'px)'; }
    }, {passive:true});
    cphoto.addEventListener('touchend', ()=>{
      dragging=false; card.style.transform='';
      if(dy>90 && window.closeCard) closeCard();
    });
  }

  /* ── 7. Мобільний чат: FAB + повноекранна панель ── */
  (function initMobileChat() {
    var fab   = document.getElementById('m-chat-fab');
    var panel = document.getElementById('m-chat-panel');
    var close = document.getElementById('m-chat-panel-close');
    var badge = document.getElementById('m-chat-fab-badge');
    if (!fab || !panel) { console.warn('m-chat-fab or m-chat-panel not found'); return; }

    // FAB показується з INIT блоку mobile.html після _mcInit()

    // Відкрити панель
    function openPanel() {
      panel.classList.add('open');
      var msgs = document.getElementById('mc-messages');
      if (msgs) setTimeout(function(){ msgs.scrollTop = msgs.scrollHeight; }, 60);
      var inp = document.getElementById('mc-input');
      if (inp) setTimeout(function(){ inp.focus(); }, 120);
      if (badge) { badge.style.display = 'none'; badge.textContent = ''; }
      _unread = 0;
    }

    // Закрити панель
    function closePanel() {
      panel.classList.remove('open');
      var inp = document.getElementById('mc-input');
      if (inp) inp.blur();
    }

    var scrollTop = document.getElementById('m-chat-scroll-top');
    var scrollBot = document.getElementById('m-chat-scroll-bot');

    fab.addEventListener('click', openPanel);
    if (close) close.addEventListener('click', closePanel);
    if (scrollTop) scrollTop.addEventListener('click', function() {
      var msgs = document.getElementById('mc-messages');
      if (msgs) msgs.scrollTo({ top: 0, behavior: 'smooth' });
    });
    if (scrollBot) scrollBot.addEventListener('click', function() {
      var msgs = document.getElementById('mc-messages');
      if (msgs) msgs.scrollTo({ top: msgs.scrollHeight, behavior: 'smooth' });
    });

    // Закрити свайпом вниз
    var _sy = 0;
    panel.addEventListener('touchstart', function(e) {
      if (e.target.closest('#mc-messages') || e.target.closest('#mc-input-row')) return;
      _sy = e.touches[0].clientY;
    }, { passive: true });
    panel.addEventListener('touchend', function(e) {
      if (e.target.closest('#mc-messages') || e.target.closest('#mc-input-row')) return;
      if (e.changedTouches[0].clientY - _sy > 60) closePanel();
    }, { passive: true });

    // Лічильник непрочитаних — коли панель закрита
    var _unread = 0;
    var _origAppend = window._mcAppend;
    // Перехоплюємо нові повідомлення через MutationObserver на #mc-messages
    var msgs = document.getElementById('mc-messages');
    if (msgs) {
      var obs = new MutationObserver(function() {
        if (!panel.classList.contains('open')) {
          _unread++;
          if (badge) {
            badge.textContent = _unread > 9 ? '9+' : _unread;
            badge.style.display = '';
          }
        }
      });
      obs.observe(msgs, { childList: true });
    }
  })();

  /* ── 9. Карта світу: кнопки перемикача закривають drawer ── */
  const modeBar = $('map-mode-bar');
  if (modeBar) {
    modeBar.addEventListener('click', e => {
      const btn = e.target.closest('.map-mode-btn');
      if (btn) { closeDrawer(); setActiveNav('map'); }
    });
  }

  /* ── 8. Підстраховка: вимикаємо десктопні блокувальники ── */
  ['rotate-overlay','too-small-overlay','mobile-blocked'].forEach(id=>{
    const el=$(id); if(el) el.style.display='none';
  });

  /* ── 10. Закривати лист пошуку клавішею Esc/назад не потрібно — нативно ── */
  window.addEventListener('popstate', ()=>{ /* openCard вже керує history */ });

  // Початковий стан навігації
  setActiveNav('map');
})();
