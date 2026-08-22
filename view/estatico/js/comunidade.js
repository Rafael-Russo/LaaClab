/* Comunidade: seletor de praça (jogo) + feed de tópicos + estatísticas e
   regras na rail. Dado vem de GET /api/v1/telas/comunidade, que aceita
   ?jogo=<slug> para trocar a praça selecionada — trocar de praça é uma
   navegação real (recarrega a página com a query nova), não SPA. */

const ALVO = "co-topicos";

/* "1284" -> "1.284" (formato pt-BR). As estatísticas chegam como
   inteiros crus da API: a formatação de milhar é responsabilidade do JS. */
function formatarMilhar(numero) {
  return Number(numero).toLocaleString("pt-BR");
}

function slugSelecionado() {
  return new URLSearchParams(location.search).get("jogo") || "";
}

function selecionarPraca(slug) {
  location.search = slug ? "?jogo=" + encodeURIComponent(slug) : "";
}

/* Cartão de praça: {id, slug, nome, iniciais, capa, total_topicos}. É uma
   forma DIFERENTE do cartão de jogo — não tem `pontuacao` nem `status` —
   então NUNCA passa pelo renderizador canônico de cartão de jogo do
   núcleo (aquele lê `status.rotulo` e quebraria a lista inteira).
   Api.capa() é segura aqui: só lê capa/iniciais/nome, que a praça tem. */
function cartaoDePraca(praca, ativa) {
  const capa = Api.capa(praca);
  capa.style.height = "64px";
  return Api.criar(
    "div",
    {
      class: "game-tile" + (ativa ? " is-active" : ""),
      style: "cursor:pointer",
      onclick: () => selecionarPraca(praca.slug),
    },
    capa,
    Api.criar("div", { class: "t-name" }, praca.nome),
    Api.criar("div", { class: "t-count" }, formatarMilhar(praca.total_topicos) + " tópicos")
  );
}

/* Uma linha do feed: avatar (iniciais do autor) + corpo + selo do tipo. */
function linhaDeTopico(topico) {
  return Api.criar(
    "div",
    { class: "topic" },
    Api.criar("div", { class: "avatar" }, Api.iniciaisDe(topico.autor)),
    Api.criar(
      "div",
      { class: "t-body" },
      Api.criar("div", { class: "t-title" }, topico.titulo),
      Api.criar("div", { class: "t-meta" }, "Iniciado por " + topico.autor + "   " + topico.quando),
      Api.criar("div", { class: "t-excerpt" }, topico.resumo)
    ),
    Api.badge(topico.tipo_rotulo, topico.nivel)
  );
}

const LINHAS_ESTATISTICA = [
  ["Total de membros", "membros"],
  ["Tópicos criados", "topicos"],
  ["Mensagens", "mensagens"],
  ["Jogos ativos", "jogos_ativos"],
];

function linhaDeEstatistica(estatisticas, rotulo, chave) {
  return Api.criar(
    "div",
    { class: "stat-row" },
    Api.criar("span", { class: "s-label" }, rotulo),
    Api.criar("span", { class: "s-value" }, formatarMilhar(estatisticas[chave]))
  );
}

/* Publica um tópico na praça selecionada. `jogo_id` é obrigatório em
   POST /api/v1/topicos desde a revisão final da API: tópico sem jogo era
   contado nas estatísticas e ficava invisível em toda praça. A tela já
   sabe qual praça está aberta (`selecionado.id`), então não há por que
   pedir esse dado de novo ao usuário. */
async function publicarTopico(selecionado) {
  const titulo = document.getElementById("co-titulo");
  const tipo = document.getElementById("co-tipo");
  const corpo = document.getElementById("co-corpo");
  const erro = document.getElementById("co-composer-erro");
  const botao = document.getElementById("co-publicar");

  erro.style.display = "none";
  if (!titulo.value.trim()) {
    titulo.focus();
    return;
  }

  botao.disabled = true;
  try {
    await Api.pedir("/api/v1/topicos", {
      metodo: "POST",
      corpo: {
        titulo: titulo.value.trim(),
        tipo: tipo.value,
        corpo: corpo.value.trim(),
        jogo_id: selecionado.id,
      },
    });
    location.reload();
  } catch (e) {
    if (Api.ehSessaoExpirada(e)) return;
    erro.textContent = e instanceof ErroApi ? e.message : "Não foi possível publicar.";
    erro.style.display = "block";
    botao.disabled = false;
  }
}

async function iniciarComunidade() {
  // Carregando antes do pedido
  Api.carregando(ALVO, "Carregando…");

  const slug = slugSelecionado();
  const caminho =
    "/api/v1/telas/comunidade" + (slug ? "?jogo=" + encodeURIComponent(slug) : "");

  let dados;
  try {
    dados = await Api.pedir(caminho);
  } catch (erro) {
    if (Api.ehSessaoExpirada(erro)) return;
    Api.erro(ALVO, "Não foi possível carregar a comunidade.");
    console.error(erro);
    return;
  }

  const selecionado = dados.selecionado;

  // Seletor de praças
  const pracas = document.getElementById("co-pracas");
  if (dados.jogos.length === 0) {
    Api.vazio("co-pracas", "Nenhum jogo cadastrado ainda.");
  } else {
    pracas.replaceChildren();
    dados.jogos.forEach((praca) =>
      pracas.append(cartaoDePraca(praca, Boolean(selecionado) && praca.slug === selecionado.slug))
    );
  }

  // Cabeçalho da lista: praça selecionada + total de tópicos
  document.getElementById("co-nome").textContent = selecionado ? selecionado.nome : "—";
  document.getElementById("co-contagem").textContent = selecionado
    ? formatarMilhar(selecionado.total_topicos) + " tópicos"
    : "—";

  // Composer: só faz sentido havendo uma praça para anexar o jogo_id
  const composer = document.getElementById("co-composer");
  const alternarComposer = document.getElementById("co-alternar-composer");
  if (!selecionado) {
    alternarComposer.style.display = "none";
  } else {
    alternarComposer.addEventListener("click", () => {
      composer.style.display = composer.style.display === "none" ? "" : "none";
      if (composer.style.display !== "none") document.getElementById("co-titulo").focus();
    });
    document.getElementById("co-publicar").addEventListener("click", () => publicarTopico(selecionado));
  }

  // Feed de tópicos: vazio quando a praça não tem nenhum
  if (dados.topicos.length === 0) {
    Api.vazio(ALVO, "Ainda não há tópicos por aqui. Seja o primeiro a publicar!");
  } else {
    const topicos = document.getElementById(ALVO);
    topicos.replaceChildren();
    dados.topicos.forEach((topico) => topicos.append(linhaDeTopico(topico)));
  }

  // Estatísticas da comunidade
  const stats = document.getElementById("co-stats");
  stats.replaceChildren();
  LINHAS_ESTATISTICA.forEach(([rotulo, chave]) =>
    stats.append(linhaDeEstatistica(dados.estatisticas, rotulo, chave))
  );

  // Regras da comunidade
  const regras = document.getElementById("co-regras");
  regras.replaceChildren();
  dados.regras.forEach((regra) =>
    regras.append(Api.criar("div", { class: "muted", style: "padding:6px 0;font-size:13px" }, regra))
  );
}

Api.aoCarregar(iniciarComunidade);
