"""Bugômetro: status, métricas, relatos, votos, histórico e alertas."""
from app.extensions import db
from app.models.usuario import agora

SEVERIDADES = ("baixa", "media", "alta", "critica")
STATUS_RELATO = ("aberto", "confirmado", "resolvido", "rejeitado")
CATEGORIAS_BUG = ("crash", "graficos", "progressao", "desempenho", "online", "outro")
SEVERIDADES_ALERTA = ("critica", "instavel", "atualizacao")


class BugometroStatus(db.Model):
    __tablename__ = "bugometro_status"

    id = db.Column(db.Integer, primary_key=True)
    jogo_id = db.Column(
        db.Integer, db.ForeignKey("jogos.id", ondelete="CASCADE"), unique=True
    )
    pontuacao = db.Column(db.SmallInteger, default=0, nullable=False)
    status = db.Column(db.String(20), default="stable", nullable=False)
    atualizado_em = db.Column(db.DateTime, default=agora, onupdate=agora)


class MetricaBug(db.Model):
    __tablename__ = "metricas_bug"

    id = db.Column(db.Integer, primary_key=True)
    jogo_id = db.Column(db.Integer, db.ForeignKey("jogos.id", ondelete="CASCADE"))
    tipo = db.Column(db.String(20))
    severidade = db.Column(db.String(20))
    porcentagem = db.Column(db.Integer)
    criado_em = db.Column(db.DateTime, default=agora)


class RelatoBug(db.Model):
    """Colapsa Bug + BugReport do Django (spec 3.4)."""

    __tablename__ = "relatos_bug"

    id = db.Column(db.Integer, primary_key=True)
    jogo_id = db.Column(db.Integer, db.ForeignKey("jogos.id", ondelete="CASCADE"))
    usuario_id = db.Column(
        db.Integer, db.ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True
    )
    titulo = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text)
    categoria = db.Column(db.String(20), default="outro", nullable=False)
    severidade = db.Column(db.String(20), default="media", nullable=False)
    status = db.Column(db.String(20), default="aberto", nullable=False)
    origem = db.Column(db.String(50), default="comunidade")
    confirmacoes = db.Column(db.Integer, default=0, nullable=False)
    oculto = db.Column(db.Boolean, default=False, nullable=False)
    criado_em = db.Column(db.DateTime, default=agora)

    votos = db.relationship("VotoBug", backref="relato", cascade="all, delete-orphan")


class VotoBug(db.Model):
    __tablename__ = "votos_bug"
    __table_args__ = (db.UniqueConstraint("relato_id", "usuario_id"),)

    id = db.Column(db.Integer, primary_key=True)
    relato_id = db.Column(db.Integer, db.ForeignKey("relatos_bug.id", ondelete="CASCADE"))
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id", ondelete="CASCADE"))
    criado_em = db.Column(db.DateTime, default=agora)


class HistoricoBug(db.Model):
    __tablename__ = "historico_bug"

    id = db.Column(db.Integer, primary_key=True)
    jogo_id = db.Column(db.Integer, db.ForeignKey("jogos.id", ondelete="CASCADE"))
    quantidade_crash = db.Column(db.Integer, default=0)
    quantidade_bug = db.Column(db.Integer, default=0)
    quantidade_fps_drop = db.Column(db.Integer, default=0)
    quantidade_stutter = db.Column(db.Integer, default=0)
    registrado_em = db.Column(db.DateTime, default=agora)


class Alerta(db.Model):
    """Tabela nova — a tela de Alertas não existia no domínio antigo."""

    __tablename__ = "alertas"

    id = db.Column(db.Integer, primary_key=True)
    jogo_id = db.Column(db.Integer, db.ForeignKey("jogos.id", ondelete="CASCADE"))
    severidade = db.Column(db.String(20), nullable=False)
    texto = db.Column(db.Text, nullable=False)
    criado_em = db.Column(db.DateTime, default=agora)
