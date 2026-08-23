import pytest

from app.services.formatacao import duracao_jogada


def _cabecalho(cliente, nome="gamer"):
    corpo = cliente.post(
        "/api/auth/registro",
        json={"nome_usuario": nome, "email": f"{nome}@l.dev", "senha": "senha123"},
    ).get_json()
    return {"Authorization": f"Bearer {corpo['token_acesso']}"}


@pytest.fixture
def biblioteca(cliente, app):
    """Três jogos na biblioteca do usuário, com tempos e progresso
    diferentes, mais um jogo fora dela."""
    from app.composicao import montar_servicos
    from app.extensions import db
    from app.models import BibliotecaUsuario, Usuario

    cabecalho = _cabecalho(cliente)
    dono = db.session.execute(
        db.select(Usuario).where(Usuario.nome_usuario == "gamer")
    ).scalars().first()

    chefe = Usuario(nome_usuario="chefe", email="chefe@l.dev", is_admin=True)
    chefe.definir_senha("senha123")
    db.session.add(chefe)
    db.session.commit()

    servicos = montar_servicos()
    jogos = [
        servicos.jogos.criar({"nome": nome}, usuario=chefe)
        for nome in ("Hollow Knight", "Celeste", "Hades", "Fora Da Lista")
    ]

    # Todas gravadas no mesmo instante: "Hades" é a última inserida,
    # e o desempate por id é o que a coloca em primeiro.
    for indice, (jogo, minutos, progresso, favorito) in enumerate(
        [
            (jogos[0], 1767, 62, True),
            (jogos[1], 90, 15, False),
            (jogos[2], 0, 0, False),
        ]
    ):
        db.session.add(
            BibliotecaUsuario(
                usuario_id=dono.id,
                jogo_id=jogo["id"],
                minutos_jogados=minutos,
                progresso=progresso,
                favorito=favorito,
            )
        )
    # Um commit só: os três `adicionado_em` colidem de propósito, para o
    # teste de ordem exercitar o desempate em vez de mascará-lo.
    db.session.commit()

    return {"cabecalho": cabecalho, "jogos": jogos, "dono": dono}


# --- formatação de duração ---------------------------------------------

@pytest.mark.parametrize(
    "minutos, esperado",
    [
        (0, "0h 00m"),
        (9, "0h 09m"),
        (60, "1h 00m"),
        (1767, "29h 27m"),
        (None, "0h 00m"),
        (-30, "0h 00m"),
        (90.5, "1h 30m"),
        (90.9, "1h 30m"),
    ],
)
def test_duracao_jogada(minutos, esperado):
    """Substitui a fórmula falsa `bug_score // 3` do sistema antigo."""
    assert duracao_jogada(minutos) == esperado


# --- /telas/biblioteca --------------------------------------------------

def test_biblioteca_devolve_total_e_jogos(cliente, biblioteca):
    corpo = cliente.get(
        "/api/v1/telas/biblioteca", headers=biblioteca["cabecalho"]
    ).get_json()
    assert set(corpo) == {"total", "jogos"}
    assert corpo["total"] == 3


def test_total_bate_com_o_tamanho_da_grade(cliente, biblioteca):
    """`total` é `len(jogos)`, nunca um COUNT separado — senão o chip
    'Todos (N)' diverge do que a grade mostra."""
    corpo = cliente.get(
        "/api/v1/telas/biblioteca", headers=biblioteca["cabecalho"]
    ).get_json()
    assert corpo["total"] == len(corpo["jogos"])


def test_entrada_da_biblioteca_traz_o_cartao_mais_entrada_id(cliente, biblioteca):
    corpo = cliente.get(
        "/api/v1/telas/biblioteca", headers=biblioteca["cabecalho"]
    ).get_json()
    entrada = corpo["jogos"][0]
    assert set(entrada) == {
        "id", "entrada_id", "favorito", "na_biblioteca", "slug", "nome", "iniciais",
        "capa", "imagem_capa", "arquivo_capa", "pontuacao", "status",
    }
    assert entrada["na_biblioteca"] is True


def test_entrada_id_e_da_biblioteca_nao_do_jogo(cliente, biblioteca, app):
    """O PATCH de favorito usa esse id: trocar pelo id do jogo faria a
    tela editar a entrada errada."""
    from app.extensions import db
    from app.models import BibliotecaUsuario

    corpo = cliente.get(
        "/api/v1/telas/biblioteca", headers=biblioteca["cabecalho"]
    ).get_json()
    ids = {e["entrada_id"] for e in corpo["jogos"]}
    reais = {
        e.id
        for e in db.session.execute(db.select(BibliotecaUsuario)).scalars().all()
    }
    assert ids == reais


def test_biblioteca_vem_do_mais_recente_para_o_mais_antigo(cliente, biblioteca):
    """As três entradas são gravadas no mesmo instante, de propósito.

    Sem `sleep` entre elas os timestamps colidem — e é justamente aí que
    o desempate importa: um `id ASC` fixo devolveria o mais ANTIGO
    primeiro, invertendo a tela. O teste falha se o desempate deixar de
    acompanhar a direção da ordenação.
    """
    corpo = cliente.get(
        "/api/v1/telas/biblioteca", headers=biblioteca["cabecalho"]
    ).get_json()
    assert [j["nome"] for j in corpo["jogos"]] == ["Hades", "Celeste", "Hollow Knight"]


def test_biblioteca_e_so_do_usuario_autenticado(cliente, biblioteca):
    """Escopo no repositório, não só na permissão."""
    outro = _cabecalho(cliente, "intruso")
    corpo = cliente.get("/api/v1/telas/biblioteca", headers=outro).get_json()
    assert corpo == {"total": 0, "jogos": []}


def test_jogo_fora_da_biblioteca_nao_aparece(cliente, biblioteca):
    corpo = cliente.get(
        "/api/v1/telas/biblioteca", headers=biblioteca["cabecalho"]
    ).get_json()
    assert "Fora Da Lista" not in [j["nome"] for j in corpo["jogos"]]


def test_favorito_vem_da_entrada_nao_de_um_padrao(cliente, biblioteca):
    corpo = cliente.get(
        "/api/v1/telas/biblioteca", headers=biblioteca["cabecalho"]
    ).get_json()
    favoritos = {j["nome"]: j["favorito"] for j in corpo["jogos"]}
    assert favoritos == {"Hades": False, "Celeste": False, "Hollow Knight": True}


def test_biblioteca_sem_token_e_401(cliente):
    assert cliente.get("/api/v1/telas/biblioteca").status_code == 401


# --- /telas/perfil ------------------------------------------------------

def test_perfil_devolve_usuario_e_jogos_recentes(cliente, biblioteca):
    corpo = cliente.get(
        "/api/v1/telas/perfil", headers=biblioteca["cabecalho"]
    ).get_json()
    assert set(corpo) == {"usuario", "jogos_recentes"}


def test_usuario_do_perfil_e_o_mesmo_payload_do_eu(cliente, biblioteca):
    """Duas telas lendo o mesmo dado por caminhos diferentes divergiriam
    na primeira mudança de campo."""
    perfil = cliente.get(
        "/api/v1/telas/perfil", headers=biblioteca["cabecalho"]
    ).get_json()
    eu = cliente.get("/api/v1/eu", headers=biblioteca["cabecalho"]).get_json()
    assert perfil["usuario"] == eu


def test_jogos_recentes_sao_os_tres_mais_recentes(cliente, biblioteca):
    """As três entradas são gravadas no mesmo instante, de propósito.
    O desempate por id coloca a última inserida (maior id) em primeiro."""
    corpo = cliente.get(
        "/api/v1/telas/perfil", headers=biblioteca["cabecalho"]
    ).get_json()
    assert [j["jogo"] for j in corpo["jogos_recentes"]] == [
        "Hades", "Celeste", "Hollow Knight",
    ]


def test_jogo_recente_tem_o_shape_da_tela(cliente, biblioteca):
    corpo = cliente.get(
        "/api/v1/telas/perfil", headers=biblioteca["cabecalho"]
    ).get_json()
    for recente in corpo["jogos_recentes"]:
        # `jogo` é o nome; o slug sai como `jogo_slug` (defeito 6 — a
        # regra é a mesma em toda a tela: nunca `slug` sozinho ao lado
        # de `jogo`).
        assert set(recente) == {"jogo", "jogo_slug", "capa", "duracao", "porcentagem"}
        assert len(recente["capa"]) == 2


def test_duracao_e_progresso_vem_das_colunas_nao_da_pontuacao(cliente, biblioteca):
    """No sistema antigo `duracao` era `bug_score // 3` e `porcentagem`
    era o próprio `bug_score` — a tela mostrava pontuação de bug fingindo
    ser progresso de jogo."""
    corpo = cliente.get(
        "/api/v1/telas/perfil", headers=biblioteca["cabecalho"]
    ).get_json()
    por_jogo = {j["jogo"]: j for j in corpo["jogos_recentes"]}
    assert por_jogo["Hollow Knight"]["duracao"] == "29h 27m"
    assert por_jogo["Hollow Knight"]["porcentagem"] == 62
    assert por_jogo["Hades"]["duracao"] == "0h 00m"
    assert por_jogo["Hades"]["porcentagem"] == 0


def test_biblioteca_vazia_devolve_recentes_vazio(cliente):
    cabecalho = _cabecalho(cliente, "novato")
    corpo = cliente.get("/api/v1/telas/perfil", headers=cabecalho).get_json()
    assert corpo["jogos_recentes"] == []
    assert corpo["usuario"]["nome_usuario"] == "novato"


def test_perfil_sem_token_e_401(cliente):
    assert cliente.get("/api/v1/telas/perfil").status_code == 401
