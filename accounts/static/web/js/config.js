/* Configuração screen: perfil editável (handle/bio/cor do avatar), atalhos de
   conta (allauth) e preferência de tema. Os dados vêm de /api/me/ e as
   alterações são salvas via PATCH /api/v1/me/. O tema usa data-bs-theme
   (mesmo mecanismo do topbar toggle em app.js), não mais o antigo data-theme. */

function markThemeActive(theme) {
  document.querySelectorAll("#cfg-theme button").forEach((b) => {
    b.classList.toggle("active", b.dataset.theme === theme);
  });
}

/* Push opt-in + per-type toggles (P5b Task 4). Reads the current
   subscription state from the browser and the user's push_kinds from
   /api/me/, and drives POST /api/push/{subscribe,unsubscribe}/ +
   PATCH /api/v1/me/ {push_kinds}. */
async function initPush(me) {
  const toggle = document.getElementById("cfg-push-toggle");
  const note = document.getElementById("cfg-push-note");
  const kindsBox = document.getElementById("cfg-push-kinds");
  if (!toggle) return;

  const showNote = (text) => {
    note.textContent = text;
    note.hidden = false;
  };

  const supported = "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;
  if (!supported) {
    toggle.disabled = true;
    showNote("Notificações push não são suportadas neste navegador.");
    return;
  }

  let vapidKey = "";
  try {
    const res = await LaaC.getJSON("/api/push/vapid-key/");
    vapidKey = res.public_key || "";
  } catch (_) { /* treated as empty below */ }

  if (!vapidKey) {
    toggle.disabled = true;
    showNote("Notificações push estão desativadas no servidor.");
    return;
  }

  // Reflect whatever subscription state the browser already has.
  let sub = null;
  try {
    const reg = await navigator.serviceWorker.ready;
    sub = await reg.pushManager.getSubscription();
  } catch (_) { /* leave sub null */ }
  toggle.checked = !!sub;
  kindsBox.hidden = !sub;

  // Per-type checkboxes: LaaC.me.push_kinds empty/absent = every kind is on.
  const activeKinds = me.push_kinds || [];
  const kindBoxes = document.querySelectorAll(".cfg-push-kind");
  kindBoxes.forEach((cb) => {
    cb.checked = activeKinds.length === 0 || activeKinds.includes(cb.value);
    cb.addEventListener("change", async () => {
      const checked = [...kindBoxes].filter((c) => c.checked).map((c) => c.value);
      try {
        await LaaC.sendJSON("/api/v1/me/", { push_kinds: checked }, "PATCH");
        LaaC.toast("Preferências de notificação atualizadas.", "stable");
      } catch (_) {
        LaaC.toast("Não foi possível salvar a preferência.", "critical");
      }
    });
  });

  toggle.addEventListener("change", async () => {
    if (toggle.checked) {
      try {
        const permission = await Notification.requestPermission();
        if (permission !== "granted") {
          toggle.checked = false;
          LaaC.toast("Permissão de notificação negada.", "critical");
          return;
        }
        const reg = await navigator.serviceWorker.ready;
        const newSub = await reg.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: LaaC.urlBase64ToUint8Array(vapidKey),
        });
        await LaaC.sendJSON("/api/push/subscribe/", newSub.toJSON(), "POST");
        kindsBox.hidden = false;
        LaaC.toast("Notificações push ativadas.", "stable");
      } catch (_) {
        toggle.checked = false;
        LaaC.toast("Não foi possível ativar as notificações push.", "critical");
      }
    } else {
      try {
        const reg = await navigator.serviceWorker.ready;
        const current = await reg.pushManager.getSubscription();
        if (current) {
          const endpoint = current.endpoint;
          await current.unsubscribe();
          await LaaC.sendJSON("/api/push/unsubscribe/", { endpoint }, "POST");
        }
        kindsBox.hidden = true;
        LaaC.toast("Notificações push desativadas.", "stable");
      } catch (_) {
        LaaC.toast("Não foi possível desativar as notificações push.", "critical");
      }
    }
  });
}

async function initConfig() {
  const me = await LaaC.getJSON("/api/me/");

  document.getElementById("cfg-handle").value = me.handle || "";
  document.getElementById("cfg-bio").value = me.bio || "";
  document.getElementById("cfg-avatar-color").value = me.avatar_color || "#6b7cff";
  markThemeActive(me.theme || "dark");
  initPush(me).catch((e) => console.error(e));

  document.getElementById("cfg-profile-form").addEventListener("submit", async (e) => {
    e.preventDefault();
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
      document.documentElement.dataset.bsTheme = theme;
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
