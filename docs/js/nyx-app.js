/* ═══════════════════════════════════════════════════════════════
   Nyx Terminal — Main Application
   Routing, data fetching, rendering
   ═══════════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  var API = window.NYX_API || 'http://localhost:8000';
  var cache = {};
  var currentView = 'dashboard';
  var chartInstances = {};
  var DEMO = window.NYX_DEMO_DATA || {};
  // Auto-detect demo mode: if we have demo data and are NOT on localhost API
  var DEMO_MODE = Object.keys(DEMO).length > 0 && !window.NYX_API;

  // ═══════════════════════════════════════════════════════════
  // I18N — Bilingual support (ES / EN)
  // ═══════════════════════════════════════════════════════════

  var currentLang = localStorage.getItem('nyx_lang') || 'es';

  var TRANSLATIONS = {
    es: {
      'sidebar.hide': 'Ocultar panel ([ )',
      'sidebar.map': 'Mapa',
      'sidebar.markets': 'Mercados',
      'sidebar.settings': 'Configuracion',
      'dash.early_warnings': 'Alertas Tempranas',
      'dash.social_sentiment': 'Sentiment Social',
      'dash.kpi.dollar': 'Dolar Blue',
      'dash.kpi.risk': 'Riesgo Pais',
      'dash.kpi.inflation': 'Inflacion',
      'dash.kpi.reserves': 'Reservas',
      'dash.kpi.spread': 'Brecha',
      'dash.chart.dollar': 'Dolar Blue vs Oficial',
      'dash.chart.inflation': 'Inflacion Mensual',
      'dash.chart.risk': 'Riesgo Pais',
      'dash.legend.official': 'Oficial',
      'dash.legend.historical': 'Historico',
      'dash.legend.monthly': 'Mensual',
      'dash.legend.average': 'Promedio',
      'dash.mini.carry': 'Carry Trade',
      'dash.mini.velocity': 'Velocidad Dolar',
      'dash.mini.monetary': 'Base Monetaria',
      'dash.signals': 'Senales de Riesgo',
      'map.signals': 'Senales Macro',
      'map.event_types': 'Tipos de Evento',
      'map.type.economic': 'Economico',
      'map.type.labor': 'Sindical',
      'map.type.regulatory': 'Regulatorio',
      'map.type.political': 'Politico',
      'map.type.climate': 'Climatico',
      'map.type.news': 'Informativo',
      'map.stat.risk': 'Riesgo Pais',
      'map.stat.spread': 'Brecha %',
      'map.stat.events': 'Eventos',
      'merc.title': 'Mercados',
      'merc.kpi.spread': 'Brecha Blue',
      'merc.kpi.carry': 'Carry Trade Blue',
      'merc.kpi.reserves': 'Reservas BCRA',
      'merc.cotiz': 'Cotizaciones',
      'merc.th.type': 'Tipo',
      'merc.th.buy': 'Compra',
      'merc.th.sell': 'Venta',
      'merc.th.spread': 'Brecha',
      'merc.th.change': 'Variacion',
      'merc.th.updated': 'Actualizado',
      'merc.bcra': 'Variables BCRA',
      'merc.carry': 'Carry Trade',
      'merc.rates': 'Tasas & Politica',
      'config.title': 'Configuracion',
      'config.save': 'Guardar',
      'config.saving': 'Guardando...',
      'config.saved': 'Guardado',
      'config.error': 'Error',
      'config.load_error': 'No se pudo cargar la configuracion',
      'chat.sub': 'AI-powered — analisis economico argentino',
      'chat.placeholder': 'Pregunta algo...',
      'live.transcript': 'Transcripcion',
      'live.alerts': 'Alertas',
      'live.waiting': 'Esperando transmision...',
      'live.no_alerts': 'Sin alertas aun...',
      'live.url_placeholder': 'URL de YouTube Live...',
      'live.start': 'Iniciar',
      'live.stop': 'Detener',
      'dyn.updated': 'actualizado',
      'dyn.convergence': 'convergencia',
      'dyn.low_spread': 'spread bajo',
      'dyn.high_spread': 'spread alto',
      'dyn.critical_spread': 'brecha critica',
      'dyn.monthly_gain': 'ganancia mensual',
      'dyn.internationals': 'internacionales',
      'dyn.no_news': 'Sin noticias disponibles',
      'dyn.api_connected': 'API conectada',
      'dyn.api_error': 'API error',
      'dyn.api_disconnected': 'API desconectada',
    },
    en: {
      'sidebar.hide': 'Hide panel ([ )',
      'sidebar.map': 'Map',
      'sidebar.markets': 'Markets',
      'sidebar.settings': 'Settings',
      'dash.early_warnings': 'Early Warnings',
      'dash.social_sentiment': 'Social Sentiment',
      'dash.kpi.dollar': 'Blue Dollar',
      'dash.kpi.risk': 'Country Risk',
      'dash.kpi.inflation': 'Inflation',
      'dash.kpi.reserves': 'Reserves',
      'dash.kpi.spread': 'Spread',
      'dash.chart.dollar': 'Blue vs Official Rate',
      'dash.chart.inflation': 'Monthly Inflation',
      'dash.chart.risk': 'Country Risk',
      'dash.legend.official': 'Official',
      'dash.legend.historical': 'Historical',
      'dash.legend.monthly': 'Monthly',
      'dash.legend.average': 'Average',
      'dash.mini.carry': 'Carry Trade',
      'dash.mini.velocity': 'Dollar Velocity',
      'dash.mini.monetary': 'Monetary Base',
      'dash.signals': 'Risk Signals',
      'map.signals': 'Macro Signals',
      'map.event_types': 'Event Types',
      'map.type.economic': 'Economic',
      'map.type.labor': 'Labor',
      'map.type.regulatory': 'Regulatory',
      'map.type.political': 'Political',
      'map.type.climate': 'Climate',
      'map.type.news': 'Informational',
      'map.stat.risk': 'Country Risk',
      'map.stat.spread': 'Spread %',
      'map.stat.events': 'Events',
      'merc.title': 'Markets',
      'merc.kpi.spread': 'Blue Spread',
      'merc.kpi.carry': 'Blue Carry Trade',
      'merc.kpi.reserves': 'BCRA Reserves',
      'merc.cotiz': 'Exchange Rates',
      'merc.th.type': 'Type',
      'merc.th.buy': 'Buy',
      'merc.th.sell': 'Sell',
      'merc.th.spread': 'Spread',
      'merc.th.change': 'Change',
      'merc.th.updated': 'Updated',
      'merc.bcra': 'BCRA Variables',
      'merc.carry': 'Carry Trade',
      'merc.rates': 'Rates & Policy',
      'config.title': 'Settings',
      'config.save': 'Save',
      'config.saving': 'Saving...',
      'config.saved': 'Saved',
      'config.error': 'Error',
      'config.load_error': 'Could not load settings',
      'chat.sub': 'AI-powered — Argentine economic analysis',
      'chat.placeholder': 'Ask something...',
      'live.transcript': 'Transcript',
      'live.alerts': 'Alerts',
      'live.waiting': 'Waiting for broadcast...',
      'live.no_alerts': 'No alerts yet...',
      'live.url_placeholder': 'YouTube Live URL...',
      'live.start': 'Start',
      'live.stop': 'Stop',
      'dyn.updated': 'updated',
      'dyn.convergence': 'convergence',
      'dyn.low_spread': 'low spread',
      'dyn.high_spread': 'high spread',
      'dyn.critical_spread': 'critical spread',
      'dyn.monthly_gain': 'monthly gain',
      'dyn.internationals': 'international',
      'dyn.no_news': 'No news available',
      'dyn.api_connected': 'API connected',
      'dyn.api_error': 'API error',
      'dyn.api_disconnected': 'API disconnected',
    }
  };

  function t(key) {
    var dict = TRANSLATIONS[currentLang] || TRANSLATIONS['es'];
    return (dict && dict[key]) || (TRANSLATIONS['es'] && TRANSLATIONS['es'][key]) || key;
  }

  function applyTranslations() {
    document.querySelectorAll('[data-i18n]').forEach(function (el) {
      var val = t(el.getAttribute('data-i18n'));
      if (val) el.textContent = val;
    });
    document.querySelectorAll('[data-i18n-title]').forEach(function (el) {
      var val = t(el.getAttribute('data-i18n-title'));
      if (val) el.title = val;
    });
    document.querySelectorAll('[data-i18n-placeholder]').forEach(function (el) {
      var val = t(el.getAttribute('data-i18n-placeholder'));
      if (val) el.placeholder = val;
    });
    document.querySelectorAll('[data-i18n-tooltip]').forEach(function (el) {
      var val = t(el.getAttribute('data-i18n-tooltip'));
      if (val) el.setAttribute('data-tooltip', val);
    });
    var langLabel = document.getElementById('lang-label');
    if (langLabel) langLabel.textContent = currentLang === 'es' ? 'EN' : 'ES';
    document.documentElement.lang = currentLang;
  }

  function initLangToggle() {
    var btn = document.getElementById('btn-lang');
    if (!btn) return;
    btn.addEventListener('click', function () {
      currentLang = currentLang === 'es' ? 'en' : 'es';
      localStorage.setItem('nyx_lang', currentLang);
      applyTranslations();
    });
    applyTranslations();
  }

  // ── Helpers ───────────────────────────────────────────────
  function $(sel) { return document.querySelector(sel); }
  function $$(sel) { return document.querySelectorAll(sel); }

  function fmt(n, dec) {
    if (n == null || isNaN(n)) return '--';
    dec = dec != null ? dec : 0;
    return Number(n).toLocaleString('es-AR', { minimumFractionDigits: dec, maximumFractionDigits: dec });
  }

  function fmtARS(n) { return n != null ? '$ ' + fmt(n, 0) : '--'; }

  async function api(path) {
    if (DEMO_MODE) {
      var demoResult = DEMO[path] || null;
      if (!demoResult) {
        // Try matching without query params
        var base = path.split('?')[0];
        for (var key in DEMO) {
          if (key.split('?')[0] === base) { demoResult = DEMO[key]; break; }
        }
      }
      return demoResult;
    }
    try {
      var res = await fetch(API + path);
      if (!res.ok) throw new Error(res.status);
      return await res.json();
    } catch (e) {
      console.warn('[nyx] API error:', path, e.message);
      // Fallback to demo data if available
      if (DEMO[path]) return DEMO[path];
      return null;
    }
  }

  // ── Clock ─────────────────────────────────────────────────
  function updateClock() {
    var el = $('#dash-time');
    if (!el) return;
    var now = new Date();
    el.textContent = now.toLocaleDateString('es-AR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })
      + '  ·  '
      + now.toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' });
  }
  setInterval(updateClock, 30000);
  updateClock();

  // ── Health check ──────────────────────────────────────────
  async function checkAPI() {
    var dot = $('#api-status');
    if (DEMO_MODE) {
      dot.classList.remove('offline');
      dot.classList.add('demo');
      dot.title = 'DEMO MODE \u2014 datos precargados';
      dot.style.background = 'hsl(38, 92%, 50%)';
      return true;
    }
    try {
      var r = await fetch(API + '/', { signal: AbortSignal.timeout(3000) });
      var ok = r.ok;
      dot.classList.toggle('offline', !ok);
      dot.title = ok ? t('dyn.api_connected') : t('dyn.api_error');
      return ok;
    } catch {
      if (Object.keys(DEMO).length > 0) {
        DEMO_MODE = true;
        dot.classList.remove('offline');
        dot.classList.add('demo');
        dot.title = 'DEMO MODE \u2014 datos precargados';
        dot.style.background = 'hsl(38, 92%, 50%)';
        return true;
      }
      dot.classList.add('offline');
      dot.title = t('dyn.api_disconnected');
      return false;
    }
  }
  checkAPI();
  setInterval(checkAPI, 60000);

  // ═══════════════════════════════════════════════════════════
  // NAVIGATION
  // ═══════════════════════════════════════════════════════════

  function navigate(view) {
    if (!view || view === currentView) return;

    // Hide all views
    $$('.nyx-view').forEach(function (v) { v.classList.remove('active'); });
    $$('.nyx-sidebar__item').forEach(function (b) { b.classList.remove('active'); });

    // Show target
    var target = $('#view-' + view);
    if (target) target.classList.add('active');

    var btn = document.querySelector('[data-view="' + view + '"].nyx-sidebar__item');
    if (btn) btn.classList.add('active');

    currentView = view;

    // Lazy init
    if (view === 'map' && !cache._mapInit) initMap();
    if (view === 'mercados' && !cache._mercadosLoaded) loadMercados();
    if (view === 'noticias' && !cache._noticiasLoaded) loadNoticias();
  }

  // Sidebar click handlers
  $$('.nyx-sidebar__item').forEach(function (btn) {
    btn.addEventListener('click', function () { navigate(btn.dataset.view); });
  });

  // Logo click
  var logo = $('.nyx-sidebar__logo');
  if (logo) logo.addEventListener('click', function () { navigate('dashboard'); });

  // ═══════════════════════════════════════════════════════════
  // MINI CHART ENGINE (canvas-based, no dependencies)
  // ═══════════════════════════════════════════════════════════

  // ── Smooth curve helper (cardinal spline) ──────────────────
  function drawSmoothLine(ctx, points, tension) {
    tension = tension || 0.3;
    if (points.length < 2) return;
    if (points.length === 2) {
      ctx.moveTo(points[0].x, points[0].y);
      ctx.lineTo(points[1].x, points[1].y);
      return;
    }
    ctx.moveTo(points[0].x, points[0].y);
    for (var i = 0; i < points.length - 1; i++) {
      var p0 = points[Math.max(i - 1, 0)];
      var p1 = points[i];
      var p2 = points[i + 1];
      var p3 = points[Math.min(i + 2, points.length - 1)];
      var cp1x = p1.x + (p2.x - p0.x) * tension;
      var cp1y = p1.y + (p2.y - p0.y) * tension;
      var cp2x = p2.x - (p3.x - p1.x) * tension;
      var cp2y = p2.y - (p3.y - p1.y) * tension;
      ctx.bezierCurveTo(cp1x, cp1y, cp2x, cp2y, p2.x, p2.y);
    }
  }

  // ── Fintech Line Chart ────────────────────────────────────
  function drawLineChart(canvasId, datasets, opts) {
    var canvas = document.getElementById(canvasId);
    if (!canvas) return;
    var ctx = canvas.getContext('2d');
    var rect = canvas.parentElement.getBoundingClientRect();
    var dpr = window.devicePixelRatio || 1;
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    canvas.style.width = rect.width + 'px';
    canvas.style.height = rect.height + 'px';
    ctx.scale(dpr, dpr);

    var w = rect.width;
    var h = rect.height;
    var pad = { top: 18, right: 12, bottom: 28, left: 50 };
    var cw = w - pad.left - pad.right;
    var ch = h - pad.top - pad.bottom;

    var allVals = [];
    datasets.forEach(function (ds) { allVals = allVals.concat(ds.data); });
    var minV = opts.minV != null ? opts.minV : Math.min.apply(null, allVals);
    var maxV = opts.maxV != null ? opts.maxV : Math.max.apply(null, allVals);
    var range = maxV - minV || 1;
    minV -= range * 0.05;
    maxV += range * 0.05;
    range = maxV - minV;

    var maxLen = 0;
    datasets.forEach(function (ds) { if (ds.data.length > maxLen) maxLen = ds.data.length; });

    function xPos(i) { return pad.left + (i / Math.max(maxLen - 1, 1)) * cw; }
    function yPos(v) { return pad.top + (1 - (v - minV) / range) * ch; }

    ctx.clearRect(0, 0, w, h);

    // Horizontal grid — dashed, subtle
    var gridCount = 5;
    ctx.setLineDash([2, 4]);
    for (var g = 0; g <= gridCount; g++) {
      var gy = pad.top + (g / gridCount) * ch;
      ctx.strokeStyle = 'rgba(255,255,255,0.04)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(pad.left, gy);
      ctx.lineTo(pad.left + cw, gy);
      ctx.stroke();

      var val = maxV - (g / gridCount) * range;
      ctx.fillStyle = 'rgba(255,255,255,0.22)';
      ctx.font = '10px "JetBrains Mono", monospace';
      ctx.textAlign = 'right';
      ctx.fillText(fmt(val, opts.decimals || 0), pad.left - 8, gy + 3);
    }
    ctx.setLineDash([]);

    // X-axis labels
    if (opts.labels && opts.labels.length) {
      ctx.fillStyle = 'rgba(255,255,255,0.18)';
      ctx.font = '9px "JetBrains Mono", monospace';
      ctx.textAlign = 'center';
      var step = Math.max(1, Math.floor(opts.labels.length / 6));
      for (var li = 0; li < opts.labels.length; li += step) {
        ctx.fillText(opts.labels[li], xPos(li), h - 6);
      }
    }

    // Draw each dataset
    datasets.forEach(function (ds) {
      if (!ds.data.length) return;

      // Build points
      var pts = [];
      for (var pi = 0; pi < ds.data.length; pi++) {
        pts.push({ x: xPos(pi), y: yPos(ds.data[pi]) });
      }

      // Area gradient fill
      if (ds.fill) {
        var grad = ctx.createLinearGradient(0, pad.top, 0, pad.top + ch);
        grad.addColorStop(0, ds.color.replace('hsl(', 'hsla(').replace(')', ', 0.18)'));
        grad.addColorStop(0.6, ds.color.replace('hsl(', 'hsla(').replace(')', ', 0.04)'));
        grad.addColorStop(1, 'transparent');
        ctx.beginPath();
        drawSmoothLine(ctx, pts, 0.25);
        ctx.lineTo(pts[pts.length - 1].x, pad.top + ch);
        ctx.lineTo(pts[0].x, pad.top + ch);
        ctx.closePath();
        ctx.fillStyle = grad;
        ctx.fill();
      }

      // Smooth curve
      ctx.beginPath();
      drawSmoothLine(ctx, pts, 0.25);
      ctx.strokeStyle = ds.color;
      ctx.lineWidth = 2;
      ctx.lineJoin = 'round';
      ctx.lineCap = 'round';
      ctx.stroke();

      // End dot (latest value)
      if (pts.length > 0) {
        var lastPt = pts[pts.length - 1];
        ctx.beginPath();
        ctx.arc(lastPt.x, lastPt.y, 3, 0, Math.PI * 2);
        ctx.fillStyle = ds.color;
        ctx.fill();
        ctx.beginPath();
        ctx.arc(lastPt.x, lastPt.y, 6, 0, Math.PI * 2);
        ctx.fillStyle = ds.color.replace('hsl(', 'hsla(').replace(')', ', 0.15)');
        ctx.fill();
      }
    });

    // Store chart info for hover tooltip
    canvas._nyxChart = { datasets: datasets, xPos: xPos, yPos: yPos, pad: pad, maxLen: maxLen, minV: minV, range: range, w: w, h: h, cw: cw, ch: ch };
    if (!canvas._nyxHover) {
      canvas._nyxHover = true;
      canvas.addEventListener('mousemove', chartHover);
      canvas.addEventListener('mouseleave', function () {
        var c = this._nyxChart;
        if (!c) return;
        var cx = this.getContext('2d');
        drawLineChart(canvasId, c.datasets, opts);
      });
    }
  }

  function chartHover(e) {
    var canvas = e.target;
    var c = canvas._nyxChart;
    if (!c || !c.datasets.length) return;
    var rect = canvas.getBoundingClientRect();
    var mx = e.clientX - rect.left;
    var my = e.clientY - rect.top;
    if (mx < c.pad.left || mx > c.pad.left + c.cw) return;

    var idx = Math.round(((mx - c.pad.left) / c.cw) * (c.maxLen - 1));
    idx = Math.max(0, Math.min(c.maxLen - 1, idx));
    var sx = c.xPos(idx);

    var ctx = canvas.getContext('2d');
    var dpr = window.devicePixelRatio || 1;
    ctx.save();
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    // Redraw base (quick: just draw crosshair overlay)
    // Vertical crosshair line
    ctx.strokeStyle = 'rgba(139, 92, 246, 0.25)';
    ctx.lineWidth = 1;
    ctx.setLineDash([3, 3]);
    ctx.beginPath();
    ctx.moveTo(sx, c.pad.top);
    ctx.lineTo(sx, c.pad.top + c.ch);
    ctx.stroke();
    ctx.setLineDash([]);

    // Value dots at crosshair
    c.datasets.forEach(function (ds) {
      if (idx >= ds.data.length) return;
      var vy = c.yPos(ds.data[idx]);
      ctx.beginPath();
      ctx.arc(sx, vy, 4, 0, Math.PI * 2);
      ctx.fillStyle = ds.color;
      ctx.fill();
      ctx.beginPath();
      ctx.arc(sx, vy, 7, 0, Math.PI * 2);
      ctx.fillStyle = ds.color.replace('hsl(', 'hsla(').replace(')', ', 0.2)');
      ctx.fill();

      // Tooltip value
      ctx.fillStyle = '#fff';
      ctx.font = 'bold 11px "JetBrains Mono", monospace';
      ctx.textAlign = sx > c.w / 2 ? 'right' : 'left';
      var tx = sx > c.w / 2 ? sx - 12 : sx + 12;
      ctx.fillText(fmt(ds.data[idx], 0), tx, vy - 8);
    });
    ctx.restore();
  }

  // ── Fintech Bar Chart ─────────────────────────────────────
  function drawBarChart(canvasId, data, opts) {
    var canvas = document.getElementById(canvasId);
    if (!canvas) return;
    var ctx = canvas.getContext('2d');
    var rect = canvas.parentElement.getBoundingClientRect();
    var dpr = window.devicePixelRatio || 1;
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    canvas.style.width = rect.width + 'px';
    canvas.style.height = rect.height + 'px';
    ctx.scale(dpr, dpr);

    var w = rect.width;
    var h = rect.height;
    var pad = { top: 20, right: 12, bottom: 28, left: 40 };
    var cw = w - pad.left - pad.right;
    var ch = h - pad.top - pad.bottom;

    var maxV = Math.max.apply(null, data.map(function (d) { return d.value; })) * 1.15;

    ctx.clearRect(0, 0, w, h);

    // Subtle horizontal grid
    ctx.setLineDash([2, 4]);
    ctx.strokeStyle = 'rgba(255,255,255,0.03)';
    ctx.lineWidth = 1;
    for (var g = 1; g <= 3; g++) {
      var gy = pad.top + (g / 4) * ch;
      ctx.beginPath();
      ctx.moveTo(pad.left, gy);
      ctx.lineTo(pad.left + cw, gy);
      ctx.stroke();
    }
    ctx.setLineDash([]);

    var totalBarSpace = cw / data.length;
    var barW = Math.min(28, totalBarSpace * 0.55);
    var barX = function (i) { return pad.left + totalBarSpace * i + (totalBarSpace - barW) / 2; };

    data.forEach(function (d, i) {
      var x = barX(i);
      var barH = (d.value / maxV) * ch;
      var y = pad.top + ch - barH;
      var r = Math.min(3, barW / 2);

      // Glow under bar
      ctx.fillStyle = 'hsla(268, 70%, 58%, 0.06)';
      ctx.beginPath();
      ctx.ellipse(x + barW / 2, pad.top + ch, barW * 0.8, 4, 0, 0, Math.PI * 2);
      ctx.fill();

      // Bar gradient
      var grad = ctx.createLinearGradient(x, y, x, pad.top + ch);
      grad.addColorStop(0, 'hsl(268, 75%, 62%)');
      grad.addColorStop(0.5, 'hsl(268, 65%, 52%)');
      grad.addColorStop(1, 'hsl(268, 45%, 30%)');
      ctx.fillStyle = grad;

      // Rounded top bar
      ctx.beginPath();
      ctx.moveTo(x, pad.top + ch);
      ctx.lineTo(x, y + r);
      ctx.arcTo(x, y, x + r, y, r);
      ctx.arcTo(x + barW, y, x + barW, y + r, r);
      ctx.lineTo(x + barW, pad.top + ch);
      ctx.closePath();
      ctx.fill();

      // Top highlight stripe
      ctx.fillStyle = 'rgba(255,255,255,0.08)';
      ctx.fillRect(x + 1, y, barW - 2, Math.min(4, barH));

      // Value label
      ctx.fillStyle = 'rgba(255,255,255,0.45)';
      ctx.font = '9px "JetBrains Mono", monospace';
      ctx.textAlign = 'center';
      ctx.fillText(fmt(d.value, 1) + '%', x + barW / 2, y - 5);

      // X-axis label
      ctx.fillStyle = 'rgba(255,255,255,0.18)';
      ctx.fillText(d.label || '', x + barW / 2, h - 6);
    });
  }

  function drawSparkline(containerId, data, color) {
    var container = document.getElementById(containerId);
    if (!container || !data || data.length < 2) return;

    var w = container.offsetWidth || 120;
    var h = 32;
    var minV = Math.min.apply(null, data);
    var maxV = Math.max.apply(null, data);
    var range = maxV - minV || 1;

    function x(i) { return (i / (data.length - 1)) * w; }
    function y(v) { return h - ((v - minV) / range) * (h - 6) - 3; }

    // Build smooth SVG path (cubic bezier)
    var pts = data.map(function (v, i) { return { x: x(i), y: y(v) }; });
    var d = 'M' + pts[0].x + ',' + pts[0].y;
    for (var i = 0; i < pts.length - 1; i++) {
      var p0 = pts[Math.max(i - 1, 0)];
      var p1 = pts[i];
      var p2 = pts[i + 1];
      var p3 = pts[Math.min(i + 2, pts.length - 1)];
      var t = 0.25;
      var cp1x = p1.x + (p2.x - p0.x) * t;
      var cp1y = p1.y + (p2.y - p0.y) * t;
      var cp2x = p2.x - (p3.x - p1.x) * t;
      var cp2y = p2.y - (p3.y - p1.y) * t;
      d += ' C' + cp1x.toFixed(1) + ',' + cp1y.toFixed(1) + ' ' + cp2x.toFixed(1) + ',' + cp2y.toFixed(1) + ' ' + p2.x.toFixed(1) + ',' + p2.y.toFixed(1);
    }

    var areaD = d + ' L' + w + ',' + h + ' L0,' + h + ' Z';
    var lastPt = pts[pts.length - 1];

    container.innerHTML =
      '<svg width="' + w + '" height="' + h + '" viewBox="0 0 ' + w + ' ' + h + '">' +
      '<defs><linearGradient id="sg-' + containerId + '" x1="0" x2="0" y1="0" y2="1">' +
      '<stop offset="0%" stop-color="' + color + '" stop-opacity="0.15"/>' +
      '<stop offset="100%" stop-color="' + color + '" stop-opacity="0"/>' +
      '</linearGradient></defs>' +
      '<path d="' + areaD + '" fill="url(#sg-' + containerId + ')"/>' +
      '<path d="' + d + '" fill="none" stroke="' + color + '" stroke-width="1.5" stroke-linecap="round"/>' +
      '<circle cx="' + lastPt.x.toFixed(1) + '" cy="' + lastPt.y.toFixed(1) + '" r="2.5" fill="' + color + '"/>' +
      '<circle cx="' + lastPt.x.toFixed(1) + '" cy="' + lastPt.y.toFixed(1) + '" r="5" fill="' + color + '" opacity="0.15"/>' +
      '</svg>';
  }

  // ── Count-up animation for KPI values ─────────────────────
  function animateValue(el, endVal, prefix, suffix, decimals) {
    if (!el) return;
    prefix = prefix || '';
    suffix = suffix || '';
    decimals = decimals || 0;
    var start = 0;
    var duration = 600;
    var startTime = null;
    function step(ts) {
      if (!startTime) startTime = ts;
      var progress = Math.min((ts - startTime) / duration, 1);
      var ease = 1 - Math.pow(1 - progress, 3); // easeOutCubic
      var current = start + (endVal - start) * ease;
      el.textContent = prefix + fmt(current, decimals) + suffix;
      if (progress < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  // ═══════════════════════════════════════════════════════════
  // DASHBOARD
  // ═══════════════════════════════════════════════════════════

  async function loadDashboard() {
    // Fire all requests in parallel
    var [dolar, riesgo, inflacion, reservas, signals, eventos, indiceNyx, analisis] = await Promise.all([
      api('/dolar'),
      api('/riesgo-pais/historial?dias=90'),
      api('/inflacion?meses=12'),
      api('/reservas'),
      api('/signals'),
      api('/eventos'),
      api('/analisis/indice-nyx'),
      api('/analisis/resumen'),
    ]);

    cache.dolar = dolar;
    cache.riesgo = riesgo;
    cache.inflacion = inflacion;
    cache.reservas = reservas;
    cache.signals = signals;
    cache.eventos = eventos;
    cache.indiceNyx = indiceNyx;
    cache.resumenAnalisis = analisis;

    // ── KPI: Dolar Blue ──
    if (dolar) {
      var blue = null;
      if (Array.isArray(dolar)) blue = dolar.find(function (d) { return d.nombre === 'Blue' || d.casa === 'blue'; });
      else if (dolar.blue) blue = dolar.blue;
      else if (dolar.venta) blue = dolar;

      if (blue) {
        var venta = blue.venta || blue.valor_venta || blue.value;
        animateValue($('#kpi-dolar'), venta, '$ ', '', 0);
        $('#map-stat-dolar').textContent = fmtARS(venta);
      }
    }

    // Load dolar history for sparkline + chart
    var dolarHist = await api('/dolar/historial/blue?dias=90');
    cache.dolarHist = dolarHist;
    if (dolarHist && Array.isArray(dolarHist) && dolarHist.length > 1) {
      var vals = dolarHist.map(function (d) { return d.venta || d.valor_venta || d.value || 0; });
      drawSparkline('kpi-dolar-spark', vals.slice(-14), 'hsl(268, 70%, 58%)');

      var last = vals[vals.length - 1];
      var prev = vals[vals.length - 2];
      if (last && prev) {
        var pctD = ((last - prev) / prev * 100).toFixed(1);
        var el = $('#kpi-dolar-change');
        el.className = 'kpi__change ' + (pctD >= 0 ? 'up' : 'down');
        el.textContent = (pctD >= 0 ? '+' : '') + pctD + '%';
      }
    }

    // Dolar chart (blue vs oficial vs MEP) + BADLAR history for sparkline
    var [dolarOficial, dolarMEP, badlarHist] = await Promise.all([
      api('/dolar/historial/oficial?dias=90'),
      api('/dolar/historial/bolsa?dias=90'),
      api('/bcra/badlar'),
    ]);
    if (dolarHist) {
      var blueVals = (Array.isArray(dolarHist) ? dolarHist : []).map(function (d) { return d.venta || d.valor_venta || d.value || 0; });
      var ofVals = (Array.isArray(dolarOficial) ? dolarOficial : []).map(function (d) { return d.venta || d.valor_venta || d.value || 0; });
      var mepVals = (Array.isArray(dolarMEP) ? dolarMEP : []).map(function (d) { return d.venta || d.valor_venta || d.value || 0; });
      var labels = (Array.isArray(dolarHist) ? dolarHist : []).map(function (d) {
        if (!d.fecha) return '';
        var parts = d.fecha.split('-');
        return parts.length >= 3 ? parts[2] + '/' + parts[1] : d.fecha;
      });

      var dolarDatasets = [
        { data: blueVals, color: 'hsl(268, 70%, 58%)', fill: true },
      ];
      if (ofVals.length) dolarDatasets.push({ data: ofVals, color: 'hsl(192, 80%, 50%)', fill: false });
      if (mepVals.length) dolarDatasets.push({ data: mepVals, color: 'hsl(38, 92%, 50%)', fill: false });

      drawLineChart('chart-dolar', dolarDatasets, { labels: labels });
    }

    // ── KPI: Riesgo Pais ──
    if (riesgo && Array.isArray(riesgo) && riesgo.length) {
      var lastR = riesgo[riesgo.length - 1];
      var rVal = lastR.valor || lastR.value || lastR;
      animateValue($('#kpi-riesgo'), rVal, '', '', 0);
      $('#map-stat-riesgo').textContent = fmt(rVal);

      var rVals = riesgo.map(function (d) { return d.valor || d.value || d; });
      drawSparkline('kpi-riesgo-spark', rVals.slice(-14), 'hsl(0, 78%, 58%)');

      if (rVals.length >= 2) {
        var pctR = ((rVals[rVals.length - 1] - rVals[rVals.length - 2]) / rVals[rVals.length - 2] * 100).toFixed(1);
        var elR = $('#kpi-riesgo-change');
        elR.className = 'kpi__change ' + (pctR <= 0 ? 'up' : 'down');
        elR.textContent = (pctR >= 0 ? '+' : '') + pctR + '%';
      }
    } else if (typeof riesgo === 'object' && riesgo && (riesgo.valor || riesgo.value)) {
      var rv = riesgo.valor || riesgo.value;
      $('#kpi-riesgo').textContent = fmt(rv);
      $('#map-stat-riesgo').textContent = fmt(rv);
    }

    // ── KPI: Inflacion ──
    if (inflacion && Array.isArray(inflacion) && inflacion.length) {
      var lastI = inflacion[inflacion.length - 1];
      var iVal = lastI.valor || lastI.value || lastI;
      animateValue($('#kpi-inflacion'), iVal, '', '%', 1);

      // Inflacion bar chart
      var monthNames = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
      var barData = inflacion.slice(-12).map(function (d) {
        var label = '';
        if (d.fecha) {
          var m = parseInt(d.fecha.split('-')[1]) - 1;
          label = monthNames[m] || '';
        } else if (d.mes) {
          label = monthNames[(d.mes - 1) % 12] || '';
        }
        return { value: d.valor || d.value || d, label: label };
      });
      drawBarChart('chart-inflacion', barData);

      // Stat context: pico vs actual
      var infStat = $('#inflacion-stat');
      if (infStat) {
        var iAvg = (barData.reduce(function (s, d) { return s + d.value; }, 0) / barData.length);
        infStat.textContent = 'prom 12m: ' + fmt(iAvg, 1) + '%';
      }
    }

    // ── Riesgo Pais dashboard chart ──
    if (riesgo && Array.isArray(riesgo) && riesgo.length) {
      var rValsAll = riesgo.map(function (d) { return d.valor || d.value || d; });
      var rLabels = riesgo.map(function (d) {
        if (!d.fecha) return '';
        var parts = d.fecha.split('-');
        return parts.length >= 3 ? parts[2] + '/' + parts[1] : d.fecha;
      });
      drawLineChart('chart-riesgo-dash', [
        { data: rValsAll, color: 'hsl(0, 78%, 58%)', fill: true },
      ], { labels: rLabels });

      // Stat: var 7d and zona
      var rLast = rValsAll[rValsAll.length - 1];
      var rPrev7 = rValsAll.length >= 7 ? rValsAll[rValsAll.length - 7] : rValsAll[0];
      var r7pct = rPrev7 ? ((rLast - rPrev7) / rPrev7 * 100).toFixed(1) : null;
      var rDashStat = $('#riesgo-dash-stat');
      if (rDashStat && r7pct != null) {
        rDashStat.textContent = '7d: ' + (r7pct >= 0 ? '+' : '') + r7pct + '%';
        rDashStat.style.color = r7pct <= 0 ? 'hsl(var(--success))' : 'hsl(var(--destructive))';
      }
    }

    // ── KPI: Reservas ──
    if (reservas) {
      var rsvVal = reservas.valor || reservas.value || (Array.isArray(reservas) ? reservas[reservas.length - 1] : null);
      if (rsvVal != null) {
        if (rsvVal > 1e9) {
          $('#kpi-reservas').textContent = 'USD ' + fmt(rsvVal / 1e9, 1) + 'B';
        } else if (rsvVal > 1e6) {
          $('#kpi-reservas').textContent = 'USD ' + fmt(rsvVal / 1e6, 0) + 'M';
        } else if (rsvVal > 1e3) {
          // BCRA reports in millions of USD
          $('#kpi-reservas').textContent = 'USD ' + fmt(rsvVal / 1e3, 1) + 'B';
        } else {
          $('#kpi-reservas').textContent = fmt(rsvVal);
        }
      }
    }

    // ── Signals ──
    renderSignals(signals);

    // ── Indice Nyx widget ──
    if (indiceNyx) {
      var score = indiceNyx.score || 0;
      var nivel = indiceNyx.nivel || (score >= 65 ? 'alto' : score >= 45 ? 'moderado' : 'bajo');
      var colorMap2 = { critico: 'hsl(var(--destructive))', alto: 'hsl(var(--warning))', moderado: 'hsl(268,70%,58%)', bajo: 'hsl(var(--success))', muy_bajo: 'hsl(var(--success))' };
      var nyxColor = colorMap2[nivel] || 'hsl(268,70%,58%)';
      var scoreEl = $('#nyx-idx-score');
      if (scoreEl) { animateValue(scoreEl, score, '', '', 0); scoreEl.style.color = nyxColor; }
      var fillEl = $('#nyx-idx-fill');
      if (fillEl) setTimeout(function () { fillEl.style.width = score + '%'; fillEl.style.background = nyxColor; fillEl.style.boxShadow = '0 0 8px ' + nyxColor; }, 120);
      var nivelEl = $('#nyx-idx-nivel');
      if (nivelEl) { nivelEl.textContent = nivel.toUpperCase(); nivelEl.style.color = nyxColor; }
      cache.nyxAlertas = indiceNyx.alertas || [];
    }

    // ── Brecha KPI ──
    if (signals && signals.brecha_cambiaria) {
      var brecha = signals.brecha_cambiaria.brecha_pct || signals.brecha_cambiaria.value;
      if (brecha != null) {
        $('#kpi-brecha').textContent = fmt(brecha, 1) + '%';
        $('#map-stat-brecha').textContent = fmt(brecha, 1) + '%';
        var brechaChEl = $('#kpi-brecha-change');
        if (brechaChEl) {
          var brechaLvl = Math.abs(brecha) < 5 ? t('dyn.convergence') : Math.abs(brecha) < 20 ? t('dyn.low_spread') : Math.abs(brecha) < 40 ? t('dyn.high_spread') : t('dyn.critical_spread');
          var brechaOk = Math.abs(brecha) < 20;
          brechaChEl.className = 'kpi__change ' + (brechaOk ? 'up' : 'down');
          brechaChEl.textContent = brechaLvl;
        }
      }
    }

    // ── BADLAR KPI ──
    var bv = signals && signals.tasa_real && signals.tasa_real.badlar != null
      ? signals.tasa_real.badlar
      : null;
    var tasaReal = signals && signals.tasa_real && signals.tasa_real.tasa_real != null
      ? signals.tasa_real.tasa_real
      : null;
    if (bv != null) {
      animateValue($('#kpi-badlar'), bv, '', '%', 1);
      var badlarChEl = $('#kpi-badlar-change');
      if (badlarChEl) {
        if (tasaReal != null) {
          var trPositive = tasaReal >= 0;
          badlarChEl.className = 'kpi__change ' + (trPositive ? 'up' : 'down');
          badlarChEl.textContent = 'real: ' + (trPositive ? '+' : '') + fmt(tasaReal, 1) + '%';
        } else {
          badlarChEl.className = 'kpi__change';
          badlarChEl.textContent = 'TNA';
        }
      }
    }
    // BADLAR sparkline — usa historial o simula desde valor actual
    if (badlarHist) {
      var bVals = Array.isArray(badlarHist)
        ? badlarHist.map(function (d) { return d.valor || d.value || 0; })
        : (badlarHist.valor != null ? [badlarHist.valor] : []);
      if (bVals.length >= 2) {
        drawSparkline('kpi-badlar-spark', bVals.slice(-14), 'hsl(268, 42%, 62%)');
      }
    }

    // ── Agent Insights widget ──
    renderInsights(indiceNyx, analisis, signals);

    // ── Event count for map stat ──
    if (eventos && Array.isArray(eventos)) {
      $('#map-stat-eventos').textContent = eventos.length;
    }

    // ── Mini context cards + News feed (parallel) ──
    var [noticias, sentiment, velocidad, monetario] = await Promise.all([
      api('/noticias'),
      api('/analisis/sentiment'),
      api('/analisis/dolar/velocidad'),
      api('/analisis/monetario'),
    ]);
    cache.noticias = noticias;
    renderDashNews(noticias);
    renderMiniSentiment(sentiment);
    renderMiniCarry(signals);
    renderMiniVelocidad(velocidad);
    renderMiniMonetario(monetario);
  }

  // ── Mini card renderers ──────────────────────────────────

  function miniRow(name, val, cls) {
    return '<div class="mini-row">'
      + '<span class="mini-row__name">' + name + '</span>'
      + '<span class="mini-row__val ' + (cls || '') + '">' + val + '</span>'
      + '</div>';
  }

  function renderMiniSentiment(s) {
    if (!s) return;
    // ── Mini card (Row 4) ──
    var toneEl = $('#mini-sent-tone');
    var subEl  = $('#mini-sent-sub');
    var negEl  = $('#mini-sent-neg');
    var posEl  = $('#mini-sent-pos');
    var topEl  = $('#mini-sent-topics');

    var toneMap = {
      pesimista: { label: 'Pesimista', color: 'hsl(var(--destructive))' },
      optimista: { label: 'Optimista', color: 'hsl(var(--success))' },
      positivo:  { label: 'Positivo',  color: 'hsl(var(--success))' },
      neutro:    { label: 'Neutro',    color: 'hsl(var(--muted-foreground))' },
    };
    var t = toneMap[(s.tono || '').toLowerCase()] || { label: s.tono || '--', color: 'hsl(var(--muted-foreground))' };

    if (toneEl) { toneEl.textContent = t.label; toneEl.style.color = t.color; }

    var total = (s.positivos || 0) + (s.negativos || 0) + (s.neutros || 0);
    if (subEl) subEl.textContent = fmt(s.total_tweets) + ' tweets analizados';

    if (negEl && posEl && total) {
      var negPct = ((s.negativos || 0) / total * 100).toFixed(1);
      var posPct = ((s.positivos || 0) / total * 100).toFixed(1);
      negEl.style.width = negPct + '%';
      posEl.style.width = posPct + '%';
    }

    if (topEl && s.volumen_por_tema) {
      var topics = Object.entries(s.volumen_por_tema)
        .sort(function (a, b) { return b[1] - a[1]; })
        .slice(0, 4);
      topEl.innerHTML = topics.map(function (kv) {
        return '<span class="mini-topic">' + kv[0].replace(/_/g, ' ') + ' ' + fmt(kv[1]) + '</span>';
      }).join('');
    }

    // ── Hero card (reemplaza Nyx Index) ──
    renderSentimentHero(s);
    cache.sentiment = s;
  }

  function renderSentimentHero(s) {
    if (!s) return;
    var toneMap = {
      pesimista: { label: 'Pesimista', color: 'hsl(var(--destructive))' },
      optimista: { label: 'Optimista', color: 'hsl(var(--success))' },
      positivo:  { label: 'Positivo',  color: 'hsl(var(--success))' },
      neutro:    { label: 'Neutro',    color: 'hsl(var(--muted-foreground))' },
    };
    var t = toneMap[(s.tono || '').toLowerCase()] || { label: s.tono || '--', color: 'hsl(268,70%,58%)' };

    var tonoEl = $('#sent-hero-tono');
    if (tonoEl) { tonoEl.textContent = t.label; tonoEl.style.color = t.color; }

    var total = (s.positivos || 0) + (s.negativos || 0) + (s.neutros || 0);
    var negEl = $('#sent-hero-neg');
    var posEl = $('#sent-hero-pos');
    if (negEl && posEl && total) {
      setTimeout(function () {
        negEl.style.width = ((s.negativos || 0) / total * 100).toFixed(1) + '%';
        posEl.style.width = ((s.positivos || 0) / total * 100).toFixed(1) + '%';
      }, 120);
    }

    var metaEl = $('#sent-hero-meta');
    if (metaEl) metaEl.textContent = fmt(s.total_tweets) + ' tweets analizados';

    var topicsEl = $('#sent-hero-topics');
    if (topicsEl && s.volumen_por_tema) {
      var topics = Object.entries(s.volumen_por_tema)
        .sort(function (a, b) { return b[1] - a[1]; })
        .slice(0, 5);
      topicsEl.innerHTML = topics.map(function (kv) {
        return '<span class="sent-topic">' + escapeHtml(kv[0].replace(/_/g, ' ')) + '</span>';
      }).join('');
    }
  }

  function renderMiniSignals(signals) {
    var rowsEl = $('#mini-signals-rows');
    if (!rowsEl || !signals) return;

    var items = [
      { key: 'presion_cambiaria', name: 'Presion Cambiaria', getValue: function(s) { return s.score; }, suffix: '/100',
        severity: function(v) {
          return v >= 75 ? { label: 'Critico', c: 'hsl(var(--destructive))' }
               : v >= 50 ? { label: 'Alto',    c: 'hsl(var(--warning))' }
               : v >= 25 ? { label: 'Moderado',c: 'hsl(192,80%,50%)' }
               :            { label: 'Bajo',    c: 'hsl(var(--success))' };
        }, hasBar: true },
      { key: 'brecha_cambiaria', name: 'Brecha Cambiaria', getValue: function(s) { return s.brecha_pct; }, suffix: '%',
        severity: function(v) {
          var a = Math.abs(v);
          return a >= 40 ? { label: 'Critico', c: 'hsl(var(--destructive))' }
               : a >= 20 ? { label: 'Alto',    c: 'hsl(var(--warning))' }
               : a >= 5  ? { label: 'Moderado',c: 'hsl(192,80%,50%)' }
               :            { label: 'Bajo',    c: 'hsl(var(--success))' };
        } },
      { key: 'tasa_real', name: 'Tasa Real', getValue: function(s) { return s.tasa_real; }, suffix: '%',
        severity: function(v) {
          return v < -5  ? { label: 'Negativa', c: 'hsl(var(--destructive))' }
               : v < 0   ? { label: 'Negativa', c: 'hsl(var(--warning))' }
               :            { label: 'Positiva', c: 'hsl(var(--success))' };
        } },
      { key: 'tendencia_reservas', name: 'Reservas 30d', getValue: function(s) { return s.cambio_usd_mm; }, suffix: ' MM',
        severity: function(v, s) {
          return s.tendencia === 'baja' ? { label: 'Baja',  c: 'hsl(var(--warning))' }
               : s.tendencia === 'sube' ? { label: 'Sube',  c: 'hsl(var(--success))' }
               :                          { label: 'Estable',c: 'hsl(var(--muted-foreground))' };
        } },
    ];

    var html = '';
    items.forEach(function(item) {
      var sig = signals[item.key];
      if (!sig) return;
      var val = item.getValue(sig);
      if (val == null) return;
      var sev = item.severity(val, sig);
      var barHtml = '';
      if (item.hasBar) {
        var pct = Math.min(100, Math.max(0, val));
        barHtml = '<div class="mini-signal__bar"><div class="mini-signal__bar-fill" style="width:' + pct + '%;background:' + sev.c + '"></div></div>';
      }
      html += '<div class="mini-signal-row">'
        + '<span class="mini-signal__name">' + item.name + '</span>'
        + '<span class="mini-signal__val">' + (val > 0 && item.suffix === ' MM' ? '+' : '') + fmt(val, 1) + item.suffix + '</span>'
        + '<span class="mini-signal__badge" style="color:' + sev.c + '">' + sev.label + '</span>'
        + barHtml
        + '</div>';
    });

    rowsEl.innerHTML = html || '<div class="mini-card__sub">Sin datos</div>';
  }

  function renderMiniCarry(signals) {
    var valEl = $('#mini-carry-val');
    var subEl = $('#mini-carry-sub');
    var rowsEl = $('#mini-carry-rows');
    if (!valEl || !signals || !signals.tasa_real) return;

    var tr = signals.tasa_real;
    var badlar = tr.badlar != null ? tr.badlar : null;
    var realRate = tr.tasa_real != null ? tr.tasa_real : null;
    var infl = tr.inflacion_12m != null ? tr.inflacion_12m : null;

    if (badlar != null) {
      valEl.textContent = fmt(badlar, 1) + '% TNA';
      valEl.style.color = 'hsl(var(--foreground))';
    }
    if (subEl && realRate != null) {
      subEl.textContent = 'Tasa real: ' + fmt(realRate, 1) + '%' + (realRate < 0 ? ' — negativa' : ' — positiva');
      subEl.style.color = realRate < 0 ? 'hsl(var(--destructive) / 0.7)' : 'hsl(var(--success) / 0.7)';
    }
    if (rowsEl) {
      var html = '';
      if (badlar != null)    html += miniRow('BADLAR TNA', fmt(badlar, 1) + '%', '');
      if (infl != null)      html += miniRow('Inflacion 12m', fmt(infl, 1) + '%', 'warn');
      if (realRate != null)  html += miniRow('Tasa real', fmt(realRate, 1) + '%', realRate >= 0 ? 'up' : 'down');
      rowsEl.innerHTML = html;
    }
  }

  function renderMiniVelocidad(v) {
    var valEl  = $('#mini-vel-val');
    var subEl  = $('#mini-vel-sub');
    var rowsEl = $('#mini-vel-rows');
    if (!valEl || !v || !v.blue) return;

    var b = v.blue;
    var tend = b.tendencia || '--';
    valEl.textContent = tend.charAt(0).toUpperCase() + tend.slice(1);
    valEl.style.color = tend === 'baja' ? 'hsl(var(--success))' : tend === 'sube' ? 'hsl(var(--destructive))' : 'hsl(var(--muted-foreground))';

    if (subEl) subEl.textContent = '90d: ' + (b.var_90d_pct > 0 ? '+' : '') + fmt(b.var_90d_pct, 1) + '% · vol ' + fmt(b.volatilidad_diaria_pct, 2) + '%/d';

    if (rowsEl) {
      var html = '';
      if (b.var_7d_pct != null)  html += miniRow('Var 7d',  (b.var_7d_pct  >= 0 ? '+' : '') + fmt(b.var_7d_pct,  1) + '%', b.var_7d_pct  <= 0 ? 'up' : 'down');
      if (b.var_30d_pct != null) html += miniRow('Var 30d', (b.var_30d_pct >= 0 ? '+' : '') + fmt(b.var_30d_pct, 1) + '%', b.var_30d_pct <= 0 ? 'up' : 'down');
      if (b.max_90d != null)     html += miniRow('Max 90d', '$ ' + fmt(b.max_90d), '');
      if (b.min_90d != null)     html += miniRow('Min 90d', '$ ' + fmt(b.min_90d), '');
      rowsEl.innerHTML = html;
    }
  }

  function renderMiniMonetario(m) {
    var valEl  = $('#mini-mon-val');
    var subEl  = $('#mini-mon-sub');
    var rowsEl = $('#mini-mon-rows');
    if (!valEl || !m || !m.expansion) return;

    var exp = m.expansion;
    var varPct = exp.base_monetaria_var_pct;
    valEl.textContent = (varPct > 0 ? '+' : '') + fmt(varPct, 1) + '%';
    valEl.style.color = varPct < 0 ? 'hsl(var(--success))' : 'hsl(var(--warning))';

    if (subEl) subEl.textContent = exp.interpretacion || '';

    if (rowsEl && m.depositos_tendencia) {
      var dt = m.depositos_tendencia;
      var html = '';
      html += miniRow('Base monetaria', (varPct > 0 ? '+' : '') + fmt(varPct, 1) + '%', varPct <= 0 ? 'up' : 'warn');
      html += miniRow('Inflacion acum ' + exp.periodo_meses + 'm', '+' + fmt(exp.inflacion_acum_pct, 1) + '%', 'warn');
      if (dt.privados) html += miniRow('Depositos priv', (dt.privados.cambio_pct >= 0 ? '+' : '') + fmt(dt.privados.cambio_pct, 1) + '%', dt.privados.cambio_pct >= 0 ? 'up' : 'down');
      rowsEl.innerHTML = html;
    }
  }


  // ═══════════════════════════════════════════════════════════
  // ALERT TICKER ENGINE
  // ═══════════════════════════════════════════════════════════

  var ASVG = {
    up:    '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="18 15 12 9 6 15"/></svg>',
    down:  '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>',
    alert: '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
    info:  '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>',
    trend: '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/></svg>',
    shield:'<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
  };
  var ACLR = {
    critical: 'hsl(var(--destructive))',
    warning:  'hsl(var(--warning))',
    positive: 'hsl(var(--success))',
    info:     'hsl(268,70%,58%)',
    neutral:  'hsl(var(--muted-foreground))',
  };

  var _tickerTimer = null;
  var _tickerProgress = null;
  var _tickerIdx = 0;
  var _tickerAlerts = [];
  var TICKER_INTERVAL = 5000; // ms per alert

  function buildAlertItem(alert) {
    // alert: { icon, category, text, type }
    var color = ACLR[alert.type] || ACLR.neutral;
    var plainText = (alert.text || '').replace(/<[^>]+>/g, '');
    var askQ = 'Analizame en detalle: ' + alert.category + ' — ' + plainText.substring(0, 220);
    return '<div class="alert-ticker__item" style="--insight-color:' + color + '">'
      + '<span class="alert-ticker__icon">' + (ASVG[alert.icon] || ASVG.info) + '</span>'
      + '<div class="alert-ticker__body">'
      + '<div class="alert-ticker__category">' + escapeHtml(alert.category) + '</div>'
      + '<div class="alert-ticker__text">' + alert.text + '</div>'
      + '</div>'
      + askBtn(askQ, alert.category)
      + '</div>';
  }

  function tickerGoTo(idx) {
    var container = $('#dash-insights-list');
    if (!container) return;
    var items = container.querySelectorAll('.alert-ticker__item');
    if (!items.length) return;

    var prev = _tickerIdx;
    _tickerIdx = ((idx % items.length) + items.length) % items.length;

    // Animate out prev
    if (items[prev] && prev !== _tickerIdx) {
      items[prev].classList.remove('active');
      items[prev].classList.add('exit');
      setTimeout(function () {
        if (items[prev]) items[prev].classList.remove('exit');
      }, 300);
    }

    // Animate in next
    if (items[_tickerIdx]) {
      items[_tickerIdx].classList.add('active');
    }

    // Update counter
    var counterEl = $('#alert-counter');
    if (counterEl) counterEl.textContent = (_tickerIdx + 1) + ' / ' + items.length;

    // Update dots
    var dots = document.querySelectorAll('.alert-ticker__dot');
    dots.forEach(function (d, i) { d.classList.toggle('active', i === _tickerIdx); });

    // Reset progress bar
    resetTickerProgress();
  }

  function resetTickerProgress() {
    if (_tickerProgress) {
      _tickerProgress.style.transition = 'none';
      _tickerProgress.style.width = '0%';
      // Force reflow then animate
      _tickerProgress.getBoundingClientRect();
      _tickerProgress.style.transition = 'width ' + TICKER_INTERVAL + 'ms linear';
      _tickerProgress.style.width = '100%';
    }
  }

  function startAlertTicker(alerts) {
    // Stop any existing ticker
    if (_tickerTimer) clearInterval(_tickerTimer);
    _tickerAlerts = alerts;
    _tickerIdx = 0;

    // Expose globally so drawer can build the expanded panel
    window.nyxAlerts = alerts;

    var container = $('#dash-insights-list');
    var navEl = $('#alert-ticker-nav');
    if (!container) return;

    // Build all items
    container.innerHTML = alerts.map(buildAlertItem).join('');

    // Show first item
    var items = container.querySelectorAll('.alert-ticker__item');
    if (items[0]) items[0].classList.add('active');

    // Build nav dots + progress bar
    if (navEl) {
      var dotsHtml = '';
      alerts.forEach(function (_, i) {
        dotsHtml += '<span class="alert-ticker__dot' + (i === 0 ? ' active' : '') + '" data-i="' + i + '"></span>';
      });
      dotsHtml += '<div class="alert-ticker__progress"><div class="alert-ticker__progress-fill" id="ticker-progress-fill"></div></div>';
      navEl.innerHTML = dotsHtml;

      // Dot click handlers
      navEl.querySelectorAll('.alert-ticker__dot').forEach(function (dot) {
        dot.addEventListener('click', function () {
          if (_tickerTimer) clearInterval(_tickerTimer);
          tickerGoTo(parseInt(dot.dataset.i));
          _tickerTimer = setInterval(function () { tickerGoTo(_tickerIdx + 1); }, TICKER_INTERVAL);
        });
      });
    }

    _tickerProgress = $('#ticker-progress-fill');

    // Set counter
    var counterEl = $('#alert-counter');
    if (counterEl) counterEl.textContent = '1 / ' + alerts.length;

    // Single alert — no need for ticker
    if (alerts.length <= 1) return;

    resetTickerProgress();
    _tickerTimer = setInterval(function () { tickerGoTo(_tickerIdx + 1); }, TICKER_INTERVAL);
  }

  // Build rich alert objects from data
  function renderInsights(nyx, analisis, signals) {
    var alerts = [];

    // 1. Presion cambiaria (highest priority)
    if (signals && signals.presion_cambiaria) {
      var pc = signals.presion_cambiaria;
      var pcScore = pc.score != null ? pc.score : pc.value;
      if (pcScore != null) {
        var pcSev = pcScore >= 75 ? 'critical' : pcScore >= 50 ? 'warning' : pcScore >= 25 ? 'info' : 'positive';
        var pcVerb = pcScore >= 75 ? 'Presion cambiaria <strong>critica</strong> —' : pcScore >= 50 ? 'Presion cambiaria <strong>elevada</strong> —' : 'Presion cambiaria <strong>moderada</strong> —';
        var pcTip = pcScore >= 75 ? ' posible movimiento de tipo de cambio inminente.'
          : pcScore >= 50 ? ' monitorear reservas y brecha en proximas 48hs.'
          : pcScore >= 25 ? ' condiciones de estres leve en el mercado cambiario.'
          : ' mercado cambiario estable, spread bajo control.';
        alerts.push({ icon: pcScore >= 50 ? 'alert' : 'shield', category: 'Presion Cambiaria · ' + fmt(pcScore, 0) + '/100', text: pcVerb + pcTip, type: pcSev });
      }
    }

    // 2. Nyx alertas directas
    if (nyx && nyx.alertas && nyx.alertas.length) {
      nyx.alertas.forEach(function (a) {
        alerts.push({ icon: 'alert', category: 'Indice Nyx', text: escapeHtml(a), type: 'warning' });
      });
    }

    // 3. Brecha cambiaria
    if (signals && signals.brecha_cambiaria) {
      var br = signals.brecha_cambiaria;
      var b = br.brecha_pct != null ? br.brecha_pct : br.value;
      if (b != null) {
        var bSev = Math.abs(b) < 5 ? 'positive' : Math.abs(b) < 20 ? 'info' : Math.abs(b) < 40 ? 'warning' : 'critical';
        var bMsg = Math.abs(b) < 5
          ? 'Brecha Blue/Oficial en <strong>' + fmt(b, 1) + '%</strong> — convergencia cambiaria sostenida, ancla de precios efectiva.'
          : Math.abs(b) < 20
          ? 'Brecha Blue/Oficial en <strong>' + fmt(b, 1) + '%</strong> — spread manejable, vigilar señales de presion.'
          : Math.abs(b) < 40
          ? 'Brecha Blue/Oficial en <strong>' + fmt(b, 1) + '%</strong> — spread significativo, posible tension en expectativas de devaluacion.'
          : 'Brecha Blue/Oficial en <strong>' + fmt(b, 1) + '%</strong> — nivel de alerta elevado, mercado desconfiado del tipo de cambio oficial.';
        alerts.push({ icon: Math.abs(b) < 20 ? 'trend' : 'alert', category: 'Tipo de Cambio', text: bMsg, type: bSev });
      }
    }

    // 4. Tasa real
    if (signals && signals.tasa_real) {
      var tr = signals.tasa_real;
      var r = tr.tasa_real != null ? tr.tasa_real : (tr.tasa_real_pct != null ? tr.tasa_real_pct : tr.value);
      if (r != null) {
        var rSev = r < -5 ? 'critical' : r < 0 ? 'warning' : 'positive';
        var rMsg = r < -5
          ? 'Tasa real <strong>' + fmt(r, 1) + '%</strong> — terreno muy negativo, deterioro del ahorro en pesos y presion sobre inflacion.'
          : r < 0
          ? 'Tasa real <strong>' + fmt(r, 1) + '%</strong> — negativa, el peso pierde poder de compra frente a la inflacion.'
          : 'Tasa real <strong>' + fmt(r, 1) + '%</strong> — positiva, el ahorro en pesos es rentable. Condicion pro-estabilizacion.';
        alerts.push({ icon: r >= 0 ? 'up' : 'down', category: 'Tasas · Politica Monetaria', text: rMsg, type: rSev });
      }
    }

    // 5. Tendencia reservas
    if (signals && signals.tendencia_reservas) {
      var res = signals.tendencia_reservas;
      if (res.tendencia) {
        var resSev = res.tendencia === 'sube' ? 'positive' : res.tendencia === 'baja' ? 'warning' : 'neutral';
        var resDiff = res.cambio_usd_mm != null ? ' (<strong>' + (res.cambio_usd_mm > 0 ? '+' : '') + fmt(res.cambio_usd_mm, 0) + ' MM USD</strong> en 30d)' : '';
        var resMsg = res.tendencia === 'sube'
          ? 'Reservas en tendencia <strong>alcista</strong>' + resDiff + ' — acumulacion de divisas, señal positiva para la estabilidad.'
          : res.tendencia === 'baja'
          ? 'Reservas en tendencia <strong>bajista</strong>' + resDiff + ' — caida de divisas, monitorear presion sobre el tipo de cambio.'
          : 'Reservas <strong>estables</strong>' + resDiff + ' — sin variacion significativa en el ultimo mes.';
        alerts.push({ icon: res.tendencia === 'sube' ? 'up' : res.tendencia === 'baja' ? 'down' : 'info', category: 'Reservas BCRA', text: resMsg, type: resSev });
      }
    }

    // 6. Carry trade / crawling peg from resumen
    var resumen = '';
    if (analisis) resumen = analisis.resumen || analisis.texto || '';
    var carryM = resumen.match(/CARRY TRADE[:\s]+(.{15,90})/i);
    if (carryM) alerts.push({ icon: 'trend', category: 'Carry Trade', text: escapeHtml(carryM[1].trim().replace(/\|.*/g, '')), type: 'info' });
    var crawlM = resumen.match(/CRAWLING PEG[:\s]+(.{15,90})/i);
    if (crawlM) alerts.push({ icon: 'trend', category: 'Crawling Peg', text: escapeHtml(crawlM[1].trim().replace(/\|.*/g, '')), type: 'neutral' });

    // Fallback
    if (!alerts.length) {
      alerts.push({ icon: 'info', category: 'Sistema', text: 'Motor de analisis cargando datos...', type: 'neutral' });
    }

    startAlertTicker(alerts);
  }

  function renderSignals(signals) {
    var container = $('#signals-list');
    if (!container || !signals) return;

    var items = [
      { key: 'presion_cambiaria', name: 'Presion Cambiaria', max: 100 },
      { key: 'brecha_cambiaria', name: 'Brecha Cambiaria', suffix: '%' },
      { key: 'tasa_real', name: 'Tasa Real', suffix: '%' },
      { key: 'tendencia_reservas', name: 'Tendencia Reservas', suffix: '%' },
    ];

    var html = '';
    items.forEach(function (item) {
      var sig = signals[item.key];
      if (!sig) return;

      var val = sig.score != null ? sig.score : (sig.brecha_pct != null ? sig.brecha_pct : (sig.tasa_real_pct != null ? sig.tasa_real_pct : (sig.variacion_pct != null ? sig.variacion_pct : sig.value)));
      if (val == null) return;

      var severity = 'low';
      if (item.key === 'presion_cambiaria') {
        if (val >= 75) severity = 'critical';
        else if (val >= 50) severity = 'high';
        else if (val >= 25) severity = 'moderate';
      } else if (item.key === 'brecha_cambiaria') {
        if (Math.abs(val) >= 80) severity = 'critical';
        else if (Math.abs(val) >= 40) severity = 'high';
        else if (Math.abs(val) >= 20) severity = 'moderate';
      }

      var severityLabel = severity === 'critical' ? 'Critico' : severity === 'high' ? 'Alto' : severity === 'moderate' ? 'Moderado' : 'Bajo';

      var askQ = 'Analiza ' + item.name + ' (' + fmt(val, 1) + (item.suffix || '') + ', ' + severityLabel + ')';

      html += '<div class="signal-row">'
        + '<span class="signal-row__name">' + item.name + '</span>'
        + '<span class="signal-row__value">' + fmt(val, 1) + (item.suffix || '') + '</span>'
        + '<span class="signal-badge ' + severity + '">' + severityLabel + '</span>';

      if (item.max) {
        var pct = Math.min(100, Math.max(0, (val / item.max) * 100));
        var barColor = severity === 'critical' ? 'hsl(var(--destructive))' : severity === 'high' ? 'hsl(var(--warning))' : severity === 'moderate' ? 'hsl(var(--signal-political))' : 'hsl(var(--success))';
        html += '<div class="signal-row__bar"><div class="signal-row__bar-fill" style="width:' + pct + '%;background:' + barColor + '"></div></div>';
      }

      html += askBtn(askQ, item.name + ' ' + fmt(val, 1) + (item.suffix || '')) + '</div>';
    });

    container.innerHTML = html;

    // Also update map signals
    renderMapSignals(signals);
  }

  function renderMapSignals(signals) {
    var container = $('#map-signals');
    if (!container || !signals) return;

    var html = '<div class="map-signals__title">Senales Macro</div>';
    var items = [
      { key: 'presion_cambiaria', name: 'Presion Cambiaria', field: 'score' },
      { key: 'brecha_cambiaria', name: 'Brecha', field: 'brecha_pct', suffix: '%' },
      { key: 'tasa_real', name: 'Tasa Real', field: 'tasa_real_pct', suffix: '%' },
      { key: 'tendencia_reservas', name: 'Reservas', field: 'variacion_pct', suffix: '%' },
    ];

    items.forEach(function (item) {
      var sig = signals[item.key];
      if (!sig) return;
      var val = sig[item.field] != null ? sig[item.field] : sig.value;
      if (val == null) return;

      var color = val < 0 ? 'hsl(var(--destructive))' : 'hsl(var(--success))';
      if (item.key === 'presion_cambiaria') {
        color = val >= 50 ? 'hsl(var(--destructive))' : 'hsl(var(--success))';
      }

      html += '<div class="map-signal-item">'
        + '<span class="map-signal-item__label">' + item.name + '</span>'
        + '<span class="map-signal-item__value" style="color:' + color + '">'
        + fmt(val, 1) + (item.suffix || '')
        + '</span></div>';
    });

    container.innerHTML = html;
  }

  function renderDashNews(noticias) {
    var container = $('#dash-news');
    if (!container) return;
    if (!noticias || !Array.isArray(noticias) || !noticias.length) {
      container.innerHTML = '<div class="empty-state">' + t('dyn.no_news') + '</div>';
      return;
    }

    var typeColors = {
      economico: 'type-economico',
      sindical: 'type-sindical',
      regulatorio: 'type-regulatorio',
      politico: 'type-politico',
      climatico: 'type-climatico',
      informativo: 'type-informativo'
    };

    var html = '';
    var items = noticias.slice(0, 12);
    items.forEach(function (n) {
      var tipo = (n.tipo || n.type || 'informativo').toLowerCase();
      var cls = typeColors[tipo] || 'type-informativo';
      var fuente = n.fuente || n.source || '';
      var fecha = n.fecha || n.date || '';

      var headline = n.titulo || n.title || '';

      html += '<div class="news-item">'
        + '<div class="news-item__type ' + cls + '"></div>'
        + '<div class="news-item__body">'
        + '<div class="news-item__headline">' + escapeHtml(headline) + '</div>'
        + '<div class="news-item__meta">' + escapeHtml(fuente) + (fecha ? ' · ' + fecha : '') + '</div>'
        + '</div>'
        + askBtn('Explica esta noticia: ' + headline, headline.substring(0, 50))
        + '</div>';
    });

    container.innerHTML = html;
  }

  // ═══════════════════════════════════════════════════════════
  // MERCADOS
  // ═══════════════════════════════════════════════════════════

  // Helper: mercados data row
  function mrow(label, value) {
    return '<div class="merc-data-row">'
      + '<span class="merc-data-row__label">' + label + '</span>'
      + '<span class="merc-data-row__value">' + value + '</span>'
      + '</div>';
  }

  async function loadMercados() {
    cache._mercadosLoaded = true;

    // Fire all in parallel
    var [dolar, riesgoHist, bcraArr, carry, crawl, tasas, resAnal, signals] = await Promise.all([
      api('/dolar'),
      api('/riesgo-pais/historial?dias=30'),
      Promise.all([api('/bcra/badlar'), api('/bcra/tm20'), api('/bcra/base_monetaria')]),
      api('/analisis/carry-trade/multi'),
      api('/analisis/dolar/crawling-peg'),
      api('/analisis/tasa-politica'),
      api('/analisis/reservas'),
      cache.signals ? Promise.resolve(cache.signals) : api('/signals'),
    ]);

    // ── KPI strip ──
    // Brecha
    if (signals && signals.brecha_cambiaria) {
      var br = signals.brecha_cambiaria.brecha_pct != null ? signals.brecha_cambiaria.brecha_pct : signals.brecha_cambiaria.value;
      if (br != null) {
        var brechaEl = $('#mkpi-brecha');
        if (brechaEl) { brechaEl.textContent = fmt(br, 1) + '%'; brechaEl.style.color = Math.abs(br) < 5 ? 'hsl(var(--success))' : Math.abs(br) < 40 ? 'hsl(var(--warning))' : 'hsl(var(--destructive))'; }
        var brechaSubEl = $('#mkpi-brecha-sub');
        if (brechaSubEl) {
          brechaSubEl.textContent = Math.abs(br) < 5 ? t('dyn.convergence') : Math.abs(br) < 20 ? t('dyn.low_spread') : Math.abs(br) < 40 ? t('dyn.high_spread') : t('dyn.critical_spread');
          brechaSubEl.style.color = Math.abs(br) < 20 ? 'hsl(var(--success))' : Math.abs(br) < 40 ? 'hsl(var(--warning))' : 'hsl(var(--destructive))';
        }
      }
    }

    // Carry trade
    if (carry && carry.blue && carry.blue.ganancia_carry_pct != null) {
      var carryEl = $('#mkpi-carry');
      var carryVal = carry.blue.ganancia_carry_pct;
      if (carryEl) { carryEl.textContent = (carryVal > 0 ? '+' : '') + fmt(carryVal, 2) + '%'; carryEl.style.color = carryVal > 0 ? 'hsl(var(--success))' : 'hsl(var(--destructive))'; }
      var carrySubEl = $('#mkpi-carry-sub');
      if (carrySubEl) carrySubEl.style.color = carryVal > 0 ? 'hsl(var(--success))' : 'hsl(var(--destructive))';
    }

    // Crawling peg
    if (crawl && crawl.tasa_mensual_pct != null) {
      var crawlEl = $('#mkpi-crawling');
      if (crawlEl) crawlEl.textContent = fmt(crawl.tasa_mensual_pct, 2) + '%';
    }

    // BADLAR — /bcra/badlar retorna null, usar signals.tasa_real.badlar
    var [badlar, tm20, baseMon] = bcraArr;
    var bv = null;
    if (badlar) bv = badlar.valor || badlar.value || (Array.isArray(badlar) && badlar.length ? badlar[badlar.length - 1].valor || badlar[badlar.length - 1].value : null);
    if (bv == null && signals && signals.tasa_real && signals.tasa_real.badlar != null) bv = signals.tasa_real.badlar;
    if (bv != null) {
      var badlarEl = $('#mkpi-badlar2');
      if (badlarEl) {
        badlarEl.textContent = fmt(bv, 1) + '%';
        // Mostrar tasa real debajo si está disponible
        var realMerc = signals && signals.tasa_real && signals.tasa_real.tasa_real != null ? signals.tasa_real.tasa_real : null;
        var badlarSubEl = badlarEl.nextElementSibling;
        if (badlarSubEl && realMerc != null) {
          badlarSubEl.textContent = 'real: ' + (realMerc >= 0 ? '+' : '') + fmt(realMerc, 1) + '%';
          badlarSubEl.style.color = realMerc >= 0 ? 'hsl(var(--success))' : 'hsl(var(--destructive))';
        }
      }
    }

    // Reservas
    if (resAnal) {
      var rv = resAnal.actual_usd_mm || resAnal.actual;
      if (rv != null) {
        var rsvEl = $('#mkpi-reservas2');
        if (rsvEl) rsvEl.textContent = 'USD ' + fmt(rv, 0) + 'MM';
        var rsvSubEl = $('#mkpi-reservas-sub');
        if (rsvSubEl && resAnal.tendencia) {
          rsvSubEl.textContent = resAnal.tendencia;
          rsvSubEl.style.color = resAnal.tendencia === 'acumulando' ? 'hsl(var(--success))' : 'hsl(var(--destructive))';
        }
      }
    }

    // ── Cotizaciones table ──
    if (dolar) {
      var rows = Array.isArray(dolar) ? dolar : [dolar];
      var oficialVenta = null;
      rows.forEach(function (d) {
        var casa = (d.casa || d.tipo || '').toLowerCase();
        var nombre = (d.nombre || '').toLowerCase();
        if (casa === 'oficial' || nombre === 'oficial') oficialVenta = d.venta || d.valor_venta || null;
      });

      var html = '';
      rows.forEach(function (d) {
        var nombre = d.nombre || d.casa || d.tipo || 'Dolar';
        var compra = d.compra || d.valor_compra || null;
        var venta = d.venta || d.valor_venta || null;
        var variacion = d.variacion != null ? parseFloat(d.variacion) : null;
        var fecha = (d.fecha_actualizacion || d.fecha || '').substring(0, 10);
        var esCasa = (d.casa || '').toLowerCase();

        var brechaStr = '--';
        var brechaClass = '';
        if (oficialVenta && venta && esCasa !== 'oficial') {
          var bv2 = (venta - oficialVenta) / oficialVenta * 100;
          brechaStr = (bv2 >= 0 ? '+' : '') + fmt(bv2, 1) + '%';
          brechaClass = Math.abs(bv2) > 50 ? 'cotiz-down' : Math.abs(bv2) > 10 ? 'cotiz-warn' : 'cotiz-up';
        }

        html += '<tr>'
          + '<td class="cotiz-tipo">' + escapeHtml(nombre) + '</td>'
          + '<td>' + (compra != null ? fmtARS(compra) : '--') + '</td>'
          + '<td class="cotiz-venta">' + (venta != null ? fmtARS(venta) : '--') + '</td>'
          + '<td class="' + brechaClass + '">' + brechaStr + '</td>'
          + '<td class="' + (variacion != null ? (variacion >= 0 ? 'cotiz-up' : 'cotiz-down') : '') + '">'
          + (variacion != null ? (variacion >= 0 ? '+' : '') + fmt(variacion, 2) + '%' : '--') + '</td>'
          + '<td class="cotiz-date">' + escapeHtml(fecha) + '</td>'
          + '</tr>';
      });
      $('#cotiz-body').innerHTML = html;

      if (rows.length) {
        var updEl = $('#cotiz-updated');
        var ts = rows[0].fecha_actualizacion || rows[0].fecha || '';
        if (updEl && ts) updEl.textContent = t('dyn.updated') + ' ' + ts.substring(0, 10);
      }
    }

    // ── Riesgo chart ──
    if (riesgoHist && Array.isArray(riesgoHist)) {
      var rVals = riesgoHist.map(function (d) { return d.valor || d.value || d; });
      var rLabels = riesgoHist.map(function (d) {
        if (!d.fecha) return '';
        var parts = d.fecha.split('-');
        return parts.length >= 3 ? parts[2] + '/' + parts[1] : '';
      });
      drawLineChart('chart-riesgo', [{ data: rVals, color: 'hsl(0, 78%, 58%)', fill: true }], { labels: rLabels });
    }

    // ── Multi-dollar chart: Blue + MEP + CCL ──
    var [blueHist, mepHist, cclHist] = await Promise.all([
      api('/dolar/historial/blue?dias=30'),
      api('/dolar/historial/bolsa?dias=30'),
      api('/dolar/historial/contadoconliqui?dias=30'),
    ]);
    drawMultiDolar(blueHist, mepHist, cclHist);

    // ── BCRA panel ──
    var bcraHtml = '';
    if (badlar) {
      var bvp = badlar.valor || badlar.value || (Array.isArray(badlar) && badlar.length ? badlar[badlar.length - 1].valor : null);
      if (bvp != null) bcraHtml += mrow('BADLAR', fmt(bvp, 1) + '% TNA');
    }
    if (tm20) {
      var tvp = tm20.valor || tm20.value || (Array.isArray(tm20) && tm20.length ? tm20[tm20.length - 1].valor : null);
      if (tvp != null) bcraHtml += mrow('TM20', fmt(tvp, 1) + '% TNA');
    }
    if (baseMon) {
      var mvp = baseMon.valor || baseMon.value || (Array.isArray(baseMon) && baseMon.length ? baseMon[baseMon.length - 1].valor : null);
      if (mvp != null) {
        var baseStr = mvp > 1e12 ? fmt(mvp / 1e12, 1) + 'T' : mvp > 1e9 ? fmt(mvp / 1e9, 1) + 'B' : fmt(mvp);
        bcraHtml += mrow('Base Monetaria', '$ ' + baseStr);
      }
    }
    if (resAnal) {
      if (resAnal.actual_usd_mm != null) bcraHtml += mrow('Reservas', 'USD ' + fmt(resAnal.actual_usd_mm, 0) + ' MM');
      if (resAnal.usd_por_dia != null) bcraHtml += mrow('Ritmo diario', (resAnal.usd_por_dia > 0 ? '+' : '') + fmt(resAnal.usd_por_dia, 1) + ' MM/dia');
      if (resAnal.tendencia) bcraHtml += mrow('Tendencia', '<span style="color:' + (resAnal.tendencia === 'acumulando' ? 'hsl(var(--success))' : 'hsl(var(--destructive))') + '">' + resAnal.tendencia + '</span>');
      if (resAnal.interpretacion) bcraHtml += '<div class="merc-data-insight">' + escapeHtml(resAnal.interpretacion.substring(0, 130)) + '</div>';
    }
    if (bcraHtml) $('#bcra-panel').innerHTML = bcraHtml;

    // ── Carry Trade panel ──
    var carryHtml = '';
    if (carry) {
      if (carry.mejor_plazo_fijo) {
        var pf = carry.mejor_plazo_fijo;
        if (pf.tna_pct != null) carryHtml += mrow('Mejor plazo fijo', fmt(pf.tna_pct, 1) + '% TNA');
        if (pf.mensual_pct != null) carryHtml += mrow('Retorno mensual', fmt(pf.mensual_pct, 2) + '%');
      }
      ['blue', 'mep', 'ccl'].forEach(function (k) {
        var c = carry[k];
        if (!c || c.ganancia_carry_pct == null) return;
        var gv = c.ganancia_carry_pct;
        var color = gv > 0 ? 'hsl(var(--success))' : 'hsl(var(--destructive))';
        carryHtml += mrow('vs ' + k.toUpperCase(), '<span style="color:' + color + '">' + (gv > 0 ? '+' : '') + fmt(gv, 2) + '%</span>');
      });
      if (carry.interpretacion) carryHtml += '<div class="merc-data-insight">' + escapeHtml(carry.interpretacion.substring(0, 130)) + '</div>';
    }
    if (carryHtml) $('#carry-panel').innerHTML = carryHtml;

    // ── Tasas panel ──
    var tasasHtml = '';
    if (tasas) {
      if (tasas.pases_pasivos != null) tasasHtml += mrow('Pases Pasivos', fmt(tasas.pases_pasivos, 1) + '%');
      if (tasas.badlar != null) tasasHtml += mrow('BADLAR', fmt(tasas.badlar, 1) + '%');
      if (tasas.spread_pases_badlar_pp != null) tasasHtml += mrow('Spread Pases-BADLAR', fmt(tasas.spread_pases_badlar_pp, 2) + 'pp');
      if (tasas.corredor) tasasHtml += mrow('Corredor', fmt(tasas.corredor.piso, 1) + '% – ' + fmt(tasas.corredor.techo, 1) + '%');
      if (tasas.interpretacion) tasasHtml += '<div class="merc-data-insight">' + escapeHtml(tasas.interpretacion.substring(0, 130)) + '</div>';
    }
    if (crawl) {
      if (crawl.tasa_mensual_pct != null) tasasHtml += mrow('Crawling peg mensual', fmt(crawl.tasa_mensual_pct, 2) + '%');
      if (crawl.tasa_anualizada_pct != null) tasasHtml += mrow('Crawling anualizado', fmt(crawl.tasa_anualizada_pct, 1) + '%');
    }
    if (tasasHtml) $('#tasas-panel').innerHTML = tasasHtml;

    // ── KPI card click handlers ──
    $$('.merc-kpi').forEach(function (card) {
      card.addEventListener('click', function () {
        var key = card.dataset.merc;
        if (key === 'brecha' && typeof window.nyxOpenBrecha === 'function') window.nyxOpenBrecha();
        else if ((key === 'badlar' || key === 'carry' || key === 'crawling') && typeof window.nyxOpenBadlar === 'function') window.nyxOpenBadlar();
        else if (key === 'reservas' && typeof window.nyxOpenReservas === 'function') window.nyxOpenReservas();
      });
    });
  }

  function drawMultiDolar(blueHist, mepHist, cclHist) {
    var datasets = [];
    var base = blueHist || mepHist || cclHist || [];
    var labels = (Array.isArray(base) ? base : []).map(function (d) {
      if (!d.fecha) return '';
      var p = d.fecha.split('-');
      return p.length >= 3 ? p[2] + '/' + p[1] : '';
    });
    if (blueHist && Array.isArray(blueHist) && blueHist.length)
      datasets.push({ data: blueHist.map(function (d) { return d.venta || d.valor_venta || 0; }), color: 'hsl(268,70%,58%)', fill: false });
    if (mepHist && Array.isArray(mepHist) && mepHist.length)
      datasets.push({ data: mepHist.map(function (d) { return d.venta || d.valor_venta || 0; }), color: 'hsl(192,80%,50%)', fill: false });
    if (cclHist && Array.isArray(cclHist) && cclHist.length)
      datasets.push({ data: cclHist.map(function (d) { return d.venta || d.valor_venta || 0; }), color: 'hsl(38,92%,55%)', fill: false });
    if (datasets.length) drawLineChart('chart-multidolar', datasets, { labels: labels });
  }

  // ═══════════════════════════════════════════════════════════
  // NOTICIAS
  // ═══════════════════════════════════════════════════════════

  var activeFilter = 'all';

  async function loadNoticias() {
    cache._noticiasLoaded = true;

    var eventos = cache.eventos || await api('/eventos');
    cache.eventos = eventos;

    renderNoticiasGrid(eventos);

    // Filter chips
    $$('#noticias-filters .filter-chip').forEach(function (chip) {
      chip.addEventListener('click', function () {
        $$('#noticias-filters .filter-chip').forEach(function (c) { c.classList.remove('active'); });
        chip.classList.add('active');
        activeFilter = chip.dataset.filter;
        renderNoticiasGrid(cache.eventos);
      });
    });

    // Search
    var searchInput = $('#noticias-search');
    if (searchInput) {
      searchInput.addEventListener('input', function () {
        renderNoticiasGrid(cache.eventos);
      });
    }
  }

  function renderNoticiasGrid(eventos) {
    var container = $('#noticias-grid');
    if (!container) return;
    if (!eventos || !Array.isArray(eventos) || !eventos.length) {
      container.innerHTML = '<div class="empty-state" style="grid-column:1/-1">Sin eventos disponibles</div>';
      return;
    }

    var searchTerm = ($('#noticias-search') || {}).value || '';
    searchTerm = searchTerm.toLowerCase().trim();

    var filtered = eventos.filter(function (e) {
      var tipo = (e.tipo || e.type || '').toLowerCase();
      if (activeFilter !== 'all' && tipo !== activeFilter) return false;
      if (searchTerm) {
        var text = ((e.titulo || e.title || '') + ' ' + (e.resumen || e.summary || '')).toLowerCase();
        if (text.indexOf(searchTerm) === -1) return false;
      }
      return true;
    });

    var html = '';
    filtered.slice(0, 30).forEach(function (e) {
      var tipo = (e.tipo || e.type || 'informativo').toLowerCase();
      var urgencia = e.urgencia || e.urgency || 0;
      var urgLabel = urgencia >= 8 ? 'Critico' : urgencia >= 5 ? 'Alto' : urgencia >= 3 ? 'Moderado' : 'Bajo';
      var urgClass = urgencia >= 8 ? 'critical' : urgencia >= 5 ? 'high' : urgencia >= 3 ? 'moderate' : 'low';

      var evTitle = e.titulo || e.title || '';

      html += '<div class="glass-panel noticia-card">'
        + '<div class="noticia-card__top">'
        + '<span class="type-badge ' + tipo + '">' + tipo + '</span>'
        + '<span class="signal-badge ' + urgClass + '">' + urgLabel + '</span>'
        + '</div>'
        + '<div class="noticia-card__title">' + escapeHtml(evTitle) + '</div>'
        + '<div class="noticia-card__summary">' + escapeHtml(e.resumen || e.summary || '') + '</div>'
        + '<div class="noticia-card__footer">'
        + '<span class="noticia-card__source">' + escapeHtml(e.fuente || e.source || '') + '</span>';

      if (e.activos && e.activos.length) {
        e.activos.slice(0, 3).forEach(function (a) {
          html += '<span class="type-badge informativo" style="font-size:8px">' + escapeHtml(a) + '</span>';
        });
      }

      html += askBtn('Analiza este evento (' + tipo + '): ' + evTitle, evTitle.substring(0, 50));
      html += '</div></div>';
    });

    container.innerHTML = html;
  }

  // ═══════════════════════════════════════════════════════════
  // FLOATING CHAT — "Ask Nyx"
  // ═══════════════════════════════════════════════════════════

  var agentBusy = false;
  var agentHasMessages = false;
  var chatOpen = false;

  function initAgent() {
    var trigger = $('#chatTrigger');
    var triggerWrap = $('.chat-trigger-wrap');
    var panel = $('#chatPanel');
    var backdrop = $('#chatBackdrop');
    var input = $('#agent-input');
    var sendBtn = $('#agent-send');
    var label = $('#chatLabel');
    var iconOpen = $('#chatIconOpen');
    var iconClose = $('#chatIconClose');
    var headerClose = $('#chatHeaderClose');

    trigger.addEventListener('click', toggleChat);
    backdrop.addEventListener('click', toggleChat);
    headerClose.addEventListener('click', toggleChat);

    sendBtn.addEventListener('click', sendAgentMsg);
    input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') sendAgentMsg();
      if (e.key === 'Escape' && chatOpen) toggleChat();
    });

    $$('.chat-suggestion').forEach(function (btn) {
      btn.addEventListener('click', function () {
        if (agentBusy) return;
        input.value = btn.dataset.q;
        sendAgentMsg();
      });
    });

    var citeClose = $('#chat-cite-close');
    if (citeClose) citeClose.addEventListener('click', function () { setCite(null); });

    document.addEventListener('keydown', function (e) {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        toggleChat();
      }
    });

    function toggleChat() {
      chatOpen = !chatOpen;
      panel.classList.toggle('open', chatOpen);
      backdrop.classList.toggle('active', chatOpen);
      // Hide the entire trigger when chat is open — only the header X closes
      triggerWrap.classList.toggle('hidden-by-expand', chatOpen);
      if (chatOpen) setTimeout(function () { input.focus(); }, 100);
    }

    window._nyxToggleChat = toggleChat;
  }

  function openChat() {
    if (!chatOpen && window._nyxToggleChat) window._nyxToggleChat();
  }

  function closeChat() {
    if (chatOpen && window._nyxToggleChat) window._nyxToggleChat();
  }

  function hideWelcome() {
    if (agentHasMessages) return;
    agentHasMessages = true;
    var suggestions = $('#chat-suggestions');
    if (suggestions) {
      suggestions.style.opacity = '0';
      suggestions.style.transition = 'opacity 0.15s';
      setTimeout(function () { suggestions.remove(); }, 180);
    }
    // Expand panel + hide trigger
    var p = $('#chatPanel');
    if (p) p.classList.add('expanded');
    var tw = $('.chat-trigger-wrap');
    if (tw) tw.classList.add('hidden-by-expand');
  }

  async function sendAgentMsg() {
    if (agentBusy) return;
    var input = $('#agent-input');
    var q = input.value.trim();
    if (!q) return;

    if (!chatOpen) openChat();
    hideWelcome();

    input.value = '';
    agentBusy = true;
    $('#agent-send').disabled = true;

    var msgs = $('#agent-messages');

    // User bubble
    var userEl = document.createElement('div');
    userEl.className = 'chat-msg--user';
    userEl.textContent = q;
    msgs.appendChild(userEl);

    // Status indicator (replaces static "analyzing...")
    var statusEl = document.createElement('div');
    statusEl.className = 'chat-msg--system';
    statusEl.textContent = 'connecting...';
    msgs.appendChild(statusEl);
    msgs.scrollTop = msgs.scrollHeight;

    var fullQ = q;
    if (currentCite) {
      fullQ = '[Contexto: ' + currentCite + '] ' + q;
      setCite(null);
    }

    // Demo mode — no backend available
    if (DEMO_MODE) {
      statusEl.remove();
      var demoReply = '### Modo Demo\n\nEsta es una **demo estatica** desplegada en GitHub Pages. El agente AI requiere el backend con la API de Claude.\n\n'
        + '- **Dolar Blue:** $ ' + ((DEMO['/dolar/blue'] || {}).venta || '--') + '\n'
        + '- **Riesgo Pais:** ' + ((DEMO['/riesgo-pais'] || {}).valor || (DEMO['/riesgo-pais'] || {}).value || '--') + '\n'
        + '- **Brecha:** ' + (((DEMO['/signals'] || {}).brecha_cambiaria || {}).brecha_pct || '--') + '%\n\n'
        + 'Para usar el agente, ejecuta el backend localmente con `python api.py`.';
      appendChatMsg(msgs, 'chat-msg--assistant', demoReply);
      agentBusy = false;
      $('#agent-send').disabled = false;
      msgs.scrollTop = msgs.scrollHeight;
      return;
    }

    fullQ += '\n\n[FORMATO: Responde en 3-5 oraciones maximo por seccion. Sin emojis. Usa ### para headers, **negrita** para datos clave, listas con - para puntos. Maximo 150 palabras. Estilo Bloomberg terminal: datos primero, opinion despues, conciso.]';

    // Try SSE streaming first, fallback to regular endpoint
    try {
      var res = await fetch(API + '/agent/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: fullQ }),
      });

      if (!res.ok) throw new Error('stream-fail');

      // SSE streaming mode
      var reader = res.body.getReader();
      var decoder = new TextDecoder();
      var responseEl = null;
      var fullText = '';
      var toolCount = 0;
      var metaData = null;

      while (true) {
        var result = await reader.read();
        if (result.done) break;

        var lines = decoder.decode(result.value, { stream: true }).split('\n');
        for (var i = 0; i < lines.length; i++) {
          var line = lines[i].trim();
          if (!line.startsWith('data: ')) continue;

          var event;
          try { event = JSON.parse(line.slice(6)); } catch(e) { continue; }

          if (event.type === 'status') {
            statusEl.textContent = event.data;
          }
          else if (event.type === 'tool') {
            toolCount++;
            statusEl.textContent = event.data + ' (' + toolCount + ' tools)';
          }
          else if (event.type === 'chunk') {
            // First chunk — remove status, create response element
            if (!responseEl) {
              statusEl.remove();
              responseEl = document.createElement('div');
              responseEl.className = 'chat-msg--assistant typing';
              msgs.appendChild(responseEl);
            }
            fullText += event.data;
            // Show plain text while streaming, render markdown at end
            responseEl.textContent = fullText;
            msgs.scrollTop = msgs.scrollHeight;
          }
          else if (event.type === 'done') {
            metaData = event.data;
          }
          else if (event.type === 'error') {
            statusEl.remove();
            appendChatMsg(msgs, 'chat-msg--assistant', 'Error: ' + event.data);
          }
        }
      }

      // Streaming done — render final markdown
      if (responseEl && fullText) {
        fullText = stripEmojis(fullText);
        responseEl.classList.remove('typing');
        responseEl.innerHTML = renderMarkdown(fullText);
      }

      // Tools + meta + citations
      if (metaData) {
        if (metaData.tool_calls && metaData.tool_calls.length) {
          // Insert tool cards before the response
          if (responseEl) msgs.insertBefore(renderToolCards(null, metaData.tool_calls), responseEl);
        }
        renderMetaFooter(msgs, metaData);
        if (metaData.citations && metaData.citations.length) {
          renderCitations(msgs, metaData.citations);
        }
      }

    } catch (streamErr) {
      // Fallback to non-streaming endpoint
      try {
        statusEl.textContent = 'analyzing...';
        var res2 = await fetch(API + '/agent/ask', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ question: fullQ }),
        });
        statusEl.remove();

        if (!res2.ok) {
          var err = await res2.json().catch(function () { return {}; });
          appendChatMsg(msgs, 'chat-msg--assistant', 'Error: ' + (err.detail || res2.status));
        } else {
          var data = await res2.json();

          // Render tool cards before the response
          if (data.tool_calls && data.tool_calls.length) {
            renderToolCards(msgs, data.tool_calls);
          }

          // Render response with typewriter
          var text = (data.respuesta || '(sin respuesta)');
          text = stripEmojis(text);
          await typewriterRender(msgs, text);

          // Meta footer + citations
          renderMetaFooter(msgs, data);
          if (data.citations && data.citations.length) {
            renderCitations(msgs, data.citations);
          }
        }
      } catch (e2) {
        statusEl.remove();
        appendChatMsg(msgs, 'chat-msg--assistant', 'No se pudo conectar con la API.');
      }
    }

    agentBusy = false;
    $('#agent-send').disabled = false;
    msgs.scrollTop = msgs.scrollHeight;
    input.focus();
  }

  function appendChatMsg(container, cls, text) {
    var el = document.createElement('div');
    el.className = cls;
    el.textContent = text;
    container.appendChild(el);
  }

  function stripEmojis(text) {
    return text.replace(/[\u{1F600}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{1FA00}-\u{1FA6F}\u{1FA70}-\u{1FAFF}\u{FE00}-\u{FE0F}\u{200D}\u{20E3}\u{E0020}-\u{E007F}]/gu, '').replace(/  +/g, ' ').trim();
  }

  var TOOL_LABELS = {
    consultar_datos: 'Datos economicos',
    consultar_senales: 'Senales de riesgo',
    consultar_noticias: 'Noticias',
    consultar_eventos: 'Eventos',
    consultar_social: 'Redes sociales',
    consultar_analisis: 'Analisis',
    busqueda_web: 'Busqueda web',
    busqueda_twitter: 'Busqueda Twitter',
    buscar_db: 'Base de datos',
    guardar_contexto: 'Guardar contexto',
  };

  // Render tool usage cards
  function renderToolCards(container, toolCalls) {
    var wrap = document.createElement('div');
    wrap.className = 'chat-tools';

    toolCalls.forEach(function (tc) {
      var name = tc.tool || tc.name || tc;
      var label = TOOL_LABELS[name] || name;
      var isLive = tc.live || name === 'busqueda_web' || name === 'busqueda_twitter';
      var inputStr = '';

      if (tc.input) {
        // Show the most relevant input param
        var inp = tc.input;
        if (inp.variable) inputStr = inp.variable;
        else if (inp.query) inputStr = inp.query;
        else if (inp.tipo) inputStr = inp.tipo;
        else if (inp.fuente) inputStr = inp.fuente;
        else if (inp.terminos) inputStr = Array.isArray(inp.terminos) ? inp.terminos.join(', ') : inp.terminos;
        else if (inp.analisis) inputStr = inp.analisis;
        else {
          var keys = Object.keys(inp);
          if (keys.length) inputStr = String(inp[keys[0]]).substring(0, 40);
        }
      }

      var pill = document.createElement('div');
      pill.className = 'chat-tool-pill' + (isLive ? ' chat-tool-pill--live' : '');
      pill.innerHTML = '<span class="chat-tool-pill__icon">'
        + (isLive ? '<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M2 12h20"/><path d="M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z"/></svg>'
                 : '<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>')
        + '</span>'
        + '<span class="chat-tool-pill__name">' + escapeHtml(label) + '</span>'
        + (inputStr ? '<span class="chat-tool-pill__param">' + escapeHtml(inputStr) + '</span>' : '')
        + (tc.cost ? '<span class="chat-tool-pill__cost">$' + tc.cost.toFixed(2) + '</span>' : '');
      wrap.appendChild(pill);
    });

    if (container) {
      container.appendChild(wrap);
    }
    return wrap;
  }

  // Render meta footer
  function renderMetaFooter(container, data) {
    var parts = [];
    if (data.tool_calls && data.tool_calls.length) parts.push(data.tool_calls.length + ' tools');
    if (data.live_calls) parts.push(data.live_calls + ' live');
    if (data.apify_spent) parts.push('$' + data.apify_spent.toFixed(2));
    if (data.elapsed_s) parts.push(data.elapsed_s + 's');
    if (data.model) {
      var m = data.model.replace('claude-', '').replace(/-\d+$/, '');
      parts.push(m);
    }
    if (parts.length) {
      var el = document.createElement('div');
      el.className = 'chat-msg--meta';
      el.textContent = parts.join(' · ');
      container.appendChild(el);
    }
  }

  // ── Simple Markdown → HTML ────────────────────────────────
  function renderMarkdown(text) {
    // Process markdown BEFORE escaping, then sanitize carefully
    // Split into lines for line-level processing
    var lines = text.split('\n');
    var out = [];
    var inList = false;

    for (var li = 0; li < lines.length; li++) {
      var line = lines[li];

      // Headers
      if (/^###\s+(.+)/.test(line)) {
        if (inList) { out.push('</ul>'); inList = false; }
        out.push('<h4>' + escapeHtml(line.replace(/^###\s+/, '')) + '</h4>');
        continue;
      }
      if (/^##\s+(.+)/.test(line)) {
        if (inList) { out.push('</ul>'); inList = false; }
        out.push('<h3>' + escapeHtml(line.replace(/^##\s+/, '')) + '</h3>');
        continue;
      }

      // Horizontal rule
      if (/^---+$/.test(line.trim())) {
        if (inList) { out.push('</ul>'); inList = false; }
        out.push('<hr>');
        continue;
      }

      // List items
      if (/^\s*[-*]\s+(.+)/.test(line)) {
        if (!inList) { out.push('<ul>'); inList = true; }
        var liContent = line.replace(/^\s*[-*]\s+/, '');
        out.push('<li>' + inlineFormat(liContent) + '</li>');
        continue;
      }

      // Close list if open
      if (inList) { out.push('</ul>'); inList = false; }

      // Empty line = paragraph break
      if (line.trim() === '') {
        out.push('<br>');
        continue;
      }

      // Regular text
      out.push('<p>' + inlineFormat(line) + '</p>');
    }

    if (inList) out.push('</ul>');
    return out.join('');
  }

  // Inline formatting: bold, italic, code, links
  function inlineFormat(text) {
    // Handle markdown links [text](url) BEFORE escaping
    var parts = [];
    var linkRe = /\[([^\]]+)\]\((https?:\/\/[^\)]+)\)/g;
    var lastIndex = 0;
    var m;
    while ((m = linkRe.exec(text)) !== null) {
      if (m.index > lastIndex) parts.push(escapeHtml(text.slice(lastIndex, m.index)));
      parts.push('<a href="' + escapeHtml(m[2]) + '" target="_blank" rel="noopener" class="chat-link">' + escapeHtml(m[1]) + '</a>');
      lastIndex = m.index + m[0].length;
    }
    if (lastIndex < text.length) parts.push(escapeHtml(text.slice(lastIndex)));
    var s = parts.join('');
    // Bold (** or __)
    s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    s = s.replace(/__([^_]+)__/g, '<strong>$1</strong>');
    // Italic
    s = s.replace(/\*([^*]+)\*/g, '<em>$1</em>');
    // Inline code
    s = s.replace(/`([^`]+)`/g, '<code>$1</code>');
    return s;
  }

  // Render source citations as clickable chips
  function renderCitations(container, citations) {
    if (!citations || !citations.length) return;
    var wrap = document.createElement('div');
    wrap.className = 'chat-citations';
    var label = document.createElement('span');
    label.className = 'chat-citations__label';
    label.textContent = 'Fuentes';
    wrap.appendChild(label);
    citations.forEach(function(c) {
      var chip = document.createElement('a');
      chip.className = 'chat-citation-chip';
      chip.href = c.url;
      chip.target = '_blank';
      chip.rel = 'noopener';
      var src = (c.fuente || '').replace(/^rss_|^article_|^rag_/i, '').split('_')[0];
      if (!src && c.url) {
        try { src = new URL(c.url).hostname.replace(/^www\./, '').split('.')[0]; } catch(e) {}
      }
      src = src || 'fuente';
      var title = (c.titulo || '').trim();
      chip.innerHTML = '<span class="chat-citation-chip__source">' + escapeHtml(src) + '</span>'
        + '<span class="chat-citation-chip__title">' + escapeHtml(title.slice(0, 55) + (title.length > 55 ? '…' : '')) + '</span>';
      wrap.appendChild(chip);
    });
    container.appendChild(wrap);
  }

  // ── Typewriter effect ─────────────────────────────────────
  function typewriterRender(container, text) {
    return new Promise(function (resolve) {
      var el = document.createElement('div');
      el.className = 'chat-msg--assistant typing';
      container.appendChild(el);

      var words = text.split(/(\s+)/);
      var idx = 0;
      var current = '';
      var speed = 10;

      function tick() {
        if (idx >= words.length) {
          el.classList.remove('typing');
          el.innerHTML = renderMarkdown(text);
          container.scrollTop = container.scrollHeight;
          resolve();
          return;
        }
        var chunk = '';
        for (var c = 0; c < 4 && idx < words.length; c++, idx++) {
          chunk += words[idx];
        }
        current += chunk;
        // Render markdown on every tick so symbols never show
        el.innerHTML = renderMarkdown(current);
        container.scrollTop = container.scrollHeight;
        setTimeout(tick, speed);
      }
      tick();
    });
  }

  // ═══════════════════════════════════════════════════════════
  // MAP (init delegated to nyx-map.js)
  // ═══════════════════════════════════════════════════════════

  function initMap() {
    cache._mapInit = true;
    // nyx-map.js handles this when view becomes active
    if (typeof window.initNyxMap === 'function') {
      window.initNyxMap();
    }
  }

  // ═══════════════════════════════════════════════════════════
  // TIMEFRAME BUTTONS
  // ═══════════════════════════════════════════════════════════

  $$('.timeframe-bar').forEach(function (bar) {
    bar.querySelectorAll('.timeframe-btn').forEach(function (btn) {
      btn.addEventListener('click', async function () {
        bar.querySelectorAll('.timeframe-btn').forEach(function (b) { b.classList.remove('active'); });
        btn.classList.add('active');

        var days = parseInt(btn.dataset.days);
        var chart = bar.dataset.chart;

        if (chart === 'dolar') {
          var [blue, oficial] = await Promise.all([
            api('/dolar/historial/blue?dias=' + days),
            api('/dolar/historial/oficial?dias=' + days),
          ]);
          if (blue && oficial) {
            var bv = blue.map(function (d) { return d.venta || d.valor_venta || d.value || 0; });
            var ov = oficial.map(function (d) { return d.venta || d.valor_venta || d.value || 0; });
            var lb = blue.map(function (d) {
              if (!d.fecha) return '';
              var p = d.fecha.split('-');
              return p.length >= 3 ? p[2] + '/' + p[1] : '';
            });
            drawLineChart('chart-dolar', [
              { data: bv, color: 'hsl(268, 70%, 58%)', fill: true },
              { data: ov, color: 'hsl(192, 80%, 50%)', fill: false },
            ], { labels: lb });
          }
        } else if (chart === 'riesgo') {
          var riesgo = await api('/riesgo-pais/historial?dias=' + days);
          if (riesgo && Array.isArray(riesgo)) {
            var rv = riesgo.map(function (d) { return d.valor || d.value || d; });
            var rl = riesgo.map(function (d) {
              if (!d.fecha) return '';
              var p = d.fecha.split('-');
              return p.length >= 3 ? p[2] + '/' + p[1] : '';
            });
            drawLineChart('chart-riesgo', [
              { data: rv, color: 'hsl(0, 78%, 58%)', fill: true },
            ], { labels: rl });
          }
        } else if (chart === 'multidolar') {
          var [md_blue, md_mep, md_ccl] = await Promise.all([
            api('/dolar/historial/blue?dias=' + days),
            api('/dolar/historial/bolsa?dias=' + days),
            api('/dolar/historial/contadoconliqui?dias=' + days),
          ]);
          drawMultiDolar(md_blue, md_mep, md_ccl);
        }
      });
    });
  });

  // ═══════════════════════════════════════════════════════════
  // RESIZE HANDLER
  // ═══════════════════════════════════════════════════════════

  var resizeTimer;
  window.addEventListener('resize', function () {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(function () {
      // Redraw visible charts
      if (currentView === 'dashboard') loadDashboard();
    }, 300);
  });

  // ═══════════════════════════════════════════════════════════
  // UTILS
  // ═══════════════════════════════════════════════════════════

  function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  // ═══════════════════════════════════════════════════════════
  // CONTEXTUAL "ASK NYX" — query AI about any data point
  // ═══════════════════════════════════════════════════════════

  var ASK_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>';

  function askBtn(question, cite) {
    return '<button class="ask-nyx" data-ask="' + escapeHtml(question) + '" data-cite="' + escapeHtml(cite || '') + '">' + ASK_ICON + '</button>';
  }

  var currentCite = null;

  function setCite(cite) {
    var citeEl = $('#chat-cite');
    var citeText = $('#chat-cite-text');
    if (!citeEl) return;
    if (cite) {
      currentCite = cite;
      citeText.textContent = cite;
      citeEl.classList.add('visible');
    } else {
      currentCite = null;
      citeEl.classList.remove('visible');
    }
  }

  // Close cite
  document.addEventListener('click', function (e) {
    if (e.target.closest('#nyx-cite-close')) {
      setCite(null);
      return;
    }
  });

  // Delegate all .ask-nyx clicks — solo muestra el chip, NO pre-llena el input
  document.addEventListener('click', function (e) {
    var btn = e.target.closest('.ask-nyx');
    if (!btn) return;
    e.stopPropagation();
    var cite = btn.dataset.cite || (btn.dataset.ask || '').substring(0, 40);
    if (!chatOpen) openChat();
    setTimeout(function () {
      setCite(cite);
      var input = $('#agent-input');
      if (input) input.focus();
    }, chatOpen ? 0 : 120);
  });

  // ═══════════════════════════════════════════════════════════
  // BOOT
  // ═══════════════════════════════════════════════════════════

  // Expose for nyx-map.js
  window.nyxCache = cache;
  window.nyxAPI = api;
  window.nyxFmt = fmt;
  window.nyxFmtARS = fmtARS;
  window.nyxEscapeHtml = escapeHtml;
  window.nyxSetCite = setCite;

  loadDashboard();
  initAgent();
  initConfig();
  initDrawer();
  initSidebarToggle();
  initLangToggle();

  // ── Sidebar toggle ────────────────────────────────────────
  function initSidebarToggle() {
    var sidebar = $('.nyx-sidebar');
    var btn     = $('#sidebar-toggle');
    if (!sidebar || !btn) return;

    var SIDEBAR_W = 62; // px, must match CSS
    var collapsed = false;

    function applyState(animate) {
      if (!animate) {
        sidebar.style.transition = 'none';
        btn.style.transition = 'none';
      }
      sidebar.classList.toggle('collapsed', collapsed);
      btn.classList.toggle('collapsed', collapsed);
      btn.title = collapsed ? 'Mostrar panel ( [ )' : 'Ocultar panel ( [ )';
      if (!animate) {
        // Force reflow then restore transitions
        sidebar.getBoundingClientRect();
        btn.getBoundingClientRect();
        sidebar.style.transition = '';
        btn.style.transition = '';
      }
      // Persist preference
      try { localStorage.setItem('nyx_sidebar_collapsed', collapsed ? '1' : '0'); } catch (e) {}
    }

    function toggle() {
      collapsed = !collapsed;
      applyState(true);
    }

    // Restore saved state (no animation on load)
    try {
      if (localStorage.getItem('nyx_sidebar_collapsed') === '1') {
        collapsed = true;
        applyState(false);
      }
    } catch (e) {}

    // Button click
    btn.addEventListener('click', toggle);

    // Keyboard shortcut: [
    document.addEventListener('keydown', function (e) {
      var tag = (e.target || {}).tagName || '';
      if (tag === 'INPUT' || tag === 'TEXTAREA') return;
      if (e.key === '[' && !e.ctrlKey && !e.metaKey && !e.altKey) {
        e.preventDefault();
        toggle();
      }
    });
  }

  // ═══════════════════════════════════════════════════════════
  // DRAWER INIT — alerts panel buttons
  // ═══════════════════════════════════════════════════════════

  function initDrawer() {
    // Expand button → panel with all alerts
    var expandBtn = $('#alerts-expand-btn');
    if (expandBtn) {
      expandBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        if (typeof window.nyxOpenAlerts === 'function') window.nyxOpenAlerts();
      });
    }

    // Ask button → open chat pre-filled with all alerts context
    var askBtn2 = $('#alerts-ask-btn');
    if (askBtn2) {
      askBtn2.addEventListener('click', function (e) {
        e.stopPropagation();
        var alerts = window.nyxAlerts || [];
        var ctx = alerts.map(function (a) {
          return a.category + ': ' + (a.text || '').replace(/<[^>]+>/g, '');
        }).join(' | ');
        var trigger = $('#chatTrigger');
        if (trigger && !$('#chatPanel').classList.contains('open')) trigger.click();
        setTimeout(function () {
          if (typeof window.nyxSetCite === 'function') window.nyxSetCite('Alertas Tempranas');
          var input = $('#agent-input');
          if (input) { input.value = ''; input.focus(); }
        }, 180);
      });
    }
  }

  // ═══════════════════════════════════════════════════════════
  // CONFIG PANEL
  // ═══════════════════════════════════════════════════════════

  function initConfig() {
    var btn = $('#btn-config');
    var panel = $('#config-panel');
    var backdrop = $('#config-backdrop');
    var closeBtn = $('#config-close');
    var saveBtn = $('#config-save');

    if (!btn || !panel) return;

    btn.addEventListener('click', openConfig);
    closeBtn.addEventListener('click', closeConfig);
    backdrop.addEventListener('click', closeConfig);
    saveBtn.addEventListener('click', saveConfig);

    function openConfig() {
      panel.classList.remove('hidden');
      backdrop.classList.remove('hidden');
      loadConfigForm();
    }

    function closeConfig() {
      panel.classList.add('hidden');
      backdrop.classList.add('hidden');
    }

    async function loadConfigForm() {
      var body = $('#config-body');
      body.innerHTML = '<div class="skeleton" style="height:200px"></div>';

      var schema = await api('/config');
      if (!schema || !schema.fields) {
        body.innerHTML = '<p style="color:var(--muted-foreground)">' + t('config.load_error') + '</p>';
        return;
      }

      var groups = schema.groups || {};
      var sortedGroups = Object.entries(groups).sort(function (a, b) { return (a[1].order || 99) - (b[1].order || 99); });

      var html = '';
      sortedGroups.forEach(function (entry) {
        var groupKey = entry[0];
        var groupMeta = entry[1];
        var fields = schema.fields.filter(function (f) { return f.group === groupKey; });
        if (!fields.length) return;

        html += '<div class="config-group">';
        html += '<div class="config-group__title">' + (groupMeta.label || groupKey) + '</div>';

        fields.forEach(function (f) {
          html += '<div class="config-field">';
          html += '<label class="config-field__label">' + f.label + '</label>';

          if (f.type === 'secret') {
            var display = f.is_set ? f.display_value : '';
            html += '<input class="config-field__input" type="password" data-key="' + f.key + '" value="' + escapeHtml(String(f.value || '')) + '" placeholder="' + (f.placeholder || '') + '">';
            if (f.is_set) html += '<span class="config-field__hint">Configurada</span>';
          }
          else if (f.type === 'select' && f.options) {
            html += '<select class="config-field__select" data-key="' + f.key + '">';
            f.options.forEach(function (opt) {
              var sel = opt.value === f.value ? ' selected' : '';
              html += '<option value="' + opt.value + '"' + sel + '>' + opt.label + '</option>';
            });
            html += '</select>';
            var selOpt = f.options.find(function (o) { return o.value === f.value; });
            if (selOpt && selOpt.description) html += '<span class="config-field__hint">' + selOpt.description + '</span>';
          }
          else if (f.type === 'toggle') {
            var checked = f.value ? ' checked' : '';
            html += '<label class="config-toggle"><input type="checkbox" data-key="' + f.key + '"' + checked + '><span class="config-toggle__slider"></span></label>';
          }
          else if (f.type === 'range') {
            html += '<div class="config-range">';
            html += '<input type="range" data-key="' + f.key + '" min="' + (f.min || 0) + '" max="' + (f.max || 1) + '" step="' + (f.step || 0.1) + '" value="' + f.value + '">';
            html += '<span class="config-range__val" id="range-' + f.key + '">' + f.value + '</span>';
            html += '</div>';
          }
          else if (f.type === 'textarea') {
            html += '<textarea class="config-field__textarea" data-key="' + f.key + '" placeholder="' + (f.placeholder || '') + '" rows="3">' + escapeHtml(String(f.value || '')) + '</textarea>';
          }
          else if (f.type === 'number') {
            html += '<input class="config-field__input config-field__input--sm" type="number" data-key="' + f.key + '" value="' + (f.value || '') + '" min="' + (f.min || '') + '" max="' + (f.max || '') + '" step="' + (f.step || 1) + '">';
          }
          else {
            html += '<input class="config-field__input" type="text" data-key="' + f.key + '" value="' + escapeHtml(String(f.value || '')) + '" placeholder="' + (f.placeholder || '') + '">';
          }

          html += '</div>';
        });

        html += '</div>';
      });

      body.innerHTML = html;

      // Wire up range sliders to show value
      body.querySelectorAll('input[type="range"]').forEach(function (r) {
        r.addEventListener('input', function () {
          var valEl = $('#range-' + r.dataset.key);
          if (valEl) valEl.textContent = r.value;
        });
      });
    }

    async function saveConfig() {
      var body = $('#config-body');
      var updates = {};

      body.querySelectorAll('[data-key]').forEach(function (el) {
        var key = el.dataset.key;
        if (el.type === 'checkbox') {
          updates[key] = el.checked;
        } else if (el.type === 'number' || el.type === 'range') {
          updates[key] = parseFloat(el.value);
        } else if (el.type === 'password' && !el.value) {
          // Don't send empty password fields (keep current)
          return;
        } else {
          updates[key] = el.value;
        }
      });

      saveBtn.textContent = t('config.saving');
      try {
        var res = await fetch(API + '/config', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(updates),
        });
        if (res.ok) {
          saveBtn.textContent = t('config.saved');
          setTimeout(function () { saveBtn.textContent = t('config.save'); }, 2000);
        }
      } catch (e) {
        saveBtn.textContent = t('config.error');
        setTimeout(function () { saveBtn.textContent = t('config.save'); }, 2000);
      }
    }
  }

})();
