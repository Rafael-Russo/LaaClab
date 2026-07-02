/* Detalhe do jogo: hero + descrição + estatísticas + comentários.
   O slug vem do template (data-slug) e alimenta o endpoint /api/jogo/<slug>/. */

async function initGameDetail() {
  const slug = document.getElementById("gd-root").dataset.slug;
  const data = await LaaC.getJSON(`/api/jogo/${slug}/`);

  // Barra: nome do jogo ———— data da última atualização
  document.getElementById("gd-name").textContent = data.name;
  document.getElementById("gd-update").textContent = data.last_update;

  // Hero com a capa (gradiente placeholder) e título em maiúsculas
  document.getElementById("gd-hero").style = LaaC.coverStyle(data.cover);
  document.getElementById("gd-title").textContent = data.name.toUpperCase();

  // Parágrafo "Sobre"
  document.getElementById("gd-about").textContent = "SOBRE: " + data.about;

  // Coluna de estatísticas: votos, tempo pra zerar e conquistas
  const stats = document.getElementById("gd-stats");

  // Votos (curtidas / descurtidas)
  stats.append(LaaC.el("div", { class: "row", style: "gap:16px" },
    LaaC.el("span", { class: "vote up" }, "👍 " + data.likes),
    LaaC.el("span", { class: "vote down" }, "👎 " + data.dislikes)));

  // Tempo pra zerar
  const ttb = data.time_to_beat;
  stats.append(LaaC.el("div", {},
    LaaC.el("div", { class: "section-title", style: "margin-bottom:6px" }, "Tempo pra zerar"),
    LaaC.el("div", { class: "muted", style: "font-size:13px;line-height:1.7" },
      LaaC.el("div", {}, "MÉDIO: " + ttb.medio),
      LaaC.el("div", {}, "SPEED RUN: " + ttb.speedrun),
      LaaC.el("div", {}, "PLATINA: " + ttb.platina))));

  // Número de conquistas
  stats.append(LaaC.el("div", { class: "section-title" },
    "Número de conquistas : " + data.achievements));

  // Card do merch
  document.getElementById("gd-merch").textContent = data.merch;

  // Lista de comentários (avatar com iniciais + autor + texto)
  const comments = document.getElementById("gd-comments");
  data.comments.forEach((c) => {
    comments.append(LaaC.el("div", { class: "comment" },
      LaaC.el("div", { class: "avatar" }, LaaC.initials(c.author)),
      LaaC.el("div", {},
        LaaC.el("div", { class: "c-author" }, c.author),
        LaaC.el("div", { class: "c-text" }, c.text))));
  });
}

document.addEventListener("DOMContentLoaded", () => initGameDetail().catch((e) => {
  if (e.message !== "unauthenticated") console.error(e);
}));
