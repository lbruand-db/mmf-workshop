# Databricks notebook source
# MAGIC %md
# MAGIC # Backtest explorer (widget)
# MAGIC
# MAGIC Defines `BACKTEST_EXPLORER_HTML`, a self-contained interactive widget (plain
# MAGIC HTML/SVG/JavaScript, no external libraries or network access) shown by
# MAGIC *3.1 Lecture — Backtesting and Forecast Stability* with `displayHTML`.
# MAGIC
# MAGIC It backtests two simple models on three synthetic daily series with MMF's
# MAGIC parameters (`prediction_length`, `backtest_length`, `stride`; window cutoffs at
# MAGIC `n - backtest_length + k * stride`, like `mmf_sa`), and measures how stable the
# MAGIC "best model" verdict is by replaying the same settings on 100 alternative
# MAGIC histories of each series. Models: Seasonal Naive vs. the average of the same
# MAGIC weekday over the last 4 weeks — close enough that one window can mislead.

# COMMAND ----------

BACKTEST_EXPLORER_HTML = r"""
<div id="bx">
<style>
  #bx { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; color: #1f2937; background: #f8fafc; padding: 16px; border-radius: 10px; max-width: 1040px; }
  #bx h3 { margin: 0 0 4px; font-size: 17px; }
  #bx .muted { color: #6b7280; font-size: 13px; line-height: 1.45; }
  #bx .controls { display: grid; grid-template-columns: repeat(3, 1fr) 150px; gap: 14px 22px; background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 14px 16px; }
  #bx label { font-size: 13px; font-weight: 600; display: block; }
  #bx label code { font-weight: 600; }
  #bx label output { float: right; font-weight: 700; color: #111827; font-variant-numeric: tabular-nums; }
  #bx input[type=range] { width: 100%; margin-top: 6px; accent-color: #2563eb; }
  #bx select { width: 100%; margin-top: 4px; padding: 3px; }
  #bx .presets { grid-column: 1 / -1; display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
  #bx button { background: #fff; border: 1px solid #cbd5e1; border-radius: 6px; padding: 5px 11px; font-size: 13px; cursor: pointer; }
  #bx button:hover { background: #eff6ff; border-color: #93c5fd; }
  #bx .windows { margin-left: auto; font-size: 14px; }
  #bx .windows b { font-size: 18px; color: #2563eb; }
  #bx .warn { color: #b45309; font-weight: 600; }
  #bx .card { background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 12px 16px 10px; margin-top: 14px; }
  #bx .card-head { display: flex; justify-content: space-between; gap: 16px; align-items: baseline; }
  #bx .legend { font-size: 12px; color: #4b5563; display: flex; gap: 14px; flex-wrap: wrap; margin: 6px 0 2px; }
  #bx .sw { display: inline-block; width: 18px; height: 3px; vertical-align: middle; margin-right: 4px; }
  #bx .grid2 { display: grid; grid-template-columns: 1fr 300px; gap: 16px; align-items: start; }
  #bx svg { width: 100%; height: auto; display: block; }
  #bx .stat { font-size: 13px; margin: 6px 0; line-height: 1.4; }
  #bx .meter { height: 10px; background: #e5e7eb; border-radius: 5px; overflow: hidden; margin: 4px 0 2px; }
  #bx .meter > div { height: 100%; }
  #bx .badge { display: inline-block; padding: 1px 8px; border-radius: 10px; font-size: 12px; font-weight: 700; color: #fff; }
  #bx table { border-collapse: collapse; width: 100%; font-size: 13px; margin-top: 8px; }
  #bx th, #bx td { border-bottom: 1px solid #e5e7eb; padding: 5px 8px; text-align: left; }
  #bx th { background: #f1f5f9; }
  @media (max-width: 760px) { #bx .controls { grid-template-columns: 1fr; } #bx .grid2 { grid-template-columns: 1fr; } }
</style>

<div class="controls">
  <label><code>prediction_length</code> (horizon, days) <output id="bx-h-out"></output>
    <input id="bx-h" type="range" min="7" max="56" step="7" value="28"></label>
  <label><code>backtest_length</code> (days) <output id="bx-bl-out"></output>
    <input id="bx-bl" type="range" min="7" max="364" step="1" value="56"></label>
  <label><code>stride</code> (days between cutoffs) <output id="bx-st-out"></output>
    <input id="bx-st" type="range" min="1" max="56" step="1" value="28"></label>
  <label>Metric
    <select id="bx-metric"><option value="smape">sMAPE (MMF default)</option><option value="mae">MAE</option></select></label>
  <div class="presets">
    <span class="muted">Presets:</span>
    <button data-p="28,28,28">One window (28 / 28)</button>
    <button data-p="28,56,28">Workshop (56 / 28)</button>
    <button data-p="28,90,7">MMF full (90 / 7)</button>
    <button data-p="28,182,14">Half a year (182 / 14)</button>
    <button id="bx-reroll">New random history</button>
    <span class="windows" id="bx-windows"></span>
  </div>
</div>

<div id="bx-cards"></div>

<div class="card">
  <h3>Summary</h3>
  <table><thead><tr><th>Series</th><th>Winner (average over windows)</th><th>Margin</th><th>Windows agreeing with it</th><th>Same winner in 100 alternative histories</th></tr></thead><tbody id="bx-summary"></tbody></table>
  <p class="muted" id="bx-note"></p>
</div>

<script>
(function () {
  "use strict";
  const N = 730, DRAWS = 100;
  const MODELS = [
    { name: "Seasonal Naive", color: "#2563eb", dash: "",    fit: (y, h) => Array.from({ length: h }, (_, i) => y[y.length - 7 + (i % 7)]) },
    // Mean of the same weekday over the last 4 weeks: also seasonal, but smoother than Seasonal Naive.
    { name: "Weekday average (4 wk)", color: "#ea580c", dash: "5 3", fit: (y, h) => Array.from({ length: h }, (_, i) => { let s = 0; for (let k = 1; k <= 4; k++) s += y[y.length - 7 * k + (i % 7)]; return s / 4; }) },
  ];
  const $ = id => document.getElementById(id);

  // ---- deterministic random numbers (mulberry32) --------------------------------
  function rng(seed) {
    let s = seed >>> 0;
    return () => { s = (s + 0x6D2B79F5) >>> 0; let t = s; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  }
  function gauss(r) { return Math.sqrt(-2 * Math.log(Math.max(r(), 1e-12))) * Math.cos(2 * Math.PI * r()); }
  function poisson(r, lambda) { let k = 0, p = 1; const L = Math.exp(-lambda); do { k++; p *= r(); } while (p > L); return k - 1; }

  // ---- three daily series with the same structure for every seed -----------------
  const WEEKLY = [0.85, 0.9, 0.95, 1.0, 1.1, 1.35, 1.25];
  const SERIES = [
    { name: "Steady seller", blurb: "Regular weekly pattern, moderate noise — the easy case.",
      gen: r => Array.from({ length: N }, (_, t) => Math.max(0, Math.round((14 + 0.004 * t) * WEEKLY[t % 7] + 2.2 * gauss(r)))) },
    { name: "Intermittent spare part", blurb: "Mostly zero days with occasional orders — common in M5 and in spare-parts demand.",
      gen: r => Array.from({ length: N }, () => (r() < 0.14 ? 1 + poisson(r, 1.5) : 0)) },
    { name: "Promotions and a level shift", blurb: "Weekly pattern, promotion spikes, and demand stepping up about four months before the end.",
      gen: r => { const promo = new Set(); for (let s = 20 + Math.floor(r() * 30); s < N; s += 35 + Math.floor(r() * 30)) for (let d = 0; d < 5; d++) promo.add(s + d);
        return Array.from({ length: N }, (_, t) => { const level = t >= N - 120 ? 16 : 9; const boost = promo.has(t) ? 2.3 : 1; return Math.max(0, Math.round(level * WEEKLY[t % 7] * boost + 1.8 * gauss(r))); }); } },
  ];

  // ---- metrics and backtest, as in mmf_sa ----------------------------------------
  function metric(kind, a, f) {
    let s = 0;
    for (let i = 0; i < a.length; i++) {
      if (kind === "mae") s += Math.abs(a[i] - f[i]);
      else { const d = Math.abs(a[i]) + Math.abs(f[i]); s += d > 0 ? 2 * Math.abs(a[i] - f[i]) / d : 0; }
    }
    return s / a.length;
  }
  function cutoffs(n, h, bl, st) {
    const out = [];
    for (let c = n - bl; c + h <= n; c += st) out.push(c);
    return out;
  }
  function backtest(y, h, bl, st, kind) {
    return cutoffs(y.length, h, bl, st).map(c => {
      const train = y.slice(0, c), actual = y.slice(c, c + h);
      const fc = MODELS.map(m => m.fit(train, h));
      return { c, actual, fc, err: fc.map(f => metric(kind, actual, f)) };
    });
  }
  const mean = a => a.reduce((x, y) => x + y, 0) / a.length;
  function verdict(wins) { const avg = MODELS.map((_, j) => mean(wins.map(w => w.err[j]))); return { avg, winner: avg[0] <= avg[1] ? 0 : 1 }; }

  // ---- state --------------------------------------------------------------------
  let baseSeed = 7;

  // ---- drawing helpers ----------------------------------------------------------
  const pth = pts => pts.map(([x, y], i) => (i ? "L" : "M") + x.toFixed(1) + "," + y.toFixed(1)).join("");
  const txt = (x, y, s, anchor, size, color) => `<text x="${x}" y="${y}" font-size="${size || 11}" fill="${color || "#6b7280"}" text-anchor="${anchor || "start"}">${s}</text>`;

  function seriesChart(y, wins, h) {
    const W = 680, H = 210, L = 38, R = 8, T = 10, B = 24;
    const first = Math.max(0, (wins.length ? wins[0].c : y.length) - 84);
    const xs = t => L + (t - first) / (y.length - 1 - first) * (W - L - R);
    const vis = y.slice(first);
    const hi = Math.max(1, ...vis, ...wins.flatMap(w => w.fc.flat())) * 1.08;
    const ys = v => T + (1 - v / hi) * (H - T - B);
    let s = "";
    wins.forEach((w, i) => { s += `<rect x="${xs(w.c)}" y="${T}" width="${xs(w.c + h) - xs(w.c)}" height="${H - T - B}" fill="#2563eb" opacity="${i % 2 ? 0.06 : 0.11}"/>`; });
    [0, hi / 2, hi].forEach(v => { s += `<line x1="${L}" x2="${W - R}" y1="${ys(v)}" y2="${ys(v)}" stroke="#eef2f7"/>` + txt(L - 5, ys(v) + 4, Math.round(v), "end"); });
    s += `<path d="${pth(vis.map((v, i) => [xs(first + i), ys(v)]))}" fill="none" stroke="#6b7280" stroke-width="1.2"/>`;
    wins.forEach(w => MODELS.forEach((m, j) => {
      s += `<path d="${pth(w.fc[j].map((v, i) => [xs(w.c + i), ys(v)]))}" fill="none" stroke="${m.color}" stroke-width="1.8" stroke-dasharray="${m.dash}" opacity="0.9"/>`;
    }));
    if (wins.length) s += `<line x1="${xs(wins[0].c)}" x2="${xs(wins[0].c)}" y1="${T}" y2="${H - B}" stroke="#2563eb" stroke-dasharray="2 3"/>` + txt(xs(wins[0].c) + 4, T + 11, "first cutoff", "start", 10, "#2563eb");
    s += txt(L, H - 6, `day ${first}`) + txt(W - R, H - 6, `day ${y.length - 1} (today)`, "end");
    return `<svg viewBox="0 0 ${W} ${H}">${s}</svg>`;
  }

  function windowChart(wins, kind) {
    const W = 300, H = 150, L = 34, R = 8, T = 12, B = 22;
    const all = wins.flatMap(w => w.err);
    const hi = Math.max(1e-9, ...all) * 1.12;
    const n = wins.length;
    const xs = i => n === 1 ? (L + W - R) / 2 : L + i / (n - 1) * (W - L - R);
    const ys = v => T + (1 - v / hi) * (H - T - B);
    let s = "";
    [0, hi / 2, hi].forEach(v => { s += `<line x1="${L}" x2="${W - R}" y1="${ys(v)}" y2="${ys(v)}" stroke="#eef2f7"/>` + txt(L - 4, ys(v) + 4, v < 10 ? v.toFixed(2) : Math.round(v), "end", 10); });
    MODELS.forEach((m, j) => {
      const avg = mean(wins.map(w => w.err[j]));
      s += `<line x1="${L}" x2="${W - R}" y1="${ys(avg)}" y2="${ys(avg)}" stroke="${m.color}" stroke-dasharray="3 3" opacity="0.6"/>`;
      if (n > 1) s += `<path d="${pth(wins.map((w, i) => [xs(i), ys(w.err[j])]))}" fill="none" stroke="${m.color}" stroke-width="1.3" opacity="0.7"/>`;
      wins.forEach((w, i) => { s += `<circle cx="${xs(i)}" cy="${ys(w.err[j])}" r="${n > 30 ? 2 : 3.2}" fill="${m.color}"/>`; });
    });
    s += txt(L, H - 6, "window 1") + txt(W - R, H - 6, `window ${n}`, "end") + txt(W - R, T - 2, `${kind === "mae" ? "MAE" : "sMAPE"} per window (lower is better)`, "end", 10);
    return `<svg viewBox="0 0 ${W} ${H}">${s}</svg>`;
  }

  function stability(si, h, bl, st, kind) {
    const counts = [0, 0];
    for (let d = 0; d < DRAWS; d++) counts[verdict(backtest(SERIES[si].gen(rng(10007 * (d + 1) + 31 * si)), h, bl, st, kind)).winner]++;
    const top = counts[0] >= counts[1] ? 0 : 1;
    return { top, share: counts[top] / DRAWS };
  }
  function badge(share, n) {
    if (n === 1 && share < 0.9) return ["Fragile", "#dc2626"];
    if (share >= 0.9) return ["Stable", "#16a34a"];
    if (share >= 0.7) return ["Moderate", "#d97706"];
    return ["Fragile", "#dc2626"];
  }

  // ---- render -------------------------------------------------------------------
  function render() {
    const h = +$("bx-h").value;
    $("bx-bl").min = h;
    if (+$("bx-bl").value < h) $("bx-bl").value = h;
    const bl = +$("bx-bl").value, st = +$("bx-st").value, kind = $("bx-metric").value;
    $("bx-h-out").value = h; $("bx-bl-out").value = bl; $("bx-st-out").value = st;
    const nWin = cutoffs(N, h, bl, st).length;
    $("bx-windows").innerHTML = `<b>${nWin}</b> backtest window${nWin > 1 ? "s" : ""}` +
      (nWin === 1 ? ` <span class="warn">— the verdict rests on ${h} days</span>` : "") +
      (st < h && nWin > 1 ? ` <span class="muted">(windows overlap: stride &lt; horizon)</span>` : "");

    let cards = "", rows = "";
    SERIES.forEach((sr, si) => {
      const y = sr.gen(rng(baseSeed * 7919 + si));
      const wins = backtest(y, h, bl, st, kind);
      const v = verdict(wins);
      const agree = wins.filter(w => (w.err[0] <= w.err[1] ? 0 : 1) === v.winner).length;
      const stab = stability(si, h, bl, st, kind);
      const [bText, bColor] = badge(stab.share, nWin);
      const margin = Math.abs(v.avg[0] - v.avg[1]);
      const fmt = x => kind === "mae" ? x.toFixed(2) : x.toFixed(3);
      const wm = MODELS[v.winner];
      cards += `<div class="card"><div class="card-head"><div><h3>${si + 1}. ${sr.name}</h3><div class="muted">${sr.blurb}</div></div>
        <span class="badge" style="background:${bColor}">${bText}</span></div>
        <div class="legend"><span><span class="sw" style="background:#6b7280"></span>actual</span>` +
        MODELS.map(m => `<span><span class="sw" style="background:${m.color}"></span>${m.name} forecast</span>`).join("") +
        `<span><span class="sw" style="background:#2563eb;opacity:.25;height:10px"></span>backtest windows</span></div>
        <div class="grid2"><div>${seriesChart(y, wins, h)}</div><div>${windowChart(wins, kind)}
        <div class="stat">Average: ` + MODELS.map((m, j) => `<b style="color:${m.color}">${fmt(v.avg[j])}</b>`).join(" vs ") +
        ` &rarr; <b style="color:${wm.color}">${wm.name}</b> wins</div>
        <div class="stat">${agree} of ${wins.length} window${wins.length > 1 ? "s" : ""} agree with that verdict.</div>
        <div class="stat">Same winner in <b>${Math.round(stab.share * 100)}%</b> of ${DRAWS} alternative histories:</div>
        <div class="meter"><div style="width:${stab.share * 100}%;background:${bColor}"></div></div></div></div></div>`;
      rows += `<tr><td>${sr.name}</td><td style="color:${wm.color};font-weight:600">${wm.name}</td><td>${fmt(margin)}</td><td>${agree} / ${wins.length}</td>
        <td><span class="badge" style="background:${bColor}">${Math.round(stab.share * 100)}%</span></td></tr>`;
    });
    $("bx-cards").innerHTML = cards;
    $("bx-summary").innerHTML = rows;
    $("bx-note").innerHTML = `“Alternative histories” replay the same series structure with different random noise ${DRAWS} times, and re-run the backtest with your settings. ` +
      `A stable setting picks the same winner almost every time; a fragile one flips with the noise. Windows that overlap (stride &lt; horizon) share days, so they add less information than their count suggests.`;
  }

  ["bx-h", "bx-bl", "bx-st", "bx-metric"].forEach(id => $(id).addEventListener("input", render));
  document.querySelectorAll("#bx [data-p]").forEach(b => b.addEventListener("click", () => {
    const [h, bl, st] = b.dataset.p.split(",").map(Number);
    $("bx-h").value = h; $("bx-bl").min = h; $("bx-bl").value = bl; $("bx-st").value = st; render();
  }));
  $("bx-reroll").addEventListener("click", () => { baseSeed += 1; render(); });
  render();
})();
</script>
</div>
"""
