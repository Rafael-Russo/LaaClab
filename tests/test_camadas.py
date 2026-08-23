"""A guarda de camadas também roda sob pytest, para que ninguém
mergeie uma violação sem ver."""
import re
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "tools"))


def test_nenhuma_violacao_de_camada():
    from verificar_camadas import violacoes

    achados = violacoes()
    assert achados == [], "Violações de camada:\n" + "\n".join(achados)


# --- A guarda precisa pegar as formas evasivas, não só a mais óbvia ------

@pytest.mark.parametrize(
    "linha",
    [
        "from app.models import Jogo",
        "from app.models.jogo import Jogo",     # submódulo: a forma idiomática aqui
        "import app.models",
        "import app.models as m",
        "from app import models",
    ],
)
def test_toda_forma_de_importar_model_e_pega(linha):
    from verificar_camadas import IMPORTA_MODELS

    assert re.search(IMPORTA_MODELS, linha), f"escapou: {linha}"


@pytest.mark.parametrize(
    "linha",
    [
        "db.session.commit()",
        "banco.session.add(x)",                # evasão por alias
        "ext.db.session.rollback()",
        "db . session.flush()",
    ],
)
def test_toda_forma_de_tocar_a_sessao_e_pega(linha):
    from verificar_camadas import USA_SESSAO

    assert re.search(USA_SESSAO, linha), f"escapou: {linha}"


def test_paginate_tem_padrao_proprio():
    from verificar_camadas import USA_PAGINATE

    assert re.search(USA_PAGINATE, "db.paginate(consulta, page=1)")


@pytest.mark.parametrize(
    "linha",
    [
        "self.session_manager.iniciar(usuario)",
        "cache.sessions.clear()",
        "oauth.session_state = token",
    ],
)
def test_identificador_que_so_comeca_com_session_nao_e_violacao(linha):
    """Sem limite de palavra, a guarda obrigaria a renomear código
    legítimo só para agradar o linter."""
    from verificar_camadas import USA_SESSAO

    assert not re.search(USA_SESSAO, linha), f"falso positivo: {linha}"


def test_modulo_com_prefixo_models_nao_e_confundido_com_o_pacote():
    from verificar_camadas import IMPORTA_MODELS

    assert not re.search(IMPORTA_MODELS, "from app import models_utils")


def test_docstring_que_menciona_db_session_nao_e_violacao(tmp_path):
    """O crud_factory.py deste projeto tem exatamente essa docstring. Se a
    guarda não ignorar strings, ela quebra o build por causa de texto
    explicativo."""
    from verificar_camadas import _linhas_sem_texto

    arquivo = tmp_path / "exemplo.py"
    arquivo.write_text(
        '"""Aqui so existe HTTP. Nenhum db.session, nenhum model."""\n'
        "# comentario citando from app.models import Jogo\n"
        "def f():\n"
        "    return 1\n",
        encoding="utf-8",
    )
    limpas = "\n".join(_linhas_sem_texto(arquivo))
    assert "db.session" not in limpas
    assert "app.models" not in limpas
    assert "def f():" in limpas


def test_arquivo_com_sintaxe_quebrada_nao_derruba_a_guarda(tmp_path):
    from verificar_camadas import _linhas_sem_texto

    arquivo = tmp_path / "quebrado.py"
    arquivo.write_text("def f(:\n  pass\n", encoding="utf-8")
    assert _linhas_sem_texto(arquivo) == ["def f(:", "  pass"]


def test_init_esta_na_lista_de_excecoes_declaradas():
    """Item 5 da revisão final: os hooks de JWT em app/__init__.py tocam
    db.session porque rodam antes de qualquer Service existir no
    request. Sem entrar em EXCECOES_SESSAO, a exceção existe só por
    app/__init__.py estar fora do escopo de pasta varrido -- invisível,
    não declarada."""
    from verificar_camadas import EXCECOES_SESSAO

    assert "app/__init__.py" in EXCECOES_SESSAO


def test_sem_a_excecao_declarada_a_guarda_pega_a_sessao_do_init():
    """Confirma que app/__init__.py é REALMENTE varrido (não é exceção
    só porque ninguém olha) -- remover a entrada declarada tem que
    fazer a guarda achar os dois `db.session.get` dos hooks de JWT."""
    import verificar_camadas as vc

    excecoes_originais = set(vc.EXCECOES_SESSAO)
    try:
        vc.EXCECOES_SESSAO.discard("app/__init__.py")
        achados = [a for a in vc.violacoes() if a.startswith("app/__init__.py:")]
        assert len(achados) == 2
    finally:
        vc.EXCECOES_SESSAO.clear()
        vc.EXCECOES_SESSAO.update(excecoes_originais)


def test_uso_de_sessao_sem_marcador_em_init_e_acusado():
    """O teste que a versão anterior (supressão por ARQUIVO) não tinha.

    app/__init__.py inteiro estar em EXCECOES_SESSAO não pode significar
    "qualquer sessão aqui passa" -- só as duas linhas marcadas com
    MARCADOR_EXCECAO. Reproduz ao vivo o que a re-revisão fez: acrescenta
    uma sessão NOVA, sem marcador, no arquivo -- que continua declarado
    em EXCECOES_SESSAO -- e confirma que a guarda ainda assim acusa.
    Antes desta correção (supressão por arquivo), essa mesma sessão nova
    passava despercebida e "Camadas OK." mentia."""
    import verificar_camadas as vc

    caminho = RAIZ / "app" / "__init__.py"
    original = caminho.read_text(encoding="utf-8")
    assert "app/__init__.py" in vc.EXCECOES_SESSAO, (
        "pré-condição do teste: o arquivo precisa continuar declarado"
    )
    try:
        mutado = original.replace(
            "from app.extensions import db, jwt, migrate\n",
            "from app.extensions import db, jwt, migrate\n\n_x = db.session.execute\n",
            1,
        )
        assert mutado != original, "marcador de substituição não bateu no arquivo real"
        caminho.write_text(mutado, encoding="utf-8")

        achados = [a for a in vc.violacoes() if a.startswith("app/__init__.py:")]
        assert any("_x = db.session.execute" in a for a in achados), (
            "sessão nova sem MARCADOR_EXCECAO não foi acusada -- "
            f"achados: {achados}"
        )
    finally:
        caminho.write_text(original, encoding="utf-8")
