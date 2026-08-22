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
    assert len(niveis) >= 2


# --- idempotência -------------------------------------------------------

def test_semear_duas_vezes_nao_duplica(app, semeado):
    """Rodar o seed de novo é o reflexo natural de quem está explorando
    o projeto — não pode dobrar o catálogo."""
    from app.extensions import db
    from app.models import Jogo, Usuario
    from app.seed import semear

    semear(silencioso=True)

    assert db.session.execute(db.select(db.func.count()).select_from(Jogo)).scalar_one() == 26
    assert db.session.execute(
        db.select(db.func.count()).select_from(Usuario)
    ).scalar_one() == 2


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
