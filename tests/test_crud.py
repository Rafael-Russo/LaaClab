import pytest


def _registrar(cliente, nome, admin=False):
    corpo = cliente.post(
        "/api/auth/registro",
        json={
            "nome_usuario": nome,
            "email": f"{nome}@l.dev",
            "senha": "senha123",
        },
    ).get_json()

    if admin:
        from app.extensions import db
        from app.models import Usuario

        usuario = db.session.get(Usuario, corpo["usuario"]["id"])
        usuario.is_admin = True
        db.session.commit()

    return corpo


def _id_do_token(cabecalho):
    """Lê o subject direto do JWT, sem depender de rota.

    `/api/v1/eu` só existe a partir da tarefa dos endpoints de tela;
    usá-lo aqui obrigaria esta tarefa a inventar o endpoint antes da
    hora.
    """
    import base64
    import json

    corpo = cabecalho["Authorization"].split()[1].split(".")[1]
    corpo += "=" * (-len(corpo) % 4)
    return int(json.loads(base64.urlsafe_b64decode(corpo))["sub"])


@pytest.fixture
def cabecalho(cliente, app):
    """Conta ADMINISTRADORA.

    A maioria dos testes deste arquivo exercita o catálogo (jogos,
    gêneros, alertas), e escrever nele exige admin — era operação do
    Django admin antes da migração. Para testar privilégio, use
    `cabecalho_comum`.
    """
    corpo = _registrar(cliente, "gamer", admin=True)
    return {"Authorization": f"Bearer {corpo['token_acesso']}"}


@pytest.fixture
def cabecalho_admin(cabecalho):
    """Apelido explícito, para os testes em que o privilégio é o assunto."""
    return cabecalho


@pytest.fixture
def cabecalho_comum(cliente, app):
    """Conta recém-registrada, sem privilégio nenhum."""
    corpo = _registrar(cliente, "novato")
    return {"Authorization": f"Bearer {corpo['token_acesso']}"}


def test_criar_exige_autenticacao(cliente):
    resposta = cliente.post("/api/v1/jogos", json={"nome": "Hades"})
    assert resposta.status_code == 401
    assert resposta.get_json() == {"erro": "Autenticação necessária."}


def test_criar_devolve_201_com_o_recurso(cliente, cabecalho):
    resposta = cliente.post("/api/v1/jogos", json={"nome": "Hades"}, headers=cabecalho)
    assert resposta.status_code == 201
    assert resposta.get_json()["nome"] == "Hades"


def test_criar_sem_campo_obrigatorio_devolve_422(cliente, cabecalho):
    resposta = cliente.post("/api/v1/jogos", json={}, headers=cabecalho)
    assert resposta.status_code == 422
    assert "nome" in resposta.get_json()["erros"]


def test_criar_com_campo_desconhecido_devolve_422(cliente, cabecalho):
    resposta = cliente.post(
        "/api/v1/jogos", json={"nome": "X", "id": 9}, headers=cabecalho
    )
    assert resposta.status_code == 422


def test_listar_devolve_envelope_em_portugues(cliente, cabecalho):
    for indice in range(3):
        cliente.post(
            "/api/v1/jogos", json={"nome": f"Jogo {indice}"}, headers=cabecalho
        )
    corpo = cliente.get("/api/v1/jogos").get_json()
    assert set(corpo) == {
        "itens", "pagina", "por_pagina", "total", "paginas", "proxima", "anterior",
    }
    assert corpo["total"] == 3
    assert corpo["por_pagina"] == 20
    assert corpo["anterior"] is None
    assert corpo["proxima"] is None


def test_proxima_e_caminho_relativo_que_o_front_pode_seguir(cliente, cabecalho):
    for indice in range(25):
        cliente.post(
            "/api/v1/jogos", json={"nome": f"Jogo {indice:02d}"}, headers=cabecalho
        )
    corpo = cliente.get("/api/v1/jogos?por_pagina=10").get_json()
    assert corpo["proxima"] == "/api/v1/jogos?pagina=2&por_pagina=10"

    segunda = cliente.get(corpo["proxima"]).get_json()
    assert segunda["pagina"] == 2
    assert segunda["anterior"] == "/api/v1/jogos?pagina=1&por_pagina=10"


def test_leitura_e_publica(cliente):
    assert cliente.get("/api/v1/jogos").status_code == 200


def test_detalhe_inexistente_devolve_404_em_json(cliente):
    resposta = cliente.get("/api/v1/jogos/9999")
    assert resposta.status_code == 404
    assert resposta.get_json() == {"erro": "Jogo não encontrado."}


def test_atualizacao_parcial(cliente, cabecalho):
    criado = cliente.post(
        "/api/v1/jogos", json={"nome": "Hades", "metacritic": 93}, headers=cabecalho
    ).get_json()
    resposta = cliente.put(
        f"/api/v1/jogos/{criado['id']}", json={"nome": "Hades II"}, headers=cabecalho
    )
    assert resposta.status_code == 200
    corpo = resposta.get_json()
    assert corpo["nome"] == "Hades II"
    assert corpo["metacritic"] == 93


def test_remover_devolve_204(cliente, cabecalho):
    criado = cliente.post(
        "/api/v1/jogos", json={"nome": "Braid"}, headers=cabecalho
    ).get_json()
    assert cliente.delete(
        f"/api/v1/jogos/{criado['id']}", headers=cabecalho
    ).status_code == 204
    assert cliente.get(f"/api/v1/jogos/{criado['id']}").status_code == 404


def test_ordenacao_fora_da_allowlist_e_recusada(cliente):
    """Interpolar o parâmetro direto no ORDER BY seria injeção."""
    resposta = cliente.get("/api/v1/jogos?ordenar_por=senha_hash")
    assert resposta.status_code == 422
    assert "ordenar_por" in resposta.get_json()["erros"]


def test_ordenar_por_pontuacao_na_rota_crud_funciona(cliente, cabecalho):
    """A rota CRUD partilha o mesmo `_clausulas_de_ordem` do catálogo, que
    aceita `pontuacao`. Sem o JOIN em `consulta_base`, isso montava
    ORDER BY sobre tabela fora do FROM e dava 500 numa rota pública."""
    cliente.post("/api/v1/jogos", json={"nome": "Hades"}, headers=cabecalho)
    resposta = cliente.get("/api/v1/jogos?ordenar_por=-pontuacao")
    assert resposta.status_code == 200


def test_ordenacao_desconhecida_continua_422_na_rota_crud(cliente):
    """A falha fechada não pode ter sido afrouxada pelo JOIN."""
    assert cliente.get("/api/v1/jogos?ordenar_por=senha_hash").status_code == 422


def test_join_do_bugometro_nao_infla_o_total_na_rota_crud(cliente, cabecalho):
    """`jogo_id` é UNIQUE em `bugometro_status`: o JOIN externo em
    `consulta_base` não pode duplicar linha. Um JOIN que duplicasse
    infla `total` sem que a lista de itens desse pista nenhuma --
    `total` vem de um COUNT sobre a mesma consulta, não de `len(itens)`."""
    ids = []
    for indice in range(5):
        criado = cliente.post(
            "/api/v1/jogos", json={"nome": f"Jogo Pontuado {indice}"},
            headers=cabecalho,
        ).get_json()
        ids.append(criado["id"])
        # Cada relato recalcula o bugômetro do próprio jogo, criando a
        # linha de bugometro_status que o JOIN externo alcança.
        cliente.post(
            "/api/v1/relatos-bug",
            json={
                "jogo_id": criado["id"], "titulo": "Bug",
                "categoria": "crash", "severidade": "critica",
            },
            headers=cabecalho,
        )

    corpo = cliente.get("/api/v1/jogos?por_pagina=100").get_json()
    assert corpo["total"] == len(corpo["itens"])
    assert corpo["total"] == len(set(j["id"] for j in corpo["itens"]))


def test_jogo_sem_bugometro_aparece_na_rota_crud(cliente, cabecalho):
    """O JOIN é EXTERNO de propósito: um jogo recém-cadastrado não tem
    linha de bugômetro ainda, e sumir do catálogo por isso seria pior
    que ordenar mal."""
    criado = cliente.post(
        "/api/v1/jogos", json={"nome": "Sem Bugometro Ainda"}, headers=cabecalho
    ).get_json()

    corpo = cliente.get("/api/v1/jogos?por_pagina=100&ordenar_por=-pontuacao").get_json()
    ids = [j["id"] for j in corpo["itens"]]
    assert criado["id"] in ids


def test_conteudo_de_outro_usuario_nao_pode_ser_editado(cliente, cabecalho):
    jogo = cliente.post(
        "/api/v1/jogos", json={"nome": "Tunic"}, headers=cabecalho
    ).get_json()
    topico = cliente.post(
        "/api/v1/topicos",
        json={"titulo": "Meu tópico", "jogo_id": jogo["id"]},
        headers=cabecalho,
    ).get_json()

    outro = cliente.post(
        "/api/auth/registro",
        json={"nome_usuario": "outro", "email": "o@l.dev", "senha": "senha123"},
    ).get_json()
    invasor = {"Authorization": f"Bearer {outro['token_acesso']}"}

    resposta = cliente.put(
        f"/api/v1/topicos/{topico['id']}", json={"titulo": "Invadido"}, headers=invasor
    )
    assert resposta.status_code == 403
    assert resposta.get_json() == {"erro": "Acesso negado."}


def test_autor_e_gravado_automaticamente(cliente, cabecalho_admin, cabecalho_comum):
    jogo = cliente.post(
        "/api/v1/jogos", json={"nome": "Celeste"}, headers=cabecalho_admin
    ).get_json()
    topico = cliente.post(
        "/api/v1/topicos",
        json={"titulo": "Dica de speedrun", "jogo_id": jogo["id"]},
        headers=cabecalho_comum,
    ).get_json()
    # Confere o id exato: gravar o autor errado passaria num `is not None`.
    assert topico["usuario_id"] == _id_do_token(cabecalho_comum)


# --- Catálogo é backoffice: escrita exige admin -------------------------

def test_conta_comum_nao_cria_jogo(cliente, cabecalho_comum):
    resposta = cliente.post(
        "/api/v1/jogos", json={"nome": "Pirata"}, headers=cabecalho_comum
    )
    assert resposta.status_code == 403
    assert resposta.get_json() == {"erro": "Acesso negado."}


def test_conta_comum_nao_apaga_jogo_do_catalogo(cliente, cabecalho_comum, cabecalho_admin):
    """Sem esta trava, qualquer conta recém-registrada apaga o catálogo."""
    jogo = cliente.post(
        "/api/v1/jogos", json={"nome": "Hades"}, headers=cabecalho_admin
    ).get_json()

    assert cliente.delete(
        f"/api/v1/jogos/{jogo['id']}", headers=cabecalho_comum
    ).status_code == 403
    assert cliente.get(f"/api/v1/jogos/{jogo['id']}").status_code == 200


def test_admin_administra_o_catalogo(cliente, cabecalho_admin):
    jogo = cliente.post(
        "/api/v1/jogos", json={"nome": "Tunic"}, headers=cabecalho_admin
    ).get_json()
    assert cliente.delete(
        f"/api/v1/jogos/{jogo['id']}", headers=cabecalho_admin
    ).status_code == 204


def test_conta_comum_ainda_publica_conteudo_proprio(cliente, cabecalho_comum, cabecalho_admin):
    """A trava do catálogo não pode ter fechado o conteúdo do usuário."""
    jogo = cliente.post(
        "/api/v1/jogos", json={"nome": "Celeste"}, headers=cabecalho_admin
    ).get_json()
    resposta = cliente.post(
        "/api/v1/topicos",
        json={"titulo": "Meu tópico", "jogo_id": jogo["id"]},
        headers=cabecalho_comum,
    )
    assert resposta.status_code == 201


# --- Paginação preserva os filtros --------------------------------------

def test_proxima_preserva_ordenar_por(cliente, cabecalho_admin):
    """Seguir `proxima` sem o `ordenar_por` faria a página 2 voltar à
    ordem padrão, misturando resultados fora de ordem."""
    for indice in range(25):
        cliente.post(
            "/api/v1/jogos",
            json={"nome": f"Jogo {indice:02d}", "metacritic": indice},
            headers=cabecalho_admin,
        )

    corpo = cliente.get(
        "/api/v1/jogos?por_pagina=10&ordenar_por=-metacritic"
    ).get_json()
    assert "ordenar_por=-metacritic" in corpo["proxima"]

    segunda = cliente.get(corpo["proxima"]).get_json()
    assert segunda["pagina"] == 2
    notas = [j["metacritic"] for j in segunda["itens"]]
    assert notas == sorted(notas, reverse=True)


# --- Usuário só administra a si mesmo -----------------------------------

def test_usuario_nao_edita_outro_usuario(cliente, cabecalho_comum):
    outro = cliente.post(
        "/api/auth/registro",
        json={"nome_usuario": "alheio", "email": "a@l.dev", "senha": "senha123"},
    ).get_json()

    resposta = cliente.put(
        f"/api/v1/usuarios/{outro['usuario']['id']}",
        json={"bio": "invadido"},
        headers=cabecalho_comum,
    )
    assert resposta.status_code == 403


def test_usuario_nao_apaga_outro_usuario(cliente, cabecalho_comum):
    outro = cliente.post(
        "/api/auth/registro",
        json={"nome_usuario": "vitima", "email": "v@l.dev", "senha": "senha123"},
    ).get_json()

    resposta = cliente.delete(
        f"/api/v1/usuarios/{outro['usuario']['id']}", headers=cabecalho_comum
    )
    assert resposta.status_code == 403
    assert cliente.get(f"/api/v1/usuarios/{outro['usuario']['id']}").status_code == 200


def test_usuario_apaga_a_propria_conta(cliente, cabecalho_comum):
    meu_id = _id_do_token(cabecalho_comum)
    assert cliente.delete(
        f"/api/v1/usuarios/{meu_id}", headers=cabecalho_comum
    ).status_code == 204
    assert cliente.get(f"/api/v1/usuarios/{meu_id}").status_code == 404


# --- Classificação de erro de banco: SQLite nos testes, MySQL em prod ---

def test_classificacao_de_integridade_cobre_sqlite_e_mysql():
    """SQLite e MySQL descrevem os MESMOS erros com textos diferentes.

    Casar só o texto do SQLite faria a detecção passar aqui e falhar em
    produção — e nenhum teste pegaria, porque os testes rodam em SQLite.
    """
    from sqlalchemy.exc import IntegrityError

    from app.errors import Conflito, DadosInvalidos
    from app.repositories.base import classificar_integridade

    class _Orig(Exception):
        pass

    def classificar(orig):
        return classificar_integridade(IntegrityError("INSERT", {}, orig))

    # Campo obrigatório ausente
    sqlite_nulo = _Orig("NOT NULL constraint failed: usuarios.senha_hash")
    mysql_nulo = _Orig(1048, "Column 'senha_hash' cannot be null")
    for orig in (sqlite_nulo, mysql_nulo):
        erro = classificar(orig)
        assert isinstance(erro, DadosInvalidos), orig
        assert erro.status == 422

    # Referência inexistente
    sqlite_fk = _Orig("FOREIGN KEY constraint failed")
    mysql_fk = _Orig(1452, "Cannot add or update a child row")
    for orig in (sqlite_fk, mysql_fk):
        erro = classificar(orig)
        assert isinstance(erro, DadosInvalidos), orig
        assert erro.status == 422

    # Duplicidade continua sendo conflito
    sqlite_unico = _Orig("UNIQUE constraint failed: usuarios.email")
    mysql_unico = _Orig(1062, "Duplicate entry 'a@b.dev' for key 'email'")
    for orig in (sqlite_unico, mysql_unico):
        erro = classificar(orig)
        assert isinstance(erro, Conflito), orig
        assert erro.status == 409


def test_usuario_edita_a_si_mesmo(cliente, cabecalho_comum):
    meu_id = _id_do_token(cabecalho_comum)
    resposta = cliente.put(
        f"/api/v1/usuarios/{meu_id}",
        json={"bio": "caçador de bugs"},
        headers=cabecalho_comum,
    )
    assert resposta.status_code == 200
    assert resposta.get_json()["bio"] == "caçador de bugs"


# --- Moderação ponta a ponta pelo HTTP ----------------------------------

def test_topico_oculto_some_da_listagem_publica(
    cliente, cabecalho_comum, cabecalho_admin, app
):
    """A lógica está testada em unidade; isto testa a FIAÇÃO em
    composicao.py — um typo na lista de services moderáveis passaria
    despercebido sem este teste."""
    from app.extensions import db
    from app.models import Topico

    jogo = cliente.post(
        "/api/v1/jogos", json={"nome": "Stray"}, headers=cabecalho_admin
    ).get_json()
    cliente.post(
        "/api/v1/topicos",
        json={"titulo": "Some daqui", "jogo_id": jogo["id"]},
        headers=cabecalho_comum,
    )
    topico = db.session.execute(db.select(Topico)).scalars().first()
    topico.oculto = True
    db.session.commit()

    assert cliente.get("/api/v1/topicos").get_json()["total"] == 0
    assert cliente.get(f"/api/v1/topicos/{topico.id}").status_code == 404


def test_recursos_expostos_sao_exatamente_os_da_especificacao(cliente):
    """Contar não detecta troca: foi assim que `bugometro` virou
    `usuarios-badges` sem ninguém notar em nove revisões."""
    from app.controllers.registro import RECURSOS

    esperado = {
        "jogos", "generos", "plataformas", "usuarios", "biblioteca",
        "avaliacoes", "relatos-bug", "votos-bug", "alertas", "topicos",
        "posts", "categorias", "badges", "notificacoes", "atividades",
        "metricas-bug", "historico-bug", "bugometro",
    }
    assert {prefixo for prefixo, _ in RECURSOS} == esperado

    for prefixo in esperado:
        resposta = cliente.get(f"/api/v1/{prefixo}")
        assert resposta.status_code == 200, prefixo
        assert "itens" in resposta.get_json(), prefixo


def test_listagem_publica_de_usuarios_nao_vaza_email(cliente, cabecalho):
    corpo = cliente.get("/api/v1/usuarios").get_json()
    assert corpo["itens"], "precisa haver ao menos um usuário para o teste valer"
    for usuario in corpo["itens"]:
        assert "email" not in usuario
        assert "senha_hash" not in usuario


def test_admin_esconde_conteudo_pela_api(cliente, cabecalho, cabecalho_comum):
    jogo = cliente.post(
        "/api/v1/jogos", json={"nome": "Inscryption"}, headers=cabecalho
    ).get_json()
    topico = cliente.post(
        "/api/v1/topicos",
        json={"titulo": "Ofensivo", "jogo_id": jogo["id"]},
        headers=cabecalho_comum,
    ).get_json()

    assert cliente.put(
        f"/api/v1/topicos/{topico['id']}",
        json={"oculto": True},
        headers=cabecalho,
    ).status_code == 200
    assert cliente.get("/api/v1/topicos").get_json()["total"] == 0


def test_autor_nao_esconde_o_proprio_conteudo(cliente, cabecalho, cabecalho_comum):
    jogo = cliente.post(
        "/api/v1/jogos", json={"nome": "Outer Wilds"}, headers=cabecalho
    ).get_json()
    topico = cliente.post(
        "/api/v1/topicos",
        json={"titulo": "Meu", "jogo_id": jogo["id"]},
        headers=cabecalho_comum,
    ).get_json()

    assert cliente.put(
        f"/api/v1/topicos/{topico['id']}",
        json={"oculto": True},
        headers=cabecalho_comum,
    ).status_code == 403


def test_conta_comum_nao_se_promove(cliente, cabecalho_comum):
    meu_id = _id_do_token(cabecalho_comum)
    resposta = cliente.put(
        f"/api/v1/usuarios/{meu_id}", json={"is_admin": True}, headers=cabecalho_comum
    )
    assert resposta.status_code == 403


def test_admin_promove_outro_usuario(cliente, cabecalho, cabecalho_comum):
    alvo = _id_do_token(cabecalho_comum)
    resposta = cliente.put(
        f"/api/v1/usuarios/{alvo}", json={"is_admin": True}, headers=cabecalho
    )
    assert resposta.status_code == 200
    assert resposta.get_json()["is_admin"] is True


def test_cliente_nao_grava_a_versao_de_sessao(cliente):
    """O campo que decide se um token vale não pode ser escrito por quem
    envia o token. Gravável, ele vira logout remoto forçado — e devolver
    o valor antigo ressuscita um token já revogado."""
    dados = cliente.post(
        "/api/auth/registro",
        json={"nome_usuario": "alvo", "email": "a@l.dev", "senha": "senhaboa123"},
    ).get_json()
    cabecalho = {"Authorization": f"Bearer {dados['token_acesso']}"}
    identificador = dados["usuario"]["id"]

    cliente.patch(
        f"/api/v1/usuarios/{identificador}",
        headers=cabecalho,
        json={"versao_sessao": 50, "senha_alterada_em": "2020-01-01T00:00:00"},
    )

    # A sessão continua valendo: o PATCH não pôde tocar nos campos.
    assert cliente.get("/api/v1/eu", headers=cabecalho).status_code == 200


def test_colunas_de_revogacao_nao_saem_no_payload_publico(cliente):
    """`GET /api/v1/usuarios` é leitura pública. Quando alguém trocou a
    senha, e quantas vezes, não é informação de listagem."""
    cliente.post(
        "/api/auth/registro",
        json={"nome_usuario": "alguem", "email": "b@l.dev", "senha": "senhaboa123"},
    )
    corpo = cliente.get("/api/v1/usuarios").get_json()
    for usuario in corpo["itens"]:
        assert "versao_sessao" not in usuario
        assert "senha_alterada_em" not in usuario
        assert "senha_hash" not in usuario


def test_comando_promover_cria_o_primeiro_admin(app):
    """Bootstrap: numa base nova não existe admin nenhum, e sem ele o
    catálogo inteiro é somente-leitura."""
    from app.extensions import db
    from app.models import Usuario

    usuario = Usuario(nome_usuario="primeiro", email="p@l.dev")
    usuario.definir_senha("senha123")
    db.session.add(usuario)
    db.session.commit()
    assert usuario.is_admin is False

    resultado = app.test_cli_runner().invoke(args=["promover", "primeiro"])
    assert resultado.exit_code == 0

    db.session.refresh(usuario)
    assert usuario.is_admin is True


def test_comando_promover_recusa_usuario_inexistente(app):
    resultado = app.test_cli_runner().invoke(args=["promover", "ninguem"])
    assert resultado.exit_code != 0


def test_rotas_sem_utilidade_respondem_405(cliente, cabecalho):
    """Registro de usuário é /api/auth/registro; e um voto não tem
    campo atualizável depois do bloqueio de troca de relato."""
    assert cliente.post(
        "/api/v1/usuarios", json={"nome_usuario": "x"}, headers=cabecalho
    ).status_code == 405
    assert cliente.put(
        "/api/v1/votos-bug/1", json={}, headers=cabecalho
    ).status_code == 405


def test_media_serve_arquivo_existente(app, tmp_path, monkeypatch):
    from app.controllers import paginas_controller

    monkeypatch.setattr(paginas_controller, "PASTA_MIDIA", tmp_path)
    (tmp_path / "capa.txt").write_text("conteudo", encoding="utf-8")

    resposta = app.test_client().get("/media/capa.txt")
    assert resposta.status_code == 200


def test_media_inexistente_e_404(app):
    assert app.test_client().get("/media/nao-existe.jpg").status_code == 404
