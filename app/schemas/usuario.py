"""Schemas de usuário e autenticação."""
from marshmallow import Schema, fields, validate

from app.models import Usuario
from app.schemas.base import SchemaBase, SchemaEntradaBase


class UsuarioSchema(SchemaBase):
    class Meta(SchemaBase.Meta):
        model = Usuario
        exclude = ("senha_hash", "email", "senha_alterada_em", "versao_sessao")


class UsuarioEntradaSchema(SchemaEntradaBase):
    class Meta(SchemaEntradaBase.Meta):
        model = Usuario
        exclude = ("senha_hash",)
        dump_only = ("id", "criado_em", "atualizado_em", "senha_alterada_em", "versao_sessao")


class RegistroSchema(Schema):
    nome_usuario = fields.Str(required=True, validate=validate.Length(min=3, max=50))
    email = fields.Email(required=True, validate=validate.Length(max=100))
    senha = fields.Str(required=True, validate=validate.Length(min=8, max=128))
    apelido = fields.Str(load_default="", validate=validate.Length(max=50))
    idade = fields.Int(load_default=None, allow_none=True)
    bio = fields.Str(load_default="", validate=validate.Length(max=280))


class LoginSchema(Schema):
    """``identificador`` aceita nome_usuario OU email."""

    identificador = fields.Str(required=True, validate=validate.Length(min=3))
    senha = fields.Str(required=True)
