import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  NOTA_POSITIVA,
  XP_POR_ATIVIDADE,
  XP_POR_NIVEL,
  agruparPor,
  alertasDe,
  bibliotecaDe,
  conquistas,
  curtidasPorAvaliacao,
  diasAtivo,
  indexarPor,
  jogosComScore,
  mesmoId,
  metricasDe,
  perfilDe,
  polegares,
  serieDe,
  topicosDe,
  xpDoUsuario,
} from '../app/static/js/derivacoes.js';

const atividade = (criado_em) => ({ usuario_id: 7, tipo: 'post', criado_em });

test('as constantes batem com o spec §5.4', () => {
  assert.equal(XP_POR_ATIVIDADE, 50);
  assert.equal(XP_POR_NIVEL, 2000);
  assert.equal(NOTA_POSITIVA, 5.0);
});

test('xp soma 50 por atividade', () => {
  const xp = xpDoUsuario([atividade('2026-08-01T10:00:00Z'), atividade('2026-08-02T10:00:00Z')]);

  assert.equal(xp.total, 100);
});

test('a barra mostra o progresso dentro do nivel atual', () => {
  const xp = xpDoUsuario(Array.from({ length: 45 }, () => atividade('2026-08-01T10:00:00Z')));

  assert.equal(xp.total, 2250);
  assert.equal(xp.noNivel, 250);
  assert.equal(xp.doNivel, 2000);
});

test('usuario sem atividade tem xp zero', () => {
  assert.deepEqual(xpDoUsuario([]), { total: 0, noNivel: 0, doNivel: 2000 });
});

test('dias ativo conta datas distintas, nao atividades', () => {
  const lista = [
    atividade('2026-08-01T10:00:00Z'),
    atividade('2026-08-01T22:00:00Z'),
    atividade('2026-08-03T08:00:00Z'),
  ];

  assert.equal(diasAtivo(lista), 2);
});

test('dias ativo de lista vazia e zero', () => {
  assert.equal(diasAtivo([]), 0);
});

test('conquistas conta so as badges do usuario', () => {
  const badges = [
    { usuario_id: 7, badge_id: 1 },
    { usuario_id: 7, badge_id: 2 },
    { usuario_id: 9, badge_id: 1 },
  ];

  assert.equal(conquistas(badges, 7), 2);
});

test('polegares separam as avaliacoes pelo corte em 5.0', () => {
  const avaliacoes = [{ nota: '9.1' }, { nota: '5.0' }, { nota: '4.9' }, { nota: '0.0' }];

  assert.deepEqual(polegares(avaliacoes), { positivas: 2, negativas: 2 });
});

test('avaliacao sem nota nao conta para nenhum lado', () => {
  const avaliacoes = [{ nota: '8.0' }, { nota: null }, { comentario: 'só texto' }];

  assert.deepEqual(polegares(avaliacoes), { positivas: 1, negativas: 0 });
});

test('curtidas viram um mapa por avaliacao', () => {
  const curtidas = [
    { avaliacao_id: 1, usuario_id: 7 },
    { avaliacao_id: 1, usuario_id: 9 },
    { avaliacao_id: 2, usuario_id: 7 },
  ];

  const mapa = curtidasPorAvaliacao(curtidas);

  assert.equal(mapa.get(1), 2);
  assert.equal(mapa.get(2), 1);
  assert.equal(mapa.get(99), undefined);
});

const JOGOS = [
  { id: 1, nome: 'Warzone', genero: 'FPS' },
  { id: 2, nome: 'Valorant', genero: 'FPS' },
];
const STATUS = [
  { id: 10, jogo_id: 1, pontuacao: 72, status: 'critico' },
  { id: 11, jogo_id: 2, pontuacao: 25, status: 'estavel' },
];

test('jogosComScore anexa pontuacao e status de cada jogo', () => {
  const resultado = jogosComScore(JOGOS, STATUS);

  assert.equal(resultado[0].pontuacao, 72);
  assert.equal(resultado[0].status, 'critico');
  assert.equal(resultado[0].nome, 'Warzone');
});

test('jogo sem bugometro_status fica com score nulo, nao some', () => {
  const resultado = jogosComScore([...JOGOS, { id: 3, nome: 'Novo' }], STATUS);

  assert.equal(resultado.length, 3);
  assert.equal(resultado[2].pontuacao, null);
});

test('bibliotecaDe traz so as entradas do usuario, com o jogo embutido', () => {
  const entradas = [
    { id: 100, usuario_id: 7, jogo_id: 1, favorito: true },
    { id: 101, usuario_id: 9, jogo_id: 2, favorito: false },
  ];

  const resultado = bibliotecaDe(entradas, JOGOS, STATUS, 7);

  assert.equal(resultado.length, 1);
  assert.equal(resultado[0].entradaId, 100);
  assert.equal(resultado[0].favorito, true);
  assert.equal(resultado[0].jogo.nome, 'Warzone');
  assert.equal(resultado[0].jogo.pontuacao, 72);
});

test('entrada apontando para jogo inexistente e descartada', () => {
  const entradas = [{ id: 100, usuario_id: 7, jogo_id: 999, favorito: false }];

  assert.deepEqual(bibliotecaDe(entradas, JOGOS, STATUS, 7), []);
});

test('metricasDe devolve as quatro chaves do vocabulario, mesmo faltando', () => {
  const metricas = [
    { id: 1, jogo_id: 1, tipo: 'crash', severidade: 'alto', porcentagem: 80 },
    { id: 2, jogo_id: 1, tipo: 'bug', severidade: 'medio', porcentagem: 50 },
    { id: 3, jogo_id: 2, tipo: 'crash', severidade: 'baixo', porcentagem: 10 },
  ];

  const resultado = metricasDe(metricas, 1);

  assert.deepEqual(Object.keys(resultado), ['crash', 'bug', 'stutter', 'fps_drop']);
  assert.equal(resultado.crash.severidade, 'alto');
  assert.equal(resultado.stutter, null);
});

test('serieDe filtra pela janela e ordena do mais antigo ao mais novo', () => {
  const historico = [
    { jogo_id: 1, registrado_em: '2026-08-19T12:00:00Z', quantidade_crash: 5 },
    { jogo_id: 1, registrado_em: '2026-08-19T10:00:00Z', quantidade_crash: 3 },
    { jogo_id: 1, registrado_em: '2026-08-10T10:00:00Z', quantidade_crash: 1 },
    { jogo_id: 2, registrado_em: '2026-08-19T11:00:00Z', quantidade_crash: 9 },
  ];

  const resultado = serieDe(historico, 1, new Date('2026-08-19T00:00:00Z'));

  assert.equal(resultado.length, 2);
  assert.equal(resultado[0].quantidade_crash, 3);
  assert.equal(resultado[1].quantidade_crash, 5);
});

const USUARIOS = [{ id: 7, nome_usuario: 'Nikola98' }];
const CATEGORIAS = [{ id: 1, nome: 'Discussão' }, { id: 2, nome: 'Bug' }];
const TOPICOS = [
  { id: 50, usuario_id: 7, categoria_id: 1, titulo: 'Queda de FPS' },
  { id: 51, usuario_id: 7, categoria_id: 2, titulo: 'Texturas' },
];
const POSTS = [
  { id: 500, topico_id: 50, usuario_id: 7, conteudo: 'Primeira mensagem.', criado_em: '2026-08-01T10:00:00Z' },
  { id: 501, topico_id: 50, usuario_id: 7, conteudo: 'Resposta.', criado_em: '2026-08-02T10:00:00Z' },
];

test('topicosDe anexa autor, categoria, contagem e excerto', () => {
  const resultado = topicosDe(TOPICOS, POSTS, USUARIOS, CATEGORIAS);

  assert.equal(resultado[0].autor.nome_usuario, 'Nikola98');
  assert.equal(resultado[0].categoria.nome, 'Discussão');
  assert.equal(resultado[0].respostas, 2);
  assert.equal(resultado[0].excerto, 'Primeira mensagem.');
});

test('topico sem post tem excerto vazio e zero respostas', () => {
  const resultado = topicosDe(TOPICOS, POSTS, USUARIOS, CATEGORIAS);

  assert.equal(resultado[1].respostas, 0);
  assert.equal(resultado[1].excerto, '');
});

test('topicosDe filtra por categoria quando pedido', () => {
  const resultado = topicosDe(TOPICOS, POSTS, USUARIOS, CATEGORIAS, 2);

  assert.equal(resultado.length, 1);
  assert.equal(resultado[0].titulo, 'Texturas');
});

const RELATOS = [
  { id: 1, jogo_id: 1, titulo: 'Crash', severidade: 'critico', criado_em: '2026-08-19T10:00:00Z' },
  { id: 2, jogo_id: 2, titulo: 'FPS', severidade: 'instavel', criado_em: '2026-08-19T12:00:00Z' },
];

test('alertasDe anexa o jogo e ordena do mais recente', () => {
  const resultado = alertasDe(RELATOS, JOGOS);

  assert.equal(resultado[0].jogo.nome, 'Valorant');
  assert.equal(resultado[1].jogo.nome, 'Warzone');
});

test('alertasDe filtra por severidade', () => {
  const resultado = alertasDe(RELATOS, JOGOS, { severidade: 'critico' });

  assert.equal(resultado.length, 1);
  assert.equal(resultado[0].titulo, 'Crash');
});

test('alertasDe busca pelo nome do jogo, sem diferenciar caixa', () => {
  const resultado = alertasDe(RELATOS, JOGOS, { busca: 'warZONE' });

  assert.equal(resultado.length, 1);
  assert.equal(resultado[0].jogo.nome, 'Warzone');
});

test('perfilDe junta badges, conquistas, dias ativo e xp', () => {
  const usuariosBadges = [{ usuario_id: 7, badge_id: 1 }, { usuario_id: 9, badge_id: 2 }];
  const badges = [{ id: 1, nome: 'Caçador de bugs' }, { id: 2, nome: 'Veterano' }];
  const atividades = [
    { usuario_id: 7, tipo: 'post', criado_em: '2026-08-01T10:00:00Z' },
    { usuario_id: 7, tipo: 'avaliacao', criado_em: '2026-08-02T10:00:00Z' },
    { usuario_id: 9, tipo: 'post', criado_em: '2026-08-03T10:00:00Z' },
  ];

  const perfil = perfilDe(USUARIOS, usuariosBadges, badges, atividades, 7);

  assert.equal(perfil.usuario.nome_usuario, 'Nikola98');
  assert.deepEqual(perfil.badges.map((b) => b.nome), ['Caçador de bugs']);
  assert.equal(perfil.conquistas, 1);
  assert.equal(perfil.diasAtivo, 2);
  assert.equal(perfil.xp.total, 100);
  assert.equal(perfil.atividades[0].criado_em, '2026-08-02T10:00:00Z');
});

// --- Tipo do id na fronteira com a API (spec §8.3) --------------------------
//
// `usuarioId` sai do Jinja como número JSON; o que o Laravel serializa depende
// de driver, cast e tamanho da coluna. Com `===` cru e `Map.get`, um lado em
// string fazia todo join devolver vazio *em silêncio* — e a tela renderizava
// um empty-state impecável.

test('mesmoId ignora o tipo em que cada id chegou', () => {
  assert.equal(mesmoId(1, '1'), true);
  assert.equal(mesmoId('42', 42), true);
  assert.equal(mesmoId(1, 2), false);
  assert.equal(mesmoId(0, ''), false);
  assert.equal(mesmoId(null, undefined), false);
});

test('indexarPor e agruparPor casam chave numerica com chave em string', () => {
  const indice = indexarPor([{ id: '1', nome: 'Warzone' }], 'id');
  const grupos = agruparPor([{ jogo_id: 1 }, { jogo_id: '1' }], 'jogo_id');

  assert.equal(indice.get(1).nome, 'Warzone');
  assert.equal(indice.get('1').nome, 'Warzone');
  assert.equal(grupos.get('1').length, 2);
  assert.equal(grupos.get(1).length, 2);
});

test('curtidasPorAvaliacao soma as duas grafias do mesmo id', () => {
  const mapa = curtidasPorAvaliacao([{ avaliacao_id: 1 }, { avaliacao_id: '1' }]);

  assert.equal(mapa.get(1), 2);
  assert.equal(mapa.get('1'), 2);
});

const STATUS_EM_STRING = [{ id: 10, jogo_id: '1', pontuacao: 72, status: 'critico' }];

test('jogosComScore resolve o status com jogo_id em string', () => {
  const resultado = jogosComScore(JOGOS, STATUS_EM_STRING);

  assert.equal(resultado[0].pontuacao, 72);
  assert.equal(resultado[0].status, 'critico');
});

test('bibliotecaDe resolve usuario e jogo com ids em string', () => {
  const entradas = [{ id: 100, usuario_id: '7', jogo_id: '1', favorito: true }];

  const resultado = bibliotecaDe(entradas, JOGOS, STATUS_EM_STRING, 7);

  assert.equal(resultado.length, 1);
  assert.equal(resultado[0].jogo.nome, 'Warzone');
  assert.equal(resultado[0].jogo.pontuacao, 72);
});

test('metricasDe e serieDe filtram com jogo_id em string', () => {
  const metricas = [{ id: 1, jogo_id: '1', tipo: 'crash', severidade: 'alto' }];
  const historico = [{ jogo_id: '1', registrado_em: '2026-08-19T10:00:00Z', quantidade_crash: 3 }];

  assert.equal(metricasDe(metricas, 1).crash.severidade, 'alto');
  assert.equal(serieDe(historico, 1, new Date('2026-08-19T00:00:00Z')).length, 1);
});

test('topicosDe joina autor, categoria e posts com ids em string', () => {
  const topicos = [{ id: '50', usuario_id: '7', categoria_id: '1', titulo: 'Queda de FPS' }];

  const resultado = topicosDe(topicos, POSTS, USUARIOS, CATEGORIAS, 1);

  assert.equal(resultado.length, 1);
  assert.equal(resultado[0].autor.nome_usuario, 'Nikola98');
  assert.equal(resultado[0].categoria.nome, 'Discussão');
  assert.equal(resultado[0].excerto, 'Primeira mensagem.');
});

test('alertasDe anexa o jogo com jogo_id em string', () => {
  const relatos = [
    { id: 1, jogo_id: '1', titulo: 'Crash', severidade: 'critico', criado_em: '2026-08-19T10:00:00Z' },
  ];

  const resultado = alertasDe(relatos, JOGOS);

  assert.equal(resultado.length, 1);
  assert.equal(resultado[0].jogo.nome, 'Warzone');
});

test('perfilDe reune badges, conquistas e atividades com ids em string', () => {
  const usuariosBadges = [{ usuario_id: '7', badge_id: '1' }];
  const badges = [{ id: 1, nome: 'Caçador de bugs' }];
  const atividades = [{ usuario_id: '7', tipo: 'post', criado_em: '2026-08-01T10:00:00Z' }];

  const perfil = perfilDe(USUARIOS, usuariosBadges, badges, atividades, 7);

  assert.equal(perfil.usuario.nome_usuario, 'Nikola98');
  assert.deepEqual(perfil.badges.map((b) => b.nome), ['Caçador de bugs']);
  assert.equal(perfil.conquistas, 1);
  assert.equal(perfil.xp.total, 50);
});

test('conquistas conta as badges com usuario_id em string', () => {
  assert.equal(conquistas([{ usuario_id: '7' }, { usuario_id: 9 }], 7), 1);
});
