/* Tela do bugômetro: painel do jogo (gauge + métricas), gráfico das
   últimas 24h, bugs reportados, atividade recente e ranking dos jogos
   mais instáveis. Convertida de view/templates/bugometro.html e
   view/static/js/bugometro.js (Django) para consumir
   GET /api/v1/telas/bugometro pelo Api central.

   Gauge e gráfico continuam desenhados como SVG inline puro — sem lib
   de gráfico, igual ao original. */

const SVGNS = "http://www.w3.org/2000/svg";

function svg(tag, atributos = {}) {
  const no = document.createElementNS(SVGNS, tag);
  for (const [chave, valor] of Object.entries(atributos)) no.setAttribute(chave, valor);
  return no;
}

/* Interpola verde → amarelo → vermelho conforme t (0..1). */
function corDoGauge(t) {
  const paradas = [
    [0.0, [34, 197, 94]],
    [0.5, [234, 179, 8]],
    [1.0, [239, 68, 68]],
  ];
  let a = paradas[0], b = paradas[paradas.length - 1];
  for (let i = 0; i < paradas.length - 1; i++) {
    if (t >= paradas[i][0] && t <= paradas[i + 1][0]) { a = paradas[i]; b = paradas[i + 1]; break; }
  }
  const f = (t - a[0]) / (b[0] - a[0] || 1);
  const c = a[1].map((v, i) => Math.round(v + (b[1][i] - v) * f));
  return `rgb(${c[0]},${c[1]},${c[2]})`;
}

/* Medidor de 0 a 100 com o status do jogo abaixo (badge colorido). */
function renderizarGauge(pontuacao, status) {
  const W = 240, H = 152, cx = W / 2, cy = 140, rExterno = 112, rInterno = 86;
  const tracos = svg("svg", { viewBox: `0 0 ${W} ${H}`, width: "240", height: "152" });
  const total = 44;
  for (let i = 0; i < total; i++) {
    const t = i / (total - 1);
    const ang = Math.PI - t * Math.PI;
    const x1 = cx + Math.cos(ang) * rInterno;
    const y1 = cy - Math.sin(ang) * rInterno;
    const x2 = cx + Math.cos(ang) * rExterno;
    const y2 = cy - Math.sin(ang) * rExterno;
    const aceso = t * 100 <= pontuacao + 1;
    tracos.append(svg("line", {
      x1, y1, x2, y2,
      stroke: corDoGauge(t),
      "stroke-width": 5,
      "stroke-linecap": "round",
      opacity: aceso ? 1 : 0.18,
    }));
  }
  const gauge = Api.criar("div", { class: "gauge" }, tracos,
    Api.criar("div", { style: "position:absolute;left:0;right:0;top:52px;text-align:center" },
      Api.criar("div", { class: "value" }, String(pontuacao)),
      Api.criar("div", { class: "max" }, "/100")));
  return Api.criar("div", { class: "gauge-wrap" }, gauge, Api.badge(status.rotulo, status.nivel));
}

/* Ícone por métrica (crash/bugs/stutter/fps) — chave `icone` de CARDS
   em bugometro_service.py. */
const ICONES_METRICA = {
  shield: '<path d="M12 3l7 3v6c0 4-3 7-7 9-4-2-7-5-7-9V6z"/>',
  bug: '<rect x="8" y="8" width="8" height="10" rx="4"/><path d="M12 4v3M5 9l3 1M19 9l-3 1M4 15h3M17 15h3"/>',
  activity: '<path d="M3 12h4l3 8 4-16 3 8h4"/>',
  gauge: '<path d="M12 13l4-3M4 18a8 8 0 1 1 16 0"/>',
};

function renderizarMetrica(m) {
  const cor = `var(--${m.nivel === "critical" ? "critical" : m.nivel === "warning" ? "warning" : "stable"})`;
  const icone = Api.criar("div", {
    class: "m-icon",
    style: `background:rgba(255,255,255,0.04);color:${cor}`,
    html: `<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${ICONES_METRICA[m.icone] || ICONES_METRICA.bug}</svg>`,
  });
  return Api.criar("div", { class: "metric-card" }, icone,
    Api.criar("div", {},
      Api.criar("div", { class: "m-label" }, m.rotulo),
      Api.criar("div", { class: "m-value", style: `color:${cor}` }, m.valor)));
}

/* Cor por série do gráfico. `chave` vem de montar_grafico() em
   bugometro_service.py: crash, bug, stutter, fps — não confundir com
   as chaves de métrica (crash/bugs/stutter/fps), que são outro eixo. */
const CORES_GRAFICO = {
  crash: "var(--critical)",
  bug: "var(--warning)",
  stutter: "var(--info)",
  fps: "#3b82f6",
};

/* Gráfico de linhas com dado SINTÉTICO: `grafico` não vem do banco nem
   olha o relógio (spec 6.7) — reproduz o comportamento antigo de
   propósito. Não é histórico real; o card acima já avisa isso na
   tela. */
function renderizarGrafico(grafico) {
  const W = 640, H = 200, pad = 8;
  const tela = svg("svg", { viewBox: `0 0 ${W} ${H}`, width: "100%", height: "220", preserveAspectRatio: "none" });
  for (let g = 0; g <= 4; g++) {
    const y = pad + (H - pad * 2) * (g / 4);
    tela.append(svg("line", { x1: 0, y1: y, x2: W, y2: y, stroke: "var(--border-soft)", "stroke-width": 1 }));
  }
  const n = grafico.rotulos.length;
  for (const serie of grafico.series) {
    const pontos = serie.dados.map((v, i) => {
      const x = (i / (n - 1)) * W;
      const y = H - pad - (v / 100) * (H - pad * 2);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(" ");
    tela.append(svg("polyline", {
      points: pontos, fill: "none", stroke: CORES_GRAFICO[serie.chave] || "var(--text-dim)",
      "stroke-width": 2.5, "stroke-linejoin": "round", "stroke-linecap": "round",
    }));
  }
  const legendas = Api.criar("div", { class: "row", style: "justify-content:space-between;font-size:11px;color:var(--text-dim);margin-top:6px" });
  grafico.rotulos.forEach((rotulo, i) => { if (i % 3 === 0) legendas.append(Api.criar("span", {}, rotulo)); });
  return Api.criar("div", {}, tela, legendas);
}

/* Uma linha da lista de bugs reportados. `categoria` e `severidade_rotulo`
   já chegam traduzidos do backend (montar_bug); `severidade` crua é
   só para escolher a cor do badge. `ja_confirmei` (fase 2) diz se o
   usuário atual já votou naquele relato — o botão de confirmar usa
   isso para nascer desabilitado quando for o caso. */
const NIVEL_POR_SEVERIDADE = { critica: "critical", alta: "warning", media: "warning", baixa: "stable" };
const ROTULOS_STATUS_RELATO = { aberto: "Aberto", confirmado: "Confirmado", resolvido: "Resolvido", rejeitado: "Rejeitado" };

function rotuloConfirmar(confirmacoes, jaConfirmei) {
  return jaConfirmei ? "✓ Confirmado" : `👍 Confirmar (${confirmacoes})`;
}

/* Botão "confirmar bug": POST /api/v1/votos-bug com {relato_id}. Nasce
   desabilitado e rotulado quando `bug.ja_confirmei` já é true.

   Um 409 aqui não é erro: a unique (relato_id, usuario_id) do backend
   significa que o voto já existe — o estado desejado já foi alcançado
   (ex.: duplo clique, ou outra aba já confirmou). Trata como sucesso
   idempotente — desabilita e rotula como confirmado, sem incrementar
   a contagem (o voto já estava contado) e sem pintar mensagem de erro,
   que aqui seria só ruído. */
function botaoConfirmarBug(bug) {
  const botao = Api.criar(
    "button",
    { class: "btn btn--outline", type: "button" },
    rotuloConfirmar(bug.confirmacoes, bug.ja_confirmei)
  );

  const marcarConfirmado = () => {
    botao.disabled = true;
    botao.style.opacity = "0.6";
    botao.style.cursor = "default";
    botao.textContent = rotuloConfirmar(bug.confirmacoes, true);
  };
  if (bug.ja_confirmei) marcarConfirmado();

  botao.addEventListener("click", async () => {
    botao.disabled = true;
    try {
      await Api.pedir("/api/v1/votos-bug", { metodo: "POST", corpo: { relato_id: bug.id } });
      bug.confirmacoes += 1;
      marcarConfirmado();
    } catch (e) {
      if (Api.ehSessaoExpirada(e)) return;
      if (e instanceof ErroApi && e.status === 409) {
        marcarConfirmado();
        return;
      }
      botao.disabled = false;
    }
  });

  return botao;
}

function renderizarBug(b) {
  const status = ROTULOS_STATUS_RELATO[b.status] || b.status;
  return Api.criar("div", { class: "activity-item" },
    Api.criar("div", {},
      Api.criar("div", { class: "a-title" }, b.titulo),
      Api.criar("div", { class: "a-sub" }, `${b.categoria} · ${status}`)),
    Api.badge(b.severidade_rotulo, NIVEL_POR_SEVERIDADE[b.severidade] || "stable"),
    botaoConfirmarBug(b));
}

/* Categoria e severidade do relato: select, não texto livre, porque
   cada valor pinta um badge de cor diferente na lista de bugs (o
   `severidade` cru escolhe a classe, o rótulo escolhe o texto). Chaves
   espelham CATEGORIAS_BUG/SEVERIDADES de app/models/bugometro.py. */
const CATEGORIAS_RELATO = [
  ["crash", "Crash"],
  ["graficos", "Gráficos"],
  ["progressao", "Progressão"],
  ["desempenho", "Desempenho"],
  ["online", "Online"],
  ["outro", "Outro"],
];
const SEVERIDADES_RELATO = [
  ["baixa", "Baixa"],
  ["media", "Média"],
  ["alta", "Alta"],
  ["critica", "Crítica"],
];

/* Mini-formulário "Reportar um bug", alternado pelo botão do card.
   POST /api/v1/relatos-bug exige jogo_id e titulo; jogo_id só existe
   no card do jogo (dados.jogo.id) — a tela só recebia o slug antes. */
function montarFormularioDeRelato(jogoId) {
  const estiloCampo =
    "width:100%;background:var(--surface-2);border:1px solid var(--border-soft);" +
    "border-radius:10px;padding:10px 12px;color:var(--text);font:inherit;margin-top:8px";

  const titulo = Api.criar("input", { type: "text", placeholder: "Título do bug…", style: estiloCampo });
  const categoria = Api.criar("select", { style: estiloCampo });
  CATEGORIAS_RELATO.forEach(([valor, rotulo]) => categoria.append(Api.criar("option", { value: valor }, rotulo)));
  categoria.value = "outro";
  const severidade = Api.criar("select", { style: estiloCampo });
  SEVERIDADES_RELATO.forEach(([valor, rotulo]) => severidade.append(Api.criar("option", { value: valor }, rotulo)));
  severidade.value = "media";
  const descricao = Api.criar("textarea", { placeholder: "Descreva o bug (opcional)…", rows: "3", style: estiloCampo });
  const erro = Api.criar("div", { style: "color:var(--critical);font-size:12px;margin-top:6px;display:none" });

  const enviar = Api.criar("button", {
    class: "btn btn--primary",
    style: "margin-top:8px",
    type: "button",
    onclick: async () => {
      if (!titulo.value.trim()) {
        erro.textContent = "Dê um título ao bug.";
        erro.style.display = "block";
        return;
      }
      enviar.disabled = true;
      erro.style.display = "none";
      const corpo = { jogo_id: jogoId, titulo: titulo.value.trim(), categoria: categoria.value, severidade: severidade.value };
      if (descricao.value.trim()) corpo.descricao = descricao.value.trim();
      try {
        await Api.pedir("/api/v1/relatos-bug", { metodo: "POST", corpo });
        location.reload();
      } catch (e) {
        if (Api.ehSessaoExpirada(e)) return;
        erro.textContent = e.erros ? Object.values(e.erros).flat().join(" ") : e.message;
        erro.style.display = "block";
        enviar.disabled = false;
      }
    },
  }, "Enviar relato");

  return Api.criar("div", { id: "bm-report-form", style: "margin-top:12px;padding-top:12px;border-top:1px solid var(--border-soft)" },
    Api.criar("div", { style: "font-weight:800;margin-bottom:4px" }, "Descreva o problema"),
    titulo, categoria, severidade, descricao, erro, enviar);
}

function renderizarAtividade(a) {
  return Api.criar("div", { class: "activity-item" },
    Api.criar("div", {
      class: "a-icon",
      style: `color:var(--${a.nivel === "critical" ? "critical" : "warning"})`,
      html: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M3 12h4l3 7 4-14 3 7h4"/></svg>',
    }),
    Api.criar("div", {},
      Api.criar("div", { class: "a-title" }, a.titulo),
      Api.criar("div", { class: "a-sub" }, a.subtitulo)),
    Api.criar("div", { class: "a-when" }, a.quando));
}

/* Linha do ranking dos jogos mais instáveis. Cada linha é também o
   "seletor de jogo" da tela: um link para /bugometro?jogo=<slug>, que
   o carregamento abaixo repassa para o endpoint. */
function renderizarTopInstavel(jogo) {
  const capa = Api.capa(jogo);
  return Api.criar("a", { class: "rank-row", href: "/bugometro?jogo=" + encodeURIComponent(jogo.slug) },
    capa,
    Api.criar("div", { class: "r-name" }, jogo.nome),
    Api.criar("b", {}, String(jogo.pontuacao)),
    Api.badge(jogo.status.rotulo, jogo.status.nivel));
}

// ---------------------------------------------------------------------
const REGIOES = ["bm-metrics", "bm-bugs", "bm-chart", "bm-activity", "bm-top"];

function marcarCarregando() {
  REGIOES.forEach((id) => Api.carregando(id));
}

function marcarErro(mensagem) {
  REGIOES.forEach((id) => Api.erro(id, mensagem));
}

function renderizarTela(dados) {
  const jogo = dados.jogo;

  const capa = Api.capa(jogo);
  capa.style.width = "96px";
  capa.style.height = "64px";
  document.getElementById("bm-cover").replaceChildren(capa);
  document.getElementById("bm-name").textContent = jogo.nome;
  document.getElementById("bm-updated").textContent = "Atualizado " + dados.atualizado_ha;

  document.getElementById("bm-gauge").replaceChildren(renderizarGauge(jogo.pontuacao, jogo.status));

  const metricas = document.getElementById("bm-metrics");
  metricas.replaceChildren(...dados.metricas.map(renderizarMetrica));

  const legenda = document.getElementById("bm-legend");
  legenda.replaceChildren(...dados.grafico.series.map((serie) =>
    Api.criar("span", {},
      Api.criar("span", { class: "dot", style: `background:${CORES_GRAFICO[serie.chave] || "var(--text-dim)"}` }),
      serie.rotulo)));
  document.getElementById("bm-chart").replaceChildren(renderizarGrafico(dados.grafico));

  const bugsHost = document.getElementById("bm-bugs");
  if (dados.bugs.length === 0) {
    Api.vazio("bm-bugs", "Nenhum bug ativo reportado para este jogo.");
  } else {
    bugsHost.replaceChildren(...dados.bugs.map(renderizarBug));
  }

  const botaoRelatar = document.getElementById("bm-report-btn");
  botaoRelatar.onclick = () => {
    const existente = document.getElementById("bm-report-form");
    if (existente) { existente.remove(); return; }
    botaoRelatar.closest(".card").append(montarFormularioDeRelato(jogo.id));
  };

  if (dados.atividades.length === 0) {
    Api.vazio("bm-activity", "Nenhuma atividade recente.");
  } else {
    document.getElementById("bm-activity").replaceChildren(...dados.atividades.map(renderizarAtividade));
  }

  if (dados.top_instaveis.length === 0) {
    Api.vazio("bm-top", "Nenhum jogo para comparar ainda.");
  } else {
    document.getElementById("bm-top").replaceChildren(...dados.top_instaveis.map(renderizarTopInstavel));
  }
}

/* `?jogo=<slug>` na URL da própria tela é repassado ao endpoint —
   é o que o ranking "top jogos instáveis" usa para trocar de jogo. */
async function carregarBugometro() {
  const slug = new URLSearchParams(location.search).get("jogo");
  const caminho = "/api/v1/telas/bugometro" + (slug ? "?jogo=" + encodeURIComponent(slug) : "");
  const dados = await Api.pedir(caminho);
  renderizarTela(dados);
}

Api.aoCarregar(async () => {
  marcarCarregando();
  try {
    await carregarBugometro();
  } catch (e) {
    if (Api.ehSessaoExpirada(e)) return; // já foi para o login
    marcarErro(e.message);
  }
});
