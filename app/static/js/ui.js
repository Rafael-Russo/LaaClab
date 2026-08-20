/**
 * Vocabulário visual compartilhado e estados de carga/erro (spec §5.5, §7.4).
 *
 * Os mapeadores no topo são puros e testados. Os construtores de DOM abaixo
 * seguem a convenção do projeto: validação manual, não teste unitário.
 */

import { ApiError } from './api.js';

const CLASSES_DE_STATUS = {
  estavel: 'laac-status-estavel',
  atencao: 'laac-status-atencao',
  instavel: 'laac-status-instavel',
  critico: 'laac-status-critico',
};

const ROTULOS_DE_STATUS = {
  estavel: 'Estável',
  atencao: 'Atenção',
  instavel: 'Instável',
  critico: 'Crítico',
};

const ROTULOS_DE_SEVERIDADE = {
  baixo: 'Baixo',
  medio: 'Médio',
  alto: 'Alto',
  critico: 'Crítico',
  instavel: 'Instável',
  atualizacao: 'Atualização',
  novidade: 'Novidade',
};

export function classeDeStatus(status) {
  return CLASSES_DE_STATUS[status] ?? 'laac-status-neutro';
}

export function rotuloDeStatus(status) {
  return ROTULOS_DE_STATUS[status] ?? '—';
}

export function rotuloDeSeveridade(severidade) {
  return ROTULOS_DE_SEVERIDADE[severidade] ?? '—';
}

/** Traduz a falha para algo que o usuário entenda (spec §5.5). */
export function mensagemDeErro(erro) {
  if (!(erro instanceof ApiError)) return 'Algo deu errado.';
  if (erro.status === 0) return 'Sem conexão com o servidor.';
  if (erro.status === 404) return 'Não encontramos esse conteúdo.';
  if (erro.status >= 500) return 'O servidor teve um problema. Tente de novo em instantes.';
  return erro.message;
}

// --- Construtores de DOM (validação manual) ---

function elemento(tag, classe, texto) {
  const no = document.createElement(tag);
  if (classe) no.className = classe;
  if (texto !== undefined) no.textContent = texto;
  return no;
}

export function estadoVazio({ icone = 'inbox', titulo, mensagem }) {
  const caixa = elemento('div', 'laac-surface text-center p-5');
  caixa.append(
    elemento('span', 'material-symbols-outlined fs-1 text-body-secondary', icone),
    elemento('p', 'h5 mt-2 mb-1', titulo),
    elemento('p', 'text-body-secondary mb-0', mensagem),
  );
  return caixa;
}

export function estadoDeErro(erro, aoTentarDeNovo) {
  const caixa = estadoVazio({
    icone: 'cloud_off',
    titulo: 'Não deu para carregar',
    mensagem: mensagemDeErro(erro),
  });
  const botao = elemento('button', 'btn btn-primary mt-3', 'Tentar de novo');
  botao.type = 'button';
  botao.addEventListener('click', aoTentarDeNovo);
  caixa.append(botao);
  return caixa;
}

export function badgeDeStatus(pontuacao, status) {
  const badge = elemento('span', `badge ${classeDeStatus(status)}`);
  // Trata `undefined` como ausência tanto quanto `null`: a API é desenvolvida
  // noutro repositório e pode omitir o campo em vez de mandá-lo nulo. Sem isso
  // o badge exibiria literalmente "undefined Estável" ao usuário.
  const semPontuacao = pontuacao === null || pontuacao === undefined;
  badge.textContent = semPontuacao
    ? rotuloDeStatus(status)
    : `${pontuacao} ${rotuloDeStatus(status)}`;
  return badge;
}

export function carregando() {
  const caixa = elemento('div', 'text-center p-5');
  const spinner = elemento('div', 'spinner-border text-primary');
  spinner.setAttribute('role', 'status');
  spinner.append(elemento('span', 'visually-hidden', 'Carregando…'));
  caixa.append(spinner);
  return caixa;
}

export function toast(mensagem) {
  let pilha = document.getElementById('laacToasts');
  if (!pilha) {
    pilha = elemento('div', 'toast-container position-fixed bottom-0 end-0 p-3');
    pilha.id = 'laacToasts';
    document.body.append(pilha);
  }
  const no = elemento('div', 'toast align-items-center text-bg-dark border-0');
  no.setAttribute('role', 'alert');
  no.append(elemento('div', 'toast-body', mensagem));
  pilha.append(no);
  new bootstrap.Toast(no, { delay: 4000 }).show();
  no.addEventListener('hidden.bs.toast', () => no.remove());
}

/**
 * Envolve o ciclo de vida de uma tela: spinner → conteúdo, ou o estado de
 * erro com "tentar de novo". É por aqui que o spec §5.5 vale para as 9 telas
 * sem cada uma reimplementar o tratamento.
 */
export async function montar(alvo, carregar, render) {
  alvo.replaceChildren(carregando());
  try {
    const dados = await carregar();
    alvo.replaceChildren();
    render(alvo, dados);
  } catch (erro) {
    alvo.replaceChildren(estadoDeErro(erro, () => montar(alvo, carregar, render)));
  }
}
