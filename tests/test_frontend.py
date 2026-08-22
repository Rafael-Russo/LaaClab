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
    """Remove comentários de JS respeitando literais de string.

    Varrer texto cru produziu três falsos positivos na construção da
    API, sempre o comentário que explicava a própria regra. Mas o
    removedor ingênuo tem o defeito oposto, e pior: `//` dentro de
    `"http://..."` apagava o resto da linha da varredura. Falso
    positivo faz barulho e alguém conserta; falso negativo silencia,
    e ninguém fica sabendo.

    O conteúdo das strings é preservado de propósito: é dele que
    `test_todo_endpoint_chamado_pelo_js_existe_na_api` extrai os
    caminhos `/api/...`.
    """
    saida = []
    i = 0
    limite = len(texto)
    aspas = None  # ' " ou ` enquanto dentro de uma string
    while i < limite:
        c = texto[i]
        if aspas:
            if c == "\\" and i + 1 < limite:
                saida.append(texto[i : i + 2])
                i += 2
                continue
            if c == aspas:
                aspas = None
            saida.append(c)
            i += 1
            continue
        if c in "'\"`":
            aspas = c
            saida.append(c)
            i += 1
            continue
        if c == "/" and i + 1 < limite and texto[i + 1] == "/":
            while i < limite and texto[i] != "\n":
                saida.append(" ")
                i += 1
            continue
        if c == "/" and i + 1 < limite and texto[i + 1] == "*":
            i += 2
            saida.append("  ")
            while i + 1 < limite and not (texto[i] == "*" and texto[i + 1] == "/"):
                saida.append("\n" if texto[i] == "\n" else " ")
                i += 1
            i += 2
            saida.append("  ")
            continue
        saida.append(c)
        i += 1
    return "".join(saida)


def test_removedor_de_comentarios_nao_confunde_url_com_comentario():
    """`//` dentro de string não é comentário. O removedor ingênuo
    apagava o resto da linha, e a varredura deixava de ver o código
    que vinha depois — falso negativo silencioso numa rede de
    segurança. O gatilho real é o `SVGNS = "http://..."` do JS
    legado que as telas convertem."""
    linha = 'const SVGNS = "http://www.w3.org/2000/svg"; usar("cover_file");'
    assert "cover_file" in _sem_comentarios(linha)


def test_removedor_de_comentarios_ainda_remove_comentarios():
    """O contrário também precisa valer: uma chave antiga citada num
    comentário (a própria receita de conversão cita) não pode acusar."""
    assert "cover_file" not in _sem_comentarios("// fala de cover_file aqui")
    assert "cover_file" not in _sem_comentarios("/* fala de\n cover_file */")


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
    Uma que escape rende `undefined` na tela, sem erro nenhum.

    Comparação por limite de palavra (`\\bfavorite\\b`), não substring:
    `favorite` cru também casava com os ids de DOM `home-favorites` e
    `al-favorites` (preservados do template legado de propósito) e com a
    variável local `favorites`, que não são a chave antiga."""
    achados = []
    for arquivo in JS.glob("*.js"):
        texto = _sem_comentarios(arquivo.read_text(encoding="utf-8"))
        for chave in CHAVES_ANTIGAS:
            if re.search(r"\b" + re.escape(chave) + r"\b", texto):
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


def _regex_de_destino_seguro():
    """Extrai a regex que `Api.destinoSeguro` usa em api.js e devolve
    compilada — testar contra o padrão que REALMENTE embarca, não uma
    cópia em Python que poderia divergir dele."""
    texto = (JS / "api.js").read_text(encoding="utf-8")
    casamento = re.search(
        r"destinoSeguro\(bruto\)\s*\{.*?(/(?:\\.|[^/\\\n])*/)\s*\.test\(bruto\)",
        texto,
        re.S,
    )
    assert casamento, "Api.destinoSeguro não encontrada em api.js no formato esperado"
    literal = casamento.group(1)[1:-1]  # remove as barras delimitadoras do literal JS
    return re.compile(literal.replace("\\/", "/"))


@pytest.mark.parametrize(
    "bruto,aceito",
    [
        ("/perfil", True),
        ("/bugometro?jogo=x", True),
        ("//evil.com", False),
        ("javascript:alert(1)", False),
        ("https://evil.com", False),
        ("", False),
    ],
)
def test_destino_seguro_aceita_so_caminho_same_origin(bruto, aceito):
    """`?destino=` só pode vir de Api.paraLogin(), que sempre produz
    location.pathname + location.search — um caminho same-origin.
    `//evil.com` é redirecionamento aberto: a tela de login real, no
    domínio real, manda a vítima para uma cópia depois de autenticar.
    `javascript:...` roda na própria origem, DEPOIS que guardarSessao()
    já gravou o token no localStorage — o cenário mais caro dos dois."""
    padrao = _regex_de_destino_seguro()
    assert bool(padrao.match(bruto)) == aceito


def test_destino_seguro_recusa_valor_nao_textual():
    """URLSearchParams.get() devolve `null` quando `destino` está
    ausente da URL — sem uma guarda de tipo explícita, o comportamento
    para esse caso (e para `undefined`) fica implícito. `null`/`undefined`
    têm que cair no mesmo "/" que qualquer valor recusado."""
    texto = (JS / "api.js").read_text(encoding="utf-8")
    trecho = texto[texto.index("destinoSeguro(bruto)") :]
    trecho = trecho[: trecho.index("},")]
    assert 'typeof bruto === "string"' in trecho


def test_destino_seguro_e_usado_no_login_e_registro():
    """A validação mora em api.js; login.js e registro.js só chamam —
    assim a terceira tela que precisar disso herda em vez de
    reinventar (e de repetir o bug)."""
    for nome in ["login.js", "registro.js"]:
        texto = _sem_comentarios((JS / nome).read_text(encoding="utf-8"))
        assert "Api.destinoSeguro(" in texto, f"{nome} não usa Api.destinoSeguro"
        assert 'destino || "/"' not in texto, f"{nome} ainda tem o fallback ingênuo"


def test_eh_sessao_expirada_implementada_corretamente():
    """`Api.ehSessaoExpirada` é o único lugar que decide se um erro é
    sessão expirada (401 já tratado por Api.paraLogin). Confere a
    implementação literal, não só a presença do nome da função."""
    texto = (JS / "api.js").read_text(encoding="utf-8")
    assert "ehSessaoExpirada(erro) {" in texto
    trecho = texto[texto.index("ehSessaoExpirada(erro) {") :]
    trecho = trecho[: trecho.index("},")]
    assert "erro instanceof ErroApi" in trecho
    assert "erro.status === 401" in trecho


def test_eh_sessao_expirada_e_usado_nos_arquivos_de_tela():
    """Um 401 já redirecionou; cada tela tratava esse caso do seu
    jeito (algumas pulavam no catch, outras pintavam erro por cima da
    navegação em voo). `Api.ehSessaoExpirada` centraliza a decisão —
    nenhum arquivo de tela pode mais montar a checagem "na mão", para
    que a décima tela herde o comportamento em vez de escolher o
    seu."""
    arquivos = [
        "biblioteca.js",
        "perfil.js",
        "comunidade.js",
        "bugometro.js",
        "jogo.js",
        "inicio.js",
        "alertas.js",
    ]
    checagem_manual = re.compile(r"instanceof\s+ErroApi\s*&&[^)]*status\s*===\s*401")
    for nome in arquivos:
        texto = _sem_comentarios((JS / nome).read_text(encoding="utf-8"))
        assert "Api.ehSessaoExpirada(" in texto, f"{nome} não usa Api.ehSessaoExpirada"
        assert not checagem_manual.search(texto), (
            f"{nome} ainda monta a checagem de 401 na mão em vez de usar o helper"
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
