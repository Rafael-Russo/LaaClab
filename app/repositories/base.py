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


def classificar_integridade(erro: IntegrityError) -> Exception:
    """Traduz IntegrityError no erro de domínio certo.

    SQLite e MySQL descrevem os mesmos erros com textos diferentes:
    - Casar só o texto do SQLite faria a detecção passar aqui e falhar
      em produção — e nenhum teste pegaria, porque os testes rodam em SQLite.
    - Retorna DadosInvalidos (422) ou Conflito (409), conforme o tipo.
    """
    detalhe = str(getattr(erro, "orig", erro)).upper()
    codigo_mysql = (getattr(getattr(erro, "orig", None), "args", None) or [None])[0]

    # Campo obrigatório ausente → 422 validação
    if "NOT NULL" in detalhe or codigo_mysql == 1048:
        return DadosInvalidos("Campo obrigatório ausente.")

    # Chave estrangeira inválida → 422 validação
    if "FOREIGN KEY" in detalhe or codigo_mysql in (1451, 1452):
        return DadosInvalidos("Referência inválida.")

    # Duplicidade → 409 conflito com estado existente
    return Conflito("Registro duplicado.")


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
        descendente = False
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

        # O desempate segue a MESMA direção do campo. Com `-criado_em` e
        # timestamps iguais — comum em inserção em lote, seed, ou duas
        # escritas no mesmo milissegundo — um `id ASC` fixo devolveria o
        # mais ANTIGO primeiro, que é o oposto de "mais recente primeiro".
        clausulas.append(
            self.model.id.desc() if descendente else self.model.id.asc()
        )
        return clausulas

    # ------------------------------------------------------------------
    # Escrita
    # ------------------------------------------------------------------
    def criar(self, **dados):
        entidade = self.model(**dados)
        db.session.add(entidade)
        self._confirmar()
        return entidade

    def persistir(self, entidade):
        """Grava uma entidade já construída. Usado quando o Service precisa
        chamar um método da entidade antes de gravar (ex.: definir_senha)."""
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
        """Traduz IntegrityError no erro de domínio certo via classificar_integridade."""
        try:
            db.session.commit()
        except IntegrityError as erro:
            db.session.rollback()
            raise classificar_integridade(erro) from erro
