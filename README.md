# LaaC Lab — frontend Flask

Aplicação web do **Bugômetro LaaCLab**: catálogo de jogos, índice de
instabilidade por jogo, biblioteca pessoal, alertas e comunidade.

O Flask aqui é **fino de propósito**. Ele serve a shell HTML e cuida da
sessão; **nenhum dado de domínio passa por ele**. O browser busca tudo
direto de uma **API REST Laravel**, que vive em outro repositório
(`api-laravel`), através dos módulos ES em `app/static/js/`.

A única camada Python que fala com a API é `app/auth/service.py`, e só para
autenticar — porque a senha não pode transitar pelo JavaScript.

> **Nota de segurança, deliberada.** Com a API pública e o browser falando
> direto com ela, a sessão do Flask é uma **convenção de identidade, não uma
> fronteira de segurança**. Não escreva código que dependa dela para
> autorizar coisa alguma.

## Pré-requisitos

| Ferramenta | Versão | Para quê |
|---|---|---|
| Python | 3.10+ | a aplicação e o `pytest` |
| Node | 22+ | só `node --test`; **não** há build de assets |
| API Laravel | — | necessária para logar (ver abaixo) |

O piso do Node é 22 porque só a partir dessa versão o `--test` expande o glob
`tests_js/*.test.js` que o script de teste passa.

Bootstrap, Chart.js, Material Symbols e Inter estão **vendorados** em
`app/static/vendor/`. Não há CDN em runtime e não há passo de build.

## Instalação

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements-dev.txt   # Linux/macOS: .venv/bin/pip
cp .env.example .env
```

Edite o `.env`:

```
API_BASE_URL=http://localhost:8000   # raiz da API, sem barra final e sem /api
SECRET_KEY=troque-isto               # assina o cookie de sessão
API_TIMEOUT=5                        # segundos de espera pela API no login
```

O `.env` é lido no import de `app/config.py`, antes de a classe `Config`
consultar o ambiente. Sem `.env`, valem os padrões de `app/config.py` — que
servem para desenvolvimento e **não** para produção.

## Rodando

```bash
.venv/Scripts/flask --app wsgi run --debug
```

Abre em <http://localhost:5000/>. Toda rota de tela exige login, então a
primeira parada é `/entrar`.

### A API Laravel precisa estar de pé

O login não funciona sem ela. Do lado do Laravel são necessários:

1. **`POST /api/login`** — recebe `{email, senha}` e responde
   `200 {id, nome_usuario, email, nivel, avatar_url, ...}`, `401` para
   credencial errada, `422` para dados inválidos.
2. **CORS liberando a origem do Flask** para `api/*`
   (`supports_credentials: false`). Sem isso **nenhuma tela carrega**, porque
   é o browser que chama a API.

O cadastro reaproveita o `POST /api/usuarios` que já existe.

Nada disso é preciso para rodar os testes: **nenhum teste toca a rede.**

## Testes e lint

```bash
.venv/Scripts/pytest        # rotas, sessão, CSRF, cliente HTTP de auth
npm test                    # node --test: joins, regras derivadas, store, ui
.venv/Scripts/ruff check .  # line-length 100, regras E, F, I, UP, B
```

Os testes Python mockam a API com `responses`; os de JavaScript injetam um
`fetch` falso. Nenhum depende do repositório `api-laravel` estar de pé.

## Mapa do repositório

```
app/
├── config.py         # lê o .env e o ambiente
├── extensions.py     # Flask-Login e CSRF
├── auth/             # /entrar, /cadastrar, /sair — service.py fala com a API
├── telas/            # as 10 rotas de tela, só renderizam template
├── templates/        # base.html (shell), _nav.html, _level_card.html
└── static/
    ├── vendor/       # bootstrap, chart.js, material-symbols, inter
    ├── css/theme.css # paleta da marca sobre as variáveis do Bootstrap
    └── js/
        ├── api.js         # transporte HTTP + ApiError
        ├── derivacoes.js  # funções puras: joins e regras derivadas
        ├── store.js       # cache de sessão + invalidação por mutação
        └── ui.js          # vocabulário visual, estados de carga e erro
tests/     # pytest
tests_js/  # node --test
```

As telas propriamente ditas (Início, Biblioteca, BugoMetro, Comunidade,
Alertas, Perfil…) ainda são stubs: esta branch entrega a **fundação** —
shell, autenticação e camada de dados do cliente.
