from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ESTATICOS = RAIZ / "app" / "static" / "web"

# Os arquivos que os templates e o JS referenciam por caminho fixo. Se algum
# sumir na centralização, a tela quebra em runtime sem erro de import.
ESSENCIAIS = [
    "css/styles.css",
    "css/theme.css",
    "js/app.js",
    "vendor/bootstrap/bootstrap.min.css",
    "vendor/bootstrap/bootstrap.bundle.min.js",
    "vendor/material-symbols/material-symbols.css",
]


def test_arquivos_essenciais_existem():
    faltando = [caminho for caminho in ESSENCIAIS if not (ESTATICOS / caminho).is_file()]
    assert faltando == []


def test_a_sonda_da_fatia_0_foi_removida():
    assert not (ESTATICOS / "css" / "probe.css").exists()


def test_estaticos_do_django_continuam_no_lugar():
    """A fatia 7 é que remove o Django; até lá ele serve os originais."""
    assert (RAIZ / "core" / "static" / "web" / "css" / "styles.css").is_file()


def test_servidos_no_prefixo_web(client):
    resposta = client.get("/static/web/css/styles.css")
    assert resposta.status_code == 200
