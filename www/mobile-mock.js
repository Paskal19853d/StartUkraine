/* ═══════════════════════════════════════════════════════════════
   mobile-mock.js — ДЕМО-ДАНІ ДЛЯ ПРЕВ'Ю
   Перехоплює fetch ЛИШЕ для /api/* і повертає демо-відповідь ТІЛЬКИ
   коли справжній бекенд недоступний (немає JSON-відповіді).
   На проді з робочим /api цей шар неактивний. Можна видалити перед деплоєм.
   ═══════════════════════════════════════════════════════════════ */
(function(){
  'use strict';
  const _fetch = window.fetch ? window.fetch.bind(window) : null;

  const CITIES = [
    ['Київ',0.62,0.34,1],['Львів',0.12,0.42,1],['Харків',0.83,0.40,1],
    ['Одеса',0.50,0.79,1],['Дніпро',0.72,0.55,1],['Запоріжжя',0.74,0.63,2],
    ['Вінниця',0.42,0.50,2],['Полтава',0.70,0.45,2],['Чернігів',0.62,0.21,2],
    ['Суми',0.76,0.28,2],['Житомир',0.45,0.36,2],['Миколаїв',0.55,0.70,2],
    ['Херсон',0.58,0.75,2],['Луцьк',0.22,0.29,2],['Тернопіль',0.25,0.46,2],
    ['Івано-Франківськ',0.18,0.52,2],['Ужгород',0.05,0.55,2],['Чернівці',0.30,0.58,2],
    ['Рівне',0.30,0.32,2],['Кропивницький',0.58,0.57,2]
  ].map((c,i)=>({id:i+1,name:c[0],pos_x:c[1],pos_y:c[2],tier:c[3],color:'#a0d7ff'}));

  const FN=['Олег','Андрій','Віктор','Тарас','Сергій','Дмитро','Іван','Богдан','Роман','Юрій','Максим','Василь','Артем','Микола','Павло','Денис'];
  const LN=['Шевченко','Коваленко','Бондаренко','Ткаченко','Мельник','Кравчук','Поліщук','Савченко','Левченко','Морозенко','Гончар','Зінченко','Литвин','Марченко','Руденко','Сидоренко'];
  const MN=['Миколайович','Петрович','Іванович','Васильович','Олександрович','Сергійович','Андрійович','Тарасович'];
  const RANKS=['Солдат','Старший солдат','Сержант','Старший сержант','Лейтенант','Старший лейтенант','Капітан','Майор'];
  const COLORS=['#4fc3f7','#ffd54f','#ef9a9a','#a5d6a7','#ce93d8','#c8b060','#ff8a65','#80cbc4'];
  const UNITS=['3-тя ОШБр','93-тя ОМБр «Холодний Яр»','25-та ОПДБр','79-та ОДШБр','Азов','ДУК'];
  const CIRC=['Артилерія','Міна','Ракетний удар','Шахед','Прямий контакт','Снайпер','Авіабомба'];

  function rnd(a){ return a[Math.floor(Math.random()*a.length)]; }
  const PEOPLE = [];
  let seed = 7;
  function rng(){ seed=(seed*1103515245+12345)&0x7fffffff; return seed/0x7fffffff; }
  for(let i=0;i<40;i++){
    const city = CITIES[Math.floor(rng()*CITIES.length)];
    const x = Math.min(0.95, Math.max(0.05, city.pos_x + (rng()-0.5)*0.10));
    const y = Math.min(0.92, Math.max(0.15, city.pos_y + (rng()-0.5)*0.10));
    const by = 1975 + Math.floor(rng()*30);
    PEOPLE.push({
      id: 1000+i,
      last: rnd(LN), first: rnd(FN), mid: rnd(MN),
      birth: by+'-0'+(1+Math.floor(rng()*8))+'-1'+Math.floor(rng()*9),
      death: '202'+(2+Math.floor(rng()*4))+'-0'+(1+Math.floor(rng()*8))+'-0'+(1+Math.floor(rng()*8)),
      loc: city.name+', напрямок', bury: city.name,
      circ: rnd(CIRC), descr: 'Вірний присязі, до останнього боронив рідну землю. Вічна памʼять Герою.',
      photo:'', video_url:'',
      color: COLORS[i%COLORS.length],
      pos_x:x, pos_y:y,
      likes: Math.floor(rng()*900), rating: rng()*8,
      grp: rng()>0.6 ? '«'+rnd(['Сокіл','Вовк','Граніт','Тінь','Беркут']) +'»': '',
      rank: rnd(RANKS), unit: rnd(UNITS), position:'Стрілець',
      added_by:'demo', slug:'demo-'+(1000+i)
    });
  }

  const COLORS_CFG = {
    bg:'#03070e', accent:'#00c8ff', neon_blue:'#00ccff', neon_yellow:'#d4a800',
    oblast_fill:'#040f1e', zoom_min:'0.4', zoom_max:'12',
    smoke_enabled:'1', sea_enabled:'1', mobile_enabled:'1',
    icon_logo:'★', icon_likes:'⭐', icon_people:'👥',
    social_facebook:'1', social_facebook_url:'https://facebook.com',
    social_telegram:'1', social_telegram_url:'https://t.me',
    social_youtube:'1', social_youtube_url:'https://youtube.com',
    social_instagram:'1', social_instagram_url:'https://instagram.com',
    social_order:'facebook,telegram,youtube,instagram'
  };

  function jsonResp(obj){
    return new Response(JSON.stringify(obj), {status:200, headers:{'Content-Type':'application/json'}});
  }

  function mock(url, opts){
    const u = url.split('?')[0];
    const q = (url.split('?')[1]||'');
    const method = (opts && opts.method ? opts.method : 'GET').toUpperCase();

    if(u.endsWith('/api/colors'))  return COLORS_CFG;
    if(u.endsWith('/api/stats'))   return {total:128, likes:14142, online:1};
    if(u.endsWith('/api/cities'))  return CITIES;
    if(u.endsWith('/api/labels'))  return [];
    if(u.includes('/api/people') && method==='GET') return {items:PEOPLE, page:1, pages:1, total:PEOPLE.length};
    if(u.includes('/api/people') && method==='POST') return {ok:true, message:'Демо-режим: запис надіслано на модерацію'};
    if(u.includes('/api/awards/catalog')) return [];
    let m;
    if((m=u.match(/\/api\/memorial\/([^\/]+)\/awards/))) return [];
    if((m=u.match(/\/api\/memorial\/by-slug\/(.+)/))){
      const p = PEOPLE.find(p=>p.slug===decodeURIComponent(m[1])) || PEOPLE[0]; return p;
    }
    if((m=u.match(/\/api\/memorial\/(\d+)/))){
      const p = PEOPLE.find(p=>String(p.id)===m[1]) || PEOPLE[0]; return p;
    }
    if(u.includes('/api/search')){
      const term = decodeURIComponent((q.match(/q=([^&]*)/)||[])[1]||'').toLowerCase();
      const res = PEOPLE.filter(p=>(p.last+' '+p.first+' '+p.loc+' '+(p.grp||'')).toLowerCase().includes(term)).slice(0,20);
      return res;
    }
    if(u.includes('/api/like/')) return {ok:true};
    if(u.includes('/api/auth/me')) return {ok:false};
    if(u.includes('/api/auth/check-availability')) return {available:true};
    if(u.includes('/api/auth/login'))  return {ok:false, detail:'Демо-режим: вхід доступний лише на сервері'};
    if(u.includes('/api/auth/register')) return {ok:false, detail:'Демо-режим: реєстрація доступна лише на сервері'};
    if(u.includes('/api/auth/send-code')) return {ok:false, detail:'Демо-режим'};
    if(u.includes('/api/auth/')) return {ok:false};
    if(u.includes('/api/online/ping')) return {ok:true, online:1};
    if(u.includes('/api/partners')) return [];
    if(u.includes('/api/yt-check')) return {ok:false};
    return undefined; // не наш endpoint
  }

  window.fetch = async function(url, opts){
    const us = (typeof url === 'string') ? url : (url && url.url) || '';
    const isApi = us.indexOf('/api/') !== -1;
    if(!isApi || !_fetch){
      if(!_fetch) throw new Error('no fetch');
      return _fetch(url, opts);
    }
    // 1) пробуємо справжній бекенд
    try{
      const r = await _fetch(url, opts);
      const ct = (r.headers.get('content-type')||'').toLowerCase();
      if(r.ok && ct.includes('application/json')) return r;       // справжній API → використовуємо
      // 401/403 з JSON (напр. auth/me) — теж справжня відповідь
      if(ct.includes('application/json')) return r;
      throw new Error('non-json');
    }catch(e){
      const data = mock(us, opts);
      if(data !== undefined){
        if(!window.__MOCK_NOTE){ window.__MOCK_NOTE = true; console.info('[Зоряна] Демо-режим: бекенд недоступний, показано тестові дані.'); }
        return jsonResp(data);
      }
      throw e;
    }
  };
})();
