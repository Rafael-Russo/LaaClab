"""Autenticação: registro, login e carga do usuário autenticado.

NÃO conhece JWT. Emitir token é responsabilidade do Controller.
"""
from dataclasses import dataclass

from marshmallow import ValidationError

from app.errors import Conflito, DadosInvalidos, NaoAutorizado
from app.schemas.usuario import LoginSchema, RegistroSchema


@dataclass(frozen=True)
class UsuarioAutenticado:
    """Identidade mínima que os outros Services precisam para autorizar.
    Deliberadamente pobre: id e privilégio, nada mais."""

    id: int
    is_admin: bool


class AuthService:
    def __init__(self, repositorio, schema_saida):
        self.repositorio = repositorio
        self.schema_saida = schema_saida
        self._registro = RegistroSchema()
        self._login = LoginSchema()

    def registrar(self, dados_brutos: dict) -> tuple[dict, int]:
        dados = self._validar(self._registro, dados_brutos)

        if self.repositorio.existe(nome_usuario=dados["nome_usuario"]):
            raise Conflito("nome_usuario já está em uso.")
        if self.repositorio.existe(email=dados["email"]):
            raise Conflito("email já está em uso.")

        senha = dados.pop("senha")
        # O Django criava o perfil por signal; com camadas, é explícito aqui.
        dados["apelido"] = dados.get("apelido") or dados["nome_usuario"]

        usuario = self.repositorio.model(**dados)
        usuario.definir_senha(senha)
        self.repositorio.persistir(usuario)
        return self.schema_saida.dump(usuario), 201

    def autenticar(self, dados_brutos: dict) -> tuple[dict, int]:
        dados = self._validar(self._login, dados_brutos)
        usuario = self.repositorio.buscar_por_identificador(dados["identificador"])

        # Mesma resposta para usuário inexistente e senha errada: não
        # revelar quais contas existem.
        if usuario is None or not usuario.checar_senha(dados["senha"]):
            raise NaoAutorizado("Credenciais inválidas.")

        return self.schema_saida.dump(usuario), 200

    def carregar_autenticado(self, usuario_id: int) -> UsuarioAutenticado:
        usuario = self.repositorio.obter(usuario_id)
        if usuario is None:
            raise NaoAutorizado("Autenticação necessária.")
        return UsuarioAutenticado(id=usuario.id, is_admin=usuario.is_admin)

    def obter_perfil(self, usuario_id: int) -> dict:
        usuario = self.repositorio.obter(usuario_id)
        if usuario is None:
            raise NaoAutorizado("Autenticação necessária.")
        return self.schema_saida.dump(usuario)

    @staticmethod
    def _validar(schema, dados_brutos: dict) -> dict:
        try:
            return schema.load(dados_brutos or {})
        except ValidationError as erro:
            raise DadosInvalidos("Dados inválidos.", erros=erro.messages) from erro
