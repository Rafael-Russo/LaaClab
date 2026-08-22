import re
from pathlib import Path

from test_frontend import _sem_comentarios

RAIZ = Path(__file__).resolve().parents[1]


def test_pagina_tem_as_regioes(cliente):
    corpo = cliente.get("/perfil").get_data(as_text=True)
    for regiao in ["pf-usuario", "pf-recentes"]:
        assert f'id="{regiao}"' in corpo


def test_js_le_o_endpoint_do_perfil():
    texto = _sem_comentarios((RAIZ / "view/estatico/js/perfil.js").read_text(encoding="utf-8"))
    assert "/api/v1/telas/perfil" in texto
    assert "jogo_slug" in texto


def test_pf_jogos_nao_existe_mais_preso_em_carregando(cliente):
    """`pf-jogos` nasceu nesta branch, marcado `Api.carregando()` e
    nunca preenchido nem tratado no erro — 'Jogos recentes' com
    'Carregando…' para sempre. `jogos_recentes` já é renderizado em
    `pf-activity` ('Atividade recente'); o container órfão foi
    removido, igual ao perfil.html legado (título + link, sem grid de
    dados)."""
    js = _sem_comentarios((RAIZ / "view/estatico/js/perfil.js").read_text(encoding="utf-8"))
    corpo = cliente.get("/perfil").get_data(as_text=True)
    assert "pf-jogos" not in js
    assert 'id="pf-jogos"' not in corpo


def test_toda_regiao_marcada_carregando_em_perfil_e_tratada_no_erro():
    """Trava geral do item 4: toda variável passada a
    `Api.carregando()` em perfil.js precisa reaparecer em
    `Api.vazio()`/`Api.erro()` — senão fica presa em 'Carregando…'
    para sempre se o pedido falhar (era exatamente o caso de
    `pf-jogos`, que nem sequer podia falhar: nada nunca o tocava de
    novo)."""
    texto = _sem_comentarios((RAIZ / "view/estatico/js/perfil.js").read_text(encoding="utf-8"))
    alvos = set(re.findall(r"Api\.carregando\(\s*(\w+)", texto))
    assert alvos, "nenhuma chamada a Api.carregando encontrada — teste desatualizado"
    for variavel in alvos:
        assert re.search(rf"Api\.(vazio|erro)\(\s*{re.escape(variavel)}\b", texto), (
            f"{variavel} é marcado carregando() mas nunca aparece em "
            "Api.vazio()/Api.erro() — pode ficar preso para sempre"
        )


def test_pf_usuario_nunca_e_alvo_de_carregando():
    """Achado extra durante a correção do item 4, confirmado por
    execução (jsdom): `Api.carregando(alvo)` faz `replaceChildren()`
    no alvo. `pf-usuario` é o container do cabeçalho inteiro —
    pf-avatar/pf-name/pf-level/pf-xp-bar/pf-xp/pf-bio/pf-achievements/
    pf-friends/pf-days são filhos dele, lidos por id no caminho feliz.
    Chamar carregando() em `pf-usuario` apaga esses filhos do DOM ANTES
    do fetch resolver: `document.getElementById("pf-avatar")` volta
    null depois, e o TypeError jogava TODO carregamento bem-sucedido no
    catch — a página nunca mostrava dado nenhum, só "Não foi possível
    carregar o perfil.", mesmo com a API respondendo 200."""
    texto = _sem_comentarios((RAIZ / "view/estatico/js/perfil.js").read_text(encoding="utf-8"))
    assert 'Api.carregando("pf-usuario"' not in texto
    assert "Api.carregando(alvo," not in texto
    assert "Api.carregando(alvo)" not in texto
