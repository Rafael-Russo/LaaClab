"""Testes estruturais das telas de login e registro.

Não abrem navegador: verificam que os campos existem no HTML servido e
que o JS fala com os endpoints certos, guarda a sessão e honra o
`?destino=` e o formato de erro de campo que a API devolve em 422.
"""

from pathlib import Path

from test_frontend import _sem_comentarios

RAIZ = Path(__file__).resolve().parents[1]


def test_paginas_tem_os_campos(cliente):
    login = cliente.get("/login").get_data(as_text=True)
    assert 'name="identificador"' in login
    assert 'name="senha"' in login

    registro = cliente.get("/registro").get_data(as_text=True)
    for campo in ["nome_usuario", "email", "senha"]:
        assert f'name="{campo}"' in registro


def test_login_guarda_os_dois_tokens_e_honra_o_destino():
    texto = _sem_comentarios((RAIZ / "view/estatico/js/login.js").read_text(encoding="utf-8"))
    assert "/api/auth/login" in texto
    assert "guardarSessao" in texto
    assert "destino" in texto


def test_registro_entra_direto_sem_passar_pelo_login():
    """O registro devolve token_acesso e token_renovacao: mandar a
    pessoa para o login depois de criar a conta a faz digitar a senha
    que ela acabou de escolher."""
    texto = _sem_comentarios((RAIZ / "view/estatico/js/registro.js").read_text(encoding="utf-8"))
    assert "/api/auth/registro" in texto
    assert "guardarSessao" in texto
    assert "/api/auth/login" not in texto


def test_erro_de_campo_aparece_no_campo():
    """422 devolve {"erros": {campo: [msg]}}; jogar tudo num alerta
    genérico desperdiça a informação que a API já deu."""
    texto = _sem_comentarios((RAIZ / "view/estatico/js/registro.js").read_text(encoding="utf-8"))
    assert ".erros" in texto


def test_login_e_registro_nao_autenticam_a_chamada():
    """`autenticar: false` é essencial: sem ele, um token velho e
    inválido sobrando no localStorage tomaria 401 e Api.pedir
    redirecionaria o login para o login."""
    login = _sem_comentarios((RAIZ / "view/estatico/js/login.js").read_text(encoding="utf-8"))
    registro = _sem_comentarios((RAIZ / "view/estatico/js/registro.js").read_text(encoding="utf-8"))
    assert "autenticar: false" in login or "autenticar:false" in login
    assert "autenticar: false" in registro or "autenticar:false" in registro
