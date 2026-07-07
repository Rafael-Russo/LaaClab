# P2 — Modularização em apps + moderação (design)

- **Data:** 2026-07-07
- **Status:** aprovado (direção), pendente de plano de implementação
- **Ordem:** implementar após P1. Ver [P1](2026-07-07-p1-catalogo-biblioteca-design.md).

## Objetivo

Quebrar o app monolítico `web` em **apps modulares e coesos**, com um app
**`core`** que gerencia **ativação/desativação de módulos** e centraliza
**grupos + permissões** do Django (com **fixtures** pré-definidas). Introduzir
**moderação** de fórum e de jogos/bugs baseada em grupos/permissões.

## Decisões (fechadas)

- Permissionamento via **Django Groups + Permissions** (nativo), junto com
  ativação/desativação de módulos no `core`.
- **Fixtures** com grupos e permissões pré-definidos.
- Um módulo = um app Django coeso; o `core` conhece e liga/desliga módulos.

## Arquitetura de apps

Refatorar `web` em:

| App          | Responsabilidade | Migra de `web` |
|--------------|------------------|-----------------|
| `core`       | base templates/shell, registro & ativação de módulos, grupos/permissões (fixtures), helpers compartilhados (`services` genéricos), autenticação/allauth glue | base.html, app.js, parte de settings/urls |
| `catalog`    | Game, Genre, LibraryEntry, ingestão (P1), Explorar, Meus Jogos | models de jogo/biblioteca, tasks, ingest |
| `community`  | Topic, Reply, GameComment, tela Comunidade, moderação de fórum | fórum |
| `alerts`     | Alert, tela Alertas | alerts |
| `accounts`   | UserProfile, tela Perfil e Configuração (P4) | profile |
| `bugs`       | Bug/BugReport (criados em **P3**), moderação de bugs | — (P3) |

> **Custo real:** mover models entre apps exige migrações cuidadosas
> (`SeparateDatabaseAndState` / `app_label`) ou, como o projeto é novo, um reset
> controlado de migrações. O plano de implementação deve escolher e detalhar a
> estratégia. O `AUTH_USER_MODEL` segue o `auth.User` padrão (FKs por string).

## Registro & ativação de módulos (`core`)

- Modelo `Module`: `key` (único, ex.: `community`), `name`, `enabled` (bool),
  `description`. Semeado por fixture com todos os módulos conhecidos.
- Gating: um *context processor* injeta os módulos ativos → a sidebar/nav só
  mostra os habilitados; um *mixin*/decorator barra as views de módulos desligados
  (404/redirect). Opcional: middleware para bloquear rotas de módulos off.
- Comando `modules --enable/--disable <key>` e admin para alternar.
- Ativação × permissão: um módulo desligado some para todos; um módulo ligado
  respeita as permissões por grupo abaixo.

## Papéis, grupos e permissões

Grupos (fixture `core/fixtures/groups.json` ou comando idempotente
`setup_permissions`):

| Grupo | Permissões (exemplos) |
|-------|------------------------|
| `Administrador` | todas (superset); gerencia módulos e usuários |
| `Moderador de Fórum` | ocultar/fixar/travar/remover `Topic`/`Reply`/`GameComment` |
| `Moderador de Jogos/Bugs` | aprovar/rejeitar/sinalizar `Game` e `Bug`; editar catálogo |
| `Usuário` (default) | criar tópicos/respostas/comentários; gerenciar a própria biblioteca |

- Permissões customizadas declaradas em `Meta.permissions` dos models
  (ex.: `can_moderate_forum`, `can_moderate_bugs`).
- DRF: classes de permissão checam `user.has_perm(...)`/pertinência a grupo
  (evoluem as atuais `IsAdminOrReadOnly`/`IsAuthorOrReadOnly`). Autor continua
  podendo editar o próprio conteúdo; moderador ganha superpoderes no módulo.

## Moderação — campos e ações

- Em `Topic`/`Reply`/`GameComment`: `is_hidden`, `is_locked` (só tópico),
  `is_pinned` (só tópico), `moderated_by`, `moderated_at`.
- Em `Game`: `is_published`/`status` (aprovado/sinalizado) para curadoria do
  catálogo; em `Bug` (P3): `status` (confirmado/rejeitado) + `moderated_by`.
- Endpoints de ação (DRF `@action`): `hide`/`unhide`, `lock`/`unlock`,
  `pin`/`unpin`, `approve`/`reject`/`flag` — gated por permissão.
- UI mínima in-app (botões de moderação visíveis só a quem tem permissão) +
  uso do Django admin para o resto.

## Testes

- Grupos/permissões criados por fixture; testes de que cada grupo tem/《não tem》
  as permissões certas.
- Ações de moderação: autor comum não modera; moderador do módulo modera; de
  outro módulo não.
- Ativação de módulo: módulo off some da nav e bloqueia rota; on respeita permissão.

## Fora de escopo

- O modelo `Bug` em si (definido em **P3**); aqui só entram os *hooks* de
  moderação que o consomem.
- Subtelas (P4).
