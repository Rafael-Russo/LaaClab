"""Garante que o que ainda não foi consumido continua existindo.

Nove das dez telas já foram convertidas e vivem em `view/paginas/` e
`view/estatico/` — o material herdado que as alimentou (`view/templates/`,
`view/static/`) cumpriu seu papel e saiu; o original segue no histórico
do git. O que resta é o insumo de um trabalho que ainda não aconteceu:
a tela Explorar, em `view/herdado/`. Este arquivo protege isso, e o
resto do que a fase 1 depende (a fixture do seed e a ausência do
Django) — não mais o material já consumido.
"""
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def test_material_da_tela_explorar_foi_preservado():
    """Explorar é a única das dez telas não convertida na fase 1: falta
    busca sem acento, ordenação por pontuação e filtro por gênero, que a
    API ainda não tem (fase 2). Até lá, o template e o script Django
    dela ficam em `view/herdado/` como insumo — apagados, a conversão
    perde a receita."""
    html = RAIZ / "view/herdado/explorar.html"
    js = RAIZ / "view/herdado/explorar.js"
    assert html.is_file() and len(html.read_text(encoding="utf-8")) > 0
    assert js.is_file() and len(js.read_text(encoding="utf-8")) > 0


def test_fixture_de_jogos_foi_preservado():
    dados = json.loads((RAIZ / "dados/jogos_steam.json").read_text(encoding="utf-8"))
    assert isinstance(dados, list)
    assert len(dados) >= 20
    assert "name" in dados[0]


def test_o_django_realmente_sumiu():
    for caminho in ["manage.py", "config/settings.py", "core", "catalog",
                    "api-laravel-laaclab", "saas-api", "docker-compose.yml"]:
        assert not (RAIZ / caminho).exists(), f"{caminho} ainda existe"
