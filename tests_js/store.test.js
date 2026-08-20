import assert from 'node:assert/strict';
import { afterEach, beforeEach, test } from 'node:test';

import { INVALIDACOES, TTL_MS, _resetar, colecao, invalidar, jogosComScore } from '../app/static/js/store.js';

let requisicoes;

function sessionStorageFalso({ cota = Infinity } = {}) {
  const dados = new Map();
  return {
    getItem: (chave) => dados.get(chave) ?? null,
    removeItem: (chave) => dados.delete(chave),
    setItem: (chave, valor) => {
      if (dados.size >= cota) {
        const erro = new Error('cota');
        erro.name = 'QuotaExceededError';
        throw erro;
      }
      dados.set(chave, valor);
    },
  };
}

beforeEach(() => {
  requisicoes = [];
  globalThis.LAAC = { apiBase: 'http://api.test', usuarioId: 7 };
  globalThis.sessionStorage = sessionStorageFalso();
  globalThis.fetch = async (url) => {
    requisicoes.push(url);
    return { ok: true, status: 200, json: async () => [{ id: 1, nome: 'Warzone' }] };
  };
  _resetar();
});

afterEach(() => {
  delete globalThis.fetch;
  delete globalThis.sessionStorage;
  delete globalThis.LAAC;
});

test('a primeira chamada busca na API', async () => {
  const dados = await colecao('jogos');

  assert.equal(requisicoes.length, 1);
  assert.deepEqual(dados, [{ id: 1, nome: 'Warzone' }]);
});

test('a segunda chamada vem do cache, sem tocar na rede', async () => {
  await colecao('jogos');
  await colecao('jogos');

  assert.equal(requisicoes.length, 1);
});

test('colecoes diferentes nao compartilham cache', async () => {
  await colecao('jogos');
  await colecao('plataformas');

  assert.equal(requisicoes.length, 2);
});

test('passado o TTL a colecao e buscada de novo', async () => {
  const agora = 1_000_000;
  await colecao('jogos', { agora });

  await colecao('jogos', { agora: agora + TTL_MS + 1 });

  assert.equal(requisicoes.length, 2);
});

test('dentro do TTL o cache ainda vale', async () => {
  const agora = 1_000_000;
  await colecao('jogos', { agora });

  await colecao('jogos', { agora: agora + TTL_MS - 1 });

  assert.equal(requisicoes.length, 1);
});

test('invalidar forca a proxima busca', async () => {
  await colecao('jogos');

  invalidar('jogos');
  await colecao('jogos');

  assert.equal(requisicoes.length, 2);
});

test('invalidar aceita varias colecoes de uma vez', async () => {
  await colecao('jogos');
  await colecao('posts');

  invalidar('jogos', 'posts');
  await colecao('jogos');
  await colecao('posts');

  assert.equal(requisicoes.length, 4);
});

test('cota estourada nao quebra: o cache cai para memoria', async () => {
  globalThis.sessionStorage = sessionStorageFalso({ cota: 0 });
  _resetar();

  await colecao('jogos');
  const segunda = await colecao('jogos');

  assert.equal(requisicoes.length, 1);
  assert.deepEqual(segunda, [{ id: 1, nome: 'Warzone' }]);
});

test('sem sessionStorage nenhum o store ainda funciona', async () => {
  delete globalThis.sessionStorage;
  _resetar();

  await colecao('jogos');
  await colecao('jogos');

  assert.equal(requisicoes.length, 1);
});

test('o mapa de invalidacao cobre as sete mutacoes do spec §5.2', () => {
  assert.deepEqual(INVALIDACOES.biblioteca, ['biblioteca_usuario']);
  assert.deepEqual(INVALIDACOES.topico, ['topicos']);
  assert.deepEqual(INVALIDACOES.post, ['posts']);
  assert.deepEqual(INVALIDACOES.curtida, ['curtidas_avaliacoes']);
  assert.deepEqual(INVALIDACOES.avaliacao, ['avaliacoes']);
  assert.deepEqual(INVALIDACOES.relato, ['relatos_bug']);
  assert.deepEqual(INVALIDACOES.notificacao, ['notificacoes']);
});

test('o store reexporta as views, para as telas importarem so ele', () => {
  const resultado = jogosComScore([{ id: 1 }], [{ jogo_id: 1, pontuacao: 72, status: 'critico' }]);

  assert.equal(resultado[0].pontuacao, 72);
});
