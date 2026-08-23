/* Comportamento da casca: tema, item ativo, avatar e card de nível.

   O markup da casca é copiado em cada página; só o comportamento é
   compartilhado. O item ativo vem de <body data-tela="..."> e não do
   HTML, para que as cópias possam ser byte a byte idênticas. */

function aplicarTema() {
  const raiz = document.documentElement;
  if (localStorage.getItem("tema") === "claro") raiz.classList.add("light");
  const botao = document.getElementById("alternar-tema");
  if (!botao) return;
  botao.addEventListener("click", () => {
    raiz.classList.toggle("light");
    localStorage.setItem("tema", raiz.classList.contains("light") ? "claro" : "escuro");
  });
}

function marcarItemAtivo() {
  const tela = document.body.dataset.tela;
  if (!tela) return;
  const item = document.querySelector(`.nav-item[data-tela="${tela}"]`);
  if (item) item.classList.add("is-active");
}

async function preencherUsuario() {
  const eu = await Api.pedir("/api/v1/eu");
  const nome = document.getElementById("sb-nome");
  if (nome) nome.textContent = eu.apelido || eu.nome_usuario;
  const nivel = document.getElementById("sb-nivel");
  if (nivel) nivel.textContent = "Nível " + eu.nivel;
  const xp = document.getElementById("sb-xp");
  if (xp) xp.textContent = `${eu.xp} / ${eu.xp_max} XP`;
  const barra = document.getElementById("sb-xp-barra");
  if (barra && eu.xp_max) {
    barra.style.width = Math.round((eu.xp / eu.xp_max) * 100) + "%";
  }
  document.querySelectorAll(".js-avatar").forEach((a) => {
    a.textContent = Api.iniciaisDe(eu.nome_usuario);
    a.style.background = eu.cor_avatar;
  });
}

Api.aoCarregar(async () => {
  aplicarTema();
  marcarItemAtivo();
  // As telas de autenticação não têm sidebar e não têm token: pedir
  // /api/v1/eu daria 401, que redirecionaria o login para o login.
  if (document.body.dataset.casca === "auth") return;
  await preencherUsuario();
});
