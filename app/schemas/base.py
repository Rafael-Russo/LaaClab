"""Bases dos schemas. Usa marshmallow_sqlalchemy PURO — nunca
flask_marshmallow, que arrastaria Flask para dentro dos Services.
"""
from marshmallow import EXCLUDE, RAISE
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema


class SchemaBase(SQLAlchemyAutoSchema):
    """Saída: serializa a entidade inteira, incluindo as FKs.

    Sem `sqla_session`: ele só é consultado quando `load_instance=True`,
    para hidratar instâncias ORM. Como carregamos dicionários, declará-lo
    seria configuração morta — e obrigaria este módulo a importar
    `app.extensions` sem necessidade.
    """

    class Meta:
        load_instance = False
        include_fk = True
        unknown = EXCLUDE


class SchemaEntradaBase(SQLAlchemyAutoSchema):
    """Entrada: recusa campos desconhecidos e os gerados pelo servidor."""

    class Meta:
        load_instance = False
        include_fk = True
        unknown = RAISE
        dump_only = ("id", "criado_em", "atualizado_em")
