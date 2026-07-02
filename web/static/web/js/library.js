/* Biblioteca screen: a full-width grid with every game the user follows.
   Each card is a placeholder cover (with the game name and, for favourites,
   a red star) plus the game's current bug score and stability status. */

/* Build one game card from a {slug,name,score,initials,cover,favorite,status}
   object exactly as returned by /api/biblioteca/. */
function renderGameCard(game) {
  // Cover tile — the game name sits inside it, like the mockup; a red star
  // is layered on top only when the game is a favourite.
  const cover = LaaC.el("div", { class: "cover", style: LaaC.coverStyle(game.cover) },
    game.favorite ? LaaC.el("span", { class: "fav" }, "★") : null,
    game.name);

  // Score chip, and the stability badge only when the game is stable.
  const scoreRow = LaaC.el("div", { class: "row" },
    LaaC.scoreChip(game.score, game.status),
    game.status.level === "stable" ? LaaC.badge(game.status.label, game.status.level) : null);

  return LaaC.el("div", { class: "game-card" },
    cover,
    LaaC.el("div", { class: "g-name" }, game.name),
    scoreRow);
}

async function initLibrary() {
  const data = await LaaC.getJSON("/api/biblioteca/");

  // "Todos" chip carries the total number of games in the library.
  const filters = document.getElementById("lib-filters");
  filters.append(LaaC.el("span", { class: "chip" }, `Todos (${data.total})`));

  // Fill the grid with one card per game.
  const grid = document.getElementById("lib-grid");
  grid.textContent = "";
  data.games.forEach((game) => grid.append(renderGameCard(game)));
}

document.addEventListener("DOMContentLoaded", () => initLibrary().catch((e) => {
  if (e.message !== "unauthenticated") console.error(e);
}));
