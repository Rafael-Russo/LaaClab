"""Identidade e autorização.

Substitui `django.contrib.auth`. As permissões deixam de passar pelo sistema
de `Permission`/`ContentType` do Django e viram strings guardadas na role —
o código só consulta duas delas, e o admin que justificava o resto saiu do
escopo na migração.
"""

from datetime import datetime
from enum import StrEnum

from flask_login import UserMixin
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    event,
    func,
)
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
    # Convenção fixada aqui para as fatias 2-6: `DateTime(timezone=True)` com
    # `server_default=func.now()` é para onde a spec manda todo `auto_now_add`
    # do Django. Gerado pelo servidor (não em Python) para que o valor exista
    # mesmo quando a linha nasce fora do ORM, e para não haver dois relógios
    # (app e banco) competindo pelo mesmo timestamp.
    date_joined: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    roles: Mapped[list[Role]] = relationship(
        secondary=user_roles, back_populates="users"
    )
    profile: Mapped["UserProfile"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    def set_password(self, raw: str) -> None:
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw: str) -> bool:
        return check_password_hash(self.password_hash, raw)

    def has_perm(self, perm: str) -> bool:
        """Mesma assinatura e mesmas strings do `has_perm` do Django.

        Staff passa em tudo, como no Django. Fora isso, basta uma role do
        usuário listar a permissão.

        A checagem de `is_active` vem antes da de staff — deliberado, não
        incidental, como no `ModelBackend.has_perm` do Django, que
        short-circuita em `is_active` antes de olhar pra staff. Hoje nenhum
        decorator chega a chamar `has_perm` numa conta desativada (todos
        checam `is_authenticated` antes, e `_load_user` já trata a sessão
        dela como anônima) — mas o método não pode depender disso
        implicitamente: uma chamada direta a `has_perm` numa conta staff
        desativada não pode devolver `True`.
        """
        if not self.is_active:
            return False
        if self.is_staff:
            return True
        return any(perm in (role.permissions or []) for role in self.roles)

    def __repr__(self) -> str:
        return f"<User {self.username}>"


class Theme(StrEnum):
    DARK = "dark"
    LIGHT = "light"


class UserProfile(db.Model):
    """Perfil do jogador, mostrado no widget da sidebar e na tela de perfil."""

    __tablename__ = "user_profile"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), unique=True
    )

    handle: Mapped[str] = mapped_column(String(50), default="")
    level: Mapped[int] = mapped_column(Integer, default=1)
    xp: Mapped[int] = mapped_column(Integer, default=0)
    xp_max: Mapped[int] = mapped_column(Integer, default=2000)
    bio: Mapped[str] = mapped_column(String(280), default="")
    avatar_color: Mapped[str] = mapped_column(String(9), default="#6b7cff")
    achievements: Mapped[int] = mapped_column(Integer, default=0)
    friends: Mapped[int] = mapped_column(Integer, default=0)
    days_active: Mapped[int] = mapped_column(Integer, default=0)
    theme: Mapped[str] = mapped_column(String(10), default=Theme.DARK)

    # Lista vazia = todos os tipos de notificação habilitados. A lista fechada
    # de tipos vive em `Notification.Kind`, que chega na fatia 6; até lá a
    # validação aceita qualquer lista de strings.
    push_kinds: Mapped[list] = mapped_column(db.JSON, default=list)

    user: Mapped[User] = relationship(back_populates="profile")

    def __repr__(self) -> str:
        return f"<UserProfile {self.handle}>"


@event.listens_for(User, "after_insert")
def _criar_perfil(mapper, connection, user):
    """Todo usuário tem perfil, desde o instante em que a conta existe.

    O Django fazia isto com um signal `post_save`. A spec trocou signals por
    chamada explícita nos services, mas este caso não é regra de negócio e sim
    invariante do model — então mora aqui, junto do que ele protege.

    Cobre só o caminho do ORM: `after_insert` dispara para o unit of work,
    não para um insert por Core ou em massa. Todo caminho usado hoje passa
    por `db.session.add(User(...))`, incluindo o `seed` — se algum dia
    alguém inserir `User` por fora do ORM, o perfil não nasce junto.
    """
    connection.execute(
        UserProfile.__table__.insert().values(user_id=user.id, handle=user.username)
    )
