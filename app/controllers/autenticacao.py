"""Ponte entre o JWT e a identidade que os Services consomem."""
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from app.errors import NaoAutorizado


def obter_usuario_atual(servico_auth):
    """Lê o token e devolve UsuarioAutenticado. Levanta 401 se não houver."""
    verify_jwt_in_request()
    identidade = get_jwt_identity()
    if identidade is None:
        raise NaoAutorizado("Autenticação necessária.")
    return servico_auth.carregar_autenticado(int(identidade))


def obter_usuario_opcional(servico_auth):
    """Mesma coisa, mas devolve ``None`` em vez de recusar.

    Usado nas rotas de LEITURA, que são públicas: sem isso o Service não
    teria como saber se quem lê é administrador, e conteúdo moderado
    (`oculto`) apareceria para todo mundo ou para ninguém.
    """
    verify_jwt_in_request(optional=True)
    identidade = get_jwt_identity()
    if identidade is None:
        return None
    try:
        return servico_auth.carregar_autenticado(int(identidade))
    except NaoAutorizado:
        return None
