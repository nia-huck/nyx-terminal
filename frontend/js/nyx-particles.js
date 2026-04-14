/* ═══════════════════════════════════════════════════════════════
   Nyx Terminal — Particle System v2
   Denser, multi-layer, mouse-reactive
   ═══════════════════════════════════════════════════════════════ */

(function () {
  'use strict';


  var canvas = document.getElementById('nyx-particles');
  if (!canvas) return;
  var ctx = canvas.getContext('2d');
  if (!ctx) return;

  var particles = [];
  var animId = 0;

  // ── Particle factory — 3x denser, more violet bias ────────
  function createParticle(stagger) {
    var lifespan = 4000 + Math.random() * 12000;
    var depth = Math.random();
    var layer = depth < 0.35 ? 'far' : depth < 0.7 ? 'mid' : 'near';

    // More violet hue bias
    var hueRoll = Math.random();
    var hue = hueRoll < 0.45 ? 268 + Math.random() * 12 - 6   // violet cluster
            : hueRoll < 0.65 ? 240 + Math.random() * 20        // blue-indigo
            : hueRoll < 0.80 ? 192 + Math.random() * 15        // cyan accent
            : 0;                                                // white

    return {
      baseX: Math.random() * canvas.width,
      baseY: Math.random() * canvas.height,
      size: layer === 'far'  ? Math.random() * 0.5 + 0.2
          : layer === 'mid'  ? Math.random() * 1.0 + 0.4
          :                    Math.random() * 1.6 + 0.7,
      depth: depth,
      layer: layer,
      driftRadius: layer === 'far' ? Math.random() * 12 + 4
                 : layer === 'mid' ? Math.random() * 22 + 8
                 :                   Math.random() * 30 + 10,
      driftSpeed: layer === 'far' ? Math.random() * 0.00015 + 0.0001
                : layer === 'mid' ? Math.random() * 0.0003 + 0.00015
                :                   Math.random() * 0.0004 + 0.0002,
      driftPhaseX: Math.random() * Math.PI * 2,
      driftPhaseY: Math.random() * Math.PI * 2,
      birth: performance.now() + (stagger ? Math.random() * 6000 : 0),
      lifespan: lifespan,
      maxOpacity: layer === 'far'  ? Math.random() * 0.18 + 0.06
               : layer === 'mid'  ? Math.random() * 0.35 + 0.12
               :                    Math.random() * 0.45 + 0.18,
      flickerSpeed: Math.random() * 0.0018 + 0.0006,
      flickerDepth: Math.random() * 0.35 + 0.08,
      flickerPhase: Math.random() * Math.PI * 2,
      hue: hue,
      sat: hue === 0 ? 0 : Math.random() * 30 + 40,
      light: Math.random() * 15 + 78,
    };
  }

  function respawn(p) {
    var n = createParticle(false);
    Object.assign(p, n);
    p.birth = performance.now();
  }

  function init() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    // ~3x density: divide by 3500 instead of 9000, cap at 200
    var count = Math.min(Math.floor(canvas.width * canvas.height / 3500), 200);
    particles = [];
    for (var i = 0; i < count; i++) {
      particles.push(createParticle(true));
    }
  }

  function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    var now = performance.now();
    var cw = canvas.width;
    var ch = canvas.height;

    for (var i = 0; i < particles.length; i++) {
      var p = particles[i];
      var age = now - p.birth;
      if (age < 0) continue;
      var remaining = p.lifespan - age;
      if (remaining <= 0) { respawn(p); continue; }

      // Smoother envelope: softer fade in/out
      var fadeIn = Math.min(age / 1200, 1);
      var fadeOut = Math.min(remaining / 2000, 1);
      var envelope = fadeIn * fadeOut;

      var flicker = 1 - p.flickerDepth * (0.5 + 0.5 * Math.sin(now * p.flickerSpeed + p.flickerPhase));
      var alpha = p.maxOpacity * envelope * flicker;
      if (alpha < 0.008) continue;

      // Drift position
      var x = p.baseX + Math.sin(now * p.driftSpeed + p.driftPhaseX) * p.driftRadius;
      var y = p.baseY + Math.cos(now * p.driftSpeed * 0.8 + p.driftPhaseY) * p.driftRadius;

      // Core dot
      ctx.beginPath();
      ctx.arc(x, y, p.size, 0, Math.PI * 2);
      ctx.fillStyle = 'hsla(' + p.hue + ',' + p.sat + '%,' + p.light + '%,' + alpha + ')';
      ctx.fill();

      // Glow halo for near-layer particles
      if (p.layer === 'near' && alpha > 0.10) {
        ctx.beginPath();
        ctx.arc(x, y, p.size * 4, 0, Math.PI * 2);
        ctx.fillStyle = 'hsla(' + p.hue + ',' + p.sat + '%,' + p.light + '%,' + (alpha * 0.05) + ')';
        ctx.fill();
      } else if (p.layer === 'mid' && alpha > 0.14) {
        ctx.beginPath();
        ctx.arc(x, y, p.size * 3, 0, Math.PI * 2);
        ctx.fillStyle = 'hsla(' + p.hue + ',' + p.sat + '%,' + p.light + '%,' + (alpha * 0.035) + ')';
        ctx.fill();
      }
    }
    animId = requestAnimationFrame(draw);
  }

  function onResize() {
    var oldW = canvas.width || 1;
    var oldH = canvas.height || 1;
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    if (particles.length > 0) {
      var sx = canvas.width / oldW;
      var sy = canvas.height / oldH;
      for (var i = 0; i < particles.length; i++) {
        particles[i].baseX *= sx;
        particles[i].baseY *= sy;
      }
    }
  }

  window.addEventListener('resize', onResize);

  // Start after short delay
  setTimeout(function () {
    init();
    draw();
    canvas.classList.add('active');
  }, 600);
})();
