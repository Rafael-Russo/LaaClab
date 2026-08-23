"""Usuário e progressão."""
from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


def agora() -> datetime:
    """Timestamp em UTC. Substitui datetime.utcnow, deprecado no 3.12."""
    return datetime.now(timezone.utc)


class Usuario(db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nome_usuario = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    senha_hash = db.Column(db.String(255), nullable=False)

    apelido = db.Column(db.String(50), default="")
    idade = db.Column(db.Integer)
    avatar_url = db.Column(db.Text)
    bio = db.Column(db.String(280), default="")

    nivel = db.Column(db.Integer, default=1, nullable=False)
    xp = db.Column(db.Integer, default=0, nullable=False)
    xp_max = db.Column(db.Integer, default=2000, nullable=False)
    cor_avatar = db.Column(db.String(9), default="#6b7cff", nullable=False)
    conquistas = db.Column(db.Integer, default=0, nullable=False)
    amigos = db.Column(db.Integer, default=0, nullable=False)
    dias_ativo = db.Column(db.Integer, default=0, nullable=False)

    # Substitui o framework de permissões do Django (spec 4.8).
    is_admin = db.Column(db.Boolean, default=False, nullable=False)

    criado_em = db.Column(db.DateTime, default=agora)

    #: Instante da última troca de senha, truncado ao segundo. Não é mais
    #: o critério de revogação (ver `versao_sessao`); é só o registro de
    #: QUANDO a senha mudou, para a tela de Configuração exibir.
    senha_alterada_em = db.Column(db.DateTime, nullable=True)

    #: Incrementa a cada troca de senha. É ESTE campo que decide se um
    #: token vale, não `senha_alterada_em`: o `iat` do JWT é inteiro em
    #: segundos, então o token emitido pela própria troca cai no MESMO
    #: segundo da marca — comparar relógio ou deixa o token velho vivo
    #: (`<`) ou mata o novo (`<=`), e nenhum ajuste constante resolve.
    versao_sessao = db.Column(db.Integer, nullable=False, default=0, server_default="0")

    biblioteca = db.relationship(
        "BibliotecaUsuario", backref="usuario", cascade="all, delete-orphan"
    )
    avaliacoes = db.relationship(
        "Avaliacao", backref="usuario", cascade="all, delete-orphan"
    )
    curtidas = db.relationship(
        "CurtidaAvaliacao", backref="usuario", cascade="all, delete-orphan"
    )
    topicos = db.relationship(
        "Topico", backref="usuario", cascade="all, delete-orphan"
    )
    posts = db.relationship("Post", backref="usuario", cascade="all, delete-orphan")
    votos = db.relationship("VotoBug", backref="usuario", cascade="all, delete-orphan")
    badges = db.relationship(
        "UsuarioBadge", backref="usuario", cascade="all, delete-orphan"
    )
    notificacoes = db.relationship(
        "Notificacao", backref="usuario", cascade="all, delete-orphan"
    )
    atividades = db.relationship(
        "Atividade", backref="usuario", cascade="all, delete-orphan"
    )

    def definir_senha(self, senha: str) -> None:
        self.senha_hash = generate_password_hash(senha)

    def checar_senha(self, senha: str) -> bool:
        return check_password_hash(self.senha_hash, senha)
