"""CRUD genérico com regra de negócio. NÃO importa Flask.

Erro é sinalizado por exceção de domínio; quem traduz para HTTP é o
handler registrado no factory.
"""
from marshmallow import ValidationError

from app.errors import AcessoNegado, DadosInvalidos, NaoAutorizado, NaoEncontrado


class ServicoBase:
    #: Campo que identifica o dono do recurso. ``None`` desliga a checagem.
    campo_dono = "usuario_id"

    #: Coluna booleana de moderação. ``None`` quando o model não a tem.
    #: Quando presente, conteúdo marcado some para quem não é admin.
    campo_oculto = None

    #: Se True, apenas administrador pode escrever.
    somente_admin = False

    #: Campo que grava o autor na criação. ``None`` não grava; ``"usuario_id"`` para a maioria.
    campo_autor = "usuario_id"

    #: Campos que só administrador pode escrever.
    campos_de_admin = ()

    def __init__(self, repositorio, schema_saida, schema_entrada, nome_recurso: str):
        self.repositorio = repositorio
        self.schema_saida = schema_saida
        self.schema_entrada = schema_entrada
        self.nome_recurso = nome_recurso

    # ------------------------------------------------------------------
    # Leitura
    # ------------------------------------------------------------------
    def listar(
        self,
        pagina=1,
        por_pagina=20,
        ordenar_por=None,
        filtros=None,
        usuario=None,
    ):
        filtros = dict(filtros or {})
        # Conteúdo moderado some para quem não é administrador (spec 4.8).
        # Sem usuário (leitura pública) conta como não-admin.
        if self.campo_oculto and not getattr(usuario, "is_admin", False):
            filtros[self.campo_oculto] = False

        resultado = self.repositorio.listar(
            pagina=pagina,
            por_pagina=por_pagina,
            ordenar_por=ordenar_por,
            filtros=filtros,
        )
        return {
            "itens": self.schema_saida.dump(resultado.itens, many=True),
            "pagina": resultado.pagina,
            "por_pagina": resultado.por_pagina,
            "total": resultado.total,
            "paginas": resultado.paginas,
        }

    def obter(self, identificador: int, usuario=None) -> dict:
        entidade = self.repositorio.obter_ou_erro(identificador, self.nome_recurso)
        # Sem isso o filtro da listagem seria decorativo: bastaria pedir
        # o recurso pelo id. Responde 404, não 403, para não revelar que
        # o conteúdo existe.
        if (
            self.campo_oculto
            and getattr(entidade, self.campo_oculto, False)
            and not getattr(usuario, "is_admin", False)
        ):
            raise NaoEncontrado(f"{self.nome_recurso} não encontrado.")
        return self.schema_saida.dump(entidade)

    def listar_entidades(
        self,
        por_pagina: int = 20,
        ordenar_por: str | None = None,
        filtros=None,
        usuario=None,
    ) -> list:
        """Entidades cruas, para outro Service compor. Não serializa —
        quem compõe decide o shape.

        Aplica o MESMO filtro de moderação que `listar`. Sem isso, um
        Service que componha conteúdo moderável precisaria lembrar de
        passar o filtro à mão toda vez — e esquecer uma vez vaza
        conteúdo oculto direto na tela.
        """
        filtros = dict(filtros or {})
        if self.campo_oculto and not getattr(usuario, "is_admin", False):
            filtros[self.campo_oculto] = False

        return self.repositorio.listar(
            pagina=1,
            por_pagina=por_pagina,
            ordenar_por=ordenar_por,
            filtros=filtros,
        ).itens

    def listar_todos(
        self,
        ordenar_por: str | None = None,
        filtros=None,
        usuario=None,
    ) -> list:
        """SEM TETO de paginação. Para composição interna que precisa de
        todos os itens (nunca vem do cliente). Aplica moderação igual ao
        `listar_entidades`. Pagina internamente porque o repositório tem
        TETO_POR_PAGINA que protege contra ?por_pagina= do cliente."""
        filtros = dict(filtros or {})
        if self.campo_oculto and not getattr(usuario, "is_admin", False):
            filtros[self.campo_oculto] = False

        itens = []
        pagina = 1
        while True:
            resultado = self.repositorio.listar(
                pagina=pagina,
                por_pagina=100,
                ordenar_por=ordenar_por,
                filtros=filtros,
            )
            itens.extend(resultado.itens)
            if pagina >= resultado.paginas:
                break
            pagina += 1
        return itens

    def obter_entidade(self, identificador: int, usuario=None):
        """Entidade crua, com a mesma proteção de moderação do `obter`."""
        entidade = self.repositorio.obter_ou_erro(identificador, self.nome_recurso)
        if (
            self.campo_oculto
            and getattr(entidade, self.campo_oculto, False)
            and not getattr(usuario, "is_admin", False)
        ):
            raise NaoEncontrado(f"{self.nome_recurso} não encontrado.")
        return entidade

    # ------------------------------------------------------------------
    # Escrita
    # ------------------------------------------------------------------
    def criar(self, dados_brutos: dict, usuario=None) -> dict:
        self._autorizar_criacao(usuario)
        dados = self._validar(dados_brutos)
        if usuario is not None and self.campo_autor:
            dados[self.campo_autor] = usuario.id
        entidade = self.repositorio.criar(**dados)
        return self.schema_saida.dump(entidade)

    def atualizar(self, identificador: int, dados_brutos: dict, usuario) -> dict:
        entidade = self.repositorio.obter_ou_erro(identificador, self.nome_recurso)
        self._autorizar_escrita(entidade, usuario)
        dados = self._validar(dados_brutos, parcial=True)

        # Moderar é ato de administrador. Sem esta trava, tornar `oculto`
        # gravável deixaria o autor esconder o próprio conteúdo — e o
        # `_autorizar_escrita` não pegaria, porque ele já passou.
        if (
            self.campo_oculto
            and self.campo_oculto in dados
            and not getattr(usuario, "is_admin", False)
        ):
            raise AcessoNegado("Acesso negado.")

        restritos = set(self.campos_de_admin) & set(dados)
        if restritos and not getattr(usuario, "is_admin", False):
            raise AcessoNegado("Acesso negado.")

        # Retaguarda própria: o dono NUNCA muda por PUT. Hoje os schemas
        # marcam o campo como dump_only, mas depender só disso significa
        # que um `Meta` esquecido em qualquer schema futuro vira sequestro
        # de posse silencioso.
        if self.campo_dono:
            dados.pop(self.campo_dono, None)
        entidade = self.repositorio.atualizar(entidade, **dados)
        return self.schema_saida.dump(entidade)

    def remover(self, identificador: int, usuario) -> None:
        entidade = self.repositorio.obter_ou_erro(identificador, self.nome_recurso)
        self._autorizar_escrita(entidade, usuario)
        self.repositorio.remover(entidade)

    # ------------------------------------------------------------------
    # Apoio
    # ------------------------------------------------------------------
    def _validar(self, dados_brutos: dict, parcial: bool = False) -> dict:
        try:
            return self.schema_entrada.load(dados_brutos or {}, partial=parcial)
        except ValidationError as erro:
            raise DadosInvalidos(
                "Dados inválidos.", erros=erro.messages
            ) from erro

    def _autorizar_criacao(self, usuario) -> None:
        """Autenticação e somente_admin para criação."""
        if usuario is None:
            raise NaoAutorizado("Autenticação necessária.")
        if self.somente_admin and not getattr(usuario, "is_admin", False):
            raise AcessoNegado("Acesso negado.")

    def _autorizar_escrita(self, entidade, usuario) -> None:
        """Autor ou administrador. Substitui o framework de permissões do
        Django (spec 4.8) — e mora AQUI, não espalhado nos controllers.

        A ORDEM das checagens é a parte que importa:

        1. Sem usuário é 401, antes de qualquer outra coisa. Uma versão
           anterior checava o dono primeiro e liberava quando ele era nulo,
           o que deixava recurso órfão editável até sem autenticação.
        2. Recurso órfão (dono nulo) fica restrito a administrador. Isso
           acontece de verdade: `relatos_bug.usuario_id` é
           `nullable=True, ondelete="SET NULL"`, então apagar um autor
           deixa os relatos dele sem dono.
        3. A comparação usa `str()` nos dois lados porque o subject do JWT
           trafega como string; `7 != "7"` negaria acesso ao dono legítimo.
        4. Conteúdo moderado (`campo_oculto`) é checado ANTES da posse: uma
           vez oculto, nem o autor edita ou apaga, só administrador. Checar
           a posse primeiro liberaria o autor a reescrever o conteúdo ou
           apagá-lo, destruindo o que o moderador ainda não revisou.
        """
        if usuario is None:
            raise NaoAutorizado("Autenticação necessária.")
        if getattr(usuario, "is_admin", False):
            return

        # Alguns recursos (catálogo, operação) têm `somente_admin = True`
        # e não podem ser editados por usuários comuns, mesmo se fossem donos.
        if self.somente_admin:
            raise AcessoNegado("Acesso negado.")

        # Conteúdo moderado é só do admin: uma vez oculto, nem o autor
        # escreve. O spec trata "oculto = true: só admin" como regra
        # SEPARADA de "autor ou admin", e o `obter` já impõe a mesma
        # assimetria. Sem isto, quem teve o post escondido poderia
        # reescrevê-lo — mascarando o motivo da moderação — ou apagá-lo,
        # destruindo o que o moderador ainda não revisou.
        if self.campo_oculto and getattr(entidade, self.campo_oculto, False):
            raise AcessoNegado("Acesso negado.")

        if not self.campo_dono:
            return

        dono = getattr(entidade, self.campo_dono, None)
        if dono is None or str(dono) != str(usuario.id):
            raise AcessoNegado("Acesso negado.")

    def repositorio_contagem(self, usuario=None, **filtros) -> int:
        """Contagem com a MESMA moderação de `listar_todos`.

        Sem isso o número diverge da lista que ele acompanha: um total
        de mensagens somando tópicos SEM os ocultos com posts INCLUINDO
        os ocultos é incoerente dentro do próprio número, e ninguém
        percebe olhando a tela.
        """
        if self.campo_oculto and not getattr(usuario, "is_admin", False):
            filtros[self.campo_oculto] = False
        return self.repositorio.contar(**filtros)
