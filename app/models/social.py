"""Badges, notificações e atividades."""
from app.extensions import db
from app.models.usuario import agora


class Badge(db.Model):
    __tablename__ = "badges"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), nullable=False)
    icone_url = db.Column(db.Text)

    usuarios = db.relationship(
        "UsuarioBadge", backref="badge", cascade="all, delete-orphan"
    )


class UsuarioBadge(db.Model):
    __tablename__ = "usuarios_badges"
    __table_args__ = (db.UniqueConstraint("usuario_id", "badge_id"),)

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id", ondelete="CASCADE"))
    badge_id = db.Column(db.Integer, db.ForeignKey("badges.id", ondelete="CASCADE"))
    conquistado_em = db.Column(db.DateTime, default=agora)


class Notificacao(db.Model):
    __tablename__ = "notificacoes"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id", ondelete="CASCADE"))
    mensagem = db.Column(db.Text, nullable=False)
    lida = db.Column(db.Boolean, default=False, nullable=False)
    criado_em = db.Column(db.DateTime, default=agora)


class Atividade(db.Model):
    __tablename__ = "atividades"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id", ondelete="CASCADE"))
    tipo = db.Column(db.String(50))
    referencia_id = db.Column(db.Integer)
    criado_em = db.Column(db.DateTime, default=agora)
