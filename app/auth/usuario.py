"""Identidade do usuário como a shell precisa dela (spec §4.2).

O Flask não tem banco: o objeto vive na sessão assinada. Guardamos só os
quatro campos que a shell renderiza — o perfil completo é buscado pelo JS
direto da API quando a tela de Perfil precisa.
"""

from __future__ import annotations

from flask import session
from flask_login import UserMixin, user_logged_in

CAMPOS_DE_SESSAO = ("id", "nome_usuario", "avatar_url", "nivel")


class Usuario(UserMixin):
    def __init__(
        self, id: int, nome_usuario: str, avatar_url: str | None = None, nivel: int = 1
    ) -> None:
        self.id = id
        self.nome_usuario = nome_usuario
        self.avatar_url = avatar_url
        self.nivel = nivel

    @classmethod
    def da_api(cls, dados: dict) -> Usuario:
        return cls(
            id=dados["id"],
            nome_usuario=dados["nome_usuario"],
            avatar_url=dados.get("avatar_url"),
            nivel=dados.get("nivel") or 1,
        )

    @classmethod
    def da_sessao(cls, dados: dict) -> Usuario:
        return cls(**dados)

    def para_sessao(self) -> dict:
        return {campo: getattr(self, campo) for campo in CAMPOS_DE_SESSAO}

    def get_id(self) -> str:
        return str(self.id)


@user_logged_in.connect
def _gravar_na_sessao(_sender, user, **_extras) -> None:
    """Mantém `session["usuario"]` sincronizada com quem acabou de logar."""
    if isinstance(user, Usuario):
        session["usuario"] = user.para_sessao()
