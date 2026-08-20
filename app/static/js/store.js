/**
 * Cache de sessão sobre a API (spec §5.2).
 *
 * O catálogo é pequeno (spec §2), então cada coleção é baixada inteira uma vez
 * por sessão e os joins acontecem em memória. Mutação invalida a coleção
 * afetada — ver INVALIDACOES.
 *
 * Reexporta derivacoes.js: um módulo de tela importa só este arquivo.
 */

import { api } from './api.js';

export * from './derivacoes.js';

const PREFIXO = 'laac:';
export const TTL_MS = 5 * 60 * 1000;

const memoria = new Map();
let armazenamentoResolvido;

function armazenamento() {
  if (armazenamentoResolvido !== undefined) return armazenamentoResolvido;
  try {
    const sonda = `${PREFIXO}sonda`;
    globalThis.sessionStorage.setItem(sonda, '1');
    globalThis.sessionStorage.removeItem(sonda);
    armazenamentoResolvido = globalThis.sessionStorage;
  } catch {
    armazenamentoResolvido = null;
  }
  return armazenamentoResolvido;
}

function ler(nome, agora) {
  const bruto = armazenamento()?.getItem(PREFIXO + nome);
  const envelope = bruto ? JSON.parse(bruto) : memoria.get(nome);
  if (!envelope) return null;
  return agora - envelope.carimbo > TTL_MS ? null : envelope.dados;
}

function gravar(nome, dados, agora) {
  const envelope = { carimbo: agora, dados };
  const store = armazenamento();
  if (store) {
    try {
      store.setItem(PREFIXO + nome, JSON.stringify(envelope));
      return;
    } catch {
      // Cota estourada: seguimos em memória, sem quebrar a tela.
    }
  }
  memoria.set(nome, envelope);
}

/** Devolve a coleção inteira, do cache ou da API. */
export async function colecao(nome, { agora = Date.now() } = {}) {
  const cacheada = ler(nome, agora);
  if (cacheada !== null) return cacheada;

  const dados = await api.listar(nome);
  gravar(nome, dados, agora);
  return dados;
}

export function invalidar(...nomes) {
  for (const nome of nomes) {
    armazenamento()?.removeItem(PREFIXO + nome);
    memoria.delete(nome);
  }
}

/** Que coleção cada mutação derruba (spec §5.2). */
export const INVALIDACOES = {
  biblioteca: ['biblioteca_usuario'],
  topico: ['topicos'],
  post: ['posts'],
  curtida: ['curtidas_avaliacoes'],
  avaliacao: ['avaliacoes'],
  relato: ['relatos_bug'],
  notificacao: ['notificacoes'],
};

/** Só para testes: esquece o cache e re-detecta o sessionStorage. */
export function _resetar() {
  memoria.clear();
  armazenamentoResolvido = undefined;
}
