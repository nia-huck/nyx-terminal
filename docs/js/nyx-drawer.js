/* ═══════════════════════════════════════════════════════════════
   Nyx Terminal — Floating Panel System
   Click any widget → glass overlay panel with deep data
   Click X or backdrop → closes
   ═══════════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  var API = window.NYX_API || 'http://localhost:8000';
  var panelCtx = '';

  function $(sel) { return document.querySelector(sel); }
  function $$(sel) { return document.querySelectorAll(sel); }
  function fmt(n, d) { if (n == null || isNaN(n)) return '--'; return Number(n).toLocaleString('es-AR', { minimumFractionDigits: d||0, maximumFractionDigits: d||0 }); }
  function fmtARS(n) { return n != null ? '$ ' + fmt(n, 0) : '--'; }
  function esc(t) { var d = document.createElement('div'); d.textContent = t; return d.innerHTML; }
  async function api(p) { try { var r = await fetch(API + p); if (!r.ok) throw 0; return await r.json(); } catch(e) { return null; } }

  function badge(v, s) {
    s = s || '%'; if (v == null) return '<span class="expand-badge expand-badge--neutral">--</span>';
    var c = v > 0 ? 'expand-badge--up' : v < 0 ? 'expand-badge--down' : 'expand-badge--neutral';
    return '<span class="expand-badge ' + c + '">' + (v > 0 ? '+' : '') + fmt(v, 2) + s + '</span>';
  }
  function stat(l, v) { return '<div class="expand-stat"><span class="expand-stat__label">' + l + '</span><span class="expand-stat__value">' + v + '</span></div>'; }
  function sec(t) { return '<div class="expand-section"><div class="expand-section__title">' + t + '</div>'; }
  var SK = '<div style="padding:20px"><div class="skeleton" style="height:14px;width:60%;margin-bottom:10px"></div><div class="skeleton" style="height:14px;width:45%;margin-bottom:10px"></div><div class="skeleton" style="height:14px;width:55%"></div></div>';

  // ═══ CREATE PANEL DOM ═══

  var backdrop, panel, panelTitle, panelBody, panelAsk, panelClose;

  function createPanel() {
    backdrop = document.createElement('div');
    backdrop.className = 'nyx-panel-backdrop';
    document.body.appendChild(backdrop);

    panel = document.createElement('div');
    panel.className = 'nyx-panel';
    panel.innerHTML = ''
      + '<div class="nyx-panel__header">'
      + '  <span class="nyx-panel__title" id="p-title"></span>'
      + '  <button class="nyx-panel__ask" id="p-ask"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>Preguntar</button>'
      + '  <button class="nyx-panel__close" id="p-close">&times;</button>'
      + '</div>'
      + '<div class="nyx-panel__body" id="p-body"></div>';
    document.body.appendChild(panel);

    panelTitle = panel.querySelector('#p-title');
    panelBody = panel.querySelector('#p-body');
    panelAsk = panel.querySelector('#p-ask');
    panelClose = panel.querySelector('#p-close');

    panelClose.addEventListener('click', closePanel);
    backdrop.addEventListener('click', closePanel);
    panelAsk.addEventListener('click', function () {
      closePanel();
      // Open chat + set citation chip (uses nyx-app.js setCite system)
      var trigger = $('#chatTrigger');
      if (trigger) trigger.click();
      setTimeout(function () {
        // Use the existing cite chip system — shows professional tag above input
        var citeEl = $('#chat-cite');
        var citeText = $('#chat-cite-text');
        if (citeEl && citeText && panelCtx) {
          citeText.textContent = panelCtx;
          citeEl.classList.add('visible');
          // Store in the app's currentCite via exposed setter or directly
          if (typeof window.nyxSetCite === 'function') {
            window.nyxSetCite(panelCtx);
          }
        }
        var input = $('#agent-input');
        if (input) { input.value = ''; input.focus(); }
      }, 200);
    });

    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closePanel(); });
  }

  function openPanel(title, html, ctx) {
    panelCtx = ctx || title;
    panelTitle.textContent = title;
    panelBody.innerHTML = html;
    backdrop.classList.add('open');
    panel.classList.add('open');
  }

  function closePanel() {
    backdrop.classList.remove('open');
    panel.classList.remove('open');
  }

  // ═══ INIT ═══

  document.addEventListener('DOMContentLoaded', function () {
    createPanel();

    // KPI cards
    // Support both old .kpi-card and new .kpi class names
    $$('.kpi-card, .kpi').forEach(function (card) {
      card.addEventListener('click', function (e) {
        if (e.target.closest('.ask-nyx') || e.target.closest('.expand-btn')) return;
        var labelEl = card.querySelector('.kpi__label') || card.querySelector('.kpi-card__label');
        var lbl = (labelEl || {}).textContent || '';
        lbl = lbl.toLowerCase();
        if (lbl.includes('dolar')) openDolar();
        else if (lbl.includes('riesgo')) openRiesgo();
        else if (lbl.includes('inflac')) openInflacion();
        else if (lbl.includes('reserv')) openReservas();
        else if (lbl.includes('brecha')) openBrecha();
        else if (lbl.includes('badlar')) openBadlar();
      });
    });

    // Expand buttons — todos los widgets
    document.addEventListener('click', function (e) {
      var btn = e.target.closest('[data-expand]');
      if (!btn) return;
      e.stopPropagation();
      var id = btn.dataset.expand;
      // Charts
      if      (id === 'chart-dolar')     openDolar();
      else if (id === 'chart-inflacion') openInflacion();
      else if (id === 'chart-riesgo')    openRiesgo();
      // KPIs
      else if (id === 'kpi-dolar')       openDolar();
      else if (id === 'kpi-riesgo')      openRiesgo();
      else if (id === 'kpi-inflacion')   openInflacion();
      else if (id === 'kpi-reservas')    openReservas();
      else if (id === 'kpi-brecha')      openBrecha();
      else if (id === 'kpi-badlar')      openBadlar();
      // Indice Nyx
      else if (id === 'nyx-index')       openNyxIndex();
      // Sentiment hero
      else if (id === 'sent-hero')       openSentiment();
      // Mini cards
      else if (id === 'mini-sentiment')  openSentiment();
      else if (id === 'mini-carry')      openCarry();
      else if (id === 'mini-velocity')   openVelocidad();
      else if (id === 'mini-monetary')   openMonetario();
      // Signals & News
      else if (id === 'signals')         openSignals();
      else if (id === 'news')            openNews();
    });

    // Nyx Index card — click o hover muestra expand btn y abre panel
    var nyxCard = $('#nyx-index');
    if (nyxCard) {
      var nyxExpandBtn = nyxCard.querySelector('.expand-btn');
      nyxCard.addEventListener('mouseenter', function () { if (nyxExpandBtn) nyxExpandBtn.style.opacity = '1'; });
      nyxCard.addEventListener('mouseleave', function () { if (nyxExpandBtn) nyxExpandBtn.style.opacity = '0'; });
      nyxCard.addEventListener('click', function (e) { if (!e.target.closest('.expand-btn')) openNyxIndex(); });
    }

    // Sentiment hero card — click abre el panel de sentiment
    var sentCard = $('#sent-hero');
    if (sentCard) { sentCard.style.cursor = 'pointer'; sentCard.addEventListener('click', function (e) { if (!e.target.closest('.ask-nyx') && !e.target.closest('.expand-btn')) openSentiment(); }); }

    // Signals + news via delegation
    document.addEventListener('click', function (e) {
      if (e.target.closest('.ask-nyx')) return;
      var row = e.target.closest('.signal-row');
      if (row) { var n = row.querySelector('.signal-row__name'); if (n) openSignal(n.textContent.trim()); return; }
      var item = e.target.closest('.news-item');
      if (item) { var h = item.querySelector('.news-item__headline'); if (h) openNoticia(h.textContent, (item.querySelector('.news-item__meta') || {}).textContent || ''); }
    });
  });

  // ═══ DOLAR ═══

  async function openDolar() {
    openPanel('Dolar — Todos los tipos', SK, 'Analiza todos los tipos de dolar, spreads y carry trade');
    var [all, vel, spreads, impl, cp, carry] = await Promise.all([
      api('/dolar'), api('/analisis/dolar/velocidad'), api('/analisis/dolar/spreads'),
      api('/analisis/dolar/implicito'), api('/analisis/dolar/crawling-peg'), api('/analisis/carry-trade/multi'),
    ]);
    var h = '';

    if (all && Array.isArray(all)) {
      h += sec('Cotizaciones Actuales');
      h += '<table class="expand-table"><thead><tr><th>Tipo</th><th>Compra</th><th>Venta</th><th>7d</th><th>30d</th><th>90d</th><th>Vol</th></tr></thead><tbody>';
      all.forEach(function (d) {
        var v = vel && vel[d.casa] ? vel[d.casa] : {};
        h += '<tr><td><strong>' + (d.nombre || d.casa) + '</strong></td><td>' + fmtARS(d.compra) + '</td><td>' + fmtARS(d.venta) + '</td>';
        h += '<td>' + badge(v.var_7d_pct) + '</td><td>' + badge(v.var_30d_pct) + '</td><td>' + badge(v.var_90d_pct) + '</td>';
        h += '<td>' + fmt(v.volatilidad_diaria_pct, 3) + '%</td></tr>';
      });
      h += '</tbody></table></div>';
    }

    if (spreads) {
      h += '<div class="expand-grid" style="margin-top:14px">';
      h += '<div>' + sec('Spreads');
      Object.keys(spreads).forEach(function (k) { var s = spreads[k];
        if (k === 'convergencia') h += '<div class="expand-insight">Convergencia: dispersion ' + fmt(s.dispersion_pct, 2) + '% (' + s.nivel + ') — rango $' + fmt(s.rango_pesos, 0) + '</div>';
        else h += stat(k.replace(/_/g, ' '), '$' + fmt(s.diferencia, 0) + ' ' + badge(s.brecha_pct));
      });
      h += '</div></div>';

      if (impl) {
        h += '<div>' + sec('Dolar Implicito');
        h += stat('Base monetaria / reservas', '$ ' + fmt(impl.dolar_implicito_base, 2));
        h += stat('Circulacion / reservas', '$ ' + fmt(impl.dolar_implicito_circulacion, 2));
        h += stat('Ratio Blue / implicito', fmt(impl.ratio_blue_vs_implicito, 2) + 'x');
        if (impl.interpretacion) h += '<div class="expand-insight">' + impl.interpretacion + '</div>';
        h += '</div></div>';
      }
      h += '</div>';
    }

    if (carry && carry.mejor_plazo_fijo) {
      h += sec('Carry Trade');
      h += '<div class="expand-insight">Mejor plazo fijo: ' + esc(carry.mejor_plazo_fijo.entidad) + ' — TNA ' + fmt(carry.mejor_plazo_fijo.tna_pct, 2) + '% (' + fmt(carry.mejor_plazo_fijo.mensual_pct, 2) + '%/mes)</div>';
      h += '<table class="expand-table"><thead><tr><th>vs Dolar</th><th>Devaluacion 30d</th><th>Ganancia carry</th></tr></thead><tbody>';
      ['blue', 'mep', 'ccl'].forEach(function (k) { var c = carry[k]; if (c) h += '<tr><td><strong>' + k.toUpperCase() + '</strong></td><td>' + badge(c.devaluacion_30d_pct) + '</td><td>' + badge(c.ganancia_carry_pct) + '</td></tr>'; });
      h += '</tbody></table>';
      if (cp) { h += stat('Crawling peg mensual', badge(cp.tasa_mensual_pct)); h += stat('Anualizado', badge(cp.tasa_anualizada_pct)); }
      h += '</div>';
    }

    panelBody.innerHTML = h;
  }

  // ═══ RIESGO PAIS ═══

  async function openRiesgo() {
    openPanel('Riesgo Pais', SK, 'Analiza el riesgo pais, probabilidad de default y tendencia');
    var data = await api('/analisis/riesgo-pais');
    if (!data) { panelBody.innerHTML = '<p style="color:var(--muted-foreground)">Sin datos</p>'; return; }

    var h = '<div class="expand-grid">';
    h += '<div>' + sec('Variaciones');
    h += stat('Actual', '<strong>' + fmt(data.actual, 0) + ' puntos</strong>');
    h += stat('7 dias', badge(data.var_7d_pct));
    h += stat('30 dias', badge(data.var_30d_pct));
    h += stat('90 dias', badge(data.var_90d_pct));
    h += stat('Rango 90d', fmt(data.min_90d, 0) + ' — ' + fmt(data.max_90d, 0) + ' pts');
    h += '</div></div>';

    h += '<div>' + sec('Indicadores');
    h += stat('Zona', '<span class="expand-badge expand-badge--' + (['estable','baja'].includes(data.zona) ? 'up' : ['critica','riesgosa'].includes(data.zona) ? 'down' : 'neutral') + '">' + (data.zona || '?').toUpperCase() + '</span>');
    h += stat('Tendencia', data.tendencia || '?');
    h += stat('Volatilidad', fmt(data.volatilidad, 2) + ' pts');
    h += stat('Prob. default 5 anos', '<strong>' + fmt(data.probabilidad_default_5a_pct, 2) + '%</strong>');
    if (data.cds_5anos_ref) h += stat('CDS 5a (ref BCRA)', fmt(data.cds_5anos_ref, 2));
    h += '</div></div>';
    h += '</div>';

    panelBody.innerHTML = h;
  }

  // ═══ INFLACION ═══

  async function openInflacion() {
    openPanel('Inflacion', SK, 'Analiza inflacion, core vs headline y poder adquisitivo');
    var [inf, cvh, ext, poder] = await Promise.all([
      api('/analisis/inflacion'), api('/analisis/inflacion/core-vs-headline'),
      api('/analisis/inflacion/extendida'), api('/analisis/poder-adquisitivo'),
    ]);
    var h = '<div class="expand-grid">';

    if (inf) {
      h += '<div>' + sec('Situacion Actual');
      h += stat('Ultimo mes', '<strong>' + fmt(inf.ultimo_mes, 1) + '%</strong>');
      h += stat('Interanual compuesta', fmt(inf.interanual_compuesta, 2) + '%');
      h += stat('Acumulada 3 meses', fmt(inf.acumulada_3m, 2) + '%');
      h += stat('Anualizada (ritmo actual)', fmt(inf.anualizada_ultimo_mes, 2) + '%');
      h += stat('Tendencia', '<span class="expand-badge expand-badge--' + (inf.tendencia === 'desacelerando' ? 'up' : inf.tendencia === 'acelerando' ? 'down' : 'neutral') + '">' + (inf.tendencia || '?').toUpperCase() + '</span>');
      h += stat('Aceleracion', badge(inf.aceleracion, 'pp'));
      h += '</div></div>';
    }

    if (cvh && cvh.serie) {
      h += '<div>' + sec('Core vs Headline');
      if (cvh.interpretacion) h += '<div class="expand-insight">' + cvh.interpretacion + '</div>';
      h += '<table class="expand-table"><thead><tr><th>Mes</th><th>Core</th><th>General</th><th>Spread</th></tr></thead><tbody>';
      cvh.serie.forEach(function (m) { h += '<tr><td>' + (m.fecha || '').slice(0, 7) + '</td><td>' + fmt(m.core_pct, 2) + '%</td><td>' + fmt(m.headline_pct, 2) + '%</td><td>' + badge(m.spread_pp, 'pp') + '</td></tr>'; });
      h += '</tbody></table></div></div>';
    }
    h += '</div>';

    h += '<div class="expand-grid" style="margin-top:14px">';
    if (poder) {
      h += '<div>' + sec('Poder Adquisitivo');
      h += stat('$1.000 de hace 12 meses hoy vale', '$ ' + fmt(poder.valor_real_1000_12m, 0));
      h += stat('$1.000 de hace 3 meses hoy vale', '$ ' + fmt(poder.valor_real_1000_3m, 0));
      h += stat('Perdida diaria', fmt(poder.perdida_diaria_pct, 3) + '%');
      h += stat('Dias para perder 1%', fmt(poder.dias_para_perder_1pct, 1));
      h += '</div></div>';
    }
    if (ext) {
      h += '<div>' + sec('Historico 60 meses');
      h += stat('Pico historico', fmt(ext.pico_mensual, 1) + '% (' + (ext.pico_fecha || '').slice(0, 7) + ')');
      h += stat('Acumulada total', fmt(ext.acumulada_total_pct, 0) + '%');
      if (ext.por_ano) {
        h += '<table class="expand-table"><thead><tr><th>Ano</th><th>Promedio mensual</th></tr></thead><tbody>';
        Object.keys(ext.por_ano).forEach(function (y) { h += '<tr><td>' + y + '</td><td>' + fmt(ext.por_ano[y].promedio_mensual, 2) + '%</td></tr>'; });
        h += '</tbody></table>';
      }
      h += '</div></div>';
    }
    h += '</div>';

    if (inf && inf.serie) {
      h += sec('Serie Mensual');
      h += '<table class="expand-table"><thead><tr><th>Mes</th><th>Inflacion %</th></tr></thead><tbody>';
      inf.serie.forEach(function (m) { h += '<tr><td>' + (m.fecha || '').slice(0, 7) + '</td><td>' + fmt(m.valor, 1) + '%</td></tr>'; });
      h += '</tbody></table></div>';
    }

    panelBody.innerHTML = h;
  }

  // ═══ RESERVAS ═══

  async function openReservas() {
    openPanel('Reservas BCRA', SK, 'Analiza reservas, expansion monetaria y multiplicador');
    var [res, mon] = await Promise.all([api('/analisis/reservas'), api('/analisis/monetario')]);
    var h = '<div class="expand-grid">';

    if (res) {
      h += '<div>' + sec('Reservas Internacionales');
      h += stat('Actual', '<strong>USD ' + fmt(res.actual_usd_mm, 0) + ' millones</strong>');
      h += stat('Cambio total', badge(res.cambio_total_usd_mm, ' MM'));
      h += stat('USD/dia (promedio)', fmt(res.usd_por_dia, 1) + ' MM');
      h += stat('USD/dia (ultima semana)', fmt(res.usd_por_dia_7d, 1) + ' MM');
      h += stat('Tendencia', '<span class="expand-badge expand-badge--' + (res.tendencia === 'acumulando' ? 'up' : 'down') + '">' + (res.tendencia || '?').toUpperCase() + '</span>');
      h += '</div></div>';
    }

    if (mon && mon.expansion) {
      var e = mon.expansion;
      h += '<div>' + sec('Expansion Monetaria');
      h += stat('Base monetaria variacion', badge(e.base_monetaria_var_pct));
      h += stat('Inflacion del periodo', fmt(e.inflacion_acum_pct, 2) + '%');
      h += stat('Exceso monetario', badge(e.exceso_monetario_pct, 'pp'));
      if (e.interpretacion) h += '<div class="expand-insight">' + e.interpretacion + '</div>';
      h += '</div></div>';
    }
    h += '</div>';

    if (mon) {
      h += '<div class="expand-grid" style="margin-top:14px">';
      if (mon.depositos_tendencia) {
        var dt = mon.depositos_tendencia;
        h += '<div>' + sec('Depositos (30 dias)');
        if (dt.privados) h += stat('Sector privado', badge(dt.privados.cambio_pct) + ' (' + dt.privados.tendencia + ')');
        if (dt.publicos) h += stat('Sector publico', badge(dt.publicos.cambio_pct) + ' (' + dt.publicos.tendencia + ')');
        if (dt.interpretacion) h += '<div class="expand-insight">' + dt.interpretacion + '</div>';
        h += '</div></div>';
      }
      if (mon.multiplicador) {
        var m = mon.multiplicador;
        h += '<div>' + sec('Multiplicador Monetario');
        h += stat('Multiplicador M2/Base', fmt(m.multiplicador, 3));
        h += stat('Circulacion / Base', fmt(m.ratio_circulacion_base_pct, 1) + '%');
        if (m.interpretacion) h += '<div class="expand-insight">' + m.interpretacion + '</div>';
        h += '</div></div>';
      }
      h += '</div>';
    }

    panelBody.innerHTML = h;
  }

  // ═══ NYX INDEX ═══

  async function openNyxIndex() {
    openPanel('Indice Nyx', SK, 'Explicame el indice Nyx, sus componentes y que significa');
    var [nyx, tp, sent] = await Promise.all([api('/analisis/indice-nyx'), api('/analisis/tasa-politica'), api('/analisis/sentiment')]);
    var h = '<div class="expand-grid">';

    if (nyx && nyx.componentes) {
      h += '<div>' + sec('Score: ' + fmt(nyx.score, 1) + '/100 — ' + (nyx.nivel || '?').toUpperCase());
      Object.keys(nyx.componentes).forEach(function (k) {
        var v = nyx.componentes[k];
        h += stat(k.replace(/_/g, ' '), typeof v === 'number' ? fmt(v, 2) : String(v));
      });
      if (nyx.alertas && nyx.alertas.length) {
        nyx.alertas.forEach(function (a) { h += '<div class="expand-insight" style="border-left-color:var(--warning)">! ' + a + '</div>'; });
      }
      h += '</div></div>';
    }

    h += '<div>';
    if (tp) {
      h += sec('Politica Monetaria');
      if (tp.pases_pasivos) h += stat('Pases pasivos (ref BCRA)', fmt(tp.pases_pasivos, 2) + '%');
      if (tp.badlar) h += stat('BADLAR', fmt(tp.badlar, 2) + '%');
      if (tp.spread_pases_badlar_pp) h += stat('Spread pases-BADLAR', fmt(tp.spread_pases_badlar_pp, 2) + 'pp');
      if (tp.corredor) h += stat('Corredor de tasas', fmt(tp.corredor.piso, 1) + '% — ' + fmt(tp.corredor.techo, 1) + '%');
      if (tp.interpretacion) h += '<div class="expand-insight">' + tp.interpretacion + '</div>';
      h += '</div>';
    }
    if (sent) {
      h += sec('Sentiment Social');
      h += stat('Tono', '<span class="expand-badge expand-badge--' + (sent.tono === 'optimista' ? 'up' : sent.tono === 'pesimista' ? 'down' : 'neutral') + '">' + (sent.tono || '?').toUpperCase() + '</span>');
      h += stat('Ratio positivo/negativo', fmt(sent.ratio_pos_neg, 2));
      h += stat('Total tweets', fmt(sent.total_tweets, 0));
      h += stat('Positivos', sent.positivos); h += stat('Negativos', sent.negativos);
      h += '</div>';
    }
    h += '</div></div>';

    panelBody.innerHTML = h;
  }

  // ═══ SIGNAL ═══

  async function openSignal(name) {
    openPanel('Senal: ' + name, SK, 'Analiza en detalle la senal ' + name);
    var map = { 'Presion Cambiaria': 'indice-nyx', 'Brecha Cambiaria': 'dolar/spreads', 'Tasa Real': 'tasas', 'Tendencia Reservas': 'reservas' };
    var ep = map[name]; if (!ep) { panelBody.innerHTML = '<p>Sin detalle</p>'; return; }
    var data = await api('/analisis/' + ep);
    if (!data) { panelBody.innerHTML = '<p>Sin datos</p>'; return; }
    var h = sec(name);
    if (typeof data === 'object' && !Array.isArray(data)) {
      Object.keys(data).forEach(function (k) { var v = data[k]; if (v != null && typeof v !== 'object') h += stat(k.replace(/_/g, ' '), typeof v === 'number' ? fmt(v, 2) : String(v)); });
    }
    h += '</div>';
    panelBody.innerHTML = h;
  }

  // ═══ BRECHA CAMBIARIA ═══

  async function openBrecha() {
    openPanel('Brecha Cambiaria', SK, 'Analiza la brecha cambiaria y spreads entre tipos de dolar');
    var [spreads, vel, impl] = await Promise.all([
      api('/analisis/dolar/spreads'), api('/analisis/dolar/velocidad'), api('/analisis/dolar/implicito'),
    ]);
    var h = '';

    if (spreads) {
      h += sec('Spreads entre tipos de dolar');
      Object.keys(spreads).forEach(function (k) {
        var s = spreads[k];
        if (k === 'convergencia') {
          h += '<div class="expand-insight">Convergencia: dispersion ' + fmt(s.dispersion_pct, 2) + '% (' + s.nivel + ') — rango $' + fmt(s.rango_pesos, 0) + '</div>';
        } else {
          h += stat(k.replace(/_/g, ' '), '$' + fmt(s.diferencia, 0) + ' ' + badge(s.brecha_pct));
        }
      });
      h += '</div>';
    }

    if (impl) {
      h += sec('Dolar Implicito');
      h += stat('Base monetaria / reservas', '$ ' + fmt(impl.dolar_implicito_base, 2));
      h += stat('Circulacion / reservas', '$ ' + fmt(impl.dolar_implicito_circulacion, 2));
      h += stat('Ratio Blue / implicito', fmt(impl.ratio_blue_vs_implicito, 2) + 'x');
      if (impl.interpretacion) h += '<div class="expand-insight">' + impl.interpretacion + '</div>';
      h += '</div>';
    }

    panelBody.innerHTML = h || '<p style="color:var(--muted-foreground)">Sin datos</p>';
  }

  // ═══ BADLAR & POLITICA MONETARIA ═══

  async function openBadlar() {
    openPanel('BADLAR & Politica Monetaria', SK, 'Analiza BADLAR, tasa politica y multiplicador monetario');
    var [tp, mon] = await Promise.all([api('/analisis/tasa-politica'), api('/analisis/monetario')]);
    var h = '<div class="expand-grid">';

    if (tp) {
      h += '<div>' + sec('Politica Monetaria');
      if (tp.pases_pasivos != null) h += stat('Pases pasivos (ref BCRA)', fmt(tp.pases_pasivos, 2) + '%');
      if (tp.badlar != null) h += stat('BADLAR', fmt(tp.badlar, 2) + '%');
      if (tp.tm20 != null) h += stat('TM20', fmt(tp.tm20, 2) + '%');
      if (tp.spread_pases_badlar_pp != null) h += stat('Spread pases-BADLAR', fmt(tp.spread_pases_badlar_pp, 2) + 'pp');
      if (tp.corredor) h += stat('Corredor de tasas', fmt(tp.corredor.piso, 1) + '% — ' + fmt(tp.corredor.techo, 1) + '%');
      if (tp.interpretacion) h += '<div class="expand-insight">' + tp.interpretacion + '</div>';
      h += '</div></div>';
    }

    if (mon) {
      if (mon.multiplicador) {
        var m = mon.multiplicador;
        h += '<div>' + sec('Multiplicador Monetario');
        h += stat('Multiplicador M2/Base', fmt(m.multiplicador, 3));
        h += stat('Circulacion / Base', fmt(m.ratio_circulacion_base_pct, 1) + '%');
        if (m.interpretacion) h += '<div class="expand-insight">' + m.interpretacion + '</div>';
        h += '</div></div>';
      }
      if (mon.expansion) {
        var ex = mon.expansion;
        h += '<div>' + sec('Expansion Monetaria');
        h += stat('Base monetaria variacion', badge(ex.base_monetaria_var_pct));
        h += stat('Inflacion del periodo', fmt(ex.inflacion_acum_pct, 2) + '%');
        h += stat('Exceso monetario', badge(ex.exceso_monetario_pct, 'pp'));
        if (ex.interpretacion) h += '<div class="expand-insight">' + ex.interpretacion + '</div>';
        h += '</div></div>';
      }
    }
    h += '</div>';

    panelBody.innerHTML = h || '<p style="color:var(--muted-foreground)">Sin datos</p>';
  }

  // ═══ NOTICIA ═══

  function openNoticia(titulo, meta) {
    var h = sec('Noticia');
    h += '<div class="expand-insight" style="font-size:14px;font-weight:500;line-height:1.6">' + esc(titulo) + '</div>';
    if (meta) h += '<p style="font-size:11px;color:var(--muted-foreground);margin-top:8px">' + esc(meta) + '</p>';
    h += '</div>';
    openPanel('Noticia', h, 'Analiza esta noticia: ' + titulo);
  }

  // ═══ SENTIMENT SOCIAL — expandido con explicación causal ═══

  async function openSentiment() {
    openPanel('Sentiment Social', SK, 'Explica por que el sentiment esta en ese nivel y que implica para el mercado');
    var data = await api('/analisis/sentiment');
    if (!data) { panelBody.innerHTML = '<p style="color:var(--muted-foreground)">Sin datos de sentiment</p>'; return; }

    var total = (data.positivos || 0) + (data.negativos || 0) + (data.neutros || 0);
    var negPct = total ? ((data.negativos || 0) / total * 100).toFixed(1) : 0;
    var posPct = total ? ((data.positivos || 0) / total * 100).toFixed(1) : 0;
    var neuPct = total ? ((data.neutros   || 0) / total * 100).toFixed(1) : 0;

    var toneColors = {
      pesimista: 'hsl(var(--destructive))',
      optimista: 'hsl(var(--success))',
      positivo:  'hsl(var(--success))',
      neutro:    'hsl(var(--muted-foreground))',
    };
    var tc = toneColors[(data.tono || '').toLowerCase()] || 'hsl(268,70%,58%)';

    var h = '';

    // ── Por qué este tono ──
    h += sec('Por que el tono es <span style="color:' + tc + '">' + esc(data.tono || '--').toUpperCase() + '</span>');

    // Explicacion basada en el ratio
    var ratio = data.ratio_pos_neg || 0;
    var razonTono = '';
    if ((data.tono || '').toLowerCase() === 'pesimista' || (data.tono || '').toLowerCase() === 'negativo') {
      razonTono = 'Hay <strong>' + negPct + '% de tweets negativos</strong> contra ' + posPct + '% positivos (ratio ' + fmt(ratio, 2) + '). '
        + 'El mercado expresa preocupacion: los temas con mayor volumen negativo dominan la conversacion.';
    } else if ((data.tono || '').toLowerCase() === 'optimista' || (data.tono || '').toLowerCase() === 'positivo') {
      razonTono = 'Hay <strong>' + posPct + '% de tweets positivos</strong> contra ' + negPct + '% negativos (ratio ' + fmt(ratio, 2) + '). '
        + 'El mercado muestra confianza: expectativas favorables superan las preocupaciones.';
    } else {
      razonTono = 'El mercado esta <strong>dividido</strong>: ' + posPct + '% positivo vs ' + negPct + '% negativo (ratio ' + fmt(ratio, 2) + '). '
        + 'Sin consenso claro, alta incertidumbre en la opinion publica.';
    }
    h += '<div class="expand-insight" style="border-left-color:' + tc + '">' + razonTono + '</div>';
    h += '</div>';

    // ── Distribucion ──
    h += '<div class="expand-grid" style="margin-top:14px">';
    h += '<div>' + sec('Distribucion de Tweets');
    h += stat('Total analizado', '<strong>' + fmt(data.total_tweets, 0) + ' tweets</strong>');
    h += stat('Positivos', '<span style="color:hsl(var(--success))">' + fmt(data.positivos, 0) + ' (' + posPct + '%)</span>');
    h += stat('Negativos', '<span style="color:hsl(var(--destructive))">' + fmt(data.negativos, 0) + ' (' + negPct + '%)</span>');
    if (data.neutros) h += stat('Neutros', fmt(data.neutros, 0) + ' (' + neuPct + '%)');
    h += stat('Ratio pos/neg', '<strong>' + fmt(ratio, 2) + '</strong> ' + (ratio >= 1 ? '(mas positivos)' : '(mas negativos)'));
    h += '</div></div>';

    // ── Temas que impulsan el tono ──
    if (data.volumen_por_tema) {
      h += '<div>' + sec('Temas que impulsan el sentiment');
      var temas = Object.entries(data.volumen_por_tema)
        .sort(function (a, b) { return b[1] - a[1]; });
      temas.slice(0, 8).forEach(function (kv) {
        var pctTema = total ? (kv[1] / data.total_tweets * 100).toFixed(1) : 0;
        h += '<div class="expand-stat">'
          + '<span class="expand-stat__label">' + esc(kv[0].replace(/_/g, ' ')) + '</span>'
          + '<span class="expand-stat__value">' + fmt(kv[1], 0) + ' tweets <span style="color:hsl(var(--muted-foreground));font-weight:400">(' + pctTema + '%)</span></span>'
          + '</div>';
      });
      h += '</div></div>';
    }
    h += '</div>';

    // ── Implicaciones para el mercado ──
    h += sec('Implicaciones para el mercado');
    var impl = '';
    if ((data.tono || '').toLowerCase() === 'pesimista') {
      impl = 'Un sentiment pesimista suele <strong>anticipar mayor demanda de dolar</strong> como refugio, presion sobre la brecha cambiaria y cautela en inversiones. Monitorear si se correlaciona con subas del blue en las proximas 48-72hs.';
    } else if ((data.tono || '').toLowerCase() === 'optimista' || (data.tono || '').toLowerCase() === 'positivo') {
      impl = 'Un sentiment positivo puede reflejar <strong>expectativas de estabilizacion</strong>, mayor predisposicion a mantener pesos y menor presion sobre el tipo de cambio. Puede ser una señal contrarian si el contexto macro es adverso.';
    } else {
      impl = 'Sentiment neutro indica <strong>alta incertidumbre</strong> en la opinion publica. El mercado espera señales claras. Cualquier novedad macro (reservas, inflacion, brecha) puede mover el tono rapidamente.';
    }
    if (data.interpretacion) impl += ' — ' + data.interpretacion;
    h += '<div class="expand-insight">' + impl + '</div>';
    h += '</div>';

    panelBody.innerHTML = h;
  }

  // ═══ CARRY TRADE (mini card) ═══

  async function openCarry() {
    openPanel('Carry Trade', SK, 'Analiza carry trade: mejor plazo fijo, rentabilidad vs Blue/MEP/CCL');
    var [carry, plazo] = await Promise.all([api('/analisis/carry-trade/multi'), api('/analisis/plazo-fijo')]);
    var h = '<div class="expand-grid">';
    if (carry && carry.mejor_plazo_fijo) {
      var pf = carry.mejor_plazo_fijo;
      h += '<div>' + sec('Mejor Plazo Fijo');
      h += stat('Entidad', esc(pf.entidad || '--'));
      h += stat('TNA', fmt(pf.tna_pct, 2) + '%');
      h += stat('Retorno mensual', fmt(pf.mensual_pct, 2) + '%');
      h += '</div></div>';
    }
    h += '<div>' + sec('vs Tipo de Cambio');
    ['blue', 'mep', 'ccl'].forEach(function (k) {
      var c = carry && carry[k];
      if (!c) return;
      var gv = c.ganancia_carry_pct;
      if (gv == null) return;
      var col = gv > 0 ? 'hsl(var(--success))' : 'hsl(var(--destructive))';
      h += stat('vs ' + k.toUpperCase(), '<span style="color:' + col + '">' + (gv > 0 ? '+' : '') + fmt(gv, 2) + '%</span>');
    });
    if (carry && carry.interpretacion) h += '<div class="expand-insight">' + esc(carry.interpretacion.substring(0, 200)) + '</div>';
    h += '</div></div>';
    h += '</div>';
    panelBody.innerHTML = h;
  }

  // ═══ VELOCIDAD DOLAR ═══

  async function openVelocidad() {
    openPanel('Velocidad del Dolar', SK, 'Analiza velocidad del dolar: variaciones 7/30/90d, volatilidad y momentum');
    var data = await api('/analisis/dolar/velocidad');
    if (!data) { panelBody.innerHTML = '<p style="color:var(--muted-foreground)">Sin datos</p>'; return; }
    var h = '';
    var tipos = ['blue', 'oficial', 'bolsa', 'contadoconliqui'];
    var names = { blue: 'Blue', oficial: 'Oficial', bolsa: 'MEP / Bolsa', contadoconliqui: 'CCL' };
    tipos.forEach(function (t) {
      var d = data[t];
      if (!d) return;
      h += sec(names[t] || t);
      h += stat('Variacion 7d', badge(d.var_7d_pct));
      h += stat('Variacion 30d', badge(d.var_30d_pct));
      h += stat('Variacion 90d', badge(d.var_90d_pct));
      h += stat('Volatilidad diaria', fmt(d.volatilidad_diaria_pct, 3) + '%');
      h += '</div>';
    });
    panelBody.innerHTML = h || '<p style="color:var(--muted-foreground)">Sin datos</p>';
  }

  // ═══ BASE MONETARIA ═══

  async function openMonetario() {
    openPanel('Base Monetaria & Monetario', SK, 'Analiza base monetaria, multiplicador y expansion monetaria');
    var data = await api('/analisis/monetario');
    if (!data) { panelBody.innerHTML = '<p style="color:var(--muted-foreground)">Sin datos</p>'; return; }
    var h = '<div class="expand-grid">';
    if (data.expansion) {
      var ex = data.expansion;
      h += '<div>' + sec('Expansion Monetaria');
      h += stat('Base monetaria variacion', badge(ex.base_monetaria_var_pct));
      h += stat('Inflacion del periodo', fmt(ex.inflacion_acum_pct, 2) + '%');
      h += stat('Exceso monetario', badge(ex.exceso_monetario_pct, 'pp'));
      if (ex.interpretacion) h += '<div class="expand-insight">' + ex.interpretacion + '</div>';
      h += '</div></div>';
    }
    if (data.multiplicador) {
      var m = data.multiplicador;
      h += '<div>' + sec('Multiplicador Monetario');
      h += stat('Multiplicador M2/Base', fmt(m.multiplicador, 3));
      h += stat('Circulacion / Base', fmt(m.ratio_circulacion_base_pct, 1) + '%');
      if (m.interpretacion) h += '<div class="expand-insight">' + m.interpretacion + '</div>';
      h += '</div></div>';
    }
    if (data.depositos_tendencia) {
      var dt = data.depositos_tendencia;
      h += '<div>' + sec('Depositos (30 dias)');
      if (dt.privados) h += stat('Sector privado', badge(dt.privados.cambio_pct) + ' (' + dt.privados.tendencia + ')');
      if (dt.publicos) h += stat('Sector publico', badge(dt.publicos.cambio_pct) + ' (' + dt.publicos.tendencia + ')');
      if (dt.interpretacion) h += '<div class="expand-insight">' + dt.interpretacion + '</div>';
      h += '</div></div>';
    }
    h += '</div>';
    panelBody.innerHTML = h;
  }

  // ═══ SEÑALES DE RIESGO (card completa) ═══

  async function openSignals() {
    openPanel('Senales de Riesgo', SK, 'Dame un analisis completo de todas las senales de riesgo macro activas');
    var data = await api('/signals');
    if (!data) { panelBody.innerHTML = '<p style="color:var(--muted-foreground)">Sin datos</p>'; return; }
    var h = '';
    var defs = [
      { key: 'presion_cambiaria',  label: 'Presion Cambiaria',  field: 'score',       suffix: '/100' },
      { key: 'brecha_cambiaria',   label: 'Brecha Cambiaria',   field: 'brecha_pct',  suffix: '%' },
      { key: 'tasa_real',          label: 'Tasa Real',          field: 'tasa_real_pct', suffix: '%' },
      { key: 'tendencia_reservas', label: 'Tendencia Reservas', field: 'variacion_pct', suffix: '%' },
    ];
    defs.forEach(function (d) {
      var sig = data[d.key];
      if (!sig) return;
      var val = sig[d.field] != null ? sig[d.field] : sig.value;
      h += sec(d.label);
      if (val != null) h += stat('Valor', '<strong>' + fmt(val, 1) + d.suffix + '</strong>');
      Object.keys(sig).forEach(function (k) {
        var v = sig[k];
        if (k === d.field || k === 'value' || typeof v === 'object' || v == null) return;
        h += stat(k.replace(/_/g, ' '), typeof v === 'number' ? fmt(v, 2) + (d.suffix || '') : esc(String(v)));
      });
      h += '</div>';
    });
    panelBody.innerHTML = h || '<p style="color:var(--muted-foreground)">Sin datos disponibles</p>';
  }

  // ═══ NOTICIAS (card completa) ═══

  async function openNews() {
    openPanel('Ultimas Noticias', SK, 'Resume y analiza las noticias economicas mas importantes y su impacto');
    var data = await api('/noticias');
    if (!data || !Array.isArray(data) || !data.length) {
      panelBody.innerHTML = '<p style="color:var(--muted-foreground)">Sin noticias</p>'; return;
    }
    var typeColors = { economico: 'hsl(268,70%,58%)', sindical: 'hsl(0,78%,58%)', regulatorio: 'hsl(38,92%,55%)', politico: 'hsl(192,80%,50%)', climatico: 'hsl(152,69%,53%)', informativo: 'hsl(220,8%,55%)' };
    var h = '';
    data.slice(0, 20).forEach(function (n) {
      var tipo = (n.tipo || n.type || 'informativo').toLowerCase();
      var ac = typeColors[tipo] || typeColors.informativo;
      var titulo = n.titulo || n.title || '';
      var askQ = 'Analiza esta noticia y su impacto economico: ' + titulo;
      h += '<div class="alerts-panel-item" style="--ac:' + ac + '">'
        + '<div class="alerts-panel-item__header">'
        + '<div class="alerts-panel-item__dot"></div>'
        + '<span class="alerts-panel-item__category">' + esc(tipo) + '</span>'
        + '<button class="alerts-panel-ask" data-ask="' + esc(askQ) + '" data-cite="' + esc(titulo.substring(0, 40)) + '">'
        + '<svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>Preguntar</button>'
        + '</div>'
        + '<div class="alerts-panel-item__text">' + esc(titulo) + '</div>'
        + (n.fuente ? '<div style="font-size:10px;color:hsl(var(--muted-foreground));margin-top:4px;font-family:var(--font-mono)">' + esc(n.fuente) + '</div>' : '')
        + '</div>';
    });

    openPanel('Ultimas Noticias', h, 'Resume y analiza las noticias economicas mas importantes y su impacto');

    setTimeout(function () {
      var body = document.querySelector('#p-body');
      if (!body) return;
      body.querySelectorAll('[data-ask]').forEach(function (btn) {
        btn.addEventListener('click', function (e) {
          e.stopPropagation(); closePanel();
          var trigger = document.querySelector('#chatTrigger');
          if (trigger) trigger.click();
          setTimeout(function () {
            if (typeof window.nyxSetCite === 'function') window.nyxSetCite(btn.dataset.cite || '');
            var input = document.querySelector('#agent-input');
            if (input) { input.value = ''; input.focus(); }
          }, 180);
        });
      });
    }, 50);
  }

  // ═══ ALERTAS TEMPRANAS — panel expandido ═══

  function openAlertasTicker() {
    var alerts = window.nyxAlerts || [];
    var h = '';

    // Resumen + botón "consultar todo"
    var allCtx = alerts.map(function (a) {
      return a.category + ': ' + (a.text || '').replace(/<[^>]+>/g, '');
    }).join('. ');
    var consultarQ = 'Dame un analisis integral y recomendaciones basadas en todas las alertas activas del sistema: ' + allCtx.substring(0, 500);

    h += '<div class="alerts-panel-summary">'
      + '<span>Hay <strong>' + alerts.length + ' alerta' + (alerts.length !== 1 ? 's' : '') + ' activa' + (alerts.length !== 1 ? 's' : '') + '</strong> en el monitor de riesgo Nyx.</span>'
      + '<button class="alerts-panel-summary-btn" data-ask="' + esc(consultarQ) + '" data-cite="Alertas Tempranas — ' + alerts.length + ' activas">'
      + '<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>'
      + 'Consultar todo'
      + '</button>'
      + '</div>';

    if (!alerts.length) {
      h += '<p style="color:hsl(var(--muted-foreground));font-size:12px">Sin alertas disponibles. Cargando datos del motor de análisis...</p>';
    } else {
      var colorMap = {
        critical: 'hsl(var(--destructive))',
        warning:  'hsl(var(--warning))',
        positive: 'hsl(var(--success))',
        info:     'hsl(268,70%,58%)',
        neutral:  'hsl(var(--muted-foreground))',
      };

      alerts.forEach(function (alert) {
        var ac = colorMap[alert.type] || colorMap.neutral;
        var plainText = (alert.text || '').replace(/<[^>]+>/g, '');
        var askQ = 'Analizame en detalle esta alerta — ' + alert.category + ': ' + plainText.substring(0, 300);

        h += '<div class="alerts-panel-item" style="--ac:' + ac + '">'
          + '<div class="alerts-panel-item__header">'
          + '<div class="alerts-panel-item__dot"></div>'
          + '<span class="alerts-panel-item__category">' + esc(alert.category) + '</span>'
          + '<button class="alerts-panel-ask" data-ask="' + esc(askQ) + '" data-cite="' + esc(alert.category) + '">'
          + '<svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>'
          + 'Preguntar'
          + '</button>'
          + '</div>'
          + '<div class="alerts-panel-item__text">' + alert.text + '</div>'
          + '</div>';
      });
    }

    openPanel('Alertas Tempranas', h, consultarQ);

    // Wire up individual ask buttons inside the panel
    setTimeout(function () {
      var body = document.querySelector('#p-body');
      if (!body) return;
      body.querySelectorAll('[data-ask]').forEach(function (btn) {
        btn.addEventListener('click', function (e) {
          e.stopPropagation();
          closePanel();
          var trigger = document.querySelector('#chatTrigger');
          if (trigger) trigger.click();
          setTimeout(function () {
            if (typeof window.nyxSetCite === 'function') window.nyxSetCite(btn.dataset.cite || '');
            var input = document.querySelector('#agent-input');
            if (input) { input.value = ''; input.focus(); }
          }, 180);
        });
      });
    }, 50);
  }

  // ═══ INDICE NYX ═══

  async function openNyxIndex() {
    openPanel('Indice Nyx', SK, 'Analiza el Indice Nyx: componentes, nivel de riesgo y alertas activas');
    var data = await api('/analisis/indice-nyx');
    if (!data) { panelBody.innerHTML = '<p style="color:var(--muted-foreground);padding:20px">Sin datos</p>'; return; }

    var score = data.score || 0;
    var nivel = (data.nivel || 'moderado').toUpperCase();
    var colorMap = { CRITICO: '#ef4444', ALTO: '#f59e0b', MODERADO: '#8b5cf6', BAJO: '#10b981', MUY_BAJO: '#10b981' };
    var col = colorMap[nivel] || '#8b5cf6';

    var h = '<div style="text-align:center;padding:16px 0 20px">'
      + '<div style="font-size:56px;font-weight:700;font-family:var(--font-display);color:' + col + ';line-height:1;letter-spacing:-0.04em">' + fmt(score, 0) + '</div>'
      + '<div style="font-family:var(--font-mono);font-size:11px;font-weight:700;letter-spacing:0.1em;color:' + col + ';margin-top:6px">' + nivel + '</div>'
      + '<div style="width:180px;height:6px;background:rgba(255,255,255,0.07);border-radius:3px;margin:12px auto 0;overflow:hidden">'
      + '<div style="width:' + score + '%;height:100%;background:' + col + ';border-radius:3px;box-shadow:0 0 8px ' + col + '"></div></div>'
      + '</div>';

    // Componentes
    if (data.componentes) {
      var compMap = {
        brecha_cambiaria:     { label: 'Brecha Cambiaria',     fmt: function(v){ return fmt(v,2) + '%'; },        good: function(v){ return Math.abs(v) < 5; } },
        riesgo_pais:          { label: 'Riesgo Pais',          fmt: function(v){ return fmt(v,0) + ' pts'; },     good: function(v){ return v < 500; } },
        volatilidad_blue:     { label: 'Volatilidad Blue',     fmt: function(v){ return fmt(v,3) + '%/d'; },      good: function(v){ return v < 0.5; } },
        reservas_usd_dia:     { label: 'Reservas USD/dia',     fmt: function(v){ return '$ ' + fmt(v,1) + 'M'; },good: function(v){ return v > 50; } },
        inflacion_tendencia:  { label: 'Inflacion Tendencia',  fmt: function(v){ return v; },                     good: function(v){ return v === 'desacelerando'; } },
        tasa_real_badlar:     { label: 'Tasa Real BADLAR',     fmt: function(v){ return fmt(v,2) + '%'; },        good: function(v){ return v >= 0; } },
        prob_default_5a:      { label: 'Prob. Default 5a',     fmt: function(v){ return fmt(v,2) + '%'; },        good: function(v){ return v < 30; } },
        emae_yoy:             { label: 'EMAE Interanual',      fmt: function(v){ return fmt(v,2) + '%'; },        good: function(v){ return v > 0; } },
        sentiment_ratio:      { label: 'Sentiment Ratio',      fmt: function(v){ return fmt(v,2); },              good: function(v){ return v > 0.5; } },
        inflacion_core_spread:{ label: 'Core Spread',          fmt: function(v){ return fmt(v,2) + 'pp'; },       good: function(v){ return Math.abs(v) < 1; } },
      };
      h += '<div>' + sec('Componentes (' + (data.variables_usadas || 10) + ' variables)');
      Object.keys(compMap).forEach(function(k) {
        var v = data.componentes[k];
        if (v == null) return;
        var cfg = compMap[k];
        var isGood = cfg.good(v);
        var badgeClass = isGood ? 'expand-badge--up' : 'expand-badge--down';
        h += stat(cfg.label, '<span class="expand-badge ' + badgeClass + '">' + cfg.fmt(v) + '</span>');
      });
      h += '</div></div>';
    }

    // Alertas
    if (data.alertas && data.alertas.length) {
      h += '<div>' + sec('Alertas Activas');
      data.alertas.forEach(function(a) {
        h += '<div style="display:flex;align-items:flex-start;gap:8px;padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.04)">'
          + '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2.5" style="flex-shrink:0;margin-top:2px"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>'
          + '<span style="font-size:12px;color:rgba(255,255,255,0.8);line-height:1.45">' + esc(a) + '</span>'
          + '</div>';
      });
      h += '</div></div>';
    }

    panelBody.innerHTML = h;
  }

  // ═══ EXPOSE para merc-kpi cards y alertas ═══
  window.nyxOpenBrecha   = openBrecha;
  window.nyxOpenBadlar   = openBadlar;
  window.nyxOpenReservas = openReservas;
  window.nyxOpenAlerts   = openAlertasTicker;

})();
