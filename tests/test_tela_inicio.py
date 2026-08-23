"""A tela de início é servida e não referencia nada que não exista."""
import re
from pathlib import Path

from test_frontend import _sem_comentarios

RAIZ = Path(__file__).resolve().parents[1]


def test_pagina_tem_as_regioes_que_o_js_preenche(cliente):
    corpo = cliente.get("/").get_data(as_text=True)
    for regiao in ["home-hero", "home-updates", "home-trending",
                   "home-favorites", "home-alert-msg"]:
        assert f'id="{regiao}"' in corpo


def test_js_nao_linka_jogo_pelo_nome_de_exibicao():
    """`jogo` é o nome de exibição; linkar por ele gera
    /jogo/Grand Theft Auto V Legacy. Esta tela não constrói link
    nenhum diretamente — banners e atualizações não linkam, e os
    favoritos passam por `Api.cartaoDeJogo`, que já usa `slug`. Então
    nenhuma concatenação `"/jogo/" + algo` pode aparecer aqui a menos
    que `algo` seja um slug."""
    texto = _sem_comentarios((RAIZ / "view/estatico/js/inicio.js").read_text(encoding="utf-8"))
    for casamento in re.finditer(r'"/jogo/"\s*\+\s*([\w.]+)', texto):
        alvo = casamento.group(1)
        assert alvo.endswith("slug"), f"link por nome de exibição: {casamento.group(0)}"


def test_js_so_chama_o_endpoint_da_tela():
    texto = _sem_comentarios((RAIZ / "view/estatico/js/inicio.js").read_text(encoding="utf-8"))
    assert "/api/v1/telas/inicio" in texto


def test_banners_vazio_nao_quebra_e_mostra_estado_vazio():
    """`data.banners[0]` sem guarda é TypeError em banco recém-criado
    (`banners == []`, confirmado em
    test_banco_vazio_devolve_listas_vazias_sem_quebrar). A guarda tem
    que existir e render um estado vazio visível, não deixar a tela
    quebrar em silêncio."""
    texto = _sem_comentarios((RAIZ / "view/estatico/js/inicio.js").read_text(encoding="utf-8"))
    assert "data.banners.length === 0" in texto
    assert 'getElementById("hero-text")' in texto


def test_hero_vazio_nao_apaga_hero_text_e_hero_dots():
    """`home-hero` é ancestral de `hero-text`/`hero-dots`, lidos por id
    no ramo com banner logo abaixo. `Api.vazio("home-hero", ...)` (ou
    `carregando`/`erro` no mesmo alvo) faria `replaceChildren()` no
    ancestral e apagaria esses filhos — a mesma armadilha que quebrava
    `pf-usuario` (achado do item 4), a uma refatoração de distância
    aqui. O estado vazio tem que escrever em `hero-text`, não
    substituir o contêiner."""
    texto = _sem_comentarios((RAIZ / "view/estatico/js/inicio.js").read_text(encoding="utf-8"))
    for chamada in ("Api.vazio(", "Api.carregando(", "Api.erro("):
        assert f'{chamada}"home-hero"' not in texto, (
            f'{chamada}"home-hero"...) apagaria hero-text/hero-dots'
        )


def test_catch_de_inicio_loga_erro_que_nao_e_da_api():
    """Um TypeError (ex.: acesso indevido a `banners[0]`) não é
    ErroApi: o catch só reagia a ErroApi, e o erro sumia inteiro — sem
    estado na tela, sem console.error. Console limpo mais
    "Carregando…" parado parece travamento, não defeito."""
    texto = _sem_comentarios((RAIZ / "view/estatico/js/inicio.js").read_text(encoding="utf-8"))
    trecho = texto[texto.index("initHome().catch") :]
    assert "console.error" in trecho


def test_catch_de_inicio_pinta_erro_tambem_para_erro_que_nao_e_da_api():
    """console.error sozinho não basta: sem pintar o estado de erro,
    `home-updates` fica presa em "Carregando…" para sempre quando o
    erro não é ErroApi — a mesma regra do item 4 (nenhuma região em
    carregamento permanente). `Api.erro("home-updates")` não pode
    ficar condicionado a `if (e instanceof ErroApi)`; tem que rodar
    nos dois casos (fora do 401, que já retorna antes)."""
    texto = _sem_comentarios((RAIZ / "view/estatico/js/inicio.js").read_text(encoding="utf-8"))
    trecho = texto[texto.index("initHome().catch") :]
    assert 'Api.erro("home-updates")' in trecho
    assert "if (e instanceof ErroApi) {" not in trecho, (
        "Api.erro ainda parece condicionado só ao ramo ErroApi"
    )
