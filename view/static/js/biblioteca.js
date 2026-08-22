/* Biblioteca screen: a full-width grid with every game the user follows.
   Each card shows a cover, the game's current bug score, and a
   favourite-toggle button backed by /api/v1/library/. When the user has no
   games yet (e.g. a brand-new account), an empty state with a CTA to
   Explorar is shown instead of the grid. */

async function initLibrary() {
  const data = await LaaC.getJSON("/api/biblioteca/");

  // "Todos" chip carries the total number of games in the library.
  const filters = document.getElementById("lib-filters");
  filters.append(LaaC.el("span", { class: "chip" }, `Todos (${data.total})`));

  // Fill the grid with one card per game, or an empty-state CTA when the
  // library is empty.
  const grid = document.getElementById("lib-grid");
  grid.innerHTML = "";
  if (data.games.length === 0) {
    grid.innerHTML =
      "<div class='muted' style='padding:16px'>Sua biblioteca está vazia. " +
      "<a href='/explorar/' style='color:var(--brand)'>Explorar jogos →</a></div>";
    return;
  }
  data.games.forEach((g) => {
    const cover = LaaC.cover(g, "");
    cover.style.height = "150px";
    const fav = LaaC.el("button", {
      class: "btn btn--outline", style: "margin-top:8px",
      onclick: async () => {
        await LaaC.sendJSON(`/api/v1/library/${g.entry_id}/`, { favorite: !g.favorite }, "PATCH");
        location.reload();
      },
    }, g.favorite ? "★ Favorito" : "☆ Favoritar");
    grid.append(LaaC.el("div", { class: "game-card" }, cover,
      LaaC.el("div", { class: "g-name" }, g.name),
      LaaC.el("div", { class: "row", style: "gap:8px" },
        LaaC.scoreChip(g.score, g.status), fav)));
  });
}

document.addEventListener("DOMContentLoaded", () => initLibrary().catch((e) => {
  if (e.message !== "unauthenticated") console.error(e);
}));
