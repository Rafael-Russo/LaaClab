/**
 * Transporte HTTP para a API Laravel (spec §5.1).
 *
 * O browser fala direto com a API — o Flask não proxia dado de domínio.
 * Este módulo só monta URL, serializa e traduz erro; nenhuma regra de
 * negócio mora aqui.
 */

export class ApiError extends Error {
  constructor(status, mensagem, errors = {}) {
    super(mensagem);
    this.name = 'ApiError';
    this.status = status;
    this.errors = errors;
  }
}

function raiz() {
  return (globalThis.LAAC?.apiBase ?? '').replace(/\/+$/, '');
}

async function pedir(metodo, caminho, corpo) {
  const url = `${raiz()}/api/${caminho}`;
  const cabecalhos = { Accept: 'application/json' };
  if (corpo !== undefined) cabecalhos['Content-Type'] = 'application/json';

  let resposta;
  try {
    resposta = await fetch(url, {
      method: metodo,
      headers: cabecalhos,
      body: corpo === undefined ? undefined : JSON.stringify(corpo),
    });
  } catch (erro) {
    throw new ApiError(0, `Sem resposta de ${url}: ${erro.message}`);
  }

  if (resposta.status === 204) return null;

  let dados = {};
  try {
    dados = await resposta.json();
  } catch {
    dados = {};
  }

  if (!resposta.ok) {
    throw new ApiError(resposta.status, dados.message ?? `HTTP ${resposta.status}`, dados.errors ?? {});
  }
  return dados;
}

export const api = {
  listar: (recurso) => pedir('GET', recurso),
  obter: (recurso, id) => pedir('GET', `${recurso}/${id}`),
  criar: (recurso, corpo) => pedir('POST', recurso, corpo),
  atualizar: (recurso, id, corpo) => pedir('PUT', `${recurso}/${id}`, corpo),
  remover: (recurso, id) => pedir('DELETE', `${recurso}/${id}`),
};
