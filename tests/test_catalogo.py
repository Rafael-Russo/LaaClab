"""Busca, ordenação por pontuação e filtro por gênero.

As três eram lacunas do spec da API sem dono desde o começo, e são o que
a tela Explorar exige.
"""
import pytest


@pytest.fixture
def catalogo(app):
    from app.extensions import db
    from app.models import BugometroStatus, Genero, Jogo, JogoGenero

    acao = Genero(nome="Ação", slug="acao")
    rpg = Genero(nome="RPG", slug="rpg")
    db.session.add_all([acao, rpg])
    db.session.flush()

    from app.services.jogo_service import normalizar_busca

    dados = [("Pokémon Legends", 80, acao), ("Elden Ring", 20, rpg), ("Zelda", 0, rpg)]
    jogos = {}
    for nome, pontuacao, genero in dados:
        jogo = Jogo(nome=nome, slug=nome.lower().replace(" ", "-"),
                    nome_busca=normalizar_busca(nome))
        db.session.add(jogo)
        db.session.flush()
        db.session.add(BugometroStatus(jogo_id=jogo.id, pontuacao=pontuacao,
                                       status="stable"))
        db.session.add(JogoGenero(jogo_id=jogo.id, genero_id=genero.id))
        jogos[nome] = jogo
    db.session.commit()
    return jogos


def _nomes(pagina):
    return [j.nome for j in pagina.itens]


def test_busca_ignora_acento_e_caixa(app, catalogo):
    from app.composicao import montar_servicos

    servicos = montar_servicos()
    assert _nomes(servicos.jogos.listar_catalogo(busca="pokemon")) == ["Pokémon Legends"]
    assert _nomes(servicos.jogos.listar_catalogo(busca="POKÉMON")) == ["Pokémon Legends"]


def test_busca_e_por_trecho_nao_por_prefixo(app, catalogo):
    from app.composicao import montar_servicos

    servicos = montar_servicos()
    assert _nomes(montar_servicos().jogos.listar_catalogo(busca="ring")) == ["Elden Ring"]


def test_busca_trata_curinga_do_like_como_texto(app, catalogo):
    """`%` e `_` digitados na caixa de busca são texto, não padrão.

    O dado importa: sem um nome que contenha os caracteres de verdade, o
    teste passa mesmo sem o `escape=` no `like()` — o SQLite trata `\\`
    como literal quando não há ESCAPE, e o padrão deixa de casar por
    coincidência, não por estar escapado.
    """
    from app.composicao import montar_servicos
    from app.extensions import db
    from app.models import Jogo
    from app.services.jogo_service import normalizar_busca

    for nome in ["100% Orange Juice", "Hack_Slash"]:
        db.session.add(
            Jogo(nome=nome, slug=normalizar_busca(nome).replace(" ", "-"),
                 nome_busca=normalizar_busca(nome))
        )
    db.session.commit()

    servicos = montar_servicos()

    # `%` casa só o jogo que tem `%` no nome, não o catálogo inteiro.
    resultado = servicos.jogos.listar_catalogo(busca="%")
    assert [j.nome for j in resultado.itens] == ["100% Orange Juice"]

    # `_` casa só o jogo que tem `_`, não qualquer caractere.
    resultado = servicos.jogos.listar_catalogo(busca="_")
    assert [j.nome for j in resultado.itens] == ["Hack_Slash"]


def test_ordena_por_pontuacao_que_mora_em_outra_tabela(app, catalogo):
    from app.composicao import montar_servicos

    servicos = montar_servicos()
    assert _nomes(servicos.jogos.listar_catalogo(ordenar_por="-pontuacao")) == [
        "Pokémon Legends", "Elden Ring", "Zelda",
    ]
    assert _nomes(servicos.jogos.listar_catalogo(ordenar_por="pontuacao")) == [
        "Zelda", "Elden Ring", "Pokémon Legends",
    ]


def test_jogo_sem_bugometro_ainda_aparece(app, catalogo):
    """O JOIN tem que ser externo: um jogo recém-cadastrado não tem linha
    de bugômetro, e sumir do catálogo por isso seria pior que ordenar mal.

    Só "está na lista" não observa o COALESCE(pontuacao, 0): com 4 jogos
    numa página de 20, todo mundo aparece em QUALQUER ordem, coalescido
    ou não. O que prova o COALESCE é a POSIÇÃO: pontuação nula tem que
    ordenar como zero -- entre Elden Ring (20) e Zelda (0), não antes
    de todo mundo (maior que 80, se nulo virasse "infinito" em algum
    dialeto) nem depois de todo mundo (se o banco jogasse NULL para o
    fim do DESC, como o SQLite faz sem COALESCE)."""
    from app.composicao import montar_servicos
    from app.extensions import db
    from app.models import Jogo
    from app.services.jogo_service import normalizar_busca

    db.session.add(Jogo(nome="Recem Chegado", slug="recem",
                        nome_busca=normalizar_busca("Recem Chegado")))
    db.session.commit()

    nomes = _nomes(montar_servicos().jogos.listar_catalogo(ordenar_por="-pontuacao"))
    assert "Recem Chegado" in nomes
    # Pokémon Legends (80), Elden Ring (20), depois o grupo empatado em
    # 0 (coalescido): Recem Chegado nasceu com id maior que Zelda, e o
    # desempate por id é descendente aqui (mesma direção do campo) --
    # então vem antes dela, não depois.
    assert nomes == ["Pokémon Legends", "Elden Ring", "Recem Chegado", "Zelda"]


def test_filtra_por_genero(app, catalogo):
    from app.composicao import montar_servicos

    nomes = _nomes(montar_servicos().jogos.listar_catalogo(genero_slug="rpg"))
    assert sorted(nomes) == ["Elden Ring", "Zelda"]


def test_ordenacao_desconhecida_continua_falhando_fechada(app, catalogo):
    from app.composicao import montar_servicos
    from app.errors import DadosInvalidos

    with pytest.raises(DadosInvalidos):
        montar_servicos().jogos.listar_catalogo(ordenar_por="senha_hash")


def test_desempate_por_id_em_pontuacoes_iguais(app, catalogo):
    """A fixture `catalogo` usa 80/20/0 -- todas distintas, então nunca
    há empate e o desempate por `Jogo.id` nunca é exercitado por
    nenhum teste deste arquivo. Acrescenta um jogo com a MESMA
    pontuação de Elden Ring (20) e atravessa a listagem com
    `por_pagina=1`: cada página é uma consulta SEPARADA, e sem uma
    chave de desempate total (a pontuação sozinha não distingue os
    dois) o banco fica livre para devolver os empatados em qualquer
    ordem em cada consulta -- o sintoma seria a paginação repetir ou
    pular um item entre uma chamada e outra."""
    from app.composicao import montar_servicos
    from app.extensions import db
    from app.models import BugometroStatus, Jogo
    from app.services.jogo_service import normalizar_busca

    empatado = Jogo(
        nome="Doom Eternal", slug="doom-eternal",
        nome_busca=normalizar_busca("Doom Eternal"),
    )
    db.session.add(empatado)
    db.session.flush()
    db.session.add(
        BugometroStatus(jogo_id=empatado.id, pontuacao=20, status="stable")
    )
    db.session.commit()

    servicos = montar_servicos()
    nomes = []
    for pagina in range(1, 5):
        resultado = servicos.jogos.listar_catalogo(
            ordenar_por="-pontuacao", por_pagina=1, pagina=pagina
        )
        nomes.extend(j.nome for j in resultado.itens)

    # Doom Eternal nasceu DEPOIS de Elden Ring (id maior) e os dois
    # empatam em 20 pontos: o desempate acompanha a mesma direção do
    # campo (descendente, porque `ordenar_por="-pontuacao"`), então
    # Doom Eternal aparece antes de Elden Ring -- sem repetir nem
    # pular nenhum dos quatro jogos ao longo das quatro páginas.
    assert nomes == ["Pokémon Legends", "Doom Eternal", "Elden Ring", "Zelda"]
