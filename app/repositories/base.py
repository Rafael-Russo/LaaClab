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
        # Tupla vazia significa "este recurso não aceita ordenação do
        # cliente" — e NÃO "aceita qualquer coisa". O default é o mais
        # restritivo de propósito: um repositório que esqueça de declarar
        # a allowlist fica seguro, não exposto.
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
        """Traduz '-popularidade' em ORDER BY, com desempate obrigatório.

        **Falha FECHADA.** Sem allowlist declarada, nenhuma ordenação vinda
        do cliente é aceita. O contrário — pular a checagem quando a
        allowlist está vazia — deixaria `?ordenar_por=senha_hash` ordenar
        por uma coluna sensível, e `?ordenar_por=<relacionamento>` derrubar
        a requisição com 500.

        O desempate por `id` é SEMPRE acrescentado: campos empatados
        (`popularidade` é 0 em todo o catálogo) produzem ordem indefinida, e
        a paginação por número de página passa a repetir e pular itens. O
        spec sugere `<campo>, nome, id`; `id` sozinho já garante ordem
        total, e nem todo model tem coluna `nome`.
        """
        clausulas = []
        if ordenar_por:
            descendente = ordenar_por.startswith("-")
            campo = ordenar_por.lstrip("-")
            # Duas checagens: a allowlist é a política; a coluna real é a
            # rede contra um nome digitado errado na allowlist.
            if (
                campo not in self.ordenacao_permitida
                or campo not in self.model.__table__.columns
            ):
                raise DadosInvalidos(
                    "Ordenação inválida.",
                    erros={"ordenar_por": [f"'{campo}' não é permitido."]},
                )
            coluna = getattr(self.model, campo)
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
        """Traduz IntegrityError no erro certo. O código antigo deixava
        vazar e respondia 500 para email duplicado.

        Unicidade e chave estrangeira são erros diferentes: duplicar um
        email conflita com o estado existente (409), enquanto apontar para
        uma linha inexistente é dado de entrada inválido (422).
        """
        try:
            db.session.commit()
        except IntegrityError as erro:
            db.session.rollback()
            detalhe = str(getattr(erro, "orig", erro)).upper()
            if "FOREIGN KEY" in detalhe:
                raise DadosInvalidos(
                    "Referência inválida.",
                    erros={
                        "_": ["Um dos identificadores informados não existe."]
                    },
                ) from erro
            raise Conflito("Registro duplicado.") from erro
