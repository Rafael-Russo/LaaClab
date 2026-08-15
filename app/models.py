"""Agregador de models.

O Alembic só enxerga uma tabela se a classe do model já tiver sido importada
quando o autogenerate roda. Cada fatia acrescenta seus imports aqui — este é
o único lugar que precisa ser lembrado ao criar um model novo.

A fatia 0 não tem models; os imports começam na fatia 1 (`accounts`/`core`).
"""

from app.accounts.models import Role, Theme, User, UserProfile, user_roles  # noqa: F401
from app.extensions import Base, db

__all__ = ["Base", "db", "Role", "Theme", "User", "UserProfile", "user_roles"]
