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
