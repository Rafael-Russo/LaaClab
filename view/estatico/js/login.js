/* Tela de login: autentica via /api/auth/login e guarda a sessão.

   `autenticar: false` na chamada é essencial: sem ele, um token velho
   e inválido sobrando no localStorage tomaria 401 e Api.pedir
   redirecionaria o login para o login (loop). */
Api.aoCarregar(async () => {
  const form = document.getElementById("form-login");
  const erroGeral = document.getElementById("erro-geral");
  const campoIdentificador = document.getElementById("identificador");
  const campoSenha = document.getElementById("senha");

  form.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    erroGeral.hidden = true;
    erroGeral.textContent = "";

    try {
      const dados = await Api.pedir("/api/auth/login", {
        metodo: "POST",
        corpo: {
          identificador: campoIdentificador.value.trim(),
          senha: campoSenha.value,
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
      // Login só devolve 401 (credencial inválida): não há erro de
      // campo aqui, só a mensagem no topo do formulário.
      erroGeral.textContent = e.message;
      erroGeral.hidden = false;
    }
  });
});
