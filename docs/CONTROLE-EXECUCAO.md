# Controle de Execução — LaaCLab

Documento **vivo** de acompanhamento da implementação dos sub-projetos P1–P4.
Rastreia status, testes automatizados, **testes manuais com validação do
usuário**, e correções/ações.

## Como este doc é usado

- Atualizado a cada entrega/correção durante a implementação.
- **Testes manuais** são executados **pelo usuário** posteriormente; ele reporta
  os resultados e este doc é atualizado (validado/reprovado) + ações tomadas.
- Cada sub-projeto tem seu **spec** (design) e, quando entra em implementação,
  seu **plano** detalhado.

### Legenda

- **Status:** `Planejado` · `Em progresso` · `Implementado` · `Correção pendente` · `Bloqueado`
- **Testes automatizados:** `n/a` · `pendente` · `passou` · `falhou`
- **Testes manuais (usuário):** `n/a` · `aguardando usuário` · `validado` · `reprovado`

## Roadmap

Implementação na ordem **P1 → P2 → P3 → P4** (specs já definidos):

| Fase | Spec | Status |
|------|------|--------|
| P1 — Catálogo + biblioteca | [spec](superpowers/specs/2026-07-07-p1-catalogo-biblioteca-design.md) · [runbook](runbooks/popular-catalogo.md) | Planejado |
| P2 — Modularização + moderação | [spec](superpowers/specs/2026-07-07-p2-modularizacao-moderacao-design.md) | Planejado |
| P3 — Detecção de bugs | [spec](superpowers/specs/2026-07-07-p3-deteccao-bugs-design.md) | Planejado |
| P4 — Subtelas | [spec](superpowers/specs/2026-07-07-p4-subtelas-design.md) | Planejado |

## Baseline já implementado (sessões anteriores)

Contexto do que já existe e está verde (não faz parte de P1–P4):

- Projeto Django + allauth; 7 telas (shells + endpoints JSON).
- API CRUD DRF em `/api/v1/` (games, genres, alerts, topics, replies, comments, library, me).
- Endpoints de tela lendo do banco; fórum com escrita (tópico/comentário) + CSRF.
- MySQL via `DATABASE_URL` (fallback SQLite); seed pequeno da Steam; Docker (web+mysql); CI (ruff+testes+build).
- **12 testes** automatizados passando; ruff limpo.

---

## P1 — Catálogo em massa + biblioteca por usuário

| # | Item | Status | Testes auto | Testes manuais (usuário) | Notas/correções |
|---|------|--------|-------------|--------------------------|-----------------|
| 1 | Deps (celery, redis, Pillow) + settings (Celery, MEDIA) | Planejado | pendente | n/a | — |
| 2 | `Game.cover_file`/`popularity` + `IngestCandidate` + migração | Planejado | pendente | n/a | — |
| 3 | `config/celery.py` + wiring do app | Planejado | pendente | n/a | — |
| 4 | Tasks `refresh_applist`/`enqueue_pending`/`ingest_game` (rate-limit/retry) | Planejado | pendente | n/a | — |
| 5 | Comandos `ingest` / `ingest_status` | Planejado | pendente | aguardando usuário | via runbook |
| 6 | Download de capas → `media/covers/` + fallback | Planejado | pendente | aguardando usuário | — |
| 7 | Tela **Explorar** (busca/filtro/paginação/adicionar) | Planejado | pendente | aguardando usuário | — |
| 8 | **Meus Jogos** por usuário (sem fallback) + estado vazio + remover/favoritar | Planejado | pendente | aguardando usuário | — |
| 9 | Imagens no front (`cover_file`→`cover_image`→gradiente) | Planejado | pendente | aguardando usuário | — |
| 10 | Remover mocks de catálogo (`TOPIC_COUNTS`, fallbacks) | Planejado | pendente | n/a | — |
| 11 | Compose: `redis`+`worker`+`beat`(off)+volume `media`; nginx `/media/` | Planejado | pendente | aguardando usuário | — |
| 12 | Testes (tasks eager+mock; API biblioteca/Explorar) | Planejado | pendente | n/a | — |
| 13 | Runbook de população validado | Planejado | n/a | aguardando usuário | [runbook](runbooks/popular-catalogo.md) |

## P2 — Modularização + moderação

| # | Item | Status | Testes auto | Testes manuais (usuário) | Notas |
|---|------|--------|-------------|--------------------------|-------|
| 1 | Split de `web` em `core`/`catalog`/`community`/`alerts`/`accounts` (+ migrações) | Planejado | pendente | n/a | detalhar estratégia no plano |
| 2 | `core`: modelo `Module` + ativação/desativação + nav gating | Planejado | pendente | aguardando usuário | — |
| 3 | Grupos + permissões (fixtures) + comando `setup_permissions` | Planejado | pendente | n/a | — |
| 4 | Campos/ações de moderação (fórum e jogos/bugs) + DRF perms | Planejado | pendente | aguardando usuário | — |

## P3 — Detecção de bugs (faseado)

| # | Item | Status | Testes auto | Testes manuais (usuário) | Notas |
|---|------|--------|-------------|--------------------------|-------|
| 1 | App `bugs`: `Bug`/`BugReport`/`BugVote`/`BugSignal`/`GameScoreSnapshot` | Planejado | pendente | n/a | — |
| 2 | Fase 3a: reports+votos da comunidade | Planejado | pendente | aguardando usuário | — |
| 3 | `bug_score` real (agregação) — remove o falso | Planejado | pendente | aguardando usuário | — |
| 4 | Fase 3b: scraping + embeddings (spike antes) | Planejado | pendente | aguardando usuário | itens em aberto no spec |
| 5 | Fase 3c: agente no PC | Planejado (só design) | n/a | n/a | mini-RFC futuro |

## P4 — Subtelas

| # | Item | Status | Testes auto | Testes manuais (usuário) | Notas |
|---|------|--------|-------------|--------------------------|-------|
| 1 | Detalhe do jogo aprofundado (abas) | Planejado | pendente | aguardando usuário | — |
| 2 | Thread de tópico (responder) | Planejado | pendente | aguardando usuário | — |
| 3 | Históricos (série real via snapshots) | Planejado | pendente | aguardando usuário | — |
| 4 | Configuração (perfil/conta/preferências) | Planejado | pendente | aguardando usuário | — |

---

## Pendências de validação manual (fila do usuário)

_Preenchido conforme os itens ficam prontos. O usuário testa e reporta; eu atualizo._

- _(nada pronto para teste manual ainda — P1 em planejamento)_

## Log de execução

| Data | Evento |
|------|--------|
| 2026-07-07 | Specs P1–P4 e este doc de controle criados. Implementação começa por P1. |

## Correções / ações

_(registrar aqui bugs encontrados em testes — auto ou manuais — e as ações tomadas)_
