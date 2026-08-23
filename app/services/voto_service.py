"""Confirmação de bug. Votar mexe na pontuação, então recalcula."""
from app.errors import Conflito, DadosInvalidos
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

    def atualizar(self, identificador: int, dados_brutos: dict, usuario) -> dict:
        """Um voto não se transfere entre relatos.

        `relato_id` é gravável no schema, e o CRUD genérico expõe PUT.
        Permitir a troca exigiria ressincronizar origem e destino — e um
        voto pertence ao relato em que foi dado; movê-lo seria reescrever
        história, não corrigir dado.
        """
        voto = self.repositorio.obter_ou_erro(identificador, self.nome_recurso)
        novo_relato = (dados_brutos or {}).get("relato_id")

        if novo_relato is not None:
            # Comparar por VALOR, não por texto. `int()` cru estouraria
            # 500 com "abc"; `str()` diria que 1.0 é diferente de 1 e
            # bloquearia o dono legítimo. As duas coisas de uma vez:
            # converte, e converte falha vira 422.
            try:
                mudou = int(novo_relato) != voto.relato_id
            except (TypeError, ValueError) as erro:
                raise DadosInvalidos(
                    "relato_id inválido.",
                    erros={"relato_id": ["Informe um identificador numérico."]},
                ) from erro

            if mudou:
                raise DadosInvalidos(
                    "Voto não pode mudar de relato.",
                    erros={
                        "relato_id": [
                            "Um voto pertence ao relato em que foi dado."
                        ]
                    },
                )

        return super().atualizar(identificador, dados_brutos, usuario)

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
