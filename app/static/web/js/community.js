/* Comunidade screen: game picker + topic feed + right rail (filters,
   stats, rules). Data comes from /api/comunidade/. Selecting a game, a
   topic type, a sort order or a search term all reload the screen with
   ?game=&type=&q=&ordering= — the four filters persist together across
   reloads; "Nova publicação" creates a topic via the REST API. */

let selectedSlug = null;

/* Bootstrap subtle-bg badge helper (same convention as game_detail.js's
   LEVEL_BADGE_CLASS): every screen renders its own status color mapping now
   that the legacy LaaC.badge() (.badge--* classes) has been removed as dead
   code. */
const LEVEL_BADGE_CLASS = {
  critical: "bg-critical-subtle",
  warning: "bg-warning-subtle-2",
  stable: "bg-stable-subtle",
  info: "bg-info-subtle",
};

function levelBadge(text, level) {
  return LaaC.el("span", { class: "badge rounded-pill " + (LEVEL_BADGE_CLASS[level] || "bg-secondary-subtle") }, text);
}

/* Real topic count from the endpoint. */
function topicCount(game) {
  return typeof game.topic_count === "number" ? game.topic_count : 0;
}

/* "342" → "342", "1284" → "1.284" (formato pt-BR). */
function fmt(n) {
  return Number(n).toLocaleString("pt-BR");
}

/* The four filters this screen persists across reloads, read from the
   current URL querystring. */
function currentFilters() {
  const params = new URLSearchParams(location.search);
  return {
    game: params.get("game") || "",
    type: params.get("type") || "",
    q: params.get("q") || "",
    ordering: params.get("ordering") || "",
  };
}

/* Reloads the screen with the current filters merged with `overrides`, so
   changing one control (game/type/q/ordering) never drops the others. */
function reload(overrides) {
  const merged = Object.assign(currentFilters(), overrides);
  const params = new URLSearchParams();
  Object.entries(merged).forEach(([k, v]) => { if (v) params.set(k, v); });
  const qs = params.toString();
  window.location = location.pathname + (qs ? "?" + qs : "");
}

/* Tile fixo "Todos os jogos" com um ícone de grade no lugar da capa. */
function renderAllTile(countLabel) {
  const icon = LaaC.icon("apps");
  icon.classList.add("text-white");
  icon.style.fontSize = "28px";
  const cover = LaaC.el("div", {
    class: "d-flex align-items-center justify-content-center",
    style: LaaC.coverStyle(["#2b2d47", "#12131f"]) + "height:64px;",
  }, icon);
  return LaaC.el("div", {
      class: "card flex-shrink-0 overflow-hidden", style: "width:130px;cursor:pointer",
      onclick: () => reload({ game: "" }),
    }, cover,
    LaaC.el("div", { class: "card-body p-2" },
      LaaC.el("div", { class: "fw-semibold small" }, "Todos os jogos"),
      LaaC.el("div", { class: "text-secondary-emphasis", style: "font-size:11px" }, countLabel)));
}

/* Um tile por jogo do catálogo; marca o jogo selecionado como ativo. */
function renderGameTile(game, active) {
  const cover = LaaC.cover(game, "");
  cover.style.height = "64px";
  cover.style.borderRadius = "0";
  return LaaC.el("div", {
      class: "card flex-shrink-0 overflow-hidden" + (active ? " border-primary border-2" : ""),
      style: "width:130px;cursor:pointer",
      onclick: () => reload({ game: game.slug }),
    }, cover,
    LaaC.el("div", { class: "card-body p-2" },
      LaaC.el("div", { class: "fw-semibold small text-truncate" }, game.name),
      LaaC.el("div", { class: "text-secondary-emphasis", style: "font-size:11px" }, fmt(topicCount(game)) + " tópicos")));
}

/* Hide/lock/pin buttons for forum moderators (LaaC.me.is_forum_moderator).
   The verb toggles with the topic's current state; on success the whole
   community view is reloaded (same post-mutation pattern the composer
   below already uses). Returns null for regular users. */
function topicModActions(topic) {
  if (!(LaaC.me && LaaC.me.is_forum_moderator)) return null;
  const act = async (verb, btn) => {
    btn.disabled = true;
    try {
      await LaaC.sendJSON(`/api/v1/topics/${topic.id}/${verb}/`, {});
      LaaC.toast("Tópico atualizado.", "stable");
      window.location.reload();
    } catch (e) {
      LaaC.toast("Ação de moderação falhou.", "critical");
    } finally {
      btn.disabled = false;
    }
  };
  const hideBtn = LaaC.el("button", { type: "button", class: "btn btn-outline-secondary" }, topic.is_hidden ? "Reexibir" : "Ocultar");
  const lockBtn = LaaC.el("button", { type: "button", class: "btn btn-outline-secondary" }, topic.is_locked ? "Destravar" : "Travar");
  const pinBtn = LaaC.el("button", { type: "button", class: "btn btn-outline-secondary" }, topic.is_pinned ? "Desafixar" : "Fixar");
  hideBtn.addEventListener("click", () => act(topic.is_hidden ? "unhide" : "hide", hideBtn));
  lockBtn.addEventListener("click", () => act(topic.is_locked ? "unlock" : "lock", lockBtn));
  pinBtn.addEventListener("click", () => act(topic.is_pinned ? "unpin" : "pin", pinBtn));
  return LaaC.el("div", { class: "btn-group btn-group-sm", role: "group", "aria-label": "Ações de moderação" },
    hideBtn, lockBtn, pinBtn);
}

/* Uma linha da lista de tópicos: avatar + corpo + selo do tipo, navegando
   para a thread do tópico (/comunidade/topico/<id>/ — Task 6) ao ser clicada.
   A linha não pode ser um <a> porque carrega botões de moderação (hide/lock/
   pin) dentro dela — um <button> aninhado num <a> dispararia a navegação
   junto com a ação, então o clique nos botões para a propagação antes de
   chegar no onclick da linha (mesmo padrão de "tile clicável" do game-picker
   acima). */
function renderTopic(topic) {
  const row = LaaC.el("div", {
      class: "list-group-item list-group-item-action d-flex align-items-start gap-3 flex-wrap",
      style: "cursor:pointer",
      onclick: () => { window.location = `/comunidade/topico/${topic.id}/`; },
    },
    LaaC.el("div", {
      class: "rounded-circle bg-primary-subtle text-primary d-flex align-items-center justify-content-center flex-shrink-0 fw-semibold small",
      style: "width:38px;height:38px",
    }, LaaC.initials(topic.author)),
    LaaC.el("div", { class: "flex-grow-1", style: "min-width:200px" },
      LaaC.el("div", { class: "fw-semibold" }, topic.title),
      LaaC.el("div", { class: "text-secondary-emphasis small mt-1" }, "Iniciado por " + topic.author + " · " + topic.when),
      LaaC.el("div", { class: "small text-secondary-emphasis mt-1" }, topic.excerpt)),
    levelBadge(topic.type, topic.level));
  const modActions = topicModActions(topic);
  if (modActions) {
    modActions.addEventListener("click", (e) => e.stopPropagation());
    row.append(modActions);
  }
  return row;
}

const STAT_ROWS = [
  ["Total de membros", "members"],
  ["Tópicos criados", "topics"],
  ["Mensagens", "messages"],
  ["Jogos ativos", "active_games"],
];

function renderStatRow(stats, label, key) {
  return LaaC.el("li", { class: "list-group-item d-flex justify-content-between align-items-center px-0" },
    LaaC.el("span", { class: "text-secondary-emphasis small" }, label),
    LaaC.el("span", { class: "fw-semibold" }, String(stats[key])));
}

/* Compositor "Nova publicação" (card+form), criado/removido ao clicar no
   botão do cabeçalho — mesmo padrão de toggle do "Reportar um bug" em
   game_detail.js (buildReportForm / reportBtn). */
function buildComposer() {
  const title = LaaC.el("input", { type: "text", class: "form-control", id: "cm-composer-title", placeholder: "Título da publicação" });
  const type = LaaC.el("select", { class: "form-select", id: "cm-composer-type" });
  [["discussion", "Discussão"], ["bug", "Bug"], ["tip", "Dica"], ["news", "Notícia"]]
    .forEach(([v, l]) => type.append(LaaC.el("option", { value: v }, l)));
  const body = LaaC.el("textarea", { class: "form-control", id: "cm-composer-body", placeholder: "Escreva sua mensagem…", rows: "3" });
  const error = LaaC.el("div", { class: "text-danger small mt-2 d-none" });
  const submit = LaaC.el("button", { type: "submit", class: "btn btn-primary mt-2" }, "Publicar");

  const form = LaaC.el("form", { id: "cm-composer", class: "card card-body", novalidate: "" },
    LaaC.el("h2", { class: "h6 mb-3" }, "Nova publicação"),
    LaaC.el("div", { class: "mb-3" },
      LaaC.el("label", { class: "form-label small", for: "cm-composer-title" }, "Título"),
      title),
    LaaC.el("div", { class: "mb-3" },
      LaaC.el("label", { class: "form-label small", for: "cm-composer-type" }, "Tipo"),
      type),
    LaaC.el("div", {},
      LaaC.el("label", { class: "form-label small", for: "cm-composer-body" }, "Mensagem"),
      body),
    error, submit);

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!title.value.trim()) { title.focus(); return; }
    submit.disabled = true;
    try {
      await LaaC.sendJSON("/api/v1/topics/", {
        title: title.value.trim(), type: type.value,
        body: body.value.trim(), game: selectedSlug,
      });
      window.location.reload();
    } catch (e2) {
      error.textContent = "Não foi possível publicar. " + e2.message;
      error.classList.remove("d-none");
      submit.disabled = false;
    }
  });

  return form;
}

async function initCommunity() {
  const data = await LaaC.getJSON("/api/comunidade/" + location.search);
  const selected = data.selected;
  selectedSlug = selected ? selected.slug : null;

  // Seletor de jogos: "Todos os jogos" + um tile por jogo do catálogo
  const picker = document.getElementById("cm-games");
  picker.replaceChildren();
  picker.append(renderAllTile(data.stats.topics + " tópicos"));
  data.games.forEach((g) =>
    picker.append(renderGameTile(g, selected && g.slug === selected.slug)));

  // Cabeçalho da lista (jogo selecionado + total de tópicos)
  document.getElementById("cm-selected-name").textContent = selected ? selected.name : "—";
  document.getElementById("cm-selected-count").textContent =
    selected ? fmt(topicCount(selected)) + " tópicos" : "—";

  const filters = currentFilters();

  // "Filtrar por": cada link seta ?type= e destaca o filtro ativo.
  document.querySelectorAll("#cm-filters a").forEach((a) => {
    const type = a.dataset.type || "";
    a.classList.toggle("active", type === filters.type);
    a.addEventListener("click", (e) => {
      e.preventDefault();
      reload({ type });
    });
  });

  // "Ordenar por": alterna entre mais recentes e mais antigos.
  const sortToggle = document.getElementById("cm-sort-toggle");
  const sortLabel = document.getElementById("cm-sort-label");
  const ordering = filters.ordering || "-created_at";
  sortLabel.textContent = ordering === "created_at" ? "Mais antigos" : "Mais recentes";
  sortToggle.addEventListener("click", () =>
    reload({ ordering: ordering === "created_at" ? "-created_at" : "created_at" }));

  // Busca do cabeçalho: envia ?q= ao pressionar Enter.
  const searchInput = document.getElementById("cm-search");
  searchInput.value = filters.q;
  searchInput.addEventListener("keydown", (e) => {
    if (e.key !== "Enter") return;
    e.preventDefault();
    reload({ q: searchInput.value.trim() });
  });

  // Compositor "Nova publicação": alterna criar/remover ao clicar no botão.
  const composerHost = document.getElementById("cm-composer-host");
  const newBtn = document.getElementById("cm-new-topic-btn");
  newBtn.addEventListener("click", () => {
    const existing = document.getElementById("cm-composer");
    if (existing) { existing.remove(); return; }
    const composer = buildComposer();
    composerHost.append(composer);
    composer.querySelector("input").focus();
  });

  // Feed de tópicos
  const topics = document.getElementById("cm-topics");
  topics.replaceChildren();
  if (data.topics.length === 0) {
    topics.append(LaaC.el("div", { class: "list-group-item text-secondary-emphasis small py-2" },
      "Ainda não há tópicos para este jogo. Seja o primeiro a publicar!"));
  }
  data.topics.forEach((t) => topics.append(renderTopic(t)));

  // Estatísticas da comunidade
  const statsHost = document.getElementById("cm-stats");
  STAT_ROWS.forEach(([label, key]) => statsHost.append(renderStatRow(data.stats, label, key)));

  // Regras da comunidade: mostra um resumo; "Ver todas as regras" expande
  // para a lista completa (nada mais a buscar — data.rules já vem inteira).
  const RULES_PREVIEW = 2;
  const rulesHost = document.getElementById("cm-rules");
  const rulesToggle = document.getElementById("cm-rules-toggle");
  function renderRules(all) {
    rulesHost.replaceChildren();
    (all ? data.rules : data.rules.slice(0, RULES_PREVIEW)).forEach((rule) =>
      rulesHost.append(LaaC.el("li", { class: "mb-2" }, rule)));
  }
  renderRules(false);
  if (rulesToggle) {
    if (data.rules.length <= RULES_PREVIEW) {
      rulesToggle.style.display = "none";
    } else {
      rulesToggle.addEventListener("click", () => {
        renderRules(true);
        rulesToggle.style.display = "none";
      });
    }
  }
}

document.addEventListener("DOMContentLoaded", () => initCommunity().catch((e) => {
  if (e.message !== "unauthenticated") console.error(e);
}));
