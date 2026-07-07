/* Explorar: catálogo paginado (busca/gênero/ordenação) + adicionar/favoritar. */

let page = 1;
let nextUrl = null;

function gameCard(g) {
  const cover = LaaC.cover(g, "");
  cover.style.height = "150px";
  const add = LaaC.el("button", {
    class: "btn btn--primary", style: "margin-top:8px;width:100%;justify-content:center",
    onclick: async () => {
      add.disabled = true;
      try {
        await LaaC.sendJSON("/api/v1/library/", { game: g.slug, favorite: false });
        add.textContent = "Na biblioteca ✓";
      } catch (e) { add.textContent = "Erro"; add.disabled = false; }
    },
  }, "Adicionar");
  return LaaC.el("div", { class: "game-card" }, cover,
    LaaC.el("div", { class: "g-name" }, g.name),
    LaaC.el("div", { class: "row", style: "gap:8px" },
      LaaC.scoreChip(g.score, g.status), add));
}

function buildQuery() {
  const p = new URLSearchParams();
  const s = document.getElementById("ex-search").value.trim();
  const genre = document.getElementById("ex-genre").value;
  const order = document.getElementById("ex-order").value;
  if (s) p.set("search", s);
  if (genre) p.set("genres__slug", genre);
  p.set("ordering", order);
  p.set("page", String(page));
  return p.toString();
}

async function load(reset) {
  const grid = document.getElementById("ex-grid");
  if (reset) { page = 1; grid.innerHTML = ""; }
  const data = await LaaC.getJSON("/api/v1/games/?" + buildQuery());
  if (reset && data.results.length === 0) {
    grid.innerHTML = "<div class='muted' style='padding:10px'>Nenhum jogo encontrado.</div>";
  }
  // /api/v1/games/ cards use REST field names; map to the shape LaaC.cover expects.
  data.results.forEach((g) => grid.append(gameCard({
    slug: g.slug, name: g.name, initials: g.initials, cover: g.cover,
    cover_file: g.cover_file, cover_image: g.cover_image,
    score: g.bug_score, status: g.status,
  })));
  nextUrl = data.next;
  document.getElementById("ex-more").style.display = nextUrl ? "" : "none";
}

async function initExplore() {
  // Genre filter options (follow pagination so no genres are dropped).
  const sel = document.getElementById("ex-genre");
  sel.append(LaaC.el("option", { value: "" }, "Todos os gêneros"));
  let gurl = "/api/v1/genres/?page=1";
  while (gurl) {
    const gdata = await LaaC.getJSON(gurl);
    (gdata.results || []).forEach((g) => sel.append(LaaC.el("option", { value: g.slug }, g.name)));
    gurl = gdata.next;
  }

  document.getElementById("ex-search").addEventListener("input", () => load(true));
  sel.addEventListener("change", () => load(true));
  document.getElementById("ex-order").addEventListener("change", () => load(true));
  document.getElementById("ex-more").addEventListener("click", () => { page += 1; load(false); });
  await load(true);
}

document.addEventListener("DOMContentLoaded", () => initExplore().catch((e) => {
  if (e.message !== "unauthenticated") console.error(e);
}));
