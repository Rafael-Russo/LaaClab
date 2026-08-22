"""Schemas do fórum."""
from marshmallow import fields, validate

from app.models import TIPOS_TOPICO, Categoria, Post, Topico
from app.schemas.base import SchemaBase, SchemaEntradaBase


class CategoriaSchema(SchemaBase):
    class Meta(SchemaBase.Meta):
        model = Categoria


class CategoriaEntradaSchema(SchemaEntradaBase):
    nome = fields.Str(required=True, validate=validate.Length(min=1, max=50))

    class Meta(SchemaEntradaBase.Meta):
        model = Categoria


class TopicoSchema(SchemaBase):
    class Meta(SchemaBase.Meta):
        model = Topico


class TopicoEntradaSchema(SchemaEntradaBase):
    titulo = fields.Str(required=True, validate=validate.Length(min=1, max=200))
    corpo = fields.Str(load_default="")
    tipo = fields.Str(load_default="discussao", validate=validate.OneOf(TIPOS_TOPICO))
    jogo_id = fields.Int(required=True)

    class Meta(SchemaEntradaBase.Meta):
        model = Topico
        dump_only = ("id", "criado_em", "usuario_id")


class PostSchema(SchemaBase):
    class Meta(SchemaBase.Meta):
        model = Post


class PostEntradaSchema(SchemaEntradaBase):
    topico_id = fields.Int(required=True)
    conteudo = fields.Str(required=True, validate=validate.Length(min=1))

    class Meta(SchemaEntradaBase.Meta):
        model = Post
        dump_only = ("id", "criado_em", "usuario_id")
