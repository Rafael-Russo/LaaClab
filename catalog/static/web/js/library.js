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

/* Bootstrap-styled score badge (bg-*-subtle utilities from theme.css), same
   convention as home.js's local levelBadge(): screens migrated under P5a
   render their own status color mapping instead of the legacy
   LaaC.scoreChip() (.score-chip.* classes). */
function scoreBadge(score, status) {
  const cls = {
    critical: "bg-critical-subtle",
    warning: "bg-warning-subtle-2",
    stable: "bg-stable-subtle",
  }[status.level] || "bg-secondary-subtle";
  return LaaC.el("span", { class: "badge rounded-pill " + cls }, String(score));
}

function renderCard(g) {
  const cover = LaaC.cover(g, "");
  cover.style.height = "140px";
  cover.style.borderRadius = "0";
  const icon = LaaC.icon(g.favorite ? "star" : "star_border");
  icon.style.fontSize = "16px";
  const fav = LaaC.el("button", {
    type: "button",
    class: "btn btn-sm mt-2 d-inline-flex align-items-center gap-1 " + (g.favorite ? "btn-warning" : "btn-outline-secondary"),
    onclick: async (e) => {
      e.preventDefault(); e.stopPropagation();
      await LaaC.sendJSON(`/api/v1/library/${g.entry_id}/`, { favorite: !g.favorite }, "PATCH");
      location.reload();
    },
  }, icon, g.favorite ? "Favorito" : "Favoritar");
  const body = LaaC.el("div", { class: "card-body d-flex flex-column gap-2" },
    LaaC.el("div", { class: "fw-semibold text-truncate" }, g.name),
    scoreBadge(g.score, g.status),
    fav);
  if (!g.slug) return LaaC.el("div", { class: "card h-100 overflow-hidden", style: "padding:0" }, cover, body);
  return LaaC.el("a", {
    class: "card h-100 overflow-hidden text-decoration-none text-reset", style: "padding:0",
    href: "/jogo/" + g.slug + "/",
  }, cover, body);
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
  grid.replaceChildren();
  const list = currentList();
  if (list.length === 0) {
    grid.append(LaaC.el("div", { class: "col-12 text-secondary-emphasis small py-4" }, "Nenhum jogo para este filtro."));
    return;
  }
  list.forEach((g) => grid.append(LaaC.el("div", { class: "col" }, renderCard(g))));
}

// Pill-shaped filter buttons: filled primary when active, muted outline
// otherwise — the Bootstrap equivalent of the legacy .chip-filter look.
function renderFilters() {
  const filters = document.getElementById("lib-filters");
  filters.replaceChildren();

  const all = LaaC.el("button", {
    type: "button",
    class: "btn btn-sm rounded-pill " + (activeGenre === null ? "btn-primary" : "btn-outline-secondary"),
    onclick: () => { activeGenre = null; renderFilters(); renderGrid(); },
  }, `Todos (${allGames.length})`);
  filters.append(all);

  // Genre chips built from the genres actually present in the loaded games.
  const genres = Array.from(new Set(allGames.flatMap((g) => g.genres || []))).sort();
  genres.forEach((name) => {
    const chip = LaaC.el("button", {
      type: "button",
      class: "btn btn-sm rounded-pill " + (activeGenre === name ? "btn-primary" : "btn-outline-secondary"),
      onclick: () => { activeGenre = activeGenre === name ? null : name; renderFilters(); renderGrid(); },
    }, name);
    filters.append(chip);
  });
}

function emptyLibrary() {
  document.getElementById("lib-toolbar").classList.add("d-none");
  const icon = LaaC.icon("sports_esports");
  icon.classList.add("d-block", "mb-3", "text-secondary-emphasis");
  icon.style.fontSize = "48px";
  document.getElementById("lib-grid").replaceChildren(LaaC.el("div", { class: "col-12 text-center py-5" },
    icon,
    LaaC.el("p", { class: "text-secondary-emphasis mb-3" }, "Sua biblioteca está vazia."),
    LaaC.el("a", { class: "btn btn-primary", href: "/explorar/" }, "Explorar jogos →")));
}

async function initLibrary() {
  const data = await LaaC.getJSON("/api/biblioteca/");
  allGames = data.games;

  if (allGames.length === 0) {
    emptyLibrary();
    return;
  }

  renderFilters();
  renderGrid();
  document.getElementById("lib-order").addEventListener("change", renderGrid);
}

document.addEventListener("DOMContentLoaded", () => initLibrary().catch((e) => {
  if (e.message !== "unauthenticated") console.error(e);
}));
