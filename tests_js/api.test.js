import assert from 'node:assert/strict';
import { afterEach, beforeEach, test } from 'node:test';

import { ApiError, api } from '../app/static/js/api.js';

let chamadas;

function responderCom({ status = 200, corpo = {} } = {}) {
  globalThis.fetch = async (url, opcoes) => {
    chamadas.push({ url, opcoes });
    return {
      ok: status >= 200 && status < 300,
      status,
      json: async () => corpo,
    };
  };
}

beforeEach(() => {
  chamadas = [];
  globalThis.LAAC = { apiBase: 'http://api.test', usuarioId: 7 };
});

afterEach(() => {
  delete globalThis.fetch;
  delete globalThis.LAAC;
});

test('listar monta a URL com o sufixo /api', async () => {
  responderCom({ corpo: [{ id: 1 }] });

  const dados = await api.listar('jogos');

  assert.equal(chamadas[0].url, 'http://api.test/api/jogos');
  assert.deepEqual(dados, [{ id: 1 }]);
});

test('obter acrescenta o id ao recurso', async () => {
  responderCom({ corpo: { id: 3 } });

  await api.obter('jogos', 3);

  assert.equal(chamadas[0].url, 'http://api.test/api/jogos/3');
});

test('criar envia POST com o corpo em JSON', async () => {
  responderCom({ status: 201, corpo: { id: 9 } });

  const criado = await api.criar('relatos_bug', { jogo_id: 1, titulo: 'Crash' });

  assert.equal(chamadas[0].opcoes.method, 'POST');
  assert.equal(chamadas[0].opcoes.body, '{"jogo_id":1,"titulo":"Crash"}');
  assert.equal(criado.id, 9);
});

test('atualizar envia PUT para o recurso com id', async () => {
  responderCom({ corpo: { id: 4, favorito: true } });

  await api.atualizar('biblioteca_usuario', 4, { favorito: true });

  assert.equal(chamadas[0].opcoes.method, 'PUT');
  assert.equal(chamadas[0].url, 'http://api.test/api/biblioteca_usuario/4');
});

test('remover trata o 204 sem corpo', async () => {
  globalThis.fetch = async () => ({ ok: true, status: 204, json: async () => { throw new Error('sem corpo'); } });

  assert.equal(await api.remover('biblioteca_usuario', 4), null);
});

test('404 vira ApiError com o status', async () => {
  responderCom({ status: 404, corpo: { message: 'Não encontrado.' } });

  await assert.rejects(api.obter('jogos', 999), (erro) => {
    assert.ok(erro instanceof ApiError);
    assert.equal(erro.status, 404);
    assert.equal(erro.message, 'Não encontrado.');
    return true;
  });
});

test('422 preserva os erros de campo', async () => {
  responderCom({ status: 422, corpo: { message: 'Inválido.', errors: { titulo: ['Obrigatório.'] } } });

  await assert.rejects(api.criar('relatos_bug', {}), (erro) => {
    assert.deepEqual(erro.errors, { titulo: ['Obrigatório.'] });
    return true;
  });
});

test('erro com corpo nao-JSON ainda vira ApiError utilizavel', async () => {
  globalThis.fetch = async () => ({
    ok: false,
    status: 500,
    json: async () => { throw new SyntaxError('nao e json'); },
  });

  await assert.rejects(api.listar('jogos'), (erro) => {
    assert.ok(erro instanceof ApiError);
    assert.equal(erro.status, 500);
    assert.equal(erro.message, 'HTTP 500');
    assert.deepEqual(erro.errors, {});
    return true;
  });
});

test('falha de rede vira ApiError com status zero', async () => {
  globalThis.fetch = async () => { throw new TypeError('failed to fetch'); };

  await assert.rejects(api.listar('jogos'), (erro) => {
    assert.ok(erro instanceof ApiError);
    assert.equal(erro.status, 0);
    return true;
  });
});

test('barra final na apiBase não vira barra dupla', async () => {
  globalThis.LAAC = { apiBase: 'http://api.test/' };
  responderCom({ corpo: [] });

  await api.listar('jogos');

  assert.equal(chamadas[0].url, 'http://api.test/api/jogos');
});
