/* Início (home) screen: hero banner, recent-update cards, trending topics
   rail, favourite games and a sticky alert bar. All data comes from
   /api/v1/telas/inicio and is rendered here with the shared Api helpers.

   IMPORTANTE: a chave `jogo` na resposta é o NOME de exibição;
   o slug é sempre `jogo_slug` em banners/atualizacoes. Os favoritos
   vêm como cartão já pronto e linkam pelo `slug` (via Api.cartaoDeJogo). */

/* Vertical three-dots glyph shown at the end of each trending row. */
const TRENDING_GLYPH =
  '<svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">' +
  '<circle cx="12" cy="5" r="1.6"/><circle cx="12" cy="12" r="1.6"/><circle cx="12" cy="19" r="1.6"/></svg>';

async function initHome() {
  const data = await Api.pedir("/api/v1/telas/inicio");

  // --- Hero: primeiro banner (fundo em gradiente + título) ---
  // `banners` vem `[]` em banco recém-criado (nenhum jogo ainda tem
  // metacritic o bastante) — sem esta guarda, `data.banners[0]` é
  // undefined e `banner.capa[0]` explode em TypeError, não ErroApi.
  if (data.banners.length === 0) {
    // Escreve em hero-text em vez de Api.vazio("home-hero", ...):
    // home-hero é ancestral de hero-text/hero-dots, lidos por id no
    // ramo com banner logo abaixo. Api.vazio() faz replaceChildren()
    // no alvo — chamado em home-hero apagaria esses filhos, a mesma
    // armadilha que quebrava pf-usuario (achado do item 4).
    document.getElementById("hero-text").textContent = "Nenhum destaque no momento.";
  } else {
    const banner = data.banners[0];
    const hero = document.getElementById("home-hero");
    hero.style.background = `linear-gradient(135deg, ${banner.capa[0]}, ${banner.capa[1]})`;
    document.getElementById("hero-text").textContent = banner.titulo;

    // Um ponto por banner; o primeiro fica ativo.
    const dots = document.getElementById("hero-dots");
    data.banners.forEach((_, i) => dots.append(Api.criar("span", i === 0 ? { class: "on" } : {})));
  }

  // --- Grade de atualizações recentes ---
  const updates = document.getElementById("home-updates");
  if (data.atualizacoes.length === 0) {
    Api.vazio("home-updates");
  } else {
    data.atualizacoes.forEach((u) => {
      updates.append(Api.criar("div", { class: "update-card" },
        // .cover com altura definida pela classe, mostrando as iniciais do jogo
        Api.criar("div", { class: "cover", style: `background: linear-gradient(135deg, ${u.capa[0]}, ${u.capa[1]});` }, Api.iniciaisDe(u.jogo)),
        Api.criar("div", { class: "u-body" },
          Api.badge(u.etiqueta, u.nivel),
          Api.criar("div", { class: "u-title" }, u.titulo),
          Api.criar("div", { class: "u-text" }, u.texto),
          Api.criar("div", { class: "u-when" }, u.quando))));
    });
  }

  // --- Trending: separador de grupo (.section-title) sempre que o rótulo muda ---
  const trending = document.getElementById("home-trending");
  if (data.assuntos.length === 0) {
    Api.vazio("home-trending");
  } else {
    let lastGroup = null;
    data.assuntos.forEach((t) => {
      if (t.grupo !== lastGroup) {
        trending.append(Api.criar("div", { class: "section-title", style: "margin:12px 0 4px" }, t.grupo));
        lastGroup = t.grupo;
      }
      trending.append(Api.criar("div", { class: "trending-item" },
        Api.criar("div", { class: "t-txt" }, t.titulo),
        Api.criar("span", { class: "dim", html: TRENDING_GLYPH })));
    });
  }

  // --- Jogos favoritos: usa cartão canônico da API ---
  const favorites = document.getElementById("home-favorites");
  if (data.favoritos.length === 0) {
    Api.vazio("home-favorites");
  } else {
    data.favoritos.forEach((g) => {
      favorites.append(Api.cartaoDeJogo(g));
    });
  }

  // --- Barra de alerta fixa: 'ALERTA:' em destaque + mensagem ---
  if (data.alerta && data.alerta.mensagem) {
    const msg = document.getElementById("home-alert-msg");
    msg.replaceChildren(
      Api.criar("b", {}, "ALERTA:"),
      " " + data.alerta.mensagem
    );
  }
}

Api.aoCarregar(() => {
  Api.carregando("home-updates");
  initHome().catch((e) => {
    // Um 401 já redirecionou: pintar "Não foi possível carregar." por
    // cima é ruído durante uma navegação que já está em voo.
    if (Api.ehSessaoExpirada(e)) return;
    if (!(e instanceof ErroApi)) {
      // Erro que não é da API (ex.: TypeError de acesso indevido a um
      // campo) não pode ficar mudo no console...
      console.error(e);
    }
    // ...nem deixar a região presa em "Carregando…" para sempre: essa
    // é a mesma regra do item 4 (nenhuma região em carregamento
    // permanente), e vale tanto para ErroApi quanto para qualquer
    // outro erro.
    Api.erro("home-updates");
  });
});
