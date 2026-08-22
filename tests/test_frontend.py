"""Testes estruturais do frontend.

Não abrem navegador: verificam que as páginas são servidas, que o que
elas referenciam existe, e que o JS fala com rotas que a API realmente
tem — a classe de erro que mais custou na construção da API, duas
metades corretas isoladamente que não se encontram.

As rotas de página (`ROTAS_DE_PAGINA`) entram na Task 4, quando
`view/paginas/` passa a ter conteúdo. Até lá, testá-las aqui deixaria
o commit vermelho de propósito.
"""

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
PAGINAS = RAIZ / "view" / "paginas"
JS = RAIZ / "view" / "estatico" / "js"

#: Chaves do JS herdado, que falava com a API REST em inglês do Django.
#: Nenhuma pode sobreviver à conversão.
#: `xp_max` NÃO entra: é chave correta da API atual, em inglês por já
#: nascer assim no domínio. Denylist só aceita termo que a API não usa.
CHAVES_ANTIGAS = [
    "cover_file", "cover_image", "bug_score", "entry_id", "favorite",
    "avatar_color", "handle", "results", "initials", "csrftoken",
]


def _sem_comentarios(texto: str) -> str:
    """Remove comentários de JS antes de varrer.

    Varrer texto cru produziu três falsos positivos na construção da
    API, sempre o comentário que explicava a própria regra — inclusive
    a receita de conversão, que cita as chaves antigas de propósito.
    """
    texto = re.sub(r"/\*.*?\*/", " ", texto, flags=re.S)
    return re.sub(r"//[^\n]*", " ", texto)


def test_estatico_serve_o_css(cliente):
    resposta = cliente.get("/estatico/css/estilos.css")
    assert resposta.status_code == 200


ROTAS_DE_PAGINA = [
    "/",
    "/biblioteca",
    "/bugometro",
    "/jogo/cyberpunk-2077",
    "/alertas",
    "/comunidade",
    "/perfil",
    "/login",
    "/registro",
]


@pytest.mark.parametrize("rota", ROTAS_DE_PAGINA)
def test_pagina_responde_html(cliente, rota):
    resposta = cliente.get(rota)
    assert resposta.status_code == 200
    assert resposta.mimetype == "text/html"


def test_guarda_de_casca_acusa_pagina_nao_registrada(tmp_path, monkeypatch):
    """Falhar aberto é pior que não ter guarda: uma página nova que
    ninguém registrou passaria sem verificação e a saída ainda diria
    `Casca OK.`, dando confiança falsa."""
    import importlib.util
    import sys

    caminho = RAIZ / "tools" / "verificar_casca.py"
    spec = importlib.util.spec_from_file_location("verificar_casca", caminho)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules["verificar_casca"] = modulo
    spec.loader.exec_module(modulo)

    for nome in ["inicio.html", "login.html", "orfa.html"]:
        (tmp_path / nome).write_text(
            "<!-- CASCA:INICIO -->x<!-- CASCA:FIM -->", encoding="utf-8"
        )
    monkeypatch.setattr(modulo, "PAGINAS", tmp_path)
    monkeypatch.setattr(
        modulo, "GRUPOS", {"aplicação": ["inicio.html"], "autenticação": ["login.html"]}
    )

    assert modulo.main() == 1


def test_todo_asset_referenciado_existe():
    """Um <script src> quebrado deixa a tela em branco sem erro visível."""
    faltando = []
    for pagina in PAGINAS.glob("*.html"):
        texto = pagina.read_text(encoding="utf-8")
        for caminho in re.findall(r'(?:src|href)="(/estatico/[^"]+)"', texto):
            alvo = RAIZ / "view" / caminho.removeprefix("/")
            if not alvo.exists():
                faltando.append(f"{pagina.name} -> {caminho}")
    assert not faltando, "referências quebradas: " + ", ".join(faltando)


def test_casca_identica_dentro_de_cada_grupo():
    """A casca é copiada por decisão de projeto; a guarda é o preço."""
    import subprocess
    import sys

    resultado = subprocess.run(
        [sys.executable, str(RAIZ / "tools" / "verificar_casca.py")],
        capture_output=True, text=True,
    )
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr


def test_nenhuma_chave_do_js_antigo_sobreviveu():
    """O JS herdado lia chaves em inglês de uma API que não existe mais.
    Uma que escape rende `undefined` na tela, sem erro nenhum."""
    achados = []
    for arquivo in JS.glob("*.js"):
        texto = _sem_comentarios(arquivo.read_text(encoding="utf-8"))
        for chave in CHAVES_ANTIGAS:
            if chave in texto:
                achados.append(f"{arquivo.name}: {chave}")
    assert not achados, "chaves do JS antigo: " + ", ".join(achados)


def test_todo_endpoint_chamado_pelo_js_existe_na_api(app):
    """O teste que mais importa.

    Pega `/api/me/` contra `/api/v1/eu` — a classe de erro que mais
    custou na construção da API: duas metades corretas isoladamente que
    não se encontram. Aqui ela falha na suíte, não na tela.
    """
    regras = {str(r.rule) for r in app.url_map.iter_rules()}

    def normalizar(caminho):
        # `/api/v1/jogos/${id}` -> `/api/v1/jogos/<int:identificador>`
        caminho = caminho.split("?")[0].rstrip("/")
        return re.sub(r"\$\{[^}]+\}", "<>", caminho)

    normalizadas = {
        re.sub(r"<[^>]+>", "<>", regra.rstrip("/")) for regra in regras
    }

    desconhecidos = []
    for arquivo in JS.glob("*.js"):
        texto = _sem_comentarios(arquivo.read_text(encoding="utf-8"))
        for bruto in re.findall(r'["`](/api/[^"`\s]*)["`]', texto):
            if normalizar(bruto) not in normalizadas:
                desconhecidos.append(f"{arquivo.name}: {bruto}")

    assert not desconhecidos, "rotas que a API não tem: " + ", ".join(desconhecidos)


@pytest.mark.xfail(
    reason="Esboços são substituídos uma a uma pelas tarefas de tela; "
    "vira falha de verdade na integração.",
    strict=False,
)
def test_nenhum_esboco_de_tela_sobreviveu():
    """Um esboço que ficou para trás renderiza "Tela em construção"
    para o usuário e passaria em todos os outros testes: o asset
    existe, não tem chave antiga e não chama endpoint nenhum. O
    marcador é a única coisa que o denuncia."""
    esbocos = sorted(
        arquivo.name
        for arquivo in JS.glob("*.js")
        if "TELA-NAO-IMPLEMENTADA" in arquivo.read_text(encoding="utf-8")
    )
    assert not esbocos, "esboços não substituídos: " + ", ".join(esbocos)
