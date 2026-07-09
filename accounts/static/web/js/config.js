/* Configuração screen: perfil editável (handle/bio/cor do avatar), atalhos de
   conta (allauth) e preferência de tema. Os dados vêm de /api/me/ e as
   alterações são salvas via PATCH /api/v1/me/. */

function markThemeActive(theme) {
  document.querySelectorAll("#cfg-theme button").forEach((b) => {
    b.classList.toggle("is-active", b.dataset.theme === theme);
  });
}

async function initConfig() {
  const me = await LaaC.getJSON("/api/me/");

  document.getElementById("cfg-handle").value = me.handle || "";
  document.getElementById("cfg-bio").value = me.bio || "";
  document.getElementById("cfg-avatar-color").value = me.avatar_color || "#6b7cff";
  markThemeActive(me.theme || "dark");

  document.getElementById("cfg-save-profile").addEventListener("click", async () => {
    try {
      await LaaC.sendJSON("/api/v1/me/", {
        handle: document.getElementById("cfg-handle").value,
        bio: document.getElementById("cfg-bio").value,
        avatar_color: document.getElementById("cfg-avatar-color").value,
      }, "PATCH");
      LaaC.toast("Perfil atualizado.", "stable");
    } catch (e) {
      LaaC.toast("Não foi possível salvar o perfil.", "critical");
    }
  });

  document.querySelectorAll("#cfg-theme button").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const theme = btn.dataset.theme;
      document.documentElement.dataset.theme = theme;
      localStorage.setItem("theme", theme);
      markThemeActive(theme);
      try {
        await LaaC.sendJSON("/api/v1/me/", { theme }, "PATCH");
        LaaC.toast("Tema atualizado.", "stable");
      } catch (e) {
        LaaC.toast("Não foi possível salvar o tema.", "critical");
      }
    });
  });
}

document.addEventListener("DOMContentLoaded", () => initConfig().catch((e) => {
  if (e.message !== "unauthenticated") console.error(e);
}));
