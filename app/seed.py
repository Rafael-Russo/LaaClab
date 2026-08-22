"""Popula o banco com conteúdo de demonstração.

Os 26 jogos são reais, vindos da Steam, preservados da aplicação antiga
em `dados/jogos_steam.json`. O arquivo tem chaves em INGLÊS — é material
herdado, e a tradução acontece aqui.

O seed escreve pelos Services sempre que possível, para não contornar as
regras de negócio. Onde escreve direto no banco (relatos, alertas), chama
o recálculo do bugômetro explicitamente: não há signal para isso.
"""
import json
from pathlib import Path

from app.extensions import db

CAMINHO_DADOS = Path(__file__).resolve().parent.parent / "dados" / "jogos_steam.json"

USUARIO_DEMO = "gamer"
SENHA_DEMO = "gamerpass123"
ADMIN_DEMO = "moderador"
SENHA_ADMIN = "moderador123"

#: Pool de votantes, além de `gamer` e `moderador`. `VotoBug` tem
#: UniqueConstraint("relato_id", "usuario_id") — confirmação real exige
#: usuário real, não um literal em `confirmacoes`. Nomes previsíveis,
#: mesma senha para todas, criadas pelo mesmo caminho das outras contas.
JOGADORES_DEMO = [f"jogador{indice:02d}" for indice in range(1, 13)]
SENHA_JOGADOR = "jogador123"

#: (slug parcial, minutos jogados, progresso, favorito)
BIBLIOTECA_DEMO = [
    ("call-of-duty", 1767, 62, True),
    ("counter-strike", 4210, 88, True),
    ("grand-theft", 930, 41, False),
    ("apex", 615, 27, False),
    ("valorant", 120, 9, False),
]

#: (slug parcial, tipo, título, corpo)
TOPICOS_DEMO = [
    ("call-of-duty", "bug", "Alguém mais com crash no ato 2?",
     "Toda vez que entro na missão do metrô o jogo fecha sem aviso e "
     "perco o progresso da última meia hora."),
    ("counter-strike", "dica", "Config de mira que me ajudou",
     "Baixei a sensibilidade e subi o zoom do scope; a diferença no "
     "primeiro tiro foi grande."),
    ("grand-theft", "noticia", "Patch novo saiu hoje",
     "Corrigiram o bug de salvar no meio da missão."),
    ("apex", "discussao", "Qual lenda vocês estão jogando?",
     "Voltei depois de uns meses e o meta parece bem diferente."),
]

#: (slug parcial, severidade, texto)
ALERTAS_DEMO = [
    ("call-of-duty", "critica", "Servidores instáveis após o patch de ontem."),
    ("counter-strike", "instavel", "Queda de FPS relatada em mapas novos."),
    ("grand-theft", "atualizacao", "Atualização 1.6 disponível para download."),
]

#: (slug parcial, categoria, severidade, título, votos)
#: `votos` é quantos dos primeiros N votantes do pool confirmam o relato.
#: `confirmacoes` NUNCA vem deste número direto — sai de uma contagem
#: real dos votos criados, para não divergir assim que alguém confirmar
#: pela API (defeito 3 da revisão). A aritmética está calibrada contra
#: `bugometro_service.calcular_pontuacao`: call-of-duty soma 123 (teto
#: 100, faixa critical), counter-strike soma 48 (warning), os outros
#: ficam abaixo de 40 (stable) — e cada relato `alta` sozinho já passa
#: de 40 com 0 votos e não sai de `warning` nem saturado, então a faixa
#: do meio é estável sob voto novo.
RELATOS_DEMO = [
    ("call-of-duty", "crash", "critica", "Crash ao entrar no metrô", 12),
    ("call-of-duty", "desempenho", "alta", "Queda de FPS na área central", 6),
    ("counter-strike", "graficos", "alta", "Textura sumindo em Mirage", 12),
    ("grand-theft", "progressao", "baixa", "Missão não marca como concluída", 3),
    ("apex", "online", "media", "Desconexão ao entrar em partida", 8),
]

#: (slug parcial, autor, texto)
COMENTARIOS_DEMO = [
    ("call-of-duty", USUARIO_DEMO, "Depois do último patch melhorou bastante."),
    ("counter-strike", USUARIO_DEMO, "Continua sendo o melhor competitivo."),
    ("grand-theft", ADMIN_DEMO, "A cidade envelheceu muito bem."),
]


def carregar_jogos() -> list[dict]:
    return json.loads(CAMINHO_DADOS.read_text(encoding="utf-8"))


def semear(silencioso: bool = False) -> dict:
    """Popula o banco. Idempotente: rodar de novo não duplica nada."""
    from app.composicao import montar_servicos
    from app.models import (
        Alerta,
        Avaliacao,
        BibliotecaUsuario,
        Genero,
        Jogo,
        JogoGenero,
        Post,
        RelatoBug,
        Topico,
        Usuario,
        VotoBug,
    )

    servicos = montar_servicos()
    contagem = {"jogos": 0, "generos": 0, "topicos": 0, "relatos": 0}

    def falar(mensagem):
        if not silencioso:
            print(mensagem)

    # --- contas -------------------------------------------------------
    demo = _garantir_usuario(Usuario, USUARIO_DEMO, SENHA_DEMO, admin=False)
    admin = _garantir_usuario(Usuario, ADMIN_DEMO, SENHA_ADMIN, admin=True)
    # Pool de votantes: confirmação real (linha em `votos_bug`) exige um
    # usuário real por trás de cada voto.
    votantes = [
        _garantir_usuario(Usuario, nome, SENHA_JOGADOR, admin=False)
        for nome in JOGADORES_DEMO
    ]

    # --- jogos e gêneros ----------------------------------------------
    por_slug = {}
    for bruto in carregar_jogos():
        jogo = _garantir_jogo(servicos, Jogo, bruto, admin)
        por_slug[jogo.slug] = jogo
        contagem["jogos"] += 1

        for nome_genero in bruto.get("genres") or []:
            genero = _garantir_genero(Genero, servicos, nome_genero)
            contagem["generos"] += 1
            existe = db.session.execute(
                db.select(JogoGenero).where(
                    JogoGenero.jogo_id == jogo.id, JogoGenero.genero_id == genero.id
                )
            ).scalars().first()
            if existe is None:
                db.session.add(JogoGenero(jogo_id=jogo.id, genero_id=genero.id))
    db.session.commit()

    def achar(parcial):
        return next((j for s, j in por_slug.items() if parcial in s), None)

    # --- biblioteca ---------------------------------------------------
    for parcial, minutos, progresso, favorito in BIBLIOTECA_DEMO:
        jogo = achar(parcial)
        if jogo is None:
            continue
        existe = db.session.execute(
            db.select(BibliotecaUsuario).where(
                BibliotecaUsuario.usuario_id == demo.id,
                BibliotecaUsuario.jogo_id == jogo.id,
            )
        ).scalars().first()
        if existe is None:
            db.session.add(
                BibliotecaUsuario(
                    usuario_id=demo.id,
                    jogo_id=jogo.id,
                    minutos_jogados=minutos,
                    progresso=progresso,
                    favorito=favorito,
                )
            )
    db.session.commit()

    # --- fórum --------------------------------------------------------
    for parcial, tipo, titulo, corpo in TOPICOS_DEMO:
        jogo = achar(parcial)
        if jogo is None or _existe(Topico, Topico.titulo == titulo, Topico.jogo_id == jogo.id):
            continue
        db.session.add(
            Topico(
                titulo=titulo, corpo=corpo, tipo=tipo,
                jogo_id=jogo.id, usuario_id=demo.id,
            )
        )
        contagem["topicos"] += 1
    db.session.commit()

    primeiro = db.session.execute(db.select(Topico)).scalars().first()
    if primeiro is not None and not _existe(Post, Post.topico_id == primeiro.id):
        db.session.add(
            Post(topico_id=primeiro.id, usuario_id=admin.id,
                 conteudo="Consegui reproduzir aqui também. Vou registrar.")
        )
        db.session.add(
            Post(topico_id=primeiro.id, usuario_id=demo.id,
                 conteudo="Obrigado! Achei que era só comigo.")
        )
    db.session.commit()

    # --- alertas ------------------------------------------------------
    for parcial, severidade, texto in ALERTAS_DEMO:
        jogo = achar(parcial)
        if jogo is None or _existe(Alerta, Alerta.texto == texto, Alerta.jogo_id == jogo.id):
            continue
        db.session.add(
            Alerta(jogo_id=jogo.id, severidade=severidade, texto=texto)
        )
    db.session.commit()

    # --- relatos e votos ------------------------------------------------
    # `confirmacoes` é contagem derivada (mesma regra de
    # `voto_service._sincronizar`): o seed cria VOTOS de verdade e conta,
    # nunca grava um literal — senão o número diverge assim que alguém
    # confirma pela API (defeito 3 da revisão).
    for parcial, categoria, severidade, titulo, votos in RELATOS_DEMO:
        jogo = achar(parcial)
        if jogo is None:
            continue

        relato = db.session.execute(
            db.select(RelatoBug).where(
                RelatoBug.titulo == titulo, RelatoBug.jogo_id == jogo.id
            )
        ).scalars().first()
        if relato is None:
            relato = RelatoBug(
                jogo_id=jogo.id, usuario_id=demo.id, titulo=titulo,
                categoria=categoria, severidade=severidade, status="confirmado",
            )
            db.session.add(relato)
            db.session.flush()  # precisa do id antes de votar
            contagem["relatos"] += 1

        # `votantes[:votos]` satura em silêncio se a tabela pedir mais votos
        # do que há gente no pool: a pontuação simplesmente sairia menor que
        # a documentada, sem erro nenhum. Melhor estourar aqui.
        assert votos <= len(votantes), (
            f"{titulo!r} pede {votos} votos, o pool tem {len(votantes)}"
        )
        for votante in votantes[:votos]:
            ja_votou = db.session.execute(
                db.select(VotoBug).where(
                    VotoBug.relato_id == relato.id, VotoBug.usuario_id == votante.id
                )
            ).scalars().first()
            if ja_votou is None:
                db.session.add(VotoBug(relato_id=relato.id, usuario_id=votante.id))
        db.session.commit()

        relato.confirmacoes = db.session.execute(
            db.select(db.func.count())
            .select_from(VotoBug)
            .where(VotoBug.relato_id == relato.id)
        ).scalar_one()
    db.session.commit()

    for parcial, autor, texto in COMENTARIOS_DEMO:
        jogo = achar(parcial)
        if jogo is None or _existe(Avaliacao, Avaliacao.comentario == texto, Avaliacao.jogo_id == jogo.id):
            continue
        quem = demo if autor == USUARIO_DEMO else admin
        db.session.add(
            Avaliacao(jogo_id=jogo.id, usuario_id=quem.id, comentario=texto)
        )
    db.session.commit()

    # --- pontuação ----------------------------------------------------
    # Escrevemos relatos direto no banco, então o recálculo não aconteceu
    # sozinho: não há signal. Sem isto, todo jogo fica com pontuação zero
    # e o bugômetro nasce mudo.
    for jogo in por_slug.values():
        servicos.bugometro.recalcular(jogo)
    db.session.commit()

    falar(
        f"  {contagem['jogos']} jogos, {contagem['topicos']} tópicos, "
        f"{contagem['relatos']} relatos"
    )
    falar(f"  conta demo:  {USUARIO_DEMO} / {SENHA_DEMO}")
    falar(f"  conta admin: {ADMIN_DEMO} / {SENHA_ADMIN}")
    falar(
        f"  votantes:    {JOGADORES_DEMO[0]}..{JOGADORES_DEMO[-1]} / "
        f"{SENHA_JOGADOR}  (confirmam os relatos)"
    )
    return contagem


# ----------------------------------------------------------------------
def _existe(model, *condicoes) -> bool:
    return (
        db.session.execute(db.select(model).where(*condicoes)).scalars().first()
        is not None
    )


def _garantir_usuario(Usuario, nome, senha, admin):
    usuario = db.session.execute(
        db.select(Usuario).where(Usuario.nome_usuario == nome)
    ).scalars().first()
    if usuario is None:
        usuario = Usuario(
            nome_usuario=nome, email=f"{nome}@laaclab.dev",
            apelido=nome, is_admin=admin,
        )
        usuario.definir_senha(senha)
        db.session.add(usuario)
        db.session.commit()
    return usuario


def _garantir_genero(Genero, servicos, nome):
    from app.services.jogo_service import gerar_slug

    genero = db.session.execute(
        db.select(Genero).where(Genero.nome == nome)
    ).scalars().first()
    if genero is None:
        genero = Genero(nome=nome, slug=gerar_slug(nome))
        db.session.add(genero)
        db.session.commit()
    return genero


def _garantir_jogo(servicos, Jogo, bruto, admin):
    """Traduz as chaves em inglês do arquivo herdado e grava pelo Service,
    que gera slug e iniciais."""
    from app.services.jogo_service import gerar_slug

    slug = bruto.get("slug") or gerar_slug(bruto["name"])
    existente = db.session.execute(
        db.select(Jogo).where(Jogo.slug == slug)
    ).scalars().first()
    if existente is not None:
        return existente

    # ServicoBase.criar devolve um dict serializado pelo schema de saída;
    # a releitura abaixo recupera a entidade ORM para recalcular e usar em por_slug.
    servicos.jogos.criar(
        {
            "nome": bruto["name"],
            "descricao": bruto.get("short_description") or "",
            "sobre": bruto.get("about") or "",
            "capa_url": bruto.get("cover_image") or "",
            "capa_gradiente": bruto.get("cover") or None,
            "metacritic": bruto.get("metacritic"),
            "desenvolvedora": bruto.get("developer") or "",
            "publicadora": bruto.get("publisher") or "",
            # Formato da Steam em português ("27 out. 2022"). O Service
            # repassa como está: quem grava é dono do formato.
            "data_lancamento": bruto.get("release_date") or "",
            "curtidas": bruto.get("likes") or 0,
            "descurtidas": bruto.get("dislikes") or 0,
            "conquistas": bruto.get("achievements") or 0,
        },
        usuario=admin,
    )
    return db.session.execute(
        db.select(Jogo).where(Jogo.slug == slug)
    ).scalars().first()
