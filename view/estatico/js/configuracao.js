/* Tela de configuração: duas seções independentes.

   Perfil (apelido/bio/idade) via PUT /api/v1/usuarios/<id>. O id vem de
   GET /api/v1/eu, que também traz os valores atuais de apelido, bio e
   idade para preencher o formulário. O corpo do PUT sempre inclui
   "idade" — `null` quando o campo está vazio — para existir caminho de
   limpar um valor já salvo; ver comentário no handler de perfil.

   Senha (senha_atual/senha_nova) via POST /api/auth/senha. Esse endpoint
   revoga a sessão antiga DE PROPÓSITO (é o ponto do recurso: quem trocou
   a senha porque ela vazou não pode deixar o token velho vivo), e
   devolve token_acesso/token_renovacao novos. Sem Api.guardarSessao(...)
   aqui, a pessoa seria deslogada no exato instante em que se protegeu. */
Api.aoCarregar(async () => {
  const formPerfil = document.getElementById("form-perfil");
  const formSenha = document.getElementById("form-senha");

  const camposPerfil = {
    apelido: document.getElementById("apelido"),
    bio: document.getElementById("bio"),
    idade: document.getElementById("idade"),
  };
  const errosPerfil = {
    apelido: document.getElementById("erro-apelido"),
    bio: document.getElementById("erro-bio"),
    idade: document.getElementById("erro-idade"),
  };
  const erroGeralPerfil = document.getElementById("cf-erro-perfil");
  const sucessoPerfil = document.getElementById("cf-sucesso-perfil");

  const camposSenha = {
    senha_atual: document.getElementById("senha_atual"),
    senha_nova: document.getElementById("senha_nova"),
  };
  const errosSenha = {
    senha_atual: document.getElementById("erro-senha_atual"),
    senha_nova: document.getElementById("erro-senha_nova"),
  };
  const erroGeralSenha = document.getElementById("cf-erro-senha");
  const sucessoSenha = document.getElementById("cf-sucesso-senha");

  // Id de quem está logado. Só chega depois de GET /api/v1/eu responder;
  // até lá o formulário de perfil recusa o submit (guarda mais abaixo).
  let usuarioId = null;

  function limparErros(errosPorCampo, erroGeral, sucesso) {
    erroGeral.hidden = true;
    erroGeral.textContent = "";
    sucesso.hidden = true;
    sucesso.textContent = "";
    for (const alvo of Object.values(errosPorCampo)) alvo.textContent = "";
  }

  // 422 -> {"erros": {campo: [msg]}}: cada mensagem ao lado do campo
  // correspondente, como o registro faz. Jogar tudo num alerta genérico
  // desperdiça a informação que a API já deu (ex.: "Senha atual
  // incorreta." precisa aparecer junto de senha_atual, não solta no topo).
  function mostrarErros(erro, errosPorCampo, erroGeral) {
    if (erro.erros) {
      for (const [campo, mensagens] of Object.entries(erro.erros)) {
        const alvo = errosPorCampo[campo];
        if (alvo) {
          alvo.textContent = mensagens.join(" ");
        } else {
          erroGeral.textContent = mensagens.join(" ");
          erroGeral.hidden = false;
        }
      }
    } else {
      erroGeral.textContent = erro.message;
      erroGeral.hidden = false;
    }
  }

  // Os dois handlers de submit são registrados AQUI, ANTES de qualquer
  // `await`. A casca já chega pintada (é inline) e os campos já aceitam
  // foco e Enter antes do `await Api.pedir("/api/v1/eu")` mais abaixo
  // resolver — rede lenta ou cold start bastam para a pessoa confirmar
  // o formulário antes disso. Sem o listener já registrado nesse
  // instante, `preventDefault()` nunca roda e o submit cai no
  // comportamento padrão do HTML: os dois `<form>` desta página não
  // têm `action`, então o alvo é a própria URL. Nesta tela isso
  // significa senha atual e nova indo para a barra de endereço, o
  // histórico do navegador e o `Referer` das requisições seguintes —
  // por isso é a única tela que não pode inverter esta ordem.

  // --- Perfil ---------------------------------------------------------------
  formPerfil.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    limparErros(errosPerfil, erroGeralPerfil, sucessoPerfil);

    if (!usuarioId) {
      erroGeralPerfil.textContent = "Não foi possível identificar sua conta. Recarregue a página.";
      erroGeralPerfil.hidden = false;
      return;
    }

    const idadeBruta = camposPerfil.idade.value.trim();
    const corpo = {
      apelido: camposPerfil.apelido.value.trim(),
      bio: camposPerfil.bio.value.trim(),
      // Sempre presente: `null` quando o campo está vazio é o único
      // jeito de existir caminho para LIMPAR uma idade já salva. Sem
      // isso, deixar o campo em branco faz o PUT parcial preservar o
      // valor antigo no banco, e a resposta repõe esse valor antigo
      // no campo — parece que "não salvou vazio" quando na verdade
      // nunca foi pedido para limpar.
      idade: idadeBruta === "" ? null : Number(idadeBruta),
    };

    try {
      const atualizado = await Api.pedir(`/api/v1/usuarios/${usuarioId}`, {
        metodo: "PUT",
        corpo,
      });
      camposPerfil.apelido.value = atualizado.apelido || "";
      camposPerfil.bio.value = atualizado.bio || "";
      camposPerfil.idade.value =
        atualizado.idade === null || atualizado.idade === undefined
          ? ""
          : atualizado.idade;
      sucessoPerfil.textContent = "Perfil atualizado.";
      sucessoPerfil.hidden = false;
    } catch (e) {
      if (!(e instanceof ErroApi)) throw e;
      if (Api.ehSessaoExpirada(e)) return;
      mostrarErros(e, errosPerfil, erroGeralPerfil);
    }
  });

  // --- Senha ------------------------------------------------------------
  formSenha.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    limparErros(errosSenha, erroGeralSenha, sucessoSenha);

    try {
      const resposta = await Api.pedir("/api/auth/senha", {
        metodo: "POST",
        corpo: {
          senha_atual: camposSenha.senha_atual.value,
          senha_nova: camposSenha.senha_nova.value,
        },
      });

      // Ver comentário no topo do arquivo: guardar os tokens novos é o
      // que impede a troca de senha de deslogar quem acabou de trocá-la.
      Api.guardarSessao(resposta);

      formSenha.reset();
      sucessoSenha.textContent = "Senha alterada.";
      sucessoSenha.hidden = false;
    } catch (e) {
      if (!(e instanceof ErroApi)) throw e;
      if (Api.ehSessaoExpirada(e)) return;
      mostrarErros(e, errosSenha, erroGeralSenha);
    }
  });

  // --- Carrega o id e os valores atuais do perfil -------------------------
  Api.carregando("cf-status", "Carregando…");
  try {
    const eu = await Api.pedir("/api/v1/eu");
    usuarioId = eu.id;
    camposPerfil.apelido.value = eu.apelido || "";
    camposPerfil.bio.value = eu.bio || "";
    camposPerfil.idade.value = eu.idade === null || eu.idade === undefined ? "" : eu.idade;
    document.getElementById("cf-status").replaceChildren();
  } catch (erro) {
    if (Api.ehSessaoExpirada(erro)) return;
    Api.erro("cf-status", "Não foi possível carregar seus dados.");
    console.error(erro);
  }
});
