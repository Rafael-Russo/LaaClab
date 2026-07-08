/* Alertas screen: lista de alertas dos jogos + resumo, favoritos e CTA.
   Os ícones são desenhados como SVG inline (estilo feather) — sem biblioteca. */

// Ícones escolhidos pelo campo `icon` de cada alerta (wifi / alert / check).
const ALERT_ICONS = {
  wifi: '<path d="M5 12.55a11 11 0 0 1 14.08 0"/><path d="M1.42 9a16 16 0 0 1 21.16 0"/><path d="M8.53 16.11a6 6 0 0 1 6.95 0"/><path d="M12 20h.01"/>',
  alert: '<path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z"/><path d="M12 9v4M12 17h.01"/>',
  check: '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><path d="m22 4-10 10.01L9 11"/>',
};

// O resumo não traz `icon`, então mapeamos a severidade para um ícone.
const LEVEL_ICON = { critical: "wifi", warning: "alert", stable: "check" };

// Ciclo do botão "Filtrar": sem filtro -> um nível por vez -> de volta.
const LEVEL_CYCLE = [null, "critical", "warning", "stable"];
const LEVEL_LABEL = { critical: "Críticos", warning: "Instável", stable: "Atualização" };

// Monta um ícone SVG inline colorido pela severidade (via currentColor).
function glyphSvg(icon, size) {
  const body = ALERT_ICONS[icon] || ALERT_ICONS.alert;
  return '<svg viewBox="0 0 24 24" width="' + size + '" height="' + size +
    '" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
    body + '</svg>';
}

// Cada alerta vira uma .alert-row: capa, corpo (selo + jogo + texto) e status.
function renderAlert(a) {
  return LaaC.el("div", { class: "alert-row" },
    // Capa placeholder do jogo com as iniciais (não enviamos arte de terceiros).
    LaaC.el("div", { class: "cover", style: LaaC.coverStyle() }, LaaC.initials(a.game)),
    // Corpo: selo de severidade, nome do jogo e descrição.
    LaaC.el("div", { class: "a-body" },
      LaaC.badge(a.severity, a.level),
      LaaC.el("div", { class: "a-title" }, a.game),
      LaaC.el("div", { class: "a-text" }, a.text)),
    // Status: glifo circular colorido + botão de detalhes.
    LaaC.el("div", { class: "a-status" },
      LaaC.el("div", { class: "status-glyph " + a.level, html: glyphSvg(a.icon, 28) }),
      LaaC.el("button", {
        class: "btn btn--outline", style: "padding:6px 14px;font-size:12px",
        onclick: () => { window.location = "/jogo/" + a.slug + "/"; },
      }, "Ver detalhes")));
}

// Linha do resumo: glifo colorido, contagem em destaque e rótulo.
function renderSummaryRow(s) {
  return LaaC.el("div", { class: "summary-row" },
    LaaC.el("span", { style: "color:var(--" + s.level + ");display:grid;place-items:center",
      html: glyphSvg(LEVEL_ICON[s.level] || "alert", 22) }),
    LaaC.el("span", { class: "n", style: "font-size:20px" }, String(s.count)),
    LaaC.el("span", {}, s.label));
}

// Linha de jogo favorito: capa pequena + nome.
function renderFavorite(f) {
  return LaaC.el("div", { class: "fav-row" },
    LaaC.cover(f),
    LaaC.el("span", { class: "f-name" }, f.name));
}

// Estado da tela: termo de busca + nível ativo, refletidos na querystring
// usada para recarregar a lista a partir de /api/alertas/.
const state = { q: "", level: null };

function buildQuery() {
  const p = new URLSearchParams();
  if (state.q) p.set("q", state.q);
  if (state.level) p.set("level", state.level);
  const s = p.toString();
  return s ? "?" + s : "";
}

// Busca e recarrega a lista + resumo + favoritos a partir do estado atual.
async function reloadAlerts() {
  const data = await LaaC.getJSON("/api/alertas/" + buildQuery());

  // Lista principal de alertas.
  const list = document.getElementById("al-list");
  list.innerHTML = "";
  if (data.alerts.length === 0) {
    list.innerHTML = "<div class='muted' style='padding:16px'>Nenhum alerta encontrado.</div>";
  } else {
    data.alerts.forEach((a) => list.append(renderAlert(a)));
  }

  // Resumo de alertas (trilha lateral).
  const summary = document.getElementById("al-summary");
  summary.innerHTML = "";
  data.summary.forEach((s) => summary.append(renderSummaryRow(s)));

  // Jogos favoritos (trilha lateral).
  const favorites = document.getElementById("al-favorites");
  favorites.innerHTML = "";
  data.favorites.forEach((f) => favorites.append(renderFavorite(f)));
}

async function initAlerts() {
  await reloadAlerts();

  // Busca por jogo: dispara a cada digitação (o termo vai como `q`).
  const search = document.getElementById("al-search");
  search.addEventListener("input", () => {
    state.q = search.value.trim();
    reloadAlerts().catch((e) => { if (e.message !== "unauthenticated") console.error(e); });
  });

  // "Filtrar" cicla entre os níveis (sem filtro -> crítico -> instável ->
  // atualização -> sem filtro), atualizando o rótulo do botão.
  const filterBtn = document.getElementById("al-filter");
  filterBtn.addEventListener("click", () => {
    const next = (LEVEL_CYCLE.indexOf(state.level) + 1) % LEVEL_CYCLE.length;
    state.level = LEVEL_CYCLE[next];
    filterBtn.textContent = state.level ? "▽ " + LEVEL_LABEL[state.level] : "▽ Filtrar";
    reloadAlerts().catch((e) => { if (e.message !== "unauthenticated") console.error(e); });
  });
}

document.addEventListener("DOMContentLoaded", () => initAlerts().catch((e) => {
  if (e.message !== "unauthenticated") console.error(e);
}));
