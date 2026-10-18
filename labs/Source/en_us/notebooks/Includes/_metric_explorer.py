# Databricks notebook source
# MAGIC %md
# MAGIC # Metric explorer (widget)
# MAGIC
# MAGIC Defines `METRIC_EXPLORER_HTML`, a self-contained interactive widget (plain
# MAGIC HTML/SVG/JavaScript, no external libraries or network access) shown by
# MAGIC *4.2 Appendix — Choosing a Forecast Metric* with `displayHTML`.
# MAGIC
# MAGIC It scores four simple forecasts of one synthetic daily series with the five
# MAGIC metrics `mmf_sa` accepts (`smape`, `mape`, `mae`, `mse`, `rmse`), using the same
# MAGIC sktime formulas as `mmf_sa` at the pinned commit (`Forecaster.calculate_metrics`):
# MAGIC percentage errors divide by `max(denominator, eps)` with `eps` = float64 machine
# MAGIC epsilon, so MAPE on a zero-sales day is about 10^15 and sMAPE is 0 when actual and
# MAGIC forecast are both 0. Each metric is averaged over 3 backtest windows
# MAGIC (`prediction_length=28`, `backtest_length=84`, `stride=28`), as 4.1 does. The
# MAGIC series' share of zero days, size, variability and promotion spikes are set by the
# MAGIC learner; a second panel draws each metric's penalty for a single day.

# COMMAND ----------

METRIC_EXPLORER_HTML = r"""
<div id="mx">
<style>
  #mx { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; color: #1f2937; background: #f8fafc; padding: 16px; border-radius: 10px; max-width: 1040px; }
  #mx h3 { margin: 0 0 4px; font-size: 17px; }
  #mx .muted { color: #6b7280; font-size: 13px; line-height: 1.45; }
  #mx .controls { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px 22px; background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 14px 16px; }
  #mx label { font-size: 13px; font-weight: 600; display: block; }
  #mx label output { float: right; font-weight: 700; color: #111827; font-variant-numeric: tabular-nums; }
  #mx input[type=range] { width: 100%; margin-top: 6px; accent-color: #2563eb; }
  #mx .presets { grid-column: 1 / -1; display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
  #mx button { background: #fff; border: 1px solid #cbd5e1; border-radius: 6px; padding: 5px 11px; font-size: 13px; cursor: pointer; }
  #mx button:hover { background: #eff6ff; border-color: #93c5fd; }
  #mx .profile { margin-left: auto; font-size: 13px; color: #374151; }
  #mx .card { background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 12px 16px 10px; margin-top: 14px; }
  #mx .legend { font-size: 12px; color: #4b5563; display: flex; gap: 14px; flex-wrap: wrap; margin: 6px 0 2px; }
  #mx .sw { display: inline-block; width: 18px; height: 3px; vertical-align: middle; margin-right: 4px; }
  #mx svg { width: 100%; height: auto; display: block; }
  #mx table { border-collapse: collapse; width: 100%; font-size: 13px; margin-top: 8px; font-variant-numeric: tabular-nums; }
  #mx th, #mx td { border-bottom: 1px solid #e5e7eb; padding: 6px 8px; text-align: right; }
  #mx th:first-child, #mx td:first-child { text-align: left; }
  #mx th { background: #f1f5f9; }
  #mx td.win { background: #dcfce7; font-weight: 700; }
  #mx td.bad { color: #b91c1c; font-weight: 600; }
  #mx tr.bias td { border-top: 2px solid #cbd5e1; }
  #mx .badge { display: inline-block; padding: 1px 8px; border-radius: 10px; font-size: 12px; font-weight: 700; color: #fff; }
  #mx ul.advice { margin: 6px 0 0; padding-left: 20px; font-size: 13px; line-height: 1.5; }
  #mx ul.advice li { margin-bottom: 6px; }
  #mx .grid4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-top: 8px; }
  #mx .mini { border: 1px solid #eef2f7; border-radius: 8px; padding: 6px 8px; }
  #mx .mini b { font-size: 13px; }
  #mx .mini .muted { font-size: 12px; }
  #mx .row { display: flex; gap: 22px; align-items: end; flex-wrap: wrap; }
  #mx .row label { min-width: 260px; }
  @media (max-width: 760px) { #mx .controls, #mx .grid4 { grid-template-columns: 1fr 1fr; } }
</style>

<div class="controls">
  <label>Days with zero sales <output id="mx-z-out"></output>
    <input id="mx-z" type="range" min="0" max="95" step="5" value="65"></label>
  <label>Units on a selling day <output id="mx-l-out"></output>
    <input id="mx-l" type="range" min="0" max="100" step="1" value="15"></label>
  <label>Day-to-day variability <output id="mx-cv-out"></output>
    <input id="mx-cv" type="range" min="0.1" max="1.2" step="0.05" value="0.5"></label>
  <label>Promotion spike days <output id="mx-s-out"></output>
    <input id="mx-s" type="range" min="0" max="10" step="1" value="0"></label>
  <div class="presets">
    <span class="muted">Presets:</span>
    <button data-p="0,40,0.3,0">Fast mover</button>
    <button data-p="5,4,0.6,0">Slow mover (a few zero days)</button>
    <button data-p="65,2,0.5,0">Typical M5 item</button>
    <button data-p="90,1.5,0.5,0">Spare part</button>
    <button data-p="0,20,0.2,10">Promotions</button>
    <button id="mx-reroll">New random history</button>
    <span class="profile" id="mx-profile"></span>
  </div>
</div>

<div class="card">
  <h3>1. The series and four candidate forecasts</h3>
  <div class="muted">Last 16 weeks of a daily series. Each shaded block is a 28-day backtest window; each candidate forecasts it from the history before it.</div>
  <div class="legend" id="mx-legend"></div>
  <div id="mx-series"></div>
</div>

<div class="card">
  <h3>2. Who wins under each metric?</h3>
  <div class="muted">Average over the 3 windows, as in 4.1 (lower is better). Green: the forecast this metric would select. The last column replays the same settings on 100 alternative histories: a low share means this verdict is a fluke of this particular history.</div>
  <table><thead id="mx-head"></thead><tbody id="mx-body"></tbody></table>
  <ul class="advice" id="mx-advice"></ul>
</div>

<div class="card">
  <h3>3. What one day costs under each metric</h3>
  <div class="muted">Penalty for a single day as the forecast moves from 0 upwards, for the actual value you choose. The dot is the forecast where the penalty is lowest; look at what happens at an actual of 0.</div>
  <div class="row">
    <label>Actual sales that day <output id="mx-a-out"></output>
      <input id="mx-a" type="range" min="0" max="20" step="1" value="10"></label>
    <span class="muted" id="mx-asym"></span>
  </div>
  <div class="grid4" id="mx-pen"></div>
</div>

<script>
(function () {
  "use strict";
  const N = 364, H = 28, BL = 84, ST = 28, DRAWS = 100, EPS = 2.220446049250313e-16;
  const $ = id => document.getElementById(id);

  // ---- deterministic random numbers (mulberry32) --------------------------------
  function rng(seed) {
    let s = seed >>> 0;
    return () => { s = (s + 0x6D2B79F5) >>> 0; let t = s; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  }
  function gauss(r) { return Math.sqrt(-2 * Math.log(Math.max(r(), 1e-12))) * Math.cos(2 * Math.PI * r()); }

  // ---- the series: zero days, size on selling days, noise, promotion spikes -------
  const WEEKLY = [0.85, 0.9, 0.95, 1.0, 1.1, 1.35, 1.25];
  function gen(p, r) {
    const sig = Math.sqrt(Math.log(1 + p.cv * p.cv));
    return Array.from({ length: N }, (_, t) => {
      if (r() < p.zeros) return 0;
      let v = p.level * WEEKLY[t % 7] * Math.exp(sig * gauss(r) - sig * sig / 2);
      if (r() < p.spikes) v *= 4;
      return Math.max(1, Math.round(v));
    });
  }

  // ---- the five metrics mmf_sa accepts, with sktime's formulas -------------------
  const pe = {
    smape: (y, f) => Math.abs(y - f) / (Math.max(Math.abs(y) + Math.abs(f), EPS) / 2),
    mape: (y, f) => Math.abs(y - f) / Math.max(Math.abs(y), EPS),
    mae: (y, f) => Math.abs(y - f),
    mse: (y, f) => (y - f) * (y - f),
  };
  const avgOf = (fn, a, f) => a.reduce((s, y, i) => s + fn(y, f[i]), 0) / a.length;
  const METRICS = [
    { key: "smape", label: "sMAPE (MMF default)", fn: (a, f) => avgOf(pe.smape, a, f) },
    { key: "mape", label: "MAPE", fn: (a, f) => avgOf(pe.mape, a, f) },
    { key: "mae", label: "MAE", fn: (a, f) => avgOf(pe.mae, a, f) },
    { key: "mse", label: "MSE", fn: (a, f) => avgOf(pe.mse, a, f) },
    { key: "rmse", label: "RMSE", fn: (a, f) => Math.sqrt(avgOf(pe.mse, a, f)) },
  ];

  // ---- four candidate forecasts ---------------------------------------------------
  const median = a => { const b = [...a].sort((x, y) => x - y), m = b.length >> 1; return b.length % 2 ? b[m] : (b[m - 1] + b[m]) / 2; };
  const MODELS = [
    { name: "Zero", color: "#6b7280", dash: "6 3", fit: (y, h) => Array(h).fill(0) },
    { name: "Median (28 d)", color: "#16a34a", dash: "", fit: (y, h) => Array(h).fill(median(y.slice(-28))) },
    { name: "Mean (28 d)", color: "#ea580c", dash: "", fit: (y, h) => { const s = y.slice(-28); return Array(h).fill(s.reduce((a, b) => a + b, 0) / s.length); } },
    { name: "Seasonal Naive", color: "#2563eb", dash: "", fit: (y, h) => Array.from({ length: h }, (_, i) => y[y.length - 7 + (i % 7)]) },
  ];

  function cutoffs() { const o = []; for (let c = N - BL; c + H <= N; c += ST) o.push(c); return o; }
  function evaluate(y) {
    const wins = cutoffs().map(c => { const a = y.slice(c, c + H); return { c, a, fc: MODELS.map(m => m.fit(y.slice(0, c), H)) }; });
    const score = METRICS.map(m => MODELS.map((_, j) => wins.reduce((s, w) => s + m.fn(w.a, w.fc[j]), 0) / wins.length));
    const total = wins.reduce((s, w) => s + w.a.reduce((x, v) => x + v, 0), 0);
    const bias = MODELS.map((_, j) => total > 0 ? wins.reduce((s, w) => s + w.fc[j].reduce((x, v) => x + v, 0), 0) / total - 1 : 0);
    return { wins, score, bias };
  }
  // Lowest score wins; ties go to the earlier (simpler) forecast.
  const argmin = s => s.reduce((b, v, j) => (v < s[b] - 1e-12 ? j : b), 0);

  // ---- formatting -----------------------------------------------------------------
  const SUP = "⁰¹²³⁴⁵⁶⁷⁸⁹";
  function fmt(v) {
    if (v >= 1e6) { const e = Math.floor(Math.log10(v)); return "≈ 10" + String(e).split("").map(d => SUP[+d]).join(""); }
    if (v >= 100) return v.toFixed(0);
    if (v >= 10) return v.toFixed(1);
    return v.toFixed(2);
  }
  const pct = x => (x > 0 ? "+" : "") + Math.round(x * 100) + "%";

  // ---- drawing helpers --------------------------------------------------------------
  const pth = pts => pts.map(([x, y], i) => (i ? "L" : "M") + x.toFixed(1) + "," + y.toFixed(1)).join("");
  const txt = (x, y, s, anchor, size, color) => `<text x="${x}" y="${y}" font-size="${size || 11}" fill="${color || "#6b7280"}" text-anchor="${anchor || "start"}">${s}</text>`;

  function seriesChart(y, ev) {
    const W = 1000, Hh = 220, L = 40, R = 10, T = 10, B = 24, first = N - 112;
    const xs = t => L + (t - first) / (N - 1 - first) * (W - L - R);
    const hi = Math.max(1, ...y.slice(first), ...ev.wins.flatMap(w => w.fc.flat())) * 1.08;
    const ys = v => T + (1 - v / hi) * (Hh - T - B);
    let s = "";
    ev.wins.forEach((w, i) => { s += `<rect x="${xs(w.c)}" y="${T}" width="${xs(w.c + H - 1) - xs(w.c)}" height="${Hh - T - B}" fill="#2563eb" opacity="${i % 2 ? 0.05 : 0.1}"/>`; });
    [0, hi / 2, hi].forEach(v => { s += `<line x1="${L}" x2="${W - R}" y1="${ys(v)}" y2="${ys(v)}" stroke="#eef2f7"/>` + txt(L - 5, ys(v) + 4, Math.round(v), "end"); });
    s += `<path d="${pth(y.slice(first).map((v, i) => [xs(first + i), ys(v)]))}" fill="none" stroke="#9ca3af" stroke-width="1.2"/>`;
    ev.wins.forEach(w => MODELS.forEach((m, j) => {
      s += `<path d="${pth(w.fc[j].map((v, i) => [xs(w.c + i), ys(v)]))}" fill="none" stroke="${m.color}" stroke-width="${j ? 1.8 : 2.6}" stroke-dasharray="${m.dash}" opacity="0.9"/>`;
    }));
    s += txt(L, Hh - 6, `day ${first}`) + txt(W - R, Hh - 6, `day ${N - 1} (today)`, "end");
    return `<svg viewBox="0 0 ${W} ${Hh}">${s}</svg>`;
  }

  // Penalty of one day as a function of the forecast, for a fixed actual.
  const PEN = [
    { label: "sMAPE", fn: pe.smape, note: "Bounded by 2. Misses below the actual cost more than misses above. At actual 0: 0 for an exact zero, 2 for anything else." },
    { label: "MAPE", fn: pe.mape, note: "Over-forecasts are unbounded, under-forecasts cost at most 1, so it prefers forecasts that are too low. At actual 0: about 10¹⁵ for anything but 0." },
    { label: "MAE", fn: pe.mae, note: "Grows linearly in both directions. Over a series, the best flat forecast is the median." },
    { label: "MSE / RMSE", fn: pe.mse, note: "Grows with the square of the miss, so big misses and spikes dominate. Over a series, the best flat forecast is the mean." },
  ];
  function penaltyChart(p, a) {
    const W = 240, Hh = 140, L = 30, R = 6, T = 10, B = 20, fmax = Math.max(10, 3 * a), K = 120;
    const xsF = Array.from({ length: K + 1 }, (_, i) => i / K * fmax);
    const cap = p.label === "MAPE" ? 3 : p.label === "sMAPE" ? 2 : Math.max(...xsF.map(f => p.fn(a, f)));
    const vals = xsF.map(f => Math.min(p.fn(a, f), cap));
    const hi = Math.max(1e-9, ...vals) * 1.1;
    const xs = f => L + f / fmax * (W - L - R), ys = v => T + (1 - v / hi) * (Hh - T - B);
    let s = "";
    [0, hi / 2, hi].forEach(v => { s += `<line x1="${L}" x2="${W - R}" y1="${ys(v)}" y2="${ys(v)}" stroke="#eef2f7"/>` + txt(L - 3, ys(v) + 4, v < 10 ? v.toFixed(1) : Math.round(v), "end", 10); });
    s += `<line x1="${xs(a)}" x2="${xs(a)}" y1="${T}" y2="${Hh - B}" stroke="#9ca3af" stroke-dasharray="2 3"/>` + txt(xs(a) + 3, T + 9, "actual", "start", 9);
    if (a === 0 && p.label !== "MAE" && p.label !== "MSE / RMSE") {
      // Jump from 0 to the cap: draw the point at 0 and the flat line just after it.
      s += `<path d="${pth(xsF.slice(1).map((f, i) => [xs(f), ys(vals[i + 1])]))}" fill="none" stroke="#2563eb" stroke-width="2"/>`;
      s += `<circle cx="${xs(0)}" cy="${ys(0)}" r="4" fill="#16a34a"/>`;
      if (p.label === "MAPE") s += txt(W - R, ys(vals[K]) + 13, "≈ 10¹⁵ (off the chart)", "end", 10, "#b91c1c");
    } else {
      s += `<path d="${pth(xsF.map((f, i) => [xs(f), ys(vals[i])]))}" fill="none" stroke="#2563eb" stroke-width="2"/>`;
      s += `<circle cx="${xs(a)}" cy="${ys(Math.min(p.fn(a, a), cap))}" r="4" fill="#16a34a"/>`;
    }
    s += txt(L, Hh - 5, "forecast 0", "start", 10) + txt(W - R, Hh - 5, fmax, "end", 10);
    return `<svg viewBox="0 0 ${W} ${Hh}">${s}</svg>`;
  }

  // ---- state ----------------------------------------------------------------------------
  let baseSeed = 11;
  // Log-scaled slider: 0..100 maps to 1..100 units.
  const levelOf = v => Math.round(Math.pow(100, v / 100) * 10) / 10;
  const sliderOf = l => Math.round(Math.log(l) / Math.log(100) * 100);
  const params = () => ({ zeros: +$("mx-z").value / 100, level: levelOf(+$("mx-l").value), cv: +$("mx-cv").value, spikes: +$("mx-s").value / 100 });

  // Share of alternative histories (same settings, different noise) where each metric picks the same winner.
  function stability(p, winners) {
    const same = winners.map(() => 0);
    for (let d = 0; d < DRAWS; d++) evaluate(gen(p, rng(10007 * (d + 1) + 17))).score.forEach((s, i) => { if (argmin(s) === winners[i]) same[i]++; });
    return same.map(c => c / DRAWS);
  }

  function advice(p, y, ev, winners, shares) {
    const hist = y.slice(0, N - BL), zs = hist.filter(v => v === 0).length / hist.length;
    const name = j => `<b style="color:${MODELS[j].color}">${MODELS[j].name}</b>`;
    const out = [];
    const zeroWins = METRICS.filter((m, i) => winners[i] === 0).map(m => m.label.split(" ")[0]);
    if (zeroWins.length) out.push(`<b>${zeroWins.join(", ")} ${zeroWins.length > 1 ? "select" : "selects"} a forecast of zero</b> — it would stock nothing (bias ${pct(ev.bias[0])}). A metric that rewards this is the wrong yardstick for this series.`);
    if (zs > 0) out.push(`<b>MAPE is unusable here:</b> ${Math.round(zs * 100)}% of days have zero sales, and MAPE divides by the actual, so a single zero day pushes any non-zero forecast to about 10¹⁵. Only an exact zero escapes.`);
    if (zs >= 0.3) out.push(`<b>sMAPE punishes every miss on a zero day with its maximum (2)</b>, however small the forecast, and scores an exact zero as perfect — so it drifts towards forecasts that copy zeros. <b>MAE</b> rewards the median, which is 0 once more than half the days are zero. <b>RMSE</b> rewards the mean and gets the total right: prefer it here, or a scaled metric outside MMF (MASE, RMSSE — the M5 competition used a weighted RMSSE).`);
    if (zs < 0.05 && p.level >= 10 && p.spikes === 0) out.push(`<b>sMAPE works well here:</b> no zero days and a decent volume. Being a percentage, it can be averaged across series of different sizes — MAE and RMSE can't: in 4.1's leaderboard averages, big series would dominate.`);
    if (p.spikes > 0) out.push(`<b>Promotion spikes:</b> MAE and sMAPE barely notice a few large misses, so they favour median-like forecasts that ignore promotions; squared errors (MSE, RMSE) are dominated by those misses. Here MAE selects ${name(winners[2])} (bias ${pct(ev.bias[winners[2]])}) and RMSE ${name(winners[4])} (bias ${pct(ev.bias[winners[4]])}). Decide whether promotion days must be stocked — or forecast promotions explicitly with exogenous variables.`);
    if (new Set(winners).size === 1) out.push(`All five metrics agree on ${name(winners[0])}` + (Math.min(...shares) < 0.7
      ? ` — but the candidates are close: in many alternative histories another one wins (last column). The metric matters less here than the number of backtest windows (see 3.1).`
      : `: for this series the metric choice doesn't change the decision.`));
    out.push(`Always read the <b>bias</b> row with the winner: a low error with a large negative bias means empty shelves.`);
    return out.map(s => `<li>${s}</li>`).join("");
  }

  function render() {
    const p = params();
    $("mx-z-out").value = Math.round(p.zeros * 100) + "%"; $("mx-l-out").value = p.level;
    $("mx-cv-out").value = p.cv.toFixed(2); $("mx-s-out").value = Math.round(p.spikes * 100) + "%";
    const y = gen(p, rng(baseSeed * 7919 + 3)), ev = evaluate(y);
    const hist = y.slice(0, N - BL);
    $("mx-profile").innerHTML = `This history: <b>${Math.round(hist.filter(v => v === 0).length / hist.length * 100)}%</b> zero days, mean <b>${fmt(hist.reduce((a, b) => a + b, 0) / hist.length)}</b> units/day`;
    $("mx-legend").innerHTML = `<span><span class="sw" style="background:#9ca3af"></span>actual</span>` +
      MODELS.map(m => `<span><span class="sw" style="background:${m.color}"></span>${m.name}</span>`).join("") +
      `<span><span class="sw" style="background:#2563eb;opacity:.25;height:10px"></span>backtest windows</span>`;
    $("mx-series").innerHTML = seriesChart(y, ev);

    $("mx-head").innerHTML = `<tr><th>Metric</th>` + MODELS.map(m => `<th style="color:${m.color}">${m.name}</th>`).join("") + `<th>Same winner in 100 histories</th></tr>`;
    const winners = ev.score.map(argmin);
    const shares = stability(p, winners);
    let rows = "";
    METRICS.forEach((m, i) => {
      const share = shares[i];
      const col = share >= 0.9 ? "#16a34a" : share >= 0.7 ? "#d97706" : "#dc2626";
      rows += `<tr><td>${m.label}</td>` + ev.score[i].map((v, j) => `<td class="${j === winners[i] ? "win" : ""}${v >= 1e6 ? " bad" : ""}">${fmt(v)}</td>`).join("") +
        `<td><span class="badge" style="background:${col}">${Math.round(share * 100)}%</span></td></tr>`;
    });
    rows += `<tr class="bias"><td>Bias: total forecast vs actual</td>` + ev.bias.map(b => `<td class="${Math.abs(b) > 0.2 ? "bad" : ""}">${pct(b)}</td>`).join("") + `<td></td></tr>`;
    $("mx-body").innerHTML = rows;
    $("mx-advice").innerHTML = advice(p, y, ev, winners, shares);
    renderPenalty();
  }

  function renderPenalty() {
    const a = +$("mx-a").value;
    $("mx-a-out").value = a;
    $("mx-pen").innerHTML = PEN.map(p => `<div class="mini"><b>${p.label}</b>${penaltyChart(p, a)}<div class="muted">${p.note}</div></div>`).join("");
    $("mx-asym").innerHTML = a > 0
      ? `Forecast ${a / 2} instead of ${a} (half): sMAPE ${pe.smape(a, a / 2).toFixed(2)}, MAPE ${pe.mape(a, a / 2).toFixed(2)}. Forecast ${a * 1.5} (half too much): sMAPE ${pe.smape(a, a * 1.5).toFixed(2)}, MAPE ${pe.mape(a, a * 1.5).toFixed(2)}.`
      : `A zero-sales day: sMAPE gives 0 to an exact zero and 2 to any other forecast; MAPE gives about 10¹⁵.`;
  }

  ["mx-z", "mx-l", "mx-cv", "mx-s"].forEach(id => $(id).addEventListener("input", render));
  $("mx-a").addEventListener("input", renderPenalty);
  document.querySelectorAll("#mx [data-p]").forEach(b => b.addEventListener("click", () => {
    const [z, l, cv, s] = b.dataset.p.split(",").map(Number);
    $("mx-z").value = z; $("mx-l").value = sliderOf(l); $("mx-cv").value = cv; $("mx-s").value = s; render();
  }));
  $("mx-reroll").addEventListener("click", () => { baseSeed += 1; render(); });
  render();
})();
</script>
</div>
"""
