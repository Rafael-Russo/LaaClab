"""Consultas do catálogo que o CRUD genérico não cobre.

Busca, ordenação por pontuação e filtro por gênero pedem `LIKE`, JOIN e
relação N-N — três coisas que o `listar` genérico não faz, e que não
deviam vazar para o Service.
"""
from app.extensions import db
from app.models import BugometroStatus, Genero, Jogo, JogoGenero
from app.repositories.base import TETO_POR_PAGINA, Pagina, RepositorioBase

#: "pontuacao" pertence aqui de verdade: consulta_base() (abaixo) põe o
#: JOIN externo com bugometro_status em TODA listagem de jogo -- a rota
#: CRUD genérica e listar_catalogo() -- então o ramo dedicado em
#: _clausulas_de_ordem sempre tem a tabela no FROM, nos dois caminhos.
ORDENACAO_JOGOS = ("nome", "metacritic", "popularidade", "criado_em", "pontuacao")


def escapar_like(termo: str) -> str:
    """`%` e `_` digitados na busca são texto, não curinga.

    Sem isto, buscar `%` devolve o catálogo inteiro e `_` casa qualquer
    caractere — o usuário não escreveu um padrão, escreveu um nome.
    """
    return termo.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class RepositorioJogos(RepositorioBase):
    def __init__(self):
        super().__init__(Jogo, ordenacao_permitida=ORDENACAO_JOGOS)

    def consulta_base(self):
        """JOIN externo com o bugômetro, para toda listagem de jogo.

        Fica aqui, e não só no `listar_catalogo`, porque `_clausulas_de_ordem`
        aceita `pontuacao` para os dois caminhos: sem o JOIN no genérico, a
        rota CRUD monta `ORDER BY bugometro_status.pontuacao` sobre uma tabela
        fora do FROM e responde 500 — numa rota pública.

        EXTERNO de propósito: jogo recém-cadastrado não tem linha de status, e
        sumir do catálogo por isso seria pior que ordenar mal. `jogo_id` é
        UNIQUE em `bugometro_status`, então o JOIN não duplica linha nem infla
        a contagem.
        """
        return db.select(Jogo).outerjoin(
            BugometroStatus, BugometroStatus.jogo_id == Jogo.id
        )

    def listar_catalogo(
        self,
        pagina: int = 1,
        por_pagina: int = 20,
        ordenar_por: str | None = None,
        busca: str | None = None,
        genero_slug: str | None = None,
    ) -> Pagina:
        por_pagina = max(1, min(por_pagina, TETO_POR_PAGINA))

        # Uma definição só do JOIN: consulta_base() (herda do genérico
        # via a mesma sobrescrita que fecha o item 2 da revisão final).
        consulta = self.consulta_base()

        if busca:
            from app.services.jogo_service import normalizar_busca

            alvo = f"%{escapar_like(normalizar_busca(busca))}%"
            consulta = consulta.where(Jogo.nome_busca.like(alvo, escape="\\"))

        if genero_slug:
            consulta = consulta.where(
                Jogo.id.in_(
                    db.select(JogoGenero.jogo_id)
                    .join(Genero, Genero.id == JogoGenero.genero_id)
                    .where(Genero.slug == genero_slug)
                )
            )

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
        """`pontuacao` mora em `bugometro_status`, não em `jogos`.

        O caminho genérico exige que o campo seja coluna do próprio model
        — e essa checagem é a rede contra ordenar por coluna sensível.
        Em vez de afrouxá-la, este ramo trata o único campo que
        legitimamente vem de fora, e delega todo o resto.
        """
        if ordenar_por and ordenar_por.lstrip("-") == "pontuacao":
            descendente = ordenar_por.startswith("-")
            # COALESCE: jogo sem bugômetro tem pontuação nula, e nulo
            # ordena de forma diferente em cada banco. Zero é o valor que
            # o resto do sistema já usa para "sem relato".
            coluna = db.func.coalesce(BugometroStatus.pontuacao, 0)
            return [
                coluna.desc() if descendente else coluna.asc(),
                Jogo.id.desc() if descendente else Jogo.id.asc(),
            ]
        return super()._clausulas_de_ordem(ordenar_por)
