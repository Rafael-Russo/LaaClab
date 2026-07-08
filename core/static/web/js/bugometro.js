/* Bugômetro screen: gauge + 24h chart + activity + ranking.
   Gauge and chart are drawn as plain inline SVG — no charting library. */

const SVGNS = "http://www.w3.org/2000/svg";

function svg(tag, attrs = {}) {
  const node = document.createElementNS(SVGNS, tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  return node;
}

/* Linear interpolate between hex colors through green → yellow → red. */
function gaugeColor(t) {
  const stops = [
    [0.0, [34, 197, 94]],
    [0.5, [234, 179, 8]],
    [1.0, [239, 68, 68]],
  ];
  let a = stops[0], b = stops[stops.length - 1];
  for (let i = 0; i < stops.length - 1; i++) {
    if (t >= stops[i][0] && t <= stops[i + 1][0]) { a = stops[i]; b = stops[i + 1]; break; }
  }
  const f = (t - a[0]) / (b[0] - a[0] || 1);
  const c = a[1].map((v, i) => Math.round(v + (b[1][i] - v) * f));
  return `rgb(${c[0]},${c[1]},${c[2]})`;
}

function renderGauge(score, status) {
  const W = 240, H = 152, cx = W / 2, cy = 140, rOuter = 112, rInner = 86;
  const s = svg("svg", { viewBox: `0 0 ${W} ${H}`, width: "240", height: "152" });
  const ticks = 44;
  for (let i = 0; i < ticks; i++) {
    const t = i / (ticks - 1);
    const ang = Math.PI - t * Math.PI;           // 180° → 0°
    const x1 = cx + Math.cos(ang) * rInner;
    const y1 = cy - Math.sin(ang) * rInner;
    const x2 = cx + Math.cos(ang) * rOuter;
    const y2 = cy - Math.sin(ang) * rOuter;
    const on = t * 100 <= score + 1;
    s.append(svg("line", {
      x1, y1, x2, y2,
      stroke: gaugeColor(t),
      "stroke-width": 5,
      "stroke-linecap": "round",
      opacity: on ? 1 : 0.18,
    }));
  }
  const wrap = LaaC.el("div", { class: "gauge-wrap" });
  const gauge = LaaC.el("div", { class: "gauge" });
  gauge.append(s);
  gauge.append(LaaC.el("div", {
    style: "position:absolute;left:0;right:0;top:52px;text-align:center",
  },
    LaaC.el("div", { class: "value" }, String(score)),
    LaaC.el("div", { class: "max" }, "/100"),
  ));
  wrap.append(gauge);
  wrap.append(LaaC.el("span", { class: "badge badge--" + status.level, style: "font-size:13px" },
    "⚠ " + status.label.toUpperCase()));
  return wrap;
}

const METRIC_ICONS = {
  shield: '<path d="M12 3l7 3v6c0 4-3 7-7 9-4-2-7-5-7-9V6z"/>',
  bug: '<rect x="8" y="8" width="8" height="10" rx="4"/><path d="M12 4v3M5 9l3 1M19 9l-3 1M4 15h3M17 15h3"/>',
  activity: '<path d="M3 12h4l3 8 4-16 3 8h4"/>',
  gauge: '<path d="M12 13l4-3M4 18a8 8 0 1 1 16 0"/>',
};

function renderMetric(m) {
  const iconColor = `var(--${m.level === "critical" ? "critical" : m.level === "warning" ? "warning" : "stable"})`;
  const icon = LaaC.el("div", {
    class: "m-icon",
    style: `background:rgba(255,255,255,0.04);color:${iconColor}`,
    html: `<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${METRIC_ICONS[m.icon] || METRIC_ICONS.bug}</svg>`,
  });
  return LaaC.el("div", { class: "metric-card" }, icon,
    LaaC.el("div", {},
      LaaC.el("div", { class: "m-label" }, m.label),
      LaaC.el("div", { class: "m-value", style: `color:${iconColor}` }, m.value),
    ),
  );
}

function renderChart(chart) {
  const W = 640, H = 200, pad = 8;
  const s = svg("svg", { viewBox: `0 0 ${W} ${H}`, width: "100%", height: "220", preserveAspectRatio: "none" });
  // horizontal grid lines
  for (let g = 0; g <= 4; g++) {
    const y = pad + (H - pad * 2) * (g / 4);
    s.append(svg("line", { x1: 0, y1: y, x2: W, y2: y, stroke: "var(--border-soft)", "stroke-width": 1 }));
  }
  const n = chart.labels.length;
  for (const serie of chart.series) {
    const pts = serie.data.map((v, i) => {
      const x = (i / (n - 1)) * W;
      const y = H - pad - (v / 100) * (H - pad * 2);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(" ");
    s.append(svg("polyline", {
      points: pts, fill: "none", stroke: serie.color,
      "stroke-width": 2.5, "stroke-linejoin": "round", "stroke-linecap": "round",
    }));
  }
  const labels = LaaC.el("div", { class: "row", style: "justify-content:space-between;font-size:11px;color:var(--text-dim);margin-top:6px" });
  chart.labels.forEach((l, i) => { if (i % 3 === 0) labels.append(LaaC.el("span", {}, l)); });
  return LaaC.el("div", {}, s, labels);
}

/* Bug category choices offered by the report mini-form (mirrors Bug.Category). */
const BUG_CATEGORIES = [
  ["crash", "Crash"],
  ["graphics", "Gráficos"],
  ["performance", "Desempenho"],
  ["progression", "Progressão"],
  ["online", "Online"],
  ["other", "Outro"],
];

function severityLevel(severity) {
  if (severity === "critical") return "critical";
  if (severity === "high" || severity === "medium") return "warning";
  return "stable";
}

/* One row in the "bugs reportados" list. */
function renderBugRow(b) {
  return LaaC.el("div", { class: "activity-item" },
    LaaC.el("div", {},
      LaaC.el("div", { class: "a-title" }, b.title),
      LaaC.el("div", { class: "a-sub" }, b.category + " · " + b.confirmations + " confirmações")),
    LaaC.badge(b.severity_display, severityLevel(b.severity)));
}

/* Inline "Reportar um bug" composer: category select + textarea, posts to
   /api/v1/bug-reports/ and reloads the screen on success. */
function buildReportForm(gameSlug) {
  const fieldStyle =
    "width:100%;background:var(--surface-2);border:1px solid var(--border);" +
    "border-radius:10px;padding:10px 12px;color:var(--text);font:inherit;margin-top:8px";

  const category = LaaC.el("select", { style: fieldStyle });
  BUG_CATEGORIES.forEach(([v, l]) => category.append(LaaC.el("option", { value: v }, l)));
  const text = LaaC.el("textarea", { placeholder: "Descreva o bug…", rows: "3", style: fieldStyle });
  const error = LaaC.el("div", { style: "color:var(--critical);font-size:12px;margin-top:6px;display:none" });

  const submit = LaaC.el("button", {
    class: "btn btn--primary", style: "margin-top:8px",
    onclick: async () => {
      if (!text.value.trim()) return;
      submit.disabled = true; error.style.display = "none";
      try {
        await LaaC.sendJSON("/api/v1/bug-reports/", {
          game: gameSlug, text: text.value.trim(), category: category.value,
        });
        location.reload();
      } catch (e) {
        error.textContent = "Não foi possível reportar. " + e.message;
        error.style.display = "block";
        submit.disabled = false;
      }
    },
  }, "Enviar");

  return LaaC.el("div", { class: "card", id: "bm-report-form", style: "margin-top:12px" },
    LaaC.el("div", { style: "font-weight:800;margin-bottom:4px" }, "Descreva o problema"),
    category, text, error, submit);
}

async function initBugometro() {
  const data = await LaaC.getJSON("/api/bugometro/");
  const g = data.game;

  document.getElementById("bm-cover").style = LaaC.coverStyle(g.cover);
  document.getElementById("bm-cover").textContent = g.initials;
  document.getElementById("bm-name").textContent = g.name;
  const upd = document.getElementById("bm-updated");
  upd.textContent = "🟢 " + data.updated_ago;

  const gaugeHost = document.getElementById("bm-gauge");
  gaugeHost.replaceWith(renderGauge(g.score, g.status));

  const metrics = document.getElementById("bm-metrics");
  data.metrics.forEach((m) => metrics.append(renderMetric(m)));

  // Bugs ativos do jogo (sem container dedicado no template: cria um bloco
  // simples logo abaixo dos cards de métricas).
  const bugsHost = LaaC.el("div", { id: "bm-bugs", class: "mt" },
    LaaC.el("div", { class: "section-title" }, "Bugs reportados"));
  if (data.bugs.length === 0) {
    bugsHost.append(LaaC.el("div", { class: "muted" }, "Nenhum bug ativo reportado."));
  }
  data.bugs.forEach((b) => bugsHost.append(renderBugRow(b)));
  document.getElementById("bm-panel").append(bugsHost);

  // "Reportar um bug": alterna um mini-form inline abaixo do botão.
  const reportBtn = document.getElementById("bm-report-btn");
  if (reportBtn) {
    reportBtn.addEventListener("click", () => {
      const existing = document.getElementById("bm-report-form");
      if (existing) { existing.remove(); return; }
      reportBtn.closest(".chart-card").append(buildReportForm(g.slug));
    });
  }

  const legend = document.getElementById("bm-legend");
  data.chart.series.forEach((serie) =>
    legend.append(LaaC.el("span", {},
      LaaC.el("span", { class: "dot", style: `background:${serie.color}` }), serie.label)));

  document.getElementById("bm-chart").append(renderChart(data.chart));

  const activity = document.getElementById("bm-activity");
  data.activity.forEach((a) => {
    activity.append(LaaC.el("div", { class: "activity-item" },
      LaaC.el("div", { class: "a-icon", style: `color:var(--${a.level === "critical" ? "critical" : "warning"})`, html:
        '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M3 12h4l3 7 4-14 3 7h4"/></svg>' }),
      LaaC.el("div", {},
        LaaC.el("div", { class: "a-title" }, a.title),
        LaaC.el("div", { class: "a-sub" }, a.subtitle)),
      LaaC.el("div", { class: "a-when" }, a.when)));
  });

  const top = document.getElementById("bm-top");
  data.top_unstable.forEach((t) => {
    top.append(LaaC.el("div", { class: "rank-row" },
      LaaC.el("div", { class: "cover", style: LaaC.coverStyle(["#3a4a3f", "#1b241f"]) }, "WZ"),
      LaaC.el("div", { class: "r-name" }, t.name),
      LaaC.el("b", {}, String(t.score)),
      LaaC.badge(t.status.label, t.status.level)));
  });
}

document.addEventListener("DOMContentLoaded", () => initBugometro().catch((e) => {
  if (e.message !== "unauthenticated") console.error(e);
}));
