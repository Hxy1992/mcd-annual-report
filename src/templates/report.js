/* 麦麦年报 · 交互脚本（内联进最终单文件 HTML） */
(function () {
  "use strict";

  // 1. 滚动显现
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (!e.isIntersecting) return;
      e.target.classList.add("in");
      // 数字滚动
      e.target.querySelectorAll("[data-target]").forEach(function (el) {
        if (el.dataset.done) return;
        el.dataset.done = "1";
        var target = parseFloat(el.dataset.target) || 0;
        var decimals = parseInt(el.dataset.decimals || "0", 10);
        var prefix = el.dataset.prefix || "";
        var suffix = el.dataset.suffix || "";
        var t0 = null;
        function step(ts) {
          if (!t0) t0 = ts;
          var p = Math.min((ts - t0) / 900, 1);
          var eased = 1 - Math.pow(1 - p, 3);
          el.textContent = prefix + (target * eased).toFixed(decimals) + suffix;
          if (p < 1) requestAnimationFrame(step);
        }
        requestAnimationFrame(step);
      });
      // 条形图生长
      e.target.querySelectorAll(".bar-row .fill").forEach(function (el) {
        el.style.width = (el.dataset.w || 0) + "%";
      });
      // 月度柱生长
      e.target.querySelectorAll(".months .b").forEach(function (el, i) {
        setTimeout(function () { el.style.height = (el.dataset.h || 0) + "%"; }, i * 60);
      });
      io.unobserve(e.target);
    });
  }, { threshold: 0.25 });
  document.querySelectorAll(".reveal").forEach(function (el) { io.observe(el); });

  // 2. 分享卡片（canvas 绘制并导出 PNG）
  var canvas = document.getElementById("share-canvas");
  var btn = document.getElementById("dl-btn");
  if (!canvas || !window.REPORT) return;
  var ctx = canvas.getContext("2d");
  var W = canvas.width, H = canvas.height;

  function drawCard() {
    var r = window.REPORT;
    var g = ctx.createLinearGradient(0, 0, W, H);
    g.addColorStop(0, "#da291c");
    g.addColorStop(0.55, "#a8121b");
    g.addColorStop(1, "#6d0d14");
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, W, H);
    // 顶部装饰圆
    ctx.globalAlpha = 0.14;
    ctx.fillStyle = "#ffc72c";
    ctx.beginPath(); ctx.arc(W * 0.86, H * 0.1, W * 0.34, 0, Math.PI * 2); ctx.fill();
    ctx.globalAlpha = 1;
    // 文案
    ctx.textAlign = "center";
    ctx.fillStyle = "rgba(255,255,255,0.72)";
    ctx.font = "600 24px sans-serif";
    ctx.fillText("我 的 麦 麦 年 报", W / 2, 96);
    ctx.fillStyle = "#ffc72c";
    ctx.font = "800 76px sans-serif";
    ctx.fillText(r.persona.code, W / 2, 210);
    ctx.fillStyle = "#ffffff";
    ctx.font = "800 52px sans-serif";
    ctx.fillText(r.persona.name, W / 2, 292);
    ctx.fillStyle = "rgba(255,255,255,0.85)";
    ctx.font = "400 24px sans-serif";
    wrapText(r.persona.tagline, W / 2, 350, W - 120, 36);
    // 数据亮点
    ctx.strokeStyle = "rgba(255,199,44,0.55)";
    ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(70, 460); ctx.lineTo(W - 70, 460); ctx.stroke();
    var lines = (r.persona.highlights || []).slice(0, 4);
    lines.forEach(function (t, i) {
      ctx.fillStyle = "rgba(255,255,255,0.92)";
      ctx.font = "500 26px sans-serif";
      ctx.fillText(t, W / 2, 530 + i * 52);
    });
    ctx.fillStyle = "rgba(255,255,255,0.55)";
    ctx.font = "400 20px sans-serif";
    ctx.fillText("麦麦年报 MCD Wrapped", W / 2, H - 130);
    ctx.fillText("非麦当劳官方产品 · 仅供娱乐参考", W / 2, H - 92);
  }
  function wrapText(text, x, y, maxW, lh) {
    var words = String(text || "").split("");
    var line = "", yy = y;
    for (var i = 0; i < words.length; i++) {
      var test = line + words[i];
      if (ctx.measureText(test).width > maxW && line) {
        ctx.fillText(line, x, yy); line = words[i]; yy += lh;
      } else { line = test; }
    }
    if (line) ctx.fillText(line, x, yy);
  }
  drawCard();
  if (btn) {
    btn.addEventListener("click", function () {
      var a = document.createElement("a");
      a.download = "麦麦年报-分享卡片.png";
      a.href = canvas.toDataURL("image/png");
      a.click();
    });
  }
})();
