"""Catálogo: jogo, gênero, plataforma, biblioteca e avaliações."""
from app.extensions import db
from app.models.usuario import agora


class Genero(db.Model):
    __tablename__ = "generos"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(80), unique=True, nullable=False)
    slug = db.Column(db.String(90), unique=True)

    jogos = db.relationship(
        "JogoGenero", backref="genero", cascade="all, delete-orphan"
    )


class Jogo(db.Model):
    __tablename__ = "jogos"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(140), unique=True)
    nome = db.Column(db.String(200), nullable=False)
    #: `nome` normalizado (minúscula, sem acento) para busca portátil.
    #: Derivada: quem escreve `nome` é responsável por atualizá-la, e o
    #: JogoService faz isso no mesmo ponto onde já gera slug e iniciais.
    nome_busca = db.Column(db.String(200), index=True, nullable=False, default="")
    iniciais = db.Column(db.String(4), default="")

    descricao = db.Column(db.Text)
    sobre = db.Column(db.Text)
    merch = db.Column(db.Text)
    classificacao = db.Column(db.String(10))
    desenvolvedora = db.Column(db.String(200))
    publicadora = db.Column(db.String(200))
    data_lancamento = db.Column(db.String(60))
    metacritic = db.Column(db.SmallInteger)

    capa_url = db.Column(db.Text)
    arquivo_capa = db.Column(db.String(255))
    # Duas cores hex. Nunca lista vazia — o Service aplica o fallback.
    capa_gradiente = db.Column(db.JSON, default=None)

    popularidade = db.Column(db.Integer, default=0, nullable=False)
    curtidas = db.Column(db.Integer, default=0, nullable=False)
    descurtidas = db.Column(db.Integer, default=0, nullable=False)
    conquistas = db.Column(db.Integer, default=0, nullable=False)

    tempo_medio = db.Column(db.String(40), default="")
    tempo_speedrun = db.Column(db.String(40), default="")
    tempo_platina = db.Column(db.String(40), default="")

    criado_em = db.Column(db.DateTime, default=agora)
    atualizado_em = db.Column(db.DateTime, default=agora, onupdate=agora)

    generos = db.relationship(
        "JogoGenero", backref="jogo", cascade="all, delete-orphan"
    )
    plataformas = db.relationship(
        "JogoPlataforma", backref="jogo", cascade="all, delete-orphan"
    )
    biblioteca = db.relationship(
        "BibliotecaUsuario", backref="jogo", cascade="all, delete-orphan"
    )
    avaliacoes = db.relationship(
        "Avaliacao", backref="jogo", cascade="all, delete-orphan"
    )
    bugometro = db.relationship(
        "BugometroStatus", backref="jogo", uselist=False, cascade="all, delete-orphan"
    )
    metricas = db.relationship(
        "MetricaBug", backref="jogo", cascade="all, delete-orphan"
    )
    relatos = db.relationship(
        "RelatoBug", backref="jogo", cascade="all, delete-orphan"
    )
    historico = db.relationship(
        "HistoricoBug", backref="jogo", cascade="all, delete-orphan"
    )
    alertas = db.relationship("Alerta", backref="jogo", cascade="all, delete-orphan")
    topicos = db.relationship("Topico", backref="jogo", cascade="all, delete-orphan")


class JogoGenero(db.Model):
    __tablename__ = "jogos_generos"
    __table_args__ = (db.UniqueConstraint("jogo_id", "genero_id"),)

    id = db.Column(db.Integer, primary_key=True)
    jogo_id = db.Column(db.Integer, db.ForeignKey("jogos.id", ondelete="CASCADE"))
    genero_id = db.Column(db.Integer, db.ForeignKey("generos.id", ondelete="CASCADE"))


class Plataforma(db.Model):
    __tablename__ = "plataformas"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), nullable=False)

    jogos = db.relationship(
        "JogoPlataforma", backref="plataforma", cascade="all, delete-orphan"
    )


class JogoPlataforma(db.Model):
    __tablename__ = "jogos_plataformas"

    id = db.Column(db.Integer, primary_key=True)
    jogo_id = db.Column(db.Integer, db.ForeignKey("jogos.id", ondelete="CASCADE"))
    plataforma_id = db.Column(
        db.Integer, db.ForeignKey("plataformas.id", ondelete="CASCADE")
    )


class BibliotecaUsuario(db.Model):
    __tablename__ = "biblioteca_usuario"
    __table_args__ = (db.UniqueConstraint("usuario_id", "jogo_id"),)

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id", ondelete="CASCADE"))
    jogo_id = db.Column(db.Integer, db.ForeignKey("jogos.id", ondelete="CASCADE"))
    favorito = db.Column(db.Boolean, default=False, nullable=False)
    # Substituem os derivados falsos do perfil (spec 3.5).
    minutos_jogados = db.Column(db.Integer, default=0, nullable=False)
    progresso = db.Column(db.SmallInteger, default=0, nullable=False)
    adicionado_em = db.Column(db.DateTime, default=agora)


class Avaliacao(db.Model):
    """Serve como avaliação com nota E como comentário do jogo (nota nula)."""

    __tablename__ = "avaliacoes"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id", ondelete="CASCADE"))
    jogo_id = db.Column(db.Integer, db.ForeignKey("jogos.id", ondelete="CASCADE"))
    nota = db.Column(db.Numeric(2, 1), nullable=True)
    comentario = db.Column(db.Text)
    oculto = db.Column(db.Boolean, default=False, nullable=False)
    criado_em = db.Column(db.DateTime, default=agora)

    curtidas = db.relationship(
        "CurtidaAvaliacao", backref="avaliacao", cascade="all, delete-orphan"
    )


class CurtidaAvaliacao(db.Model):
    __tablename__ = "curtidas_avaliacoes"
    __table_args__ = (db.UniqueConstraint("avaliacao_id", "usuario_id"),)

    id = db.Column(db.Integer, primary_key=True)
    avaliacao_id = db.Column(
        db.Integer, db.ForeignKey("avaliacoes.id", ondelete="CASCADE")
    )
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id", ondelete="CASCADE"))
