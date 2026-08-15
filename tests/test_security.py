import pytest
from flask import jsonify, request
from werkzeug.middleware.proxy_fix import ProxyFix

from app import create_app
from app.config import ProdConfig, TestConfig
from app.security import _hostname


@pytest.fixture
def client_com_hosts():
    config = TestConfig()
    config.ALLOWED_HOSTS = ["laaclab.example", "localhost"]
    return create_app(config).test_client()


def test_host_permitido_passa(client_com_hosts):
    resposta = client_com_hosts.get("/healthz", headers={"Host": "laaclab.example"})
    assert resposta.status_code == 200


def test_host_com_porta_e_comparado_sem_a_porta(client_com_hosts):
    resposta = client_com_hosts.get("/healthz", headers={"Host": "laaclab.example:8000"})
    assert resposta.status_code == 200


def test_host_desconhecido_e_rejeitado(client_com_hosts):
    resposta = client_com_hosts.get("/healthz", headers={"Host": "atacante.example"})
    assert resposta.status_code == 400


def test_host_com_sufixo_apos_dois_pontos_e_rejeitado(client_com_hosts):
    """Host header injection: um host permitido seguido de ``:destino`` não
    pode passar pela allowlist enquanto ``request.host`` continua envenenado
    para quem monta URLs absolutas depois (ex.: link de reset de senha)."""
    resposta = client_com_hosts.get(
        "/healthz", headers={"Host": "laaclab.example:evil.example"}
    )
    assert resposta.status_code == 400


def test_host_com_dois_dois_pontos_e_rejeitado(client_com_hosts):
    """Host malformado (mais de um ``:``) precisa ser rejeitado, não
    remendado por um fatiamento que só olha o primeiro ou o último ``:``."""
    resposta = client_com_hosts.get(
        "/healthz", headers={"Host": "laaclab.example:8000:evil"}
    )
    assert resposta.status_code == 400


def test_host_e_comparado_sem_diferenciar_maiusculas(client_com_hosts):
    """Nomes de domínio não diferenciam maiúsculas de minúsculas."""
    resposta = client_com_hosts.get("/healthz", headers={"Host": "LaaCLab.Example"})
    assert resposta.status_code == 200


def test_host_ipv6_com_porta_e_aceito():
    """Literal IPv6 entre colchetes precisa ser reconhecido como um único
    host, com a porta reconhecida e descartada separadamente — fatiar no
    ``:`` quebraria isso, já que o próprio literal é cheio de ``:``."""
    config = TestConfig()
    config.ALLOWED_HOSTS = ["[::1]"]
    cliente = create_app(config).test_client()
    resposta = cliente.get("/healthz", headers={"Host": "[::1]:8000"})
    assert resposta.status_code == 200


def test_lista_vazia_desliga_a_checagem(client):
    """TestConfig usa ALLOWED_HOSTS=[]; qualquer host passa."""
    resposta = client.get("/healthz", headers={"Host": "qualquer.example"})
    assert resposta.status_code == 200


def test_host_com_newline_final_e_rejeitado():
    """``$`` (ao contrário de ``\\Z``) casa antes de um ``\\n`` final, então
    ``"laaclab.example:8000\\n"`` resolveria para o hostname válido em vez de
    ser rejeitado como malformado."""
    assert _hostname("laaclab.example:8000\n") is None


def test_checagem_de_host_roda_antes_do_csrf():
    """A checagem de Host precisa ser o primeiro before_request: o CSRFProtect
    monta o referrer esperado a partir de ``request.host`` dentro do próprio
    handler, então rodar depois usaria um Host que a allowlist ainda não
    validou."""
    aplicacao = create_app(TestConfig())
    nomes = [f.__qualname__ for f in aplicacao.before_request_funcs[None]]
    assert nomes.index("register_host_check.<locals>._checar_host") < nomes.index(
        "CSRFProtect.init_app.<locals>.csrf_protect"
    )


def test_proxy_fix_embrulha_quando_trusted_proxy_ligado(monkeypatch):
    """Fora de debug/testing o WhiteNoise embrulha por cima (fix 2 pede
    explicitamente que ele sobre por último): o ProxyFix fica um nível abaixo,
    mais perto do Flask, guardado em ``WhiteNoise.application``."""
    monkeypatch.setenv("SECRET_KEY", "chave-real")
    monkeypatch.setenv("ALLOWED_HOSTS", "localhost")
    monkeypatch.setenv("TRUSTED_PROXY", "1")
    aplicacao = create_app(ProdConfig())
    assert isinstance(aplicacao.wsgi_app.application, ProxyFix)


def test_proxy_fix_nao_embrulha_quando_trusted_proxy_desligado(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "chave-real")
    monkeypatch.setenv("ALLOWED_HOSTS", "localhost")
    monkeypatch.setenv("TRUSTED_PROXY", "0")
    aplicacao = create_app(ProdConfig())
    assert not isinstance(aplicacao.wsgi_app.application, ProxyFix)


# ``ProdConfig.PREFERRED_URL_SCHEME = "https"``. O test client do Flask usa
# essa config como esquema default ao montar o environ de uma requisição sem
# esquema explícito — então, sem forçar ``base_url="http://..."``, toda
# chamada já chegaria "segura" mesmo com TRUSTED_PROXY desligado e nenhum
# cabeçalho X-Forwarded-Proto, mascarando exatamente o que estes testes
# querem provar.
_BASE_URL_HTTP = "http://localhost"


def test_x_forwarded_proto_torna_a_requisicao_segura_via_proxy(monkeypatch):
    """Sem consumir X-Forwarded-Proto, request.is_secure fica sempre falso
    atrás do nginx — o que desativa o WTF_CSRF_SSL_STRICT e faz
    url_for(_external=True) gerar links http://."""
    monkeypatch.setenv("SECRET_KEY", "chave-real")
    monkeypatch.setenv("ALLOWED_HOSTS", "localhost")
    monkeypatch.setenv("TRUSTED_PROXY", "1")
    monkeypatch.setenv("SSL_REDIRECT", "0")
    aplicacao = create_app(ProdConfig())

    @aplicacao.get("/dbg-secure")
    def _dbg_secure():
        return jsonify({"secure": request.is_secure})

    cliente = aplicacao.test_client()

    sem_proxy = cliente.get("/dbg-secure", base_url=_BASE_URL_HTTP)
    assert sem_proxy.get_json() == {"secure": False}

    com_proxy = cliente.get(
        "/dbg-secure", base_url=_BASE_URL_HTTP, headers={"X-Forwarded-Proto": "https"}
    )
    assert com_proxy.get_json() == {"secure": True}


def test_ssl_redirect_gera_301_para_https(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "chave-real")
    monkeypatch.setenv("ALLOWED_HOSTS", "localhost")
    monkeypatch.setenv("TRUSTED_PROXY", "0")  # sem proxy: is_secure nunca fica true
    aplicacao = create_app(ProdConfig())
    cliente = aplicacao.test_client()
    resposta = cliente.get("/healthz", base_url=_BASE_URL_HTTP)
    assert resposta.status_code == 301
    assert resposta.headers["Location"].startswith("https://")


def test_hsts_aparece_so_em_resposta_segura(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "chave-real")
    monkeypatch.setenv("ALLOWED_HOSTS", "localhost")
    monkeypatch.setenv("TRUSTED_PROXY", "1")
    monkeypatch.setenv("SSL_REDIRECT", "0")  # isola o teste do redirect
    aplicacao = create_app(ProdConfig())
    cliente = aplicacao.test_client()

    segura = cliente.get(
        "/healthz", base_url=_BASE_URL_HTTP, headers={"X-Forwarded-Proto": "https"}
    )
    assert "Strict-Transport-Security" in segura.headers

    insegura = cliente.get("/healthz", base_url=_BASE_URL_HTTP)
    assert "Strict-Transport-Security" not in insegura.headers
