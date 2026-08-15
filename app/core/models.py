"""Módulos de funcionalidade ligáveis/desligáveis."""

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db

# Os módulos que ganham (ou perdem) link na navegação. `home`, `bugometro` e
# `perfil` são telas do núcleo, sempre ligadas, e nunca aparecem aqui.
MODULE_CANDIDATES = {"catalog", "community", "alerts"}


class Module(db.Model):
    __tablename__ = "module"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(String(200), default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    def __repr__(self) -> str:
        return f"<Module {self.key} {'on' if self.enabled else 'off'}>"


def module_enabled(key: str) -> bool:
    """True se o módulo está ligado. Módulo sem registro conta como ligado —
    assim um deploy novo não precisa semear a tabela para tudo funcionar."""
    linha = db.session.query(Module).filter_by(key=key).first()
    return linha.enabled if linha else True
