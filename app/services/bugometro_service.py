"""Fórmulas do bugômetro.

Os números são especificação, não exemplo — vieram de bugs/scoring.py e
core/services.py do Django. Não simplifique.
"""
import math

from app.services.base import ServicoBase
from app.services.jogo_service import status_para

#: Peso por severidade. Severidade desconhecida usa 10 (o mesmo de 'media').
PESOS_SEVERIDADE = {"baixa": 4, "media": 10, "alta": 20, "critica": 35}
PESO_PADRAO = 10

STATUS_ATIVOS = ("aberto", "confirmado")
TETO_CONFIRMACOES = 20

#: (chave, rótulo, ícone) — o front lê exatamente estas 4 chaves, nesta ordem.
CARDS = [
    ("crash", "Crash", "shield"),
    ("bugs", "Bugs", "bug"),
    ("stutter", "Stutter", "activity"),
    ("fps", "FPS Drop", "gauge"),
]

#: Categoria do relato → card que ele alimenta.
CATEGORIA_PARA_CARD = {
    "crash": "crash",
    "graficos": "bugs",
    "progressao": "bugs",
    "outro": "bugs",
    "desempenho": "stutter",
    "online": "fps",
}

ORDEM_SEVERIDADE = {"baixa": 0, "media": 1, "alta": 2, "critica": 3}

ROTULOS_GRAFICO = [
    "06h", "07h", "08h", "09h", "10h", "11h", "12h", "13h",
    "14h", "15h", "16h", "17h", "18h", "19h", "20h", "21h",
    "22h", "23h", "00h", "01h", "02h", "03h", "04h", "05h",
]


class BugometroService(ServicoBase):
    campo_dono = "usuario_id"

    def __init__(
        self,
        *args,
        repositorio_status=None,
        repositorio_jogos=None,
        repositorio_votos=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.repositorio_status = repositorio_status
        self.repositorio_jogos = repositorio_jogos
        self.repositorio_votos = repositorio_votos

    # ------------------------------------------------------------------
    @staticmethod
    def _relatos_ativos(jogo):
        return [r for r in jogo.relatos if r.status in STATUS_ATIVOS and not r.oculto]

    def calcular_pontuacao(self, jogo) -> int:
        total = 0.0
        for relato in self._relatos_ativos(jogo):
            base = PESOS_SEVERIDADE.get(relato.severidade, PESO_PADRAO)
            multiplicador = 1.5 if relato.status == "confirmado" else 1.0
            # Retornos decrescentes: satura em 2.0 aos 20 votos.
            impulso = 1.0 + min(relato.confirmacoes, TETO_CONFIRMACOES) / float(
                TETO_CONFIRMACOES
            )
            total += base * multiplicador * impulso
        return int(min(100, round(total)))

    # --- Escritas: toda uma delas recalcula --------------------------
    # Sem signals, o recálculo tem que ser explícito. Se alguém acrescentar
    # uma escrita nova e esquecer de chamar recalcular, a pontuação fica
    # errada em silêncio — é o modo de falha que a spec 4.1.1 descreve.
    def criar(self, dados_brutos: dict, usuario=None) -> dict:
        resultado = super().criar(dados_brutos, usuario=usuario)
        self._recalcular_por_id(resultado.get("jogo_id"))
        return resultado

    def atualizar(self, identificador: int, dados_brutos: dict, usuario) -> dict:
        entidade = self.repositorio.obter_ou_erro(identificador, self.nome_recurso)
        jogo_anterior = entidade.jogo_id

        resultado = super().atualizar(identificador, dados_brutos, usuario)
        self._recalcular_por_id(resultado.get("jogo_id"))

        # Mover um relato entre jogos tira pontuação de um e põe no
        # outro. Recalcular só o destino deixa a ORIGEM travada no valor
        # antigo — e sem erro nenhum, que é o modo de falha que este
        # ponto único de recálculo existe para evitar.
        if jogo_anterior != resultado.get("jogo_id"):
            self._recalcular_por_id(jogo_anterior)
        return resultado

    def remover(self, identificador: int, usuario) -> None:
        entidade = self.repositorio.obter_ou_erro(identificador, self.nome_recurso)
        jogo_id = entidade.jogo_id
        super().remover(identificador, usuario)
        self._recalcular_por_id(jogo_id)

    def _recalcular_por_id(self, jogo_id) -> None:
        if jogo_id is None:
            return
        jogo = self.repositorio_jogos.obter(jogo_id)
        if jogo is not None:
            self.recalcular(jogo)

    def recalcular(self, jogo) -> int:
        """Ponto ÚNICO de recálculo. O Django fazia isso por signal; sem
        signals, TODA escrita de relato, voto ou moderação chama aqui.
        Esquecer uma chamada deixa a pontuação errada sem nenhum erro."""
        pontuacao = self.calcular_pontuacao(jogo)
        nivel = status_para(pontuacao)["nivel"]

        status = jogo.bugometro
        if status is None:
            self.repositorio_status.criar(
                jogo_id=jogo.id, pontuacao=pontuacao, status=nivel
            )
        elif status.pontuacao != pontuacao or status.status != nivel:
            self.repositorio_status.atualizar(
                status, pontuacao=pontuacao, status=nivel
            )
        return pontuacao

    # ------------------------------------------------------------------
    def montar_metricas(self, jogo) -> list[dict]:
        baldes = {chave: [] for chave, _, _ in CARDS}
        for relato in self._relatos_ativos(jogo):
            baldes[CATEGORIA_PARA_CARD.get(relato.categoria, "bugs")].append(relato)

        metricas = []
        for chave, rotulo, icone in CARDS:
            valor, nivel = self._classificar_balde(baldes[chave])
            metricas.append(
                {
                    "chave": chave,
                    "rotulo": rotulo,
                    "valor": valor,
                    "nivel": nivel,
                    "icone": icone,
                }
            )
        return metricas

    @staticmethod
    def _classificar_balde(relatos: list) -> tuple[str, str]:
        if not relatos:
            return "Baixo", "stable"
        maxima = max(ORDEM_SEVERIDADE.get(r.severidade, 0) for r in relatos)
        if maxima >= ORDEM_SEVERIDADE["alta"] or len(relatos) >= 5:
            return "Alto", "critical"
        return "Médio", "warning"

    # ------------------------------------------------------------------
    @staticmethod
    def montar_grafico() -> dict:
        """DADO SINTÉTICO, por decisão registrada no spec (6.7).

        Não consulta o banco e não olha o relógio — reproduz exatamente o
        comportamento atual do Django. Histórico real depende da tabela
        historico_bug e é trabalho futuro.
        """

        def serie(amplitude: float, fase: float, base: float) -> list[int]:
            return [
                round(max(0, base + amplitude * math.sin((i / 24) * math.pi * 2 + fase)))
                for i in range(24)
            ]

        return {
            "rotulos": list(ROTULOS_GRAFICO),
            "series": [
                {"chave": "crash", "rotulo": "Crash", "dados": serie(35, 0.4, 55)},
                {"chave": "bug", "rotulo": "Bug", "dados": serie(28, 1.6, 45)},
                {"chave": "stutter", "rotulo": "Stutter", "dados": serie(22, 2.7, 35)},
                {"chave": "fps", "rotulo": "FPS Drop", "dados": serie(30, 3.9, 48)},
            ],
        }

    # --- Composição para as telas -------------------------------------
    def montar_bug(self, relato, ja_confirmei: bool) -> dict:
        """Par cru + rótulo: o cru define a cor, o rótulo define o texto.

        SEM DEFAULT em `ja_confirmei`: é estado do usuário logado, não do
        relato. Um default `False` transformaria esquecer de resolvê-lo em
        resposta errada em vez de erro — foi assim que `/telas/bugometro`
        mentiu sobre `favorito` na revisão da fase 1.
        """
        from app.services.rotulos import rotulo_categoria, rotulo_severidade

        return {
            "id": relato.id,
            "titulo": relato.titulo,
            "categoria": rotulo_categoria(relato.categoria),
            "confirmacoes": relato.confirmacoes,
            "severidade": relato.severidade,
            "severidade_rotulo": rotulo_severidade(relato.severidade),
            "status": relato.status,
            "ja_confirmei": ja_confirmei,
        }

    def listar_ativos(self, jogo, usuario=None, limite: int = 20) -> list[dict]:
        ativos = sorted(
            self._relatos_ativos(jogo),
            key=lambda r: (r.confirmacoes, r.criado_em),
            reverse=True,
        )[:limite]
        confirmados = set()
        if usuario is not None and self.repositorio_votos is not None:
            confirmados = self.repositorio_votos.ids_confirmados_por(
                usuario.id, [r.id for r in ativos]
            )
        return [self.montar_bug(r, r.id in confirmados) for r in ativos]
