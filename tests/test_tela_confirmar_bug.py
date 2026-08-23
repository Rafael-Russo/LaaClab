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


def test_409_e_tratado_como_ja_confirmado_e_nao_como_erro():
    """Clicar duas vezes não é falha: o estado desejado já existe."""
    for nome in ["bugometro.js", "jogo.js"]:
        assert "409" in _codigo(nome), nome
