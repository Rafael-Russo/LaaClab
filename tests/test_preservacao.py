"""Garante que o que ainda não foi consumido continua existindo.

As onze telas já foram convertidas e vivem em `view/paginas/` e
`view/estatico/` — o material herdado que as alimentou (`view/templates/`,
`view/static/`, e por fim `view/herdado/`, consumido pela tela Explorar
na fase 2) cumpriu seu papel e saiu; o original segue no histórico do
git. O que resta é o que a fase 1 depende (a fixture do seed e a
ausência do Django) — não mais material herdado nenhum.
"""
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def test_fixture_de_jogos_foi_preservado():
    dados = json.loads((RAIZ / "dados/jogos_steam.json").read_text(encoding="utf-8"))
    assert isinstance(dados, list)
    assert len(dados) >= 20
    assert "name" in dados[0]


def test_o_django_realmente_sumiu():
    for caminho in ["manage.py", "config/settings.py", "core", "catalog",
                    "api-laravel-laaclab", "saas-api", "docker-compose.yml"]:
        assert not (RAIZ / caminho).exists(), f"{caminho} ainda existe"
