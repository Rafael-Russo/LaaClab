# LaaCLab — Bugômetro

Plataforma de monitoramento de estabilidade de jogos (crash, bugs, stutter, FPS drop),
com biblioteca de jogos, comunidade, alertas e perfil do jogador.

Projeto **Django** servindo tanto o back-end quanto o front-end. As telas são
*shells* estáticos (HTML/CSS/JS) e obtêm seus dados via **endpoints JSON**
(`/api/...`) consumidos por `fetch`. Autenticação com **django-allauth**.
Em produção, **nginx** faz de webserver na frente do gunicorn.

> Os dados ainda são *mock* (`web/mock_data.py`) — "nada complexo por enquanto".
> Quando surgir um banco real, só `web/api.py` muda; o contrato JSON das telas continua igual.

## Arquitetura

```
Navegador ──HTML shell──> Django (views em web/views.py, templates em web/templates/web)
    │
    └──fetch /api/...──> Django (endpoints JSON em web/api.py) ──> web/mock_data.py
```

- `config/` — projeto Django (settings, urls, wsgi/asgi).
- `web/` — **módulo de visualização web** (o app). Páginas + endpoints + estáticos.
  - `views.py` — views que renderizam os shells (todas exigem login).
  - `api.py` — endpoints JSON (401 em JSON quando não autenticado).
  - `mock_data.py` — dados de exemplo.
  - `templates/web/` — `base.html` (sidebar + topbar) e uma página por tela.
  - `static/web/` — `css/styles.css` (design system), `js/app.js` (helpers) + um JS por tela.
- `templates/account/` — telas de login/cadastro/logout (override do allauth).
- `deploy/nginx.conf` — configuração de produção.
- `docs/mockups/` — imagens de referência das telas.

### Telas e endpoints

| Tela            | Página              | Endpoint                     |
|-----------------|---------------------|------------------------------|
| Início          | `/`                 | `/api/home/`                 |
| Bugômetro       | `/bugometro/`       | `/api/bugometro/`            |
| Biblioteca      | `/biblioteca/`      | `/api/biblioteca/`           |
| Comunidade      | `/comunidade/`      | `/api/comunidade/`           |
| Alertas         | `/alertas/`         | `/api/alertas/`              |
| Perfil          | `/perfil/`          | `/api/perfil/`               |
| Detalhe do jogo | `/jogo/<slug>/`     | `/api/jogo/<slug>/`          |
| (compartilhado) | —                   | `/api/me/`                   |

## Desenvolvimento

Requisitos: Python 3.12+.

```bash
# 1. Ambiente virtual
py -3.12 -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # Linux/macOS

# 2. Dependências
pip install -r requirements.txt

# 3. (opcional) variáveis de ambiente
copy .env.example .env            # Windows  (cp no Linux/macOS)

# 4. Banco (auth/sessões) + usuário
python manage.py migrate
python manage.py createsuperuser

# 5. Rodar
python manage.py runserver
```

Acesse http://127.0.0.1:8000 — você será redirecionado ao login. Crie uma conta
em `/accounts/signup/` ou use o superusuário.

## Produção (nginx + gunicorn)

```bash
python manage.py collectstatic --noinput
gunicorn config.wsgi:application --bind 127.0.0.1:8000 --workers 3
```

Ajuste `deploy/nginx.conf` (domínio e caminhos) e configure o `.env`
(`DJANGO_DEBUG=0`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_SECRET_KEY` novo, etc.).

## Convenções

- **Commits:** [Conventional Commits](https://www.conventionalcommits.org/) com
  mensagens enxutas (`feat(web): ...`, `chore: ...`).
- **Fonte:** o design usa *Motiva Sans Medium* (proprietária). O CSS cai para uma
  pilha de fontes do sistema; para fidelidade total, adicione o arquivo da fonte
  em `web/static/web/fonts/` e um `@font-face` em `styles.css`.
- As capas dos jogos são *placeholders* em gradiente (não distribuímos arte de terceiros).
