"""Composição dos payloads de tela.

Compõe SERVICES de domínio, nunca repositórios: cada regra continua morando
com seu dono, e esta camada só monta o objeto que a tela consome.
"""
from app.services.formatacao import tempo_relativo
from app.services.jogo_service import CAPA_PADRAO

GRUPO_ASSUNTOS = "Últimos assuntos"
SEM_ALERTA = "Nenhum alerta recente."
XP_MAXIMO_PADRAO = 2000


class TelaService:
    def __init__(
        self,
        servico_jogos,
        servico_alertas,
        servico_topicos,
        servico_biblioteca,
        servico_auth,
    ):
        self.jogos = servico_jogos
        self.alertas = servico_alertas
        self.topicos = servico_topicos
        self.biblioteca = servico_biblioteca
        self.auth = servico_auth

    # ------------------------------------------------------------------
    def eu(self, usuario_id: int) -> dict:
        usuario = self.auth.obter_entidade(usuario_id)
        return {
            "id": usuario.id,
            "nome_usuario": usuario.nome_usuario,
            # Nunca vazio: o JS não tem fallback para o card de nível.
            "apelido": usuario.apelido or usuario.nome_usuario,
            "email": usuario.email,
            "nivel": usuario.nivel,
            "xp": usuario.xp,
            # Zero produziria NaN% na largura da barra de progresso.
            "xp_max": usuario.xp_max or XP_MAXIMO_PADRAO,
            "cor_avatar": usuario.cor_avatar,
            "bio": usuario.bio or "",
            "conquistas": usuario.conquistas,
            "amigos": usuario.amigos,
            "dias_ativo": usuario.dias_ativo,
            "avatar_url": usuario.avatar_url or "",
        }

    # ------------------------------------------------------------------
    def inicio(self, usuario_id: int) -> dict:
        favoritos = self._cartoes_favoritos(usuario_id)
        alertas = self.alertas.recentes(limite=4)

        return {
            "banners": [self._banner(j) for j in self.jogos.destaques(limite=3)],
            "atualizacoes": [self._atualizacao(a) for a in alertas],
            "assuntos": self._assuntos(limite=8),
            "favoritos": favoritos,
            "alerta": self._alerta_do_topo(alertas),
        }

    # ------------------------------------------------------------------
    @staticmethod
    def _capa(jogo) -> list:
        gradiente = jogo.capa_gradiente or None
        if not gradiente or len(gradiente) < 2:
            return list(CAPA_PADRAO)
        return list(gradiente)

    def _banner(self, jogo) -> dict:
        return {
            "jogo": jogo.slug or "",
            "titulo": f"Novidades e atualizações em {jogo.nome}",
            "capa": self._capa(jogo),
        }

    def _atualizacao(self, alerta) -> dict:
        apresentado = self.alertas.apresentar(alerta)
        return {
            "jogo": apresentado["jogo"],
            "jogo_slug": apresentado["slug"],
            "capa": self._capa(alerta.jogo) if alerta.jogo else list(CAPA_PADRAO),
            "etiqueta": apresentado["severidade"],
            "nivel": apresentado["nivel"],
            # Caixa alta no servidor: o CSS não aplica text-transform aqui.
            "titulo": apresentado["jogo"].upper(),
            "texto": alerta.texto,
            "quando": tempo_relativo(alerta.criado_em),
        }

    def _assuntos(self, limite: int) -> list[dict]:
        # `listar_entidades` e não `.repositorio`: um Service alcançar o
        # repositório de outro é o vazamento que esta camada evita.
        # Sem `filtros={"oculto": False}` à mão: `listar_entidades` já
        # aplica a moderação, e depender da memória de quem compõe é
        # exatamente como conteúdo escondido vaza para a tela.
        topicos = self.topicos.listar_entidades(
            por_pagina=limite, ordenar_por="-criado_em"
        )
        return [{"grupo": GRUPO_ASSUNTOS, "titulo": t.titulo} for t in topicos]

    def _cartoes_favoritos(self, usuario_id: int) -> list[dict]:
        entradas = self.biblioteca.listar_entidades(
            por_pagina=50,
            ordenar_por="-adicionado_em",
            filtros={"usuario_id": usuario_id, "favorito": True},
        )
        return [
            self.jogos.montar_card(e.jogo, favorito=True, na_biblioteca=True)
            for e in entradas
            if e.jogo is not None
        ]

    @staticmethod
    def _alerta_do_topo(alertas: list) -> dict:
        if not alertas:
            return {"mensagem": SEM_ALERTA, "jogo": ""}
        primeiro = alertas[0]
        return {
            "mensagem": primeiro.texto,
            "jogo": primeiro.jogo.slug if primeiro.jogo else "",
        }
