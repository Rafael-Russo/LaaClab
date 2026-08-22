import pytest

from app.errors import AcessoNegado, DadosInvalidos, NaoEncontrado


def test_servico_nao_importa_flask():
    """A prova da camada: o Service não pode importar Flask.

    Olha os IMPORTS via `ast`, não o texto do arquivo. Uma docstring que
    explica a regra menciona os termos proibidos, e um teste de substring
    acusaria o comentário que documenta a própria regra.

    A outra metade da prova são os testes abaixo: eles usam dublês e
    rodam SEM a fixture `app` — se o Service precisasse de app context,
    falhariam.
    """
    import ast

    import app.services.base as base

    proibidos = {"flask", "flask_jwt_extended"}
    arvore = ast.parse(open(base.__file__, encoding="utf-8").read())
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            for alias in no.names:
                assert alias.name.split(".")[0] not in proibidos, alias.name
        if isinstance(no, ast.ImportFrom):
            assert (no.module or "").split(".")[0] not in proibidos, no.module


class _RepoFalso:
    """Dublê de repositório — nenhum banco, nenhum app context."""

    def __init__(self):
        self.itens = {}
        self.proximo_id = 1

    def obter(self, identificador):
        return self.itens.get(identificador)

    def obter_ou_erro(self, identificador, nome_recurso):
        item = self.obter(identificador)
        if item is None:
            raise NaoEncontrado(f"{nome_recurso} não encontrado.")
        return item

    def criar(self, **dados):
        from types import SimpleNamespace

        item = SimpleNamespace(id=self.proximo_id, **dados)
        self.itens[self.proximo_id] = item
        self.proximo_id += 1
        return item

    def atualizar(self, entidade, **dados):
        for campo, valor in dados.items():
            setattr(entidade, campo, valor)
        return entidade

    def remover(self, entidade):
        del self.itens[entidade.id]


class _SchemaFalso:
    def __init__(self, obrigatorios=()):
        self.obrigatorios = obrigatorios

    def dump(self, entidade, many=False):
        if many:
            return [self.dump(e) for e in entidade]
        return {k: v for k, v in vars(entidade).items()}

    def load(self, dados, partial=False):
        from marshmallow import ValidationError

        if not partial:
            faltando = {c: ["Campo obrigatório."] for c in self.obrigatorios if c not in dados}
            if faltando:
                raise ValidationError(faltando)
        return dict(dados)


@pytest.fixture
def servico():
    from app.services.base import ServicoBase

    return ServicoBase(
        repositorio=_RepoFalso(),
        schema_saida=_SchemaFalso(),
        schema_entrada=_SchemaFalso(obrigatorios=("titulo",)),
        nome_recurso="Tópico",
    )


def test_criar_devolve_dicionario_serializado(servico):
    resultado = servico.criar({"titulo": "Primeiro"})
    assert resultado["titulo"] == "Primeiro"
    assert resultado["id"] == 1


def test_criar_sem_campo_obrigatorio_levanta_dados_invalidos(servico):
    with pytest.raises(DadosInvalidos) as excecao:
        servico.criar({})
    assert excecao.value.status == 422
    assert "titulo" in excecao.value.erros


def test_criar_grava_o_dono_quando_informado(servico):
    resultado = servico.criar({"titulo": "Meu"}, usuario_id=42)
    assert resultado["usuario_id"] == 42


def test_obter_inexistente_levanta_nao_encontrado(servico):
    with pytest.raises(NaoEncontrado) as excecao:
        servico.obter(999)
    assert excecao.value.mensagem == "Tópico não encontrado."


def test_dono_pode_atualizar(servico):
    from types import SimpleNamespace

    servico.criar({"titulo": "Meu"}, usuario_id=7)
    autor = SimpleNamespace(id=7, is_admin=False)
    resultado = servico.atualizar(1, {"titulo": "Editado"}, usuario=autor)
    assert resultado["titulo"] == "Editado"


def test_estranho_nao_pode_atualizar(servico):
    from types import SimpleNamespace

    servico.criar({"titulo": "Meu"}, usuario_id=7)
    estranho = SimpleNamespace(id=8, is_admin=False)
    with pytest.raises(AcessoNegado) as excecao:
        servico.atualizar(1, {"titulo": "Invadido"}, usuario=estranho)
    assert excecao.value.status == 403


def test_admin_pode_atualizar_recurso_alheio(servico):
    from types import SimpleNamespace

    servico.criar({"titulo": "Meu"}, usuario_id=7)
    admin = SimpleNamespace(id=99, is_admin=True)
    resultado = servico.atualizar(1, {"titulo": "Moderado"}, usuario=admin)
    assert resultado["titulo"] == "Moderado"


def test_remover_respeita_a_mesma_regra_de_dono(servico):
    from types import SimpleNamespace

    servico.criar({"titulo": "Meu"}, usuario_id=7)
    with pytest.raises(AcessoNegado):
        servico.remover(1, usuario=SimpleNamespace(id=8, is_admin=False))
    servico.remover(1, usuario=SimpleNamespace(id=7, is_admin=False))
