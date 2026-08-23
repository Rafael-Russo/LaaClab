/* Detalhe do jogo: barra (nome + última atualização) + hero + sobre +
   estatísticas + bugs reportados + comentários.

   O slug não chega mais por `data-slug` (o template Django injetava; o
   mecanismo morreu com ele). A rota `/jogo/<slug>` serve o MESMO
   `jogo.html` para qualquer slug, então quem sabe qual jogo é este é o
   último segmento de `location.pathname`. */

/* "1284" -> "1.284" (formato pt-BR). Unifica com a tela de comunidade:
   o servidor manda o inteiro cru, o cliente formata. */
function fmt(n) {
  return Number(n).toLocaleString("pt-BR");
}

/* severidade (baixa/media/alta/critica) -> nível de badge/score-chip. */
function nivelDeSeveridade(severidade) {
  if (severidade === "critica") return "critical";
  if (severidade === "alta" || severidade === "media") return "warning";
  return "stable";
}

const ESTILO_CAMPO =
  "width:100%;background:var(--surface-2);border:1px solid var(--border);" +
  "border-radius:10px;padding:10px 12px;color:var(--text);font:inherit";

/* Mini-formulário "Reportar um bug": só título é obrigatório além do
   jogo_id — categoria e severidade têm default no servidor. */
function construirFormularioDeBug(jogoId) {
  const titulo = Api.criar("input", {
    type: "text",
    placeholder: "Título do bug…",
    style: ESTILO_CAMPO + ";margin-top:8px",
  });
  const erro = Api.criar("div", {
    style: "color:var(--critical);font-size:12px;margin-top:6px;display:none",
  });

  const botao = Api.criar(
    "button",
    {
      class: "btn btn--primary",
      style: "width:100%;justify-content:center;margin-top:8px",
      onclick: async () => {
        if (!titulo.value.trim()) return;
        botao.disabled = true;
        erro.style.display = "none";
        try {
          await Api.pedir("/api/v1/relatos-bug", {
            metodo: "POST",
            corpo: { jogo_id: jogoId, titulo: titulo.value.trim() },
          });
          location.reload();
        } catch (e) {
          if (Api.ehSessaoExpirada(e)) return;
          // 422 -> {"erros": {campo: [msg]}}, não {"erro": msg}: usar
          // e.message aqui sempre caía no genérico "Não foi possível
          // completar a operação.", desperdiçando o campo que a API
          // já apontou (o bugômetro já faz isto certo).
          erro.textContent = e.erros
            ? Object.values(e.erros).flat().join(" ")
            : "Não foi possível reportar o bug. " + e.message;
          erro.style.display = "block";
          botao.disabled = false;
        }
      },
    },
    "🐞 Reportar um bug"
  );

  return Api.criar("div", { style: "margin-top:12px" }, titulo, botao, erro);
}

/* Compositor de comentário: publica em /api/v1/avaliacoes e recarrega a
   tela (a resposta do POST não traz o nome do autor, só usuario_id — o
   jeito simples e confiável de mostrar o comentário certo é recarregar,
   igual ao botão de favoritar da biblioteca). */
function construirComposerDeComentario(jogoId) {
  const texto = Api.criar("textarea", {
    placeholder: "Escreva um comentário…",
    rows: "2",
    style: ESTILO_CAMPO,
  });
  const erro = Api.criar("div", {
    style: "color:var(--critical);font-size:12px;margin-top:6px;display:none",
  });

  const botao = Api.criar(
    "button",
    {
      class: "btn btn--primary",
      style: "margin-top:8px;width:100%;justify-content:center",
      onclick: async () => {
        if (!texto.value.trim()) return;
        botao.disabled = true;
        erro.style.display = "none";
        try {
          await Api.pedir("/api/v1/avaliacoes", {
            metodo: "POST",
            corpo: { jogo_id: jogoId, comentario: texto.value.trim() },
          });
          location.reload();
        } catch (e) {
          if (Api.ehSessaoExpirada(e)) return;
          erro.textContent = "Não foi possível comentar. " + e.message;
          erro.style.display = "block";
          botao.disabled = false;
        }
      },
    },
    "Comentar"
  );

  return Api.criar("div", { style: "margin-bottom:14px" }, texto, botao, erro);
}

function montarStats(dados) {
  const ttz = dados.tempo_para_zerar;

  document.getElementById("jg-stats").replaceChildren(
    Api.criar(
      "div",
      {},
      Api.criar("div", { class: "section-title", style: "margin-bottom:6px" }, "Curtidas"),
      Api.criar(
        "div",
        { class: "row", style: "gap:16px" },
        Api.criar("span", { class: "vote up" }, "👍 " + fmt(dados.curtidas)),
        Api.criar("span", { class: "vote down" }, "👎 " + fmt(dados.descurtidas))
      )
    ),
    Api.criar(
      "div",
      {},
      Api.criar("div", { class: "section-title", style: "margin-bottom:6px" }, "Tempo pra zerar"),
      Api.criar(
        "div",
        { class: "stat-row" },
        Api.criar("span", { class: "s-label" }, "Médio"),
        Api.criar("span", { class: "s-value" }, ttz.medio)
      ),
      Api.criar(
        "div",
        { class: "stat-row" },
        Api.criar("span", { class: "s-label" }, "Speedrun"),
        Api.criar("span", { class: "s-value" }, ttz.speedrun)
      ),
      Api.criar(
        "div",
        { class: "stat-row" },
        Api.criar("span", { class: "s-label" }, "Platina"),
        Api.criar("span", { class: "s-value" }, ttz.platina)
      )
    ),
    Api.criar(
      "div",
      { class: "stat-row" },
      Api.criar("span", { class: "s-label" }, "Conquistas"),
      Api.criar("span", { class: "s-value" }, fmt(dados.conquistas))
    )
  );
}

function rotuloConfirmar(confirmacoes, jaConfirmei) {
  return jaConfirmei ? "✓ Confirmado" : `👍 Confirmar (${confirmacoes})`;
}

/* Botão "confirmar bug": POST /api/v1/votos-bug com {relato_id}. Nasce
   desabilitado e rotulado quando `bug.ja_confirmei` já é true (chega
   pronto do backend, por relato e por usuário logado).

   Um 409 aqui não é erro: a unique (relato_id, usuario_id) do backend
   significa que o voto já existe — o estado desejado já foi alcançado
   (ex.: duplo clique). Trata como sucesso idempotente — desabilita e
   rotula como confirmado, sem incrementar a contagem e sem pintar
   mensagem de erro, que aqui seria só ruído. */
function botaoConfirmarBug(bug) {
  const botao = Api.criar(
    "button",
    { class: "btn btn--outline", type: "button" },
    rotuloConfirmar(bug.confirmacoes, bug.ja_confirmei)
  );

  const marcarConfirmado = () => {
    botao.disabled = true;
    botao.style.opacity = "0.6";
    botao.style.cursor = "default";
    botao.textContent = rotuloConfirmar(bug.confirmacoes, true);
  };
  if (bug.ja_confirmei) marcarConfirmado();

  botao.addEventListener("click", async () => {
    botao.disabled = true;
    try {
      await Api.pedir("/api/v1/votos-bug", { metodo: "POST", corpo: { relato_id: bug.id } });
      bug.confirmacoes += 1;
      marcarConfirmado();
    } catch (e) {
      if (Api.ehSessaoExpirada(e)) return;
      if (e instanceof ErroApi && e.status === 409) {
        marcarConfirmado();
        return;
      }
      botao.disabled = false;
    }
  });

  return botao;
}

function montarBugs(dados) {
  if (dados.bugs.length === 0) {
    Api.vazio("jg-bugs", "Nenhum bug ativo reportado.");
  } else {
    document.getElementById("jg-bugs").replaceChildren(
      ...dados.bugs.map((bug) =>
        Api.criar(
          "div",
          { class: "row between", style: "padding:6px 0;font-size:13px" },
          Api.criar(
            "div",
            { class: "row", style: "gap:8px" },
            Api.criar("span", {}, bug.titulo + " · " + bug.categoria),
            Api.badge(bug.severidade_rotulo, nivelDeSeveridade(bug.severidade))
          ),
          botaoConfirmarBug(bug)
        )
      )
    );
  }

  document.getElementById("jg-relatar").replaceChildren(construirFormularioDeBug(dados.id));
}

function montarComentarios(dados) {
  document.getElementById("jg-comentar").replaceChildren(construirComposerDeComentario(dados.id));

  if (dados.comentarios.length === 0) {
    Api.vazio("jg-comentarios", "Nenhum comentário ainda.");
    return;
  }

  document.getElementById("jg-comentarios").replaceChildren(
    ...dados.comentarios.map((c) =>
      Api.criar(
        "div",
        { class: "comment" },
        Api.criar("div", { class: "avatar" }, Api.iniciaisDe(c.autor)),
        Api.criar(
          "div",
          {},
          Api.criar("div", { class: "c-author" }, c.autor),
          Api.criar("div", { class: "c-text" }, c.texto)
        )
      )
    )
  );
}

function montarTela(dados) {
  document.getElementById("jg-nome").textContent = dados.nome;
  // Texto livre no formato da Steam ("27 out. 2022") ou "—": exibe como
  // veio, sem tentar reformatar ou parsear como DD/MM/AAAA.
  document.getElementById("jg-atualizacao").textContent = dados.ultima_atualizacao;
  document.getElementById("jg-titulo").textContent = dados.nome.toUpperCase();

  const [cor1, cor2] = dados.capa;
  document.getElementById("jg-hero").style.background = `linear-gradient(135deg, ${cor1}, ${cor2})`;

  document.getElementById("jg-sobre").textContent = dados.sobre || "Sem descrição disponível.";
  document.getElementById("jg-merch").textContent = dados.merch;

  montarStats(dados);
  montarBugs(dados);
  montarComentarios(dados);
}

async function iniciarJogo() {
  const slug = location.pathname.split("/").pop();

  Api.carregando("jg-stats", "Carregando…");
  Api.carregando("jg-bugs", "Carregando…");
  Api.carregando("jg-comentarios", "Carregando…");

  const dados = await Api.pedir(`/api/v1/telas/jogo/${slug}`);
  montarTela(dados);
}

Api.aoCarregar(() => {
  iniciarJogo().catch((erro) => {
    if (erro instanceof ErroApi && erro.status === 404) {
      Api.erro("conteudo", "Jogo não encontrado.");
      return;
    }
    if (Api.ehSessaoExpirada(erro)) return;
    Api.erro("conteudo", "Não foi possível carregar o jogo.");
  });
});
