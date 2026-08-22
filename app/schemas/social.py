"""Schemas de badges, notificações e atividades."""
from marshmallow import fields, validate

from app.models import Atividade, Badge, Notificacao, UsuarioBadge
from app.schemas.base import SchemaBase, SchemaEntradaBase


class BadgeSchema(SchemaBase):
    class Meta(SchemaBase.Meta):
        model = Badge


class BadgeEntradaSchema(SchemaEntradaBase):
    nome = fields.Str(required=True, validate=validate.Length(min=1, max=50))

    class Meta(SchemaEntradaBase.Meta):
        model = Badge


class UsuarioBadgeSchema(SchemaBase):
    class Meta(SchemaBase.Meta):
        model = UsuarioBadge


class UsuarioBadgeEntradaSchema(SchemaEntradaBase):
    badge_id = fields.Int(required=True)

    class Meta(SchemaEntradaBase.Meta):
        model = UsuarioBadge
        dump_only = ("id", "conquistado_em")


class NotificacaoSchema(SchemaBase):
    class Meta(SchemaBase.Meta):
        model = Notificacao


class NotificacaoEntradaSchema(SchemaEntradaBase):
    mensagem = fields.Str(required=True, validate=validate.Length(min=1))

    class Meta(SchemaEntradaBase.Meta):
        model = Notificacao
        dump_only = ("id", "criado_em")


class AtividadeSchema(SchemaBase):
    class Meta(SchemaBase.Meta):
        model = Atividade


class AtividadeEntradaSchema(SchemaEntradaBase):
    tipo = fields.Str(required=True, validate=validate.Length(min=1, max=50))

    class Meta(SchemaEntradaBase.Meta):
        model = Atividade
        dump_only = ("id", "criado_em")
