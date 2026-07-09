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

  /* Material Symbols icon helper: LaaC.icon("home") -> <span class="material-symbols-outlined">home</span> */
  icon(name) {
    return LaaC.el("span", { class: "material-symbols-outlined" }, name);
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
  // Theme (Bootstrap reads color mode off data-bs-theme on <html>)
  const root = document.documentElement;
  const saved = localStorage.getItem("theme");
  if (saved) root.dataset.bsTheme = saved;
  const themeBtn = document.getElementById("theme-toggle");
  const applyThemeIcon = () => {
    if (!themeBtn) return;
    const icon = themeBtn.querySelector(".material-symbols-outlined");
    if (icon) icon.textContent = root.dataset.bsTheme === "light" ? "light_mode" : "dark_mode";
  };
  applyThemeIcon();
  if (themeBtn) {
    themeBtn.addEventListener("click", () => {
      root.dataset.bsTheme = root.dataset.bsTheme === "light" ? "dark" : "light";
      localStorage.setItem("theme", root.dataset.bsTheme);
      applyThemeIcon();
      if (LaaC.me) {
        LaaC.sendJSON("/api/v1/me/", { theme: root.dataset.bsTheme }, "PATCH").catch(() => { /* noop */ });
      }
    });
  }

  // Current user → sidebar level card + top-bar avatar
  try {
    const me = await LaaC.getJSON("/api/me/");
    LaaC.me = me;
    // Server is the source of truth for a logged-in user's theme; keep the
    // client toggle above as an instant, unauthenticated-friendly fallback.
    root.dataset.bsTheme = me.theme || saved || "dark";
    applyThemeIcon();
    const name = document.getElementById("sb-name");
    if (name) name.textContent = me.handle;
    document.querySelectorAll(".js-avatar").forEach((a) => {
      a.textContent = LaaC.initials(me.username);
      a.style.background = me.avatar_color;
    });
  } catch (e) {
    if (e.message !== "unauthenticated") console.error(e);
  }

  // Notificações: dropdown Bootstrap (badge + lista). The dropdown itself
  // (show/hide, outside-click dismissal, aria-expanded) is handled by the
  // Bootstrap bundle via the button's data-bs-toggle="dropdown" attribute;
  // here we only populate its contents and keep the unread badge in sync.
  const badge = document.getElementById("notif-badge");
  const btn = document.getElementById("notif-btn");
  const setBadge = (n) => {
    if (!badge) return;
    badge.textContent = n > 99 ? "99+" : String(n);
    badge.hidden = !n;
    if (btn) btn.setAttribute("aria-label", n ? `Notificações (${n} não lidas)` : "Notificações");
  };
  if (LaaC.me) setBadge(LaaC.me.unread_count || 0);
  const list = document.getElementById("notif-list");
  async function loadNotifs() {
    const data = await LaaC.getJSON("/api/notifications/");
    setBadge(data.unread_count);
    list.replaceChildren();
    if (!data.notifications.length) {
      list.append(LaaC.el("div", { class: "list-group-item text-secondary-emphasis small" }, "Nenhuma notificação."));
      return;
    }
    for (const n of data.notifications) {
      const item = LaaC.el("a", {
        class: "list-group-item list-group-item-action" + (n.is_read ? "" : " fw-semibold"),
        href: n.url || "#",
      }, LaaC.el("div", { class: "small" }, n.text), LaaC.el("div", { class: "text-secondary-emphasis small" }, n.when));
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
  if (btn && list) {
    const dropdown = btn.closest(".dropdown");
    if (dropdown) {
      dropdown.addEventListener("show.bs.dropdown", async () => {
        try { await loadNotifs(); } catch (_) { /* noop */ }
      });
    }
    const readall = document.getElementById("notif-readall");
    if (readall) readall.addEventListener("click", async (e) => {
      e.stopPropagation();
      try { await LaaC.sendJSON("/api/notifications/read-all/", {}); await loadNotifs(); } catch (_) { /* noop */ }
    });
    // Polling leve do contador (nunca redireciona em 401: falha silenciosa).
    setInterval(async () => {
      try {
        const res = await fetch("/api/notifications/", {
          headers: { "Accept": "application/json" },
          credentials: "same-origin",
        });
        if (res.ok) { const d = await res.json(); setBadge(d.unread_count); }
      } catch (_) { /* silent */ }
    }, 60000);
  }

  // Global topbar search → Explore screen
  const search = document.getElementById("topbar-search");
  if (search) {
    search.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && search.value.trim()) {
        window.location = "/explorar/?q=" + encodeURIComponent(search.value.trim());
      }
    });
  }

  // Mobile nav drawer: handled entirely by the Bootstrap offcanvas component
  // (data-bs-toggle="offcanvas" / data-bs-dismiss="offcanvas" in base.html) —
  // no manual JS control needed here anymore (P4a's hand-rolled drawer removed).
}

document.addEventListener("DOMContentLoaded", bootShell);
