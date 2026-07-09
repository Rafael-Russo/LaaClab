/* Shared front-end helpers for every LaaCLab screen.
   Screens fetch their data from the /api/ endpoints and render it here. */

const LaaC = {
  /* Current user object from /api/me/, populated by bootShell. Null until
     the fetch resolves (or if it fails / is unauthenticated). */
  me: null,

  /* Fetch JSON from an endpoint. On 401 (session expired) send the user to
     the login page, preserving where they were. */
  async getJSON(url) {
    const res = await fetch(url, {
      headers: { "Accept": "application/json" },
      credentials: "same-origin",
    });
    if (res.status === 401) {
      window.location = "/accounts/login/?next=" + encodeURIComponent(location.pathname);
      throw new Error("unauthenticated");
    }
    if (!res.ok) throw new Error("HTTP " + res.status);
    return res.json();
  },

  /* CSRF token for API writes (set from the <meta> in base.html). */
  csrftoken() {
    const m = document.querySelector('meta[name="csrf-token"]');
    return m ? m.getAttribute("content") : "";
  },

  /* Send a write request (POST/PATCH/DELETE) to the REST API with CSRF.
     Returns the parsed JSON (or null for 204). Throws Error(detail) on failure. */
  async sendJSON(url, data, method = "POST") {
    const res = await fetch(url, {
      method,
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-CSRFToken": LaaC.csrftoken(),
      },
      credentials: "same-origin",
      body: method === "DELETE" ? undefined : JSON.stringify(data || {}),
    });
    if (res.status === 401) {
      window.location = "/accounts/login/?next=" + encodeURIComponent(location.pathname);
      throw new Error("unauthenticated");
    }
    if (!res.ok) {
      let detail = "HTTP " + res.status;
      try { detail = JSON.stringify(await res.json()); } catch (_) { /* keep default */ }
      throw new Error(detail);
    }
    return res.status === 204 ? null : res.json();
  },

  /* Create a DOM node: el("div", {class: "card"}, child, "text"). */
  el(tag, attrs = {}, ...children) {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (k === "class") node.className = v;
      else if (k === "html") node.innerHTML = v;
      else if (k.startsWith("on") && typeof v === "function") node.addEventListener(k.slice(2), v);
      else if (v !== null && v !== undefined) node.setAttribute(k, v);
    }
    for (const c of children.flat()) {
      if (c === null || c === undefined) continue;
      node.append(c.nodeType ? c : document.createTextNode(String(c)));
    }
    return node;
  },

  /* Gradient background string for a placeholder cover tile. */
  coverStyle(cover) {
    const [a, b] = cover || ["#2b2d47", "#12131f"];
    return `background: linear-gradient(135deg, ${a}, ${b});`;
  },

  /* Build a cover tile: real image when available, else gradient + initials. */
  cover(game, cls = "") {
    const src = game.cover_file || game.cover_image || "";
    const tile = LaaC.el("div", { class: "cover " + cls, style: LaaC.coverStyle(game.cover) },
      game.initials || game.name || "");
    if (src) {
      const img = LaaC.el("img", {
        src, alt: game.name || "", loading: "lazy",
        style: "width:100%;height:100%;object-fit:cover;position:absolute;inset:0",
        onerror: () => img.remove(),
      });
      tile.style.position = "relative";
      tile.style.overflow = "hidden";
      tile.append(img);
    }
    return tile;
  },

  /* Colored score chip from a status object {label, level}. */
  scoreChip(score, status) {
    return LaaC.el("span", { class: "score-chip " + status.level }, String(score));
  },

  badge(label, level) {
    return LaaC.el("span", { class: "badge badge--" + level }, label);
  },

  /* Simple avatar with the first letters of a name. */
  initials(name) {
    return (name || "?").trim().slice(0, 2).toUpperCase();
  },

  /* Notificação efêmera no canto da tela. */
  toast(message, kind = "info") {
    let host = document.querySelector(".toast-host");
    if (!host) {
      host = LaaC.el("div", { class: "toast-host", "aria-live": "polite", role: "status" });
      document.body.append(host);
    }
    const node = LaaC.el("div", { class: "toast toast--" + kind }, message);
    host.append(node);
    setTimeout(() => node.remove(), 4000);
  },
};

/* --- Shell bootstrap: sidebar user widget, avatar, theme toggle --------- */

async function bootShell() {
  // Theme
  const root = document.documentElement;
  const saved = localStorage.getItem("theme");
  if (saved) root.dataset.theme = saved;
  const themeBtn = document.getElementById("theme-toggle");
  if (themeBtn) {
    themeBtn.addEventListener("click", () => {
      root.dataset.theme = root.dataset.theme === "light" ? "dark" : "light";
      localStorage.setItem("theme", root.dataset.theme);
    });
  }

  // Current user → sidebar level card + top-bar avatar
  try {
    const me = await LaaC.getJSON("/api/me/");
    LaaC.me = me;
    const name = document.getElementById("sb-name");
    if (name) name.textContent = me.handle;
    const lvl = document.getElementById("sb-level");
    if (lvl) lvl.textContent = "Nível " + me.level;
    const xp = document.getElementById("sb-xp");
    if (xp) xp.textContent = `${me.xp} / ${me.xp_max} XP`;
    const bar = document.getElementById("sb-xp-bar");
    if (bar) bar.style.width = Math.round((me.xp / me.xp_max) * 100) + "%";
    document.querySelectorAll(".js-avatar").forEach((a) => {
      a.textContent = LaaC.initials(me.username);
      a.style.background = me.avatar_color;
    });
  } catch (e) {
    if (e.message !== "unauthenticated") console.error(e);
  }

  // Badge de notificações (contador vem do /api/me/)
  const badge = document.getElementById("notif-badge");
  const setBadge = (n) => {
    if (!badge) return;
    badge.textContent = n > 99 ? "99+" : String(n);
    badge.hidden = !n;
  };
  if (LaaC.me) setBadge(LaaC.me.unread_count || 0);

  const btn = document.getElementById("notif-btn");
  const panel = document.getElementById("notif-panel");
  const list = document.getElementById("notif-list");
  async function loadNotifs() {
    const data = await LaaC.getJSON("/api/notifications/");
    setBadge(data.unread_count);
    list.replaceChildren();
    if (!data.notifications.length) {
      list.append(LaaC.el("div", { class: "notif-empty" }, "Nenhuma notificação."));
      return;
    }
    for (const n of data.notifications) {
      const item = LaaC.el("a", {
        class: "notif-item" + (n.is_read ? "" : " is-unread"),
        href: n.url || "#",
      }, LaaC.el("div", { class: "n-text" }, n.text), LaaC.el("div", { class: "n-when" }, n.when));
      item.addEventListener("click", async (e) => {
        e.preventDefault();
        try { await LaaC.sendJSON(`/api/notifications/${n.id}/read/`, {}); } catch (_) { /* noop */ }
        if (n.url) {
          window.location = n.url;
        } else {
          try { await loadNotifs(); } catch (_) { /* noop */ }
        }
      });
      list.append(item);
    }
  }
  if (btn && panel) {
    btn.addEventListener("click", async (e) => {
      e.preventDefault();
      const opening = panel.hidden;
      panel.hidden = !opening;
      if (opening) { try { await loadNotifs(); } catch (_) { /* noop */ } }
    });
    document.addEventListener("click", (e) => {
      if (!panel.hidden && !panel.contains(e.target) && !btn.contains(e.target)) panel.hidden = true;
    });
    const readall = document.getElementById("notif-readall");
    if (readall) readall.addEventListener("click", async (e) => {
      e.stopPropagation();
      try { await LaaC.sendJSON("/api/notifications/read-all/", {}); await loadNotifs(); } catch (_) { /* noop */ }
    });
    // Polling leve do contador
    setInterval(async () => {
      try { const d = await LaaC.getJSON("/api/notifications/"); setBadge(d.unread_count); } catch (_) { /* noop */ }
    }, 60000);
  }

  // Global topbar search → Explore screen
  const search = document.querySelector(".topbar .search input");
  if (search) {
    search.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && search.value.trim()) {
        window.location = "/explorar/?q=" + encodeURIComponent(search.value.trim());
      }
    });
  }

  // Mobile nav drawer
  const toggle = document.getElementById("nav-toggle");
  const drawer = document.getElementById("mobile-drawer");
  const overlay = document.getElementById("drawer-overlay");
  if (toggle && drawer && overlay) {
    const open = (yes) => {
      drawer.classList.toggle("is-open", yes);
      overlay.hidden = !yes;
      drawer.setAttribute("aria-hidden", yes ? "false" : "true");
      toggle.setAttribute("aria-expanded", yes ? "true" : "false");
      document.body.style.overflow = yes ? "hidden" : "";
    };
    toggle.addEventListener("click", () => open(!drawer.classList.contains("is-open")));
    overlay.addEventListener("click", () => open(false));
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") open(false); });
  }
}

document.addEventListener("DOMContentLoaded", bootShell);
