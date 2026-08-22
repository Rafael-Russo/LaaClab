"""Consultas específicas de usuário."""
from app.extensions import db
from app.models import Usuario
from app.repositories.base import RepositorioBase


class RepositorioUsuario(RepositorioBase):
    def __init__(self):
        super().__init__(
            Usuario, ordenacao_permitida=("nome_usuario", "nivel", "xp", "criado_em")
        )

    def buscar_por_identificador(self, identificador: str):
        """Aceita nome_usuario OU email — o formulário de login tem um campo só."""
        consulta = db.select(Usuario).where(
            (Usuario.nome_usuario == identificador) | (Usuario.email == identificador)
        )
        return db.session.execute(consulta).scalars().first()
