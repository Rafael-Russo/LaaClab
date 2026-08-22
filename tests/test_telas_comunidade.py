import pytest


def _cabecalho(cliente, nome="gamer"):
    corpo = cliente.post(
        "/api/auth/registro",
        json={"nome_usuario": nome, "email": f"{nome}@l.dev", "senha": "senha123"},
    ).get_json()
    return {"Authorization": f"Bearer {corpo['token_acesso']}"}


@pytest.fixture
def praca(cliente, app):
    """Dois jogos com tópicos, um sem, um tópico oculto e dois alertas."""
    from app.composicao import montar_servicos
    from app.extensions import db
    from app.models import Alerta, BibliotecaUsuario, Topico, Usuario

    cabecalho = _cabecalho(cliente)
    autor = db.session.execute(
        db.select(Usuario).where(Usuario.nome_usuario == "gamer")
    ).scalars().first()

    chefe = Usuario(nome_usuario="chefe", email="chefe@l.dev", is_admin=True)
    chefe.definir_senha("senha123")
    db.session.add(chefe)
    db.session.commit()

    servicos = montar_servicos()
    movimentado = servicos.jogos.criar({"nome": "Cyberpunk 2077"}, usuario=chefe)
    calmo = servicos.jogos.criar({"nome": "Hollow Knight"}, usuario=chefe)
    deserto = servicos.jogos.criar({"nome": "Sem Assunto"}, usuario=chefe)

    servicos.topicos.criar(
        {
            "titulo": "Alguém mais com crash no ato 2?",
            "tipo": "bug",
            "corpo": "Toda vez que entro no metrô da Watson o jogo fecha "
            "sem aviso nenhum e perco o progresso da última meia hora, "
            "o que é bem frustrante depois de uma sessão longa demais.",
            "jogo_id": movimentado["id"],
        },
        usuario=autor,
    )
    servicos.topicos.criar(
        {"titulo": "Dica de build", "tipo": "dica", "jogo_id": movimentado["id"]},
        usuario=autor,
    )
    servicos.topicos.criar(
        {"titulo": "Patch novo", "tipo": "noticia", "jogo_id": calmo["id"]},
        usuario=autor,
    )

    escondido = Topico(
        titulo="Spam", tipo="discussao", usuario_id=autor.id,
        jogo_id=movimentado["id"], oculto=True,
    )
    db.session.add(escondido)
    db.session.add(
        Alerta(jogo_id=movimentado["id"], severidade="critica", texto="Servidores fora.")
    )
    db.session.add(
        Alerta(jogo_id=calmo["id"], severidade="atualizacao", texto="Patch 1.2 no ar.")
    )
    db.session.add(
        BibliotecaUsuario(usuario_id=autor.id, jogo_id=calmo["id"], favorito=True)
    )
    db.session.commit()

    return {
        "cabecalho": cabecalho,
        "movimentado": movimentado,
        "calmo": calmo,
        "deserto": deserto,
    }


# --- rótulos de tópico --------------------------------------------------

def test_rotulos_e_niveis_cobrem_todos_os_tipos():
    from app.models import TIPOS_TOPICO
    from app.services.rotulos import nivel_tipo, rotulo_tipo

    for chave in TIPOS_TOPICO:
        assert rotulo_tipo(chave) != chave
        assert nivel_tipo(chave) in {"discussion", "warning", "stable", "info"}


def test_nivel_do_tipo_segue_o_mapa_do_css():
    from app.services.rotulos import nivel_tipo

    assert nivel_tipo("discussao") == "discussion"
    assert nivel_tipo("bug") == "warning"
    assert nivel_tipo("dica") == "stable"
    assert nivel_tipo("noticia") == "info"
    assert nivel_tipo("inventado") == "discussion"


# --- /telas/comunidade --------------------------------------------------

def test_comunidade_devolve_as_cinco_chaves(cliente, praca):
    corpo = cliente.get(
        "/api/v1/telas/comunidade", headers=praca["cabecalho"]
    ).get_json()
    assert set(corpo) == {
        "selecionado", "jogos", "topicos", "estatisticas", "regras",
    }


def test_sem_parametro_seleciona_o_jogo_com_mais_topicos(cliente, praca):
    corpo = cliente.get(
        "/api/v1/telas/comunidade", headers=praca["cabecalho"]
    ).get_json()
    assert corpo["selecionado"]["slug"] == "cyberpunk-2077"


def test_slug_inexistente_e_404_e_nao_fallback_silencioso(cliente, praca):
    """O sistema antigo caía em outro jogo sem avisar — o usuário via
    tópicos de um jogo que não pediu."""
    resposta = cliente.get(
        "/api/v1/telas/comunidade?jogo=nao-existe", headers=praca["cabecalho"]
    )
    assert resposta.status_code == 404
    assert resposta.get_json() == {"erro": "Jogo não encontrado."}


def test_total_de_topicos_ignora_os_ocultos(cliente, praca):
    """O tile mostrava um número e a lista mostrava outro."""
    corpo = cliente.get(
        "/api/v1/telas/comunidade", headers=praca["cabecalho"]
    ).get_json()
    assert corpo["selecionado"]["total_topicos"] == 2
    assert len(corpo["topicos"]) == 2


def test_jogo_sem_topicos_aparece_na_lista_com_zero(cliente, praca):
    corpo = cliente.get(
        "/api/v1/telas/comunidade", headers=praca["cabecalho"]
    ).get_json()
    por_slug = {j["slug"]: j["total_topicos"] for j in corpo["jogos"]}
    assert por_slug["sem-assunto"] == 0


def test_topico_tem_tipo_cru_e_rotulo(cliente, praca):
    """O sistema antigo colidia os dois no mesmo campo."""
    corpo = cliente.get(
        "/api/v1/telas/comunidade", headers=praca["cabecalho"]
    ).get_json()
    topico = next(t for t in corpo["topicos"] if t["tipo"] == "bug")
    assert topico["tipo_rotulo"] == "Bug"
    assert topico["nivel"] == "warning"
    assert set(topico) == {
        "id", "titulo", "autor", "quando", "resumo", "tipo", "tipo_rotulo", "nivel",
    }


def test_resumo_e_truncado_em_160(cliente, praca):
    corpo = cliente.get(
        "/api/v1/telas/comunidade", headers=praca["cabecalho"]
    ).get_json()
    longo = next(t for t in corpo["topicos"] if t["tipo"] == "bug")
    assert len(longo["resumo"]) <= 161
    assert longo["resumo"].endswith("…")


def test_topicos_do_jogo_pedido_e_nao_de_todos(cliente, praca):
    corpo = cliente.get(
        "/api/v1/telas/comunidade?jogo=hollow-knight", headers=praca["cabecalho"]
    ).get_json()
    assert [t["titulo"] for t in corpo["topicos"]] == ["Patch novo"]


def test_estatisticas_sao_inteiros_crus(cliente, praca):
    """Três das quatro eram string formatada no servidor. A formatação
    de milhar virou responsabilidade do JS."""
    corpo = cliente.get(
        "/api/v1/telas/comunidade", headers=praca["cabecalho"]
    ).get_json()
    estatisticas = corpo["estatisticas"]
    assert set(estatisticas) == {"membros", "topicos", "mensagens", "jogos_ativos"}
    for valor in estatisticas.values():
        assert isinstance(valor, int)


def test_estatisticas_contam_o_que_prometem(cliente, praca):
    corpo = cliente.get(
        "/api/v1/telas/comunidade", headers=praca["cabecalho"]
    ).get_json()
    estatisticas = corpo["estatisticas"]
    assert estatisticas["membros"] == 2
    assert estatisticas["topicos"] == 3
    assert estatisticas["jogos_ativos"] == 2


def test_regras_vem_como_constante(cliente, praca):
    corpo = cliente.get(
        "/api/v1/telas/comunidade", headers=praca["cabecalho"]
    ).get_json()
    assert len(corpo["regras"]) == 4
    assert corpo["regras"][0] == "Respeite todos os membros."


def test_comunidade_sem_token_e_401(cliente):
    assert cliente.get("/api/v1/telas/comunidade").status_code == 401


# --- /telas/alertas -----------------------------------------------------

def test_alertas_devolve_as_tres_chaves(cliente, praca):
    corpo = cliente.get(
        "/api/v1/telas/alertas", headers=praca["cabecalho"]
    ).get_json()
    assert set(corpo) == {"alertas", "resumo", "favoritos"}


def test_alerta_tem_rotulo_nivel_e_icone(cliente, praca):
    corpo = cliente.get(
        "/api/v1/telas/alertas", headers=praca["cabecalho"]
    ).get_json()
    critico = next(a for a in corpo["alertas"] if a["nivel"] == "critical")
    assert critico["severidade_rotulo"] == "CRÍTICO"
    assert critico["icone"] == "wifi"
    assert critico["jogo"] == "Cyberpunk 2077"
    assert critico["jogo_slug"] == "cyberpunk-2077"
    assert set(critico) == {
        "id", "jogo", "jogo_slug", "severidade_rotulo", "nivel", "icone", "texto",
    }


def test_resumo_tem_sempre_tres_linhas_na_ordem_fixa(cliente, praca):
    corpo = cliente.get(
        "/api/v1/telas/alertas", headers=praca["cabecalho"]
    ).get_json()
    assert [linha["nivel"] for linha in corpo["resumo"]] == [
        "critical", "warning", "stable",
    ]
    assert [linha["rotulo"] for linha in corpo["resumo"]] == [
        "Críticos", "Instável", "Atualização",
    ]


def test_resumo_conta_a_tabela_inteira_nao_so_os_dez_devolvidos(cliente, praca):
    """Decisão consciente: o sistema antigo contava só a página."""
    from app.extensions import db
    from app.models import Alerta

    for _ in range(15):
        db.session.add(
            Alerta(jogo_id=praca["movimentado"]["id"], severidade="critica", texto="x")
        )
    db.session.commit()

    corpo = cliente.get(
        "/api/v1/telas/alertas", headers=praca["cabecalho"]
    ).get_json()
    assert len(corpo["alertas"]) == 10
    por_nivel = {linha["nivel"]: linha["contagem"] for linha in corpo["resumo"]}
    assert por_nivel["critical"] == 16


def test_resumo_mostra_zero_em_vez_de_sumir(cliente):
    cabecalho = _cabecalho(cliente, "sozinho")
    corpo = cliente.get("/api/v1/telas/alertas", headers=cabecalho).get_json()
    assert [linha["contagem"] for linha in corpo["resumo"]] == [0, 0, 0]
    assert corpo["alertas"] == []


def test_favoritos_do_alerta_sao_do_usuario_autenticado(cliente, praca):
    corpo = cliente.get(
        "/api/v1/telas/alertas", headers=praca["cabecalho"]
    ).get_json()
    assert [j["nome"] for j in corpo["favoritos"]] == ["Hollow Knight"]

    outro = _cabecalho(cliente, "intruso")
    assert cliente.get("/api/v1/telas/alertas", headers=outro).get_json()[
        "favoritos"
    ] == []


def test_alertas_sem_token_e_401(cliente):
    assert cliente.get("/api/v1/telas/alertas").status_code == 401
