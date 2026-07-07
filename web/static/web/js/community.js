/* Comunidade screen: game picker + topic feed + right rail (filters,
   stats, rules). Data comes from /api/comunidade/. Selecting a game reloads
   with ?game=<slug>; "Nova publicação" creates a topic via the REST API. */

let selectedSlug = null;

/* Real topic count from the endpoint. */
function topicCount(game) {
  return typeof game.topic_count === "number" ? game.topic_count : 0;
}

/* "342" → "342", "1284" → "1.284" (formato pt-BR). */
function fmt(n) {
  return Number(n).toLocaleString("pt-BR");
}

function go(query) {
  window.location = location.pathname + query;
}

/* Tile fixo "Todos os jogos" com um ícone de grade no lugar da capa. */
function renderAllTile(countLabel) {
  const cover = LaaC.el("div", {
    class: "cover",
    style: LaaC.coverStyle(["#2b2d47", "#12131f"]) + "height:64px",
    html: '<svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>',
  });
  return LaaC.el("div", { class: "game-tile", style: "cursor:pointer",
      onclick: () => go("") }, cover,
    LaaC.el("div", { class: "t-name" }, "Todos os jogos"),
    LaaC.el("div", { class: "t-count" }, countLabel));
}

/* Um tile por jogo do catálogo; marca o jogo selecionado como ativo. */
function renderGameTile(game, active) {
  const cover = LaaC.el("div", {
    class: "cover",
    style: LaaC.coverStyle(game.cover) + "height:64px",
  }, game.initials);
  return LaaC.el("div", {
      class: "game-tile" + (active ? " is-active" : ""),
      style: "cursor:pointer",
      onclick: () => go("?game=" + encodeURIComponent(game.slug)),
    }, cover,
    LaaC.el("div", { class: "t-name" }, game.name),
    LaaC.el("div", { class: "t-count" }, fmt(topicCount(game)) + " tópicos"));
}

/* Uma linha da lista de tópicos: avatar + corpo + selo do tipo.
   'discussion' vira badge--discussion; os demais níveis usam badge--{level}. */
function renderTopic(topic) {
  const level = topic.level === "discussion" ? "discussion" : topic.level;
  return LaaC.el("div", { class: "topic" },
    LaaC.el("div", { class: "avatar" }, LaaC.initials(topic.author)),
    LaaC.el("div", { class: "t-body" },
      LaaC.el("div", { class: "t-title" }, topic.title),
      LaaC.el("div", { class: "t-meta" }, "Iniciado por " + topic.author + "    " + topic.when),
      LaaC.el("div", { class: "t-excerpt" }, topic.excerpt)),
    LaaC.badge(topic.type, level));
}

const STAT_ROWS = [
  ["total de membros", "members"],
  ["Tópicos criados", "topics"],
  ["mensagens", "messages"],
  ["Jogos ativos", "active_games"],
];

function renderStatRow(stats, label, key) {
  return LaaC.el("div", { class: "stat-row" },
    LaaC.el("span", { class: "s-label" }, label),
    LaaC.el("span", { class: "s-value" }, String(stats[key])));
}

/* Inline "Nova publicação" composer, toggled by the header button. */
function buildComposer() {
  const inputStyle =
    "width:100%;background:var(--surface-2);border:1px solid var(--border);" +
    "border-radius:10px;padding:10px 12px;color:var(--text);font:inherit;margin-top:8px";

  const title = LaaC.el("input", { type: "text", placeholder: "Título da publicação", style: inputStyle });
  const type = LaaC.el("select", { style: inputStyle });
  [["discussion", "Discussão"], ["bug", "Bug"], ["tip", "Dica"], ["news", "Notícia"]]
    .forEach(([v, l]) => type.append(LaaC.el("option", { value: v }, l)));
  const body = LaaC.el("textarea", { placeholder: "Escreva sua mensagem…", rows: "3", style: inputStyle });
  const error = LaaC.el("div", { class: "muted", style: "color:var(--critical);font-size:13px;margin-top:8px;display:none" });

  const submit = LaaC.el("button", { class: "btn btn--primary", style: "margin-top:10px",
    onclick: async () => {
      if (!title.value.trim()) { title.focus(); return; }
      submit.disabled = true;
      try {
        await LaaC.sendJSON("/api/v1/topics/", {
          title: title.value.trim(), type: type.value,
          body: body.value.trim(), game: selectedSlug,
        });
        window.location.reload();
      } catch (e) {
        error.textContent = "Não foi possível publicar. " + e.message;
        error.style.display = "block";
        submit.disabled = false;
      }
    } }, "Publicar");

  const card = LaaC.el("div", { class: "card", id: "cm-composer", style: "display:none" },
    LaaC.el("div", { style: "font-weight:800;font-size:16px" }, "Nova publicação"),
    title, type, body, error, submit);
  return card;
}

async function initCommunity() {
  const data = await LaaC.getJSON("/api/comunidade/");
  const selected = data.selected;
  selectedSlug = selected ? selected.slug : null;

  // Seletor de jogos: "Todos os jogos" + um tile por jogo do catálogo
  const picker = document.getElementById("cm-games");
  picker.innerHTML = "";
  picker.append(renderAllTile(data.stats.topics + " tópicos"));
  data.games.forEach((g) =>
    picker.append(renderGameTile(g, selected && g.slug === selected.slug)));

  // Cabeçalho da lista (jogo selecionado + total de tópicos)
  document.getElementById("cm-selected-name").textContent = selected ? selected.name : "—";
  document.getElementById("cm-selected-count").textContent =
    selected ? fmt(topicCount(selected)) + " tópicos" : "—";

  // Composer (inserted above the topic feed) + wire the header button
  const topics = document.getElementById("cm-topics");
  const composer = buildComposer();
  topics.parentNode.insertBefore(composer, topics);
  const newBtn = document.querySelector(".page-head .btn--primary");
  if (newBtn) {
    newBtn.addEventListener("click", () => {
      composer.style.display = composer.style.display === "none" ? "" : "none";
      if (composer.style.display !== "none") composer.querySelector("input").focus();
    });
  }

  // Feed de tópicos
  topics.innerHTML = "";
  if (data.topics.length === 0) {
    topics.append(LaaC.el("div", { class: "muted", style: "padding:8px 0" },
      "Ainda não há tópicos para este jogo. Seja o primeiro a publicar!"));
  }
  data.topics.forEach((t) => topics.append(renderTopic(t)));

  // Estatísticas da comunidade
  const statsHost = document.getElementById("cm-stats");
  STAT_ROWS.forEach(([label, key]) => statsHost.append(renderStatRow(data.stats, label, key)));

  // Regras da comunidade
  const rulesHost = document.getElementById("cm-rules");
  data.rules.forEach((rule) =>
    rulesHost.append(LaaC.el("div", { class: "muted", style: "padding:6px 0;font-size:13px" }, rule)));
}

document.addEventListener("DOMContentLoaded", () => initCommunity().catch((e) => {
  if (e.message !== "unauthenticated") console.error(e);
}));
