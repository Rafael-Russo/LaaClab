"""Schemas Marshmallow do domínio accounts."""

from marshmallow import EXCLUDE, Schema, fields, validate

from app.accounts.models import Theme


class UserProfileSchema(Schema):
    """Perfil do usuário autenticado.

    Progressão (`level`, `xp`, contadores) é do servidor: sai na leitura e é
    ignorada na escrita, como o `read_only_fields` do serializer do DRF.

    `unknown = EXCLUDE` é o que torna esse "ignorada" verdadeiro. Sem ele o
    Marshmallow usa `RAISE`, e como campo `dump_only` fica fora do
    `load_fields`, um PATCH que devolva o objeto inteiro lido no GET — o
    caminho mais comum de um cliente — seria rejeitado por inteiro com 422 em
    vez de aplicar a parte editável.
    """

    class Meta:
        unknown = EXCLUDE

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
