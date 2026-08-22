import pytest
import uuid

from app.models import Alerta, Jogo, RelatoBug
from app.services.alerta_service import APRESENTACAO, AlertaService
from app.services.bugometro_service import PESOS_SEVERIDADE
from app.services.jogo_service import (
    CAPA_PADRAO,
    gerar_iniciais,
    gerar_slug,
    status_para,
)


@pytest.fixture
def admin(app):
    """Administrador REAL no banco.

    As FKs de autoria exigem que o usuário exista: um objeto inventado
    passaria pela autorização e quebraria no INSERT.
    """
    from app.extensions import db
    from app.models import Usuario

    usuario = Usuario(nome_usuario="chefe", email="chefe@l.dev", is_admin=True)
    usuario.definir_senha("senha123")
    db.session.add(usuario)
    db.session.commit()
    return usuario


def _eleitor(numero):
    """Cria um usuário comum, para os testes de confirmação de bug."""
    from app.extensions import db
    from app.models import Usuario

    usuario = Usuario(nome_usuario=f"eleitor{numero}", email=f"e{numero}@l.dev")
    usuario.definir_senha("senha123")
    db.session.add(usuario)
    db.session.commit()
    return usuario


# ------------------------------------------------------- slug e iniciais
@pytest.mark.parametrize(
    "nome, esperado",
    [
        ("Hollow Knight", "hollow-knight"),
        ("Call of Duty®", "call-of-duty"),
        ("Ação e Aventura", "acao-e-aventura"),
        ("  Espaços   Demais  ", "espacos-demais"),
    ],
)
def test_gerar_slug(nome, esperado):
    assert gerar_slug(nome) == esperado


def test_slug_tem_teto_de_140_caracteres():
    assert len(gerar_slug("a " * 200)) <= 140


@pytest.mark.parametrize(
    "nome, esperado",
    [
        ("Hollow Knight", "HK"),
        ("Celeste", "C"),
        ("Grand Theft Auto V", "GT"),
        ("", ""),
    ],
)
def test_gerar_iniciais_usa_a_primeira_letra_das_duas_primeiras_palavras(
    nome, esperado
):
    assert gerar_iniciais(nome) == esperado


def test_iniciais_tem_teto_de_4_caracteres():
    assert len(gerar_iniciais("Um Dois Três Quatro Cinco")) <= 4


# ------------------------------------------------------------- status_para
@pytest.mark.parametrize(
    "pontuacao, nivel",
    [
        (100, "critical"),
        (80, "critical"),   # caso do catalog/tests.py:211
        (65, "critical"),   # limiar exato
        (64, "warning"),
        (50, "warning"),    # caso do catalog/tests.py:212
        (40, "warning"),    # limiar exato
        (39, "stable"),
        (10, "stable"),     # caso do catalog/tests.py:213
        (0, "stable"),
    ],
)
def test_status_para_respeita_os_limiares_65_e_40(pontuacao, nivel):
    assert status_para(pontuacao)["nivel"] == nivel


def test_status_para_traz_rotulo_em_portugues():
    assert status_para(80)["rotulo"] == "Crítico"
    assert status_para(50)["rotulo"] == "Instável"
    assert status_para(10)["rotulo"] == "Estável"


# -------------------------------------------------- pontuação do bugômetro
def _jogo_com_relatos(sessao, relatos):
    slug_unico = f"teste-{uuid.uuid4().hex[:8]}"
    jogo = Jogo(nome="Teste", slug=slug_unico)
    sessao.add(jogo)
    sessao.commit()
    for severidade, status, confirmacoes in relatos:
        sessao.add(
            RelatoBug(
                jogo_id=jogo.id,
                titulo="bug",
                severidade=severidade,
                status=status,
                confirmacoes=confirmacoes,
            )
        )
    sessao.commit()
    return jogo


def test_pesos_de_severidade_sao_os_do_django():
    assert PESOS_SEVERIDADE == {"baixa": 4, "media": 10, "alta": 20, "critica": 35}


def test_jogo_sem_relatos_tem_pontuacao_zero(app, sessao):
    from app.composicao import montar_servicos

    jogo = _jogo_com_relatos(sessao, [])
    assert montar_servicos().bugometro.calcular_pontuacao(jogo) == 0


def test_um_relato_medio_aberto_sem_confirmacoes_vale_10(app, sessao):
    from app.composicao import montar_servicos

    jogo = _jogo_com_relatos(sessao, [("media", "aberto", 0)])
    assert montar_servicos().bugometro.calcular_pontuacao(jogo) == 10


def test_confirmado_multiplica_por_1_ponto_5(app, sessao):
    from app.composicao import montar_servicos

    jogo = _jogo_com_relatos(sessao, [("media", "confirmado", 0)])
    assert montar_servicos().bugometro.calcular_pontuacao(jogo) == 15


def test_confirmacoes_saturam_em_20(app, sessao):
    """conf_boost = 1 + min(confirmacoes, 20)/20, teto 2.0."""
    from app.composicao import montar_servicos

    servico = montar_servicos().bugometro
    com_20 = _jogo_com_relatos(sessao, [("baixa", "aberto", 20)])
    assert servico.calcular_pontuacao(com_20) == 8  # 4 * 1.0 * 2.0

    com_100 = _jogo_com_relatos(sessao, [("baixa", "aberto", 100)])
    assert servico.calcular_pontuacao(com_100) == 8


def test_severidade_desconhecida_usa_peso_10(app, sessao):
    from app.composicao import montar_servicos

    jogo = _jogo_com_relatos(sessao, [("inventada", "aberto", 0)])
    assert montar_servicos().bugometro.calcular_pontuacao(jogo) == 10


def test_relato_resolvido_nao_conta(app, sessao):
    from app.composicao import montar_servicos

    jogo = _jogo_com_relatos(
        sessao, [("critica", "resolvido", 0), ("critica", "rejeitado", 0)]
    )
    assert montar_servicos().bugometro.calcular_pontuacao(jogo) == 0


def test_pontuacao_tem_teto_de_100(app, sessao):
    """Um crítico confirmado com 20 confirmações vale 105 sozinho."""
    from app.composicao import montar_servicos

    jogo = _jogo_com_relatos(sessao, [("critica", "confirmado", 20)])
    assert montar_servicos().bugometro.calcular_pontuacao(jogo) == 100


def test_recalcular_persiste_o_status_do_bugometro(app, sessao):
    from app.composicao import montar_servicos

    servico = montar_servicos().bugometro
    jogo = _jogo_com_relatos(sessao, [("critica", "confirmado", 5)])
    pontuacao = servico.recalcular(jogo)

    assert jogo.bugometro is not None
    assert jogo.bugometro.pontuacao == pontuacao
    assert jogo.bugometro.status == status_para(pontuacao)["nivel"]


# ------------------------------------------------------- métricas por card
def test_metricas_devolvem_sempre_os_4_cards_na_ordem(app, sessao):
    from app.composicao import montar_servicos

    jogo = _jogo_com_relatos(sessao, [])
    metricas = montar_servicos().bugometro.montar_metricas(jogo)
    assert [m["chave"] for m in metricas] == ["crash", "bugs", "stutter", "fps"]


def test_card_sem_bugs_e_baixo_e_estavel(app, sessao):
    from app.composicao import montar_servicos

    jogo = _jogo_com_relatos(sessao, [])
    for metrica in montar_servicos().bugometro.montar_metricas(jogo):
        assert metrica["valor"] == "Baixo"
        assert metrica["nivel"] == "stable"


def test_severidade_alta_torna_o_card_critico(app, sessao):
    from app.composicao import montar_servicos

    jogo = Jogo(nome="X", slug="x")
    sessao.add(jogo)
    sessao.commit()
    sessao.add(
        RelatoBug(jogo_id=jogo.id, titulo="b", categoria="crash", severidade="alta")
    )
    sessao.commit()

    metricas = {m["chave"]: m for m in montar_servicos().bugometro.montar_metricas(jogo)}
    assert metricas["crash"]["valor"] == "Alto"
    assert metricas["crash"]["nivel"] == "critical"


def test_cinco_bugs_leves_tambem_tornam_o_card_critico(app, sessao):
    from app.composicao import montar_servicos

    jogo = Jogo(nome="Y", slug="y")
    sessao.add(jogo)
    sessao.commit()
    for _ in range(5):
        sessao.add(
            RelatoBug(
                jogo_id=jogo.id, titulo="b", categoria="crash", severidade="baixa"
            )
        )
    sessao.commit()

    metricas = {m["chave"]: m for m in montar_servicos().bugometro.montar_metricas(jogo)}
    assert metricas["crash"]["nivel"] == "critical"


def test_grafico_tem_24_rotulos_e_4_series(app):
    from app.composicao import montar_servicos

    grafico = montar_servicos().bugometro.montar_grafico()
    assert len(grafico["rotulos"]) == 24
    assert grafico["rotulos"][0] == "06h"
    assert len(grafico["series"]) == 4
    for serie in grafico["series"]:
        assert len(serie["dados"]) == 24


# ---------------------------------------------------------------- alertas
def test_mapa_de_apresentacao_do_alerta():
    assert APRESENTACAO == {
        "critica": ("CRÍTICO", "critical", "wifi"),
        "instavel": ("INSTÁVEL", "warning", "alert"),
        "atualizacao": ("Atualização", "stable", "check"),
    }


def test_atualizacao_vira_nivel_stable_e_nao_update(app, sessao):
    """A assimetria: severidade 'atualizacao' tem nível 'stable'. Não existe
    classe .badge--update no CSS."""
    jogo = Jogo(nome="Z", slug="z")
    sessao.add(jogo)
    sessao.commit()
    alerta = Alerta(jogo_id=jogo.id, severidade="atualizacao", texto="patch")
    sessao.add(alerta)
    sessao.commit()

    apresentado = AlertaService.apresentar(alerta)
    assert apresentado["nivel"] == "stable"
    assert apresentado["severidade"] == "Atualização"
    assert apresentado["icone"] == "check"


def test_severidade_desconhecida_cai_no_fallback_critico(app, sessao):
    jogo = Jogo(nome="W", slug="w")
    sessao.add(jogo)
    sessao.commit()
    alerta = Alerta(jogo_id=jogo.id, severidade="inventada", texto="x")
    sessao.add(alerta)
    sessao.commit()

    apresentado = AlertaService.apresentar(alerta)
    assert apresentado["nivel"] == "critical"
    assert apresentado["icone"] == "wifi"


# ------------------------------------------------------------ card de jogo
def test_card_de_jogo_tem_o_shape_canonico(app, sessao):
    from app.composicao import montar_servicos

    jogo = Jogo(nome="Hollow Knight")
    sessao.add(jogo)
    sessao.commit()

    card = montar_servicos().jogos.montar_card(jogo)
    assert set(card) == {
        "slug", "nome", "pontuacao", "iniciais", "capa", "imagem_capa",
        "arquivo_capa", "favorito", "na_biblioteca", "status",
    }


def test_capa_vazia_recebe_o_gradiente_padrao(app, sessao):
    """Armadilha: array vazio é truthy em JS, então o fallback tem que ser
    aplicado aqui, no servidor."""
    from app.composicao import montar_servicos

    jogo = Jogo(nome="Sem Capa", capa_gradiente=[])
    sessao.add(jogo)
    sessao.commit()

    card = montar_servicos().jogos.montar_card(jogo)
    assert card["capa"] == CAPA_PADRAO
    assert len(card["capa"]) == 2


def test_criar_jogo_gera_slug_e_iniciais(app, admin):
    from app.composicao import montar_servicos

    criado = montar_servicos().jogos.criar({"nome": "Hollow Knight"}, usuario=admin)
    assert criado["slug"] == "hollow-knight"
    assert criado["iniciais"] == "HK"


# ------------------------------- ponto único de recálculo (spec 4.1.1)
def test_criar_relato_pela_api_ja_move_a_pontuacao(app, sessao, admin):
    """Sem signals, o recálculo é explícito. Se não estiver ligado às
    escritas, a pontuação nunca sai de zero — e sem erro nenhum."""
    from app.composicao import montar_servicos
    from app.models import Jogo

    servicos = montar_servicos()
    jogo = Jogo(nome="Cyberpunk", slug="cyberpunk")
    sessao.add(jogo)
    sessao.commit()

    servicos.relatos_bug.criar(
        {"jogo_id": jogo.id, "titulo": "Crash", "severidade": "critica"},
        usuario=admin,
    )

    sessao.refresh(jogo)
    assert jogo.bugometro is not None
    assert jogo.bugometro.pontuacao == 35
    assert jogo.bugometro.status == "stable"


def test_remover_relato_devolve_a_pontuacao_para_zero(app, sessao, admin):
    from app.composicao import montar_servicos
    from app.models import Jogo

    servicos = montar_servicos()
    jogo = Jogo(nome="Anthem", slug="anthem")
    sessao.add(jogo)
    sessao.commit()

    relato = servicos.relatos_bug.criar(
        {"jogo_id": jogo.id, "titulo": "Crash", "severidade": "critica"},
        usuario=admin,
    )
    servicos.relatos_bug.remover(relato["id"], admin)

    sessao.refresh(jogo)
    assert jogo.bugometro.pontuacao == 0


def test_votar_incrementa_confirmacoes_e_recalcula(app, sessao, admin):
    from app.composicao import montar_servicos
    from app.models import Jogo

    servicos = montar_servicos()
    jogo = Jogo(nome="No Man's Sky", slug="no-mans-sky")
    sessao.add(jogo)
    sessao.commit()

    relato = servicos.relatos_bug.criar(
        {"jogo_id": jogo.id, "titulo": "Textura", "severidade": "media"},
        usuario=admin,
    )
    assert jogo.bugometro.pontuacao == 10

    servicos.votos_bug.criar({"relato_id": relato["id"]}, usuario=admin)

    sessao.expire_all()
    atualizado = servicos.relatos_bug.obter(relato["id"])
    assert atualizado["confirmacoes"] == 1
    # 10 * 1.0 * (1 + 1/20) = 10.5 -> arredonda para 10
    assert jogo.bugometro.pontuacao == 10

    for numero in range(10):
        servicos.votos_bug.criar(
            {"relato_id": relato["id"]}, usuario=_eleitor(numero)
        )

    sessao.expire_all()
    # 11 votos: 10 * (1 + 11/20) = 15.5 -> 16
    assert jogo.bugometro.pontuacao == 16


def test_confirmar_bug_pela_api_ponta_a_ponta(app, sessao):
    """Exercita a pilha HTTP inteira, não o Service direto.

    Um Service especializado que sobrescreva `criar` com a assinatura
    antiga passa em todo teste de unidade — porque os testes chamam o
    Service direto — e devolve 500 pela API, porque o `crud_factory`
    chama com `usuario=`. Só um teste por HTTP pega isso.
    """
    from app.extensions import db
    from app.models import Jogo

    cliente = app.test_client()
    entrada = cliente.post(
        "/api/auth/registro",
        json={"nome_usuario": "votante", "email": "vt@l.dev", "senha": "senha123"},
    ).get_json()
    cabecalho = {"Authorization": f"Bearer {entrada['token_acesso']}"}

    jogo = Jogo(nome="Cyberpunk", slug="cyberpunk-api")
    db.session.add(jogo)
    db.session.commit()

    relato = cliente.post(
        "/api/v1/relatos-bug",
        json={"jogo_id": jogo.id, "titulo": "Crash", "severidade": "media"},
        headers=cabecalho,
    )
    assert relato.status_code == 201, relato.get_json()
    relato_id = relato.get_json()["id"]

    voto = cliente.post(
        "/api/v1/votos-bug", json={"relato_id": relato_id}, headers=cabecalho
    )
    assert voto.status_code == 201, voto.get_json()

    repetido = cliente.post(
        "/api/v1/votos-bug", json={"relato_id": relato_id}, headers=cabecalho
    )
    assert repetido.status_code == 409


def test_services_especializados_nao_afrouxam_a_autorizacao(app):
    """Sobrescrever `criar` num Service especializado não pode desligar a
    porta que o ServicoBase impõe. Já aconteceu: uma adaptação bem
    intencionada removeu a checagem de dois services de uma vez."""
    from app.composicao import montar_servicos
    from app.errors import NaoAutorizado

    servicos = montar_servicos()
    for nome in ("jogos", "relatos_bug", "votos_bug", "alertas"):
        with pytest.raises(NaoAutorizado):
            getattr(servicos, nome).criar({}, usuario=None)


def test_votar_duas_vezes_no_mesmo_relato_e_conflito(app, sessao, admin):
    import pytest as _pytest

    from app.composicao import montar_servicos
    from app.errors import Conflito
    from app.models import Jogo

    servicos = montar_servicos()
    jogo = Jogo(nome="Fallout 76", slug="fallout-76")
    sessao.add(jogo)
    sessao.commit()

    relato = servicos.relatos_bug.criar(
        {"jogo_id": jogo.id, "titulo": "Bug", "severidade": "baixa"},
        usuario=admin,
    )
    servicos.votos_bug.criar({"relato_id": relato["id"]}, usuario=admin)

    with _pytest.raises(Conflito) as excecao:
        servicos.votos_bug.criar({"relato_id": relato["id"]}, usuario=admin)
    assert excecao.value.status == 409
