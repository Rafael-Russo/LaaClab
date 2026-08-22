import pytest

from app.errors import (
    AcessoNegado,
    Conflito,
    DadosInvalidos,
    ErroDeDominio,
    NaoAutorizado,
    NaoEncontrado,
)


def test_excecoes_carregam_status_e_mensagem():
    erro = NaoEncontrado("Jogo não encontrado.")
    assert erro.status == 404
    assert erro.mensagem == "Jogo não encontrado."
    assert isinstance(erro, ErroDeDominio)


@pytest.mark.parametrize(
    "classe, status",
    [
        (NaoAutorizado, 401),
        (AcessoNegado, 403),
        (NaoEncontrado, 404),
        (Conflito, 409),
        (DadosInvalidos, 422),
    ],
)
def test_status_de_cada_excecao(classe, status):
    assert classe("x").status == status


def test_dados_invalidos_carrega_dicionario_de_erros():
    erro = DadosInvalidos("Inválido.", erros={"titulo": ["Campo obrigatório."]})
    assert erro.erros == {"titulo": ["Campo obrigatório."]}


def test_classes_de_erro_nao_dependem_de_flask():
    """As classes de exceção não podem depender de Flask — é isso que
    permite ao Service levantá-las sem violar a regra de camadas.

    `registrar_handlers` importa Flask DENTRO da função, e isso é
    intencional: ela é a tradução para HTTP e só o factory a chama. Por
    isso o teste olha apenas os imports de nível superior do módulo, não
    o texto do arquivo inteiro.
    """
    import ast

    import app.errors as modulo

    arvore = ast.parse(open(modulo.__file__, encoding="utf-8").read())
    for no in arvore.body:
        if isinstance(no, ast.Import):
            nomes = [alias.name for alias in no.names]
            assert not any(n.startswith("flask") for n in nomes), nomes
        if isinstance(no, ast.ImportFrom):
            assert not (no.module or "").startswith("flask"), no.module
