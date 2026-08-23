"""Busca, ordenação por pontuação e filtro por gênero.

As três eram lacunas do spec da API sem dono desde o começo, e são o que
a tela Explorar exige.
"""
import pytest


@pytest.fixture
def catalogo(app):
    from app.extensions import db
    from app.models import BugometroStatus, Genero, Jogo, JogoGenero

    acao = Genero(nome="Ação", slug="acao")
    rpg = Genero(nome="RPG", slug="rpg")
    db.session.add_all([acao, rpg])
    db.session.flush()

    from app.services.jogo_service import normalizar_busca

    dados = [("Pokémon Legends", 80, acao), ("Elden Ring", 20, rpg), ("Zelda", 0, rpg)]
    jogos = {}
    for nome, pontuacao, genero in dados:
        jogo = Jogo(nome=nome, slug=nome.lower().replace(" ", "-"),
                    nome_busca=normalizar_busca(nome))
        db.session.add(jogo)
        db.session.flush()
        db.session.add(BugometroStatus(jogo_id=jogo.id, pontuacao=pontuacao,
                                       status="stable"))
        db.session.add(JogoGenero(jogo_id=jogo.id, genero_id=genero.id))
        jogos[nome] = jogo
    db.session.commit()
    return jogos


def _nomes(pagina):
    return [j.nome for j in pagina.itens]


def test_busca_ignora_acento_e_caixa(app, catalogo):
    from app.composicao import montar_servicos

    servicos = montar_servicos()
    assert _nomes(servicos.jogos.listar_catalogo(busca="pokemon")) == ["Pokémon Legends"]
    assert _nomes(servicos.jogos.listar_catalogo(busca="POKÉMON")) == ["Pokémon Legends"]


def test_busca_e_por_trecho_nao_por_prefixo(app, catalogo):
    from app.composicao import montar_servicos

    servicos = montar_servicos()
    assert _nomes(montar_servicos().jogos.listar_catalogo(busca="ring")) == ["Elden Ring"]


def test_busca_escapa_curinga_do_like(app, catalogo):
    """Um `%` digitado na caixa de busca não pode virar 'tudo'."""
    from app.composicao import montar_servicos

    assert montar_servicos().jogos.listar_catalogo(busca="%").total == 0


def test_ordena_por_pontuacao_que_mora_em_outra_tabela(app, catalogo):
    from app.composicao import montar_servicos

    servicos = montar_servicos()
    assert _nomes(servicos.jogos.listar_catalogo(ordenar_por="-pontuacao")) == [
        "Pokémon Legends", "Elden Ring", "Zelda",
    ]
    assert _nomes(servicos.jogos.listar_catalogo(ordenar_por="pontuacao")) == [
        "Zelda", "Elden Ring", "Pokémon Legends",
    ]


def test_jogo_sem_bugometro_ainda_aparece(app, catalogo):
    """O JOIN tem que ser externo: um jogo recém-cadastrado não tem linha
    de bugômetro, e sumir do catálogo por isso seria pior que ordenar mal."""
    from app.composicao import montar_servicos
    from app.extensions import db
    from app.models import Jogo
    from app.services.jogo_service import normalizar_busca

    db.session.add(Jogo(nome="Recem Chegado", slug="recem",
                        nome_busca=normalizar_busca("Recem Chegado")))
    db.session.commit()

    nomes = _nomes(montar_servicos().jogos.listar_catalogo(ordenar_por="-pontuacao"))
    assert "Recem Chegado" in nomes


def test_filtra_por_genero(app, catalogo):
    from app.composicao import montar_servicos

    nomes = _nomes(montar_servicos().jogos.listar_catalogo(genero_slug="rpg"))
    assert sorted(nomes) == ["Elden Ring", "Zelda"]


def test_ordenacao_desconhecida_continua_falhando_fechada(app, catalogo):
    from app.composicao import montar_servicos
    from app.errors import DadosInvalidos

    with pytest.raises(DadosInvalidos):
        montar_servicos().jogos.listar_catalogo(ordenar_por="senha_hash")
