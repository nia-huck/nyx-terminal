/* ═══════════════════════════════════════════════════════════════
   Nyx Terminal — Map Module
   Leaflet + Clusters + Province boundaries
   Integrated with nyx-app.js design system
   ═══════════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  var API = window.NYX_API || 'http://localhost:8000';

  // ── Color System ──────────────────────────────────────────
  var TIPO_COLORS = {
    economico:   { hex: '#8b5cf6', label: 'Economico' },
    sindical:    { hex: '#ef4444', label: 'Sindical' },
    regulatorio: { hex: '#f59e0b', label: 'Regulatorio' },
    politico:    { hex: '#06b6d4', label: 'Politico' },
    climatico:   { hex: '#34d399', label: 'Climatico' },
    informativo: { hex: '#6b7280', label: 'Informativo' },
  };

  var URGENCIA_COLORS = {
    critico:  { bg: 'hsl(0 78% 58% / 0.15)',   text: 'hsl(0 78% 68%)',   border: 'hsl(0 78% 58% / 0.25)' },
    alto:     { bg: 'hsl(38 92% 55% / 0.15)',   text: 'hsl(38 92% 65%)',  border: 'hsl(38 92% 55% / 0.25)' },
    moderado: { bg: 'hsl(268 70% 58% / 0.15)',  text: 'hsl(268 70% 72%)', border: 'hsl(268 70% 58% / 0.25)' },
    bajo:     { bg: 'hsl(152 69% 53% / 0.12)',  text: 'hsl(152 69% 63%)', border: 'hsl(152 69% 53% / 0.2)' },
  };

  var PROVINCIAS_AR = new Set([
    'CABA','Buenos Aires','Cordoba','Santa Fe','Rosario','Mendoza','Tucuman',
    'Salta','Entre Rios','Misiones','Chaco','Corrientes','Santiago del Estero',
    'San Juan','Jujuy','Rio Negro','Neuquen','Formosa','Chubut','San Luis',
    'Catamarca','La Rioja','La Pampa','Santa Cruz','Tierra del Fuego',
  ]);

  // ── State ─────────────────────────────────────────────────
  var map = null;
  var clusterGroup = null;
  var markersList = [];
  var events = [];
  var provinciasLayer = null;
  var selectedProvincia = null;

  // ── Exposed init function ─────────────────────────────────
  window.initNyxMap = function () {
    if (map) {
      map.invalidateSize();
      return;
    }
    createMap();
    loadProvincias();
    loadEvents();
  };

  // ── Map Setup ─────────────────────────────────────────────
  function createMap() {
    map = L.map('nyx-leaflet-map', {
      center: [-38.0, -64.0],
      zoom: 4,
      minZoom: 3,
      zoomControl: true,
      attributionControl: false,
      preferCanvas: true,
    });

    // CartoDB dark (global)
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png', {
      subdomains: 'abcd',
      maxZoom: 19,
      opacity: 0.35,
    }).addTo(map);

    // IGN Argenmap Oscuro (Argentine labels)
    L.tileLayer('https://wms.ign.gob.ar/geoserver/gwc/service/tms/1.0.0/argenmap_oscuro@EPSG%3A3857@png/{z}/{x}/{y}.png', {
      tms: true,
      maxZoom: 18,
      opacity: 0.55,
      pane: 'overlayPane',
    }).addTo(map);

    map.zoomControl.setPosition('bottomright');

    // Islas Malvinas
    var malvinasIcon = L.divIcon({
      html: '<div style="font-family:var(--font-display);font-size:11px;font-weight:600;color:hsl(268,70%,72%);text-align:center;text-shadow:0 0 8px rgba(139,92,246,0.4)">Islas Malvinas<br><span style="font-size:9px;font-weight:400;opacity:0.6">Republica Argentina</span></div>',
      className: '',
      iconSize: [160, 36],
      iconAnchor: [80, 18],
    });
    L.marker([-51.75, -59.0], { icon: malvinasIcon, interactive: false, zIndexOffset: 9000 }).addTo(map);
    L.circle([-51.75, -59.0], {
      radius: 120000,
      color: '#8b5cf6', weight: 1.2, opacity: 0.3,
      fillColor: '#8b5cf6', fillOpacity: 0.04,
      dashArray: '6 4', interactive: false,
    }).addTo(map);

    // Cluster group
    clusterGroup = L.markerClusterGroup({
      maxClusterRadius: 45,
      spiderfyOnMaxZoom: true,
      showCoverageOnHover: false,
      zoomToBoundsOnClick: true,
      spiderfyDistanceMultiplier: 1.8,
      chunkedLoading: true,
      iconCreateFunction: createClusterIcon,
    });
    map.addLayer(clusterGroup);

    // Feed back button
    var backBtn = document.getElementById('map-feed-back');
    if (backBtn) {
      backBtn.addEventListener('click', function () {
        selectedProvincia = null;
        if (provinciasLayer) {
          provinciasLayer.eachLayer(function (l) { provinciasLayer.resetStyle(l); });
        }
        map.setView([-38.0, -64.0], 4);
        renderMarkers();
        renderFeed();
      });
    }
  }

  // ── Province GeoJSON ──────────────────────────────────────
  async function loadProvincias() {
    try {
      var res = await fetch('data/argentina-provincias.geojson');
      var geojson = await res.json();

      provinciasLayer = L.geoJSON(geojson, {
        style: function () {
          return {
            color: '#8b5cf6',
            weight: 1.2,
            opacity: 0.35,
            fillColor: '#8b5cf6',
            fillOpacity: 0.03,
          };
        },
        onEachFeature: function (feature, layer) {
          layer.on({
            mouseover: onHover,
            mouseout: onOut,
            click: onClick,
          });
        },
      });

      provinciasLayer.addTo(map);
    } catch (e) {
      console.warn('[nyx-map] Could not load provinces:', e.message);
    }
  }

  function onHover(e) {
    var layer = e.target;
    var name = layer.feature.properties.nombre;
    if (selectedProvincia && name === selectedProvincia) return;
    layer.setStyle({ weight: 2, opacity: 0.6, fillOpacity: 0.08 });
    layer.bringToFront();

    var count = events.filter(function (ev) { return matchProv(ev.provincia, name); }).length;
    layer.bindTooltip('<strong>' + name + '</strong><br>' + count + ' eventos', {
      className: 'nyx-tooltip',
      sticky: true,
    }).openTooltip(e.latlng);
  }

  function onOut(e) {
    var name = e.target.feature.properties.nombre;
    if (selectedProvincia === name) return;
    provinciasLayer.resetStyle(e.target);
    e.target.closeTooltip();
  }

  function onClick(e) {
    var name = e.target.feature.properties.nombre;

    if (selectedProvincia === name) {
      selectedProvincia = null;
      provinciasLayer.resetStyle(e.target);
      map.setView([-38.0, -64.0], 4);
      renderMarkers();
      renderFeed();
      return;
    }

    if (provinciasLayer) {
      provinciasLayer.eachLayer(function (l) { provinciasLayer.resetStyle(l); });
    }

    selectedProvincia = name;
    e.target.setStyle({ weight: 2.5, opacity: 0.85, fillOpacity: 0.12, color: '#a78bfa', fillColor: '#8b5cf6' });
    e.target.bringToFront();
    map.fitBounds(e.target.getBounds(), { padding: [40, 40], maxZoom: 8 });

    renderMarkers();
    renderFeed();
  }

  function matchProv(eventProv, geoName) {
    if (!eventProv || !geoName) return false;
    var a = eventProv.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
    var b = geoName.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
    return a === b || a.indexOf(b) !== -1 || b.indexOf(a) !== -1;
  }

  // ── Cluster Icon ──────────────────────────────────────────
  function createClusterIcon(cluster) {
    var children = cluster.getAllChildMarkers();
    var count = children.length;
    var tally = {};
    var maxUrg = 0;

    children.forEach(function (m) {
      var ev = m._nyxEvent;
      if (!ev) return;
      tally[ev.tipo] = (tally[ev.tipo] || 0) + 1;
      if (ev.urgencia > maxUrg) maxUrg = ev.urgencia;
    });

    var dominant = Object.entries(tally).sort(function (a, b) { return b[1] - a[1]; })[0];
    var domColor = (dominant && TIPO_COLORS[dominant[0]]) ? TIPO_COLORS[dominant[0]].hex : '#8b5cf6';
    var size = Math.max(36, Math.min(60, 30 + count * 0.4));

    var dots = Object.entries(tally)
      .sort(function (a, b) { return b[1] - a[1]; })
      .slice(0, 4)
      .map(function (entry) {
        var c = TIPO_COLORS[entry[0]] ? TIPO_COLORS[entry[0]].hex : '#6b7280';
        return '<span style="width:5px;height:5px;border-radius:50%;background:' + c + ';box-shadow:0 0 4px ' + c + '"></span>';
      }).join('');

    return L.divIcon({
      html: '<div style="width:' + size + 'px;height:' + size + 'px;border-radius:50%;'
        + 'background:rgba(10,7,20,0.85);border:2px solid ' + domColor + '40;'
        + 'display:flex;flex-direction:column;align-items:center;justify-content:center;'
        + 'box-shadow:0 0 16px ' + domColor + '30;font-family:var(--font-mono);font-size:12px;font-weight:600;color:hsl(var(--foreground))">'
        + '<span>' + count + '</span>'
        + '<div style="display:flex;gap:2px;margin-top:2px">' + dots + '</div>'
        + '</div>',
      className: '',
      iconSize: [size + 16, size + 16],
      iconAnchor: [(size + 16) / 2, (size + 16) / 2],
    });
  }

  // ── Load Events ───────────────────────────────────────────
  async function loadEvents() {
    var data = window.nyxCache && window.nyxCache.eventos;
    if (!data) {
      try {
        var res = await fetch(API + '/eventos');
        if (res.ok) data = await res.json();
      } catch (e) { /* ignore */ }
    }
    if (!data) {
      try {
        var res2 = await fetch('data/nyx-events-demo.json');
        data = await res2.json();
      } catch (e) { data = []; }
    }
    events = Array.isArray(data) ? data : [];
    renderMarkers();
    renderFeed();
  }

  // ── Markers ───────────────────────────────────────────────
  function renderMarkers() {
    if (!clusterGroup) return;
    clusterGroup.clearLayers();
    markersList = [];

    var filtered = events;
    if (selectedProvincia) {
      filtered = filtered.filter(function (e) { return matchProv(e.provincia, selectedProvincia); });
    }

    var geolocated = filtered.filter(function (e) { return e.lat != null && e.lon != null; });

    geolocated.forEach(function (ev) {
      var tipo = ev.tipo || 'informativo';
      var color = TIPO_COLORS[tipo] ? TIPO_COLORS[tipo].hex : '#6b7280';
      var size = Math.max(14, Math.min(22, 10 + (ev.urgencia || 0) * 1.2));
      var isUrgent = (ev.urgencia || 0) >= 8;

      var icon = L.divIcon({
        html: '<div style="width:' + size + 'px;height:' + size + 'px;border-radius:50%;'
          + 'background:' + color + ';box-shadow:0 0 8px ' + color + '60;'
          + 'border:2px solid ' + color + '80;'
          + (isUrgent ? 'animation:pulse-glow 1.5s ease-in-out infinite;' : '')
          + '"></div>',
        className: '',
        iconSize: [size + 8, size + 8],
        iconAnchor: [(size + 8) / 2, (size + 8) / 2],
      });

      var marker = L.marker([ev.lat, ev.lon], {
        icon: icon,
        zIndexOffset: (ev.urgencia || 0) * 100,
      });

      marker.bindPopup(buildPopup(ev), { maxWidth: 300, closeButton: true });
      marker._nyxEvent = ev;
      markersList.push(marker);
    });

    clusterGroup.addLayers(markersList);

    // Update event count stat
    var countEl = document.getElementById('map-stat-eventos');
    if (countEl) countEl.textContent = events.length;
  }

  function buildPopup(ev) {
    var tipo = TIPO_COLORS[ev.tipo] || TIPO_COLORS.informativo;
    var urgClass = (ev.urgencia || 0) >= 8 ? 'critico' : (ev.urgencia || 0) >= 6 ? 'alto' : (ev.urgencia || 0) >= 4 ? 'moderado' : 'bajo';
    var urgLabel = urgClass === 'critico' ? 'Critico' : urgClass === 'alto' ? 'Alto' : urgClass === 'moderado' ? 'Moderado' : 'Bajo';
    var urgStyle = URGENCIA_COLORS[urgClass];
    var esc = window.nyxEscapeHtml || function (s) { return s || ''; };

    var tags = '';
    if (ev.activos_afectados && ev.activos_afectados.length) {
      tags = '<div style="display:flex;gap:4px;flex-wrap:wrap;margin-top:8px">'
        + ev.activos_afectados.map(function (a) {
          return '<span style="font-family:var(--font-mono);font-size:9px;padding:2px 6px;border-radius:4px;background:rgba(255,255,255,0.06);color:hsl(var(--muted-foreground))">' + esc(a) + '</span>';
        }).join('')
        + '</div>';
    }

    return '<div style="min-width:220px">'
      + '<div style="display:flex;align-items:center;gap:6px;margin-bottom:8px">'
      + '<span style="width:8px;height:8px;border-radius:50%;background:' + tipo.hex + ';box-shadow:0 0 6px ' + tipo.hex + '"></span>'
      + '<span style="color:' + tipo.hex + ';font-family:var(--font-mono);font-size:10px;font-weight:600;text-transform:uppercase">' + tipo.label + '</span>'
      + '<span style="color:hsl(var(--muted-foreground));font-size:10px;margin-left:auto">' + esc(ev.provincia) + '</span>'
      + '</div>'
      + '<div style="font-weight:600;font-size:13px;line-height:1.4;margin-bottom:6px">' + esc(ev.titulo) + '</div>'
      + '<div style="font-size:11px;color:hsl(var(--muted-foreground));line-height:1.5">' + esc(ev.resumen) + '</div>'
      + tags
      + '<div style="display:flex;align-items:center;gap:8px;margin-top:10px;padding-top:8px;border-top:1px solid rgba(255,255,255,0.06)">'
      + '<span style="font-family:var(--font-mono);font-size:10px;padding:2px 8px;border-radius:4px;background:' + urgStyle.bg + ';color:' + urgStyle.text + ';border:1px solid ' + urgStyle.border + '">' + urgLabel + ' ' + (ev.urgencia || 0) + '/10</span>'
      + (ev.fuente_url ? '<a href="' + ev.fuente_url + '" target="_blank" rel="noopener" style="font-size:10px;color:hsl(var(--primary));text-decoration:none;margin-left:auto">' + esc(ev.fuente || 'Fuente') + ' &rarr;</a>' : '')
      + '</div></div>';
  }

  // ── Feed Panel ────────────────────────────────────────────
  function renderFeed() {
    var container = document.getElementById('map-feed-list');
    var titleEl = document.getElementById('map-feed-title');
    var countEl = document.getElementById('map-feed-count');
    var backBtn = document.getElementById('map-feed-back');
    if (!container) return;

    var filtered = events;
    if (selectedProvincia) {
      filtered = filtered.filter(function (e) { return matchProv(e.provincia, selectedProvincia); });
    }

    if (titleEl) titleEl.textContent = selectedProvincia || 'Todas las provincias';
    if (countEl) countEl.textContent = filtered.length;
    if (backBtn) backBtn.classList.toggle('visible', !!selectedProvincia);

    if (!selectedProvincia) {
      // Group by province
      var byProv = {};
      filtered.forEach(function (ev) {
        if (!ev.provincia) return;
        if (!byProv[ev.provincia]) byProv[ev.provincia] = { events: [], maxUrg: 0 };
        byProv[ev.provincia].events.push(ev);
        if ((ev.urgencia || 0) > byProv[ev.provincia].maxUrg) byProv[ev.provincia].maxUrg = ev.urgencia;
      });

      var sorted = Object.entries(byProv).sort(function (a, b) {
        if (b[1].maxUrg !== a[1].maxUrg) return b[1].maxUrg - a[1].maxUrg;
        return b[1].events.length - a[1].events.length;
      });

      var html = '';
      sorted.forEach(function (entry) {
        var prov = entry[0];
        var data = entry[1];
        var urgColor = data.maxUrg >= 8 ? 'hsl(0,78%,58%)' : data.maxUrg >= 6 ? 'hsl(38,92%,55%)' : data.maxUrg >= 4 ? 'hsl(268,70%,58%)' : 'hsl(152,69%,53%)';
        var pct = Math.min(100, data.maxUrg * 10);
        var isIntl = !PROVINCIAS_AR.has(prov);

        html += '<div class="prov-card" data-prov="' + prov.replace(/"/g, '&quot;') + '">'
          + '<span class="prov-card__name">' + (window.nyxEscapeHtml ? window.nyxEscapeHtml(prov) : prov) + (isIntl ? ' <span style="font-size:9px;color:hsl(192,80%,50%)">[EXT]</span>' : '') + '</span>'
          + '<span class="prov-card__count">' + data.events.length + '</span>'
          + '<div class="prov-card__urgency"><div class="prov-card__urgency-fill" style="width:' + pct + '%;background:' + urgColor + '"></div></div>'
          + '</div>';
      });

      container.innerHTML = html;

      // Attach click handlers
      container.querySelectorAll('.prov-card').forEach(function (card) {
        card.addEventListener('click', function () {
          var prov = card.dataset.prov;
          selectProvByName(prov);
        });
      });
    } else {
      // Event detail list
      var sortedEvents = filtered.slice().sort(function (a, b) { return (b.urgencia || 0) - (a.urgencia || 0); });
      var html2 = '';
      sortedEvents.forEach(function (ev) {
        var tipo = TIPO_COLORS[ev.tipo] || TIPO_COLORS.informativo;
        var urgClass = (ev.urgencia || 0) >= 8 ? 'critico' : (ev.urgencia || 0) >= 6 ? 'alto' : (ev.urgencia || 0) >= 4 ? 'moderado' : 'bajo';
        var urgStyle = URGENCIA_COLORS[urgClass];

        html2 += '<div class="prov-card" data-evid="' + ev.id + '">'
          + '<div style="display:flex;align-items:center;gap:6px;width:100%">'
          + '<span style="width:6px;height:6px;border-radius:50%;background:' + tipo.hex + ';flex-shrink:0"></span>'
          + '<span class="prov-card__name" style="flex:1;font-size:11px;line-height:1.4">' + (window.nyxEscapeHtml ? window.nyxEscapeHtml(ev.titulo) : ev.titulo) + '</span>'
          + '<span style="font-family:var(--font-mono);font-size:10px;padding:1px 6px;border-radius:4px;background:' + urgStyle.bg + ';color:' + urgStyle.text + ';flex-shrink:0">' + (ev.urgencia || 0) + '</span>'
          + '</div></div>';
      });
      container.innerHTML = html2;

      // Click to focus on marker
      container.querySelectorAll('.prov-card[data-evid]').forEach(function (card) {
        card.addEventListener('click', function () {
          var evId = parseInt(card.dataset.evid);
          var marker = markersList.find(function (m) { return m._nyxEvent && m._nyxEvent.id === evId; });
          if (marker) {
            clusterGroup.zoomToShowLayer(marker, function () { marker.openPopup(); });
          }
        });
      });
    }
  }

  function selectProvByName(name) {
    selectedProvincia = name;

    if (provinciasLayer) {
      provinciasLayer.eachLayer(function (layer) {
        if (matchProv(layer.feature.properties.nombre, name)) {
          layer.setStyle({ weight: 2.5, opacity: 0.85, fillOpacity: 0.12, color: '#a78bfa', fillColor: '#8b5cf6' });
          layer.bringToFront();
          map.fitBounds(layer.getBounds(), { padding: [40, 40], maxZoom: 8 });
        } else {
          provinciasLayer.resetStyle(layer);
        }
      });
    }

    renderMarkers();
    renderFeed();
  }

  // Leaflet tooltip styling
  var tooltipStyle = document.createElement('style');
  tooltipStyle.textContent = '.nyx-tooltip{font-family:var(--font-body)!important;font-size:12px!important;background:rgba(10,7,20,0.92)!important;border:1px solid rgba(140,100,230,0.18)!important;border-radius:8px!important;box-shadow:0 4px 20px rgba(0,0,0,0.6)!important;color:hsl(var(--foreground))!important;padding:8px 12px!important}.leaflet-tooltip-top:before,.leaflet-tooltip-bottom:before,.leaflet-tooltip-left:before,.leaflet-tooltip-right:before{border-color:transparent!important}';
  document.head.appendChild(tooltipStyle);

})();
