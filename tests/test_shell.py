from pathlib import Path

VENDOR = Path("app/static/vendor")

ARQUIVOS_ESPERADOS = [
    VENDOR / "bootstrap" / "bootstrap.min.css",
    VENDOR / "bootstrap" / "bootstrap.bundle.min.js",
    VENDOR / "chartjs" / "chart.umd.min.js",
    VENDOR / "material-symbols" / "material-symbols.css",
    VENDOR / "inter" / "inter.css",
    Path("app/static/css/theme.css"),
]


def test_todos_os_assets_estao_vendorados():
    faltando = [str(caminho) for caminho in ARQUIVOS_ESPERADOS if not caminho.is_file()]

    assert faltando == [], f"assets ausentes: {faltando}"


def test_nenhum_css_de_fonte_aponta_para_a_internet():
    """Os assets precisam funcionar offline (spec §7.2)."""
    for nome in ("material-symbols/material-symbols.css", "inter/inter.css"):
        conteudo = (VENDOR / nome).read_text(encoding="utf-8")

        assert "https://" not in conteudo, f"{nome} ainda referencia host externo"


def test_theme_css_define_a_paleta_do_spec():
    conteudo = Path("app/static/css/theme.css").read_text(encoding="utf-8")

    for token in (
        "--laac-sidebar",
        "--laac-surface",
        "--laac-estavel",
        "--laac-atencao",
        "--laac-critico",
    ):
        assert token in conteudo, f"token {token} ausente do theme.css"
