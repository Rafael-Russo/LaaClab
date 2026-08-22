"""Tabela de recursos → blueprints. Um lugar só para saber o que a API expõe."""
from app.controllers.crud_factory import criar_controller_crud

#: (prefixo_da_rota, atributo_em_servicos, grava_autor)
RECURSOS = [
    ("jogos", "jogos", False),
    ("generos", "generos", False),
    ("plataformas", "plataformas", False),
    ("usuarios", "usuarios", False),
    ("biblioteca", "biblioteca", True),
    ("avaliacoes", "avaliacoes", True),
    ("relatos-bug", "relatos_bug", True),
    ("votos-bug", "votos_bug", True),
    ("alertas", "alertas", False),
    ("topicos", "topicos", True),
    ("posts", "posts", True),
    ("categorias", "categorias", False),
    ("badges", "badges", False),
    ("usuarios-badges", "usuarios_badges", True),
    ("notificacoes", "notificacoes", True),
    ("atividades", "atividades", True),
    ("metricas-bug", "metricas_bug", False),
    ("historico-bug", "historico_bug", False),
]


def registrar_controllers(app, servicos) -> None:
    for prefixo, atributo, grava_autor in RECURSOS:
        app.register_blueprint(
            criar_controller_crud(
                nome=f"crud_{atributo}",
                servico=getattr(servicos, atributo),
                prefixo=prefixo,
                servico_auth=servicos.auth,
                grava_autor=grava_autor,
            )
        )
