/*
Привиди в диму — ізольований Canvas2D-модуль поверх існуючого WebGL fluid-диму
(js/script.js). Малює 1-6 SVG-силуетів (завантажуються адміном окремо), які
в звичайному стані практично невидимі і проявляються лише там і тоді, де дим
реально присутній і активний (наближення курсора + недавній mousemove +
window._fluidConfig.PAUSED===false).

Ізоляція: власний <canvas id="ghost-layer">, власний rAF-цикл, власні
mousemove/resize слухачі. Єдині точки читання з існуючої системи диму —
window._fluidConfig.PAUSED та window._fluidConfig.SPLAT_RADIUS (read-only,
нічого не пишеться назад і не викликається з js/script.js).

Публічний контракт: window.applyGhostConfig() і window._ghostSyncState() —
викликаються ззовні (index.html/mobile.html) поруч з applySmokeConfig()/
_applySmokeState(), за тим самим guard-патерном (може викликатись до того як
конфіг ще завантажений з БД — тоді просто чекає наступного виклику).
*/

"use strict";

(function () {
  const canvas = document.getElementById("ghost-layer");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");

  function isMobileGhost() {
    return typeof window.isMobile === "function"
      ? window.isMobile()
      : /Mobi|Android/i.test(navigator.userAgent);
  }

  function scaleByPixelRatioGhost(input) {
    const maxDpr = isMobileGhost() ? 1.5 : 2;
    const pixelRatio = Math.min(window.devicePixelRatio || 1, maxDpr);
    return Math.floor(input * pixelRatio);
  }

  function resizeCanvas() {
    const width = scaleByPixelRatioGhost(window.innerWidth);
    const height = scaleByPixelRatioGhost(window.innerHeight);
    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width;
      canvas.height = height;
      return true;
    }
    return false;
  }
  resizeCanvas();

  /* ── Конфіг: дефолти дублюють ghost_* ключі з colors (Paskal.py/DATABASE.md) ── */
  let cfg = {
    enabled: true,
    active_count: 1,
    selection_mode: "random_no_repeat",
    image_change_frequency_sec: 45,
    position_change_delay_sec: 6,
    size_min_px: 220,
    size_max_px: 420,
    size_fixed: false,
    edge_margin_percent: 12,
    reveal_threshold_px: 280,
    max_opacity: 0.55,
    reveal_curve: 2.2,
    fade_in_speed: 0.06,
    fade_out_speed: 0.03,
    hold_duration_sec: 0,
    blur_amount_px: 6,
    glow_strength: 0.35,
    glow_radius_px: 18,
    glow_softness: 0.5,
    mouse_recency_threshold_ms: 450,
    // Колір тонування силуету — за прямим запитом користувача: без тонування
    // силует, залитий чорним (типово для іконок-SVG), був би НІКОЛИ не
    // видимий на #ghost-layer (mix-blend-mode:screen робить чорний повністю
    // прозорим візуально). tint_opacity — сила тонування (0=колір SVG як є,
    // 1=повна заміна на tint_color), регулюється окремо від самого кольору.
    tint_color: "#e8f4ff",
    tint_opacity: 1,
    dev_mode: false,
    // 0 = повністю тверда стіна (та сама сила, що й межі canvas/екрана) —
    // дефолт за прямим запитом користувача: "дим повинен відштовхуватись від
    // привида так само, як від краю екрана". Регулюється через адмінку.
    obstacle_permeability: 0,
    // "Примагнічування" диму вздовж контуру привида — за прямим запитом
    // користувача, додатково до стінки. 0 = вимкнено. Ненульове значення
    // (дефолт підібраний щоб ефект був явно помітний, не хаотичний).
    obstacle_attract_strength: 6000,
    // Підсвічена кромка силуету, кольору "як у диму" — за прямим запитом
    // користувача. Видима лише локально, поруч з курсором (radius_px), не по
    // всьому контуру одразу. Суто візуальний шар, не впливає на фізику.
    // radius_px=35 (не 15, як спершу просив користувач) — свідомий запас:
    // реальний альфа-контур SVG може відстояти від краю bounding box на
    // 15-20px+ (залежить від конкретного силуету — перевірено живим тестом,
    // напр. один з тестових SVG мав 19px відступу справа), тому курсор,
    // наведений туди, де силует "на око" видно (glow/blur розширюють його
    // видиму межу), може опинитись поза жорстким альфа-порогом. Збільшений
    // радіус компенсує цей розрив для більшості форм; регулюється в адмінці.
    edge_highlight_enabled: true,
    edge_highlight_radius_px: 35,
    edge_highlight_width_px: 3,
    edge_highlight_blur_px: 3,
    edge_highlight_strength: 0.9,
  };

  function readCfgFromColors() {
    if (typeof window.getC !== "function") return false;
    const c = (k, fb) => window.getC(k, fb);
    cfg.enabled = c("ghost_enabled", "1") !== "0";
    cfg.active_count = parseInt(c("ghost_active_count", "1"), 10) || 1;
    cfg.selection_mode = c("ghost_selection_mode", "random_no_repeat");
    cfg.image_change_frequency_sec = parseFloat(c("ghost_image_change_frequency_sec", "45")) || 45;
    cfg.position_change_delay_sec = parseFloat(c("ghost_position_change_delay_sec", "6")) || 6;
    cfg.size_min_px = parseFloat(c("ghost_size_min_px", "220")) || 220;
    cfg.size_max_px = parseFloat(c("ghost_size_max_px", "420")) || 420;
    cfg.size_fixed = c("ghost_size_fixed", "0") === "1";
    cfg.edge_margin_percent = parseFloat(c("ghost_edge_margin_percent", "12")) || 12;
    cfg.reveal_threshold_px = parseFloat(c("ghost_reveal_threshold_px", "280")) || 280;
    cfg.max_opacity = Math.min(0.95, Math.max(0.02, parseFloat(c("ghost_max_opacity", "0.55")) || 0.55));
    cfg.reveal_curve = Math.max(0.5, parseFloat(c("ghost_reveal_curve", "2.2")) || 2.2);
    cfg.fade_in_speed = Math.min(1, Math.max(0.005, parseFloat(c("ghost_fade_in_speed", "0.06")) || 0.06));
    cfg.fade_out_speed = Math.min(1, Math.max(0.005, parseFloat(c("ghost_fade_out_speed", "0.03")) || 0.03));
    cfg.hold_duration_sec = Math.max(0, parseFloat(c("ghost_hold_duration_sec", "0")) || 0);
    cfg.blur_amount_px = Math.max(0, parseFloat(c("ghost_blur_amount_px", "6")) || 0);
    cfg.glow_strength = Math.max(0, parseFloat(c("ghost_glow_strength", "0.35")) || 0);
    cfg.glow_radius_px = Math.max(0, parseFloat(c("ghost_glow_radius_px", "18")) || 0);
    cfg.glow_softness = Math.max(0, parseFloat(c("ghost_glow_softness", "0.5")) || 0.5);
    cfg.mouse_recency_threshold_ms = Math.max(50, parseFloat(c("ghost_mouse_recency_threshold_ms", "450")) || 450);
    // Валідація формату (лише #rgb/#rrggbb) — значення йде напряму в
    // ctx.fillStyle, некоректний рядок там просто мовчки ігнорується
    // браузером (не помилка безпеки), але тримаємо дефолт як safe fallback.
    const rawTint = c("ghost_tint_color", "#e8f4ff");
    cfg.tint_color = /^#[0-9a-fA-F]{3}([0-9a-fA-F]{3})?$/.test(rawTint) ? rawTint : "#e8f4ff";
    const parsedTintOpacity = parseFloat(c("ghost_tint_opacity", "1"));
    cfg.tint_opacity = Math.min(1, Math.max(0, isNaN(parsedTintOpacity) ? 1 : parsedTintOpacity));
    cfg.dev_mode = c("ghost_dev_mode", "0") === "1";
    cfg.obstacle_permeability = Math.min(1, Math.max(0, parseFloat(c("ghost_obstacle_permeability", "0")) || 0));
    cfg.obstacle_attract_strength = Math.max(0, parseFloat(c("ghost_obstacle_attract_strength", "6000")) || 0);
    cfg.edge_highlight_enabled = c("ghost_edge_highlight_enabled", "1") !== "0";
    cfg.edge_highlight_radius_px = Math.max(1, parseFloat(c("ghost_edge_highlight_radius_px", "35")) || 35);
    cfg.edge_highlight_width_px = Math.max(0.5, parseFloat(c("ghost_edge_highlight_width_px", "3")) || 3);
    cfg.edge_highlight_blur_px = Math.max(0, parseFloat(c("ghost_edge_highlight_blur_px", "3")) || 3);
    cfg.edge_highlight_strength = Math.min(1, Math.max(0, parseFloat(c("ghost_edge_highlight_strength", "0.9")) || 0.9));
    return true;
  }

  /* ── Список призраків (з публічного /api/ghost-faces) ── */
  let _ghostList = [];
  let _lastIndex = -1;
  let _listLoaded = false;

  function apiBase() {
    return (typeof window.API === "string" ? window.API : "");
  }

  async function loadGhostList() {
    try {
      const res = await fetch(apiBase() + "/api/ghost-faces");
      if (!res.ok) return;
      const data = await res.json();
      _ghostList = Array.isArray(data) ? data : [];
      _listLoaded = true;
    } catch (e) {
      _listLoaded = false;
    }
  }

  function pickNextIndex() {
    const n = _ghostList.length;
    if (n === 0) return -1;
    if (n === 1) return 0;
    if (cfg.selection_mode === "sequential") {
      _lastIndex = (_lastIndex + 1) % n;
      return _lastIndex;
    }
    if (cfg.selection_mode === "random") {
      return Math.floor(Math.random() * n);
    }
    // random_no_repeat (default)
    let idx;
    do {
      idx = Math.floor(Math.random() * n);
    } while (idx === _lastIndex);
    _lastIndex = idx;
    return idx;
  }

  /* ── Растеризація SVG в offscreen canvas ──
     КРИТИЧНО: #ghost-layer canvas має CSS mix-blend-mode:screen (index.html) —
     при цьому режимі чорний колір (RGB 0,0,0) завжди повністю прозорий
     візуально, незалежно від alpha-каналу самого пікселя. Багато SVG-іконок
     (в т.ч. завантажені адміном) залиті суцільним чорним — без тонування
     такий силует був би НІКОЛИ не видимий, навіть на повній яскравості/
     dev_mode (підтверджено живим пиксельним тестом: RGB(0,0,0), alpha=233,
     і при цьому на екрані абсолютно нічого не малювалось). Тонуємо RGB усіх
     непрозорих пікселів у налаштований колір (ghost_tint_color, дефолт
     #e8f4ff — світлий блакитно-білий) через globalCompositeOperation
     "source-in" (малює суцільний прямокутник кольору, але лишає лише ту
     альфу/форму, що вже була намальована) — форма/альфа-канал (потрібні для
     фізичної GL-маски і контуру кромки) лишаються точними, змінюється лише
     колір заливки. tint_opacity — сила тонування (0=колір SVG лишається як
     є, 1=повна заміна кольору): рахується через globalAlpha на етапі заливки
     (не через альфа-канал самого fillStyle), тому SOURCE-IN коректно змішує
     новий колір із уже намальованим під ним замість того щоб просто
     применшити альфу форми. */
  function rasterizeSvg(svgUrl, targetMaxDim) {
    return new Promise((resolve) => {
      const img = new Image();
      img.onload = () => {
        const iw = img.naturalWidth || 1;
        const ih = img.naturalHeight || 1;
        const scale = targetMaxDim / Math.max(iw, ih);
        const dw = Math.max(1, Math.round(iw * scale));
        const dh = Math.max(1, Math.round(ih * scale));
        const off = document.createElement("canvas");
        off.width = dw;
        off.height = dh;
        const octx = off.getContext("2d");
        try {
          octx.drawImage(img, 0, 0, dw, dh);
          if (cfg.tint_opacity > 0) {
            octx.globalCompositeOperation = "source-in";
            octx.globalAlpha = cfg.tint_opacity;
            octx.fillStyle = cfg.tint_color || "#e8f4ff";
            octx.fillRect(0, 0, dw, dh);
            octx.globalCompositeOperation = "source-over";
            octx.globalAlpha = 1;
          }
        } catch (e) { /* CORS/decode failure — ignore, ghost simply won't render */ }
        resolve({ canvas: off, w: dw, h: dh });
      };
      img.onerror = () => resolve(null);
      img.src = svgUrl;
    });
  }

  /* ── Активний привид (state) ── */
  const ghost = {
    data: null,          // {id, svg_file, name, individual_size_px}
    offscreen: null,     // {canvas, w, h}
    x: 0, y: 0,          // px, центр
    w: 0, h: 0,          // px, розмір відмальовки
    currentOpacity: 0,
    targetOpacity: 0,
    // Рівномірна (constant-rate) fade-анімація — currentOpacity рухається до
    // targetOpacity з фіксованою швидкістю (частка/секунду, з cfg.fade_in_speed/
    // fade_out_speed), а не експоненціальним згладжуванням "current +=
    // (target-current)*speed", яке суб'єктивно відчувалось нерівномірним —
    // швидко на старті, потім різко гальмує й "зависає" біля цілі (за прямим
    // запитом користувача: "должно работать плавное появление и затухание").
    // _lastTickTs — timestamp попереднього кадру, для обчислення реального dt
    // (незалежно від частоти кадрів). -1 (не 0!) як маркер "ще не було жодного
    // тика" — performance.now() теоретично може повернути легітимний 0 на
    // самому старті сторінки, а `0` в JS falsy, тому перевірка `if (x)` на
    // звичайному 0-таймстемпі помилково трактувала б "ще не було" щоразу і
    // ламала dt (перший реальний крок після цього миттєво "телепортував" би
    // opacity до цілі замість плавного руху — саме такий баг був спіймано
    // ізольованим unit-тестом при розробці цього фіксу).
    _lastTickTs: -1,
    phase: "hidden",     // hidden | visible | waiting_relocate
    hiddenSinceTs: 0,
    lastImageChangeTs: 0,
    pendingImageChange: false,
    contour: null,        // [{u,v,nx,ny}, ...] — локальні координати 0..1 + нормаль назовні
    contourMaxDim: 0,      // w/h offscreen-канваса на момент побудови контуру (для перевірки)
  };

  /* ── Контур силуету (для підсвіченої кромки, курсор-залежної) ──
     Одноразовий (при зміні SVG, не щокадру) прохід по альфа-каналу offscreen
     canvas — знаходить межові пікселі (альфа переходить через поріг) і
     нормаль "назовні" в цій точці (градієнт альфи по сусідах, той самий
     прийом, що й у obstacleAttractShader в js/script.js). Координати
     зберігаються НОРМАЛІЗОВАНИМИ (0..1 відносно w/h offscreen-канваса) — не
     залежать від поточного розміру/позиції відмальовки на екрані, тому не
     потребують перерахунку при resize/relocate в межах того самого SVG. */
  const CONTOUR_ALPHA_THRESHOLD = 40; // 0..255, той самий порядок, що й GL-маска (>0.15*255≈38)
  const CONTOUR_STEP_PX = 3;          // прорідження скану — досить для гладкої кромки

  function extractContourPoints(offscreenCanvas, w, h) {
    if (!offscreenCanvas || w < 2 || h < 2) return [];
    let data;
    try {
      const octx = offscreenCanvas.getContext("2d", { willReadFrequently: true });
      data = octx.getImageData(0, 0, w, h).data;
    } catch (e) {
      // SecurityError (tainted canvas) чи будь-яка інша проблема читання —
      // деградуємо тихо до порожнього контуру, підсвітка кромки просто не
      // з'явиться, решта модуля (силует, фізика) продовжує працювати.
      return [];
    }
    const alphaAt = (x, y) => {
      if (x < 0 || y < 0 || x >= w || y >= h) return 0;
      return data[(y * w + x) * 4 + 3];
    };
    const points = [];
    for (let y = 1; y < h - 1; y += CONTOUR_STEP_PX) {
      for (let x = 1; x < w - 1; x += CONTOUR_STEP_PX) {
        const a = alphaAt(x, y);
        const isSolid = a > CONTOUR_ALPHA_THRESHOLD;
        if (!isSolid) continue;
        const aL = alphaAt(x - 1, y);
        const aR = alphaAt(x + 1, y);
        const aT = alphaAt(x, y - 1);
        const aB = alphaAt(x, y + 1);
        const isEdge = aL <= CONTOUR_ALPHA_THRESHOLD || aR <= CONTOUR_ALPHA_THRESHOLD ||
          aT <= CONTOUR_ALPHA_THRESHOLD || aB <= CONTOUR_ALPHA_THRESHOLD;
        if (!isEdge) continue;
        // Градієнт альфи вказує ВСЕРЕДИНУ (від прозорого до непрозорого) —
        // нормаль "назовні" це протилежний напрямок.
        let nx = -(aR - aL);
        let ny = -(aB - aT);
        const len = Math.hypot(nx, ny) || 1;
        nx /= len;
        ny /= len;
        points.push({ u: x / w, v: y / h, nx, ny });
      }
    }
    return points;
  }

  function randomSize() {
    if (cfg.size_fixed) return cfg.size_min_px;
    return cfg.size_min_px + Math.random() * Math.max(0, cfg.size_max_px - cfg.size_min_px);
  }

  /* Реальний bbox намальованої мапи України на екрані зараз (враховує поточні
     pan/zoom — #ukraine-svg сам є контейнером із transform, тому просто його
     getBoundingClientRect() дає майже порожню область з великими полями).
     За прямим запитом користувача привид повинен спавнитись лише над картою —
     там, де реально є фоновий дим/glow, а не будь-де на весь viewport (де
     часто взагалі немає диму, і зіткнення з перешкодою нема на чому побачити).
     Викликається лише в момент relocate (раз на кілька секунд, не щокадру) —
     повний скан <path> прийнятний за цією частотою. */
  function getMapScreenBBox() {
    const svg = document.getElementById("ukraine-svg");
    if (!svg) return null;
    try {
      const paths = svg.querySelectorAll("path");
      if (!paths.length) return null;
      let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
      // Достатньо вибірки — контур мапи великий, суцільний, немає потреби
      // перевіряти геометрію кожного з 1000+ <path>.
      const step = Math.max(1, Math.floor(paths.length / 150));
      for (let i = 0; i < paths.length; i += step) {
        const r = paths[i].getBoundingClientRect();
        if (r.width === 0 && r.height === 0) continue;
        if (r.left < minX) minX = r.left;
        if (r.top < minY) minY = r.top;
        if (r.right > maxX) maxX = r.right;
        if (r.bottom > maxY) maxY = r.bottom;
      }
      if (!isFinite(minX) || maxX <= minX || maxY <= minY) return null;
      return { x: minX, y: minY, w: maxX - minX, h: maxY - minY };
    } catch (e) {
      return null;
    }
  }

  function pickRandomPosition(sizePx) {
    const halfSize = sizePx / 2;
    // Базова зона — реальний контур мапи; якщо з якоїсь причини недоступний
    // (мапа ще не завантажена/DOM інший) — деградуємо до старої поведінки
    // (весь viewport з відступом), щоб привид взагалі не зникав.
    const mapBox = getMapScreenBBox();
    const marginX = (cfg.edge_margin_percent / 100) * window.innerWidth;
    const marginY = (cfg.edge_margin_percent / 100) * window.innerHeight;
    const areaX = mapBox ? mapBox.x : marginX;
    const areaY = mapBox ? mapBox.y : marginY;
    const areaW = mapBox ? mapBox.w : (window.innerWidth - marginX * 2);
    const areaH = mapBox ? mapBox.h : (window.innerHeight - marginY * 2);
    // Легкий внутрішній відступ від самого краю контуру мапи (не % від
    // viewport, як раніше, а невеликий фіксований запас) — щоб силует не
    // "вилазив" за межі видимого контуру/glow.
    const inset = Math.min(areaW, areaH) * 0.06;
    const minX = areaX + Math.min(inset, Math.max(0, areaW / 2 - halfSize)) + halfSize;
    const maxX = areaX + areaW - Math.min(inset, Math.max(0, areaW / 2 - halfSize)) - halfSize;
    const minY = areaY + Math.min(inset, Math.max(0, areaH / 2 - halfSize)) + halfSize;
    const maxY = areaY + areaH - Math.min(inset, Math.max(0, areaH / 2 - halfSize)) - halfSize;
    return {
      x: minX + Math.random() * Math.max(0, maxX - minX),
      y: minY + Math.random() * Math.max(0, maxY - minY),
    };
  }

  async function relocateAndMaybeChangeImage(forceNewImage) {
    if (!_listLoaded || _ghostList.length === 0) return;
    if (forceNewImage || !ghost.data) {
      const idx = pickNextIndex();
      if (idx < 0) return;
      const item = _ghostList[idx];
      const sizePx = item.individual_size_px || randomSize();
      const svgUrl = apiBase() + "/img/ghosts/" + item.svg_file;
      const raster = await rasterizeSvg(svgUrl, sizePx);
      if (!raster) return;
      ghost.data = item;
      ghost.offscreen = raster;
      ghost.w = raster.w;
      ghost.h = raster.h;
      ghost.lastImageChangeTs = performance.now();
      // Оновлюємо GL-маску форми привида в js/script.js разом зі зміною SVG —
      // фізична перешкода тепер впирається точно в контур силуету, а не в
      // прямокутний bounding box (за прямим запитом користувача).
      if (typeof window._fluidUpdateObstacleMask === "function") {
        window._fluidUpdateObstacleMask(raster.canvas);
      }
      // Контур для підсвіченої кромки (Canvas2D, курсор-залежна) — той самий
      // offscreen canvas, один прохід при зміні SVG, не щокадру.
      ghost.contour = extractContourPoints(raster.canvas, raster.w, raster.h);
      ghost.contourMaxDim = Math.max(raster.w, raster.h);
    }
    const sizeForPos = Math.max(ghost.w, ghost.h);
    const pos = pickRandomPosition(sizeForPos);
    ghost.x = pos.x;
    ghost.y = pos.y;
    ghost.pendingImageChange = false;
    ghost.phase = "hidden";
  }

  /* ── Перерастеризація ПОТОЧНОГО SVG з новими налаштуваннями тонування ──
     Викликається лише коли колір/сила тонування реально змінились (адмінка,
     live-preview) — на відміну від relocateAndMaybeChangeImage(true), НЕ
     обирає нове зображення й НЕ переміщує привида, лише перемальовує вже
     завантажений силует новим кольором, щоб зміна в адмінці була видна
     миттєво, а не аж після наступної природної зміни картинки. */
  async function reRasterizeCurrentGhost() {
    if (!ghost.data) return;
    const sizePx = ghost.data.individual_size_px || Math.max(ghost.w, ghost.h);
    const svgUrl = apiBase() + "/img/ghosts/" + ghost.data.svg_file;
    const raster = await rasterizeSvg(svgUrl, sizePx);
    if (!raster) return;
    ghost.offscreen = raster;
    ghost.w = raster.w;
    ghost.h = raster.h;
    if (typeof window._fluidUpdateObstacleMask === "function") {
      window._fluidUpdateObstacleMask(raster.canvas);
    }
    ghost.contour = extractContourPoints(raster.canvas, raster.w, raster.h);
    ghost.contourMaxDim = Math.max(raster.w, raster.h);
  }

  /* ── Синхронізація прямокутника привида з obstacle-полем js/script.js ──
     Пишемо (не читаємо) window._fluidConfig.OBSTACLE_ENABLED/OBSTACLE_RECT —
     єдине місце у всьому модулі, де ми виходимо за рамки read-only контракту
     з існуючим двигуном диму, і робимо це навмисно, за тим самим "pull"
     патерном, яким index.html вже керує CURL/SPLAT_RADIUS (config.js читає ці
     поля сам щокадру, ніякого зворотного виклику в script.js не потрібно).

     За прямим запитом користувача перешкода поводиться як БЕЗУМОВНА межа —
     той самий принцип, що й стінки canvas у divergenceShader (js/script.js,
     "if (vL.x < 0.0) { L = -C.x; }" і т.д. — завжди активні, не залежать від
     курсора/яскравості). Раніше перешкода вмикалась лише коли currentOpacity
     (візуальна прозорість силуету) перевищував поріг, і permeability
     масштабувалась разом з нею — на практиці це давало вузьке, рідкісне вікно
     "курсор поруч І дим фізично щільний саме тут", тому дим візуально майже
     ніколи не "натикався" на привида. Тепер фізична перешкода активна завжди,
     поки модуль увімкнено і в привида є розмальована позиція (ghost.offscreen
     готовий) — незалежно від того, наскільки він зараз проступив на очах.
     Візуальна прозорість силуету (render(), alpha/blur/glow) — окремий,
     суто естетичний шар, який ця функція більше не чіпає. */
  function syncObstacleWithFluid() {
    const fc = window._fluidConfig;
    if (!fc) return;
    const active = cfg.enabled && !!ghost.offscreen;
    fc.OBSTACLE_ENABLED = active;
    if (!active) return;
    // CSS px (top-left origin, y росте вниз) -> normalized GL texcoord
    // (y росте вгору) — обов'язкова інверсія Y, інакше перешкода буде
    // дзеркально не там, де насправді малюється силует.
    const rectX = (ghost.x - ghost.w / 2) / window.innerWidth;
    const rectYTopLeft = (ghost.y - ghost.h / 2) / window.innerHeight;
    const rectW = ghost.w / window.innerWidth;
    const rectH = ghost.h / window.innerHeight;
    const rectY = 1 - rectYTopLeft - rectH; // GL: y=0 внизу
    fc.OBSTACLE_RECT = { x: rectX, y: rectY, w: rectW, h: rectH };
    // Постійна проникність — не залежить від currentOpacity (див. коментар
    // вище): дим завжди частково відштовхується/розділяється контуром
    // привида, навіть коли той ще майже не проступив на очах.
    fc.OBSTACLE_PERMEABILITY = cfg.obstacle_permeability;
    // "Примагнічування" вздовж контуру (js/script.js, obstacleAttractShader)
    // — за прямим запитом користувача, щоб форма привида була візуально
    // набагато помітнішою: дим не лише відбивається, а й тягнеться вздовж
    // краю силуету, обрисовуючи його своїм рухом.
    fc.OBSTACLE_ATTRACT_STRENGTH = cfg.obstacle_attract_strength;
  }

  /* ── Активність диму (read-only з window._fluidConfig) ── */
  let _lastMouseMoveTs = 0;
  let _mouseX = -9999, _mouseY = -9999;

  function computeSmokeActivity(now) {
    const fc = window._fluidConfig;
    if (!fc || fc.PAUSED) return false;
    if (document.hidden) return false;
    return (now - _lastMouseMoveTs) < cfg.mouse_recency_threshold_ms;
  }

  /* ── Реальна щільність диму в точці привида ──
     #fluid — окремий WebGL-canvas (js/script.js), намальований чорним фоном з
     mix-blend-mode:screen — де диму немає, піксель майже чорний (r,g,b≈0);
     де дим є — піксель світлий. Читаємо невеликий семпл (5×5, не весь canvas)
     навколо позиції привида через 2D-canvas trick: drawImage WebGL-canvas як
     texture-джерело в маленький offscreen 2D-canvas, потім getImageData лише
     з нього (5×5=25 пікселів) — на порядок дешевше за readPixels() на весь
     екран, і не потребує залазити у внутрішні WebGL-буфери js/script.js
     (read-only, зовнішній observer, як і решта контракту цього модуля).
     Троттлиться (не щокадру) — рахуємо раз на кожні _SMOKE_SAMPLE_EVERY_MS. */
  const _SMOKE_SAMPLE_EVERY_MS = 120;
  const _smokeSampleCanvas = document.createElement("canvas");
  _smokeSampleCanvas.width = 5;
  _smokeSampleCanvas.height = 5;
  const _smokeSampleCtx = _smokeSampleCanvas.getContext("2d", { willReadFrequently: true });
  let _lastSmokeSampleTs = 0;
  let _cachedSmokeDensity = 0;

  function sampleSmokeDensityAt(px, py) {
    const fluidCanvas = document.getElementById("fluid");
    if (!fluidCanvas || fluidCanvas.width === 0 || fluidCanvas.height === 0) return 0;
    // px,py — координати у CSS-пікселях (як mouse/ghost.x/y), fluidCanvas — у
    // власному внутрішньому розмірі (свій DPR-скейлінг) — перевести пропорційно.
    const fx = (px / window.innerWidth) * fluidCanvas.width;
    const fy = (py / window.innerHeight) * fluidCanvas.height;
    const sx = Math.max(0, Math.min(fluidCanvas.width - 5, Math.round(fx - 2)));
    const sy = Math.max(0, Math.min(fluidCanvas.height - 5, Math.round(fy - 2)));
    try {
      _smokeSampleCtx.clearRect(0, 0, 5, 5);
      _smokeSampleCtx.drawImage(fluidCanvas, sx, sy, 5, 5, 0, 0, 5, 5);
      const data = _smokeSampleCtx.getImageData(0, 0, 5, 5).data;
      let sum = 0;
      for (let i = 0; i < data.length; i += 4) {
        // Яскравість пікселя (r+g+b усереднено) — де диму немає, фон майже
        // чорний; де дим є (навіть напівпрозорий), яскравість помітно вища.
        sum += (data[i] + data[i + 1] + data[i + 2]) / 3;
      }
      const avgBrightness = sum / (data.length / 4); // 0..255
      return Math.max(0, Math.min(1, avgBrightness / 60)); // нормалізація: поріг ~60/255 вже "є дим"
    } catch (e) {
      // SecurityError (canvas tainted) чи будь-яка інша проблема читання —
      // деградуємо тихо до 0 (привид просто не проявлятиметься через дим),
      // не ламаючи решту модуля.
      return 0;
    }
  }

  function updateSmokeDensitySample(now, px, py) {
    if (now - _lastSmokeSampleTs < _SMOKE_SAMPLE_EVERY_MS) return _cachedSmokeDensity;
    _lastSmokeSampleTs = now;
    _cachedSmokeDensity = sampleSmokeDensityAt(px, py);
    return _cachedSmokeDensity;
  }

  function computeVisibilityTarget(now) {
    if (!cfg.enabled) return 0;
    if (!ghost.offscreen) return 0;
    if (!computeSmokeActivity(now)) return 0;
    const dist = Math.hypot(_mouseX - ghost.x, _mouseY - ghost.y);
    const splatR = (window._fluidConfig && typeof window._fluidConfig.SPLAT_RADIUS === "number")
      ? window._fluidConfig.SPLAT_RADIUS : 0.25;
    const effectiveRadius = cfg.reveal_threshold_px * (0.5 + splatR);
    if (dist >= effectiveRadius) return 0;
    const t = 1 - (dist / effectiveRadius);
    const proximityFactor = Math.pow(Math.max(0, Math.min(1, t)), cfg.reveal_curve);

    // Реальна щільність видимого диму саме в точці привида — без цього привид
    // проявлявся б і там, де диму візуально немає взагалі (лише курсор поруч).
    const smokeDensity = updateSmokeDensitySample(now, ghost.x, ghost.y);

    return proximityFactor * smokeDensity * cfg.max_opacity;
  }

  /* ── rAF-цикл: власний, незалежний від js/script.js ── */
  let _rafHandle = null;

  function tick(now) {
    _rafHandle = requestAnimationFrame(tick);
    if (document.hidden) return;
    if (!cfg.enabled || !_listLoaded || _ghostList.length === 0) {
      if (ghost.currentOpacity > 0) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ghost.currentOpacity = 0;
      }
      if (window._fluidConfig) window._fluidConfig.OBSTACLE_ENABLED = false;
      return;
    }
    if (resizeCanvas()) { /* new size picked up next frame */ }

    // computeVisibilityTarget() повертає БЕЗПЕРЕРВНО "плаваюче" значення
    // (курсор рухається, щільність диму міняється щокадру) — тому "ціль
    // змінилась" відбувається майже щокадру, і ease-перехід з фіксованою
    // тривалістю, що перезапускається щоразу, ніколи не встигав би
    // завершитись (застрягав би у постійному рестарті). Замість цього —
    // РІВНОМІРНА швидкість зміни opacity в одиницю часу (constant-rate fade,
    // не експоненціальне згладжування "current += (target-current)*speed",
    // яке суб'єктивно відчувалось нерівномірним — швидко на старті, потім
    // різко гальмує й "зависає" біля цілі). cfg.fade_in_speed/fade_out_speed
    // — та сама одиниця (частка opacity за секунду), тому дефолтні значення
    // з адмінки (0.06/0.03) лишаються прямо сумісними, просто застосовані
    // рівномірно, а не по спадній кривій.
    ghost.targetOpacity = computeVisibilityTarget(now);
    const dt = ghost._lastTickTs >= 0 ? Math.min(0.1, (now - ghost._lastTickTs) / 1000) : 0;
    ghost._lastTickTs = now;
    const rate = (ghost.targetOpacity > ghost.currentOpacity ? cfg.fade_in_speed : cfg.fade_out_speed) * 12;
    const maxStep = rate * dt;
    const diff = ghost.targetOpacity - ghost.currentOpacity;
    // maxStep=0 (перший тик після старту/паузи, dt ще не визначено) означає
    // "не рухаємось у ЦЬОМУ кадрі" — НЕ "ціль уже досягнута". Попередня
    // умова `|| maxStep <= 0` помилково телепортувала opacity до цілі на
    // самому першому кадрі (спіймано ізольованим unit-тестом).
    if (maxStep > 0 && Math.abs(diff) <= maxStep) {
      ghost.currentOpacity = ghost.targetOpacity;
    } else if (maxStep > 0) {
      ghost.currentOpacity += Math.sign(diff) * maxStep;
    }

    // Перехід у "приховано" — фіксуємо момент, коли справді стало невидимо
    if (ghost.currentOpacity < 0.01 && ghost.targetOpacity === 0) {
      if (ghost.phase !== "waiting_relocate" && ghost.phase !== "hidden_idle") {
        ghost.hiddenSinceTs = now;
        ghost.phase = "waiting_relocate";
      }
    } else if (ghost.currentOpacity > 0.01) {
      ghost.phase = "visible";
    }

    syncObstacleWithFluid();

    // Незалежний таймер зміни зображення — застосовується лише коли невидимо
    if (!ghost.pendingImageChange &&
        (now - ghost.lastImageChangeTs) > cfg.image_change_frequency_sec * 1000) {
      ghost.pendingImageChange = true;
    }

    // Реагуємо на relocate/зміну зображення лише після достатньої паузи в прихованому стані
    if (ghost.phase === "waiting_relocate" &&
        (now - ghost.hiddenSinceTs) > cfg.position_change_delay_sec * 1000) {
      relocateAndMaybeChangeImage(ghost.pendingImageChange);
      ghost.phase = "hidden_idle";
    }

    render();
  }

  /* ── Режим розробки (підсвітка) — керується з адмінки (ghost_dev_mode) ──
     Коли увімкнено: силует завжди показується на повній видимості (ігноруючи
     курсор/дим) — щоб адмін одразу бачив, ДЕ саме зараз знаходиться привид,
     без потреби наводити курсор чи відкривати консоль браузера. За прямим
     запитом користувача прямокутна рамка/заливка прибрані — фізична
     перешкода тепер працює по реальному контуру SVG (альфа-маска в
     js/script.js), і візуальний прямокутник навколо силуету вводив в оману
     ("дим ніби має впиратись саме в рамку"), хоча насправді рамка була лише
     bounding box, не формою перешкоди. Лишився тільки текстовий підпис —
     без обведення контуру. Не змінює основну механіку проявлення — лише
     поверх неї, коли прапорець увімкнено. */
  function renderDevOverlay(dpr, dx, dy, dw, dh) {
    if (!cfg.dev_mode || !ghost.data) return;
    ctx.save();
    ctx.filter = "none";
    ctx.globalAlpha = 1;
    ctx.globalCompositeOperation = "source-over";
    ctx.fillStyle = "#ffdd00";
    ctx.font = `${14 * dpr}px sans-serif`;
    const label = `GHOST DEV · id=${ghost.data.id} · ${ghost.data.name || ""}`;
    ctx.fillText(label, dx, Math.max(14 * dpr, dy - 6 * dpr));
    ctx.restore();
  }

  /* ── Приблизний "колір диму" (незалежний генератор, не читає js/script.js) ──
     Плавний циклічний дрейф відтінку в синьо-блакитному спектрі (той самий
     смисловий діапазон, що й дефолтний colorRange диму в js/script.js), без
     різких стрибків — лінійна інтерполяція між поточним і наступним випадково
     обраним відтінком раз на кілька секунд. Суто візуальне наближення "схоже
     на дим", за прямим рішенням користувача не тягнути реальний колір з
     WebGL-частини (щоб не чіпати js/script.js в цій фічі). */
  let _edgeColorFromHue = 0.56, _edgeColorToHue = 0.56, _edgeColorStartTs = 0;
  const _EDGE_COLOR_CYCLE_MS = 3200;

  function smokeLikeColor(now) {
    if (now - _edgeColorStartTs > _EDGE_COLOR_CYCLE_MS) {
      _edgeColorFromHue = _edgeColorToHue;
      // Синьо-блакитний діапазон (~200°-230° у HSL, тобто hue 0.5-0.64) —
      // той самий смисловий простір, що й дефолтний #0057B7 дим.
      _edgeColorToHue = 0.52 + Math.random() * 0.12;
      _edgeColorStartTs = now;
    }
    const t = Math.min(1, (now - _edgeColorStartTs) / _EDGE_COLOR_CYCLE_MS);
    const hue = _edgeColorFromHue + (_edgeColorToHue - _edgeColorFromHue) * t;
    // Висока яскравість/насиченість (95%/85%) — контрастніше до фонового
    // диму (за прямим запитом користувача: "не зливалось", кромка мала
    // читатись окремо, майже біло-блакитним світінням, не тьмяним відтінком.
    return `hsl(${Math.round(hue * 360)}, 95%, 85%)`;
  }

  /* ── Підсвічена кромка силуету, курсор-залежна, однобічна ──
     За прямим запитом користувача: розмита кромка кольору "як у диму",
     видима ЛИШЕ поруч з курсором (edge_highlight_radius_px, дефолт ~15px), і
     ЛИШЕ з того боку контуру, де курсор зараз — не заливає весь силует, а
     "оживає" локально, ніби дим облизує край. Суто декоративний шар (не
     впливає на фізику/OBSTACLE_*), тому не залежить від ghost.currentOpacity
     — курсор може "намацати" кромку навіть коли привид ще майже не
     проступив на очах (дим все одно реально фізично взаємодіє з контуром,
     навіть коли той візуально малопомітний — ця підсвітка про це сигналізує).
     dx,dy,dw,dh — device-px destination rect, той самий, що й для силуету. */
  function renderEdgeHighlight(dpr, dx, dy, dw, dh) {
    if (!cfg.edge_highlight_enabled) return;
    if (!ghost.contour || ghost.contour.length === 0) return;
    const radiusCss = cfg.edge_highlight_radius_px;
    // Швидкий ранній вихід: якщо курсор далеко за межами bbox+радіус —
    // не варто гнати повний прохід по точках контуру щокадру.
    const bboxPad = radiusCss + 4;
    if (_mouseX < ghost.x - ghost.w / 2 - bboxPad || _mouseX > ghost.x + ghost.w / 2 + bboxPad ||
        _mouseY < ghost.y - ghost.h / 2 - bboxPad || _mouseY > ghost.y + ghost.h / 2 + bboxPad) {
      return;
    }

    const now = performance.now();
    const color = smokeLikeColor(now);
    const widthDev = cfg.edge_highlight_width_px * dpr;
    const blurDev = cfg.edge_highlight_blur_px * dpr;

    // Canvas2D не підтримує per-vertex alpha в одному path/fill виклику —
    // кожна активна точка малюється власним коротким fill з власною
    // globalAlpha. Кількість активних точок обмежена радіусом підсвітки
    // (~15px) відносно кроку сканування контуру (CONTOUR_STEP_PX=3) — завжди
    // невелика підмножина від усього контуру, дешево навіть по одній на fill.
    ctx.save();
    ctx.filter = blurDev > 0 ? `blur(${blurDev}px)` : "none";
    ctx.fillStyle = color;
    for (let i = 0; i < ghost.contour.length; i++) {
      const p = ghost.contour[i];
      // Локальна (0..1) -> CSS px екрана (центр силуету + офсет від центру
      // offscreen-канваса, промасштабований до поточного розміру відмальовки).
      const px = ghost.x - ghost.w / 2 + p.u * ghost.w;
      const py = ghost.y - ghost.h / 2 + p.v * ghost.h;
      const dist = Math.hypot(_mouseX - px, _mouseY - py);
      if (dist > radiusCss) continue;
      const t = 1 - dist / radiusCss;
      // Крива згасання — компроміс між "надто круто" (1.6, ефект майже не
      // видно) і "надто плоско" (0.7, всі точки в радіусі 35px світяться
      // майже однаково → зливаються у суцільну кляксу, не тонку лінію вздовж
      // курсора). 1.1 дає плавний, але виразний спад — яскраво біля курсора,
      // помітно тьмяніше вже за 1/3 радіуса.
      const alpha = Math.pow(t, 1.1) * cfg.edge_highlight_strength;
      if (alpha < 0.03) continue;
      // Точка кромки в device-px, трохи зсунута вздовж нормалі назовні —
      // підсвітка виглядає як обвідка ПО КРАЮ, не всередині силуету.
      const cx = dx + p.u * dw + p.nx * widthDev * 0.4;
      const cy = dy + p.v * dh + p.ny * widthDev * 0.4;
      ctx.globalAlpha = alpha;
      ctx.beginPath();
      ctx.arc(cx, cy, widthDev, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.restore();
  }

  function render() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const dpr = canvas.width / window.innerWidth;
    const effectiveOpacity = cfg.dev_mode ? Math.max(ghost.currentOpacity, cfg.max_opacity, 0.9) : ghost.currentOpacity;
    if (!ghost.offscreen) return;
    const dx = (ghost.x - ghost.w / 2) * dpr;
    const dy = (ghost.y - ghost.h / 2) * dpr;
    const dw = ghost.w * dpr;
    const dh = ghost.h * dpr;

    if (effectiveOpacity > 0.003) {
      ctx.save();
      if (cfg.glow_radius_px > 0 && cfg.glow_strength > 0) {
        ctx.filter = `blur(${cfg.glow_radius_px * dpr}px)`;
        ctx.globalAlpha = effectiveOpacity * cfg.glow_strength * cfg.glow_softness;
        ctx.drawImage(ghost.offscreen.canvas, dx, dy, dw, dh);
      }
      ctx.filter = cfg.blur_amount_px > 0 ? `blur(${cfg.blur_amount_px * dpr}px)` : "none";
      ctx.globalAlpha = effectiveOpacity;
      ctx.drawImage(ghost.offscreen.canvas, dx, dy, dw, dh);
      ctx.restore();

      renderDevOverlay(dpr, dx, dy, dw, dh);
    }

    // Підсвічена кромка — НЕЗАЛЕЖНО від effectiveOpacity силуету (див.
    // коментар над renderEdgeHighlight): курсор може "намацати" кромку
    // навіть коли привид ще практично невидимий на очах.
    renderEdgeHighlight(dpr, dx, dy, dw, dh);
  }

  function startLoop() {
    if (_rafHandle !== null) return;
    _rafHandle = requestAnimationFrame(tick);
  }

  /* ── Вхідні події: власні, незалежні від js/script.js ── */
  window.addEventListener("mousemove", (e) => {
    _lastMouseMoveTs = performance.now();
    _mouseX = e.clientX;
    _mouseY = e.clientY;
  });

  window.addEventListener("resize", () => {
    resizeCanvas();
    // Позиція активного привида зберігається у px відносно вікна — при ресайзі
    // просто перевіряємо межі safe-zone, не "стрибаємо" довільно.
    if (ghost.data) {
      const sizeForPos = Math.max(ghost.w, ghost.h);
      const marginX = (cfg.edge_margin_percent / 100) * window.innerWidth;
      const marginY = (cfg.edge_margin_percent / 100) * window.innerHeight;
      const halfSize = sizeForPos / 2;
      ghost.x = Math.min(Math.max(ghost.x, Math.max(marginX, halfSize)), window.innerWidth - Math.max(marginX, halfSize));
      ghost.y = Math.min(Math.max(ghost.y, Math.max(marginY, halfSize)), window.innerHeight - Math.max(marginY, halfSize));
    }
  });

  document.addEventListener("visibilitychange", () => {
    // rAF сам собою продовжує планувати кадри (браузер троттлить неактивні
    // вкладки самостійно) — tick() перевіряє document.hidden і рано виходить.
  });

  /* ── Публічний контракт ── */
  window.applyGhostConfig = function () {
    const prevTintColor = cfg.tint_color;
    const prevTintOpacity = cfg.tint_opacity;
    readCfgFromColors();
    // Живий preview в адмінці: якщо колір/сила тонування реально змінились —
    // перемальовуємо вже завантажений силует негайно, не чекаючи наступної
    // природної зміни картинки (яка може статись через хвилини).
    if (ghost.data && (cfg.tint_color !== prevTintColor || cfg.tint_opacity !== prevTintOpacity)) {
      reRasterizeCurrentGhost();
    }
  };

  window._ghostSyncState = function () {
    readCfgFromColors();
    canvas.style.display = cfg.enabled ? "" : "none";
  };

  // Debug-геттер — корисно для підтримки/діагностики, не використовується в UI.
  window._ghostDebugState = function () {
    return {
      cfg: Object.assign({}, cfg),
      ghost: {
        id: ghost.data ? ghost.data.id : null,
        x: ghost.x, y: ghost.y, w: ghost.w, h: ghost.h,
        currentOpacity: ghost.currentOpacity,
        targetOpacity: ghost.targetOpacity,
        phase: ghost.phase,
      },
      listLoaded: _listLoaded,
      listLength: _ghostList.length,
    };
  };

  /* ── Ініціалізація ──
     Мінімум 2 SVG — вимога ТЗ, щоб мав сенс selection_mode (інакше "вибір
     наступного привида" з 1 елементом — тавтологія). */
  document.addEventListener("DOMContentLoaded", async () => {
    readCfgFromColors();
    await loadGhostList();
    if (_ghostList.length >= 2) {
      await relocateAndMaybeChangeImage(true);
      startLoop();
    }
  });
})();
