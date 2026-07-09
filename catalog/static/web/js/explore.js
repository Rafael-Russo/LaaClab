/* Explorar: catálogo paginado (busca/gênero/ordenação) + adicionar/favoritar. */

let page = 1;
let nextUrl = null;

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

function gameCard(g) {
  const cover = LaaC.cover(g, "");
  cover.style.height = "140px";
  cover.style.borderRadius = "0";
  const add = LaaC.el("button", {
    type: "button", class: "btn btn-primary btn-sm w-100 mt-2",
    onclick: async (e) => {
      e.preventDefault(); e.stopPropagation();
      add.disabled = true;
      try {
        await LaaC.sendJSON("/api/v1/library/", { game: g.slug, favorite: false });
        add.textContent = "Na biblioteca ✓";
        add.classList.replace("btn-primary", "btn-success");
      } catch (err) {
        add.textContent = "Erro";
        add.classList.replace("btn-primary", "btn-danger");
        add.disabled = false;
      }
    },
  }, "Adicionar");
  const body = LaaC.el("div", { class: "card-body d-flex flex-column gap-2" },
    LaaC.el("div", { class: "fw-semibold text-truncate" }, g.name),
    scoreBadge(g.score, g.status),
    add);
  if (!g.slug) return LaaC.el("div", { class: "card h-100 overflow-hidden", style: "padding:0" }, cover, body);
  return LaaC.el("a", {
    class: "card h-100 overflow-hidden text-decoration-none text-reset", style: "padding:0",
    href: "/jogo/" + g.slug + "/",
  }, cover, body);
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
  if (reset) { page = 1; grid.replaceChildren(); }
  const data = await LaaC.getJSON("/api/v1/games/?" + buildQuery());
  if (reset && data.results.length === 0) {
    grid.append(LaaC.el("div", { class: "col-12 text-secondary-emphasis small py-4" }, "Nenhum jogo encontrado."));
  }
  // /api/v1/games/ cards use REST field names; map to the shape LaaC.cover expects.
  data.results.forEach((g) => grid.append(LaaC.el("div", { class: "col" }, gameCard({
    slug: g.slug, name: g.name, initials: g.initials, cover: g.cover,
    cover_file: g.cover_file, cover_image: g.cover_image,
    score: g.bug_score, status: g.status,
  }))));
  nextUrl = data.next;
  document.getElementById("ex-more").classList.toggle("d-none", !nextUrl);
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

  // Pick up ?q= from the global topbar search (see core/static/web/js/app.js)
  // and use it as the initial search term.
  const q = new URLSearchParams(location.search).get("q");
  if (q) document.getElementById("ex-search").value = q;

  document.getElementById("ex-search").addEventListener("input", () => load(true));
  sel.addEventListener("change", () => load(true));
  document.getElementById("ex-order").addEventListener("change", () => load(true));
  document.getElementById("ex-more").addEventListener("click", () => { page += 1; load(false); });
  await load(true);
}

document.addEventListener("DOMContentLoaded", () => initExplore().catch((e) => {
  if (e.message !== "unauthenticated") console.error(e);
}));
