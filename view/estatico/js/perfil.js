/* Perfil: header com avatar, nível, XP e bio; estatísticas (conquistas, amigos,
   dias ativo); e atividade recente (jogos recentes na trilha lateral).
   Todos os dados vêm de /api/v1/telas/perfil — nada é embutido no template. */

async function iniciarPerfil() {
  const alvo = "pf-usuario";
  const alvoAtividade = "pf-activity";

  // Mostrar carregando antes do pedido. `pf-usuario` NÃO entra aqui:
  // ele é o container do cabeçalho inteiro, com pf-avatar/pf-name/
  // pf-level/... como filhos por id. Api.carregando() faz
  // replaceChildren() no alvo — chamado em "pf-usuario" ele apaga
  // esses filhos, e o caminho feliz que faz
  // document.getElementById("pf-avatar") logo abaixo pega null e
  // lança TypeError, caindo sempre no catch (bug real, confirmado por
  // execução: /perfil nunca mostrava dado nenhum, só o estado de
  // erro). O HTML já nasce com os placeholders "—" / "Nível —", que
  // fazem o papel do carregando aqui.
  Api.carregando(alvoAtividade, "Carregando…");

  try {
    const dados = await Api.pedir("/api/v1/telas/perfil");
    const u = dados.usuario;

    // --- Cabeçalho: avatar com as iniciais e a cor do usuário ---
    const avatar = document.getElementById("pf-avatar");
    avatar.textContent = Api.iniciaisDe(u.nome_usuario);
    avatar.style.background = u.cor_avatar;

    // --- Identidade: nome, nível, progresso de XP e bio ---
    document.getElementById("pf-name").textContent = u.nome_usuario;
    document.getElementById("pf-level").textContent = "Nível " + u.nivel;
    const porcentagemXp = Math.round((u.xp / u.xp_max) * 100);
    document.getElementById("pf-xp-bar").style.width = porcentagemXp + "%";
    document.getElementById("pf-xp").textContent = `${u.xp} / ${u.xp_max} XP`;
    document.getElementById("pf-bio").textContent = `"${u.bio}"`;

    // --- Estatísticas: conquistas / amigos / dias ativo ---
    document.getElementById("pf-achievements").textContent = u.conquistas;
    document.getElementById("pf-friends").textContent = u.amigos;
    document.getElementById("pf-days").textContent = u.dias_ativo;

    // --- Atividade recente (trilha): capa, jogo, duração e barra de progresso ---
    const activity = document.getElementById(alvoAtividade);
    if (dados.jogos_recentes.length === 0) {
      Api.vazio(alvoAtividade, "Nenhum jogo recente.");
    } else {
      activity.replaceChildren();
      dados.jogos_recentes.forEach((g) => {
        activity.append(
          Api.criar(
            "a",
            { class: "profile-recent", href: "/jogo/" + g.jogo_slug },
            Api.criar(
              "div",
              {
                class: "cover",
                style: `background: linear-gradient(135deg, ${g.capa[0]}, ${g.capa[1]});width:64px;height:40px;font-size:9px`,
              },
              Api.iniciaisDe(g.jogo)
            ),
            Api.criar(
              "div",
              { style: "flex:1;min-width:0" },
              Api.criar("div", { style: "font-weight:700;font-size:13px" }, g.jogo),
              Api.criar("div", { class: "dim", style: "font-size:12px" }, g.duracao),
              Api.criar(
                "div",
                { class: "row", style: "gap:8px;margin-top:6px" },
                Api.criar(
                  "div",
                  { class: "progress", style: "flex:1" },
                  Api.criar("span", { style: "width:" + g.porcentagem + "%" })
                ),
                Api.criar("span", { style: "font-size:11px;font-weight:700" }, g.porcentagem + "%")
              )
            )
          )
        );
      });
    }

  } catch (erro) {
    // Tratar erro
    if (!Api.ehSessaoExpirada(erro)) {
      Api.erro(alvo, "Não foi possível carregar o perfil.");
      Api.erro(alvoAtividade, "Não foi possível carregar a atividade recente.");
      console.error(erro);
    }
  }
}

Api.aoCarregar(iniciarPerfil);
