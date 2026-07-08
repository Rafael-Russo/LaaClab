/* Detalhe do jogo: hero + descrição + estatísticas + comentários.
   O slug vem do template (data-slug) e alimenta o endpoint /api/jogo/<slug>/. */

/* Bug category choices offered by the report mini-form (mirrors Bug.Category). */
const BUG_CATEGORIES = [
  ["crash", "Crash"],
  ["graphics", "Gráficos"],
  ["performance", "Desempenho"],
  ["progression", "Progressão"],
  ["online", "Online"],
  ["other", "Outro"],
];

function severityLevel(severity) {
  if (severity === "critical") return "critical";
  if (severity === "high" || severity === "medium") return "warning";
  return "stable";
}

/* Confirm/undo-confirm vote button, reflecting bug.user_vote_id state.
   Toggles POST/DELETE against /api/v1/bug-votes/ and re-renders via onChange. */
function voteButton(bug, onChange) {
  const voted = bug.user_vote_id != null;
  const btn = LaaC.el("button", {
    class: "btn btn--outline" + (voted ? " is-voted" : ""),
    "aria-pressed": voted ? "true" : "false",
  }, `✓ Confirmar (${bug.confirmations})`);
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

/* Compact variant of voteButton, sized for the tighter game-detail row. */
function compactVoteButton(bug, onChange) {
  const btn = voteButton(bug, onChange);
  btn.style.padding = "6px 10px";
  btn.style.fontSize = "12px";
  return btn;
}

/* Confirm/reject/resolve buttons for games moderators (LaaC.me.is_games_moderator).
   Returns null (nothing rendered) for regular users or before LaaC.me resolves. */
function bugModActions(bug, reload) {
  if (!(LaaC.me && LaaC.me.is_games_moderator)) return null;
  const act = async (verb) => {
    try { await LaaC.sendJSON(`/api/v1/bugs/${bug.id}/${verb}/`, {}); LaaC.toast("Bug atualizado.", "stable"); reload(); }
    catch (e) { LaaC.toast("Ação de moderação falhou.", "critical"); }
  };
  return LaaC.el("span", { class: "mod-actions" },
    LaaC.el("button", { class: "btn", onclick: () => act("confirm") }, "Confirmar"),
    LaaC.el("button", { class: "btn", onclick: () => act("reject") }, "Rejeitar"),
    LaaC.el("button", { class: "btn", onclick: () => act("resolve") }, "Resolver"),
  );
}

/* One row in the "bugs reportados" list. `reload` re-fetches the bugs list
   after a moderation action (only used when mod actions are rendered). */
function renderBugRow(b, reload) {
  const info = LaaC.el("div", { class: "row", style: "gap:8px" },
    LaaC.el("span", {}, b.title + " · " + b.category),
    LaaC.badge(b.severity_display, severityLevel(b.severity)));
  const row = LaaC.el("div", { class: "row between", style: "padding:6px 0;font-size:13px" }, info);
  let vote = compactVoteButton(b, onVoteChange);
  function onVoteChange(updated) {
    const fresh = compactVoteButton(updated, onVoteChange);
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
  const fieldStyle =
    "width:100%;background:var(--surface-2);border:1px solid var(--border);" +
    "border-radius:10px;padding:10px 12px;color:var(--text);font:inherit;margin-top:8px";

  const category = LaaC.el("select", { style: fieldStyle });
  BUG_CATEGORIES.forEach(([v, l]) => category.append(LaaC.el("option", { value: v }, l)));
  const text = LaaC.el("textarea", { placeholder: "Descreva o bug…", rows: "3", style: fieldStyle });
  const error = LaaC.el("div", { style: "color:var(--critical);font-size:12px;margin-top:6px;display:none" });

  const submit = LaaC.el("button", {
    class: "btn btn--primary", style: "margin-top:8px",
    onclick: async () => {
      if (!text.value.trim()) return;
      submit.disabled = true; error.style.display = "none";
      try {
        await LaaC.sendJSON("/api/v1/bug-reports/", {
          game: gameSlug, text: text.value.trim(), category: category.value,
        });
        location.reload();
      } catch (e) {
        error.textContent = "Não foi possível reportar. " + e.message;
        error.style.display = "block";
        submit.disabled = false;
      }
    },
  }, "Enviar");

  return LaaC.el("div", { id: "gd-report-form", style: "margin-top:10px" },
    category, text, error, submit);
}

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

  // Bugs ativos do jogo + botão para reportar um novo
  const bugsList = LaaC.el("div", { class: "mt" });

  /* Re-render the bugs list from a fresh dataset (initial load or reload). */
  function renderBugsList(bugs) {
    bugsList.innerHTML = "";
    if (bugs.length === 0) {
      bugsList.append(LaaC.el("div", { class: "muted", style: "font-size:13px" }, "Nenhum bug ativo reportado."));
    }
    bugs.forEach((b) => bugsList.append(renderBugRow(b, reloadBugs)));
  }

  /* Re-fetch /api/jogo/<slug>/ and re-render just the bugs list (used after
     a moderation action changes a bug's status). */
  async function reloadBugs() {
    const fresh = await LaaC.getJSON(`/api/jogo/${slug}/`);
    renderBugsList(fresh.bugs);
  }

  renderBugsList(data.bugs);

  const reportBtn = LaaC.el("button", {
    class: "btn btn--primary", style: "width:100%;justify-content:center;margin-top:12px",
    onclick: () => {
      const existing = document.getElementById("gd-report-form");
      if (existing) { existing.remove(); return; }
      bugsCard.append(buildReportForm(slug));
    },
  }, "🐞 Reportar um bug");

  const bugsCard = LaaC.el("div", { class: "card" },
    LaaC.el("div", { class: "section-title" }, "Bugs reportados"),
    bugsList, reportBtn);

  document.getElementById("gd-merch").closest(".card").insertAdjacentElement("afterend", bugsCard);

  // Lista de comentários (avatar com iniciais + autor + texto)
  const comments = document.getElementById("gd-comments");
  const renderComment = (author, text) =>
    LaaC.el("div", { class: "comment" },
      LaaC.el("div", { class: "avatar" }, LaaC.initials(author)),
      LaaC.el("div", {},
        LaaC.el("div", { class: "c-author" }, author),
        LaaC.el("div", { class: "c-text" }, text)));

  // Compositor: publica um comentário via API e o insere no topo da lista.
  const fieldStyle =
    "width:100%;background:var(--surface-2);border:1px solid var(--border);" +
    "border-radius:10px;padding:10px 12px;color:var(--text);font:inherit";
  const cText = LaaC.el("textarea", { placeholder: "Escreva um comentário…", rows: "2", style: fieldStyle });
  const cErr = LaaC.el("div", { style: "color:var(--critical);font-size:12px;margin-top:6px;display:none" });
  const cBtn = LaaC.el("button", {
    class: "btn btn--primary", style: "margin-top:8px;width:100%;justify-content:center",
    onclick: async () => {
      if (!cText.value.trim()) return;
      cBtn.disabled = true; cErr.style.display = "none";
      try {
        const created = await LaaC.sendJSON("/api/v1/comments/", { game: slug, text: cText.value.trim() });
        comments.prepend(renderComment(created.author, created.text));
        cText.value = "";
      } catch (e) {
        cErr.textContent = "Não foi possível comentar. " + e.message;
        cErr.style.display = "block";
      } finally {
        cBtn.disabled = false;
      }
    },
  }, "Comentar");
  comments.parentNode.insertBefore(
    LaaC.el("div", { style: "margin-bottom:14px" }, cText, cBtn, cErr), comments);

  data.comments.forEach((c) => comments.append(renderComment(c.author, c.text)));
}

document.addEventListener("DOMContentLoaded", () => initGameDetail().catch((e) => {
  if (e.message !== "unauthenticated") console.error(e);
}));
