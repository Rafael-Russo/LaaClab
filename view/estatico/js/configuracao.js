/* Tela de configuração: duas seções independentes.

   Perfil (apelido/bio/idade) via PUT /api/v1/usuarios/<id>. O id vem de
   GET /api/v1/eu, que também traz os valores atuais de apelido e bio
   para preencher o formulário — mas NÃO traz idade, então esse campo
   nasce em branco. Por isso o corpo do PUT só inclui "idade" quando a
   pessoa realmente digitou algo: mandar null todo salvamento de perfil
   apagaria uma idade já salva sem a pessoa ter tocado no campo.

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

  // --- Carrega o id e os valores atuais do perfil -------------------------
  Api.carregando("cf-status", "Carregando…");
  try {
    const eu = await Api.pedir("/api/v1/eu");
    usuarioId = eu.id;
    camposPerfil.apelido.value = eu.apelido || "";
    camposPerfil.bio.value = eu.bio || "";
    document.getElementById("cf-status").replaceChildren();
  } catch (erro) {
    if (Api.ehSessaoExpirada(erro)) return;
    Api.erro("cf-status", "Não foi possível carregar seus dados.");
    console.error(erro);
  }

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
    };
    if (idadeBruta !== "") corpo.idade = Number(idadeBruta);

    try {
      const atualizado = await Api.pedir(`/api/v1/usuarios/${usuarioId}`, {
        metodo: "PUT",
        corpo,
      });
      camposPerfil.apelido.value = atualizado.apelido || "";
      camposPerfil.bio.value = atualizado.bio || "";
      if (atualizado.idade !== null && atualizado.idade !== undefined) {
        camposPerfil.idade.value = atualizado.idade;
      }
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
});
