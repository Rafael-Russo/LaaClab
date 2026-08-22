"""Bases dos schemas. Usa marshmallow_sqlalchemy PURO, sem extensões
que arrastem Flask para dentro dos Services.
"""
from marshmallow import EXCLUDE, RAISE
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema

from app.extensions import db


class SchemaBase(SQLAlchemyAutoSchema):
    """Saída: serializa a entidade inteira, incluindo as FKs."""

    class Meta:
        load_instance = False
        include_fk = True
        sqla_session = db.session
        unknown = EXCLUDE


class SchemaEntradaBase(SQLAlchemyAutoSchema):
    """Entrada: recusa campos desconhecidos e os gerados pelo servidor."""

    class Meta:
        load_instance = False
        include_fk = True
        sqla_session = db.session
        unknown = RAISE
        dump_only = ("id", "criado_em", "atualizado_em")
