"""Schemas do catálogo."""
from marshmallow import fields, validate

from app.models import (
    Avaliacao,
    BibliotecaUsuario,
    CurtidaAvaliacao,
    Genero,
    Jogo,
    JogoGenero,
    JogoPlataforma,
    Plataforma,
)
from app.schemas.base import SchemaBase, SchemaEntradaBase


class JogoSchema(SchemaBase):
    class Meta(SchemaBase.Meta):
        model = Jogo


class JogoEntradaSchema(SchemaEntradaBase):
    nome = fields.Str(required=True, validate=validate.Length(min=1, max=200))

    class Meta(SchemaEntradaBase.Meta):
        model = Jogo
        dump_only = ("id", "criado_em", "atualizado_em", "slug", "iniciais", "nome_busca")


class GeneroSchema(SchemaBase):
    class Meta(SchemaBase.Meta):
        model = Genero


class GeneroEntradaSchema(SchemaEntradaBase):
    nome = fields.Str(required=True, validate=validate.Length(min=1, max=80))

    class Meta(SchemaEntradaBase.Meta):
        model = Genero
        dump_only = ("id", "slug")


class PlataformaSchema(SchemaBase):
    class Meta(SchemaBase.Meta):
        model = Plataforma


class PlataformaEntradaSchema(SchemaEntradaBase):
    nome = fields.Str(required=True, validate=validate.Length(min=1, max=50))

    class Meta(SchemaEntradaBase.Meta):
        model = Plataforma


class JogoGeneroSchema(SchemaBase):
    class Meta(SchemaBase.Meta):
        model = JogoGenero


class JogoGeneroEntradaSchema(SchemaEntradaBase):
    class Meta(SchemaEntradaBase.Meta):
        model = JogoGenero


class JogoPlataformaSchema(SchemaBase):
    class Meta(SchemaBase.Meta):
        model = JogoPlataforma


class JogoPlataformaEntradaSchema(SchemaEntradaBase):
    class Meta(SchemaEntradaBase.Meta):
        model = JogoPlataforma


class BibliotecaSchema(SchemaBase):
    class Meta(SchemaBase.Meta):
        model = BibliotecaUsuario


class BibliotecaEntradaSchema(SchemaEntradaBase):
    jogo_id = fields.Int(required=True)

    class Meta(SchemaEntradaBase.Meta):
        model = BibliotecaUsuario
        dump_only = ("id", "adicionado_em", "usuario_id")


class AvaliacaoSchema(SchemaBase):
    class Meta(SchemaBase.Meta):
        model = Avaliacao


class AvaliacaoEntradaSchema(SchemaEntradaBase):
    jogo_id = fields.Int(required=True)
    comentario = fields.Str(required=True, validate=validate.Length(min=1))
    nota = fields.Decimal(load_default=None, allow_none=True, as_string=True)

    class Meta(SchemaEntradaBase.Meta):
        model = Avaliacao
        dump_only = ("id", "criado_em", "usuario_id")


class CurtidaAvaliacaoSchema(SchemaBase):
    class Meta(SchemaBase.Meta):
        model = CurtidaAvaliacao


class CurtidaAvaliacaoEntradaSchema(SchemaEntradaBase):
    avaliacao_id = fields.Int(required=True)

    class Meta(SchemaEntradaBase.Meta):
        model = CurtidaAvaliacao
        dump_only = ("id", "usuario_id")
