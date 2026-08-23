from pathlib import Path

from test_frontend import _sem_comentarios

RAIZ = Path(__file__).resolve().parents[1]


def test_pagina_tem_as_regioes(cliente):
    corpo = cliente.get("/comunidade").get_data(as_text=True)
    for regiao in ["co-pracas", "co-topicos", "co-stats"]:
        assert f'id="{regiao}"' in corpo


def test_criar_topico_manda_jogo_id():
    """`jogo_id` virou obrigatório: tópico órfão era contado nas
    estatísticas e não aparecia em praça nenhuma. Sem ele, 422."""
    texto = _sem_comentarios((RAIZ / "view/estatico/js/comunidade.js").read_text(encoding="utf-8"))
    assert "/api/v1/topicos" in texto
    assert "jogo_id" in texto


def test_praca_nao_e_renderizada_como_cartao_de_jogo():
    """O cartão de praça não tem pontuacao nem status; passá-lo a
    `cartaoDeJogo` quebra ao ler `status.rotulo`."""
    texto = _sem_comentarios((RAIZ / "view/estatico/js/comunidade.js").read_text(encoding="utf-8"))
    assert "cartaoDeJogo" not in texto
