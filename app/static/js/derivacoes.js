/**
 * Funções puras: joins e regras derivadas (spec §5.3 e §5.4).
 *
 * Este módulo não conhece browser, rede nem armazenamento — é o que o torna
 * testável com `node --test`. Quem cuida de cache e fetch é o store.js.
 */

export const XP_POR_ATIVIDADE = 50;
export const XP_POR_NIVEL = 2000;
export const NOTA_POSITIVA = 5.0;

/**
 * Normaliza um id para comparação.
 *
 * Ids cruzam a fronteira da API em tipos que não controlamos: `usuarioId` vem
 * do Jinja como número JSON, e o que o Laravel serializa depende de driver,
 * cast e tamanho da coluna. `1 === '1'` é falso e `Map.get` usa SameValueZero,
 * então um único id com o tipo trocado faz o join devolver vazio *em
 * silêncio* — a tela renderiza um empty-state impecável e ninguém percebe.
 * É a falha que o spec §8.3 chama de "telas quebram silenciosamente".
 *
 * Normalizamos para string, não para número: `Number` perde precisão em id
 * grande serializado como string, e colapsa `null`, `''` e `false` todos em 0.
 * `null` e `undefined` passam intactos para não virarem a string `'null'`.
 */
export function normalizarId(valor) {
  return valor === null || valor === undefined ? valor : String(valor);
}

/** Compara dois ids sem se importar com o tipo em que cada um chegou. */
export function mesmoId(a, b) {
  return normalizarId(a) === normalizarId(b);
}

/**
 * `Map` com id normalizado na chave: `get(1)` e `get('1')` acham a mesma
 * entrada.
 *
 * É a única forma de o mapa continuar seguro depois de devolvido — quem
 * consome não precisa saber que existe normalização, e um módulo de tela que
 * faça `indexarPor(jogos, 'id').get(entrada.jogo_id)` acerta com qualquer um
 * dos dois tipos.
 */
class MapaDeIds extends Map {
  get(chave) {
    return super.get(normalizarId(chave));
  }

  set(chave, valor) {
    return super.set(normalizarId(chave), valor);
  }

  has(chave) {
    return super.has(normalizarId(chave));
  }

  delete(chave) {
    return super.delete(normalizarId(chave));
  }
}

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
  return usuariosBadges.filter((ub) => mesmoId(ub.usuario_id, usuarioId)).length;
}

/** 👍/👎 do jogo. Avaliação sem nota não conta para nenhum lado. */
export function polegares(avaliacoes) {
  const comNota = avaliacoes.filter((a) => a.nota !== null && a.nota !== undefined);
  const positivas = comNota.filter((a) => Number(a.nota) >= NOTA_POSITIVA).length;
  return { positivas, negativas: comNota.length - positivas };
}

export function curtidasPorAvaliacao(curtidas) {
  const mapa = new MapaDeIds();
  for (const curtida of curtidas) {
    mapa.set(curtida.avaliacao_id, (mapa.get(curtida.avaliacao_id) ?? 0) + 1);
  }
  return mapa;
}

export function indexarPor(colecao, chave) {
  const mapa = new MapaDeIds();
  for (const item of colecao) mapa.set(item[chave], item);
  return mapa;
}

export function agruparPor(colecao, chave) {
  const mapa = new MapaDeIds();
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
    .filter((entrada) => mesmoId(entrada.usuario_id, usuarioId))
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
  const doJogo = metricas.filter((m) => mesmoId(m.jogo_id, jogoId));
  return Object.fromEntries(
    TIPOS_DE_METRICA.map((tipo) => [tipo, doJogo.find((m) => m.tipo === tipo) ?? null]),
  );
}

/** historico_bug de um jogo dentro da janela, do mais antigo ao mais novo. */
export function serieDe(historico, jogoId, desde) {
  return historico
    .filter((h) => mesmoId(h.jogo_id, jogoId) && new Date(h.registrado_em) >= desde)
    .sort(porData('registrado_em'));
}

/** topicos ⨝ usuarios ⨝ categorias, com contagem de posts e excerto. */
export function topicosDe(topicos, posts, usuarios, categorias, categoriaId = null) {
  const autores = indexarPor(usuarios, 'id');
  const nomes = indexarPor(categorias, 'id');
  const porTopico = agruparPor(posts, 'topico_id');

  return topicos
    .filter((t) => (categoriaId === null ? true : mesmoId(t.categoria_id, categoriaId)))
    .map((topico) => {
      const mensagens = (porTopico.get(topico.id) ?? []).slice().sort(porData('criado_em'));
      return {
        ...topico,
        autor: autores.get(topico.usuario_id) ?? null,
        categoria: nomes.get(topico.categoria_id) ?? null,
        // O tópico não tem coluna de corpo: a primeira mensagem *é* o corpo
        // (spec §6.1), e é dela que sai o excerto logo abaixo. Contá-la como
        // resposta faria a Comunidade dizer "2 respostas" numa thread com uma.
        respostas: Math.max(0, mensagens.length - 1),
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
  const minhas = atividades.filter((a) => mesmoId(a.usuario_id, usuarioId));

  return {
    usuario: usuarios.find((u) => mesmoId(u.id, usuarioId)) ?? null,
    badges: usuariosBadges
      .filter((ub) => mesmoId(ub.usuario_id, usuarioId))
      .map((ub) => catalogoDeBadges.get(ub.badge_id))
      .filter(Boolean),
    conquistas: conquistas(usuariosBadges, usuarioId),
    diasAtivo: diasAtivo(minhas),
    xp: xpDoUsuario(minhas),
    atividades: minhas.slice().sort(porDataDesc('criado_em')),
  };
}
