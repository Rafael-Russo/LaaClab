# Iniciação ao projeto — LAAC-LAB

Este documento é para quem está entrando no projeto agora. Ele cobre o que o
sistema é, como colocá-lo para rodar do zero, e as regras que o código segue —
incluindo o porquê de cada uma, porque várias parecem arbitrárias até você
saber o que elas evitam.

---

## O que é

O **LAAC-LAB (Bugômetro)** é uma plataforma de QA de jogos: pessoas se
cadastram, montam uma biblioteca de jogos, relatam bugs, confirmam relatos de
outras pessoas e acompanham a estabilidade de cada jogo através de uma
pontuação calculada a partir desses relatos.

O backend é uma **API REST em Flask**. O frontend é HTML, CSS e JavaScript
puros consumindo essa API, servido pelo próprio Flask a partir de
`view/paginas/` e `view/estatico/`.

---

## Como rodar, do zero

Você precisa de **Python 3.10**. A versão importa: o código usa `timezone.utc`
em vez de `datetime.UTC`, porque este último só existe a partir do 3.11.

```bash
python -m venv venv
./venv/Scripts/python.exe -m pip install -r requirements.txt

cp .env.example .env
./venv/Scripts/python.exe -m flask db upgrade
./venv/Scripts/python.exe -m flask seed-db
./venv/Scripts/python.exe wsgi.py
```

A API sobe em `http://127.0.0.1:5000`. Confirme com:

```bash
curl http://127.0.0.1:5000/saude
```

### O que o `seed-db` faz

Ele popula o banco com 26 jogos reais da Steam, tópicos, alertas, relatos de
bug e contas prontas:

| Conta | Senha | Papel |
|---|---|---|
| `gamer` | `gamerpass123` | conta comum |
| `moderador` | `moderador123` | administrador |
| `jogador01`…`jogador12` | `jogador123` | confirmam os relatos |

São credenciais públicas de demonstração, de propósito — o seed existe para
que você abra as telas e veja o sistema funcionando, não para rodar em
produção.

O pool de doze votantes não é enfeite: `confirmacoes` é **contagem derivada**
dos votos, recalculada por `VotoService` a cada voto, e há uma unique de
`(relato_id, usuario_id)`. Um seed que gravasse "128 confirmações" sem os
votos por trás veria esse número **cair para 1** no primeiro clique de quem
confirmasse o relato. Cada confirmação semeada tem um voto real de um usuário
real, então votar de novo faz o número subir.

Ele é **idempotente**: rodar de novo não duplica nada, então não custa nada
executar por reflexo. E os dados cobrem todas as categorias de tópico, todas
as severidades de alerta e as três faixas de estabilidade do bugômetro de
propósito — cada uma pinta um badge de cor diferente na tela, e com uma
amostra pobre as outras cores nunca apareceriam.

### Criando o primeiro administrador

Cadastrar jogo, criar alerta e moderar conteúdo exigem privilégio de
administrador — eram operações do painel administrativo do sistema anterior. O
registro pela API sempre cria conta comum, e **não existe rota que conceda
privilégio a partir do nada**: qualquer rota capaz disso seria uma rota capaz
de ser abusada.

Se você rodou o `seed-db`, já tem um: a conta `moderador`. Num banco que
não foi semeado, o primeiro admin nasce por linha de comando, que exige acesso
ao servidor — a credencial certa para essa operação:

```bash
# registre uma conta normalmente pela API, depois:
./venv/Scripts/python.exe -m flask promover <nome_usuario>
```

Depois do primeiro, um admin promove outro pela API, com
`PUT /api/v1/usuarios/<id>` mandando `{"is_admin": true}`.

**Sem um admin, o catálogo inteiro é somente-leitura.** Se você subir a API
numa base nova e não conseguir cadastrar um jogo, é isto.

### Rodando os testes

```bash
./venv/Scripts/python.exe -m pytest tests/ -q
./venv/Scripts/python.exe tools/verificar_camadas.py
./venv/Scripts/python.exe tools/verificar_casca.py
```

Os três precisam passar. O segundo é explicado abaixo. O terceiro compara
byte a byte a casca (cabeçalho, navegação, rodapé) copiada em cada uma das
páginas de `view/paginas/` — sem `{% extends %}` nem injeção por JS, cada
página chega pintada, e uma cópia que diverge silenciosamente só aparece
depois, na tela.

---

## A arquitetura, e por que ela é assim

O projeto tem uma cadeia de camadas obrigatória:

```
Tela → API Flask → Controller → Service → Model/Repository → Banco
```

Isso se traduz em três regras:

| Camada | Pode | Não pode |
|---|---|---|
| `app/controllers/` | Ler a requisição, chamar o Service, escolher o status HTTP | Tocar `db.session`, importar model ou repositório |
| `app/services/` | Regra de negócio, autorização, composição | Importar `flask`, `flask_jwt_extended` ou `app.extensions` |
| `app/repositories/` | `db.session`, `db.select`, `db.paginate` | — é o único lugar que fala com o banco |

**Essas regras não dependem de você lembrar delas.** O
`tools/verificar_camadas.py` varre o código e falha se alguma for violada; ele
roda também dentro do `pytest`, então uma violação quebra a suíte.

Ele ignora strings e comentários antes de varrer — senão a própria docstring
que explica a regra viraria uma violação dela.

### Por que a autorização mora no Service

Porque foi tentado do outro jeito e não funcionou. Quando o `criar()` recebia
só o `usuario_id` — um inteiro — não dava para checar privilégio, e a checagem
migrou naturalmente para o Controller. Espalhar autorização pelos controllers é
exatamente o que essa camada existe para evitar, então a assinatura mudou para
receber o usuário inteiro.

Se você precisar autorizar algo, o lugar é `ServicoBase._autorizar_escrita` ou
`_autorizar_criacao`. Nunca no Controller.

### `app/composicao.py`

É o *composition root*: o único lugar autorizado a conhecer as três camadas ao
mesmo tempo, para montar Repository → Service e entregar ao Controller. Ele
fica **fora** de `app/controllers/` de propósito — se morasse lá, a guarda
acusaria violação.

É também onde cada Service é configurado: quem tem dono, quem exige admin,
quem tem conteúdo moderável.

---

## Convenções

### Idioma

Português em models, colunas, rotas e chaves JSON. `usuarios`, `relatos_bug`,
`pontuacao`, `criado_em`.

**Com uma exceção deliberada:** os valores de `nivel`
(`critical`/`warning`/`stable`) e os nomes de ícone (`wifi`/`alert`/`check`)
ficam em inglês, porque são sufixo de classe CSS e chave de dicionário no
JavaScript. Traduzi-los obrigaria a reescrever o CSS sem ganho nenhum.

### Contrato de erro

Sempre JSON UTF-8, nunca HTML, nunca redirect.

| Status | Quando |
|---|---|
| 401 | Token ausente, expirado ou inválido |
| 403 | Autenticado, mas não é dono nem admin |
| 404 | Recurso não encontrado |
| 409 | Conflito com o estado existente (duplicidade) |
| 422 | Dados inválidos |

**Token ausente responde 401, nunca 403.** O frontend reage ao status, e só o
401 dispara o redirecionamento para o login — um 403 deixaria a pessoa presa
numa tela quebrada.

### Paginação

```json
{ "itens": [], "pagina": 1, "por_pagina": 20, "total": 137, "paginas": 7,
  "proxima": "/api/v1/jogos?pagina=2&por_pagina=20", "anterior": null }
```

`proxima` e `anterior` são caminhos relativos e **preservam os demais
parâmetros da consulta** — sem isso, seguir o link perderia a ordenação e a
página 2 voltaria à ordem padrão.

O teto de `por_pagina` é 100. Para composição interna que precisa de tudo, use
`ServicoBase.listar_todos()`, que não tem teto — o teto existe para proteger
contra `?por_pagina=` vindo do cliente, e composição interna não vem do
cliente.

### Ordenação

A allowlist de ordenação **falha fechada**: um repositório que não declare
quais campos aceita não aceita nenhum. Isso impede `?ordenar_por=senha_hash`.

O desempate por `id` acompanha a direção do campo. Com `-criado_em` e
timestamps empatados, um `id ASC` fixo devolveria o registro mais antigo
primeiro — o oposto de "mais recente primeiro".

### Moderação

Conteúdo com `oculto = true` some das listagens para quem não é admin, e o
`obter` responde **404** (não 403) para não revelar que existe.

Moderação sobrepõe posse: uma vez oculto, nem o autor edita. Senão ele
reescreveria o conteúdo escondido e mascararia o motivo da moderação.

---

## Estrutura

```
app/
├── __init__.py        application factory
├── cli.py             linha de comando (flask promover, flask seed-db)
├── composicao.py      composition root
├── errors.py          exceções de domínio e a tradução delas para HTTP
├── extensions.py      db, migrate, jwt
├── models/            22 tabelas
├── repositories/      único lugar que fala com o banco
├── schemas/           contratos de entrada e saída (marshmallow puro)
├── services/          regra de negócio
├── controllers/       só HTTP
└── seed.py            dados de demonstração (infra de CLI, não é Service)
migrations/            versionamento do schema
tests/                 444 testes
tools/                 verificar_camadas.py, verificar_casca.py
view/
├── paginas/           as 11 páginas HTML servidas pelo Flask (rotas em web_controller.py)
└── estatico/          css e js que essas páginas consomem
dados/jogos_steam.json 26 jogos reais da Steam, matéria-prima do seed
```

---

## O que existe e o que não existe

**Existe:** autenticação JWT (access de 30 min, refresh de 7 dias), CRUD de 18
recursos, as fórmulas do bugômetro portadas do sistema anterior, os nove
endpoints de tela (os oito de antes mais `GET /telas/explorar`), e o **frontend**
completo — as onze telas (início, biblioteca, bugômetro, jogo, alertas,
comunidade, perfil, login, registro, explorar, configuração), servidas pelo
próprio Flask a partir de `view/paginas/` e `view/estatico/`, sem servidor
separado.

A tela **Explorar** tem busca sem acento (coluna `nome_busca`), ordenação por
pontuação (join com `bugometro_status`) e filtro por gênero. A tela
**Configuração** troca a senha via `POST /api/auth/senha`: além de validar a
senha atual, isso sobe a `versao_sessao` do usuário e devolve tokens novos.
Todo refresh token emitido *antes* da troca passa a responder 401 na próxima
renovação — mesmo sem ter expirado — porque `token_in_blocklist_loader`
compara a `versao_sessao` carimbada no token com a atual; o endpoint devolve
tokens novos na mesma resposta para a pessoa não ser deslogada pela própria
troca.

**Não existe ainda:**

- As telas de **Notificações** e **Históricos**.
- **Upload de imagem de capa.** Capas vêm por URL ou pelo gradiente gerado.

---

## Coisas que vão te confundir se ninguém avisar

**O gráfico de 24 horas do bugômetro é dado sintético.** Ele não consulta o
banco e não olha o relógio — reproduz exatamente o comportamento do sistema
anterior. Histórico real depende da tabela `historico_bug`, que ninguém
popula ainda.

**`atualizado_em` não é "quando o jogo foi atualizado".** É carimbo técnico de
escrita da linha. A tela usa `data_lancamento`, que é `String(60)` livre e sai
do Service exatamente como foi gravado — o seed grava o formato da Steam
(`"27 out. 2022"`), não `DD/MM/YYYY`. Quem grava é responsável pelo formato.

**Um relato crítico confirmado com 20+ confirmações vale 105 pontos sozinho** e
estoura o teto de 100. É o comportamento do sistema anterior, preservado de
propósito.

**Rotas que respondem 405 não estão quebradas.** `POST /api/v1/usuarios` e
`PUT /api/v1/votos-bug/<id>` foram desligadas porque não podiam fazer nada
útil: registro é `/api/auth/registro`, e um voto não tem campo editável.

---

## Onde estão as decisões

O documento de especificação e o plano de implementação estão em `docs/`, que
é **ignorado pelo git** por decisão do time — eles existem apenas na máquina de
quem os escreveu. Se você precisar deles, peça.

Este arquivo é versionado justamente por isso: é o que sobrevive.
