/* Comunidade screen: game picker + topic feed + right rail (filters,
   stats, rules). Data comes from /api/comunidade/ and is rendered here. */

/* Contagem de tópicos por jogo. Enquanto não há backend real, usamos os
   valores dos mockups para os jogos conhecidos e uma contagem sintética
   determinística (sem randomização) para os demais. */
const TOPIC_COUNTS = { cs2: 342, valorant: 287, warzone: 120 };

function topicCount(game) {
  if (TOPIC_COUNTS[game.slug] !== undefined) return TOPIC_COUNTS[game.slug];
  return 60 + ((game.name.length * 29 + game.score * 3) % 300);
}

/* "342" → "342", "1284" → "1.284" (formato pt-BR). */
function fmt(n) {
  return Number(n).toLocaleString("pt-BR");
}

/* Tile fixo "Todos os jogos" com um ícone de grade no lugar da capa. */
function renderAllTile(countLabel) {
  const cover = LaaC.el("div", {
    class: "cover",
    style: LaaC.coverStyle(["#2b2d47", "#12131f"]) + "height:64px",
    html: '<svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>',
  });
  return LaaC.el("div", { class: "game-tile" }, cover,
    LaaC.el("div", { class: "t-name" }, "Todos os jogos"),
    LaaC.el("div", { class: "t-count" }, countLabel));
}

/* Um tile por jogo do catálogo; marca o jogo selecionado como ativo. */
function renderGameTile(game, active) {
  const cover = LaaC.el("div", {
    class: "cover",
    style: LaaC.coverStyle(game.cover) + "height:64px",
  }, game.initials);
  return LaaC.el("div", { class: "game-tile" + (active ? " is-active" : "") }, cover,
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
      LaaC.el("div", { class: "t-meta" }, "Iniciado por " + topic.author + "    " + topic.when),
      LaaC.el("div", { class: "t-excerpt" }, topic.excerpt)),
    LaaC.badge(topic.type, level));
}

/* Linhas do cartão de estatísticas: rótulo → chave em stats. */
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

async function initCommunity() {
  const data = await LaaC.getJSON("/api/comunidade/");
  const selected = data.selected;

  // Seletor de jogos: "Todos os jogos" + um tile por jogo do catálogo
  const picker = document.getElementById("cm-games");
  picker.innerHTML = "";
  picker.append(renderAllTile(data.stats.topics + " tópicos"));
  data.games.forEach((g) =>
    picker.append(renderGameTile(g, g.slug === selected.slug)));

  // Cabeçalho da lista (jogo selecionado + total de tópicos)
  document.getElementById("cm-selected-name").textContent = selected.name;
  document.getElementById("cm-selected-count").textContent = fmt(topicCount(selected)) + " tópicos";

  // Feed de tópicos
  const topics = document.getElementById("cm-topics");
  topics.innerHTML = "";
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
