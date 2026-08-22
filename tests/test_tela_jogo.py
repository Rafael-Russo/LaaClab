from pathlib import Path

from test_frontend import _sem_comentarios

RAIZ = Path(__file__).resolve().parents[1]


def test_qualquer_slug_serve_a_mesma_pagina(cliente):
    for slug in ["cyberpunk-2077", "um-slug-qualquer"]:
        assert cliente.get(f"/jogo/{slug}").status_code == 200


def test_js_le_o_slug_da_url():
    """O `data-slug` era injetado pelo template Django e morreu com ele."""
    texto = _sem_comentarios((RAIZ / "view/estatico/js/jogo.js").read_text(encoding="utf-8"))
    assert "location.pathname" in texto
    assert "dataset.slug" not in texto


def test_comentar_e_relatar_mandam_jogo_id():
    texto = _sem_comentarios((RAIZ / "view/estatico/js/jogo.js").read_text(encoding="utf-8"))
    assert "/api/v1/avaliacoes" in texto
    assert "/api/v1/relatos-bug" in texto
    assert "comentario" in texto
    assert "jogo_id" in texto


def test_relatar_bug_titulo_longo_devolve_erros_por_campo_e_js_usa(cliente, app):
    """422 devolve {"erros": {campo: [msg]}}, nunca {"erro": msg}: usar
    só `e.message` aqui sempre caía no genérico "Não foi possível
    completar a operação.", desperdiçando o campo que a API já
    apontou (o bugômetro já faz isto certo). Confirmado contra a API
    real, não só por leitura do JS."""
    from app.extensions import db
    from app.models import Jogo

    entrada = cliente.post(
        "/api/auth/registro",
        json={"nome_usuario": "relator", "email": "relator@l.dev", "senha": "senha123"},
    ).get_json()
    cabecalho = {"Authorization": f"Bearer {entrada['token_acesso']}"}

    jogo = Jogo(nome="Cyberpunk", slug="cyberpunk-item5")
    db.session.add(jogo)
    db.session.commit()

    resposta = cliente.post(
        "/api/v1/relatos-bug",
        json={"jogo_id": jogo.id, "titulo": "x" * 201},  # máximo é 200
        headers=cabecalho,
    )
    corpo = resposta.get_json()
    assert resposta.status_code == 422
    assert "erros" in corpo
    assert "erro" not in corpo

    texto = _sem_comentarios((RAIZ / "view/estatico/js/jogo.js").read_text(encoding="utf-8"))
    inicio = texto.index("construirFormularioDeBug")
    trecho = texto[inicio : inicio + 1500]
    assert "e.erros" in trecho, "jogo.js ainda ignora e.erros e cai sempre no genérico"
