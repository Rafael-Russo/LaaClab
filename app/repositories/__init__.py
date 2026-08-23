"""Camada Repository — único lugar do projeto com db.session e db.select."""
from app.repositories.base import Pagina, RepositorioBase, classificar_integridade

__all__ = ["Pagina", "RepositorioBase", "classificar_integridade"]
