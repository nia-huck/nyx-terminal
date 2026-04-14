/* ═══════════════════════════════════════════════════════════════
   Nyx Terminal — Live Monitor v2
   Tabs: Transcripcion | Alertas | Keywords
   ═══════════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  var API = window.NYX_API || 'http://localhost:8000';

  /* ── State ──────────────────────────────────────────────────── */
  var state = {
    sessionId: null,
    sse: null,
    minimized: false,
    dragging: false,
    dragOffX: 0,
    dragOffY: 0,
    segments: 0,
    alertCount: 0,
    totalWords: 0,
    uptimeStart: null,
    uptimeTimer: null,
    transcriptBuf: [],
    MAX_TRANSCRIPT: 120,
    activeTab: 'transcript',
  };

  /* ── DOM refs ───────────────────────────────────────────────── */
  var W, titlebar, body, dot, sessionLabel, iframe,
      transcript, alerts, segCount, alertBadge, alertTabBadge,
      wordsEl, uptimeEl,
      urlInput, startBtn, stopBtn;

  /* ── Helpers ────────────────────────────────────────────────── */
  function ytEmbedUrl(rawUrl) {
    if (!rawUrl) return '';
    var m = rawUrl.match(/(?:youtu\.be\/|[?&]v=|\/live\/)([A-Za-z0-9_-]{11})/);
    if (m) return 'https://www.youtube.com/embed/' + m[1] + '?autoplay=1&mute=0';
    return rawUrl;
  }

  function urgencyColor(u) {
    u = u || 0;
    if (u >= 9) return 'var(--alert-critical)';
    if (u >= 7) return 'var(--alert-high)';
    if (u >= 5) return 'var(--alert-med)';
    return 'var(--alert-low)';
  }

  function urgencyLabel(u) {
    u = u || 0;
    if (u >= 9) return 'CRITICO';
    if (u >= 7) return 'ALTO';
    if (u >= 5) return 'MEDIO';
    return 'INFO';
  }

  function escHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function fmtTime(s) {
    s = Math.round(s || 0);
    if (s < 60) return s + 's';
    if (s < 3600) return Math.floor(s / 60) + 'm ' + (s % 60) + 's';
    return Math.floor(s / 3600) + 'h ' + Math.floor((s % 3600) / 60) + 'm';
  }

  function nowLabel() {
    return new Date().toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  }

  /* ── Uptime ticker ──────────────────────────────────────────── */
  function startUptime() {
    state.uptimeStart = Date.now();
    if (state.uptimeTimer) clearInterval(state.uptimeTimer);
    state.uptimeTimer = setInterval(function () {
      if (uptimeEl) uptimeEl.textContent = fmtTime((Date.now() - state.uptimeStart) / 1000);
    }, 1000);
  }

  function stopUptime() {
    if (state.uptimeTimer) { clearInterval(state.uptimeTimer); state.uptimeTimer = null; }
    if (uptimeEl) uptimeEl.textContent = '0s';
  }

  /* ── Stats update ───────────────────────────────────────────── */
  function updateStats(segs, alerts, words) {
    if (segs !== undefined) { state.segments = segs; if (segCount) segCount.textContent = segs; }
    if (alerts !== undefined) { state.alertCount = alerts; if (alertBadge) alertBadge.textContent = alerts; }
    if (words !== undefined) { state.totalWords = words; if (wordsEl) wordsEl.textContent = words; }
  }

  /* ── Tabs ───────────────────────────────────────────────────── */
  function switchTab(name) {
    state.activeTab = name;
    document.querySelectorAll('.nlive-tab').forEach(function (btn) {
      btn.classList.toggle('nlive-tab--active', btn.dataset.tab === name);
    });
    document.querySelectorAll('.nlive-tabpanel').forEach(function (panel) {
      panel.classList.toggle('nlive-tabpanel--hidden', panel.id !== 'nlive-tab-' + name);
    });
    if (name === 'keywords') loadKeywords();
  }

  function initTabs() {
    document.querySelectorAll('.nlive-tab').forEach(function (btn) {
      btn.addEventListener('click', function () { switchTab(btn.dataset.tab); });
    });
  }

  /* ── SSE connection ─────────────────────────────────────────── */
  function connectSSE(sessionId) {
    if (state.sse) { state.sse.close(); state.sse = null; }

    var url = API + '/live/events/stream?session_id=' + encodeURIComponent(sessionId);
    state.sse = new EventSource(url);

    state.sse.addEventListener('transcript', function (e) {
      try { handleTranscript(JSON.parse(e.data)); } catch (_) {}
    });

    state.sse.addEventListener('alert', function (e) {
      try { handleAlert(JSON.parse(e.data)); } catch (_) {}
    });

    state.sse.addEventListener('status', function (e) {
      try { handleStatus(JSON.parse(e.data)); } catch (_) {}
    });

    state.sse.addEventListener('error', function (e) {
      try {
        var d = JSON.parse(e.data);
        var msg = (d.message || '?').split('\n')[0];
        appendTranscriptLine('<span class="nlive-line--error">[ERROR] ' + escHtml(msg) + '</span>');
        setDot('error');
      } catch (_) {}
    });

    state.sse.onerror = function () {
      setDot('error');
    };

    state.sse.onopen = function () {
      setDot('live');
      appendTranscriptLine('<span class="nlive-line--info">[' + nowLabel() + '] Conectado · sesion ' + escHtml(sessionId) + '</span>');
    };
  }

  function disconnectSSE() {
    if (state.sse) { state.sse.close(); state.sse = null; }
    setDot('idle');
  }

  /* ── Event handlers ─────────────────────────────────────────── */
  function handleTranscript(data) {
    var text = data.text || '';
    if (!text.trim()) return;
    state.segments++;
    state.totalWords += (data.words || text.split(' ').length);
    if (segCount) segCount.textContent = state.segments;
    if (wordsEl) wordsEl.textContent = state.totalWords;
    appendTranscriptLine(
      '<span class="nlive-ts-time">' + nowLabel() + '</span> ' + escHtml(text)
    );
  }

  function handleAlert(data) {
    state.alertCount++;
    if (alertBadge) alertBadge.textContent = state.alertCount;
    if (alertTabBadge) alertTabBadge.textContent = state.alertCount;

    var urgency = data.urgency || 0;
    var sector  = data.sector  || 'general';
    var keyword = data.keyword || '';
    var text    = data.text    || '';
    var color   = urgencyColor(urgency);
    var label   = urgencyLabel(urgency);

    // Highlight in transcript
    appendTranscriptLine(
      '<span class="nlive-alert-inline" style="--ac:' + color + '">' +
      '<b>[' + label + ']</b> ' + escHtml(keyword ? keyword + ': ' : '') + escHtml(text.slice(0, 140)) +
      '</span>'
    );

    // Chip in alerts panel
    var el = document.createElement('div');
    el.className = 'nlive-alert-chip';
    el.style.setProperty('--ac', color);
    el.innerHTML =
      '<div class="nlive-alert-chip__top">' +
        '<span class="nlive-alert-chip__badge">' + label + '</span>' +
        '<span class="nlive-alert-chip__sector">' + escHtml(sector) + '</span>' +
        '<span class="nlive-alert-chip__kw">' + escHtml(keyword) + '</span>' +
        '<span class="nlive-alert-chip__time">' + nowLabel() + '</span>' +
        '<button class="nlive-alert-chip__mark" title="Marcar">&#9733;</button>' +
      '</div>' +
      '<div class="nlive-alert-chip__text">' + escHtml(text.slice(0, 200)) + '</div>';

    // Mark toggle
    el.querySelector('.nlive-alert-chip__mark').addEventListener('click', function (e) {
      e.stopPropagation();
      el.classList.toggle('nlive-alert-chip--marked');
      this.style.color = el.classList.contains('nlive-alert-chip--marked') ? 'hsl(45,95%,60%)' : '';
    });

    if (alerts) {
      var empty = alerts.querySelector('.nlive-empty');
      if (empty) empty.remove();
      alerts.prepend(el);
      var chips = alerts.querySelectorAll('.nlive-alert-chip');
      if (chips.length > 60) chips[chips.length - 1].remove();
    }

    // Flash tab badge
    if (state.activeTab !== 'alerts' && alertTabBadge) {
      alertTabBadge.classList.add('nlive-badge--flash');
      setTimeout(function () { alertTabBadge.classList.remove('nlive-badge--flash'); }, 800);
    }

    // Pulse dot
    if (urgency >= 7 && dot) {
      dot.classList.add('nlive-dot--pulse');
      setTimeout(function () { dot.classList.remove('nlive-dot--pulse'); }, 2000);
    }

    // Desktop notification
    if (urgency >= 8 && window.Notification && Notification.permission === 'granted') {
      new Notification('Nyx Live — ' + label, {
        body: (keyword ? keyword + ': ' : '') + text.slice(0, 100),
        tag: 'nyx-live-' + Date.now(),
        silent: false,
      });
    }
  }

  function handleStatus(data) {
    var segs  = data.segments_count !== undefined ? data.segments_count : state.segments;
    var alts  = data.alerts_count   !== undefined ? data.alerts_count   : state.alertCount;
    var words = data.total_words    !== undefined ? data.total_words     : state.totalWords;
    updateStats(segs, alts, words);
    if (data.state === 'done') {
      appendTranscriptLine('<span class="nlive-line--info">[' + nowLabel() + '] Transcripcion completa · ' + segs + ' segmentos · ' + words + ' palabras</span>');
      setDot('idle');
      stopUptime();
    }
  }

  /* ── Transcript append ──────────────────────────────────────── */
  function appendTranscriptLine(html) {
    if (!transcript) return;
    var empty = transcript.querySelector('.nlive-empty');
    if (empty) empty.remove();

    var line = document.createElement('div');
    line.className = 'nlive-ts-line';
    line.innerHTML = html;
    transcript.appendChild(line);

    state.transcriptBuf.push(line);
    if (state.transcriptBuf.length > state.MAX_TRANSCRIPT) {
      var old = state.transcriptBuf.shift();
      if (old.parentNode) old.parentNode.removeChild(old);
    }

    var atBottom = transcript.scrollHeight - transcript.scrollTop - transcript.clientHeight < 60;
    if (atBottom) transcript.scrollTop = transcript.scrollHeight;
  }

  /* ── Dot indicator ──────────────────────────────────────────── */
  function setDot(status) {
    if (!dot) return;
    dot.className = 'nlive-dot nlive-dot--' + status;
  }

  /* ── Start / Stop ───────────────────────────────────────────── */
  async function startStream() {
    var url = urlInput ? urlInput.value.trim() : '';
    if (!url) { urlInput && urlInput.focus(); return; }

    if (startBtn) { startBtn.disabled = true; startBtn.textContent = 'Iniciando...'; }
    setDot('connecting');

    try {
      var resp = await fetch(API + '/live/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url, language: 'es' }),
      });

      if (!resp.ok) {
        var err = await resp.json().catch(function () { return {}; });
        var detail = err.detail || ('HTTP ' + resp.status);
        throw new Error(String(detail).split('\n')[0].slice(0, 200));
      }

      var data = await resp.json();
      if (!data.session_id) throw new Error(data.detail || 'Respuesta inesperada');
      state.sessionId = data.session_id;

      if (sessionLabel) sessionLabel.textContent = '· ' + state.sessionId;
      if (iframe) iframe.src = ytEmbedUrl(url);

      // Reset stats
      state.segments = 0; state.alertCount = 0; state.totalWords = 0;
      updateStats(0, 0, 0);
      startUptime();

      connectSSE(state.sessionId);

      if (startBtn) { startBtn.textContent = 'Conectado'; startBtn.disabled = true; }
      if (stopBtn)  stopBtn.style.display = '';

      if (window.Notification && Notification.permission === 'default') Notification.requestPermission();

    } catch (e) {
      var msg = (e.message || 'Error').split('\n')[0];
      appendTranscriptLine('<span class="nlive-line--error">[ERROR] ' + escHtml(msg) + '</span>');
      setDot('error');
      if (startBtn) { startBtn.textContent = 'Reintentar'; startBtn.disabled = false; }
    }
  }

  async function stopStream() {
    disconnectSSE();
    stopUptime();
    if (state.sessionId) {
      try { await fetch(API + '/live/stop/' + state.sessionId, { method: 'DELETE' }); } catch (_) {}
    }
    state.sessionId = null;
    if (iframe) iframe.src = '';
    if (sessionLabel) sessionLabel.textContent = '';
    if (startBtn) { startBtn.textContent = 'Iniciar'; startBtn.disabled = false; }
    if (stopBtn)  stopBtn.style.display = 'none';
    appendTranscriptLine('<span class="nlive-line--info">[' + nowLabel() + '] Stream detenido.</span>');
    setDot('idle');
  }

  /* ── Keywords ───────────────────────────────────────────────── */
  function loadKeywords() {
    var list = document.getElementById('nlive-kw-list');
    if (!list) return;
    list.innerHTML = '<div class="nlive-empty">Cargando...</div>';

    fetch(API + '/live/keywords')
      .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
      .then(function (data) {
        list.innerHTML = '';
        var entries = Object.entries(data).sort(function (a, b) {
          return (b[1].urgency || 0) - (a[1].urgency || 0);
        });
        if (!entries.length) {
          list.innerHTML = '<div class="nlive-empty">Sin keywords</div>';
          return;
        }
        entries.forEach(function (kv) {
          var kw = kv[0], meta = kv[1];
          var row = document.createElement('div');
          row.className = 'nlive-kw-row';
          row.dataset.kw = kw;
          row.innerHTML =
            '<span class="nlive-kw-row__urgency" style="background:' + urgencyColor(meta.urgency) + '">' + (meta.urgency || '?') + '</span>' +
            '<span class="nlive-kw-row__word">' + escHtml(kw) + '</span>' +
            '<span class="nlive-kw-row__sector">' + escHtml(meta.sector || '') + '</span>' +
            '<button class="nlive-kw-row__del" title="Eliminar">&times;</button>';
          row.querySelector('.nlive-kw-row__del').addEventListener('click', function () {
            deleteKeyword(kw, row);
          });
          list.appendChild(row);
        });
      })
      .catch(function (err) {
        list.innerHTML = '<div class="nlive-empty" style="color:hsl(0,72%,60%)">Error cargando keywords (¿Diaricat corriendo?)</div>';
      });
  }

  function addKeyword() {
    var inp = document.getElementById('nlive-kw-input');
    var sel = document.getElementById('nlive-kw-sector');
    var urg = document.getElementById('nlive-kw-urgency');
    if (!inp) return;
    var kw = inp.value.trim();
    if (!kw) { inp.focus(); return; }

    var btn = document.getElementById('nlive-kw-add-btn');
    if (btn) btn.disabled = true;

    fetch(API + '/live/keywords', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        keyword: kw,
        sector: sel ? sel.value : 'general',
        urgency: urg ? parseInt(urg.value) : 5,
      }),
    })
      .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
      .then(function () {
        inp.value = '';
        loadKeywords();
      })
      .catch(function () {
        inp.style.borderColor = 'hsl(0,72%,50%)';
        setTimeout(function () { inp.style.borderColor = ''; }, 1500);
      })
      .finally(function () {
        if (btn) btn.disabled = false;
      });
  }

  function deleteKeyword(kw, rowEl) {
    if (rowEl) rowEl.style.opacity = '0.4';
    fetch(API + '/live/keywords/' + encodeURIComponent(kw), { method: 'DELETE' })
      .then(function (r) {
        if (r.ok && rowEl) rowEl.remove();
        else if (rowEl) rowEl.style.opacity = '';
      })
      .catch(function () { if (rowEl) rowEl.style.opacity = ''; });
  }

  function initKeywords() {
    var addBtn = document.getElementById('nlive-kw-add-btn');
    if (addBtn) addBtn.addEventListener('click', addKeyword);

    var inp = document.getElementById('nlive-kw-input');
    if (inp) inp.addEventListener('keydown', function (e) { if (e.key === 'Enter') addKeyword(); });
  }

  /* ── Dragging ───────────────────────────────────────────────── */
  function initDrag() {
    if (!titlebar || !W) return;
    titlebar.addEventListener('mousedown', function (e) {
      if (e.target.closest('button')) return;
      state.dragging = true;
      var rect = W.getBoundingClientRect();
      state.dragOffX = e.clientX - rect.left;
      state.dragOffY = e.clientY - rect.top;
      W.style.transition = 'none';
      W.style.userSelect = 'none';
      e.preventDefault();
    });
    document.addEventListener('mousemove', function (e) {
      if (!state.dragging) return;
      var x = Math.max(0, Math.min(window.innerWidth  - W.offsetWidth,  e.clientX - state.dragOffX));
      var y = Math.max(0, Math.min(window.innerHeight - W.offsetHeight, e.clientY - state.dragOffY));
      W.style.left = x + 'px';
      W.style.top  = y + 'px';
      W.style.right = 'auto';
      W.style.bottom = 'auto';
    });
    document.addEventListener('mouseup', function () {
      if (!state.dragging) return;
      state.dragging = false;
      W.style.transition = '';
      W.style.userSelect = '';
    });
  }

  /* ── Minimize / Open / Close ────────────────────────────────── */
  function minimize() {
    state.minimized = true;
    W.classList.add('nlive-minimized');
    if (body) body.style.display = 'none';
    var sb = document.getElementById('nyx-live-statsbar');
    if (sb) sb.style.display = 'none';
  }

  function restore() {
    state.minimized = false;
    W.classList.remove('nlive-minimized');
    if (body) body.style.display = '';
    var sb = document.getElementById('nyx-live-statsbar');
    if (sb) sb.style.display = '';
  }

  function open() { W.style.display = ''; restore(); }

  function close() {
    stopStream();
    W.style.display = 'none';
    var btn = document.getElementById('btn-live');
    if (btn) btn.classList.remove('active');
  }

  /* ── Sidebar button ─────────────────────────────────────────── */
  function initSidebarBtn() {
    var btn = document.getElementById('btn-live');
    if (!btn) return;
    btn.addEventListener('click', function () {
      if (!W.style.display || W.style.display === 'none') {
        btn.classList.add('active');
        open();
      } else {
        btn.classList.remove('active');
        close();
      }
    });
  }

  /* ── Init ───────────────────────────────────────────────────── */
  function init() {
    W            = document.getElementById('nyx-live-window');
    titlebar     = document.getElementById('nyx-live-titlebar');
    body         = document.getElementById('nyx-live-body');
    dot          = document.getElementById('nyx-live-dot');
    sessionLabel = document.getElementById('nyx-live-session-label');
    iframe       = document.getElementById('nyx-live-iframe');
    transcript   = document.getElementById('nyx-live-transcript');
    alerts       = document.getElementById('nyx-live-alerts');
    segCount     = document.getElementById('nyx-live-seg-count');
    alertBadge   = document.getElementById('nyx-live-alert-count');
    alertTabBadge= document.getElementById('nyx-live-alert-badge');
    wordsEl      = document.getElementById('nyx-live-words');
    uptimeEl     = document.getElementById('nyx-live-uptime');
    urlInput     = document.getElementById('nyx-live-url-input');
    startBtn     = document.getElementById('nyx-live-start-btn');
    stopBtn      = document.getElementById('nyx-live-stop-btn');

    if (!W) return;

    initDrag();
    initTabs();
    initSidebarBtn();
    initKeywords();

    document.getElementById('nyx-live-minimize').addEventListener('click', function () {
      state.minimized ? restore() : minimize();
    });
    document.getElementById('nyx-live-close').addEventListener('click', close);

    if (startBtn) startBtn.addEventListener('click', startStream);
    if (stopBtn)  stopBtn.addEventListener('click', stopStream);
    if (urlInput) urlInput.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') startStream();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
