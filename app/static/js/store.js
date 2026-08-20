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

/** Remove uma entrada do storage sem deixar a falha vazar. */
function descartar(store, nome) {
  try {
    store?.removeItem(PREFIXO + nome);
  } catch {
    // Nem remover foi possível; a memória ainda serve de cache.
  }
}

function envelopeGuardado(nome) {
  const store = armazenamento();
  const bruto = store?.getItem(PREFIXO + nome);
  if (!bruto) return memoria.get(nome) ?? null;

  try {
    return JSON.parse(bruto);
  } catch {
    // Dado corrompido (deploy anterior com outro formato, adulteração
    // manual): descarta e cai para a memória, em vez de derrubar a tela
    // com um SyntaxError vindo de dentro de `colecao`.
    descartar(store, nome);
    return memoria.get(nome) ?? null;
  }
}

function ler(nome, agora) {
  const envelope = envelopeGuardado(nome);
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
      // Cota estourada nesta chave. É preciso remover o valor velho: se ele
      // ficar, toda leitura futura o encontrará, verá que venceu, e re-buscará
      // a API para sempre — o valor fresco que estamos prestes a guardar em
      // memória nunca seria alcançado, porque `envelopeGuardado` só recorre à
      // memória quando o storage não tem nada sob a chave.
      descartar(store, nome);
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
