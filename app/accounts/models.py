"""Identidade e autorização.

Substitui `django.contrib.auth`. As permissões deixam de passar pelo sistema
de `Permission`/`ContentType` do Django e viram strings guardadas na role —
o código só consulta duas delas, e o admin que justificava o resto saiu do
escopo na migração.
"""

from datetime import UTC, datetime

from flask_login import UserMixin
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import Base, db

user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("user.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", Integer, ForeignKey("role.id", ondelete="CASCADE"), primary_key=True),
)


class Role(db.Model):
    """Um papel e as permissões que ele concede.

    `permissions` guarda as strings no formato do Django (`app.codename`) para
    que os call sites de `has_perm` não mudem de forma na migração.
    """

    __tablename__ = "role"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    label: Mapped[str] = mapped_column(String(200), default="")
    permissions: Mapped[list] = mapped_column(db.JSON, default=list)

    users: Mapped[list["User"]] = relationship(
        secondary=user_roles, back_populates="roles"
    )

    def __repr__(self) -> str:
        return f"<Role {self.name}>"


class User(UserMixin, db.Model):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(150), unique=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))

    is_staff: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    date_joined: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )

    roles: Mapped[list[Role]] = relationship(
        secondary=user_roles, back_populates="users"
    )

    def set_password(self, raw: str) -> None:
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw: str) -> bool:
        return check_password_hash(self.password_hash, raw)

    def has_perm(self, perm: str) -> bool:
        """Mesma assinatura e mesmas strings do `has_perm` do Django.

        Staff passa em tudo, como no Django. Fora isso, basta uma role do
        usuário listar a permissão.
        """
        if self.is_staff:
            return True
        return any(perm in (role.permissions or []) for role in self.roles)

    def __repr__(self) -> str:
        return f"<User {self.username}>"
