import assert from 'node:assert/strict';
import { test } from 'node:test';

import { ApiError } from '../app/static/js/api.js';
import {
  classeDeStatus,
  mensagemDeErro,
  rotuloDeSeveridade,
  rotuloDeStatus,
} from '../app/static/js/ui.js';

test('cada status do vocabulario tem sua classe', () => {
  assert.equal(classeDeStatus('estavel'), 'laac-status-estavel');
  assert.equal(classeDeStatus('atencao'), 'laac-status-atencao');
  assert.equal(classeDeStatus('instavel'), 'laac-status-instavel');
  assert.equal(classeDeStatus('critico'), 'laac-status-critico');
});

test('status desconhecido ou ausente cai num neutro, nao quebra', () => {
  assert.equal(classeDeStatus('inventado'), 'laac-status-neutro');
  assert.equal(classeDeStatus(null), 'laac-status-neutro');
});

test('os rotulos de status saem acentuados como nos mockups', () => {
  assert.equal(rotuloDeStatus('estavel'), 'Estável');
  assert.equal(rotuloDeStatus('critico'), 'Crítico');
  assert.equal(rotuloDeStatus(null), '—');
});

test('severidade de metrica e de relato compartilham o mesmo rotulador', () => {
  assert.equal(rotuloDeSeveridade('baixo'), 'Baixo');
  assert.equal(rotuloDeSeveridade('medio'), 'Médio');
  assert.equal(rotuloDeSeveridade('alto'), 'Alto');
  assert.equal(rotuloDeSeveridade('atualizacao'), 'Atualização');
  assert.equal(rotuloDeSeveridade('novidade'), 'Novidade');
});

test('falha de rede vira recado de conexao, nao stack trace', () => {
  assert.equal(mensagemDeErro(new ApiError(0, 'Sem resposta de …')), 'Sem conexão com o servidor.');
});

test('404 e 500 tem recados proprios', () => {
  assert.equal(mensagemDeErro(new ApiError(404, 'x')), 'Não encontramos esse conteúdo.');
  assert.equal(mensagemDeErro(new ApiError(503, 'x')), 'O servidor teve um problema. Tente de novo em instantes.');
});

test('422 mostra a mensagem que a API mandou', () => {
  assert.equal(mensagemDeErro(new ApiError(422, 'Título é obrigatório.')), 'Título é obrigatório.');
});

test('erro que nao e ApiError ainda produz recado legivel', () => {
  assert.equal(mensagemDeErro(new Error('qualquer coisa')), 'Algo deu errado.');
});
