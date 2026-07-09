/* Históricos screen: bug_score time series for a game from the user's
   library, with a game selector and a 7d/30d/90d window. The chart is a
   plain inline SVG (same approach as the bugômetro chart), but drawn as a
   single line and defensive about sparse data: with 0 or 1 points there is
   no line to draw (a polyline needs at least two points to divide the width
   by), so we render an empty-state / single dot instead of a NaN polyline. */

const SVGNS = "http://www.w3.org/2000/svg";

function svg(tag, attrs = {}) {
  const node = document.createElementNS(SVGNS, tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  return node;
}

/* Renders `series` ({labels, data}) as a single-line chart. Guards against
   dividing by zero: `data.length <= 1` never reaches the `x = i / (n - 1)`
   step that would produce NaN/Infinity coordinates. */
function renderLineChart(series) {
  const data = series.data || [];
  const labels = series.labels || [];
  const n = data.length;

  if (n <= 1) {
    const msg = n === 0
      ? "Sem dados no período selecionado."
      : "Dados insuficientes para o gráfico.";
    const W = 640, H = 200, pad = 8;
    const s = svg("svg", { viewBox: `0 0 ${W} ${H}`, width: "100%", height: "220", preserveAspectRatio: "none" });
    for (let g = 0; g <= 4; g++) {
      const y = pad + (H - pad * 2) * (g / 4);
      s.append(svg("line", { x1: 0, y1: y, x2: W, y2: y, stroke: "var(--border-soft)", "stroke-width": 1 }));
    }
    if (n === 1) {
      const y = H - pad - (data[0] / 100) * (H - pad * 2);
      s.append(svg("circle", { cx: W / 2, cy: y, r: 4, fill: "#e01e2b" }));
    }
    return LaaC.el("div", {},
      s,
      LaaC.el("div", { class: "muted", style: "text-align:center;margin-top:6px;font-size:13px" }, msg),
    );
  }

  const W = 640, H = 200, pad = 8;
  const s = svg("svg", { viewBox: `0 0 ${W} ${H}`, width: "100%", height: "220", preserveAspectRatio: "none" });
  for (let g = 0; g <= 4; g++) {
    const y = pad + (H - pad * 2) * (g / 4);
    s.append(svg("line", { x1: 0, y1: y, x2: W, y2: y, stroke: "var(--border-soft)", "stroke-width": 1 }));
  }
  const pts = data.map((v, i) => {
    const x = (i / (n - 1)) * W;
    const y = H - pad - (v / 100) * (H - pad * 2);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
  s.append(svg("polyline", {
    points: pts, fill: "none", stroke: "#e01e2b",
    "stroke-width": 2.5, "stroke-linejoin": "round", "stroke-linecap": "round",
  }));

  const labelRow = LaaC.el("div", { class: "row", style: "justify-content:space-between;font-size:11px;color:var(--text-dim);margin-top:6px" });
  labels.forEach((l, i) => { if (i % 3 === 0) labelRow.append(LaaC.el("span", {}, l)); });
  return LaaC.el("div", {}, s, labelRow);
}

async function initHistoricos() {
  const empty = document.getElementById("hi-empty");
  const body = document.getElementById("hi-body");
  const select = document.getElementById("hi-game");
  const chartHost = document.getElementById("hi-chart");
  const rangeTabs = document.querySelectorAll("#hi-range button[data-r]");

  function setActiveTab(range) {
    rangeTabs.forEach((b) => b.classList.toggle("is-active", Number(b.dataset.r) === Number(range)));
  }

  function renderChart(series) {
    chartHost.innerHTML = "";
    chartHost.append(renderLineChart(series));
  }

  async function load(gameSlug, range) {
    const params = new URLSearchParams();
    if (gameSlug) params.set("game", gameSlug);
    if (range) params.set("range", range);
    const data = await LaaC.getJSON("/api/historicos/?" + params.toString());

    if (!data.games || data.games.length === 0) {
      empty.hidden = false;
      body.hidden = true;
      return data;
    }
    empty.hidden = true;
    body.hidden = false;

    select.innerHTML = "";
    data.games.forEach((g) => {
      select.append(LaaC.el("option", { value: g.slug }, g.name));
    });
    if (data.selected) select.value = data.selected.slug;

    setActiveTab(data.range);
    renderChart(data.series);
    return data;
  }

  select.addEventListener("change", async () => {
    const activeTab = document.querySelector("#hi-range button.is-active");
    try {
      await load(select.value, activeTab ? activeTab.dataset.r : 30);
    } catch (e) {
      LaaC.toast("Não foi possível carregar o histórico.", "critical");
    }
  });

  rangeTabs.forEach((btn) => {
    btn.addEventListener("click", async () => {
      if (btn.classList.contains("is-active")) return;
      try {
        await load(select.value, btn.dataset.r);
      } catch (e) {
        LaaC.toast("Não foi possível carregar o histórico.", "critical");
      }
    });
  });

  await load(null, 30);
}

document.addEventListener("DOMContentLoaded", () => initHistoricos().catch((e) => {
  if (e.message !== "unauthenticated") console.error(e);
}));
