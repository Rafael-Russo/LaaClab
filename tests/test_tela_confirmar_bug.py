from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
JS = RAIZ / "view/estatico/js"


def _codigo(nome):
    import sys
    sys.path.insert(0, str(RAIZ / "tests"))
    from test_frontend import _sem_comentarios

    return _sem_comentarios((JS / nome).read_text(encoding="utf-8"))


def test_as_duas_telas_confirmam_bug():
    for nome in ["bugometro.js", "jogo.js"]:
        texto = _codigo(nome)
        assert "/api/v1/votos-bug" in texto, nome
        assert "ja_confirmei" in texto, nome
        # `botaoConfirmarBug` continuaria "presente" no arquivo mesmo se
        # ninguém a chamasse na renderização — ela ficaria definida e
        # morta, e o resto do teste (que só olha /votos-bug e
        # ja_confirmei, ambos dentro DELA) passaria do mesmo jeito. Uma
        # única ocorrência de "botaoConfirmarBug(" é só a declaração
        # (`function botaoConfirmarBug(bug) {`); uma segunda é uma
        # chamada de verdade em algum renderizador de lista de bugs.
        ocorrencias = texto.count("botaoConfirmarBug(")
        assert ocorrencias >= 2, (
            f"{nome}: botaoConfirmarBug parece só definida, nunca chamada "
            f"({ocorrencias} ocorrência(s))"
        )


def test_409_e_tratado_como_ja_confirmado_e_nao_como_erro():
    """Clicar duas vezes não é falha: o estado desejado já existe."""
    for nome in ["bugometro.js", "jogo.js"]:
        texto = _codigo(nome)
        assert "409" in texto, nome

        # Não basta o número 409 aparecer no arquivo (ele aparece até
        # no comentário que explica a regra) -- o RAMO que trata esse
        # status precisa chamar quem marca o botão como confirmado, não
        # reabilitá-lo como se fosse um erro qualquer.
        inicio_ramo = texto.index("status === 409")
        abre_chave = texto.index("{", inicio_ramo)
        fecha_chave = texto.index("}", abre_chave)
        ramo_409 = texto[abre_chave:fecha_chave]

        assert "marcarConfirmado()" in ramo_409, (
            f"{nome}: o ramo do 409 não chama marcarConfirmado()"
        )
        assert "botao.disabled = false" not in ramo_409, (
            f"{nome}: o ramo do 409 reabilita o botão, tratando o "
            "estado já alcançado como se fosse erro"
        )
