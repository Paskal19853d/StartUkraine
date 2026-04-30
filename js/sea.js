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
};

let currentSvgContent = '';   // останній застосований SVG

/* ── АНІМАЦІЯ ─────────────────────────────────────────────────────────── */
let t = 0;
let _lastSeaFrame = 0;
function animate(ts) {
  if (!document.hidden) requestAnimationFrame(animate);
  // Throttle to ~12fps — sea waves are slow, imperceptible above 10fps
  if (ts - _lastSeaFrame < 80) return;
  _lastSeaFrame = ts;
  t += 0.013;
  const rad  = (CFG.waveDir * Math.PI) / 180;
  const base = 0.0008 + (CFG.waveSpeed / 20) * 0.0006;
  const bfX  = (base * Math.max(0.25, Math.abs(Math.cos(rad))) + Math.sin(t * 0.4) * base * 0.3).toFixed(6);
  const bfY  = (base * Math.max(0.25, Math.abs(Math.sin(rad))) + Math.cos(t * 0.3) * base * 0.25).toFixed(6);
  turb.setAttribute('baseFrequency', `${bfX} ${bfY}`);
}
document.addEventListener('visibilitychange', () => {
  if (!document.hidden) requestAnimationFrame(animate);
});

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
  nodes.forEach(n => {
    const imported = document.importNode(n, true);
    /* Знімаємо власні fill/stroke щоб успадковувалось від групи */
    [imported, ...imported.querySelectorAll('*')].forEach(el => {
      if (el.removeAttribute) {
        el.removeAttribute('fill');
        el.removeAttribute('stroke');
        el.removeAttribute('stroke-width');
      }
      if (el.style) { el.style.fill = ''; el.style.stroke = ''; }
    });
    pathsG.appendChild(imported);
  });
  group.appendChild(pathsG);

  currentSvgContent = svgText;
  return true;
}

/* ── ЗАСТОСУВАННЯ КОНФІГУ ─────────────────────────────────────────────── */
function applyConfig(svgContent) {
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
    group.innerHTML = '';
    currentSvgContent = '';
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
      if (v === '' || v === null || v === undefined) return;
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
  /* Одразу застосовуємо стан з сервера (window.SEA_ENABLED вбудовано в <head>) */
  seaSvg.style.display = (window.SEA_ENABLED === false) ? 'none' : '';
  requestAnimationFrame(animate);
  const waitColors = (attempts = 0) => {
    if (window.COLORS && Object.keys(window.COLORS).length > 0) {
      syncCfg();
    } else if (attempts < 100) {
      setTimeout(() => waitColors(attempts + 1), 50);
    }
  };
  waitColors();
}

if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
else init();

})();
