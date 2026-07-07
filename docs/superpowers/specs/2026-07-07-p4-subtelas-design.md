# P4 — Subtelas complementares (design)

- **Data:** 2026-07-07
- **Status:** aprovado (escopo), pendente de plano de implementação
- **Ordem:** implementar após P3. Ver [P1](2026-07-07-p1-catalogo-biblioteca-design.md), [P2](2026-07-07-p2-modularizacao-moderacao-design.md), [P3](2026-07-07-p3-deteccao-bugs-design.md).

## Objetivo

Completar as telas não-principais que dependem dos dados reais de P1–P3.
Quatro subtelas (todas no escopo).

## 1. Detalhe do jogo aprofundado

- Rota atual `/jogo/<slug>/` expandida com **abas**: *Sobre* | *Bugs & Alertas* |
  *Comunidade*.
  - *Sobre*: dados do catálogo (P1), capa real, gêneros, links.
  - *Bugs & Alertas*: lista de `Bug` reais (P3) + `Alert` do jogo; usuário pode
    **reportar bug** (P3) e ver severidade/status; moderador vê ações (P2).
  - *Comunidade*: tópicos do jogo + atalho para novo tópico (P1/P2).
- Ações do usuário: adicionar/favoritar na biblioteca (P1), reportar/confirmar
  bug (P3), comentar.
- Endpoint: estende `/api/jogo/<slug>/` (abas montadas por `fetch` às APIs REST).

## 2. Thread de tópico (responder)

- Nova rota `/comunidade/topico/<id>/` → tópico + lista de `Reply` + **compositor
  de resposta** (usa `POST /api/v1/replies/`).
- Da tela Comunidade, clicar um tópico abre a thread.
- Moderação (P2): ocultar/travar/fixar/remover visível a moderador de fórum;
  tópico travado desabilita o compositor.
- Endpoint de leitura: `/api/topico/<id>/` (tópico + replies paginadas) ou uso
  direto de `/api/v1/topics/<id>/` + `/api/v1/replies/?topic=<id>`.

## 3. Históricos

- Nova rota `/historicos/` (item já existe na sidebar) → evolução do `bug_score`
  e alertas por jogo ao longo do tempo.
- Fonte: `GameScoreSnapshot` (definido em P3), capturado periodicamente por
  Celery Beat. Substitui o gráfico sintético por série temporal **real**.
- Filtros: por jogo (favoritos/biblioteca) e janela (7d/30d).
- Endpoint: `/api/historicos/?game=<slug>&range=30d`.

## 4. Configuração (perfil/conta)

- Nova rota `/configuracao/` (item "Configuração" da sidebar) com seções:
  - *Perfil*: editar `handle`/`bio`/`avatar_color` via `PATCH /api/v1/me/`.
  - *Conta*: e-mail/senha via fluxos do **allauth** (reset/change password).
  - *Preferências*: tema (persistir server-side no `UserProfile`, ex.:
    `theme`), notificações (flag simples).
- App `accounts` (P2) hospeda perfil + configuração.

## Dependências

- **P1**: catálogo/biblioteca/imagens reais.
- **P2**: apps modulares (`community`, `accounts`, `bugs`), permissões de
  moderação, ativação de módulos.
- **P3**: `Bug`/`BugReport`, `GameScoreSnapshot`, `bug_score` real.

## Testes

- Detalhe: abas carregam bugs/alertas/tópicos reais; reportar bug cria `Bug`.
- Thread: listar replies, responder, tópico travado bloqueia resposta;
  moderador modera.
- Históricos: série temporal a partir de snapshots (fixtures determinísticas).
- Configuração: PATCH de perfil respeita campos read-only; troca de tema persiste.

## Fora de escopo

- Novos sistemas de dados (todos vêm de P1–P3); P4 é primariamente **UI/telas**
  sobre o que já existe.
