/**
 * sea.js — Хвилі морів (SVG feTurbulence, окремий #sea-svg)
 *
 * Два режими:
 *  1. Кастомний SVG — якщо sea_svg_content є в COLORS, вставляє SVG-шляхи морів
 *     з трансформом (translate + scale) у #sea-group.
 *  2. Дефолтні еліпси — якщо sea_svg_content порожній.
 *
 * Керування: BroadcastChannel 'zoryana_sea' або window.seaApplyConfig().
 */
(function () {
'use strict';

const seaSvg = document.getElementById('sea-svg');
const group  = document.getElementById('sea-group');
const turb   = document.getElementById('sea-turb');
const disp   = document.getElementById('sea-disp');
if (!seaSvg || !group || !turb || !disp) return;

const CFG = {
  waveColor:   '#a0d7ff',
  intensity:   42,
  numOctaves:  3,
  sizeX:       100,
  sizeY:       100,
  shoreImpact: 50,
  blur:        0,
  waveDir:     45,
  waveSpeed:   5,
  glowOn:      true,
  glowColor:   '#60b8ff',
  glowSpread:  30,
  svgTx:       0,
  svgTy:       0,
  svgScale:    1,
  /* дефолтні еліпси */
  blackCx: 6050,  blackCy: 8450, blackRx: 4950, blackRy: 1050,
  azovCx:  11350, azovCy:  7725, azovRx:  2050, azovRy:  1225,
};

let currentSvgContent = '';   // останній застосований SVG

/* ── АНІМАЦІЯ ─────────────────────────────────────────────────────────── */
let t = 0;
function animate() {
  t += 0.003 + CFG.waveSpeed * 0.0007;
  const rad  = (CFG.waveDir * Math.PI) / 180;
  const base = 0.0008 + (CFG.waveSpeed / 20) * 0.0006;
  const bfX  = (base * Math.max(0.25, Math.abs(Math.cos(rad))) + Math.sin(t * 0.4) * base * 0.3).toFixed(6);
  const bfY  = (base * Math.max(0.25, Math.abs(Math.sin(rad))) + Math.cos(t * 0.3) * base * 0.25).toFixed(6);
  turb.setAttribute('baseFrequency', `${bfX} ${bfY}`);
  requestAnimationFrame(animate);
}

/* ── SVG-КОНТЕНТ: вставляє шляхи завантаженого файлу ─────────────────── */
function applyCustomSvg(svgText) {
  const parser  = new DOMParser();
  const svgDoc  = parser.parseFromString(svgText, 'image/svg+xml');
  const svgRoot = svgDoc.documentElement;

  if (svgRoot.tagName === 'parsererror' || !svgRoot.querySelector) return false;

  /* Витягуємо дочірні елементи (skip defs/title/metadata) */
  const skip = new Set(['defs','title','desc','metadata','style']);
  const nodes = [...svgRoot.childNodes].filter(n =>
    n.nodeType === Node.ELEMENT_NODE && !skip.has(n.tagName.toLowerCase())
  );
  if (!nodes.length) return false;

  /* Замінюємо вміст sea-group на кастомні шляхи */
  group.innerHTML = '';
  const pathsG = document.createElementNS('http://www.w3.org/2000/svg', 'g');
  pathsG.id = 'sea-paths';
  nodes.forEach(n => pathsG.appendChild(document.importNode(n, true)));
  group.appendChild(pathsG);

  currentSvgContent = svgText;
  return true;
}

/* ── ДЕФОЛТНІ ЕЛІПСИ ─────────────────────────────────────────────────── */
function applyDefaultEllipses() {
  const sx = CFG.sizeX / 100, sy = CFG.sizeY / 100;
  group.innerHTML = `
    <ellipse id="sea-black" cx="${CFG.blackCx}" cy="${CFG.blackCy}"
             rx="${CFG.blackRx * sx}" ry="${CFG.blackRy * sy}" fill="${CFG.waveColor}"/>
    <ellipse id="sea-azov"  cx="${CFG.azovCx}"  cy="${CFG.azovCy}"
             rx="${CFG.azovRx * sx}" ry="${CFG.azovRy * sy}" fill="${CFG.waveColor}"/>`;
  currentSvgContent = '';
}

/* ── ЗАСТОСУВАННЯ КОНФІГУ ─────────────────────────────────────────────── */
function applyConfig(svgContent) {
  /* Якщо кастомний SVG — вставляємо або оновлюємо трансформ */
  if (svgContent) {
    if (svgContent !== currentSvgContent) applyCustomSvg(svgContent);
    const pathsG = document.getElementById('sea-paths');
    if (pathsG) {
      pathsG.setAttribute('transform',
        `translate(${CFG.svgTx},${CFG.svgTy}) scale(${CFG.svgScale})`);
      pathsG.setAttribute('fill', CFG.waveColor);
      pathsG.setAttribute('stroke', 'none');
    }
  } else {
    if (currentSvgContent) {
      applyDefaultEllipses();   /* SVG видалено → повертаємо еліпси */
    } else if (!document.getElementById('sea-black')) {
      applyDefaultEllipses();   /* перший старт без попереднього малювання */
    } else {
      /* Оновлюємо атрибути еліпсів без перемальовування */
      const sx = CFG.sizeX / 100, sy = CFG.sizeY / 100;
      const elB = document.getElementById('sea-black');
      const elA = document.getElementById('sea-azov');
      if (elB) { elB.setAttribute('cx',CFG.blackCx); elB.setAttribute('cy',CFG.blackCy);
                 elB.setAttribute('rx',CFG.blackRx*sx); elB.setAttribute('ry',CFG.blackRy*sy);
                 elB.setAttribute('fill',CFG.waveColor); }
      if (elA) { elA.setAttribute('cx',CFG.azovCx); elA.setAttribute('cy',CFG.azovCy);
                 elA.setAttribute('rx',CFG.azovRx*sx); elA.setAttribute('ry',CFG.azovRy*sy);
                 elA.setAttribute('fill',CFG.waveColor); }
    }
  }

  /* Прозорість */
  group.setAttribute('opacity', (0.2 + (CFG.intensity / 100) * 0.55).toFixed(2));

  /* Амплітуда хвиль */
  disp.setAttribute('scale', Math.round(150 + CFG.shoreImpact * 7));

  /* Деталізація */
  turb.setAttribute('numOctaves', Math.min(8, Math.max(1, CFG.numOctaves)));

  /* Власне свічення моря */
  if (CFG.glowOn && CFG.glowSpread > 0) {
    const s = CFG.glowSpread;
    seaSvg.style.filter = [
      `drop-shadow(0 0 ${Math.round(s*0.3)}px ${CFG.glowColor})`,
      `drop-shadow(0 0 ${Math.round(s*0.7)}px ${CFG.glowColor}99)`,
      `drop-shadow(0 0 ${s}px ${CFG.glowColor}55)`,
    ].join(' ');
  } else {
    seaSvg.style.filter = '';
  }

  /* Розмитість */
  group.style.filter = CFG.blur > 0 ? `url(#sea-filter) blur(${CFG.blur}px)` : 'url(#sea-filter)';
}

/* ── ЧИТАННЯ З COLORS ──────────────────────────────────────────────────── */
function syncCfg(src) {
  const C = src || window.COLORS || {};
  const g = k => { const v = C[k]; return v?.value ?? v; };

  CFG.waveColor   = g('sea_wave_color')    || '#a0d7ff';
  CFG.intensity   = parseFloat(g('sea_wave_intensity') ?? 42);
  CFG.numOctaves  = parseInt(g('sea_wave_count')       ?? 3);
  CFG.sizeX       = parseFloat(g('sea_size_x')         ?? 100);
  CFG.sizeY       = parseFloat(g('sea_size_y')         ?? 100);
  CFG.shoreImpact = parseFloat(g('sea_shore_impact')   ?? 50);
  CFG.blur        = parseFloat(g('sea_blur')           ?? 0);
  CFG.waveDir     = parseFloat(g('sea_wave_dir')       ?? 45);
  CFG.waveSpeed   = parseFloat(g('sea_wave_speed')     ?? 5);
  CFG.glowOn      = (g('sea_glow_on')   ?? '1') !== '0';
  CFG.glowColor   = g('sea_glow_color') || '#60b8ff';
  const seaOn = (g('sea_enabled') ?? '1') !== '0';
  seaSvg.style.display = seaOn ? '' : 'none';
  CFG.glowSpread  = parseFloat(g('sea_glow_spread')    ?? 30);
  CFG.svgTx       = parseFloat(g('sea_svg_tx')         ?? 0);
  CFG.svgTy       = parseFloat(g('sea_svg_ty')         ?? 0);
  CFG.svgScale    = parseFloat(g('sea_svg_scale')      ?? 1);
  CFG.blackCx = parseFloat(g('sea_black_cx') ?? 6050);
  CFG.blackCy = parseFloat(g('sea_black_cy') ?? 8450);
  CFG.blackRx = parseFloat(g('sea_black_rx') ?? 4950);
  CFG.blackRy = parseFloat(g('sea_black_ry') ?? 1050);
  CFG.azovCx  = parseFloat(g('sea_azov_cx')  ?? 11350);
  CFG.azovCy  = parseFloat(g('sea_azov_cy')  ?? 7725);
  CFG.azovRx  = parseFloat(g('sea_azov_rx')  ?? 2050);
  CFG.azovRy  = parseFloat(g('sea_azov_ry')  ?? 1225);

  applyConfig(g('sea_svg_content') || '');
}
window.seaApplyConfig = () => syncCfg();

/* ── ПЕРЕЗАВАНТАЖЕННЯ COLORS З СЕРВЕРА (після завантаження нового SVG) ── */
async function reloadFromServer() {
  try {
    const api = window.API || 'http://127.0.0.1:8000';
    const r = await fetch(`${api}/api/colors`);
    window.COLORS = await r.json();
    syncCfg();
  } catch (_) {}
}

/* ── BROADCASTCHANNEL ──────────────────────────────────────────────────── */
try {
  const bc = new BroadcastChannel('zoryana_sea');
  bc.onmessage = e => {
    if (!e.data) return;
    if (e.data.type === 'sea_reload') { reloadFromServer(); return; }
    if (e.data.type !== 'sea_update') return;
    if (!window.COLORS) window.COLORS = {};
    Object.entries(e.data.config).forEach(([k, v]) => {
      if (!window.COLORS[k]) window.COLORS[k] = { value: v, label: k };
      else window.COLORS[k].value = v;
    });
    // Синхронізуємо SEA_ENABLED щоб live-toggle з адмінки працював
    if ('sea_enabled' in e.data.config) {
      window.SEA_ENABLED = e.data.config['sea_enabled'] !== '0';
    }
    syncCfg();
  };
} catch (_) {}

/* ── ЗАПУСК ────────────────────────────────────────────────────────────── */
function init() {
  // Миттєва перевірка значення з сервера (вбудовано в HTML до завантаження COLORS)
  if (window.SEA_ENABLED === false) {
    seaSvg.style.display = 'none';
  }
  animate();
  const waitColors = () => {
    if (window.COLORS && Object.keys(window.COLORS).length > 0) {
      syncCfg();
    } else {
      setTimeout(waitColors, 50);
    }
  };
  waitColors();
}

if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
else init();

})();
