/* Topic thread: header (author/when/badge) + body + replies + reply composer.
   The topic id comes from the template (data-topic) and feeds
   /api/topico/<id>/. Replying posts to /api/v1/replies/; moderation actions
   post to /api/v1/topics/<id>/<verb>/ (same actions the Comunidade feed
   already exposes to forum moderators). */

/* Bootstrap subtle-bg badge helper — same mapping as community.js/
   game_detail.js: every screen renders its own status color mapping now
   that the legacy LaaC.badge() has been removed as dead code. */
const LEVEL_BADGE_CLASS = {
  critical: "bg-critical-subtle",
  warning: "bg-warning-subtle-2",
  stable: "bg-stable-subtle",
  info: "bg-info-subtle",
};

function levelBadge(text, level) {
  return LaaC.el("span", { class: "badge rounded-pill " + (LEVEL_BADGE_CLASS[level] || "bg-secondary-subtle") }, text);
}

/* Hide/lock/pin buttons for forum moderators (LaaC.me.is_forum_moderator).
   Mirrors community.js's topicModActions; on success the thread reloads so
   the header badge and composer state reflect the new moderation state. */
function threadModActions(topic) {
  if (!(LaaC.me && LaaC.me.is_forum_moderator)) return null;
  const act = async (verb, btn) => {
    btn.disabled = true;
    try {
      await LaaC.sendJSON(`/api/v1/topics/${topic.id}/${verb}/`, {});
      LaaC.toast("Tópico atualizado.", "stable");
      window.location.reload();
    } catch (e) {
      LaaC.toast("Ação de moderação falhou.", "critical");
    } finally {
      btn.disabled = false;
    }
  };
  const hideBtn = LaaC.el("button", { type: "button", class: "btn btn-outline-secondary" }, topic.is_hidden ? "Reexibir" : "Ocultar");
  const lockBtn = LaaC.el("button", { type: "button", class: "btn btn-outline-secondary" }, topic.is_locked ? "Destravar" : "Travar");
  const pinBtn = LaaC.el("button", { type: "button", class: "btn btn-outline-secondary" }, topic.is_pinned ? "Desafixar" : "Fixar");
  hideBtn.addEventListener("click", () => act(topic.is_hidden ? "unhide" : "hide", hideBtn));
  lockBtn.addEventListener("click", () => act(topic.is_locked ? "unlock" : "lock", lockBtn));
  pinBtn.addEventListener("click", () => act(topic.is_pinned ? "unpin" : "pin", pinBtn));
  return LaaC.el("div", { class: "btn-group btn-group-sm", role: "group", "aria-label": "Ações de moderação" },
    hideBtn, lockBtn, pinBtn);
}

/* One reply row: avatar + author/when + body, same visual as game_detail's
   comment list. */
function renderReply(r) {
  return LaaC.el("div", { class: "list-group-item d-flex gap-3" },
    LaaC.el("div", {
      class: "rounded-circle bg-primary-subtle text-primary d-flex align-items-center justify-content-center flex-shrink-0 fw-semibold small",
      style: "width:32px;height:32px",
    }, LaaC.initials(r.author)),
    LaaC.el("div", {},
      LaaC.el("div", { class: "fw-semibold small" }, r.author + " · " + r.when),
      LaaC.el("div", { class: "small text-secondary-emphasis" }, r.body)));
}

async function initThread() {
  const topicId = document.getElementById("th-root").dataset.topic;
  const data = await LaaC.getJSON(`/api/topico/${topicId}/`);
  const topic = data.topic;

  // Cabeçalho: avatar, título, autor/quando, selo do tipo
  document.getElementById("th-avatar").textContent = LaaC.initials(topic.author);
  document.getElementById("th-title").textContent = topic.title;
  document.getElementById("th-meta").textContent = "Iniciado por " + topic.author + " · " + topic.when;
  document.getElementById("th-badge").append(levelBadge(topic.type_display, topic.level));
  document.getElementById("th-body").textContent = topic.body;

  // Ações de moderação (hide/lock/pin), visíveis só a moderadores do fórum
  const modActions = threadModActions(topic);
  if (modActions) document.getElementById("th-mod-actions").append(modActions);

  // Lista de respostas
  const repliesHost = document.getElementById("th-replies");
  if (data.replies.length === 0) {
    repliesHost.append(LaaC.el("div", { class: "list-group-item text-secondary-emphasis small" },
      "Ainda não há respostas. Seja o primeiro a responder!"));
  }
  data.replies.forEach((r) => repliesHost.append(renderReply(r)));

  // Compositor de resposta: desabilitado (com aviso) quando o tópico está
  // travado — o servidor também recusa a resposta, mas travamos a UI antes.
  const form = document.getElementById("th-reply-form");
  const input = document.getElementById("th-reply-input");
  const sendBtn = document.getElementById("th-send");
  const error = document.getElementById("th-error");
  if (topic.is_locked) {
    document.getElementById("th-locked-notice").classList.remove("d-none");
    input.disabled = true;
    sendBtn.disabled = true;
  } else {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const body = input.value.trim();
      if (!body) { input.focus(); return; }
      sendBtn.disabled = true;
      error.classList.add("d-none");
      try {
        await LaaC.sendJSON("/api/v1/replies/", { topic: topic.id, body });
        window.location.reload();
      } catch (e2) {
        error.textContent = "Não foi possível responder. " + e2.message;
        error.classList.remove("d-none");
        sendBtn.disabled = false;
      }
    });
  }
}

document.addEventListener("DOMContentLoaded", () => initThread().catch((e) => {
  if (e.message !== "unauthenticated") console.error(e);
}));
