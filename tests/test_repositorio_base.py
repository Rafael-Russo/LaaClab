import pytest

from app.errors import Conflito, DadosInvalidos, NaoEncontrado
from app.models import Jogo, Usuario
from app.repositories.base import RepositorioBase


ORDENACAO_JOGOS = ("nome", "metacritic", "popularidade", "criado_em")


@pytest.fixture
def repo_jogos(app):
    return RepositorioBase(Jogo, ordenacao_permitida=ORDENACAO_JOGOS)


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


# --- A allowlist tem que falhar FECHADA ---------------------------------

def test_repositorio_sem_allowlist_recusa_qualquer_ordenacao(app):
    """Falhar aberto aqui deixaria `?ordenar_por=senha_hash` ordenar por
    coluna sensível em qualquer recurso cujo repositório esquecesse a
    allowlist."""
    repo = RepositorioBase(Usuario)
    with pytest.raises(DadosInvalidos) as excecao:
        repo.listar(ordenar_por="senha_hash")
    assert excecao.value.status == 422
    assert "ordenar_por" in excecao.value.erros


def test_coluna_fora_da_allowlist_e_recusada(repo_jogos):
    with pytest.raises(DadosInvalidos):
        repo_jogos.listar(ordenar_por="slug")


def test_ordenar_por_relacionamento_da_422_e_nao_500(app):
    """`avaliacoes` é relationship, não coluna: sem a checagem, o ORDER BY
    derruba a requisição com erro interno."""
    repo = RepositorioBase(Usuario, ordenacao_permitida=("avaliacoes",))
    with pytest.raises(DadosInvalidos):
        repo.listar(ordenar_por="avaliacoes")


def test_desempate_por_id_esta_sempre_nas_clausulas(repo_jogos):
    """Prova direta do defeito 7.1. Não dá para confiar num teste de
    integração aqui: o SQLite devolve as linhas em ordem de rowid por
    acidente do plano de execução, então a paginação parece correta mesmo
    sem o desempate. Este teste olha as cláusulas geradas."""
    def nome_da_ultima(ordenar_por):
        clausulas = repo_jogos._clausulas_de_ordem(ordenar_por)
        return str(clausulas[-1])

    assert nome_da_ultima(None) == "jogos.id ASC"
    assert len(repo_jogos._clausulas_de_ordem("-popularidade")) == 2

    # O desempate acompanha a direção: com `-campo` e valores empatados,
    # um `id ASC` fixo devolveria o mais antigo primeiro.
    assert nome_da_ultima("-popularidade") == "jogos.id DESC"
    assert nome_da_ultima("popularidade") == "jogos.id ASC"


# --- Unicidade e chave estrangeira são erros diferentes ------------------

def test_fk_inexistente_vira_422_e_nao_409(app):
    """Apontar para linha inexistente é entrada inválida, não conflito
    com o estado existente."""
    from app.models import Avaliacao

    repo = RepositorioBase(Avaliacao)
    with pytest.raises(DadosInvalidos) as excecao:
        repo.criar(usuario_id=9999, jogo_id=9999, comentario="órfã")
    assert excecao.value.status == 422
