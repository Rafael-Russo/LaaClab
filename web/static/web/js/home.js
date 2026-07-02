/* Início (home) screen: hero banner, recent-update cards, a trending-topics
   rail, favourite games and a sticky alert bar. All data comes from
   /api/home/ and is rendered here with the shared LaaC helpers. */

/* Vertical three-dots glyph shown at the end of each trending row. */
const TRENDING_GLYPH =
  '<svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">' +
  '<circle cx="12" cy="5" r="1.6"/><circle cx="12" cy="12" r="1.6"/><circle cx="12" cy="19" r="1.6"/></svg>';

async function initHome() {
  const data = await LaaC.getJSON("/api/home/");

  // --- Hero: primeiro banner (fundo em gradiente + título) ---
  const banner = data.banners[0];
  const hero = document.getElementById("home-hero");
  hero.style = LaaC.coverStyle(banner.cover);
  document.getElementById("hero-text").textContent = banner.title;

  // Um ponto por banner; o primeiro fica ativo.
  const dots = document.getElementById("hero-dots");
  data.banners.forEach((_, i) => dots.append(LaaC.el("span", i === 0 ? { class: "on" } : {})));

  // --- Grade de atualizações recentes ---
  const updates = document.getElementById("home-updates");
  data.updates.forEach((u) => {
    updates.append(LaaC.el("div", { class: "update-card" },
      // .cover com altura definida pela classe, mostrando as iniciais do jogo
      LaaC.el("div", { class: "cover", style: LaaC.coverStyle(u.cover) }, LaaC.initials(u.game)),
      LaaC.el("div", { class: "u-body" },
        LaaC.badge(u.tag, u.level),
        LaaC.el("div", { class: "u-title" }, u.title),
        LaaC.el("div", { class: "u-text" }, u.text),
        LaaC.el("div", { class: "u-when" }, u.when))));
  });

  // --- Trending: separador de grupo (.section-title) sempre que o rótulo muda ---
  const trending = document.getElementById("home-trending");
  let lastGroup = null;
  data.trending.forEach((t) => {
    if (t.group !== lastGroup) {
      trending.append(LaaC.el("div", { class: "section-title", style: "margin:12px 0 4px" }, t.group));
      lastGroup = t.group;
    }
    trending.append(LaaC.el("div", { class: "trending-item" },
      LaaC.el("div", { class: "t-txt" }, t.title),
      LaaC.el("span", { class: "dim", html: TRENDING_GLYPH })));
  });

  // --- Jogos favoritos: capa pequena + nome + ponto de status ---
  const favorites = document.getElementById("home-favorites");
  data.favorites.forEach((g) => {
    favorites.append(LaaC.el("div", { class: "fav-row" },
      LaaC.cover(g),
      LaaC.el("div", { class: "f-name" }, g.name),
      LaaC.el("span", { class: "dot " + g.status.level })));
  });

  // --- Barra de alerta fixa: 'ALERTA:' em destaque + mensagem ---
  const msg = document.getElementById("home-alert-msg");
  msg.append(LaaC.el("b", {}, "ALERTA:"), " " + data.alert.message);
}

document.addEventListener("DOMContentLoaded", () => initHome().catch((e) => {
  if (e.message !== "unauthenticated") console.error(e);
}));
