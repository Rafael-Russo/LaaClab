/**
 * Funções puras: joins e regras derivadas (spec §5.3 e §5.4).
 *
 * Este módulo não conhece browser, rede nem armazenamento — é o que o torna
 * testável com `node --test`. Quem cuida de cache e fetch é o store.js.
 */

export const XP_POR_ATIVIDADE = 50;
export const XP_POR_NIVEL = 2000;
export const NOTA_POSITIVA = 5.0;

/** XP derivado das atividades. O *nível* vem da API, não daqui (spec §5.4). */
export function xpDoUsuario(atividades) {
  const total = atividades.length * XP_POR_ATIVIDADE;
  return { total, noNivel: total % XP_POR_NIVEL, doNivel: XP_POR_NIVEL };
}

/** Dias distintos em que o usuário fez alguma coisa. */
export function diasAtivo(atividades) {
  return new Set(atividades.map((a) => String(a.criado_em).slice(0, 10))).size;
}

export function conquistas(usuariosBadges, usuarioId) {
  return usuariosBadges.filter((ub) => ub.usuario_id === usuarioId).length;
}

/** 👍/👎 do jogo. Avaliação sem nota não conta para nenhum lado. */
export function polegares(avaliacoes) {
  const comNota = avaliacoes.filter((a) => a.nota !== null && a.nota !== undefined);
  const positivas = comNota.filter((a) => Number(a.nota) >= NOTA_POSITIVA).length;
  return { positivas, negativas: comNota.length - positivas };
}

export function curtidasPorAvaliacao(curtidas) {
  const mapa = new Map();
  for (const curtida of curtidas) {
    mapa.set(curtida.avaliacao_id, (mapa.get(curtida.avaliacao_id) ?? 0) + 1);
  }
  return mapa;
}

export function indexarPor(colecao, chave) {
  const mapa = new Map();
  for (const item of colecao) mapa.set(item[chave], item);
  return mapa;
}

export function agruparPor(colecao, chave) {
  const mapa = new Map();
  for (const item of colecao) {
    const grupo = mapa.get(item[chave]);
    if (grupo) grupo.push(item);
    else mapa.set(item[chave], [item]);
  }
  return mapa;
}

const porData = (campo) => (a, b) => new Date(a[campo]) - new Date(b[campo]);
const porDataDesc = (campo) => (a, b) => new Date(b[campo]) - new Date(a[campo]);

/** jogos ⨝ bugometro_status. Jogo sem status fica com score nulo, não some. */
export function jogosComScore(jogos, statusPorJogo) {
  const status = indexarPor(statusPorJogo, 'jogo_id');
  return jogos.map((jogo) => ({
    ...jogo,
    pontuacao: status.get(jogo.id)?.pontuacao ?? null,
    status: status.get(jogo.id)?.status ?? null,
  }));
}

/** biblioteca_usuario ⨝ jogos ⨝ bugometro_status, do usuário informado. */
export function bibliotecaDe(entradas, jogos, statusPorJogo, usuarioId) {
  const catalogo = indexarPor(jogosComScore(jogos, statusPorJogo), 'id');
  return entradas
    .filter((entrada) => entrada.usuario_id === usuarioId)
    .map((entrada) => ({
      entradaId: entrada.id,
      favorito: Boolean(entrada.favorito),
      jogo: catalogo.get(entrada.jogo_id) ?? null,
    }))
    .filter((item) => item.jogo !== null);
}

/** Vocabulário de metricas_bug.tipo — spec §8.3. */
export const TIPOS_DE_METRICA = ['crash', 'bug', 'stutter', 'fps_drop'];

/** Sempre devolve as quatro chaves; a que faltar vem `null`. */
export function metricasDe(metricas, jogoId) {
  const doJogo = metricas.filter((m) => m.jogo_id === jogoId);
  return Object.fromEntries(
    TIPOS_DE_METRICA.map((tipo) => [tipo, doJogo.find((m) => m.tipo === tipo) ?? null]),
  );
}

/** historico_bug de um jogo dentro da janela, do mais antigo ao mais novo. */
export function serieDe(historico, jogoId, desde) {
  return historico
    .filter((h) => h.jogo_id === jogoId && new Date(h.registrado_em) >= desde)
    .sort(porData('registrado_em'));
}

/** topicos ⨝ usuarios ⨝ categorias, com contagem de posts e excerto. */
export function topicosDe(topicos, posts, usuarios, categorias, categoriaId = null) {
  const autores = indexarPor(usuarios, 'id');
  const nomes = indexarPor(categorias, 'id');
  const porTopico = agruparPor(posts, 'topico_id');

  return topicos
    .filter((t) => (categoriaId === null ? true : t.categoria_id === categoriaId))
    .map((topico) => {
      const mensagens = (porTopico.get(topico.id) ?? []).slice().sort(porData('criado_em'));
      return {
        ...topico,
        autor: autores.get(topico.usuario_id) ?? null,
        categoria: nomes.get(topico.categoria_id) ?? null,
        respostas: mensagens.length,
        excerto: mensagens[0]?.conteudo ?? '',
      };
    });
}

/** relatos_bug ⨝ jogos — é o que alimenta a tela Alertas (spec §2). */
export function alertasDe(relatos, jogos, { severidade = null, busca = '' } = {}) {
  const catalogo = indexarPor(jogos, 'id');
  const termo = busca.trim().toLowerCase();

  return relatos
    .filter((r) => (severidade === null ? true : r.severidade === severidade))
    .map((r) => ({ ...r, jogo: catalogo.get(r.jogo_id) ?? null }))
    .filter((r) => r.jogo !== null)
    .filter((r) => (termo === '' ? true : r.jogo.nome.toLowerCase().includes(termo)))
    .sort(porDataDesc('criado_em'));
}

/** usuarios ⨝ usuarios_badges ⨝ badges ⨝ atividades, com as regras derivadas. */
export function perfilDe(usuarios, usuariosBadges, badges, atividades, usuarioId) {
  const catalogoDeBadges = indexarPor(badges, 'id');
  const minhas = atividades.filter((a) => a.usuario_id === usuarioId);

  return {
    usuario: usuarios.find((u) => u.id === usuarioId) ?? null,
    badges: usuariosBadges
      .filter((ub) => ub.usuario_id === usuarioId)
      .map((ub) => catalogoDeBadges.get(ub.badge_id))
      .filter(Boolean),
    conquistas: conquistas(usuariosBadges, usuarioId),
    diasAtivo: diasAtivo(minhas),
    xp: xpDoUsuario(minhas),
    atividades: minhas.slice().sort(porDataDesc('criado_em')),
  };
}
