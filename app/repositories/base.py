"""CRUD genérico sobre um model. Nenhuma outra camada toca db.session."""
from dataclasses import dataclass
from typing import Any

from sqlalchemy.exc import IntegrityError

from app.errors import Conflito, DadosInvalidos, NaoEncontrado
from app.extensions import db

TETO_POR_PAGINA = 100


@dataclass
class Pagina:
    """Resultado paginado, sem nada de HTTP. O Controller o transforma
    no envelope JSON."""

    itens: list
    pagina: int
    por_pagina: int
    total: int
    paginas: int


class RepositorioBase:
    def __init__(self, model, ordenacao_permitida: tuple[str, ...] = ()):
        self.model = model
        # Allowlist contra injeção via ?ordenar_por= (defeito 7.2 do spec).
        self.ordenacao_permitida = ordenacao_permitida

    # ------------------------------------------------------------------
    # Leitura
    # ------------------------------------------------------------------
    def obter(self, identificador: int):
        return db.session.get(self.model, identificador)

    def obter_ou_erro(self, identificador: int, nome_recurso: str):
        entidade = self.obter(identificador)
        if entidade is None:
            raise NaoEncontrado(f"{nome_recurso} não encontrado.")
        return entidade

    def existe(self, **filtros) -> bool:
        return self.contar(**filtros) > 0

    def contar(self, **filtros) -> int:
        consulta = db.select(db.func.count()).select_from(self.model)
        for campo, valor in filtros.items():
            consulta = consulta.where(getattr(self.model, campo) == valor)
        return db.session.execute(consulta).scalar_one()

    def consulta_base(self):
        """Gancho para repositórios concretos acrescentarem joins/filtros."""
        return db.select(self.model)

    def listar(
        self,
        pagina: int = 1,
        por_pagina: int = 20,
        ordenar_por: str | None = None,
        filtros: dict[str, Any] | None = None,
    ) -> Pagina:
        por_pagina = max(1, min(por_pagina, TETO_POR_PAGINA))
        consulta = self.consulta_base()

        for campo, valor in (filtros or {}).items():
            consulta = consulta.where(getattr(self.model, campo) == valor)

        consulta = consulta.order_by(*self._clausulas_de_ordem(ordenar_por))

        resultado = db.paginate(
            consulta, page=pagina, per_page=por_pagina, error_out=False
        )
        return Pagina(
            itens=list(resultado.items),
            pagina=resultado.page,
            por_pagina=resultado.per_page,
            total=resultado.total,
            paginas=resultado.pages,
        )

    def _clausulas_de_ordem(self, ordenar_por: str | None):
        """Traduz '-popularidade' em ORDER BY. SEMPRE acrescenta id como
        desempate — sem isso, campos empatados (popularidade=0 em todo o
        catálogo) produzem ordem indefinida e a paginação repete e pula
        itens entre páginas."""
        clausulas = []
        if ordenar_por:
            descendente = ordenar_por.startswith("-")
            campo = ordenar_por.lstrip("-")
            if self.ordenacao_permitida and campo not in self.ordenacao_permitida:
                raise DadosInvalidos(
                    "Ordenação inválida.",
                    erros={"ordenar_por": [f"'{campo}' não é permitido."]},
                )
            coluna = getattr(self.model, campo, None)
            if coluna is not None:
                clausulas.append(coluna.desc() if descendente else coluna.asc())
        clausulas.append(self.model.id.asc())
        return clausulas

    # ------------------------------------------------------------------
    # Escrita
    # ------------------------------------------------------------------
    def criar(self, **dados):
        entidade = self.model(**dados)
        db.session.add(entidade)
        self._confirmar()
        return entidade

    def atualizar(self, entidade, **dados):
        for campo, valor in dados.items():
            setattr(entidade, campo, valor)
        self._confirmar()
        return entidade

    def remover(self, entidade) -> None:
        db.session.delete(entidade)
        self._confirmar()

    def _confirmar(self) -> None:
        """Traduz IntegrityError em Conflito. O código antigo deixava
        vazar e respondia 500 para email duplicado."""
        try:
            db.session.commit()
        except IntegrityError as erro:
            db.session.rollback()
            raise Conflito("Registro duplicado ou referência inválida.") from erro
