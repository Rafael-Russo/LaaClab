import pytest
from marshmallow import ValidationError

from app.models import Jogo, Usuario
from app.schemas.jogo import JogoEntradaSchema, JogoSchema
from app.schemas.usuario import LoginSchema, RegistroSchema, UsuarioSchema


def test_schemas_nao_importam_flask():
    """Se um schema arrastar Flask, o Service que o importa viola a regra
    de camadas. É por isso que flask-marshmallow foi removido."""
    import app.schemas.base as base

    fonte = open(base.__file__, encoding="utf-8").read()
    assert "flask_marshmallow" not in fonte
    assert "from flask import" not in fonte


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
