import pytest


@pytest.fixture
def semeado(app):
    from app.seed import semear

    return semear(silencioso=True)


# --- carga dos jogos ----------------------------------------------------

def test_carregar_jogos_le_o_arquivo_real():
    """26 jogos reais da Steam, preservados da aplicação antiga."""
    from app.seed import carregar_jogos

    jogos = carregar_jogos()
    assert len(jogos) == 26
    assert all("name" in j for j in jogos)


def test_semear_cria_os_26_jogos(app, semeado):
    from app.extensions import db
    from app.models import Jogo

    assert semeado["jogos"] == 26
    assert db.session.execute(db.select(db.func.count()).select_from(Jogo)).scalar_one() == 26


def test_campos_do_jogo_sao_traduzidos_do_ingles(app, semeado):
    """O arquivo veio da aplicação antiga, com chaves em inglês."""
    from app.extensions import db
    from app.models import Jogo

    jogo = db.session.execute(
        db.select(Jogo).where(Jogo.nome.like("Call of Duty%"))
    ).scalars().first()

    assert jogo is not None
    assert jogo.curtidas == 73430
    assert jogo.descurtidas == 4079
    assert jogo.conquistas == 157
    assert jogo.publicadora == "Activision"
    assert jogo.data_lancamento == "27 out. 2022"
    assert jogo.capa_gradiente == ["#c07f2a", "#241608"]


def test_slug_e_iniciais_sao_gerados(app, semeado):
    """O arquivo traz `slug` vazio e não traz iniciais."""
    from app.extensions import db
    from app.models import Jogo

    for jogo in db.session.execute(db.select(Jogo)).scalars().all():
        assert jogo.slug, jogo.nome
        assert jogo.iniciais, jogo.nome


def test_slugs_sao_unicos(app, semeado):
    from app.extensions import db
    from app.models import Jogo

    slugs = [j.slug for j in db.session.execute(db.select(Jogo)).scalars().all()]
    assert len(slugs) == len(set(slugs))


def test_generos_viram_entidades_ligadas(app, semeado):
    """A tela de exploração filtra por gênero, então ele precisa ser
    entidade, não string."""
    from app.extensions import db
    from app.models import Genero, JogoGenero

    assert semeado["generos"] > 0
    assert db.session.execute(
        db.select(db.func.count()).select_from(JogoGenero)
    ).scalar_one() > 0

    acao = db.session.execute(
        db.select(Genero).where(Genero.nome == "Ação")
    ).scalars().first()
    assert acao is not None
    assert acao.slug == "acao"


# --- contas -------------------------------------------------------------

def test_cria_conta_demo_e_administrador(app, semeado):
    from app.extensions import db
    from app.models import Usuario
    from app.seed import ADMIN_DEMO, SENHA_DEMO, USUARIO_DEMO

    demo = db.session.execute(
        db.select(Usuario).where(Usuario.nome_usuario == USUARIO_DEMO)
    ).scalars().first()
    admin = db.session.execute(
        db.select(Usuario).where(Usuario.nome_usuario == ADMIN_DEMO)
    ).scalars().first()

    assert demo is not None and demo.checar_senha(SENHA_DEMO)
    assert demo.is_admin is False
    assert admin is not None and admin.is_admin is True


def test_administrador_do_seed_consegue_cadastrar_jogo(app, semeado):
    """Sem isso, quem roda o seed ainda precisaria do `flask promover`."""
    from app.composicao import montar_servicos
    from app.extensions import db
    from app.models import Usuario
    from app.seed import ADMIN_DEMO

    admin = db.session.execute(
        db.select(Usuario).where(Usuario.nome_usuario == ADMIN_DEMO)
    ).scalars().first()

    criado = montar_servicos().jogos.criar({"nome": "Jogo Novo"}, usuario=admin)
    assert criado["slug"] == "jogo-novo"


def test_usuarios_totalizam_quatorze_apos_o_seed(app, semeado):
    """`gamer` + `moderador` + o pool de 12 votantes (defeito 3): sem
    usuários reais por trás de cada voto, `confirmacoes` não pode ser
    uma contagem de verdade — `VotoBug` exige um `usuario_id` distinto
    por relato."""
    from app.extensions import db
    from app.models import Usuario

    total = db.session.execute(
        db.select(db.func.count()).select_from(Usuario)
    ).scalar_one()
    assert total == 14


# --- conteúdo -----------------------------------------------------------

def test_biblioteca_tem_tempo_e_progresso_reais(app, semeado):
    """A tela de perfil mostra esses números. Zerados, ela nasce vazia."""
    from app.extensions import db
    from app.models import BibliotecaUsuario

    entradas = db.session.execute(db.select(BibliotecaUsuario)).scalars().all()
    assert len(entradas) >= 5
    assert any(e.favorito for e in entradas)
    assert any(e.minutos_jogados > 0 for e in entradas)
    assert any(e.progresso > 0 for e in entradas)


def test_forum_tem_topicos_e_respostas(app, semeado):
    from app.extensions import db
    from app.models import Post, Topico

    assert db.session.execute(db.select(db.func.count()).select_from(Topico)).scalar_one() >= 3
    assert db.session.execute(db.select(db.func.count()).select_from(Post)).scalar_one() >= 2


def test_topicos_cobrem_os_quatro_tipos(app, semeado):
    """A tela mostra um badge colorido por tipo; com um tipo só, três
    cores nunca aparecem."""
    from app.extensions import db
    from app.models import Topico

    tipos = {
        t.tipo for t in db.session.execute(db.select(Topico)).scalars().all()
    }
    assert tipos == {"discussao", "bug", "dica", "noticia"}


def test_alertas_cobrem_as_tres_severidades(app, semeado):
    """Mesma razão: o resumo da tela tem três chips."""
    from app.extensions import db
    from app.models import Alerta

    severidades = {
        a.severidade for a in db.session.execute(db.select(Alerta)).scalars().all()
    }
    assert severidades == {"critica", "instavel", "atualizacao"}


def test_relatos_cobrem_as_quatro_severidades(app, semeado):
    from app.extensions import db
    from app.models import RelatoBug

    severidades = {
        r.severidade
        for r in db.session.execute(db.select(RelatoBug)).scalars().all()
    }
    assert severidades == {"baixa", "media", "alta", "critica"}


def test_confirmacoes_batem_com_os_votos_gravados(app, semeado):
    """Defeito 3 da revisão: o seed gravava `confirmacoes` sem os votos
    correspondentes em `votos_bug`. `confirmacoes` é contagem derivada
    (mesma regra de `voto_service._sincronizar`) — nunca um literal."""
    from app.extensions import db
    from app.models import RelatoBug, VotoBug

    relatos = db.session.execute(db.select(RelatoBug)).scalars().all()
    assert relatos, "seed precisa gravar ao menos um relato"
    for relato in relatos:
        votos_reais = db.session.execute(
            db.select(db.func.count())
            .select_from(VotoBug)
            .where(VotoBug.relato_id == relato.id)
        ).scalar_one()
        assert relato.confirmacoes == votos_reais


def test_pontuacao_do_bugometro_e_recalculada(app, semeado):
    """O seed grava relatos direto no banco, então precisa disparar o
    recálculo explicitamente — não há signal para fazer isso."""
    from app.extensions import db
    from app.models import BugometroStatus

    status = db.session.execute(db.select(BugometroStatus)).scalars().all()
    assert status, "nenhum jogo teve a pontuação calculada"
    assert any(s.pontuacao > 0 for s in status)
    for s in status:
        assert s.status in {"critical", "warning", "stable"}


def test_ha_jogo_em_cada_faixa_de_estabilidade(app, semeado):
    """A tela do bugômetro mostra três cores. Se todos os jogos ficarem
    na mesma faixa, duas nunca aparecem."""
    from app.extensions import db
    from app.models import BugometroStatus

    niveis = {
        s.status
        for s in db.session.execute(db.select(BugometroStatus)).scalars().all()
    }
    assert niveis == {"critical", "warning", "stable"}


# --- idempotência -------------------------------------------------------

def test_semear_duas_vezes_nao_duplica(app, semeado):
    """Rodar o seed de novo é o reflexo natural de quem está explorando
    o projeto — não pode dobrar o catálogo."""
    from app.extensions import db
    from app.models import (
        Alerta, Avaliacao, BibliotecaUsuario, Jogo, JogoGenero, Post,
        RelatoBug, Topico, Usuario, VotoBug,
    )
    from app.seed import semear

    # Captura contagem antes da segunda rodada
    contagem_antes = {
        "jogo": db.session.execute(db.select(db.func.count()).select_from(Jogo)).scalar_one(),
        "usuario": db.session.execute(db.select(db.func.count()).select_from(Usuario)).scalar_one(),
        "topico": db.session.execute(db.select(db.func.count()).select_from(Topico)).scalar_one(),
        "post": db.session.execute(db.select(db.func.count()).select_from(Post)).scalar_one(),
        "alerta": db.session.execute(db.select(db.func.count()).select_from(Alerta)).scalar_one(),
        "relato": db.session.execute(db.select(db.func.count()).select_from(RelatoBug)).scalar_one(),
        # Pool de votantes e votos são novos nesta revisão (defeito 3):
        # rodar de novo não pode duplicar nem contas nem votos.
        "voto": db.session.execute(db.select(db.func.count()).select_from(VotoBug)).scalar_one(),
        "avaliacao": db.session.execute(db.select(db.func.count()).select_from(Avaliacao)).scalar_one(),
        "biblioteca": db.session.execute(db.select(db.func.count()).select_from(BibliotecaUsuario)).scalar_one(),
        "jogo_genero": db.session.execute(db.select(db.func.count()).select_from(JogoGenero)).scalar_one(),
    }

    semear(silencioso=True)

    assert db.session.execute(db.select(db.func.count()).select_from(Jogo)).scalar_one() == contagem_antes["jogo"]
    assert db.session.execute(db.select(db.func.count()).select_from(Usuario)).scalar_one() == contagem_antes["usuario"]
    assert db.session.execute(db.select(db.func.count()).select_from(Topico)).scalar_one() == contagem_antes["topico"]
    assert db.session.execute(db.select(db.func.count()).select_from(Post)).scalar_one() == contagem_antes["post"]
    assert db.session.execute(db.select(db.func.count()).select_from(Alerta)).scalar_one() == contagem_antes["alerta"]
    assert db.session.execute(db.select(db.func.count()).select_from(RelatoBug)).scalar_one() == contagem_antes["relato"]
    assert db.session.execute(db.select(db.func.count()).select_from(VotoBug)).scalar_one() == contagem_antes["voto"]
    assert db.session.execute(db.select(db.func.count()).select_from(Avaliacao)).scalar_one() == contagem_antes["avaliacao"]
    assert db.session.execute(db.select(db.func.count()).select_from(BibliotecaUsuario)).scalar_one() == contagem_antes["biblioteca"]
    assert db.session.execute(db.select(db.func.count()).select_from(JogoGenero)).scalar_one() == contagem_antes["jogo_genero"]


# --- voto real pela API, sobre relato semeado ---------------------------

def _registrar(cliente, nome):
    return cliente.post(
        "/api/auth/registro",
        json={"nome_usuario": nome, "email": f"{nome}@l.dev", "senha": "senha123"},
    ).get_json()


def test_votar_num_relato_semeado_pela_api_soma_em_vez_de_derrubar(app, cliente, semeado):
    """Reprodução do defeito 3: com `confirmacoes` gravado sem votos
    correspondentes, o primeiro voto real pela API SUBSTITUÍA um número
    inflado por uma contagem real menor — a confirmação parecia apagar
    votos em vez de somar. Com o pool de votantes do seed, o relato já
    nasce com confirmações reais, e um voto novo só soma."""
    from app.extensions import db
    from app.models import RelatoBug

    relato = db.session.execute(
        db.select(RelatoBug).where(RelatoBug.titulo == "Crash ao entrar no metrô")
    ).scalars().first()
    assert relato is not None
    antes = relato.confirmacoes
    assert antes > 0, "o seed precisa ter gravado votos reais para este relato"

    dados = _registrar(cliente, "recemchegado")
    cabecalho = {"Authorization": f"Bearer {dados['token_acesso']}"}

    resposta = cliente.post(
        "/api/v1/votos-bug", json={"relato_id": relato.id}, headers=cabecalho
    )
    assert resposta.status_code == 201

    db.session.refresh(relato)
    assert relato.confirmacoes == antes + 1


def test_tres_faixas_sobrevivem_a_um_voto_pela_api(app, cliente, semeado):
    """As três faixas (critical/warning/stable) do banco semeado
    continuam presentes depois de um voto real — não é um estado que só
    existe antes de alguém confirmar um bug pela API.

    O voto é no relato do counter-strike de propósito: é o único jogo na
    faixa `warning`, e o único cujo voto discrimina. Votar no relato do
    call-of-duty não prova nada — a pontuação dele já está no teto de
    100, então a faixa dele sobrevive a qualquer coisa, inclusive ao
    defeito que este teste existe para pegar.
    """
    from app.extensions import db
    from app.models import BugometroStatus, RelatoBug

    relato = db.session.execute(
        db.select(RelatoBug).where(RelatoBug.titulo == "Textura sumindo em Mirage")
    ).scalars().first()
    assert relato is not None

    dados = _registrar(cliente, "outrovotante")
    cabecalho = {"Authorization": f"Bearer {dados['token_acesso']}"}

    resposta = cliente.post(
        "/api/v1/votos-bug", json={"relato_id": relato.id}, headers=cabecalho
    )
    assert resposta.status_code == 201

    niveis = {
        s.status
        for s in db.session.execute(db.select(BugometroStatus)).scalars().all()
    }
    assert niveis == {"critical", "warning", "stable"}


# --- as telas nascem com conteúdo --------------------------------------

def test_telas_principais_nao_nascem_vazias(app, semeado):
    """O objetivo do seed: abrir o app e ver algo."""
    from app.models import Usuario
    from app.extensions import db
    from app.seed import SENHA_DEMO, USUARIO_DEMO

    cliente = app.test_client()
    entrada = cliente.post(
        "/api/auth/login",
        json={"identificador": USUARIO_DEMO, "senha": SENHA_DEMO},
    ).get_json()
    cabecalho = {"Authorization": f"Bearer {entrada['token_acesso']}"}

    inicio = cliente.get("/api/v1/telas/inicio", headers=cabecalho).get_json()
    assert inicio["banners"] and inicio["atualizacoes"] and inicio["favoritos"]

    bugometro = cliente.get("/api/v1/telas/bugometro", headers=cabecalho).get_json()
    assert bugometro["bugs"] and bugometro["top_instaveis"]

    comunidade = cliente.get("/api/v1/telas/comunidade", headers=cabecalho).get_json()
    assert comunidade["topicos"] and comunidade["selecionado"]

    alertas = cliente.get("/api/v1/telas/alertas", headers=cabecalho).get_json()
    assert alertas["alertas"] and alertas["favoritos"]

    biblioteca = cliente.get("/api/v1/telas/biblioteca", headers=cabecalho).get_json()
    assert biblioteca["total"] >= 5

    perfil = cliente.get("/api/v1/telas/perfil", headers=cabecalho).get_json()
    assert perfil["jogos_recentes"]
