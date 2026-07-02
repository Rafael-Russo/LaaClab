/* Perfil screen: user header (avatar, nível, barra de XP e bio), estatísticas
   e a lista de atividade recente na trilha lateral. Os dados vêm de
   /api/perfil/ — nada é embutido no template. */

async function initProfile() {
  const data = await LaaC.getJSON("/api/perfil/");
  const u = data.user;

  // Cabeçalho: avatar com as iniciais e a cor do usuário
  const avatar = document.getElementById("pf-avatar");
  avatar.textContent = LaaC.initials(u.username);
  avatar.style.background = u.avatar_color;

  // Identidade: nome, nível, progresso de XP e bio entre aspas
  document.getElementById("pf-name").textContent = u.username;
  document.getElementById("pf-level").textContent = "Nível " + u.level;
  document.getElementById("pf-xp-bar").style.width = Math.round((u.xp / u.xp_max) * 100) + "%";
  document.getElementById("pf-xp").textContent = `${u.xp}/ ${u.xp_max} XP`;
  document.getElementById("pf-bio").textContent = `"${u.bio}"`;

  // Estatísticas: conquistas / amigos / dias ativo
  document.getElementById("pf-achievements").textContent = u.achievements;
  document.getElementById("pf-friends").textContent = u.friends;
  document.getElementById("pf-days").textContent = u.days_active;

  // Atividade recente (trilha): capa, jogo, duração e barra de progresso
  const activity = document.getElementById("pf-activity");
  data.recent_games.forEach((g) => {
    activity.append(LaaC.el("div", { class: "profile-recent" },
      LaaC.el("div", {
        class: "cover",
        style: LaaC.coverStyle(g.cover) + "width:64px;height:40px;font-size:9px",
      }, LaaC.initials(g.game)),
      LaaC.el("div", { style: "flex:1;min-width:0" },
        LaaC.el("div", { style: "font-weight:700;font-size:13px" }, g.game),
        LaaC.el("div", { class: "dim", style: "font-size:12px" }, g.duration),
        LaaC.el("div", { class: "row", style: "gap:8px;margin-top:6px" },
          LaaC.el("div", { class: "progress", style: "flex:1" },
            LaaC.el("span", { style: "width:" + g.percent + "%" })),
          LaaC.el("span", { style: "font-size:11px;font-weight:700" }, g.percent + "%")))));
  });
}

document.addEventListener("DOMContentLoaded", () => initProfile().catch((e) => {
  if (e.message !== "unauthenticated") console.error(e);
}));
