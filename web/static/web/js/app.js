/* Shared front-end helpers for every LaaCLab screen.
   Screens fetch their data from the /api/ endpoints and render it here. */

const LaaC = {
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
};

/* --- Shell bootstrap: sidebar user widget, avatar, theme toggle --------- */

async function bootShell() {
  // Theme
  const root = document.documentElement;
  if (localStorage.getItem("theme") === "light") root.classList.add("light");
  const themeBtn = document.getElementById("theme-toggle");
  if (themeBtn) {
    themeBtn.addEventListener("click", () => {
      root.classList.toggle("light");
      localStorage.setItem("theme", root.classList.contains("light") ? "light" : "dark");
    });
  }

  // Current user → sidebar level card + top-bar avatar
  try {
    const me = await LaaC.getJSON("/api/me/");
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
}

document.addEventListener("DOMContentLoaded", bootShell);
