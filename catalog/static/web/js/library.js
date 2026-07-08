/* Biblioteca screen: a full-width grid with every game the user follows.
   Each card shows a cover, the game's current bug score, and a
   favourite-toggle button backed by /api/v1/library/. When the user has no
   games yet (e.g. a brand-new account), an empty state with a CTA to
   Explorar is shown instead of the grid.

   "Ordenar" and the genre chips both operate on the already-loaded list
   (no extra round-trip): sorting reorders it client-side and the genre
   chips are built from the genres present among the loaded games. */

let allGames = []; // Original order from the server (already -added_at, i.e. "Recentes").
let activeGenre = null; // null = "Todos".

function renderCard(g) {
  const cover = LaaC.cover(g, "");
  cover.style.height = "150px";
  const fav = LaaC.el("button", {
    class: "btn btn--outline", style: "margin-top:8px",
    onclick: async (e) => {
      e.preventDefault(); e.stopPropagation();
      await LaaC.sendJSON(`/api/v1/library/${g.entry_id}/`, { favorite: !g.favorite }, "PATCH");
      location.reload();
    },
  }, g.favorite ? "★ Favorito" : "☆ Favoritar");
  const body = [
    cover,
    LaaC.el("div", { class: "g-name" }, g.name),
    LaaC.el("div", { class: "row", style: "gap:8px" },
      LaaC.scoreChip(g.score, g.status), fav),
  ];
  return g.slug
    ? LaaC.el("a", { class: "game-card", href: "/jogo/" + g.slug + "/" }, ...body)
    : LaaC.el("div", { class: "game-card" }, ...body);
}

// Chip visual state: the default `.chip-filter .chip` look (brand fill) for
// the active chip; a muted outline (existing tokens, no new hex) otherwise.
function paintChip(chip, active) {
  chip.style.background = active ? "" : "var(--surface-2)";
  chip.style.color = active ? "" : "var(--text)";
}

function currentList() {
  const filtered = activeGenre
    ? allGames.filter((g) => (g.genres || []).includes(activeGenre))
    : allGames.slice();
  const order = document.getElementById("lib-order").value;
  if (order === "name") filtered.sort((a, b) => a.name.localeCompare(b.name));
  else if (order === "score") filtered.sort((a, b) => b.score - a.score);
  // "recent" keeps the server order (already -added_at) — nothing to do.
  return filtered;
}

function renderGrid() {
  const grid = document.getElementById("lib-grid");
  grid.innerHTML = "";
  const list = currentList();
  if (list.length === 0) {
    grid.innerHTML = "<div class='muted' style='padding:16px'>Nenhum jogo para este filtro.</div>";
    return;
  }
  list.forEach((g) => grid.append(renderCard(g)));
}

function renderFilters() {
  const filters = document.getElementById("lib-filters");
  filters.innerHTML = "";

  const all = LaaC.el("span", {
    class: "chip", style: "cursor:pointer",
    onclick: () => { activeGenre = null; renderFilters(); renderGrid(); },
  }, `Todos (${allGames.length})`);
  paintChip(all, activeGenre === null);
  filters.append(all);

  // Genre chips built from the genres actually present in the loaded games.
  const genres = Array.from(new Set(allGames.flatMap((g) => g.genres || []))).sort();
  genres.forEach((name) => {
    const chip = LaaC.el("span", {
      class: "chip", style: "cursor:pointer",
      onclick: () => { activeGenre = activeGenre === name ? null : name; renderFilters(); renderGrid(); },
    }, name);
    paintChip(chip, activeGenre === name);
    filters.append(chip);
  });
}

async function initLibrary() {
  const data = await LaaC.getJSON("/api/biblioteca/");
  allGames = data.games;

  if (allGames.length === 0) {
    document.getElementById("lib-filters").append(LaaC.el("span", { class: "chip" }, "Todos (0)"));
    document.getElementById("lib-grid").innerHTML =
      "<div class='muted' style='padding:16px'>Sua biblioteca está vazia. " +
      "<a href='/explorar/' style='color:var(--brand)'>Explorar jogos →</a></div>";
    return;
  }

  renderFilters();
  renderGrid();
  document.getElementById("lib-order").addEventListener("change", renderGrid);
}

document.addEventListener("DOMContentLoaded", () => initLibrary().catch((e) => {
  if (e.message !== "unauthenticated") console.error(e);
}));
