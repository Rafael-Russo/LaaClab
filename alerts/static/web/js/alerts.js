/* Alertas screen: lista de alertas dos jogos + resumo, favoritos e CTA.
   Data comes from /api/alertas/ (unchanged since P4a/P4b): search (`q`),
   level filter (`level`), summary counts always unfiltered (P4b fix). */

/* Bootstrap subtle-bg badge helper (same convention as game_detail.js's/
   bugometro.js's/community.js's LEVEL_BADGE_CLASS): every screen renders its
   own status color mapping now that the legacy LaaC.badge() (.badge--*
   classes) has been removed as dead code. */
const LEVEL_BADGE_CLASS = {
  critical: "bg-critical-subtle",
  warning: "bg-warning-subtle-2",
  stable: "bg-stable-subtle",
};

function levelBadge(text, level) {
  return LaaC.el("span", { class: "badge rounded-pill " + (LEVEL_BADGE_CLASS[level] || "bg-secondary-subtle") }, text);
}

/* Maps the API's `level` (derived from Alert.PRESENTATION, see
   alerts/models.py) to a Material Symbols glyph name — same mapping already
   used by game_detail.js's alerts-tab rows, kept identical here so the same
   alert reads the same icon everywhere. */
const ALERT_ICON = { critical: "error", warning: "warning", stable: "check_circle" };

/* Cada alerta vira uma linha da lista: capa placeholder do jogo, selo de
   severidade + nome + texto, glifo de status e um link "Ver detalhes". */
function renderAlert(a) {
  const cls = LEVEL_BADGE_CLASS[a.level] || "bg-secondary-subtle";
  const icon = LaaC.icon(ALERT_ICON[a.level] || "info");
  icon.style.fontSize = "20px";
  // A API de alertas não envia campos de capa (cover/initials) do jogo —
  // só o nome —, então montamos um objeto mínimo para LaaC.cover().
  const cover = LaaC.cover({ name: a.game, initials: LaaC.initials(a.game) }, "flex-shrink-0");
  cover.style.width = "48px";
  cover.style.height = "48px";
  cover.style.fontSize = "14px";

  return LaaC.el("div", { class: "list-group-item d-flex align-items-center gap-3" },
    cover,
    LaaC.el("div", { class: "flex-grow-1", style: "min-width:0" },
      LaaC.el("div", { class: "d-flex align-items-center gap-2 mb-1" },
        levelBadge(a.severity, a.level),
        LaaC.el("span", { class: "fw-semibold text-truncate" }, a.game)),
      LaaC.el("div", { class: "text-secondary-emphasis small" }, a.text)),
    LaaC.el("div", {
      class: "rounded-3 d-flex align-items-center justify-content-center flex-shrink-0 " + cls,
      style: "width:38px;height:38px",
    }, icon),
    LaaC.el("a", {
      class: "btn btn-outline-secondary btn-sm flex-shrink-0",
      href: "/jogo/" + a.slug + "/",
    }, "Ver detalhes"));
}

/* Linha do resumo: glifo colorido por nível + contagem em destaque + rótulo
   (mesmo padrão visual do renderMetric() do bugômetro). */
function renderSummaryRow(s) {
  const cls = LEVEL_BADGE_CLASS[s.level] || "bg-secondary-subtle";
  const icon = LaaC.icon(ALERT_ICON[s.level] || "info");
  icon.style.fontSize = "18px";
  return LaaC.el("div", { class: "d-flex align-items-center gap-3" },
    LaaC.el("div", {
      class: "rounded-3 d-flex align-items-center justify-content-center flex-shrink-0 " + cls,
      style: "width:38px;height:38px",
    }, icon),
    LaaC.el("span", { class: "fw-bold fs-5" }, String(s.count)),
    LaaC.el("span", { class: "text-secondary-emphasis small" }, s.label));
}

/* Linha de jogo favorito: capa pequena + nome + ponto de status (mesmo
   padrão já usado na Home para a mesma lista de favoritos). */
function renderFavorite(f) {
  const thumb = LaaC.cover(f, "flex-shrink-0");
  thumb.style.width = "34px";
  thumb.style.height = "34px";
  thumb.style.fontSize = "10px";
  const body = [
    thumb,
    LaaC.el("span", { class: "flex-grow-1 fw-semibold small text-truncate" }, f.name),
    LaaC.el("span", { class: "dot " + f.status.level }),
  ];
  return f.slug
    ? LaaC.el("a", { class: "list-group-item list-group-item-action d-flex align-items-center gap-2 px-0", href: "/jogo/" + f.slug + "/" }, ...body)
    : LaaC.el("div", { class: "list-group-item d-flex align-items-center gap-2 px-0" }, ...body);
}

// Ciclo do botão "Filtrar": sem filtro -> um nível por vez -> de volta.
const LEVEL_CYCLE = [null, "critical", "warning", "stable"];
const LEVEL_LABEL = { critical: "Críticos", warning: "Instável", stable: "Atualização" };

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
  list.replaceChildren();
  if (data.alerts.length === 0) {
    list.append(LaaC.el("div", { class: "list-group-item text-secondary-emphasis small text-center py-4" }, "Nenhum alerta encontrado."));
  } else {
    data.alerts.forEach((a) => list.append(renderAlert(a)));
  }

  // Resumo de alertas (trilha lateral) — sempre não filtrado (P4b).
  const summary = document.getElementById("al-summary");
  summary.replaceChildren();
  data.summary.forEach((s) => summary.append(renderSummaryRow(s)));

  // Jogos favoritos (trilha lateral).
  const favorites = document.getElementById("al-favorites");
  favorites.replaceChildren();
  if (data.favorites.length === 0) {
    favorites.append(LaaC.el("div", { class: "list-group-item text-secondary-emphasis small px-0" }, "Você ainda não tem jogos favoritos."));
  } else {
    data.favorites.forEach((f) => favorites.append(renderFavorite(f)));
  }
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
  // atualização -> sem filtro), atualizando o rótulo e o destaque do botão.
  const filterBtn = document.getElementById("al-filter");
  const filterLabel = document.getElementById("al-filter-label");
  filterBtn.addEventListener("click", () => {
    const next = (LEVEL_CYCLE.indexOf(state.level) + 1) % LEVEL_CYCLE.length;
    state.level = LEVEL_CYCLE[next];
    filterLabel.textContent = state.level ? LEVEL_LABEL[state.level] : "Filtrar";
    filterBtn.classList.toggle("btn-primary", !!state.level);
    filterBtn.classList.toggle("btn-outline-secondary", !state.level);
    reloadAlerts().catch((e) => { if (e.message !== "unauthenticated") console.error(e); });
  });
}

document.addEventListener("DOMContentLoaded", () => initAlerts().catch((e) => {
  if (e.message !== "unauthenticated") console.error(e);
}));
