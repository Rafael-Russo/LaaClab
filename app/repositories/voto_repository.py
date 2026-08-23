"""Consultas de voto que a tela precisa e o CRUD genérico não dá."""
from app.extensions import db
from app.models import VotoBug
from app.repositories.base import RepositorioBase


class RepositorioVotosBug(RepositorioBase):
    def __init__(self):
        super().__init__(VotoBug, ordenacao_permitida=("criado_em",))

    def ids_confirmados_por(self, usuario_id: int, relato_ids) -> set[int]:
        """Quais destes relatos o usuário já confirmou — numa consulta só.

        Um lookup por bug faria N consultas numa lista de 20, e é a forma
        que a revisão final da fase 1 cobrou no `favorito`. O `IN` mantém
        constante o número de idas ao banco.
        """
        ids = list(relato_ids)
        if not usuario_id or not ids:
            return set()
        consulta = db.select(VotoBug.relato_id).where(
            VotoBug.usuario_id == usuario_id,
            VotoBug.relato_id.in_(ids),
        )
        return set(db.session.execute(consulta).scalars())
