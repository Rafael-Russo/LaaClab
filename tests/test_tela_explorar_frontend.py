"""Testes estruturais da tela Explorar (frontend).

Não confundir com tests/test_tela_explorar.py, que testa a API
(`GET /api/v1/telas/explorar`). Este arquivo testa a página e o JS que a
consomem: as regiões da tela, o envelope de paginação novo (`itens`,
não `.results`/`.next` do DRF herdado) e o POST de adicionar à
biblioteca (`jogo_id`).
"""
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def _codigo():
    import sys
    sys.path.insert(0, str(RAIZ / "tests"))
    from test_frontend import _sem_comentarios

    return _sem_comentarios(
        (RAIZ / "view/estatico/js/explorar.js").read_text(encoding="utf-8")
    )


def test_pagina_tem_as_regioes(cliente):
    corpo = cliente.get("/explorar").get_data(as_text=True)
    for regiao in ["ex-busca", "ex-genero", "ex-ordem", "ex-grade", "ex-mais"]:
        assert f'id="{regiao}"' in corpo


def test_usa_o_envelope_novo_e_nao_o_do_drf():
    texto = _codigo()
    assert "/api/v1/telas/explorar" in texto
    assert "itens" in texto
    assert ".results" not in texto
    # (Removido: `assert ".next" not in texto` -- tautologia. Nenhuma
    # versão deste arquivo jamais usou `.next`, e `next` já está na
    # denylist global de CHAVES_ANTIGAS em test_frontend.py; a
    # asserção nunca discriminou nada aqui.)

    # FE1: "Carregar mais" tem que seguir `dados.proxima` COMO VEIO, não
    # remontar a query a partir dos filtros da tela -- isso é a
    # armadilha que o próprio cabeçalho do arquivo descreve (a página 2
    # voltaria à ordenação padrão e misturaria resultados fora de
    # ordem).
    assert "proximoCaminho = dados.proxima" in texto, (
        "proximoCaminho não vem direto de dados.proxima"
    )
    inicio_clique = texto.index('"ex-mais").addEventListener("click"')
    bloco_clique = texto[inicio_clique : texto.index("});", inicio_clique)]
    assert "carregar(proximoCaminho" in bloco_clique, (
        '"Carregar mais" não repassa proximoCaminho adiante'
    )
    assert "montarCaminhoDaBusca()" not in bloco_clique, (
        '"Carregar mais" remonta a query em vez de seguir dados.proxima'
    )


def test_adicionar_a_biblioteca_manda_jogo_id():
    texto = _codigo()
    assert "/api/v1/biblioteca" in texto
    assert "jogo_id" in texto


def test_pagina_tem_a_regiao_de_erro_do_carregar_mais(cliente):
    """Item 7: o erro do incremental precisa de um lugar próprio na
    tela, perto do botão — sem isso não há como mostrá-lo sem reusar
    (e apagar) a grade."""
    corpo = cliente.get("/explorar").get_data(as_text=True)
    assert 'id="ex-erro-mais"' in corpo


def test_falha_no_carregar_mais_nao_apaga_a_grade():
    """Defeito 7 da revisão: `Api.erro("ex-grade", ...)` no catch do
    carregamento incremental usa `replaceChildren` por baixo e apagava
    os 60 jogos já na tela numa oscilação de rede ao clicar "Carregar
    mais" — só se recuperava mexendo na busca. O ramo de erro do
    incremental (`reset` falso) não pode tocar `ex-grade`; o de
    carregamento inicial (`reset` verdadeiro), que não tem nada a
    preservar, continua podendo."""
    texto = _codigo()
    # Duas funções têm "catch (erro) {": a do botão de biblioteca (trata
    # 409) e a de `carregar` (trata falha de rede). É esta segunda que
    # importa aqui — procurar a partir de `async function carregar`
    # evita pegar a primeira por engano.
    inicio_carregar = texto.index("async function carregar(")
    inicio = texto.index("catch (erro) {", inicio_carregar)
    bloco_catch = texto[inicio : texto.index("\n  }", inicio)]

    ramo_reset = bloco_catch[bloco_catch.index("if (reset)") : bloco_catch.index("} else {")]
    ramo_incremental = bloco_catch[bloco_catch.index("} else {") :]

    assert 'Api.erro("ex-grade"' in ramo_reset
    assert 'Api.erro("ex-grade"' not in ramo_incremental
    assert 'Api.erro("ex-erro-mais"' in ramo_incremental
    # O botão continua utilizável para nova tentativa, não escondido.
    assert "botaoMais.disabled = false" in ramo_incremental
    assert "style.display" not in ramo_incremental
