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
      LaaC.el("button", { class: "btn btn--outline", style: "padding:6px 14px;font-size:12px" }, "Ver detalhes")));
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

async function initAlerts() {
  const data = await LaaC.getJSON("/api/alertas/");

  // Lista principal de alertas.
  const list = document.getElementById("al-list");
  list.innerHTML = "";
  data.alerts.forEach((a) => list.append(renderAlert(a)));

  // Resumo de alertas (trilha lateral).
  const summary = document.getElementById("al-summary");
  data.summary.forEach((s) => summary.append(renderSummaryRow(s)));

  // Jogos favoritos (trilha lateral).
  const favorites = document.getElementById("al-favorites");
  data.favorites.forEach((f) => favorites.append(renderFavorite(f)));
}

document.addEventListener("DOMContentLoaded", () => initAlerts().catch((e) => {
  if (e.message !== "unauthenticated") console.error(e);
}));
