/* Perfil screen: identidade (avatar, handle, bio), estatísticas REAIS de
   atividade (biblioteca, bugs reportados, confirmações, tópicos,
   comentários) e a lista de jogos recentes. Tudo vem de /api/perfil/ — nada
   é embutido no template, e não há mais nível/XP/conquistas fake (P5a). */

// Mapa estático: cada estatística real tem um rótulo, um glifo Material
// Symbols e uma cor "subtle" nativa do Bootstrap (sem hex hardcoded).
const STAT_META = [
  { key: "library", label: "Biblioteca", icon: "sports_esports", cls: "bg-primary-subtle text-primary" },
  { key: "bugs_reported", label: "Bugs reportados", icon: "bug_report", cls: "bg-danger-subtle text-danger" },
  { key: "confirmations", label: "Confirmações", icon: "thumb_up", cls: "bg-success-subtle text-success" },
  { key: "topics", label: "Tópicos", icon: "forum", cls: "bg-info-subtle text-info" },
  { key: "comments", label: "Comentários", icon: "chat_bubble", cls: "bg-warning-subtle text-warning" },
];

function renderStatCard(meta, value) {
  const icon = LaaC.icon(meta.icon);
  const iconBox = LaaC.el("div", {
    class: "rounded-3 d-flex align-items-center justify-content-center flex-shrink-0 " + meta.cls,
    style: "width:42px;height:42px",
  }, icon);
  return LaaC.el("div", { class: "col" },
    LaaC.el("div", { class: "card h-100" },
      LaaC.el("div", { class: "card-body d-flex align-items-center gap-3" },
        iconBox,
        LaaC.el("div", {},
          LaaC.el("div", { class: "fw-bold fs-5" }, String(value)),
          LaaC.el("div", { class: "text-secondary-emphasis small" }, meta.label)))));
}

// Uma linha de jogo recente: capa, nome e progresso (bug score do jogo).
function renderRecent(g) {
  const cover = LaaC.cover({ name: g.game, initials: LaaC.initials(g.game), cover: g.cover }, "flex-shrink-0");
  cover.style.width = "64px";
  cover.style.height = "40px";
  cover.style.fontSize = "11px";
  return LaaC.el("div", { class: "list-group-item d-flex align-items-center gap-3" },
    cover,
    LaaC.el("div", { class: "flex-grow-1", style: "min-width:0" },
      LaaC.el("div", { class: "fw-semibold text-truncate" }, g.game),
      LaaC.el("div", { class: "text-secondary-emphasis small" }, g.duration)),
    LaaC.el("div", { class: "d-flex align-items-center gap-2", style: "width:140px" },
      LaaC.el("div", { class: "progress flex-grow-1", style: "height:6px" },
        LaaC.el("div", { class: "progress-bar", style: "width:" + g.percent + "%" })),
      LaaC.el("span", { class: "small fw-semibold" }, g.percent + "%")));
}

async function initProfile() {
  const data = await LaaC.getJSON("/api/perfil/");
  const u = data.user;

  // Identidade: avatar com iniciais e cor do usuário, handle e bio.
  const avatar = document.getElementById("pf-avatar");
  avatar.textContent = LaaC.initials(u.handle);
  avatar.style.background = u.avatar_color;

  document.getElementById("pf-name").textContent = u.handle;
  document.getElementById("pf-bio").textContent = u.bio ? `"${u.bio}"` : "Sem bio ainda.";

  // Estatísticas reais de atividade.
  const stats = document.getElementById("pf-stats");
  stats.replaceChildren();
  STAT_META.forEach((meta) => stats.append(renderStatCard(meta, data.stats[meta.key] || 0)));

  // Jogos recentes.
  const recent = document.getElementById("pf-recent");
  recent.replaceChildren();
  if (data.recent_games.length === 0) {
    recent.append(LaaC.el("div", { class: "list-group-item text-secondary-emphasis small text-center py-4" }, "Nenhum jogo recente ainda."));
  } else {
    data.recent_games.forEach((g) => recent.append(renderRecent(g)));
  }
}

document.addEventListener("DOMContentLoaded", () => initProfile().catch((e) => {
  if (e.message !== "unauthenticated") console.error(e);
}));
