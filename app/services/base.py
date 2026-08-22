"""CRUD genérico com regra de negócio. NÃO importa Flask.

Erro é sinalizado por exceção de domínio; quem traduz para HTTP é o
handler registrado no factory.
"""
from marshmallow import ValidationError

from app.errors import AcessoNegado, DadosInvalidos


class ServicoBase:
    #: Campo que identifica o dono do recurso. ``None`` desliga a checagem.
    campo_dono = "usuario_id"

    def __init__(self, repositorio, schema_saida, schema_entrada, nome_recurso: str):
        self.repositorio = repositorio
        self.schema_saida = schema_saida
        self.schema_entrada = schema_entrada
        self.nome_recurso = nome_recurso

    # ------------------------------------------------------------------
    # Leitura
    # ------------------------------------------------------------------
    def listar(self, pagina=1, por_pagina=20, ordenar_por=None, filtros=None):
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

    def obter(self, identificador: int) -> dict:
        entidade = self.repositorio.obter_ou_erro(identificador, self.nome_recurso)
        return self.schema_saida.dump(entidade)

    # ------------------------------------------------------------------
    # Escrita
    # ------------------------------------------------------------------
    def criar(self, dados_brutos: dict, usuario_id: int | None = None) -> dict:
        dados = self._validar(dados_brutos)
        if usuario_id is not None and self.campo_dono:
            dados[self.campo_dono] = usuario_id
        entidade = self.repositorio.criar(**dados)
        return self.schema_saida.dump(entidade)

    def atualizar(self, identificador: int, dados_brutos: dict, usuario) -> dict:
        entidade = self.repositorio.obter_ou_erro(identificador, self.nome_recurso)
        self._autorizar_escrita(entidade, usuario)
        dados = self._validar(dados_brutos, parcial=True)
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

    def _autorizar_escrita(self, entidade, usuario) -> None:
        """Autor ou administrador. Substitui o framework de permissões
        do Django (spec 4.8) — e mora AQUI, não espalhado nos controllers."""
        if usuario is not None and getattr(usuario, "is_admin", False):
            return
        if not self.campo_dono:
            return
        dono = getattr(entidade, self.campo_dono, None)
        if dono is None:
            return
        if usuario is None or dono != usuario.id:
            raise AcessoNegado("Acesso negado.")
