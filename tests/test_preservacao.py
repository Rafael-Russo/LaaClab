"""Garante que os arquivos herdados do Django sobreviveram à remoção.

Se este teste falhar, o plano de frontend perdeu sua matéria-prima.
"""
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

TEMPLATES = [
    "_shell.html", "_shell_auth.html", "home.html", "bugometro.html",
    "jogo.html", "explorar.html", "biblioteca.html", "comunidade.html",
    "alertas.html", "perfil.html", "login.html", "registro.html",
]

JS = [
    "app.js", "home.js", "bugometro.js", "jogo.js", "explorar.js",
    "biblioteca.js", "comunidade.js", "alertas.js", "perfil.js",
]


def test_todos_os_templates_foram_preservados():
    faltando = [n for n in TEMPLATES if not (RAIZ / "view/templates" / n).is_file()]
    assert faltando == [], f"templates perdidos: {faltando}"


def test_todos_os_js_foram_preservados():
    faltando = [n for n in JS if not (RAIZ / "view/static/js" / n).is_file()]
    assert faltando == [], f"scripts perdidos: {faltando}"


def test_css_foi_preservado_e_nao_esta_vazio():
    css = RAIZ / "view/static/css/styles.css"
    assert css.is_file()
    assert len(css.read_text(encoding="utf-8")) > 5000


def test_fixture_de_jogos_foi_preservado():
    dados = json.loads((RAIZ / "dados/jogos_steam.json").read_text(encoding="utf-8"))
    assert isinstance(dados, list)
    assert len(dados) >= 20
    assert "name" in dados[0]


def test_o_django_realmente_sumiu():
    for caminho in ["manage.py", "config/settings.py", "core", "catalog",
                    "api-laravel-laaclab", "saas-api", "docker-compose.yml"]:
        assert not (RAIZ / caminho).exists(), f"{caminho} ainda existe"
