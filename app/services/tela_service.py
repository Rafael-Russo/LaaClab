"""Composição dos payloads de tela.

Compõe SERVICES de domínio, nunca repositórios: cada regra continua morando
com seu dono, e esta camada só monta o objeto que a tela consome.
"""
from app.services.formatacao import tempo_relativo, duracao_jogada
from app.services.jogo_service import CAPA_PADRAO, gerar_iniciais

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
        servico_avaliacoes,
        servico_bugometro,
        servico_posts=None,
        servico_usuarios=None,
        servico_generos=None,
    ):
        self.jogos = servico_jogos
        self.alertas_servico = servico_alertas
        self.topicos = servico_topicos
        self.biblioteca_servico = servico_biblioteca
        self.auth = servico_auth
        self.avaliacoes = servico_avaliacoes
        self.bugometro_servico = servico_bugometro
        self.posts = servico_posts
        self.usuarios = servico_usuarios
        self.generos = servico_generos

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
            # Sem fallback: `None` é "não informada", e é o que
            # configuracao.js usa para deixar o campo em branco em vez
            # de reexibir um 0 que ninguém digitou.
            "idade": usuario.idade,
            "conquistas": usuario.conquistas,
            "amigos": usuario.amigos,
            "dias_ativo": usuario.dias_ativo,
            "avatar_url": usuario.avatar_url or "",
        }

    # ------------------------------------------------------------------
    def inicio(self, usuario_id: int) -> dict:
        favoritos = self._cartoes_favoritos(usuario_id)
        alertas = self.alertas_servico.recentes(limite=4)

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
        # Regra única (defeito 6 da revisão): `jogo` é sempre o NOME de
        # exibição; o slug, quando existe, é sempre `jogo_slug`.
        return {
            "jogo": jogo.nome,
            "jogo_slug": jogo.slug or "",
            "titulo": f"Novidades e atualizações em {jogo.nome}",
            "capa": self._capa(jogo),
        }

    def _atualizacao(self, alerta) -> dict:
        apresentado = self.alertas_servico.apresentar(alerta)
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
        entradas = self.biblioteca_servico.listar_entidades(
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
            return {"mensagem": SEM_ALERTA, "jogo": "", "jogo_slug": ""}
        primeiro = alertas[0]
        # Mesma regra do `_banner`: `jogo` é o nome, `jogo_slug` é o slug.
        return {
            "mensagem": primeiro.texto,
            "jogo": primeiro.jogo.nome if primeiro.jogo else "",
            "jogo_slug": primeiro.jogo.slug if primeiro.jogo else "",
        }

    # ------------------------------------------------------------------
    SEM_JOGOS = "Sem jogos cadastrados."
    TETO_SUBTITULO = 48

    def bugometro(self, slug: str | None = None, usuario=None) -> dict:
        jogo = self._jogo_do_bugometro(slug)
        status = jogo.bugometro
        biblioteca = self._biblioteca_por_jogo(usuario)
        favorito, na_biblioteca = self._estado_no_card(jogo.id, biblioteca)

        return {
            "jogo": self.jogos.montar_card(
                jogo, favorito=favorito, na_biblioteca=na_biblioteca
            ),
            "atualizado_ha": (
                tempo_relativo(status.atualizado_em) if status else "agora mesmo"
            ),
            "metricas": self.bugometro_servico.montar_metricas(jogo),
            "bugs": self.bugometro_servico.listar_ativos(jogo, usuario=usuario),
            "grafico": self.bugometro_servico.montar_grafico(),
            "atividades": self._atividades_do_jogo(jogo),
            "top_instaveis": self._top_instaveis(biblioteca),
        }

    def jogo(self, slug: str, usuario=None) -> dict:
        entidade = self.jogos.buscar_por_slug(slug)
        biblioteca = self._biblioteca_por_jogo(usuario)
        favorito, na_biblioteca = self._estado_no_card(entidade.id, biblioteca)
        return self.jogos.montar_detalhe(
            entidade,
            comentarios=self._comentarios(entidade),
            bugs=self.bugometro_servico.listar_ativos(entidade, usuario=usuario),
            favorito=favorito,
            na_biblioteca=na_biblioteca,
        )

    def explorar(
        self,
        usuario,
        pagina: int = 1,
        por_pagina: int = 20,
        ordenar_por: str | None = None,
        busca: str | None = None,
        genero_slug: str | None = None,
    ) -> dict:
        """Catálogo paginado com o estado da biblioteca de quem olha."""
        resultado = self.jogos.listar_catalogo(
            pagina=pagina,
            por_pagina=por_pagina,
            ordenar_por=ordenar_por,
            busca=busca,
            genero_slug=genero_slug,
        )
        # Uma consulta para a página inteira, não uma por cartão.
        na_biblioteca = self._biblioteca_por_jogo(usuario)
        itens = []
        for jogo in resultado.itens:
            entrada = na_biblioteca.get(jogo.id)
            itens.append(
                self.jogos.montar_card(
                    jogo,
                    favorito=bool(entrada and entrada.favorito),
                    na_biblioteca=entrada is not None,
                )
            )
        return {
            "itens": itens,
            "pagina": resultado.pagina,
            "por_pagina": resultado.por_pagina,
            "total": resultado.total,
            "paginas": resultado.paginas,
            "generos": [
                {"slug": g.slug or "", "nome": g.nome}
                for g in self.generos.listar_todos(ordenar_por="nome")
            ],
        }

    # ------------------------------------------------------------------
    RECENTES_NO_PERFIL = 3

    def biblioteca(self, usuario_id: int) -> dict:
        entradas = self._entradas_da_biblioteca(usuario_id)
        jogos = [self._entrada_em_cartao(e) for e in entradas if e.jogo is not None]
        # `total` é o tamanho da grade, nunca um COUNT separado: senão o
        # chip "Todos (N)" diverge do que a tela mostra.
        return {"total": len(jogos), "jogos": jogos}

    def perfil(self, usuario_id: int) -> dict:
        entradas = self._entradas_da_biblioteca(usuario_id)[: self.RECENTES_NO_PERFIL]
        return {
            "usuario": self.eu(usuario_id),
            "jogos_recentes": [
                {
                    "jogo": e.jogo.nome,
                    "jogo_slug": e.jogo.slug or "",
                    "capa": self._capa(e.jogo),
                    "duracao": duracao_jogada(e.minutos_jogados),
                    "porcentagem": e.progresso,
                }
                for e in entradas
                if e.jogo is not None
            ],
        }

    # ------------------------------------------------------------------
    def _entradas_da_biblioteca(self, usuario_id: int) -> list:
        """Escopo no repositório, não só na checagem de permissão: filtrar
        depois de carregar tudo é como biblioteca alheia vaza."""
        return self.biblioteca_servico.listar_todos(
            ordenar_por="-adicionado_em", filtros={"usuario_id": usuario_id}
        )

    def _entrada_em_cartao(self, entrada) -> dict:
        cartao = self.jogos.montar_card(
            entrada.jogo, favorito=entrada.favorito, na_biblioteca=True
        )
        # O PATCH de favorito usa este id. Mandar o id do jogo faria a
        # tela editar a entrada errada.
        cartao["entrada_id"] = entrada.id
        return cartao

    # ------------------------------------------------------------------
    def _jogo_do_bugometro(self, slug: str | None):
        """Sem slug, escolhe o mais instável. Sem jogos, 404 — o JS
        congela em 'Carregando…' se não receber nada."""
        from app.errors import NaoEncontrado

        if slug:
            return self.jogos.buscar_por_slug(slug)

        jogos = self.jogos.listar_todos()
        if not jogos:
            raise NaoEncontrado(self.SEM_JOGOS)
        return max(
            jogos, key=lambda j: j.bugometro.pontuacao if j.bugometro else 0
        )

    def _atividades_do_jogo(self, jogo) -> list[dict]:
        """Só alertas DESTE jogo. O sistema antigo caía num fallback
        global e mostrava alerta de outro jogo na tela."""
        alertas = self.alertas_servico.listar_entidades(
            por_pagina=4, ordenar_por="-criado_em", filtros={"jogo_id": jogo.id}
        )
        atividades = []
        for alerta in alertas:
            apresentado = self.alertas_servico.apresentar(alerta)
            texto = alerta.texto or ""
            if len(texto) > self.TETO_SUBTITULO:
                texto = texto[: self.TETO_SUBTITULO] + "…"
            atividades.append(
                {
                    "nivel": apresentado["nivel"],
                    "titulo": apresentado["severidade"],
                    "subtitulo": texto,
                    "quando": tempo_relativo(alerta.criado_em),
                }
            )
        return atividades

    def _biblioteca_por_jogo(self, usuario) -> dict:
        """Entradas da biblioteca do usuário, indexadas por jogo_id.

        Uma consulta por REQUEST, não um lookup por card: é o mesmo
        caminho (`biblioteca_servico.listar_todos`) que `_entradas_da_
        biblioteca` já usa, só que sem o filtro por usuário aplicado
        cedo demais — aqui o resultado alimenta vários jogos ao mesmo
        tempo. Sem `usuario` (rota sem autenticação, se um dia existir)
        devolve vazio: ausência de usuário é `False`, não esquecimento.
        """
        if usuario is None:
            return {}
        entradas = self.biblioteca_servico.listar_todos(
            filtros={"usuario_id": usuario.id}
        )
        return {e.jogo_id: e for e in entradas}

    @staticmethod
    def _estado_no_card(jogo_id: int, biblioteca: dict) -> tuple[bool, bool]:
        entrada = biblioteca.get(jogo_id)
        return bool(entrada and entrada.favorito), entrada is not None

    def _top_instaveis(self, biblioteca: dict, limite: int = 4) -> list[dict]:
        """Cartão completo: o JS mostrava iniciais hardcoded por falta
        de slug, iniciais e capa aqui."""
        jogos = self.jogos.listar_todos()
        jogos.sort(
            key=lambda j: j.bugometro.pontuacao if j.bugometro else 0, reverse=True
        )
        cartoes = []
        for j in jogos[:limite]:
            favorito, na_biblioteca = self._estado_no_card(j.id, biblioteca)
            cartoes.append(
                self.jogos.montar_card(j, favorito=favorito, na_biblioteca=na_biblioteca)
            )
        return cartoes

    def _comentarios(self, jogo) -> list[dict]:
        # Sem `usuario=`: conteúdo moderado não aparece na tela pública,
        # nem para admin — igual ao `_assuntos` da home. Fila de
        # moderação é outra tela, com outro endpoint.
        avaliacoes = self.avaliacoes.listar_entidades(
            por_pagina=10,
            ordenar_por="-criado_em",
            filtros={"jogo_id": jogo.id},
        )
        return [
            {
                "id": a.id,
                "texto": a.comentario or "",
                "autor": a.usuario.nome_usuario if a.usuario else "",
            }
            for a in avaliacoes
        ]

    # ------------------------------------------------------------------
    REGRAS_COMUNIDADE = [
        "Respeite todos os membros.",
        "Não faça spam ou autopromoção.",
        "Evite conteúdos ofensivos.",
        "Ajude outros jogadores!",
    ]
    TETO_RESUMO = 160
    TOPICOS_NA_TELA = 20
    ALERTAS_NA_TELA = 10

    def comunidade(self, slug: str | None = None) -> dict:
        topicos = self.topicos.listar_todos(ordenar_por="-criado_em")
        por_jogo = {}
        for topico in topicos:
            por_jogo[topico.jogo_id] = por_jogo.get(topico.jogo_id, 0) + 1

        jogos = self.jogos.listar_todos(ordenar_por="nome")
        cartoes = [self._cartao_de_praca(j, por_jogo.get(j.id, 0)) for j in jogos]

        selecionado = self._selecionar_praca(slug, jogos, por_jogo)
        visiveis = [
            t for t in topicos if selecionado is None or t.jogo_id == selecionado.id
        ]

        return {
            "selecionado": (
                self._cartao_de_praca(selecionado, por_jogo.get(selecionado.id, 0))
                if selecionado is not None
                else None
            ),
            "jogos": cartoes,
            "topicos": [
                self._topico_em_card(t) for t in visiveis[: self.TOPICOS_NA_TELA]
            ],
            "estatisticas": self._estatisticas(topicos),
            "regras": list(self.REGRAS_COMUNIDADE),
        }

    def alertas(self, usuario_id: int) -> dict:
        from app.services.rotulos import ROTULOS_NIVEL_ALERTA

        todos = self.alertas_servico.listar_todos(ordenar_por="-criado_em")
        contagem = {"critical": 0, "warning": 0, "stable": 0}
        for alerta in todos:
            nivel = self.alertas_servico.apresentar(alerta)["nivel"]
            contagem[nivel] = contagem.get(nivel, 0) + 1

        return {
            "alertas": [
                self._alerta_em_card(a) for a in todos[: self.ALERTAS_NA_TELA]
            ],
            # Sempre três linhas, nesta ordem, mesmo zeradas: o JS
            # renderiza os três chips fixos. Rótulo vem da MESMA fonte
            # que `AlertaService.apresentar` usa para o card — duas
            # tabelas divergindo em capitalização era o defeito 8.
            "resumo": [
                {
                    "nivel": nivel,
                    "contagem": contagem[nivel],
                    "rotulo": ROTULOS_NIVEL_ALERTA[nivel],
                }
                for nivel in ("critical", "warning", "stable")
            ],
            "favoritos": self._cartoes_favoritos(usuario_id),
        }

    # ------------------------------------------------------------------
    def _cartao_de_praca(self, jogo, total: int) -> dict:
        return {
            "id": jogo.id,  # criar tópico exige `jogo_id`
            "slug": jogo.slug or "",
            "nome": jogo.nome,
            # Mesma regra de `jogo_service.montar_card`: reaproveita
            # `gerar_iniciais`, não uma segunda decisão (defeito 7).
            "iniciais": jogo.iniciais or gerar_iniciais(jogo.nome),
            "capa": self._capa(jogo),
            "total_topicos": total,
        }

    def _selecionar_praca(self, slug, jogos, por_jogo):
        """Slug inválido é 404, não fallback silencioso: o sistema antigo
        caía em outro jogo e o usuário via tópicos que não pediu."""
        if slug:
            return self.jogos.buscar_por_slug(slug)
        if not jogos:
            return None
        return max(jogos, key=lambda j: por_jogo.get(j.id, 0))

    def _topico_em_card(self, topico) -> dict:
        from app.services.rotulos import nivel_tipo, rotulo_tipo

        corpo = topico.corpo or ""
        if len(corpo) > self.TETO_RESUMO:
            corpo = corpo[: self.TETO_RESUMO] + "…"

        return {
            "id": topico.id,
            "titulo": topico.titulo,
            "autor": topico.usuario.nome_usuario if topico.usuario else "",
            "quando": tempo_relativo(topico.criado_em),
            "resumo": corpo,
            "tipo": topico.tipo,
            "tipo_rotulo": rotulo_tipo(topico.tipo),
            "nivel": nivel_tipo(topico.tipo),
        }

    def _estatisticas(self, topicos: list) -> dict:
        """Inteiros crus: três dos quatro saíam formatados do servidor.
        A formatação de milhar é do JS.

        `mensagens` só soma posts que estão DENTRO de um tópico visível
        (defeito 4 da revisão): a moderação é aplicada ao flag do
        próprio post, nunca ao do tópico pai, então um post não-oculto
        num tópico oculto continuava sendo contado — o tile caía 1
        quando devia cair 3. `topicos` já é a lista visível (moderação
        aplicada por quem chama), então o filtro por `topico_id` aqui
        cobre exatamente esse buraco.
        """
        ids_visiveis = {t.id for t in topicos}
        posts_em_topicos_visiveis = [
            p for p in self.posts.listar_todos(usuario=None)
            if p.topico_id in ids_visiveis
        ]
        return {
            "membros": self.usuarios.repositorio_contagem(usuario=None),
            "topicos": len(topicos),
            "mensagens": len(topicos) + len(posts_em_topicos_visiveis),
            "jogos_ativos": len({t.jogo_id for t in topicos if t.jogo_id}),
        }

    def _alerta_em_card(self, alerta) -> dict:
        apresentado = self.alertas_servico.apresentar(alerta)
        return {
            "id": alerta.id,
            "jogo": apresentado["jogo"],
            "jogo_slug": apresentado["slug"],
            "severidade_rotulo": apresentado["severidade"],
            "nivel": apresentado["nivel"],
            "icone": apresentado["icone"],
            "texto": alerta.texto,
        }
