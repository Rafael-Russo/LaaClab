/* Tela de registro: cria a conta via /api/auth/registro.

   O registro devolve token_acesso e token_renovacao: quem se registra
   já entra, sem passar pelo login de novo. `autenticar: false` na
   chamada evita que um token velho e inválido no localStorage tome
   401 e redirecione o registro para o login antes mesmo de tentar. */
Api.aoCarregar(async () => {
  const form = document.getElementById("form-registro");
  const erroGeral = document.getElementById("erro-geral");
  const campos = {
    nome_usuario: document.getElementById("nome_usuario"),
    email: document.getElementById("email"),
    senha: document.getElementById("senha"),
  };
  const errosDeCampo = {
    nome_usuario: document.getElementById("erro-nome_usuario"),
    email: document.getElementById("erro-email"),
    senha: document.getElementById("erro-senha"),
  };

  function limparErros() {
    erroGeral.hidden = true;
    erroGeral.textContent = "";
    for (const alvo of Object.values(errosDeCampo)) alvo.textContent = "";
  }

  form.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    limparErros();

    try {
      const dados = await Api.pedir("/api/auth/registro", {
        metodo: "POST",
        corpo: {
          nome_usuario: campos.nome_usuario.value.trim(),
          email: campos.email.value.trim(),
          senha: campos.senha.value,
        },
        autenticar: false,
      });

      Api.guardarSessao(dados);

      // Honra o ?destino= que o api.js grava ao expulsar alguém por
      // sessão expirada; sem ele, volta para a página inicial.
      // Api.destinoSeguro recusa qualquer coisa que não seja um
      // caminho same-origin (redirecionamento aberto / javascript:).
      const destino = Api.destinoSeguro(new URLSearchParams(location.search).get("destino"));
      window.location = destino;
    } catch (e) {
      if (!(e instanceof ErroApi)) throw e;

      if (e.erros) {
        // 422 -> {"erros": {campo: [msg]}}: cada mensagem ao lado do
        // campo correspondente. Jogar tudo num alerta genérico
        // desperdiça a informação que a API já deu.
        for (const [campo, mensagens] of Object.entries(e.erros)) {
          const alvo = errosDeCampo[campo];
          if (alvo) {
            alvo.textContent = mensagens.join(" ");
          } else {
            erroGeral.textContent = mensagens.join(" ");
            erroGeral.hidden = false;
          }
        }
      } else {
        // 409 (usuário ou email já existe) ou qualquer outro erro sem
        // detalhe por campo: mensagem no topo do formulário.
        erroGeral.textContent = e.message;
        erroGeral.hidden = false;
      }
    }
  });
});
