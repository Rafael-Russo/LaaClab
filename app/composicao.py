"""Composition root: monta Repository → Service e entrega ao Controller.

Vive fora de app/controllers/ de propósito: é o único lugar autorizado a
conhecer as três camadas ao mesmo tempo.
"""
from types import SimpleNamespace

from app.repositories.usuario_repository import RepositorioUsuario
from app.schemas.usuario import UsuarioSchema
from app.services.auth_service import AuthService


def montar_servicos() -> SimpleNamespace:
    repositorio_usuario = RepositorioUsuario()

    return SimpleNamespace(
        auth=AuthService(
            repositorio=repositorio_usuario,
            schema_saida=UsuarioSchema(),
        ),
    )
