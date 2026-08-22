/* Biblioteca: tela com grid de todos os jogos na biblioteca do usuário.
   Cada cartão mostra capa, nome, score e um botão de favoritar que usa
   entrada_id (não id do jogo) para fazer PATCH em /api/v1/biblioteca/. */

async function iniciarBiblioteca() {
  const alvo = "lib-grid";

  // Mostrar carregando antes do pedido
  Api.carregando(alvo, "Carregando…");

  try {
    const dados = await Api.pedir("/api/v1/telas/biblioteca");

    // Mostrar total de jogos em chip "Todos"
    const filtros = document.getElementById("lib-filters");
    filtros.replaceChildren(Api.criar("span", { class: "chip" }, `Todos (${dados.total})`));

    // Se vazio, mostrar mensagem
    if (dados.jogos.length === 0) {
      Api.vazio(alvo, "Sua biblioteca está vazia.");
      return;
    }

    // Preencher grid com cartões de jogo
    const grid = document.getElementById(alvo);
    grid.replaceChildren();

    dados.jogos.forEach((jogo) => {
      // Botão de favoritar usando entrada_id
      const botaoFavoritar = Api.criar(
        "button",
        {
          class: "btn btn--outline",
          style: "margin-top:8px",
          onclick: async (evento) => {
            evento.preventDefault();
            evento.stopPropagation();
            try {
              await Api.pedir(`/api/v1/biblioteca/${jogo.entrada_id}`, {
                metodo: "PATCH",
                corpo: { favorito: !jogo.favorito },
              });
              // Recarregar página após favoritar
              location.reload();
            } catch (erro) {
              if (!Api.ehSessaoExpirada(erro)) {
                console.error(erro);
              }
            }
          },
        },
        jogo.favorito ? "★ Favorito" : "☆ Favoritar"
      );

      // Cartão de jogo com todos os elementos
      const cartao = Api.criar(
        "div",
        { class: "game-card" },
        Api.capa(jogo),
        Api.criar("div", { class: "g-name" }, jogo.nome),
        Api.criar(
          "div",
          { class: "row", style: "gap:8px" },
          Api.chipPontuacao(jogo.pontuacao, jogo.status),
          botaoFavoritar
        )
      );

      grid.append(cartao);
    });
  } catch (erro) {
    // Tratar erro
    if (!Api.ehSessaoExpirada(erro)) {
      Api.erro(alvo, "Não foi possível carregar a biblioteca.");
      console.error(erro);
    }
  }
}

Api.aoCarregar(iniciarBiblioteca);
