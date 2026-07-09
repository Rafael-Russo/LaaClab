/* Detalhe do jogo: hero + abas (Sobre / Bugs & Alertas / Comunidade).
   O slug vem do template (data-slug) e alimenta o endpoint /api/jogo/<slug>/.
   Tab switching é feito pelo componente Tab do Bootstrap (data-bs-toggle="tab"
   nos botões do template) — nenhum JS de troca de aba é necessário aqui. */

/* Bootstrap subtle-bg utilities from theme.css, keyed by status level (same
   convention as bugometro.js/home.js). Falls back to Bootstrap's own
   `bg-info-subtle`/`bg-secondary-subtle` for levels theme.css doesn't define
   (topics can be "info"/"discussion"). */
const LEVEL_BADGE_CLASS = {
  critical: "bg-critical-subtle",
  warning: "bg-warning-subtle-2",
  stable: "bg-stable-subtle",
  info: "bg-info-subtle",
};

function levelBadge(text, level) {
  return LaaC.el("span", { class: "badge rounded-pill " + (LEVEL_BADGE_CLASS[level] || "bg-secondary-subtle") }, text);
}

/* Bug category choices offered by the report mini-form (mirrors Bug.Category). */
const BUG_CATEGORIES = [
  ["crash", "Crash"],
  ["graphics", "Gráficos"],
  ["performance", "Desempenho"],
  ["progression", "Progressão"],
  ["online", "Online"],
  ["other", "Outro"],
];

/* Severity icon per alert level (level comes from Alert.level, already in
   the /api/jogo/<slug>/ payload — no backend change needed). */
const ALERT_ICON = { critical: "error", warning: "warning", stable: "check_circle" };

function severityLevel(severity) {
  if (severity === "critical") return "critical";
  if (severity === "high" || severity === "medium") return "warning";
  return "stable";
}

/* Confirm/undo-confirm vote button, reflecting bug.user_vote_id state.
   Toggles POST/DELETE against /api/v1/bug-votes/ and re-renders via onChange. */
function voteButton(bug, onChange) {
  const voted = bug.user_vote_id != null;
  const icon = LaaC.icon("check_circle");
  icon.style.fontSize = "16px";
  const btn = LaaC.el("button", {
    type: "button",
    class: "btn btn-sm d-inline-flex align-items-center gap-1 " + (voted ? "btn-success" : "btn-outline-secondary"),
    "aria-pressed": voted ? "true" : "false",
  }, icon, `Confirmar (${bug.confirmations})`);
  btn.addEventListener("click", async () => {
    btn.disabled = true;
    try {
      if (bug.user_vote_id != null) {
        await LaaC.sendJSON(`/api/v1/bug-votes/${bug.user_vote_id}/`, null, "DELETE");
        bug.user_vote_id = null; bug.confirmations = Math.max(0, bug.confirmations - 1);
      } else {
        const v = await LaaC.sendJSON("/api/v1/bug-votes/", { bug: bug.id });
        bug.user_vote_id = v.id; bug.confirmations += 1;
      }
      onChange(bug);
    } catch (e) { LaaC.toast("Não foi possível registrar o voto.", "critical"); }
    finally { btn.disabled = false; }
  });
  return btn;
}

/* Confirm/reject/resolve buttons for games moderators (LaaC.me.is_games_moderator).
   Returns null (nothing rendered) for regular users or before LaaC.me resolves. */
function bugModActions(bug, reload) {
  if (!(LaaC.me && LaaC.me.is_games_moderator)) return null;
  const act = async (verb, btn) => {
    btn.disabled = true;
    try {
      await LaaC.sendJSON(`/api/v1/bugs/${bug.id}/${verb}/`, {});
      LaaC.toast("Bug atualizado.", "stable");
      await reload();
    } catch (e) {
      LaaC.toast("Ação de moderação falhou.", "critical");
    } finally {
      btn.disabled = false;
    }
  };
  const confirmBtn = LaaC.el("button", { type: "button", class: "btn btn-outline-success" }, "Confirmar");
  const rejectBtn = LaaC.el("button", { type: "button", class: "btn btn-outline-danger" }, "Rejeitar");
  const resolveBtn = LaaC.el("button", { type: "button", class: "btn btn-outline-primary" }, "Resolver");
  confirmBtn.addEventListener("click", () => act("confirm", confirmBtn));
  rejectBtn.addEventListener("click", () => act("reject", rejectBtn));
  resolveBtn.addEventListener("click", () => act("resolve", resolveBtn));
  return LaaC.el("div", { class: "btn-group btn-group-sm", role: "group", "aria-label": "Ações de moderação" },
    confirmBtn, rejectBtn, resolveBtn);
}

/* One row in the "bugs reportados" list. `reload` re-fetches the bugs list
   after a moderation action (only used when mod actions are rendered). */
function renderBugRow(b, reload) {
  const sub = LaaC.el("div", { class: "text-secondary-emphasis small" }, b.category + " · " + b.confirmations + " confirmações");
  const row = LaaC.el("div", { class: "d-flex align-items-center gap-3 flex-wrap border rounded-3 p-3" },
    LaaC.el("div", { class: "flex-grow-1" },
      LaaC.el("div", { class: "fw-semibold" }, b.title),
      sub),
    levelBadge(b.severity_display, severityLevel(b.severity)));
  let vote = voteButton(b, onVoteChange);
  function onVoteChange(updated) {
    sub.textContent = updated.category + " · " + updated.confirmations + " confirmações";
    const fresh = voteButton(updated, onVoteChange);
    vote.replaceWith(fresh);
    vote = fresh;
  }
  row.append(vote);
  const modActions = bugModActions(b, reload);
  if (modActions) row.append(modActions);
  return row;
}

/* Inline "Reportar um bug" composer: category select + textarea, posts to
   /api/v1/bug-reports/ and reloads the screen on success. */
function buildReportForm(gameSlug) {
  const category = LaaC.el("select", { class: "form-select", id: "gd-report-category" });
  BUG_CATEGORIES.forEach(([v, l]) => category.append(LaaC.el("option", { value: v }, l)));
  const text = LaaC.el("textarea", { class: "form-control", id: "gd-report-text", placeholder: "Descreva o bug…", rows: "3" });
  const error = LaaC.el("div", { class: "text-danger small mt-2 d-none" });
  const submit = LaaC.el("button", { type: "submit", class: "btn btn-primary mt-3" }, "Enviar");

  const form = LaaC.el("form", { id: "gd-report-form", class: "card card-body mt-3", novalidate: "" },
    LaaC.el("h3", { class: "h6 mb-3" }, "Descreva o problema"),
    LaaC.el("div", { class: "mb-3" },
      LaaC.el("label", { class: "form-label small", for: "gd-report-category" }, "Categoria"),
      category),
    LaaC.el("div", {},
      LaaC.el("label", { class: "form-label small", for: "gd-report-text" }, "Descrição"),
      text),
    error, submit);

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!text.value.trim()) return;
    submit.disabled = true; error.classList.add("d-none");
    try {
      await LaaC.sendJSON("/api/v1/bug-reports/", {
        game: gameSlug, text: text.value.trim(), category: category.value,
      });
      location.reload();
    } catch (e2) {
      error.textContent = "Não foi possível reportar. " + e2.message;
      error.classList.remove("d-none");
      submit.disabled = false;
    }
  });

  return form;
}

/* One row in the "alertas" list (aba Bugs & Alertas): icon by severity level
   + severity badge + text + relative time. */
function renderAlertRow(a) {
  const cls = LEVEL_BADGE_CLASS[a.level] || "bg-secondary-subtle";
  const icon = LaaC.icon(ALERT_ICON[a.level] || "info");
  icon.style.fontSize = "18px";
  return LaaC.el("div", { class: "list-group-item d-flex align-items-start gap-3" },
    LaaC.el("div", {
      class: "rounded-3 d-flex align-items-center justify-content-center flex-shrink-0 " + cls,
      style: "width:38px;height:38px",
    }, icon),
    LaaC.el("div", { class: "flex-grow-1" },
      levelBadge(a.severity_display, a.level),
      LaaC.el("div", { class: "small mt-1" }, a.text),
      LaaC.el("div", { class: "text-secondary-emphasis small mt-1" }, a.when)));
}

/* One row in the "tópicos" list (aba Comunidade): linka para a thread do
   tópico (rota /comunidade/topico/<id>/, do P4c). */
function renderTopicRow(t) {
  return LaaC.el("a", {
      class: "list-group-item list-group-item-action d-flex align-items-center justify-content-between gap-3 text-decoration-none text-reset",
      href: `/comunidade/topico/${t.id}/`,
    },
    LaaC.el("div", {},
      LaaC.el("div", { class: "fw-semibold" }, t.title),
      LaaC.el("div", { class: "text-secondary-emphasis small" }, t.when)),
    levelBadge(t.type_display, t.level));
}

/* Avatar-with-initials + author + text, used by the comments list. */
function renderComment(author, text) {
  return LaaC.el("div", { class: "d-flex gap-2" },
    LaaC.el("div", {
      class: "rounded-circle bg-primary-subtle text-primary d-flex align-items-center justify-content-center flex-shrink-0 fw-semibold small",
      style: "width:32px;height:32px",
    }, LaaC.initials(author)),
    LaaC.el("div", {},
      LaaC.el("div", { class: "fw-semibold small" }, author),
      LaaC.el("div", { class: "small text-secondary-emphasis" }, text)));
}

/* Compositor: publica um comentário via API e devolve o node criado ao
   chamador (para inserção no topo da lista). */
function buildCommentForm(slug, onCreated) {
  const text = LaaC.el("textarea", { class: "form-control", id: "gd-comment-text", placeholder: "Escreva um comentário…", rows: "2" });
  const error = LaaC.el("div", { class: "text-danger small mt-2 d-none" });
  const submit = LaaC.el("button", { type: "submit", class: "btn btn-primary w-100 mt-2" }, "Comentar");

  const form = LaaC.el("form", {}, text, error, submit);
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!text.value.trim()) return;
    submit.disabled = true; error.classList.add("d-none");
    try {
      const created = await LaaC.sendJSON("/api/v1/comments/", { game: slug, text: text.value.trim() });
      onCreated(created);
      text.value = "";
    } catch (e2) {
      error.textContent = "Não foi possível comentar. " + e2.message;
      error.classList.remove("d-none");
    } finally {
      submit.disabled = false;
    }
  });
  return form;
}

async function initGameDetail() {
  const slug = document.getElementById("gd-root").dataset.slug;
  const data = await LaaC.getJSON(`/api/jogo/${slug}/`);

  // Cabeçalho: nome do jogo + data da última atualização
  document.getElementById("gd-name").textContent = data.name;
  const upd = document.getElementById("gd-update");
  upd.append(document.createTextNode(data.last_update));

  // Hero com a capa (gradiente placeholder) e título em maiúsculas. `style =`
  // substitui o atributo inteiro, então o min-height precisa ir na mesma
  // atribuição (mesma convenção de home.js para os slides do carrossel).
  document.getElementById("gd-hero").style = LaaC.coverStyle(data.cover) + "min-height:220px;";
  document.getElementById("gd-title").textContent = data.name.toUpperCase();

  // ---- Aba Sobre: descrição, estatísticas, merch e comentários ----------

  document.getElementById("gd-about").textContent = data.about;

  // Coluna de estatísticas: votos, tempo pra zerar e conquistas
  const stats = document.getElementById("gd-stats");

  const upIcon = LaaC.icon("thumb_up"); upIcon.style.fontSize = "16px";
  const downIcon = LaaC.icon("thumb_down"); downIcon.style.fontSize = "16px";
  stats.append(LaaC.el("div", { class: "d-flex gap-3" },
    LaaC.el("span", { class: "d-inline-flex align-items-center gap-1 text-stable fw-semibold" }, upIcon, String(data.likes)),
    LaaC.el("span", { class: "d-inline-flex align-items-center gap-1 text-critical fw-semibold" }, downIcon, String(data.dislikes))));

  const ttb = data.time_to_beat;
  stats.append(LaaC.el("div", {},
    LaaC.el("div", { class: "text-uppercase text-secondary-emphasis small fw-semibold mb-1" }, "Tempo pra zerar"),
    LaaC.el("div", { class: "small text-secondary-emphasis" },
      LaaC.el("div", {}, "Médio: " + ttb.medio),
      LaaC.el("div", {}, "Speedrun: " + ttb.speedrun),
      LaaC.el("div", {}, "Platina: " + ttb.platina))));

  stats.append(LaaC.el("div", { class: "small" },
    LaaC.el("span", { class: "text-secondary-emphasis" }, "Conquistas: "),
    LaaC.el("span", { class: "fw-semibold" }, String(data.achievements))));

  // Card do merch
  document.getElementById("gd-merch").textContent = data.merch;

  // Compositor + lista de comentários (avatar com iniciais + autor + texto)
  const comments = document.getElementById("gd-comments");
  document.getElementById("gd-comment-form").append(
    buildCommentForm(slug, (created) => comments.prepend(renderComment(created.author, created.text))));

  if (data.comments.length === 0) {
    comments.append(LaaC.el("div", { class: "text-secondary-emphasis small" }, "Nenhum comentário ainda."));
  }
  data.comments.forEach((c) => comments.append(renderComment(c.author, c.text)));

  // ---- Aba Bugs & Alertas: bugs ativos (voto/moderação, do P4a) ---------

  const bugsHost = document.getElementById("gd-bugs");

  /* Re-render the bugs list from a fresh dataset (initial load or reload). */
  function renderBugsList(bugs) {
    bugsHost.replaceChildren();
    if (bugs.length === 0) {
      bugsHost.append(LaaC.el("div", { class: "text-secondary-emphasis small" }, "Nenhum bug ativo reportado."));
      return;
    }
    bugs.forEach((b) => bugsHost.append(renderBugRow(b, reloadBugs)));
  }

  /* Re-fetch /api/jogo/<slug>/ and re-render just the bugs list (used after
     a moderation action changes a bug's status). */
  async function reloadBugs() {
    const fresh = await LaaC.getJSON(`/api/jogo/${slug}/`);
    renderBugsList(fresh.bugs);
  }

  renderBugsList(data.bugs);

  // "Reportar um bug": alterna um mini-form inline abaixo da lista.
  const reportBtn = document.getElementById("gd-report-btn");
  reportBtn.addEventListener("click", () => {
    const existing = document.getElementById("gd-report-form");
    if (existing) { existing.remove(); return; }
    reportBtn.closest(".card-body").append(buildReportForm(slug));
  });

  // Alertas do jogo: uma linha por alerta, com ícone + badge por nível.
  const alertsList = document.getElementById("gd-alerts");
  if (data.alerts.length === 0) {
    alertsList.append(LaaC.el("div", { class: "list-group-item text-secondary-emphasis small" }, "Nenhum alerta para este jogo."));
  }
  data.alerts.forEach((a) => alertsList.append(renderAlertRow(a)));

  // ---- Aba Comunidade: tópicos do jogo + atalho para a comunidade -------

  // "Acesse a comunidade": abre a comunidade já filtrada pelo jogo atual.
  document.getElementById("gd-community-btn").addEventListener("click", () => {
    window.location = "/comunidade/?game=" + slug;
  });

  const topicsList = document.getElementById("gd-topics");
  if (data.topics.length === 0) {
    topicsList.append(LaaC.el("div", { class: "list-group-item text-secondary-emphasis small" }, "Ainda não há tópicos para este jogo."));
  }
  data.topics.forEach((t) => topicsList.append(renderTopicRow(t)));
}

document.addEventListener("DOMContentLoaded", () => initGameDetail().catch((e) => {
  if (e.message !== "unauthenticated") console.error(e);
}));
