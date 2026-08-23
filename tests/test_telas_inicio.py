from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.services.formatacao import tempo_relativo
from test_frontend import _sem_comentarios

RAIZ = Path(__file__).resolve().parent.parent


# ------------------------------------------------------------ formatação
@pytest.mark.parametrize(
    "delta, esperado",
    [
        (timedelta(seconds=5), "agora mesmo"),
        (timedelta(minutes=1), "há 1 minuto"),
        (timedelta(minutes=3), "há 3 minutos"),
        (timedelta(hours=1), "há 1 hora"),
        (timedelta(hours=5), "há 5 horas"),
        (timedelta(days=1), "há 1 dia"),
        (timedelta(days=2), "há 2 dias"),
        (timedelta(days=40), "há 1 mês"),
        (timedelta(days=90), "há 3 meses"),
        (timedelta(days=400), "há 1 ano"),
    ],
)
def test_tempo_relativo_em_portugues(delta, esperado):
    agora = datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc)
    assert tempo_relativo(agora - delta, agora_utc=agora) == esperado


def test_tempo_relativo_aceita_datetime_ingenuo():
    """As colunas DateTime do SQLAlchemy voltam sem tzinfo."""
    agora = datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc)
    ingenuo = datetime(2026, 8, 22, 11, 57)
    assert tempo_relativo(ingenuo, agora_utc=agora) == "há 3 minutos"


@pytest.mark.parametrize(
    "delta, esperado",
    [
        (timedelta(seconds=59), "agora mesmo"),
        (timedelta(seconds=61), "há 1 minuto"),
        (timedelta(hours=23, minutes=59), "há 23 horas"),
        (timedelta(days=29), "há 29 dias"),
        (timedelta(days=30), "há 1 mês"),
        (timedelta(days=364), "há 12 meses"),
        (timedelta(days=365), "há 1 ano"),
    ],
)
def test_tempo_relativo_nas_fronteiras_de_escala(delta, esperado):
    """As fronteiras são onde um `>` trocado por `>=` passaria batido."""
    agora = datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc)
    assert tempo_relativo(agora - delta, agora_utc=agora) == esperado


def test_tempo_relativo_no_futuro_nao_quebra():
    """Relógio dessincronizado entre servidores produz data futura."""
    agora = datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc)
    assert tempo_relativo(agora + timedelta(minutes=5), agora_utc=agora) == "agora mesmo"


def test_listar_entidades_esconde_oculto_por_padrao(app, sessao):
    """A armadilha que isto fecha: quem compõe teria de lembrar do filtro
    toda vez, e esquecer uma vez vaza conteúdo moderado na tela."""
    from app.composicao import montar_servicos
    from app.models import Topico, Usuario

    autor = Usuario(nome_usuario="autor", email="a@l.dev")
    autor.definir_senha("senha123")
    sessao.add(autor)
    sessao.commit()

    sessao.add(Topico(titulo="Visível", usuario_id=autor.id))
    sessao.add(Topico(titulo="Escondido", usuario_id=autor.id, oculto=True))
    sessao.commit()

    servicos = montar_servicos()
    titulos = [t.titulo for t in servicos.topicos.listar_entidades()]
    assert titulos == ["Visível"]


def test_listar_entidades_mostra_oculto_para_admin(app, sessao):
    from types import SimpleNamespace

    from app.composicao import montar_servicos
    from app.models import Topico, Usuario

    autor = Usuario(nome_usuario="autor", email="a@l.dev")
    autor.definir_senha("senha123")
    sessao.add(autor)
    sessao.commit()
    sessao.add(Topico(titulo="Escondido", usuario_id=autor.id, oculto=True))
    sessao.commit()

    servicos = montar_servicos()
    admin = SimpleNamespace(id=99, is_admin=True)
    assert len(servicos.topicos.listar_entidades(usuario=admin)) == 1


def test_formatacao_nao_importa_flask():
    """Olha os imports via `ast`, não o texto do arquivo."""
    import ast

    import app.services.formatacao as modulo

    arvore = ast.parse(open(modulo.__file__, encoding="utf-8").read())
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            for alias in no.names:
                assert not alias.name.startswith("flask"), alias.name
        if isinstance(no, ast.ImportFrom):
            assert not (no.module or "").startswith("flask"), no.module


# ------------------------------------------------------------------- /eu
def _registrar(cliente, nome="gamer"):
    return cliente.post(
        "/api/auth/registro",
        json={"nome_usuario": nome, "email": f"{nome}@l.dev", "senha": "senha123"},
    ).get_json()


def test_eu_devolve_o_shape_do_shell(cliente):
    dados = _registrar(cliente)
    cabecalho = {"Authorization": f"Bearer {dados['token_acesso']}"}

    corpo = cliente.get("/api/v1/eu", headers=cabecalho).get_json()
    assert set(corpo) == {
        "id", "nome_usuario", "apelido", "email", "nivel", "xp", "xp_max",
        "cor_avatar", "bio", "conquistas", "amigos", "dias_ativo", "avatar_url",
        "idade",
    }


def test_eu_devolve_a_idade(cliente, app):
    """Sem `idade` no shape, a tela de Configuração não tem como
    preencher o campo — ele nasce vazio mesmo depois de salvo, e a
    pessoa acha que não salvou."""
    from app.extensions import db
    from app.models import Usuario

    dados = _registrar(cliente)
    usuario = db.session.get(Usuario, dados["usuario"]["id"])
    usuario.idade = 30
    db.session.commit()

    cabecalho = {"Authorization": f"Bearer {dados['token_acesso']}"}
    assert cliente.get("/api/v1/eu", headers=cabecalho).get_json()["idade"] == 30


def test_eu_nunca_expoe_o_hash(cliente):
    dados = _registrar(cliente)
    cabecalho = {"Authorization": f"Bearer {dados['token_acesso']}"}
    assert "senha_hash" not in cliente.get("/api/v1/eu", headers=cabecalho).get_json()


def test_apelido_cai_no_nome_de_usuario_quando_vazio(cliente, app):
    """O JS não tem fallback: apelido vazio deixaria o card de nível em branco."""
    from app.extensions import db
    from app.models import Usuario

    dados = _registrar(cliente)
    usuario = db.session.get(Usuario, dados["usuario"]["id"])
    usuario.apelido = ""
    db.session.commit()

    cabecalho = {"Authorization": f"Bearer {dados['token_acesso']}"}
    assert cliente.get("/api/v1/eu", headers=cabecalho).get_json()["apelido"] == "gamer"


def test_xp_max_nunca_e_zero(cliente, app):
    """xp_max zero produz NaN% na largura da barra de progresso."""
    from app.extensions import db
    from app.models import Usuario

    dados = _registrar(cliente)
    usuario = db.session.get(Usuario, dados["usuario"]["id"])
    usuario.xp_max = 0
    db.session.commit()

    cabecalho = {"Authorization": f"Bearer {dados['token_acesso']}"}
    assert cliente.get("/api/v1/eu", headers=cabecalho).get_json()["xp_max"] == 2000


def test_eu_sem_token_responde_401(cliente):
    resposta = cliente.get("/api/v1/eu")
    assert resposta.status_code == 401


# --------------------------------------------------------- /telas/inicio
@pytest.fixture
def cenario(cliente, app):
    """Dois jogos, um alerta, um tópico e um favorito.

    Escrever no catálogo exige administrador — cadastrar jogo era
    operação de backoffice antes da migração. O usuário comum do cenário
    é quem tem o favorito e escreve o tópico.
    """
    from app.composicao import montar_servicos
    from app.extensions import db
    from app.models import Alerta, BibliotecaUsuario, Usuario

    dados = _registrar(cliente)
    comum = db.session.get(Usuario, dados["usuario"]["id"])

    chefe = Usuario(nome_usuario="chefe", email="chefe@l.dev", is_admin=True)
    chefe.definir_senha("senha123")
    db.session.add(chefe)
    db.session.commit()

    servicos = montar_servicos()
    alto = servicos.jogos.criar(
        {"nome": "Cyberpunk 2077", "metacritic": 86}, usuario=chefe
    )
    baixo = servicos.jogos.criar(
        {"nome": "Hollow Knight", "metacritic": 90}, usuario=chefe
    )

    db.session.add(
        Alerta(jogo_id=alto["id"], severidade="critica", texto="Servidores instáveis.")
    )
    db.session.add(
        BibliotecaUsuario(usuario_id=comum.id, jogo_id=baixo["id"], favorito=True)
    )
    db.session.commit()

    servicos.topicos.criar(
        {"titulo": "Alguém mais com crash no ato 2?", "jogo_id": alto["id"]},
        usuario=comum,
    )

    return {
        "cabecalho": {"Authorization": f"Bearer {dados['token_acesso']}"},
        "alto": alto,
        "baixo": baixo,
    }


def test_inicio_devolve_as_cinco_chaves(cliente, cenario):
    corpo = cliente.get("/api/v1/telas/inicio", headers=cenario["cabecalho"]).get_json()
    assert set(corpo) == {"banners", "atualizacoes", "assuntos", "favoritos", "alerta"}


def test_banners_sao_os_de_maior_metacritic(cliente, cenario):
    corpo = cliente.get("/api/v1/telas/inicio", headers=cenario["cabecalho"]).get_json()
    # `jogo` é sempre o NOME de exibição; o slug é sempre `jogo_slug`
    # (defeito 6 da revisão — antes `banners[].jogo` era o slug).
    assert corpo["banners"][0]["jogo"] == "Hollow Knight"
    assert corpo["banners"][0]["jogo_slug"] == "hollow-knight"
    assert corpo["banners"][0]["titulo"] == "Novidades e atualizações em Hollow Knight"
    assert len(corpo["banners"][0]["capa"]) == 2


def test_alerta_do_topo_traz_nome_e_slug_separados(cliente, cenario):
    """Mesma regra do defeito 6, no alerta: `banners[].jogo`,
    `atualizacoes[].jogo` e `alerta.jogo` saem no MESMO objeto, e antes
    discordavam — os dois primeiros nome, o terceiro slug. Um
    `href = '/jogo/' + item.jogo` funcionava num e gerava
    `/jogo/Cyberpunk 2077` no outro.
    """
    corpo = cliente.get("/api/v1/telas/inicio", headers=cenario["cabecalho"]).get_json()
    assert corpo["alerta"]["jogo"] == "Cyberpunk 2077"
    assert corpo["alerta"]["jogo_slug"] == "cyberpunk-2077"


def test_banco_vazio_devolve_listas_vazias_sem_quebrar(cliente):
    """A chave nunca é omitida — o JS acessa data.banners direto."""
    dados = _registrar(cliente)
    cabecalho = {"Authorization": f"Bearer {dados['token_acesso']}"}

    corpo = cliente.get("/api/v1/telas/inicio", headers=cabecalho).get_json()
    assert corpo["banners"] == []
    assert corpo["atualizacoes"] == []
    assert corpo["favoritos"] == []
    assert corpo["alerta"]["mensagem"] == "Nenhum alerta recente."


def test_atualizacao_traz_titulo_em_caixa_alta_e_nivel_derivado(cliente, cenario):
    corpo = cliente.get("/api/v1/telas/inicio", headers=cenario["cabecalho"]).get_json()
    atualizacao = corpo["atualizacoes"][0]
    assert atualizacao["titulo"] == "CYBERPUNK 2077"
    # Capitalização normal, não caixa alta (defeito 8).
    assert atualizacao["etiqueta"] == "Crítico"
    assert atualizacao["nivel"] == "critical"
    assert atualizacao["quando"].startswith("agora mesmo") or atualizacao[
        "quando"
    ].startswith("há")
    assert len(atualizacao["capa"]) == 2


def test_atualizacao_expoe_jogo_e_o_js_le_essa_chave_nao_nome(cliente, cenario):
    """Defeito da revisão final: inicio.js lia `u.nome`, chave que
    `atualizacoes[]` nunca teve — só `jogo` (nome de exibição). Todo
    ladrilho da grade mostrava "?" (Api.iniciaisDe(undefined) devolve
    "?"). Confirmado contra a API real, não só por leitura do JS."""
    corpo = cliente.get("/api/v1/telas/inicio", headers=cenario["cabecalho"]).get_json()
    atualizacao = corpo["atualizacoes"][0]
    assert "jogo" in atualizacao
    assert "nome" not in atualizacao

    texto = _sem_comentarios((RAIZ / "view/estatico/js/inicio.js").read_text(encoding="utf-8"))
    assert "u.jogo" in texto
    assert "u.nome" not in texto


def test_assuntos_trazem_grupo_constante(cliente, cenario):
    corpo = cliente.get("/api/v1/telas/inicio", headers=cenario["cabecalho"]).get_json()
    assert corpo["assuntos"][0]["grupo"] == "Últimos assuntos"
    assert corpo["assuntos"][0]["titulo"] == "Alguém mais com crash no ato 2?"


def test_topico_oculto_nao_aparece_nos_assuntos(cliente, cenario, app):
    from app.extensions import db
    from app.models import Topico

    topico = db.session.execute(db.select(Topico)).scalars().first()
    topico.oculto = True
    db.session.commit()

    corpo = cliente.get("/api/v1/telas/inicio", headers=cenario["cabecalho"]).get_json()
    assert corpo["assuntos"] == []


def test_favoritos_usam_o_cartao_canonico(cliente, cenario):
    corpo = cliente.get("/api/v1/telas/inicio", headers=cenario["cabecalho"]).get_json()
    favorito = corpo["favoritos"][0]
    assert favorito["nome"] == "Hollow Knight"
    assert favorito["favorito"] is True
    assert favorito["na_biblioteca"] is True
    assert set(favorito) == {
        "id", "slug", "nome", "pontuacao", "iniciais", "capa", "imagem_capa",
        "arquivo_capa", "favorito", "na_biblioteca", "status",
    }


def test_inicio_sem_token_responde_401(cliente):
    assert cliente.get("/api/v1/telas/inicio").status_code == 401
