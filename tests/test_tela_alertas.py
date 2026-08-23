from pathlib import Path

from test_frontend import _sem_comentarios

RAIZ = Path(__file__).resolve().parents[1]


def test_pagina_tem_as_regioes(cliente):
    corpo = cliente.get("/alertas").get_data(as_text=True)
    for regiao in ["al-list", "al-summary", "al-favorites"]:
        assert f'id="{regiao}"' in corpo


def test_usa_o_rotulo_pronto_da_api():
    """`severidade_rotulo` já vem em português; montar outro no cliente
    cria uma segunda tabela de vocabulário que diverge da primeira."""
    texto = _sem_comentarios((RAIZ / "view/estatico/js/alertas.js").read_text(encoding="utf-8"))
    assert "severidade_rotulo" in texto
    assert "/api/v1/telas/alertas" in texto


def test_catch_de_alertas_loga_erro_que_nao_e_da_api():
    """O catch só reagia a ErroApi: qualquer outro erro sumia
    inteiro — sem estado na tela, sem console.error. Console limpo
    mais "Carregando…" parado parece travamento, não defeito."""
    texto = _sem_comentarios((RAIZ / "view/estatico/js/alertas.js").read_text(encoding="utf-8"))
    trecho = texto[texto.index("initAlerts().catch") :]
    assert "console.error" in trecho


def test_catch_de_alertas_pinta_erro_tambem_para_erro_que_nao_e_da_api():
    """console.error sozinho não basta: sem pintar o estado de erro,
    `al-list` fica preso em "Carregando…" para sempre quando o erro
    não é ErroApi — a mesma regra do item 4 (nenhuma região em
    carregamento permanente). `Api.erro("al-list")` não pode ficar
    condicionado a `if (e instanceof ErroApi)`; tem que rodar nos dois
    casos (fora do 401, que já retorna antes)."""
    texto = _sem_comentarios((RAIZ / "view/estatico/js/alertas.js").read_text(encoding="utf-8"))
    trecho = texto[texto.index("initAlerts().catch") :]
    assert 'Api.erro("al-list")' in trecho
    assert "if (e instanceof ErroApi) {" not in trecho, (
        "Api.erro ainda parece condicionado só ao ramo ErroApi"
    )
