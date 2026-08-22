/* Alertas screen: lista de alertas dos jogos + resumo, favoritos e CTA.
   Os ícones são desenhados como SVG inline (estilo feather) — sem biblioteca. */

// Ícones escolhidos pelo campo `icone` de cada alerta (wifi / alert / check).
const ALERT_ICONS = {
  wifi: '<path d="M5 12.55a11 11 0 0 1 14.08 0"/><path d="M1.42 9a16 16 0 0 1 21.16 0"/><path d="M8.53 16.11a6 6 0 0 1 6.95 0"/><path d="M12 20h.01"/>',
  alert: '<path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z"/><path d="M12 9v4M12 17h.01"/>',
  check: '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><path d="m22 4-10 10.01L9 11"/>',
};

// O resumo não traz `icone`, então mapeamos a severidade para um ícone.
const LEVEL_ICON = { critical: "wifi", warning: "alert", stable: "check" };

// Monta um ícone SVG inline colorido pela severidade (via currentColor).
function glyphSvg(icon, size) {
  const body = ALERT_ICONS[icon] || ALERT_ICONS.alert;
  return '<svg viewBox="0 0 24 24" width="' + size + '" height="' + size +
    '" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
    body + '</svg>';
}

// Cada alerta vira uma .alert-row: capa, corpo (rótulo + jogo + texto) e status.
function renderAlert(alerta) {
  return Api.criar("div", { class: "alert-row" },
    // Capa do jogo com as iniciais
    Api.criar("div", { class: "cover", style: `background: linear-gradient(135deg, ${alerta.jogo?.capa?.[0] || '#2b2d47'}, ${alerta.jogo?.capa?.[1] || '#12131f'});` }, Api.iniciaisDe(alerta.jogo)),
    // Corpo: rótulo de severidade, nome do jogo e descrição.
    Api.criar("div", { class: "a-body" },
      Api.badge(alerta.severidade_rotulo, alerta.nivel),
      Api.criar("div", { class: "a-title" }, alerta.jogo),
      Api.criar("div", { class: "a-text" }, alerta.texto)),
    // Status: glifo circular colorido + botão de detalhes.
    Api.criar("div", { class: "a-status" },
      Api.criar("div", { class: "status-glyph " + alerta.nivel, html: glyphSvg(alerta.icone, 28) }),
      Api.criar("button", { class: "btn btn--outline", style: "padding:6px 14px;font-size:12px" }, "Ver detalhes")));
}

// Linha do resumo: glifo colorido, contagem em destaque e rótulo.
function renderSummaryRow(resumo) {
  return Api.criar("div", { class: "summary-row" },
    Api.criar("span", { style: "color:var(--" + resumo.nivel + ");display:grid;place-items:center",
      html: glyphSvg(LEVEL_ICON[resumo.nivel] || "alert", 22) }),
    Api.criar("span", { class: "n", style: "font-size:20px" }, String(resumo.contagem)),
    Api.criar("span", {}, resumo.rotulo));
}

// Linha de jogo favorito: usa o cartão canônico da API.
function renderFavorite(jogo) {
  return Api.cartaoDeJogo(jogo);
}

async function initAlerts() {
  const data = await Api.pedir("/api/v1/telas/alertas");

  // Lista principal de alertas.
  const list = document.getElementById("al-list");
  if (data.alertas.length === 0) {
    Api.vazio("al-list");
  } else {
    list.replaceChildren();
    data.alertas.forEach((a) => list.append(renderAlert(a)));
  }

  // Resumo de alertas (trilha lateral).
  const summary = document.getElementById("al-summary");
  if (data.resumo.length === 0) {
    Api.vazio("al-summary");
  } else {
    data.resumo.forEach((s) => summary.append(renderSummaryRow(s)));
  }

  // Jogos favoritos (trilha lateral).
  const favorites = document.getElementById("al-favorites");
  if (data.favoritos.length === 0) {
    Api.vazio("al-favorites");
  } else {
    data.favoritos.forEach((f) => favorites.append(renderFavorite(f)));
  }
}

Api.aoCarregar(() => {
  Api.carregando("al-list");
  initAlerts().catch((e) => {
    // Um 401 já redirecionou: pintar "Não foi possível carregar." por
    // cima é ruído durante uma navegação que já está em voo.
    if (Api.ehSessaoExpirada(e)) return;
    if (!(e instanceof ErroApi)) {
      // Erro que não é da API não pode ficar mudo no console...
      console.error(e);
    }
    // ...nem deixar a região presa em "Carregando…" para sempre: essa
    // é a mesma regra do item 4 (nenhuma região em carregamento
    // permanente), e vale tanto para ErroApi quanto para qualquer
    // outro erro.
    Api.erro("al-list");
  });
});
