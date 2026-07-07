# P1 — Catálogo real em massa + biblioteca por usuário (design)

- **Data:** 2026-07-07
- **Status:** aprovado (design), pendente de plano de implementação
- **Sub-projeto:** P1 de 4 (ver "Decomposição" abaixo)

## Contexto

O LaaCLab hoje tem um catálogo pequeno (~26 jogos) semeado de um fixture, a tela
"Meus Jogos" cai para o catálogo inteiro quando o usuário não tem biblioteca, as
capas são placeholders em gradiente, e vários dados ainda são sintéticos. Este
sub-projeto torna o catálogo real e em massa, com imagens self-hosted, e vincula
a biblioteca ao usuário.

### Decomposição do pedido maior (contexto)

O pedido do usuário abrange 4 subsistemas independentes; este spec cobre **apenas P1**:

- **P1 (este doc)** — catálogo em massa + imagens + biblioteca por usuário + tela Explorar.
- **P2** — papéis & moderação (fórum e jogos/bugs).
- **P3** — identificação de bugs funcionais (scraping+embeddings e/ou agente no PC). Define o modelo `Bug` e substitui o `bug_score` falso.
- **P4** — subtelas complementares (detalhe aprofundado, thread de tópico, Históricos, Configuração).

## Objetivo e critérios de sucesso

1. Banco populado com **2.000–5.000 jogos** reais da Steam (via API), de forma
   **resumível** e sem inflar o git.
2. Capas **baixadas e self-hosted** em `media/`, exibidas no front (com fallback).
3. **"Meus Jogos"** lista **somente** a biblioteca do usuário autenticado, com
   estado vazio + CTA. Nada de fallback para o catálogo geral.
4. Nova tela **"Explorar"**: busca, filtro por gênero, ordenação, paginação e
   ações de adicionar/favoritar.
5. Mocks de catálogo removidos (fallback de biblioteca/favoritos; `TOPIC_COUNTS`
   sintético do `community.js`).
6. CI/testes seguem **offline e rápidos** com o seed pequeno; a massa é só via worker.

## Decisões (fechadas no brainstorm)

| Tema | Decisão |
|------|---------|
| Escala/fonte | ~2k–5k jogos via API da Steam, rankeados por popularidade (SteamSpy) |
| Imagens | Baixar e self-hostar em `media/covers/` (fallback: `cover_image` URL → gradiente) |
| Descoberta/adição | Tela nova **Explorar**; "Meus Jogos" estritamente do usuário |
| Pipeline | **Celery + Redis** (assíncrono, resumível, agendável) |
| Fixtures/CI | Seed pequeno (~26) versionado para CI/testes; massa só via worker |
| Disparo | Sob demanda por management command; Beat opcional, desligado por padrão |

## Arquitetura

```
web (Django)  ──enfileira──>  Redis (broker/result)  ──>  Celery worker  ──>  SteamSpy + Steam appdetails
   │                                                            │
   └──────────────── MySQL <───────── upsert ───────────────────┘
                     media/covers/ <──────── baixa capa ─────────┘
Celery Beat (opcional, off por padrão) ── agenda refresh ──> Redis
```

Serviços novos no `docker-compose.yml`: `redis`, `worker`, `beat` (atrás de um
profile). Redis é broker **e** result backend.

## Modelo de dados (`web/models.py`)

**`Game`** — novos campos:
- `cover_file = ImageField(upload_to="covers/", blank=True)` — capa self-hosted.
- `popularity = PositiveIntegerField(default=0)` — estimativa de *owners* (SteamSpy), usada para ordenar o catálogo.
- Mantém `cover_image` (URL de origem) e `cover` (gradiente) como fallbacks.
- Precedência de render: **`cover_file` → `cover_image` → gradiente**.

**`IngestCandidate`** (novo) — fila de trabalho resumível:
- `appid` (PositiveIntegerField, único)
- `name` (CharField, blank)
- `owners` (PositiveIntegerField, default 0) / `rank` (PositiveIntegerField, null)
- `status` (`pending` | `fetching` | `done` | `failed`)
- `attempts` (PositiveIntegerField, default 0)
- `last_error` (TextField, blank)
- `updated_at` (auto_now)
- Índice em `status`. Reprocessa só o que não está `done`.

**`LibraryEntry`** — inalterado no P1 (`user`, `game`, `favorite`, `added_at`).
Status/nota/horas ficam para P4.

**Mídia:** `MEDIA_ROOT = BASE_DIR/"media"`, `MEDIA_URL = "media/"`. Servido pelo
runserver em dev e por `location /media/` no nginx em prod; volume `media` no Docker.

## Pipeline de ingestão (`web/tasks.py`)

Fonte do ranking: **SteamSpy** endpoint `all` (páginas de ~1000 jogos ordenados
por *owners*, rate-limit ~1 req/60s). Dá appid + popularidade; a **appdetails**
da Steam enriquece (descrição, gêneros, capa).

Tasks:
- `refresh_applist(pages)` — chama SteamSpy, faz upsert de `IngestCandidate`
  (`pending`), grava `owners`/`rank`. Idempotente.
- `enqueue_pending(limit=None)` — dispara `ingest_game.delay(appid)` para cada
  candidato não-`done` (o kickoff/resume).
- `ingest_game(appid)` — marca `fetching`; chama appdetails; upsert do `Game`;
  **baixa a capa** para `media/covers/<slug>.jpg` (fallback: mantém
  `cover_image`/gradiente se falhar); marca `done` ou `failed` + `last_error` +
  incrementa `attempts`. Idempotente.

Robustez:
- `ingest_game` com `rate_limit="40/m"` (~1 req/1,5s) + `max_retries` com backoff
  para timeouts/HTTP 429. Worker com concorrência baixa respeita o limite.
- 2k–5k jogos ≈ 50–125 min em background, **resumível** (`enqueue_pending`
  retoma o que não está `done`).

Management commands:
- `ingest --pages N [--limit N] [--resume] [--sync]` — orquestra:
  `refresh_applist` → `enqueue_pending`. `--resume` pula o refresh e só reenfileira
  pendentes/falhos. `--sync` roda inline sem worker (para testes pequenos).
- `ingest_status` — imprime contagem por `status`.

Agendamento (opcional): task periódica no Beat (ex.: semanal) para reprocessar,
**desligada por padrão** via `INGEST_SCHEDULE_ENABLED=0`.

## API

- **Catálogo/Explorar:** reusa `GET /api/v1/games/` (DRF, já paginado,
  `PAGE_SIZE=20`) com `?search=`, `?genres__slug=`, `?ordering=-popularity`
  (ou `-bug_score`, `name`). Serializer inclui `cover_file`/`cover_image`.
- **Biblioteca por usuário:** `GET /api/v1/library/` (já é *owner-scoped*);
  `POST` adiciona (upsert idempotente), `PATCH /api/v1/library/<id>/` alterna
  `favorite`, `DELETE` remove.
- **Endpoint de tela `/api/biblioteca/`:** passa a retornar só a biblioteca do
  usuário (remoção do fallback em `services.user_library_cards`). A biblioteca de
  um usuário é tipicamente pequena → sem paginação neste endpoint.
- `services.user_favorite_cards`: remove fallback; retorna só favoritos do usuário
  (pode ser vazio → estado vazio no front).

## Frontend

- **Explorar** (`web/templates/web/explore.html` + `explore.js`): grid do catálogo
  com **capas reais**, busca, filtro por gênero, ordenação e paginação por
  **"Carregar mais"** (scroll infinito, usando `?page=`). Cada card: "Adicionar" /
  "Favoritar" → `POST /api/v1/library/`. Novo item "Explorar" na sidebar
  (`base.html`) + view/rota.
- **Meus Jogos** (`library.js`): lista só a biblioteca; **estado vazio** com CTA →
  Explorar; cada card com remover/favoritar.
- **Imagens** (`app.js`): helper de capa passa a usar `<img>` com
  `cover_file`→`cover_image` e cair para o gradiente `onerror`/ausência.
- **Home/Alertas**: tratam favoritos vazios graciosamente (sem quebrar layout).

## Infra & Docker

- `docker-compose.yml`: serviços `redis` (redis:7), `worker`
  (`celery -A config worker -l info`), `beat` (profile `beat`, off por padrão);
  volume `media`; `web`/`worker` dependem de `redis` (e `db`).
- `config/celery.py`: app Celery lendo `CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND`
  (default `redis://redis:6379/0`). `config/__init__.py` importa o app.
- `settings.py`: config Celery, `MEDIA_URL`/`MEDIA_ROOT`, Pillow.
- `deploy/nginx.conf`: `location /media/ { alias .../media/; }`.
- `.env.example`: `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `INGEST_SCHEDULE_ENABLED=0`.

## Dependências novas

`celery`, `redis` (cliente Python), `Pillow` (para `ImageField`).

## Fora de escopo do P1 (fica para outros sub-projetos)

- `bug_score` real, gráfico das 24h e métricas do Bugômetro → **P3** (permanecem
  como estão / sintéticos até lá).
- Papéis e moderação → **P2**.
- Detalhe do jogo aprofundado, thread de tópico, Históricos, Configuração → **P4**.

## Testes

- **Tasks:** `CELERY_TASK_ALWAYS_EAGER=True` + `requests` **mockado** (sem rede).
  Cobrir: `ingest_game` faz upsert do `Game`, baixa capa (mock), e no erro marca
  `failed`+`attempts`; `refresh_applist` cria candidatos; `--resume` reprocessa só
  não-`done`.
- **API/telas:** biblioteca estritamente do usuário (sem fallback), estado vazio,
  add/remove/favoritar, Explorar (busca/filtro/paginação), permissões inalteradas.
- **CI:** segue offline com seed pequeno; nenhuma chamada de rede nos testes.

## Runbook (execução manual da população)

Ver também `docs/runbooks/popular-catalogo.md`.

```bash
docker compose up -d db redis worker web
docker compose exec web python manage.py ingest --pages 5     # ~5k jogos
docker compose logs -f worker                                 # progresso
docker compose exec web python manage.py ingest_status        # contagem por status
docker compose exec web python manage.py ingest --resume      # retoma se cair
```

Local (sem Docker): subir Redis, `celery -A config worker -l info` num terminal,
`python manage.py ingest --pages 5` no outro. `--sync` roda inline.

## Riscos / notas

- Rate-limits (SteamSpy 1/min; Steam appdetails ~40/min): respeitados por
  `rate_limit` + backoff; ingestão longa mas resumível.
- Alguns appids não têm capa/descrição válidas (DLC, ferramentas): `ingest_game`
  filtra `type == "game"` e cai para fallback quando falta capa.
- Volume de mídia (~200–500MB): `media/` é gitignored; volume Docker persiste.
- Migração do `bug_score` falso é **fora de escopo** aqui; permanece provisório
  até o P3.
