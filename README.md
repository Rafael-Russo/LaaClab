# LAAC-LAB

Membros:
Clara Santa Bárbara Utsch, 22400109
Luís Henrique Rocha Brandão, 22402284
Arthur Mariano Gonçalves Barroso, 22400567
Arthur Assis dos Santos, 22402209
Aureo Henrique Badaró de Carvalho, 22400273
--------------------------------------------------------------------------
Stack utilizada no projeto, separando frontend, backend e banco de dados;

FRONT END -
HTML / CSS / C#

BACKEND - 
Python 3.12
SimpleJWT
Docker + Docker Compose
Redis
Celery
Brevo (SMTP)
drf-spectacular (Swagger)
python-decouple
Gunicorn

BANCO DE DADOS -
PostgreSQL
SQLite3
MYSQL / DBEAVER

IDES: 
POSTMAN
CURSOR / VISUAL STUDIO 
D BEAVER 
MYSQL 

-----------------------------------------

## Sobre o sistema

O **LAAC_LAB (Bugômetro)** é uma plataforma de QA/game testing: usuários se
cadastram, cadastram jogos em um catálogo e reportam bugs, avaliações e
métricas de qualidade sobre eles. O backend ativo do projeto é a API REST em
**Flask + SQLAlchemy** (`api-flask-laaclab/`); o `frontend/login/` é a
aplicação Flask que renderiza as telas e consome essa API via HTTP.

## CRUD implementado (Models, rotas e telas)

A API `api-flask-laaclab` já expõe CRUD completo (Model → Schema →
Blueprint/rota) para todas as 18 entidades do domínio — ver a tabela de
rotas em [`api-flask-laaclab/README.md`](api-flask-laaclab/README.md).

Nesta etapa, o **frontend (`frontend/login/`)** passou a consumir essa API
(em vez de acessar banco local diretamente) e ganhou as telas de
cadastrar/listar/editar/excluir para as models principais:

| Model     | Rotas da API consumidas                                            | Telas no frontend                                                             |
|-----------|----------------------------------------------------------------------|--------------------------------------------------------------------------------|
| `Usuario` | `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/usuarios`, `GET/PUT/DELETE /api/usuarios/<id>` | `/registro`, `/login`, `/usuarios` (listar), `/perfil` (ver), `/perfil/editar`, `/perfil/excluir` |
| `Jogo`    | `GET /api/jogos`, `GET /api/jogos/<id>`, `POST /api/jogos`, `PUT /api/jogos/<id>`, `DELETE /api/jogos/<id>` | `/jogos` (listar), `/jogos/<id>` (ver), `/jogos/novo` (cadastrar), `/jogos/<id>/editar`, `/jogos/<id>/excluir` |

Escrita (cadastrar/editar/excluir jogos, editar/excluir o próprio perfil)
exige estar autenticado — o token JWT retornado pelo login é guardado na
sessão do Flask e enviado como `Authorization: Bearer <token>` em cada
chamada à API (ver `frontend/login/api_client.py`).

## Como executar o projeto

O projeto tem **dois servidores Flask** rodando ao mesmo tempo: a API e o
frontend.

### 1. API (`api-flask-laaclab/`) — porta 5000

```powershell
cd api-flask-laaclab
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
flask init-db    # cria as tabelas
flask seed-db    # (opcional) popula dados de exemplo
python wsgi.py   # API em http://127.0.0.1:5000
```

### 2. Frontend (`frontend/login/`) — porta 5001

Em outro terminal, com a API já rodando:

```powershell
cd frontend/login
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py    # telas em http://127.0.0.1:5001
```

Por padrão o frontend chama a API em `http://127.0.0.1:5000`. Para apontar
para outro endereço, defina a variável de ambiente `API_BASE_URL` antes de
rodar `python app.py`.

Fluxo básico: crie uma conta em `/registro`, faça login em `/login` e use o
menu no topo para acessar **Jogos** (catálogo, com cadastro/edição/exclusão)
e **Usuários**/**Meu perfil**.
