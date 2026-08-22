"""Composition root: monta Repository → Service e entrega ao Controller.

Vive fora de app/controllers/ de propósito: é o único lugar autorizado a
conhecer as três camadas ao mesmo tempo.
"""
from types import SimpleNamespace

from app import models as m
from app import schemas as _  # noqa: F401  (garante o pacote carregado)
from app.repositories.base import RepositorioBase
from app.repositories.usuario_repository import RepositorioUsuario
from app.schemas import bugometro as sb
from app.schemas import forum as sf
from app.schemas import jogo as sj
from app.schemas import social as ss
from app.schemas.usuario import UsuarioEntradaSchema, UsuarioSchema
from app.services.auth_service import AuthService
from app.services.base import ServicoBase

#: (atributo, model, schema_saida, schema_entrada, nome_recurso, ordenacao)
CATALOGO = [
    ("jogos", m.Jogo, sj.JogoSchema, sj.JogoEntradaSchema, "Jogo",
     ("nome", "metacritic", "popularidade", "criado_em")),
    ("generos", m.Genero, sj.GeneroSchema, sj.GeneroEntradaSchema, "Gênero",
     ("nome",)),
    ("plataformas", m.Plataforma, sj.PlataformaSchema, sj.PlataformaEntradaSchema,
     "Plataforma", ("nome",)),
    ("biblioteca", m.BibliotecaUsuario, sj.BibliotecaSchema,
     sj.BibliotecaEntradaSchema, "Entrada da biblioteca", ("adicionado_em",)),
    ("avaliacoes", m.Avaliacao, sj.AvaliacaoSchema, sj.AvaliacaoEntradaSchema,
     "Avaliação", ("criado_em", "nota")),
    ("relatos_bug", m.RelatoBug, sb.RelatoBugSchema, sb.RelatoBugEntradaSchema,
     "Relato de bug", ("criado_em", "confirmacoes", "severidade")),
    ("votos_bug", m.VotoBug, sb.VotoBugSchema, sb.VotoBugEntradaSchema,
     "Voto", ("criado_em",)),
    ("alertas", m.Alerta, sb.AlertaSchema, sb.AlertaEntradaSchema, "Alerta",
     ("criado_em", "severidade")),
    ("metricas_bug", m.MetricaBug, sb.MetricaBugSchema, sb.MetricaBugEntradaSchema,
     "Métrica", ("criado_em",)),
    ("historico_bug", m.HistoricoBug, sb.HistoricoBugSchema,
     sb.HistoricoBugEntradaSchema, "Histórico", ("registrado_em",)),
    ("topicos", m.Topico, sf.TopicoSchema, sf.TopicoEntradaSchema, "Tópico",
     ("criado_em", "titulo")),
    ("posts", m.Post, sf.PostSchema, sf.PostEntradaSchema, "Post", ("criado_em",)),
    ("categorias", m.Categoria, sf.CategoriaSchema, sf.CategoriaEntradaSchema,
     "Categoria", ("nome",)),
    ("badges", m.Badge, ss.BadgeSchema, ss.BadgeEntradaSchema, "Badge", ("nome",)),
    ("usuarios_badges", m.UsuarioBadge, ss.UsuarioBadgeSchema,
     ss.UsuarioBadgeEntradaSchema, "Badge do usuário", ("conquistado_em",)),
    ("notificacoes", m.Notificacao, ss.NotificacaoSchema,
     ss.NotificacaoEntradaSchema, "Notificação", ("criado_em",)),
    ("atividades", m.Atividade, ss.AtividadeSchema, ss.AtividadeEntradaSchema,
     "Atividade", ("criado_em",)),
]


def montar_servicos() -> SimpleNamespace:
    repositorio_usuario = RepositorioUsuario()

    servicos = SimpleNamespace(
        auth=AuthService(
            repositorio=repositorio_usuario, schema_saida=UsuarioSchema()
        ),
        usuarios=ServicoBase(
            repositorio=repositorio_usuario,
            schema_saida=UsuarioSchema(),
            schema_entrada=UsuarioEntradaSchema(),
            nome_recurso="Usuário",
        ),
    )
    # O dono de um Usuario é ele mesmo: o campo é 'id', não 'usuario_id'.
    servicos.usuarios.campo_dono = "id"
    servicos.usuarios.campo_autor = None

    for atributo, model, saida, entrada, nome, ordenacao in CATALOGO:
        setattr(
            servicos,
            atributo,
            ServicoBase(
                repositorio=RepositorioBase(model, ordenacao_permitida=ordenacao),
                schema_saida=saida(),
                schema_entrada=entrada(),
                nome_recurso=nome,
            ),
        )

    # Substitui os services genéricos pelos especializados, que carregam
    # as fórmulas do domínio.
    from app.models import Alerta, BugometroStatus, Jogo, RelatoBug, VotoBug
    from app.services.alerta_service import AlertaService
    from app.services.bugometro_service import BugometroService
    from app.services.jogo_service import JogoService

    servicos.jogos = JogoService(
        repositorio=RepositorioBase(
            Jogo, ordenacao_permitida=("nome", "metacritic", "popularidade", "criado_em")
        ),
        schema_saida=sj.JogoSchema(),
        schema_entrada=sj.JogoEntradaSchema(),
        nome_recurso="Jogo",
    )

    servicos.bugometro = BugometroService(
        repositorio=RepositorioBase(
            RelatoBug,
            ordenacao_permitida=("criado_em", "confirmacoes", "severidade"),
        ),
        schema_saida=sb.RelatoBugSchema(),
        schema_entrada=sb.RelatoBugEntradaSchema(),
        nome_recurso="Relato de bug",
        repositorio_status=RepositorioBase(BugometroStatus),
        repositorio_jogos=RepositorioBase(Jogo),
    )
    servicos.relatos_bug = servicos.bugometro

    # Votar também mexe na pontuação: o voto atualiza confirmacoes e
    # dispara o mesmo recálculo.
    from app.services.voto_service import VotoService

    servicos.votos_bug = VotoService(
        repositorio=RepositorioBase(VotoBug, ordenacao_permitida=("criado_em",)),
        schema_saida=sb.VotoBugSchema(),
        schema_entrada=sb.VotoBugEntradaSchema(),
        nome_recurso="Voto",
        servico_bugometro=servicos.bugometro,
        repositorio_relatos=RepositorioBase(RelatoBug),
    )

    servicos.alertas = AlertaService(
        repositorio=RepositorioBase(
            Alerta, ordenacao_permitida=("criado_em", "severidade")
        ),
        schema_saida=sb.AlertaSchema(),
        schema_entrada=sb.AlertaEntradaSchema(),
        nome_recurso="Alerta",
    )

    # Conteúdo moderável: `oculto` some para quem não é admin (spec 4.8).
    for atributo in ("topicos", "posts", "avaliacoes", "relatos_bug"):
        getattr(servicos, atributo).campo_oculto = "oculto"

    # Catálogo e operação: não têm dono, e escrever neles era trabalho do
    # Django admin. Sem `somente_admin`, `campo_dono = None` deixaria
    # qualquer conta recém-registrada apagar o catálogo inteiro.
    for atributo in ("jogos", "generos", "plataformas", "alertas", "categorias",
                     "badges", "metricas_bug", "historico_bug"):
        servico = getattr(servicos, atributo)
        servico.campo_dono = None
        servico.somente_admin = True
        servico.campo_autor = None

    return servicos
