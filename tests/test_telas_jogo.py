import pytest


def _cabecalho(cliente, nome="gamer"):
    corpo = cliente.post(
        "/api/auth/registro",
        json={"nome_usuario": nome, "email": f"{nome}@l.dev", "senha": "senha123"},
    ).get_json()
    return {"Authorization": f"Bearer {corpo['token_acesso']}"}


@pytest.fixture
def mundo(cliente, app):
    """Dois jogos, relatos de severidades diferentes, um alerta e um
    comentário. O catálogo exige admin; o conteúdo é do usuário comum."""
    from app.composicao import montar_servicos
    from app.extensions import db
    from app.models import Alerta, Usuario

    cabecalho = _cabecalho(cliente)
    comum = db.session.execute(
        db.select(Usuario).where(Usuario.nome_usuario == "gamer")
    ).scalars().first()

    chefe = Usuario(nome_usuario="chefe", email="chefe@l.dev", is_admin=True)
    chefe.definir_senha("senha123")
    db.session.add(chefe)
    db.session.commit()

    servicos = montar_servicos()
    instavel = servicos.jogos.criar(
        {
            "nome": "Cyberpunk 2077",
            "sobre": "RPG em Night City.",
            "curtidas": 73430,
            "descurtidas": 1284,
            "conquistas": 44,
            "tempo_medio": "25h",
        },
        usuario=chefe,
    )
    calmo = servicos.jogos.criar({"nome": "Hollow Knight"}, usuario=chefe)

    servicos.relatos_bug.criar(
        {
            "jogo_id": instavel["id"],
            "titulo": "Crash ao entrar no metrô",
            "categoria": "crash",
            "severidade": "critica",
        },
        usuario=comum,
    )
    servicos.relatos_bug.criar(
        {
            "jogo_id": instavel["id"],
            "titulo": "Textura sumindo",
            "categoria": "graficos",
            "severidade": "baixa",
        },
        usuario=comum,
    )

    db.session.add(
        Alerta(
            jogo_id=instavel["id"],
            severidade="critica",
            texto="Servidores instáveis após o patch 2.3, muita gente relatando.",
        )
    )
    db.session.commit()

    servicos.avaliacoes.criar(
        {"jogo_id": instavel["id"], "comentario": "Depois do patch melhorou."},
        usuario=comum,
    )

    return {"cabecalho": cabecalho, "instavel": instavel, "calmo": calmo}


# --- rótulos -----------------------------------------------------------

def test_rotulos_cobrem_todas_as_chaves_do_dominio():
    """Uma chave sem rótulo apareceria crua na tela, em inglês."""
    from app.models import CATEGORIAS_BUG, SEVERIDADES
    from app.services.rotulos import CATEGORIAS, rotulo_categoria, rotulo_severidade

    assert set(CATEGORIAS) == set(CATEGORIAS_BUG)
    for chave in CATEGORIAS_BUG:
        assert rotulo_categoria(chave) != chave
    for chave in SEVERIDADES:
        assert rotulo_severidade(chave) != chave


def test_rotulo_desconhecido_cai_num_padrao_legivel():
    from app.services.rotulos import rotulo_categoria, rotulo_severidade

    assert rotulo_categoria("inventada") == "Outro"
    assert rotulo_severidade("inventada") == "Média"


# --- /telas/bugometro --------------------------------------------------

def test_bugometro_devolve_as_sete_chaves(cliente, mundo):
    corpo = cliente.get(
        "/api/v1/telas/bugometro", headers=mundo["cabecalho"]
    ).get_json()
    assert set(corpo) == {
        "jogo", "atualizado_ha", "metricas", "bugs", "grafico",
        "atividades", "top_instaveis",
    }


def test_bugometro_sem_parametro_escolhe_o_mais_instavel(cliente, mundo):
    corpo = cliente.get(
        "/api/v1/telas/bugometro", headers=mundo["cabecalho"]
    ).get_json()
    assert corpo["jogo"]["slug"] == "cyberpunk-2077"
    assert corpo["jogo"]["pontuacao"] > 0


def test_bugometro_respeita_o_slug_pedido(cliente, mundo):
    corpo = cliente.get(
        "/api/v1/telas/bugometro?jogo=hollow-knight", headers=mundo["cabecalho"]
    ).get_json()
    assert corpo["jogo"]["slug"] == "hollow-knight"
    assert corpo["bugs"] == []


def test_bugometro_com_slug_inexistente_e_404(cliente, mundo):
    resposta = cliente.get(
        "/api/v1/telas/bugometro?jogo=nao-existe", headers=mundo["cabecalho"]
    )
    assert resposta.status_code == 404


def test_bugometro_sem_jogos_no_banco_e_404_com_mensagem(cliente):
    """O JS congela em 'Carregando...' se não receber nada — precisa de
    um erro para exibir."""
    cabecalho = _cabecalho(cliente, "sozinho")
    resposta = cliente.get("/api/v1/telas/bugometro", headers=cabecalho)
    assert resposta.status_code == 404
    assert resposta.get_json() == {"erro": "Sem jogos cadastrados."}


def test_bugometro_traz_sempre_os_quatro_cards(cliente, mundo):
    corpo = cliente.get(
        "/api/v1/telas/bugometro", headers=mundo["cabecalho"]
    ).get_json()
    assert [m["chave"] for m in corpo["metricas"]] == [
        "crash", "bugs", "stutter", "fps",
    ]
    for metrica in corpo["metricas"]:
        assert set(metrica) == {"chave", "rotulo", "valor", "nivel", "icone"}


def test_bug_traz_severidade_crua_e_rotulo(cliente, mundo):
    """O valor cru define a cor; o rótulo define o texto."""
    corpo = cliente.get(
        "/api/v1/telas/bugometro", headers=mundo["cabecalho"]
    ).get_json()
    bug = next(b for b in corpo["bugs"] if b["severidade"] == "critica")
    assert bug["severidade_rotulo"] == "Crítica"
    assert bug["categoria"] == "Crash"
    assert set(bug) == {
        "id", "titulo", "categoria", "confirmacoes", "severidade",
        "severidade_rotulo", "status", "ja_confirmei",
    }


def test_bugs_vem_ordenados_por_confirmacoes(cliente, mundo, app):
    from app.extensions import db
    from app.models import RelatoBug

    relatos = db.session.execute(db.select(RelatoBug)).scalars().all()
    relatos[1].confirmacoes = 99
    db.session.commit()

    corpo = cliente.get(
        "/api/v1/telas/bugometro", headers=mundo["cabecalho"]
    ).get_json()
    assert corpo["bugs"][0]["confirmacoes"] == 99


def test_atividades_sao_do_jogo_pedido_e_nao_globais(cliente, mundo):
    """O sistema antigo caía num fallback global e mostrava alerta de
    outro jogo. Aqui, jogo sem alerta devolve lista vazia."""
    corpo = cliente.get(
        "/api/v1/telas/bugometro?jogo=hollow-knight", headers=mundo["cabecalho"]
    ).get_json()
    assert corpo["atividades"] == []


def test_atividade_tem_subtitulo_truncado(cliente, mundo):
    corpo = cliente.get(
        "/api/v1/telas/bugometro", headers=mundo["cabecalho"]
    ).get_json()
    atividade = corpo["atividades"][0]
    assert set(atividade) == {"nivel", "titulo", "subtitulo", "quando"}
    assert len(atividade["subtitulo"]) <= 49
    assert atividade["subtitulo"].endswith("…")
    # Capitalização normal, não caixa alta (defeito 8).
    assert atividade["titulo"] == "Crítico"
    assert atividade["nivel"] == "critical"


def test_top_instaveis_traz_o_cartao_completo(cliente, mundo):
    """O JS mostrava iniciais hardcoded por falta desses campos."""
    corpo = cliente.get(
        "/api/v1/telas/bugometro", headers=mundo["cabecalho"]
    ).get_json()
    topo = corpo["top_instaveis"][0]
    assert topo["slug"] == "cyberpunk-2077"
    assert topo["iniciais"] == "C2"
    assert len(topo["capa"]) == 2
    assert topo["status"]["nivel"] in {"critical", "warning", "stable"}
    # Caso negativo do defeito 1: sem entrada na biblioteca, os dois
    # campos são `False` porque é verdade, não porque alguém esqueceu de
    # passar o usuário. O par com o teste positivo abaixo é o que
    # distingue as duas situações.
    assert topo["favorito"] is False
    assert topo["na_biblioteca"] is False


def test_bugometro_reflete_favorito_e_biblioteca_do_usuario(cliente, mundo, app):
    """Bloqueador da revisão (defeito 1): `bugometro()` recebia `usuario`
    e descartava, então `montar_card` caía nos defaults e mentia
    favorito/na_biblioteca para quem já tinha o jogo na biblioteca —
    tanto no card principal quanto em cada card de `top_instaveis`."""
    from app.extensions import db
    from app.models import BibliotecaUsuario, Usuario

    comum = db.session.execute(
        db.select(Usuario).where(Usuario.nome_usuario == "gamer")
    ).scalars().first()
    db.session.add(
        BibliotecaUsuario(
            usuario_id=comum.id, jogo_id=mundo["instavel"]["id"], favorito=True
        )
    )
    db.session.commit()

    corpo = cliente.get(
        "/api/v1/telas/bugometro?jogo=cyberpunk-2077", headers=mundo["cabecalho"]
    ).get_json()
    assert corpo["jogo"]["favorito"] is True
    assert corpo["jogo"]["na_biblioteca"] is True

    topo = next(c for c in corpo["top_instaveis"] if c["slug"] == "cyberpunk-2077")
    assert topo["favorito"] is True
    assert topo["na_biblioteca"] is True


def test_grafico_tem_a_forma_que_o_js_espera(cliente, mundo):
    corpo = cliente.get(
        "/api/v1/telas/bugometro", headers=mundo["cabecalho"]
    ).get_json()
    grafico = corpo["grafico"]
    assert len(grafico["rotulos"]) == 24
    assert [s["chave"] for s in grafico["series"]] == [
        "crash", "bug", "stutter", "fps",
    ]
    for serie in grafico["series"]:
        assert len(serie["dados"]) == 24
        assert all(0 <= v <= 100 for v in serie["dados"])


def test_atualizado_ha_e_relativo_e_nao_literal(cliente, mundo):
    corpo = cliente.get(
        "/api/v1/telas/bugometro", headers=mundo["cabecalho"]
    ).get_json()
    assert corpo["atualizado_ha"] in ("agora mesmo",) or corpo[
        "atualizado_ha"
    ].startswith("há ")


def test_bugometro_sem_token_e_401(cliente):
    assert cliente.get("/api/v1/telas/bugometro").status_code == 401


# --- /telas/jogo/<slug> ------------------------------------------------

def test_jogo_devolve_o_shape_completo(cliente, mundo):
    corpo = cliente.get(
        "/api/v1/telas/jogo/cyberpunk-2077", headers=mundo["cabecalho"]
    ).get_json()
    # `favorito`/`na_biblioteca` passam a sair no detalhe (defeito 2 da
    # revisão): antes eram removidos com `.pop()` por não haver como
    # calculá-los certo; agora `usuario` chega até `montar_detalhe`.
    assert set(corpo) == {
        "id", "slug", "nome", "capa", "imagem_capa", "arquivo_capa", "iniciais",
        "ultima_atualizacao", "sobre", "curtidas", "descurtidas",
        "tempo_para_zerar", "conquistas", "merch", "pontuacao", "status",
        "bugs", "comentarios", "favorito", "na_biblioteca",
    }


def test_jogo_detalhe_reflete_favorito_e_biblioteca_do_usuario(cliente, mundo, app):
    """Item 12 da revisão (defeito 2): a tela de detalhe é onde o botão
    de favoritar mais importa, e o valor agora sai correto em vez de
    ser removido do payload."""
    from app.extensions import db
    from app.models import BibliotecaUsuario, Usuario

    comum = db.session.execute(
        db.select(Usuario).where(Usuario.nome_usuario == "gamer")
    ).scalars().first()
    db.session.add(
        BibliotecaUsuario(
            usuario_id=comum.id, jogo_id=mundo["instavel"]["id"], favorito=True
        )
    )
    db.session.commit()

    corpo = cliente.get(
        "/api/v1/telas/jogo/cyberpunk-2077", headers=mundo["cabecalho"]
    ).get_json()
    assert corpo["favorito"] is True
    assert corpo["na_biblioteca"] is True


def test_curtidas_sao_inteiro_cru_nao_texto_formatado(cliente, mundo):
    """A formatação de milhar virou responsabilidade do JS, para unificar
    com a tela de comunidade, que já formatava no cliente."""
    corpo = cliente.get(
        "/api/v1/telas/jogo/cyberpunk-2077", headers=mundo["cabecalho"]
    ).get_json()
    assert corpo["curtidas"] == 73430
    assert corpo["descurtidas"] == 1284


def test_campos_vazios_caem_em_padrao_legivel(cliente, mundo):
    corpo = cliente.get(
        "/api/v1/telas/jogo/hollow-knight", headers=mundo["cabecalho"]
    ).get_json()
    assert corpo["merch"] == "Sem informações de merch para este jogo."
    assert corpo["ultima_atualizacao"] == "—"
    assert corpo["tempo_para_zerar"] == {
        "medio": "—", "speedrun": "—", "platina": "—",
    }


def test_tempo_para_zerar_usa_o_valor_quando_existe(cliente, mundo):
    corpo = cliente.get(
        "/api/v1/telas/jogo/cyberpunk-2077", headers=mundo["cabecalho"]
    ).get_json()
    assert corpo["tempo_para_zerar"]["medio"] == "25h"


def test_comentarios_trazem_autor_e_texto(cliente, mundo):
    corpo = cliente.get(
        "/api/v1/telas/jogo/cyberpunk-2077", headers=mundo["cabecalho"]
    ).get_json()
    comentario = corpo["comentarios"][0]
    assert set(comentario) == {"id", "autor", "texto"}
    assert comentario["autor"] == "gamer"


def test_comentario_oculto_nao_aparece(cliente, mundo, app):
    """Moderação vazada era um bug do sistema antigo."""
    from app.extensions import db
    from app.models import Avaliacao

    avaliacao = db.session.execute(db.select(Avaliacao)).scalars().first()
    avaliacao.oculto = True
    db.session.commit()

    corpo = cliente.get(
        "/api/v1/telas/jogo/cyberpunk-2077", headers=mundo["cabecalho"]
    ).get_json()
    assert corpo["comentarios"] == []


def test_bugs_do_detalhe_sao_a_mesma_lista_do_bugometro(cliente, mundo):
    """A chave `bugs` é lista nos dois endpoints e sai do MESMO lugar.
    Reimplementar a regra de "relato ativo" no detalhe faria as duas
    telas divergirem em silêncio quando um status novo aparecesse."""
    detalhe = cliente.get(
        "/api/v1/telas/jogo/cyberpunk-2077", headers=mundo["cabecalho"]
    ).get_json()
    bugometro = cliente.get(
        "/api/v1/telas/bugometro?jogo=cyberpunk-2077", headers=mundo["cabecalho"]
    ).get_json()

    assert isinstance(detalhe["bugs"], list)
    assert detalhe["bugs"] == bugometro["bugs"]
    assert {b["titulo"] for b in detalhe["bugs"]} == {
        "Crash ao entrar no metrô",
        "Textura sumindo",
    }


def test_comentario_oculto_some_ate_para_admin(cliente, mundo, app):
    """A tela pública se comporta igual para todo mundo — o mesmo que a
    home faz com tópicos ocultos. Moderação é outra tela."""
    from app.extensions import db
    from app.models import Avaliacao

    avaliacao = db.session.execute(db.select(Avaliacao)).scalars().first()
    avaliacao.oculto = True
    db.session.commit()

    admin = _cabecalho(cliente, "chefona")
    from app.models import Usuario

    conta = db.session.execute(
        db.select(Usuario).where(Usuario.nome_usuario == "chefona")
    ).scalars().first()
    conta.is_admin = True
    db.session.commit()

    corpo = cliente.get(
        "/api/v1/telas/jogo/cyberpunk-2077", headers=admin
    ).get_json()
    assert corpo["comentarios"] == []


def test_catalogo_acima_do_teto_de_pagina_nao_esconde_o_mais_instavel(
    cliente, mundo, app
):
    """`listar_entidades` corta em 100. Pedir 200 e receber 100 fazia o
    jogo mais instável sumir do bugômetro assim que o catálogo passava
    de 100 itens — resultado errado, não lento."""
    from app.composicao import montar_servicos
    from app.extensions import db
    from app.models import Usuario

    chefe = db.session.execute(
        db.select(Usuario).where(Usuario.nome_usuario == "chefe")
    ).scalars().first()
    servicos = montar_servicos()

    for indice in range(120):
        servicos.jogos.criar({"nome": f"Enchimento {indice:03d}"}, usuario=chefe)

    ultimo = servicos.jogos.criar({"nome": "Zumbi Instável"}, usuario=chefe)
    # Precisa ser inequivocamente o pior: o jogo do `mundo` já soma 39
    # (um relato crítico de 35 mais um leve de 4). Três críticos aqui
    # dão 100, o teto — sem margem para empate mascarar a falha.
    for indice in range(3):
        servicos.relatos_bug.criar(
            {
                "jogo_id": ultimo["id"],
                "titulo": f"Trava tudo {indice}",
                "categoria": "crash",
                "severidade": "critica",
            },
            usuario=chefe,
        )

    corpo = cliente.get(
        "/api/v1/telas/bugometro", headers=mundo["cabecalho"]
    ).get_json()
    assert corpo["jogo"]["slug"] == "zumbi-instavel"
    assert corpo["top_instaveis"][0]["slug"] == "zumbi-instavel"


def test_jogo_inexistente_e_404(cliente, mundo):
    resposta = cliente.get(
        "/api/v1/telas/jogo/nao-existe", headers=mundo["cabecalho"]
    )
    assert resposta.status_code == 404
    assert resposta.get_json() == {"erro": "Jogo não encontrado."}


def test_jogo_sem_token_e_401(cliente):
    assert cliente.get("/api/v1/telas/jogo/qualquer").status_code == 401


def test_data_de_lancamento_chega_a_tela_sem_reformatacao(cliente, mundo, app):
    """O Service repassa `data_lancamento` como está gravado.

    A coluna é `String(60)` livre. Quem grava é responsável pelo
    formato — o seed grava o formato da Steam (ex.: "27 out. 2022").
    Este teste trava o contrato antes de existir importador: se alguém
    acrescentar normalização no Service, precisa ser decisão consciente,
    não efeito colateral.
    """
    from app.extensions import db
    from app.models import Jogo

    jogo = db.session.execute(
        db.select(Jogo).where(Jogo.slug == "cyberpunk-2077")
    ).scalars().first()
    jogo.data_lancamento = "10/12/2020"
    db.session.commit()

    corpo = cliente.get(
        "/api/v1/telas/jogo/cyberpunk-2077", headers=mundo["cabecalho"]
    ).get_json()
    assert corpo["ultima_atualizacao"] == "10/12/2020"


def test_cartao_de_jogo_carrega_id(cliente, mundo):
    """Quatro das seis escritas das telas exigem `jogo_id`, e nenhum
    payload devolvia id — só slug. Não havia como resolver um pelo
    outro: a listagem do CRUD ignora `?slug=` em silêncio, devolvendo
    o catálogo inteiro com 200."""
    corpo = cliente.get(
        "/api/v1/telas/bugometro", headers=mundo["cabecalho"]
    ).get_json()
    assert isinstance(corpo["jogo"]["id"], int)
    for cartao in corpo["top_instaveis"]:
        assert isinstance(cartao["id"], int)


def test_detalhe_carrega_id(cliente, mundo):
    """A tela de detalhe relata bug e comenta: as duas escritas
    precisam de `jogo_id`."""
    corpo = cliente.get(
        "/api/v1/telas/jogo/cyberpunk-2077", headers=mundo["cabecalho"]
    ).get_json()
    assert isinstance(corpo["id"], int)


def test_bug_diz_se_o_usuario_ja_confirmou(cliente, mundo, app):
    """Sem este campo o botão de confirmar apareceria disponível em todo
    relato, e clicar num já votado levaria 409 pela unique
    (relato_id, usuario_id). É a mesma forma do bloqueador de `favorito`:
    estado do usuário ausente de um payload que o usuário vê."""
    from app.extensions import db
    from app.models import RelatoBug, Usuario, VotoBug

    comum = db.session.execute(
        db.select(Usuario).where(Usuario.nome_usuario == "gamer")
    ).scalars().first()
    relatos = db.session.execute(db.select(RelatoBug)).scalars().all()
    assert len(relatos) >= 2, "o cenário precisa de dois relatos"
    db.session.add(VotoBug(relato_id=relatos[0].id, usuario_id=comum.id))
    db.session.commit()

    corpo = cliente.get(
        "/api/v1/telas/bugometro", headers=mundo["cabecalho"]
    ).get_json()
    por_id = {b["id"]: b for b in corpo["bugs"]}
    assert por_id[relatos[0].id]["ja_confirmei"] is True
    assert por_id[relatos[1].id]["ja_confirmei"] is False


def test_ids_confirmados_por_respeita_o_filtro_de_relatos(mundo, app):
    """`ids_confirmados_por` usa `VotoBug.relato_id.in_(ids)` para não
    varrer TODOS os votos que o usuário já deu -- só os relevantes para
    a tela atual. Um teste com um voto só não observa essa filtragem:
    removê-la da consulta devolveria exatamente o mesmo resultado,
    porque o único voto que existe também é o único pedido. Aqui o
    usuário vota em relatos de DOIS jogos diferentes, e o conjunto
    devolvido para uma consulta que só pede o relato de UM dos jogos
    não pode conter o do outro, mesmo com o voto lá."""
    from app.extensions import db
    from app.models import RelatoBug, Usuario, VotoBug
    from app.repositories.voto_repository import RepositorioVotosBug

    comum = db.session.execute(
        db.select(Usuario).where(Usuario.nome_usuario == "gamer")
    ).scalars().first()

    relato_instavel = db.session.execute(
        db.select(RelatoBug).where(RelatoBug.jogo_id == mundo["instavel"]["id"])
    ).scalars().first()

    relato_calmo = RelatoBug(
        jogo_id=mundo["calmo"]["id"],
        titulo="Queda de FPS numa área específica",
        usuario_id=comum.id,
    )
    db.session.add(relato_calmo)
    db.session.commit()

    # O usuário confirma os dois -- de jogos diferentes.
    db.session.add(VotoBug(relato_id=relato_instavel.id, usuario_id=comum.id))
    db.session.add(VotoBug(relato_id=relato_calmo.id, usuario_id=comum.id))
    db.session.commit()

    repositorio = RepositorioVotosBug()
    resultado = repositorio.ids_confirmados_por(comum.id, [relato_instavel.id])

    assert resultado == {relato_instavel.id}
    assert relato_calmo.id not in resultado


def test_uma_consulta_para_todos_os_bugs_da_tela(cliente, mundo, app):
    """Um lookup por bug faria N consultas numa lista de 20. A revisão
    final da fase 1 cobrou exatamente essa forma no `favorito`."""
    from app.extensions import db

    chamadas = []
    from app.repositories.voto_repository import RepositorioVotosBug

    original = RepositorioVotosBug.ids_confirmados_por

    def espiao(self, usuario_id, relato_ids):
        chamadas.append(list(relato_ids))
        return original(self, usuario_id, relato_ids)

    RepositorioVotosBug.ids_confirmados_por = espiao
    try:
        cliente.get("/api/v1/telas/bugometro", headers=mundo["cabecalho"])
    finally:
        RepositorioVotosBug.ids_confirmados_por = original

    assert len(chamadas) == 1, f"chamou {len(chamadas)} vezes, deveria ser 1"
