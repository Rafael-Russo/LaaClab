import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  NOTA_POSITIVA,
  XP_POR_ATIVIDADE,
  XP_POR_NIVEL,
  conquistas,
  curtidasPorAvaliacao,
  diasAtivo,
  polegares,
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
