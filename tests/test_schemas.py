import pytest
from marshmallow import ValidationError

from app.models import Jogo, Usuario
from app.schemas.jogo import JogoEntradaSchema, JogoSchema
from app.schemas.usuario import LoginSchema, RegistroSchema, UsuarioSchema


def test_schemas_funcionam_sem_app_context():
    """A propriedade real que ganhamos ao abandonar flask-marshmallow.

    NÃO testamos `"flask" not in sys.modules`: isso é sempre falso, porque
    os models são `db.Model` do Flask-SQLAlchemy e importar qualquer
    `app.*` carrega `app/__init__.py`, que importa Flask. Perseguir esse
    objetivo daria falsa confiança.

    O que importa é que o schema serialize e valide sem que `create_app()`
    tenha sido chamado — um schema flask-marshmallow dependeria de
    `current_app` e falharia aqui.
    """
    from flask import current_app

    dados = JogoEntradaSchema().load({"nome": "Sem Contexto"})
    assert dados["nome"] == "Sem Contexto"

    with pytest.raises(RuntimeError):
        _ = current_app.name  # prova que realmente não há app context


def test_nenhum_schema_importa_extensao_flask():
    """Varre TODOS os módulos de schema, não só o base.

    Inspeciona os IMPORTS via `ast`, não o texto do arquivo. Um teste de
    substring acusaria a própria docstring que explica por que NÃO usamos
    `flask_marshmallow` — o mesmo motivo que levou a guarda de camadas a
    apagar strings e comentários antes de varrer.
    """
    import ast
    import importlib
    import pkgutil

    import app.schemas as pacote

    proibidos = {"flask", "flask_marshmallow", "flask_jwt_extended"}

    def raiz_proibida(nome):
        return (nome or "").split(".")[0] in proibidos

    assert len(list(pkgutil.iter_modules(pacote.__path__))) >= 6

    for info in pkgutil.iter_modules(pacote.__path__):
        modulo = importlib.import_module(f"app.schemas.{info.name}")
        arvore = ast.parse(open(modulo.__file__, encoding="utf-8").read())
        for no in ast.walk(arvore):
            if isinstance(no, ast.Import):
                for alias in no.names:
                    assert not raiz_proibida(alias.name), f"{info.name}: {alias.name}"
            if isinstance(no, ast.ImportFrom):
                assert not raiz_proibida(no.module), f"{info.name}: {no.module}"


def test_entrada_de_usuario_aceita_is_admin_mas_quem_decide_e_o_service():
    """A proteção de `is_admin` mudou de camada de propósito.

    No schema ela era cega: barrava o campo para todo mundo, inclusive
    para o administrador — e era por isso que não havia como existir um
    segundo admin. Agora o campo é aceito aqui e barrado em
    `ServicoBase.atualizar` via `campos_de_admin`, que sabe quem está
    pedindo. A trava está coberta por `test_conta_comum_nao_se_promove`
    e `test_admin_promove_outro_usuario`, em tests/test_crud.py.
    """
    from app.schemas.usuario import UsuarioEntradaSchema

    dados = UsuarioEntradaSchema().load({"is_admin": True}, partial=True)
    assert dados["is_admin"] is True


def test_entrada_de_usuario_recusa_senha_hash():
    from app.schemas.usuario import UsuarioEntradaSchema

    with pytest.raises(ValidationError) as excecao:
        UsuarioEntradaSchema().load({"senha_hash": "forjado"}, partial=True)
    assert "senha_hash" in excecao.value.messages


def test_saida_de_usuario_nunca_expoe_o_hash(app, sessao):
    u = Usuario(nome_usuario="gamer", email="g@l.dev")
    u.definir_senha("senha123")
    sessao.add(u)
    sessao.commit()

    saida = UsuarioSchema().dump(u)
    assert "senha_hash" not in saida
    assert saida["nome_usuario"] == "gamer"


def test_entrada_de_jogo_rejeita_id_e_criado_em(app):
    """Bug herdado: o schema antigo fazia dump e load, então dava para
    enviar id e criado_em num POST."""
    with pytest.raises(ValidationError) as excecao:
        JogoEntradaSchema().load({"nome": "Hades", "id": 7, "criado_em": "2020-01-01"})
    assert "id" in excecao.value.messages


def test_entrada_de_jogo_exige_nome(app):
    with pytest.raises(ValidationError) as excecao:
        JogoEntradaSchema().load({})
    assert "nome" in excecao.value.messages


def test_entrada_de_jogo_aceita_carga_valida(app):
    dados = JogoEntradaSchema().load({"nome": "Hades", "metacritic": 93})
    assert dados["nome"] == "Hades"
    assert dados["metacritic"] == 93


def test_registro_exige_senha_de_pelo_menos_8(app):
    with pytest.raises(ValidationError) as excecao:
        RegistroSchema().load(
            {"nome_usuario": "gamer", "email": "g@l.dev", "senha": "curta"}
        )
    assert "senha" in excecao.value.messages


def test_registro_valida_formato_de_email(app):
    with pytest.raises(ValidationError) as excecao:
        RegistroSchema().load(
            {"nome_usuario": "gamer", "email": "nao-e-email", "senha": "senha123"}
        )
    assert "email" in excecao.value.messages


def test_login_aceita_nome_ou_email_no_identificador(app):
    dados = LoginSchema().load({"identificador": "gamer", "senha": "senha123"})
    assert dados["identificador"] == "gamer"


def test_atualizacao_parcial_aceita_um_campo_so(app):
    dados = JogoEntradaSchema().load({"metacritic": 88}, partial=True)
    assert dados == {"metacritic": 88}
