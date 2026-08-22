import pytest

from app.errors import Conflito, NaoEncontrado
from app.models import Jogo, Usuario
from app.repositories.base import RepositorioBase


@pytest.fixture
def repo_jogos(app):
    return RepositorioBase(Jogo)


def _semear(repo, nomes):
    for nome in nomes:
        repo.criar(nome=nome, slug=nome.lower().replace(" ", "-"), popularidade=0)


def test_criar_e_obter(repo_jogos):
    jogo = repo_jogos.criar(nome="Hades", slug="hades")
    assert jogo.id is not None
    assert repo_jogos.obter(jogo.id).nome == "Hades"


def test_obter_inexistente_devolve_none(repo_jogos):
    assert repo_jogos.obter(9999) is None


def test_obter_ou_erro_levanta_nao_encontrado(repo_jogos):
    with pytest.raises(NaoEncontrado) as excecao:
        repo_jogos.obter_ou_erro(9999, "Jogo")
    assert excecao.value.status == 404
    assert excecao.value.mensagem == "Jogo não encontrado."


def test_listar_pagina_com_envelope_completo(repo_jogos):
    _semear(repo_jogos, [f"Jogo {i:02d}" for i in range(25)])
    pagina = repo_jogos.listar(pagina=1, por_pagina=10)
    assert len(pagina.itens) == 10
    assert pagina.total == 25
    assert pagina.paginas == 3
    assert pagina.pagina == 1


def test_ordenacao_empatada_nao_repete_itens_entre_paginas(repo_jogos):
    """Defeito 7.1: popularidade é 0 em todos, o desempate por id evita
    que a paginação repita e pule itens."""
    _semear(repo_jogos, [f"Jogo {i:02d}" for i in range(30)])

    p1 = repo_jogos.listar(pagina=1, por_pagina=10, ordenar_por="-popularidade")
    p2 = repo_jogos.listar(pagina=2, por_pagina=10, ordenar_por="-popularidade")
    p3 = repo_jogos.listar(pagina=3, por_pagina=10, ordenar_por="-popularidade")

    ids = [j.id for j in p1.itens + p2.itens + p3.itens]
    assert len(ids) == 30
    assert len(set(ids)) == 30, "paginação repetiu itens em ordenação empatada"


def test_por_pagina_tem_teto_de_100(repo_jogos):
    _semear(repo_jogos, [f"Jogo {i:03d}" for i in range(150)])
    pagina = repo_jogos.listar(pagina=1, por_pagina=500)
    assert pagina.por_pagina == 100


def test_atualizar_altera_apenas_os_campos_passados(repo_jogos):
    jogo = repo_jogos.criar(nome="Celeste", slug="celeste", metacritic=94)
    repo_jogos.atualizar(jogo, nome="Celeste Classic")
    assert jogo.nome == "Celeste Classic"
    assert jogo.metacritic == 94


def test_remover_apaga(repo_jogos):
    jogo = repo_jogos.criar(nome="Braid", slug="braid")
    repo_jogos.remover(jogo)
    assert repo_jogos.obter(jogo.id) is None


def test_violacao_de_unicidade_vira_conflito_e_nao_500(app):
    repo = RepositorioBase(Usuario)
    repo.criar(nome_usuario="gamer", email="a@b.dev", senha_hash="x")
    with pytest.raises(Conflito) as excecao:
        repo.criar(nome_usuario="gamer", email="c@d.dev", senha_hash="x")
    assert excecao.value.status == 409


def test_existe_e_contar(repo_jogos):
    repo_jogos.criar(nome="Tunic", slug="tunic")
    assert repo_jogos.existe(slug="tunic") is True
    assert repo_jogos.existe(slug="nao-existe") is False
    assert repo_jogos.contar() == 1
