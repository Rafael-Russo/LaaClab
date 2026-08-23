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

    def obter_entidade(self, usuario_id: int):
        from app.errors import NaoAutorizado

        usuario = self.repositorio.obter(usuario_id)
        if usuario is None:
            raise NaoAutorizado("Autenticação necessária.")
        return usuario

    def trocar_senha(self, usuario_id: int, dados_brutos: dict) -> None:
        """Troca a senha e incrementa `versao_sessao`, para derrubar
        tokens antigos.

        Recebe o id e carrega a entidade: `UsuarioAutenticado` é um
        dataclass congelado com id e privilégio, sem os métodos de senha.

        Quem revoga é `versao_sessao` (comparação por igualdade em
        `app/__init__.py`), não `senha_alterada_em`. Relógio não serve
        para isso: o `iat` do JWT é inteiro em segundos, e o token emitido
        por esta própria troca nasce no mesmo segundo da marca — nenhuma
        comparação de instantes separa "antes" de "depois" nesse empate.
        `senha_alterada_em` continua sendo gravado, mas só como registro
        de quando a senha mudou (ex.: tela de Configuração).
        """
        from datetime import datetime, timezone

        usuario = self.repositorio.obter(usuario_id)
        if usuario is None:
            raise NaoAutorizado("Autenticação necessária.")

        dados = dados_brutos or {}
        atual = dados.get("senha_atual") or ""
        nova = dados.get("senha_nova") or ""

        erros = {}
        if not usuario.checar_senha(atual):
            erros["senha_atual"] = ["Senha atual incorreta."]
        if not 8 <= len(nova) <= 128:
            erros["senha_nova"] = ["A senha precisa ter de 8 a 128 caracteres."]
        if erros:
            raise DadosInvalidos("Dados inválidos.", erros=erros)

        usuario.definir_senha(nova)
        usuario.senha_alterada_em = datetime.now(timezone.utc).replace(microsecond=0)
        usuario.versao_sessao = (usuario.versao_sessao or 0) + 1
        self.repositorio.persistir(usuario)

    @staticmethod
    def _validar(schema, dados_brutos: dict) -> dict:
        try:
            return schema.load(dados_brutos or {})
        except ValidationError as erro:
            raise DadosInvalidos("Dados inválidos.", erros=erro.messages) from erro
