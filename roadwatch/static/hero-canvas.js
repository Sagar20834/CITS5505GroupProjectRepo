/* RoadWatch landing hero canvas. Perspective road grid with scan pulses and report nodes. */
(function () {
  "use strict";

  var DEFAULT_ACCENT = [32, 227, 178];
  var DEFAULT_SECONDARY = [0, 213, 255];
  var DEFAULT_ALERT = [255, 42, 138];

  function parseRgb(value, fallback) {
    var match = String(value || "").match(/(\d{1,3})[\s,]+(\d{1,3})[\s,]+(\d{1,3})/);
    if (!match) return fallback.slice();
    return [
      Math.max(0, Math.min(255, Number(match[1]))),
      Math.max(0, Math.min(255, Number(match[2]))),
      Math.max(0, Math.min(255, Number(match[3]))),
    ];
  }

  function readPalette() {
    var styles = window.getComputedStyle(document.documentElement);
    return {
      accent: parseRgb(styles.getPropertyValue("--rw-hero-accent-rgb"), DEFAULT_ACCENT),
      secondary: parseRgb(styles.getPropertyValue("--rw-hero-secondary-rgb"), DEFAULT_SECONDARY),
      alert: parseRgb(styles.getPropertyValue("--rw-hero-alert-rgb"), DEFAULT_ALERT),
      gridStrength: Math.max(0.7, Math.min(1.8, Number(styles.getPropertyValue("--rw-hero-grid-strength")) || 1)),
    };
  }

  function rgba(rgb, alpha) {
    return "rgba(" + rgb[0] + "," + rgb[1] + "," + rgb[2] + "," + alpha + ")";
  }

  function lerp(a, b, t) {
    return a + (b - a) * t;
  }

  function init(canvas) {
    if (!canvas || canvas.dataset.roadwatchHeroReady === "true") return;
    canvas.dataset.roadwatchHeroReady = "true";

    var ctx = canvas.getContext("2d");
    if (!ctx) return;

    var palette = readPalette();
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    var motionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    var reduced = motionQuery.matches;
    var width = 0;
    var height = 0;
    var horizonY = 0;
    var groundBottomY = 0;
    var rafId = 0;
    var running = false;
    var isVisible = true;
    var lastFrame = 0;
    var lastPulseAt = 0;
    var longLines = 14;
    var latLines = 9;
    var pulses = [];
    var nodes = [];
    var vp = { x: 0, y: 0 };
    var vpTarget = { x: 0, y: 0 };
    var defaultVp = { x: 0, y: 0 };
    var observer = null;

    function resize() {
      var rect = canvas.getBoundingClientRect();
      width = Math.max(1, Math.floor(rect.width));
      height = Math.max(1, Math.floor(rect.height));
      canvas.width = Math.floor(width * dpr);
      canvas.height = Math.floor(height * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      horizonY = height * 0.4;
      groundBottomY = height * 1.07;
      defaultVp.x = width * 0.76;
      defaultVp.y = horizonY;
      vp.x = defaultVp.x;
      vp.y = defaultVp.y;
      vpTarget.x = defaultVp.x;
      vpTarget.y = defaultVp.y;
      rebuildNodes();
      if (reduced) renderStaticFrame();
    }

    function rebuildNodes() {
      nodes = [];
      for (var i = 0; i < 24; i++) {
        nodes.push({
          u: Math.random() * (longLines - 1),
          depth: Math.pow(Math.random(), 1.55),
          phase: Math.random() * Math.PI * 2,
          flash: 0,
          alert: Math.random() < 0.16,
        });
      }
    }

    function project(u, depth) {
      var nearLeft = -width * 0.12;
      var nearRight = width * 1.12;
      var t = 1 - depth;
      var perspective = Math.pow(t, 1.5);
      var nearX = lerp(nearLeft, nearRight, u / (longLines - 1));

      return {
        x: lerp(nearX, vp.x, perspective),
        y: lerp(groundBottomY, horizonY, perspective),
        depth: depth,
      };
    }

    function drawGrid() {
      for (var i = 0; i < longLines; i++) {
        var near = project(i, 1);
        var far = project(i, 0);
        var center = (longLines - 1) / 2;
        var decay = Math.abs(i - center) / center;
        var gradient = ctx.createLinearGradient(near.x, near.y, far.x, far.y);

        gradient.addColorStop(0, rgba(palette.accent, Math.min(0.88, (0.58 - decay * 0.24) * palette.gridStrength)));
        gradient.addColorStop(0.55, rgba(palette.secondary, Math.min(0.42, 0.16 * palette.gridStrength)));
        gradient.addColorStop(1, rgba(palette.accent, Math.min(0.12, 0.02 * palette.gridStrength)));
        ctx.strokeStyle = gradient;
        ctx.lineWidth = i === 0 || i === longLines - 1 ? 1.6 : 1;
        ctx.beginPath();
        ctx.moveTo(near.x, near.y);
        ctx.lineTo(far.x, far.y);
        ctx.stroke();
      }

      for (var j = 0; j < latLines; j++) {
        var depth = Math.pow(j / (latLines - 1), 1.55);
        var left = project(0, depth);
        var right = project(longLines - 1, depth);
        var alpha = Math.min(0.68, (0.06 + (1 - depth) * 0.34) * palette.gridStrength);

        ctx.strokeStyle = rgba(j % 3 === 0 ? palette.secondary : palette.accent, alpha);
        ctx.lineWidth = j === latLines - 1 ? 1.5 : 0.8;
        ctx.beginPath();
        ctx.moveTo(left.x, left.y);
        ctx.lineTo(right.x, right.y);
        ctx.stroke();
      }
    }

    function spawnPulse() {
      pulses.push({
        u: Math.floor(Math.random() * longLines),
        d: 0,
        speed: 0.00058 + Math.random() * 0.00055,
        scanned: {},
      });
    }

    function drawPulses(dtMs) {
      for (var i = pulses.length - 1; i >= 0; i--) {
        var pulse = pulses[i];
        pulse.d += pulse.speed * dtMs;
        if (pulse.d >= 1) {
          pulses.splice(i, 1);
          continue;
        }

        var head = project(pulse.u, pulse.d);
        var tail = project(pulse.u, Math.max(0, pulse.d - 0.12));
        var radius = 12 + pulse.d * 28;
        var glow = ctx.createRadialGradient(head.x, head.y, 0, head.x, head.y, radius);

        glow.addColorStop(0, rgba(palette.secondary, 0.56));
        glow.addColorStop(0.42, rgba(palette.accent, 0.24));
        glow.addColorStop(1, rgba(palette.accent, 0));
        ctx.fillStyle = glow;
        ctx.beginPath();
        ctx.arc(head.x, head.y, radius, 0, Math.PI * 2);
        ctx.fill();

        ctx.strokeStyle = rgba(palette.secondary, 0.92);
        ctx.lineWidth = 1.5 + pulse.d * 1.9;
        ctx.beginPath();
        ctx.moveTo(tail.x, tail.y);
        ctx.lineTo(head.x, head.y);
        ctx.stroke();

        for (var n = 0; n < nodes.length; n++) {
          if (pulse.scanned[n]) continue;
          if (Math.abs(nodes[n].u - pulse.u) < 0.5 && Math.abs(nodes[n].depth - pulse.d) < 0.04) {
            nodes[n].flash = 1;
            pulse.scanned[n] = true;
          }
        }
      }
    }

    function drawNodes(now) {
      for (var n = 0; n < nodes.length; n++) {
        var node = nodes[n];
        var pos = project(node.u, node.depth);
        var color = node.alert ? palette.alert : palette.accent;
        var breathe = 0.45 + 0.35 * (Math.sin(now * 0.001 + node.phase) * 0.5 + 0.5);
        var alpha = breathe * (0.45 + node.depth * 0.55);
        var size = 1.4 + node.depth * 2.6;

        if (node.flash > 0.01) {
          var flashRadius = size + 10 + node.flash * 18;
          var flash = ctx.createRadialGradient(pos.x, pos.y, 0, pos.x, pos.y, flashRadius);
          flash.addColorStop(0, "rgba(255,255,255," + 0.62 * node.flash + ")");
          flash.addColorStop(0.32, rgba(color, 0.58 * node.flash));
          flash.addColorStop(1, rgba(color, 0));
          ctx.fillStyle = flash;
          ctx.beginPath();
          ctx.arc(pos.x, pos.y, flashRadius, 0, Math.PI * 2);
          ctx.fill();
          node.flash *= 0.92;
        }

        ctx.fillStyle = rgba(color, alpha);
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, size, 0, Math.PI * 2);
        ctx.fill();

        if (node.depth > 0.55) {
          ctx.strokeStyle = rgba(color, alpha * 0.52);
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.arc(pos.x, pos.y, size + 3, 0, Math.PI * 2);
          ctx.stroke();
        }
      }
    }

    function frame(now) {
      var dtMs = lastFrame ? now - lastFrame : 16;
      lastFrame = now;
      vp.x = lerp(vp.x, vpTarget.x, 0.06);
      vp.y = lerp(vp.y, vpTarget.y, 0.06);
      ctx.clearRect(0, 0, width, height);
      drawGrid();
      if (now - lastPulseAt > 820 + Math.random() * 720) {
        spawnPulse();
        lastPulseAt = now;
      }
      drawPulses(dtMs);
      drawNodes(now);
      if (running) rafId = window.requestAnimationFrame(frame);
    }

    function renderStaticFrame() {
      ctx.clearRect(0, 0, width, height);
      drawGrid();
      for (var n = 0; n < nodes.length; n++) {
        var node = nodes[n];
        var pos = project(node.u, node.depth);
        var color = node.alert ? palette.alert : palette.accent;
        ctx.fillStyle = rgba(color, 0.56 * (0.45 + node.depth * 0.55));
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, 1.4 + node.depth * 2.6, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    function start() {
      if (running || reduced) return;
      running = true;
      lastFrame = 0;
      rafId = window.requestAnimationFrame(frame);
    }

    function stop() {
      running = false;
      if (rafId) window.cancelAnimationFrame(rafId);
    }

    function syncMotionPreference() {
      var shouldReduce = motionQuery.matches;
      if (shouldReduce === reduced) return;

      reduced = shouldReduce;
      if (reduced) {
        stop();
        renderStaticFrame();
      } else if (!observer || isVisible) {
        start();
      }
    }

    canvas.addEventListener("pointermove", function (event) {
      if (reduced) return;
      var rect = canvas.getBoundingClientRect();
      var nx = (event.clientX - rect.left) / rect.width;
      var ny = (event.clientY - rect.top) / rect.height;
      vpTarget.x = defaultVp.x + (nx - 0.5) * 64;
      vpTarget.y = defaultVp.y + (ny - 0.5) * 32;
    });

    canvas.addEventListener("pointerleave", function () {
      vpTarget.x = defaultVp.x;
      vpTarget.y = defaultVp.y;
    });

    window.addEventListener("roadwatch-theme-change", function () {
      palette = readPalette();
      if (reduced) renderStaticFrame();
    });

    if (motionQuery.addEventListener) {
      motionQuery.addEventListener("change", syncMotionPreference);
    } else if (motionQuery.addListener) {
      motionQuery.addListener(syncMotionPreference);
    }

    if ("ResizeObserver" in window) {
      new ResizeObserver(resize).observe(canvas);
    } else {
      window.addEventListener("resize", resize);
    }

    observer = "IntersectionObserver" in window
      ? new IntersectionObserver(function (entries) {
          entries.forEach(function (entry) {
            isVisible = entry.isIntersecting;
            if (isVisible) start();
            else stop();
          });
        }, { threshold: 0.05 })
      : null;

    resize();
    if (reduced) {
      renderStaticFrame();
    }
    if (observer) {
      observer.observe(canvas);
    } else if (!reduced) {
      start();
    }
  }

  function boot() {
    init(document.getElementById("hero-canvas"));
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }

  window.RoadWatchHero = { init: init };
})();
