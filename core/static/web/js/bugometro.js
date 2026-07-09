/* Bugômetro screen: gauge + range-tabbed chart + metrics + activity + ranking
   + active bugs (voting/moderation) + report form.
   Gauge and chart are drawn as plain inline SVG — no charting library, kept
   verbatim from the pre-Bootstrap version (only their host markup changed). */

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

/* Bootstrap subtle-bg utilities from theme.css, keyed by status level. Local
   to this file (same convention as explore.js/library.js's scoreBadge()) so
   the shared LaaC.badge() (still used by the not-yet-migrated game_detail.js)
   stays untouched. */
const LEVEL_BADGE_CLASS = {
  critical: "bg-critical-subtle",
  warning: "bg-warning-subtle-2",
  stable: "bg-stable-subtle",
};

function levelBadge(text, level) {
  return LaaC.el("span", { class: "badge rounded-pill " + (LEVEL_BADGE_CLASS[level] || "bg-secondary-subtle") }, text);
}

/* The SVG gauge ring/tick drawing is unchanged from the pre-Bootstrap version
   — only the surrounding markup (status pill) was reclassed. */
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
  wrap.append(levelBadge(status.label.toUpperCase(), status.level));
  return wrap;
}

/* Maps the API's metric.icon key (unchanged backend contract, see
   core/services.py _METRIC_DEFS) to a Material Symbols glyph name. */
const METRIC_ICON_NAMES = {
  shield: "shield",
  bug: "bug_report",
  activity: "monitoring",
  gauge: "speed",
};

function renderMetric(m) {
  const cls = LEVEL_BADGE_CLASS[m.level] || "bg-secondary-subtle";
  const icon = LaaC.icon(METRIC_ICON_NAMES[m.icon] || "bug_report");
  const iconBox = LaaC.el("div", {
    class: "rounded-3 d-flex align-items-center justify-content-center flex-shrink-0 " + cls,
    style: "width:42px;height:42px",
  }, icon);
  return LaaC.el("div", { class: "col" },
    LaaC.el("div", { class: "card h-100" },
      LaaC.el("div", { class: "card-body d-flex align-items-center gap-3" },
        iconBox,
        LaaC.el("div", {},
          LaaC.el("div", { class: "text-secondary-emphasis small" }, m.label),
          LaaC.el("div", { class: "fw-bold fs-5" }, m.value)),
      ),
    ),
  );
}

/* Line-chart SVG drawing is unchanged from the pre-Bootstrap version — only
   the host markup (card, legend) around it changed. */
function renderChart(chart) {
  const W = 640, H = 200, pad = 8;
  const s = svg("svg", { viewBox: `0 0 ${W} ${H}`, width: "100%", height: "220", preserveAspectRatio: "none" });
  // horizontal grid lines
  for (let g = 0; g <= 4; g++) {
    const y = pad + (H - pad * 2) * (g / 4);
    s.append(svg("line", { x1: 0, y1: y, x2: W, y2: y, stroke: "var(--border-soft)", "stroke-width": 1 }));
  }
  const n = chart.labels.length;
  const denom = Math.max(n - 1, 1);
  for (const serie of chart.series) {
    const pts = serie.data.map((v, i) => {
      const x = (i / denom) * W;
      const y = H - pad - (v / 100) * (H - pad * 2);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(" ");
    s.append(svg("polyline", {
      points: pts, fill: "none", stroke: serie.color,
      "stroke-width": 2.5, "stroke-linejoin": "round", "stroke-linecap": "round",
    }));
  }
  const labels = LaaC.el("div", { class: "d-flex justify-content-between small text-secondary-emphasis mt-2" });
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

/* Confirm/reject/resolve buttons for games moderators (LaaC.me.is_games_moderator).
   Returns null (nothing rendered) for regular users or before LaaC.me resolves. */
function bugModActions(bug, reload) {
  if (!(LaaC.me && LaaC.me.is_games_moderator)) return null;
  const act = async (verb, btn) => {
    btn.disabled = true;
    try {
      await LaaC.sendJSON(`/api/v1/bugs/${bug.id}/${verb}/`, {});
      LaaC.toast("Bug atualizado.", "stable");
      await reload();
    } catch (e) {
      LaaC.toast("Ação de moderação falhou.", "critical");
    } finally {
      btn.disabled = false;
    }
  };
  const confirmBtn = LaaC.el("button", { type: "button", class: "btn btn-outline-success" }, "Confirmar");
  const rejectBtn = LaaC.el("button", { type: "button", class: "btn btn-outline-danger" }, "Rejeitar");
  const resolveBtn = LaaC.el("button", { type: "button", class: "btn btn-outline-primary" }, "Resolver");
  confirmBtn.addEventListener("click", () => act("confirm", confirmBtn));
  rejectBtn.addEventListener("click", () => act("reject", rejectBtn));
  resolveBtn.addEventListener("click", () => act("resolve", resolveBtn));
  return LaaC.el("div", { class: "btn-group btn-group-sm", role: "group", "aria-label": "Ações de moderação" },
    confirmBtn, rejectBtn, resolveBtn);
}

/* Confirm/undo-confirm vote button, reflecting bug.user_vote_id state.
   Toggles POST/DELETE against /api/v1/bug-votes/ and re-renders via onChange. */
function voteButton(bug, onChange) {
  const voted = bug.user_vote_id != null;
  const icon = LaaC.icon("check_circle");
  icon.style.fontSize = "16px";
  const btn = LaaC.el("button", {
    type: "button",
    class: "btn btn-sm d-inline-flex align-items-center gap-1 " + (voted ? "btn-success" : "btn-outline-secondary"),
    "aria-pressed": voted ? "true" : "false",
  }, icon, `Confirmar (${bug.confirmations})`);
  btn.addEventListener("click", async () => {
    btn.disabled = true;
    try {
      if (bug.user_vote_id != null) {
        await LaaC.sendJSON(`/api/v1/bug-votes/${bug.user_vote_id}/`, null, "DELETE");
        bug.user_vote_id = null; bug.confirmations = Math.max(0, bug.confirmations - 1);
      } else {
        const v = await LaaC.sendJSON("/api/v1/bug-votes/", { bug: bug.id });
        bug.user_vote_id = v.id; bug.confirmations += 1;
      }
      onChange(bug);
    } catch (e) { LaaC.toast("Não foi possível registrar o voto.", "critical"); }
    finally { btn.disabled = false; }
  });
  return btn;
}

/* One row in the "bugs reportados" list. `reload` re-fetches the bugs list
   after a moderation action (only used when mod actions are rendered). */
function renderBugRow(b, reload) {
  const sub = LaaC.el("div", { class: "text-secondary-emphasis small" }, b.category + " · " + b.confirmations + " confirmações");
  const row = LaaC.el("div", { class: "d-flex align-items-center gap-3 flex-wrap border rounded-3 p-3" },
    LaaC.el("div", { class: "flex-grow-1" },
      LaaC.el("div", { class: "fw-semibold" }, b.title),
      sub),
    levelBadge(b.severity_display, severityLevel(b.severity)));
  let vote = voteButton(b, onVoteChange);
  function onVoteChange(updated) {
    sub.textContent = updated.category + " · " + updated.confirmations + " confirmações";
    const fresh = voteButton(updated, onVoteChange);
    vote.replaceWith(fresh);
    vote = fresh;
  }
  row.append(vote);
  const modActions = bugModActions(b, reload);
  if (modActions) row.append(modActions);
  return row;
}

/* Inline "Reportar um bug" composer: category select + textarea, posts to
   /api/v1/bug-reports/ and reloads the screen on success. */
function buildReportForm(gameSlug) {
  const category = LaaC.el("select", { class: "form-select", id: "bm-report-category" });
  BUG_CATEGORIES.forEach(([v, l]) => category.append(LaaC.el("option", { value: v }, l)));
  const text = LaaC.el("textarea", { class: "form-control", id: "bm-report-text", placeholder: "Descreva o bug…", rows: "3" });
  const error = LaaC.el("div", { class: "text-danger small mt-2 d-none" });
  const submit = LaaC.el("button", { type: "submit", class: "btn btn-primary mt-3" }, "Enviar");

  const form = LaaC.el("form", { id: "bm-report-form", class: "card card-body mt-3", novalidate: "" },
    LaaC.el("h3", { class: "h6 mb-3" }, "Descreva o problema"),
    LaaC.el("div", { class: "mb-3" },
      LaaC.el("label", { class: "form-label small", for: "bm-report-category" }, "Categoria"),
      category),
    LaaC.el("div", {},
      LaaC.el("label", { class: "form-label small", for: "bm-report-text" }, "Descrição"),
      text),
    error, submit);

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!text.value.trim()) return;
    submit.disabled = true; error.classList.add("d-none");
    try {
      await LaaC.sendJSON("/api/v1/bug-reports/", {
        game: gameSlug, text: text.value.trim(), category: category.value,
      });
      location.reload();
    } catch (e2) {
      error.textContent = "Não foi possível reportar. " + e2.message;
      error.classList.remove("d-none");
      submit.disabled = false;
    }
  });

  return form;
}

function renderActivityItem(a) {
  const cls = a.level === "critical" ? "bg-critical-subtle" : "bg-warning-subtle-2";
  const icon = LaaC.icon("warning");
  icon.style.fontSize = "18px";
  return LaaC.el("div", { class: "list-group-item d-flex align-items-center gap-3" },
    LaaC.el("div", {
      class: "rounded-3 d-flex align-items-center justify-content-center flex-shrink-0 " + cls,
      style: "width:38px;height:38px",
    }, icon),
    LaaC.el("div", { class: "flex-grow-1" },
      LaaC.el("div", { class: "fw-semibold small" }, a.title),
      LaaC.el("div", { class: "text-secondary-emphasis small" }, a.subtitle)),
    LaaC.el("div", { class: "text-secondary-emphasis small text-nowrap" }, a.when));
}

function renderTopRow(t) {
  const cover = LaaC.el("div", { class: "cover flex-shrink-0", style: LaaC.coverStyle(["#3a4a3f", "#1b241f"]) }, LaaC.initials(t.name));
  cover.style.width = "42px"; cover.style.height = "30px"; cover.style.fontSize = "10px";
  const body = [
    cover,
    LaaC.el("div", { class: "flex-grow-1 text-truncate fw-semibold" }, t.name),
    LaaC.el("span", { class: "fw-bold" }, String(t.score)),
    levelBadge(t.status.label, t.status.level),
  ];
  return t.slug
    ? LaaC.el("a", { class: "list-group-item list-group-item-action d-flex align-items-center gap-2 text-decoration-none text-reset", href: "/jogo/" + t.slug + "/" }, ...body)
    : LaaC.el("div", { class: "list-group-item d-flex align-items-center gap-2" }, ...body);
}

async function initBugometro() {
  const data = await LaaC.getJSON("/api/bugometro/");
  const g = data.game;

  document.getElementById("bm-cover").style = LaaC.coverStyle(g.cover);
  document.getElementById("bm-cover").textContent = g.initials;
  document.getElementById("bm-name").textContent = g.name;
  const upd = document.getElementById("bm-updated");
  const updIcon = LaaC.icon("schedule");
  updIcon.style.fontSize = "14px";
  upd.replaceChildren(updIcon, document.createTextNode(data.updated_ago));

  // "Seguir": adiciona o jogo à biblioteca do usuário.
  const followBtn = document.getElementById("bm-follow-btn");
  followBtn.addEventListener("click", async () => {
    followBtn.disabled = true;
    try {
      await LaaC.sendJSON("/api/v1/library/", { game: g.slug });
      LaaC.toast("Adicionado à sua biblioteca.", "stable");
    } catch (e) {
      LaaC.toast("Não foi possível seguir o jogo.", "critical");
    } finally {
      followBtn.disabled = false;
    }
  });

  const gaugeHost = document.getElementById("bm-gauge");
  gaugeHost.replaceWith(renderGauge(g.score, g.status));

  const metrics = document.getElementById("bm-metrics");
  data.metrics.forEach((m) => metrics.append(renderMetric(m)));

  /* Re-render the bugs list from a fresh dataset (initial load or reload). */
  const bugsHost = document.getElementById("bm-bugs");
  function renderBugsList(bugs) {
    bugsHost.replaceChildren();
    if (bugs.length === 0) {
      bugsHost.append(LaaC.el("div", { class: "text-secondary-emphasis small py-3" }, "Nenhum bug ativo reportado."));
      return;
    }
    bugs.forEach((b) => bugsHost.append(renderBugRow(b, reloadBugs)));
  }

  /* Re-fetch /api/bugometro/ and re-render just the bugs list (used after a
     moderation action changes a bug's status). */
  async function reloadBugs() {
    const fresh = await LaaC.getJSON("/api/bugometro/");
    renderBugsList(fresh.bugs);
  }

  renderBugsList(data.bugs);

  // "Reportar um bug": alterna um mini-form inline abaixo do botão.
  const reportBtn = document.getElementById("bm-report-btn");
  if (reportBtn) {
    reportBtn.addEventListener("click", () => {
      const existing = document.getElementById("bm-report-form");
      if (existing) { existing.remove(); return; }
      reportBtn.closest(".card").append(buildReportForm(g.slug));
    });
  }

  /* Render the legend + chart from a `chart` payload ({labels, series}),
     replacing whatever was there before (used on load and on range-tab switch). */
  function renderChartAndLegend(chart) {
    const legend = document.getElementById("bm-legend");
    legend.replaceChildren();
    chart.series.forEach((serie) =>
      legend.append(LaaC.el("span", { class: "d-inline-flex align-items-center gap-1" },
        LaaC.el("span", { class: "rounded-circle", style: `display:inline-block;width:8px;height:8px;background:${serie.color}` }),
        serie.label)));

    const chartHost = document.getElementById("bm-chart");
    chartHost.replaceChildren(renderChart(chart));
  }

  renderChartAndLegend(data.chart);

  // Abas de faixa (7d/30d/90d): re-busca o bugômetro do jogo atual com a
  // faixa selecionada e re-renderiza só o gráfico + legenda.
  const rangeTabs = document.querySelectorAll("#bm-range button[data-r]");
  rangeTabs.forEach((btn) => {
    btn.addEventListener("click", async () => {
      if (btn.classList.contains("active")) return;
      rangeTabs.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      try {
        const fresh = await LaaC.getJSON(
          `/api/bugometro/?game=${encodeURIComponent(g.slug)}&range=${btn.dataset.r}`
        );
        renderChartAndLegend(fresh.chart);
      } catch (e) {
        LaaC.toast("Não foi possível carregar o gráfico.", "critical");
      }
    });
  });

  const activity = document.getElementById("bm-activity");
  if (data.activity.length === 0) {
    activity.append(LaaC.el("div", { class: "list-group-item text-secondary-emphasis small" }, "Sem atividade recente."));
  } else {
    data.activity.forEach((a) => activity.append(renderActivityItem(a)));
  }

  const top = document.getElementById("bm-top");
  if (data.top_unstable.length === 0) {
    top.append(LaaC.el("div", { class: "list-group-item text-secondary-emphasis small" }, "Sem dados suficientes."));
  } else {
    data.top_unstable.forEach((t) => top.append(renderTopRow(t)));
  }
}

document.addEventListener("DOMContentLoaded", () => initBugometro().catch((e) => {
  if (e.message !== "unauthenticated") console.error(e);
}));
