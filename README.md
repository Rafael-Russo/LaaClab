# LaaCLab — Bugômetro

Plataforma de monitoramento de estabilidade de jogos (crash, bugs, stutter, FPS drop),
com biblioteca de jogos, comunidade (fórum), alertas e perfil do jogador.

Projeto **Django** servindo tanto o back-end quanto o front-end. As telas são
*shells* estáticos (HTML/CSS/JS) e obtêm seus dados via **endpoints JSON**
consumidos por `fetch`. Autenticação com **django-allauth**. A API de dados usa
**Django REST Framework**. O catálogo de jogos é populado a partir de uma base
real (**Steam store API**). Em produção, **nginx** faz de webserver na frente do
gunicorn.

## Arquitetura

```
Navegador ──HTML shell──> Django (web/views.py + templates)
    │
    ├─ fetch /api/...    ──> endpoints por tela (web/api.py) ─┐
    └─ fetch /api/v1/... ──> API CRUD DRF (web/rest.py)  ─────┤
                                                             ▼
                                       ORM (web/models.py) ──> MySQL
```

- `config/` — projeto Django (settings, urls, wsgi/asgi).
- `web/` — **módulo de visualização web** (o app):
  - `models.py` — domínio (Game, Genre, Alert, Topic/Reply, GameComment, LibraryEntry, UserProfile).
  - `views.py` — views que renderizam os shells (todas exigem login).
  - `api.py` — endpoints JSON por tela (401 em JSON quando não autenticado).
  - `services.py` — agregações derivadas (gráfico 24h, métricas, favoritos).
  - `rest.py` / `serializers.py` / `permissions.py` — API CRUD em `/api/v1/`.
  - `management/commands/` — `fetch_steam` (busca dados) e `seed` (popula o banco).
  - `fixtures/games_seed.json` — catálogo versionado gerado do Steam.
  - `templates/web/` + `static/web/` — telas e design system.
- `templates/account/` — telas de login/cadastro/logout (override do allauth).
- `deploy/` — `nginx.conf` (produção) e `entrypoint.sh` (container).
- `Dockerfile`, `docker-compose.yml` — containerização (app + MySQL).
- `.github/workflows/ci.yml` — pipeline de CI.

### Telas e endpoints por tela

| Tela            | Página          | Endpoint            |
|-----------------|-----------------|---------------------|
| Início          | `/`             | `/api/home/`        |
| Bugômetro       | `/bugometro/`   | `/api/bugometro/`   |
| Biblioteca      | `/biblioteca/`  | `/api/biblioteca/`  |
| Comunidade      | `/comunidade/`  | `/api/comunidade/`  |
| Alertas         | `/alertas/`     | `/api/alertas/`     |
| Perfil          | `/perfil/`      | `/api/perfil/`      |
| Detalhe do jogo | `/jogo/<slug>/` | `/api/jogo/<slug>/` |
| (compartilhado) | —               | `/api/me/`          |

### API CRUD (`/api/v1/`, DRF navegável)

Autenticação por sessão (o mesmo login das telas); escritas exigem CSRF.

| Recurso    | Rota                  | Escrita                              |
|------------|-----------------------|--------------------------------------|
| Jogos      | `/api/v1/games/`      | somente staff (catálogo)             |
| Gêneros    | `/api/v1/genres/`     | somente staff                        |
| Alertas    | `/api/v1/alerts/`     | somente staff                        |
| Tópicos    | `/api/v1/topics/`     | autenticado; edição pelo autor       |
| Respostas  | `/api/v1/replies/`    | autenticado; edição pelo autor       |
| Comentários| `/api/v1/comments/`   | autenticado; edição pelo autor       |
| Biblioteca | `/api/v1/library/`    | do próprio usuário                   |
| Perfil     | `/api/v1/me/`         | GET/PATCH do próprio perfil          |

Filtros úteis: `?search=`, `?ordering=-bug_score`, `?game=<slug>`, `?type=bug`, `?topic=<id>`.

## Desenvolvimento (local, sem Docker)

Requisitos: Python 3.12+. Sem `DATABASE_URL`, usa um SQLite local (nenhum
servidor de banco necessário).

```bash
py -3.12 -m venv .venv
.venv\Scripts\activate                 # Windows (source .venv/bin/activate no Linux/macOS)
pip install -r requirements.txt

python manage.py migrate
python manage.py fetch_steam           # (opcional) atualiza o fixture a partir do Steam
python manage.py seed                  # popula o catálogo + dados de demonstração
python manage.py runserver
```

Acesse http://127.0.0.1:8000. Faça login com o usuário de demonstração
**`gamer` / `gamerpass123`** (criado pelo `seed`) ou crie uma conta em
`/accounts/signup/`.

## Desenvolvimento com Docker (MySQL + app)

```bash
docker compose up --build
```

O container espera o MySQL, aplica migrations, roda o `seed` e sobe o servidor
de desenvolvimento em http://localhost:8000. Dados persistem no volume
`mysql_data`.

## Produção (nginx + gunicorn + MySQL)

A imagem `Dockerfile` roda gunicorn e faz `collectstatic` no start. Configure via
ambiente:

- `DATABASE_URL=mysql://usuario:senha@host:3306/laaclab`
- `DJANGO_DEBUG=0`, `DJANGO_SECRET_KEY=<novo>`, `DJANGO_ALLOWED_HOSTS=...`

Com `DEBUG=0` o Django **exige** um `DJANGO_SECRET_KEY` real (falha no boot caso
contrário) e ativa cookies seguros/HSTS. Ajuste `deploy/nginx.conf` (domínio e
caminhos) para servir na frente do gunicorn.

## CI

`.github/workflows/ci.yml` (GitHub Actions) roda em push/PR: lint (ruff),
checagem de migrations, testes contra um MySQL de serviço e build da imagem
Docker.

```bash
ruff check .            # lint
python manage.py test   # testes
```

## Convenções

- **Commits:** [Conventional Commits](https://www.conventionalcommits.org/) com
  mensagens enxutas, feitos de forma incremental.
- **Fonte:** o design usa *Motiva Sans Medium* (proprietária). O CSS cai para uma
  pilha de fontes do sistema; para fidelidade total, adicione o arquivo em
  `web/static/web/fonts/` e um `@font-face` em `styles.css`.
- As capas dos jogos guardam a URL real (Steam) com *fallback* em gradiente.
