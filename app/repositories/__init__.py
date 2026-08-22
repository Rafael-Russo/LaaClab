"""Camada Repository — único lugar do projeto com db.session e db.select."""
from app.repositories.base import Pagina, RepositorioBase

__all__ = ["Pagina", "RepositorioBase"]
