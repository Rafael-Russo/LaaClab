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


class _Entidade:
    """Entidade de teste que recusa campo desconhecido, como o model real.

    `SimpleNamespace` aceitaria qualquer nome, então um `campo_dono` mal
    configurado passaria pelos testes e só quebraria em produção.
    """

    CAMPOS = {"id", "titulo", "usuario_id", "oculto"}

    def __init__(self, **dados):
        desconhecidos = set(dados) - self.CAMPOS
        if desconhecidos:
            raise TypeError(f"campo inexistente: {sorted(desconhecidos)}")
        self.oculto = False
        for campo, valor in dados.items():
            setattr(self, campo, valor)

    def __repr__(self):
        return f"_Entidade({vars(self)})"


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
        item = _Entidade(id=self.proximo_id, **dados)
        self.itens[self.proximo_id] = item
        self.proximo_id += 1
        return item

    def listar(self, pagina=1, por_pagina=20, ordenar_por=None, filtros=None):
        from app.repositories.base import Pagina

        itens = list(self.itens.values())
        for campo, valor in (filtros or {}).items():
            itens = [i for i in itens if getattr(i, campo, None) == valor]
        return Pagina(
            itens=itens,
            pagina=1,
            por_pagina=por_pagina,
            total=len(itens),
            paginas=1,
        )

    def atualizar(self, entidade, **dados):
        for campo, valor in dados.items():
            setattr(entidade, campo, valor)
        return entidade

    def remover(self, entidade):
        del self.itens[entidade.id]


class _Usuario:
    """Dublê de usuário autenticado."""

    def __init__(self, usuario_id=None, admin=False):
        self.id = usuario_id
        self.is_admin = admin


class _SchemaFalso:
    """Dublê de schema. Modela `dump_only` de propósito: sem isso, os
    testes não conseguem exercitar o caso em que o schema NÃO protege o
    campo de dono — que é justamente onde o Service precisa ter
    retaguarda própria."""

    def __init__(self, obrigatorios=(), dump_only=()):
        self.obrigatorios = obrigatorios
        self.dump_only = dump_only

    def dump(self, entidade, many=False):
        if many:
            return [self.dump(e) for e in entidade]
        return {k: v for k, v in vars(entidade).items()}

    def load(self, dados, partial=False):
        from marshmallow import ValidationError

        if not partial:
            faltando = {
                c: ["Campo obrigatório."]
                for c in self.obrigatorios
                if c not in dados
            }
            if faltando:
                raise ValidationError(faltando)
        return {k: v for k, v in dados.items() if k not in self.dump_only}


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
    resultado = servico.criar({"titulo": "Primeiro"}, usuario=_Usuario(999))
    assert resultado["titulo"] == "Primeiro"
    assert resultado["id"] == 1


def test_criar_sem_campo_obrigatorio_levanta_dados_invalidos(servico):
    with pytest.raises(DadosInvalidos) as excecao:
        servico.criar({}, usuario=_Usuario(999))
    assert excecao.value.status == 422
    assert "titulo" in excecao.value.erros


def test_criar_grava_o_dono_quando_informado(servico):
    resultado = servico.criar({"titulo": "Meu"}, usuario=_Usuario(42))
    assert resultado["usuario_id"] == 42


def test_obter_inexistente_levanta_nao_encontrado(servico):
    with pytest.raises(NaoEncontrado) as excecao:
        servico.obter(999)
    assert excecao.value.mensagem == "Tópico não encontrado."


def test_dono_pode_atualizar(servico):
    from types import SimpleNamespace

    servico.criar({"titulo": "Meu"}, usuario=_Usuario(7))
    autor = SimpleNamespace(id=7, is_admin=False)
    resultado = servico.atualizar(1, {"titulo": "Editado"}, usuario=autor)
    assert resultado["titulo"] == "Editado"


def test_estranho_nao_pode_atualizar(servico):
    from types import SimpleNamespace

    servico.criar({"titulo": "Meu"}, usuario=_Usuario(7))
    estranho = SimpleNamespace(id=8, is_admin=False)
    with pytest.raises(AcessoNegado) as excecao:
        servico.atualizar(1, {"titulo": "Invadido"}, usuario=estranho)
    assert excecao.value.status == 403


def test_admin_pode_atualizar_recurso_alheio(servico):
    from types import SimpleNamespace

    servico.criar({"titulo": "Meu"}, usuario=_Usuario(7))
    admin = SimpleNamespace(id=99, is_admin=True)
    resultado = servico.atualizar(1, {"titulo": "Moderado"}, usuario=admin)
    assert resultado["titulo"] == "Moderado"


def test_remover_respeita_a_mesma_regra_de_dono(servico):
    from types import SimpleNamespace

    servico.criar({"titulo": "Meu"}, usuario=_Usuario(7))
    with pytest.raises(AcessoNegado):
        servico.remover(1, usuario=SimpleNamespace(id=8, is_admin=False))
    servico.remover(1, usuario=SimpleNamespace(id=7, is_admin=False))


# --- Autorização: a ordem das checagens é a parte que importa -----------

def _pessoa(identificador, admin=False):
    from types import SimpleNamespace

    return SimpleNamespace(id=identificador, is_admin=admin)


def test_sem_usuario_e_401_e_nao_403(servico):
    """401 dispara o redirect para o login; 403 não."""
    from app.errors import NaoAutorizado

    servico.criar({"titulo": "Meu"}, usuario=_Usuario(7))
    with pytest.raises(NaoAutorizado) as excecao:
        servico.atualizar(1, {"titulo": "x"}, usuario=None)
    assert excecao.value.status == 401


def test_recurso_orfao_so_admin_edita(servico):
    """`relatos_bug.usuario_id` é nullable com ON DELETE SET NULL: apagar
    um autor deixa relatos sem dono. Órfão não pode virar editável por
    qualquer um."""
    servico.criar({"titulo": "Órfão"}, usuario=_Usuario(None))

    with pytest.raises(AcessoNegado):
        servico.atualizar(1, {"titulo": "invadido"}, usuario=_pessoa(8))

    assert servico.atualizar(
        1, {"titulo": "moderado"}, usuario=_pessoa(99, admin=True)
    )["titulo"] == "moderado"


def test_put_nao_troca_o_dono_mesmo_com_schema_permissivo(servico):
    """A retaguarda do Service: mesmo que o schema esqueça o dump_only,
    o dono não muda por PUT."""
    servico.criar({"titulo": "Meu"}, usuario=_Usuario(7))
    servico.atualizar(1, {"titulo": "ok", "usuario_id": 999}, usuario=_pessoa(7))
    assert servico.repositorio.obter(1).usuario_id == 7


def test_dono_com_id_em_string_ainda_e_reconhecido(servico):
    """O subject do JWT trafega como string; 7 != "7" negaria acesso ao
    dono legítimo."""
    servico.criar({"titulo": "Meu"}, usuario=_Usuario(7))
    assert servico.atualizar(1, {"titulo": "editado"}, usuario=_pessoa("7"))


# --- Moderação: conteúdo oculto some para quem não é admin --------------

@pytest.fixture
def servico_moderado():
    from app.services.base import ServicoBase

    servico = ServicoBase(
        repositorio=_RepoFalso(),
        schema_saida=_SchemaFalso(),
        schema_entrada=_SchemaFalso(obrigatorios=("titulo",)),
        nome_recurso="Tópico",
    )
    servico.campo_oculto = "oculto"
    return servico


def _semear_moderado(servico):
    servico.criar({"titulo": "Público"}, usuario=_Usuario(1))
    escondido = servico.repositorio.criar(titulo="Escondido", usuario_id=1)
    escondido.oculto = True
    return escondido


def test_listagem_esconde_oculto_de_quem_nao_e_admin(servico_moderado):
    _semear_moderado(servico_moderado)
    titulos = [
        i["titulo"] for i in servico_moderado.listar(usuario=_pessoa(1))["itens"]
    ]
    assert titulos == ["Público"]


def test_leitura_publica_tambem_esconde_oculto(servico_moderado):
    _semear_moderado(servico_moderado)
    itens = servico_moderado.listar(usuario=None)["itens"]
    assert [i["titulo"] for i in itens] == ["Público"]


def test_admin_ve_tudo_na_listagem(servico_moderado):
    _semear_moderado(servico_moderado)
    itens = servico_moderado.listar(usuario=_pessoa(99, admin=True))["itens"]
    assert len(itens) == 2


def test_obter_oculto_responde_404_para_nao_admin(servico_moderado):
    """Sem isso o filtro da listagem seria decorativo — bastaria pedir
    pelo id. E é 404, não 403, para não revelar que existe."""
    from app.errors import NaoEncontrado

    escondido = _semear_moderado(servico_moderado)
    with pytest.raises(NaoEncontrado):
        servico_moderado.obter(escondido.id, usuario=_pessoa(1))

    assert servico_moderado.obter(escondido.id, usuario=_pessoa(99, admin=True))


def test_dono_nao_edita_o_proprio_recurso_depois_de_oculto(servico_moderado):
    """Moderação sobrepõe a posse. Sem isto, quem teve o post escondido
    reescreveria o conteúdo e mascararia o motivo da moderação."""
    escondido = _semear_moderado(servico_moderado)
    with pytest.raises(AcessoNegado):
        servico_moderado.atualizar(
            escondido.id, {"titulo": "reescrito"}, usuario=_pessoa(1)
        )


def test_dono_nao_apaga_o_proprio_recurso_depois_de_oculto(servico_moderado):
    """Apagar destruiria o que o moderador ainda não revisou."""
    escondido = _semear_moderado(servico_moderado)
    with pytest.raises(AcessoNegado):
        servico_moderado.remover(escondido.id, usuario=_pessoa(1))


def test_admin_ainda_edita_recurso_oculto(servico_moderado):
    escondido = _semear_moderado(servico_moderado)
    resultado = servico_moderado.atualizar(
        escondido.id, {"titulo": "moderado"}, usuario=_pessoa(99, admin=True)
    )
    assert resultado["titulo"] == "moderado"


def test_recurso_visivel_continua_editavel_pelo_dono(servico_moderado):
    """A regra nova não pode ter fechado o caso normal."""
    _semear_moderado(servico_moderado)
    assert servico_moderado.atualizar(
        1, {"titulo": "editado"}, usuario=_pessoa(1)
    )["titulo"] == "editado"


def test_dubles_recusam_campo_inexistente():
    """Se o dublê aceitasse qualquer nome, um `campo_dono` mal escrito
    passaria por todos os testes acima."""
    with pytest.raises(TypeError):
        _Entidade(id=1, campo_que_nao_existe=True)
