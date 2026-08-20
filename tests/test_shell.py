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


def test_a_shell_carrega_bootstrap_e_o_tema(cliente_logado):
    html = cliente_logado.get("/").get_data(as_text=True)

    assert "vendor/bootstrap/bootstrap.min.css" in html
    assert "vendor/bootstrap/bootstrap.bundle.min.js" in html
    assert "css/theme.css" in html


def test_a_shell_expoe_o_objeto_LAAC_com_a_url_da_api(cliente_logado):
    html = cliente_logado.get("/").get_data(as_text=True)

    assert "window.LAAC" in html
    assert '"http://api.test"' in html


def test_a_shell_publica_o_id_do_usuario_logado(cliente_logado):
    html = cliente_logado.get("/").get_data(as_text=True)

    assert "usuarioId: 7" in html


def test_a_shell_mostra_o_level_card_do_usuario(cliente_logado):
    html = cliente_logado.get("/").get_data(as_text=True)

    assert "Nikola98" in html
    assert "Nível 12" in html


def test_o_level_card_e_declarado_uma_vez_e_usado_duas(cliente_logado):
    """Sidebar e offcanvas consomem a mesma macro, então os hooks de XP saem em
    duas cópias — F6 precisa preencher as duas, não só a primeira."""
    html = cliente_logado.get("/").get_data(as_text=True)

    assert html.count("data-xp-barra") == 2


def test_a_shell_oferece_logout(cliente_logado):
    html = cliente_logado.get("/").get_data(as_text=True)

    assert 'action="/sair"' in html


def test_a_shell_tem_sidebar_e_offcanvas(cliente_logado):
    html = cliente_logado.get("/").get_data(as_text=True)

    assert "laac-sidebar" in html
    assert 'class="offcanvas' in html


def test_a_navegacao_lista_os_seis_itens_primarios(cliente_logado):
    html = cliente_logado.get("/").get_data(as_text=True)

    for rotulo in ("Início", "Meus jogos", "BugoMetro", "Históricos", "Alertas", "Comunidade"):
        assert rotulo in html


def test_a_navegacao_e_declarada_uma_vez_e_usada_duas(cliente_logado):
    """Sidebar e offcanvas consomem a mesma partial, então cada item aparece 2x."""
    html = cliente_logado.get("/").get_data(as_text=True)

    assert html.count('href="/bugometro"') == 2


def test_o_item_da_tela_atual_vem_marcado_como_ativo(cliente_logado):
    html = cliente_logado.get("/alertas").get_data(as_text=True)

    assert 'nav-link active" href="/alertas"' in html
