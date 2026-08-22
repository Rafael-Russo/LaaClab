"""Schemas do bugômetro e alertas."""
from marshmallow import fields, validate

from app.models import (
    CATEGORIAS_BUG,
    SEVERIDADES,
    SEVERIDADES_ALERTA,
    STATUS_RELATO,
    Alerta,
    BugometroStatus,
    HistoricoBug,
    MetricaBug,
    RelatoBug,
    VotoBug,
)
from app.schemas.base import SchemaBase, SchemaEntradaBase


class BugometroStatusSchema(SchemaBase):
    class Meta(SchemaBase.Meta):
        model = BugometroStatus


class BugometroStatusEntradaSchema(SchemaEntradaBase):
    jogo_id = fields.Int(required=True)

    class Meta(SchemaEntradaBase.Meta):
        model = BugometroStatus
        dump_only = ("id", "atualizado_em")


class MetricaBugSchema(SchemaBase):
    class Meta(SchemaBase.Meta):
        model = MetricaBug


class MetricaBugEntradaSchema(SchemaEntradaBase):
    jogo_id = fields.Int(required=True)

    class Meta(SchemaEntradaBase.Meta):
        model = MetricaBug
        dump_only = ("id", "criado_em")


class RelatoBugSchema(SchemaBase):
    class Meta(SchemaBase.Meta):
        model = RelatoBug


class RelatoBugEntradaSchema(SchemaEntradaBase):
    jogo_id = fields.Int(required=True)
    titulo = fields.Str(required=True, validate=validate.Length(min=1, max=200))
    categoria = fields.Str(
        load_default="outro", validate=validate.OneOf(CATEGORIAS_BUG)
    )
    severidade = fields.Str(
        load_default="media", validate=validate.OneOf(SEVERIDADES)
    )
    status = fields.Str(load_default="aberto", validate=validate.OneOf(STATUS_RELATO))

    class Meta(SchemaEntradaBase.Meta):
        model = RelatoBug
        dump_only = ("id", "criado_em", "confirmacoes", "usuario_id")


class VotoBugSchema(SchemaBase):
    class Meta(SchemaBase.Meta):
        model = VotoBug


class VotoBugEntradaSchema(SchemaEntradaBase):
    relato_id = fields.Int(required=True)

    class Meta(SchemaEntradaBase.Meta):
        model = VotoBug
        dump_only = ("id", "criado_em", "usuario_id")


class HistoricoBugSchema(SchemaBase):
    class Meta(SchemaBase.Meta):
        model = HistoricoBug


class HistoricoBugEntradaSchema(SchemaEntradaBase):
    jogo_id = fields.Int(required=True)

    class Meta(SchemaEntradaBase.Meta):
        model = HistoricoBug
        dump_only = ("id", "registrado_em")


class AlertaSchema(SchemaBase):
    class Meta(SchemaBase.Meta):
        model = Alerta


class AlertaEntradaSchema(SchemaEntradaBase):
    jogo_id = fields.Int(required=True)
    texto = fields.Str(required=True, validate=validate.Length(min=1))
    severidade = fields.Str(
        required=True, validate=validate.OneOf(SEVERIDADES_ALERTA)
    )

    class Meta(SchemaEntradaBase.Meta):
        model = Alerta
        dump_only = ("id", "criado_em")
