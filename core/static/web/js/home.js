/* Início (home) screen: highlights carousel, recent-update cards, a
   trending-topics rail, favourite games and a dismissible alert bar. All
   data comes from /api/home/ and is rendered here with the shared LaaC
   helpers. */

/* Bootstrap-styled severity badge (bg-*-subtle utilities from theme.css).
   Kept local to this screen: the shared LaaC.badge() helper still emits the
   legacy .badge--* classes for the screens P5a hasn't migrated yet. */
function levelBadge(label, level) {
  const cls = {
    critical: "bg-critical-subtle",
    warning: "bg-warning-subtle-2",
    stable: "bg-stable-subtle",
  }[level] || "bg-secondary-subtle";
  return LaaC.el("span", { class: "badge " + cls + " align-self-start" }, label);
}

function emptyState(text) {
  return LaaC.el("div", { class: "text-secondary-emphasis small py-2" }, text);
}

async function initHome() {
  const data = await LaaC.getJSON("/api/home/");

  // --- Carrossel de destaque: um slide por banner, com indicadores reais ---
  const hero = document.getElementById("home-hero");
  const heroInner = document.getElementById("hero-inner");
  const heroDots = document.getElementById("hero-dots");
  if (data.banners.length) {
    data.banners.forEach((banner, i) => {
      // Véu escuro sobre o gradiente da capa, para o título ficar legível
      // (mesmo tratamento do antigo .hero::after, movido para inline).
      const scrim = LaaC.el("div", {
        class: "position-absolute top-0 start-0 w-100 h-100",
        style: "background:linear-gradient(90deg, rgba(0,0,0,.75), transparent 70%)",
      });
      const caption = LaaC.el("div", { class: "position-relative h-100 d-flex align-items-center p-4 p-md-5" },
        LaaC.el("div", { class: "fs-3 fw-bold text-white", style: "max-width:46%" }, banner.title));
      heroInner.append(LaaC.el("div", {
        class: "carousel-item" + (i === 0 ? " active" : ""),
        style: LaaC.coverStyle(banner.cover) + "min-height:300px;",
      }, scrim, caption));

      const dotAttrs = {
        type: "button",
        "data-bs-target": "#home-hero",
        "data-bs-slide-to": String(i),
        "aria-label": "Destaque " + (i + 1),
      };
      if (i === 0) {
        dotAttrs.class = "active";
        dotAttrs["aria-current"] = "true";
      }
      heroDots.append(LaaC.el("button", dotAttrs));
    });
    if (window.bootstrap) new bootstrap.Carousel(hero, { interval: 6000 });
  } else {
    heroInner.append(LaaC.el("div", {
      class: "carousel-item active d-flex align-items-center justify-content-center text-secondary-emphasis",
      style: "min-height:200px",
    }, "Sem novidades em destaque."));
  }

  // --- Grade de atualizações recentes ---
  const updates = document.getElementById("home-updates");
  if (!data.updates.length) {
    updates.append(LaaC.el("div", { class: "col-12" }, emptyState("Nenhuma novidade recente.")));
  }
  data.updates.forEach((u) => {
    const body = [
      // Capa flush no topo do card (radius 0; o card cuida do arredondado
      // externo via overflow-hidden), iniciais do jogo por cima do gradiente.
      LaaC.el("div", { class: "cover", style: LaaC.coverStyle(u.cover) + "height:120px;border-radius:0;" }, LaaC.initials(u.game)),
      LaaC.el("div", { class: "card-body d-flex flex-column gap-2" },
        levelBadge(u.tag, u.level),
        LaaC.el("h3", { class: "h6 mb-0" }, u.title),
        LaaC.el("p", { class: "small text-secondary-emphasis mb-0" }, u.text),
        LaaC.el("div", { class: "small text-secondary-emphasis mt-auto" }, u.when)),
    ];
    const card = u.slug
      ? LaaC.el("a", { class: "card h-100 overflow-hidden text-decoration-none text-reset", style: "padding:0", href: "/jogo/" + u.slug + "/" }, ...body)
      : LaaC.el("div", { class: "card h-100 overflow-hidden", style: "padding:0" }, ...body);
    updates.append(LaaC.el("div", { class: "col" }, card));
  });

  // --- Trending: separador de grupo (heading) sempre que o rótulo muda ---
  const trending = document.getElementById("home-trending");
  if (!data.trending.length) {
    trending.append(emptyState("Nenhum assunto em alta."));
  }
  let lastGroup = null;
  data.trending.forEach((t) => {
    if (t.group !== lastGroup) {
      trending.append(LaaC.el("div", { class: "text-uppercase text-secondary-emphasis small fw-semibold mt-3 mb-1" }, t.group));
      lastGroup = t.group;
    }
    trending.append(LaaC.el("div", { class: "d-flex align-items-center justify-content-between gap-2 border-bottom py-2" },
      LaaC.el("span", { class: "fw-semibold small" }, t.title),
      LaaC.icon("more_vert")));
  });

  // --- Jogos favoritos: capa pequena + nome + ponto de status ---
  const favorites = document.getElementById("home-favorites");
  if (!data.favorites.length) {
    favorites.append(emptyState("Você ainda não tem jogos favoritos."));
  }
  data.favorites.forEach((g) => {
    const thumb = LaaC.cover(g, "flex-shrink-0");
    thumb.style.width = "34px";
    thumb.style.height = "34px";
    thumb.style.fontSize = "10px";
    const body = [
      thumb,
      LaaC.el("span", { class: "flex-grow-1 fw-semibold small text-truncate" }, g.name),
      LaaC.el("span", { class: "dot " + g.status.level }),
    ];
    favorites.append(g.slug
      ? LaaC.el("a", { class: "list-group-item list-group-item-action d-flex align-items-center gap-2 px-0", href: "/jogo/" + g.slug + "/" }, ...body)
      : LaaC.el("div", { class: "list-group-item d-flex align-items-center gap-2 px-0" }, ...body));
  });

  // --- Barra de alerta: 'ALERTA:' em destaque + mensagem ---
  const msg = document.getElementById("home-alert-msg");
  msg.append(LaaC.el("b", {}, "ALERTA:"), " " + data.alert.message);

  // Some se o usuário já dispensou esta mesma mensagem antes.
  const bar = document.getElementById("home-alert");
  if (data.alert.message && data.alert.message === localStorage.getItem("home_alert_dismissed")) {
    bar.classList.add("d-none");
  }

  document.getElementById("home-alert-btn").addEventListener("click", () => {
    window.location = "/alertas/";
  });

  document.getElementById("home-alert-dismiss").addEventListener("click", () => {
    bar.classList.add("d-none");
    localStorage.setItem("home_alert_dismissed", data.alert.message);
  });
}

document.addEventListener("DOMContentLoaded", () => initHome().catch((e) => {
  if (e.message !== "unauthenticated") console.error(e);
}));
