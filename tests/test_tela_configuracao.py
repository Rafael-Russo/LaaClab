from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def _codigo():
    import sys
    sys.path.insert(0, str(RAIZ / "tests"))
    from test_frontend import _sem_comentarios

    return _sem_comentarios(
        (RAIZ / "view/estatico/js/configuracao.js").read_text(encoding="utf-8")
    )


def test_pagina_tem_os_campos(cliente):
    corpo = cliente.get("/configuracao").get_data(as_text=True)
    for campo in ["senha_atual", "senha_nova", "apelido", "bio"]:
        assert f'name="{campo}"' in corpo


def test_guarda_os_tokens_novos_depois_de_trocar_a_senha():
    """A troca revoga a sessão antiga de propósito. Sem guardar os
    tokens que ela devolve, a pessoa é expulsa no exato momento em que
    se protegeu."""
    texto = _codigo()
    assert "/api/auth/senha" in texto
    assert "guardarSessao" in texto


def test_erro_de_senha_atual_aparece_no_campo():
    """422 -> {"erros": {"senha_atual": [...]}} tem que acender o erro
    NO ELEMENTO do campo (id erro-senha_atual) -- não só disparar o
    alerta geral, que existe para erro SEM campo (401 de senha errada
    não tem, por exemplo). A string ".erros" sozinha não discrimina:
    aparece até se toda mensagem cair no alerta geral, contanto que o
    código ainda leia `erro.erros` em algum lugar."""
    texto = _codigo()

    # mostrarErros precisa rotear pelo NOME do campo que veio no erro
    # (errosPorCampo[campo]) e escrever no elemento achado -- não jogar
    # tudo para o alerta geral independente do que a API apontou.
    #
    # "\n  }" (indentado), não "\n}": mostrarErros está aninhada dentro
    # de Api.aoCarregar(async () => {...}), então sua chave de
    # fechamento tem 2 espaços de indentação, não fica na coluna 0.
    # Procurar "\n}" acharia só a chave de fechamento do wrapper
    # externo, no fim do arquivo -- capturando ~66% do arquivo em vez
    # da função. Mesma variante já usada em
    # test_falha_no_carregar_mais_nao_apaga_a_grade
    # (test_tela_explorar_frontend.py), para o mesmo motivo.
    inicio = texto.index("function mostrarErros(")
    corpo = texto[inicio : texto.index("\n  }", inicio)]
    assert "errosPorCampo[campo]" in corpo, (
        "mostrarErros não indexa o erro pelo nome do campo"
    )
    assert "alvo.textContent" in corpo, (
        "mostrarErros não escreve a mensagem no elemento do campo"
    )

    # E a tela de senha precisa ter registrado 'senha_atual' no mapa
    # que alimenta mostrarErros -- sem essa entrada, o roteamento por
    # campo genérico acima não tem para onde cair NESTE campo.
    assert 'senha_atual: document.getElementById("erro-senha_atual")' in texto
