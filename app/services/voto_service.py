"""Confirmação de bug. Votar mexe na pontuação, então recalcula."""
from app.errors import Conflito
from app.services.base import ServicoBase


class VotoService(ServicoBase):
    campo_dono = "usuario_id"

    def __init__(
        self, *args, servico_bugometro=None, repositorio_relatos=None, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.servico_bugometro = servico_bugometro
        self.repositorio_relatos = repositorio_relatos

    def criar(self, dados_brutos: dict, usuario=None) -> dict:
        self._autorizar_criacao(usuario)
        dados = self._validar(dados_brutos)
        dados["usuario_id"] = usuario.id if usuario is not None else None

        if self.repositorio.existe(
            relato_id=dados["relato_id"], usuario_id=dados["usuario_id"]
        ):
            raise Conflito("Você já confirmou este bug.")

        voto = self.repositorio.criar(**dados)
        self._sincronizar(dados["relato_id"])
        return self.schema_saida.dump(voto)

    def remover(self, identificador: int, usuario) -> None:
        voto = self.repositorio.obter_ou_erro(identificador, self.nome_recurso)
        relato_id = voto.relato_id
        self._autorizar_escrita(voto, usuario)
        self.repositorio.remover(voto)
        self._sincronizar(relato_id)

    def _sincronizar(self, relato_id: int) -> None:
        """confirmacoes é contagem derivada; a pontuação depende dela."""
        relato = self.repositorio_relatos.obter(relato_id)
        if relato is None:
            return
        self.repositorio_relatos.atualizar(
            relato, confirmacoes=self.repositorio.contar(relato_id=relato_id)
        )
        if relato.jogo is not None:
            self.servico_bugometro.recalcular(relato.jogo)
