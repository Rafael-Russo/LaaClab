"""Schemas Marshmallow do domínio accounts."""

from marshmallow import Schema, fields, validate

from app.accounts.models import Theme


class UserProfileSchema(Schema):
    """Perfil do usuário autenticado.

    Progressão (`level`, `xp`, contadores) é do servidor: sai na leitura e é
    ignorada na escrita, como o `read_only_fields` do serializer do DRF.
    """

    username = fields.String(dump_only=True, attribute="user.username")
    email = fields.String(dump_only=True, attribute="user.email")

    handle = fields.String(validate=validate.Length(max=50))
    bio = fields.String(validate=validate.Length(max=280))
    avatar_color = fields.String(validate=validate.Length(max=9))
    theme = fields.String(validate=validate.OneOf([t.value for t in Theme]))
    push_kinds = fields.List(fields.String())

    level = fields.Integer(dump_only=True)
    xp = fields.Integer(dump_only=True)
    xp_max = fields.Integer(dump_only=True)
    achievements = fields.Integer(dump_only=True)
    friends = fields.Integer(dump_only=True)
    days_active = fields.Integer(dump_only=True)
