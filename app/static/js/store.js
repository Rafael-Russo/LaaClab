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
/**
 * Requisições em voo, por nome de coleção.
 *
 * Sem isto, dois `await colecao('jogos')` concorrentes disparam dois GETs da
 * coleção inteira: o cache só é escrito quando a primeira resposta chega, e
 * até lá toda chamada vê um miss. A tela de Início compõe seis coleções em
 * painéis diferentes (spec §6), então isso acontece já na primeira tela.
 */
const emVoo = new Map();
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

/** Devolve a coleção inteira, do cache, de uma requisição em voo, ou da API. */
export async function colecao(nome, { agora = Date.now() } = {}) {
  const cacheada = ler(nome, agora);
  if (cacheada !== null) return cacheada;

  const jaPedida = emVoo.get(nome);
  // Quem cai aqui recebe a mesma instância do array com que `jaPedida` vai
  // resolver — não uma cópia. Antes da deduplicação, cada leitura do cache
  // vinha de um `JSON.parse` novo e era segura para mutar; agora, uma tela
  // que ordene ou altere esse array no lugar (em vez de operar sobre uma
  // cópia, como `derivacoes.js` faz com `.slice().sort()`) corrompe a visão
  // de toda chamada concorrente que aguarda a mesma promessa.
  if (jaPedida) return jaPedida;

  const promessa = api
    .listar(nome)
    .then((dados) => {
      gravar(nome, dados, agora);
      return dados;
    })
    .finally(() => {
      // Só apaga se a entrada ainda for esta. Um `invalidar()` no meio do voo
      // remove a entrada e a chamada seguinte registra outra promessa; apagar
      // por nome derrubaria a nova.
      if (emVoo.get(nome) === promessa) emVoo.delete(nome);
    });

  emVoo.set(nome, promessa);
  return promessa;
}

export function invalidar(...nomes) {
  for (const nome of nomes) {
    armazenamento()?.removeItem(PREFIXO + nome);
    memoria.delete(nome);
    // A requisição em voo foi disparada antes da mutação: seu resultado já
    // nasce velho e não pode ser reaproveitado por quem chegar depois.
    emVoo.delete(nome);
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
  emVoo.clear();
  armazenamentoResolvido = undefined;
}
