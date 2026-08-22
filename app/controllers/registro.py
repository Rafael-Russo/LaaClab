"""Tabela de recursos → blueprints. Um lugar só para saber o que a API expõe."""
from app.controllers.crud_factory import criar_controller_crud

#: (prefixo_da_rota, atributo_em_servicos)
RECURSOS = [
    ("jogos", "jogos"),
    ("generos", "generos"),
    ("plataformas", "plataformas"),
    ("usuarios", "usuarios"),
    ("biblioteca", "biblioteca"),
    ("avaliacoes", "avaliacoes"),
    ("relatos-bug", "relatos_bug"),
    ("votos-bug", "votos_bug"),
    ("alertas", "alertas"),
    ("topicos", "topicos"),
    ("posts", "posts"),
    ("categorias", "categorias"),
    ("badges", "badges"),
    ("notificacoes", "notificacoes"),
    ("atividades", "atividades"),
    ("metricas-bug", "metricas_bug"),
    ("historico-bug", "historico_bug"),
    ("bugometro", "bugometro_status"),
]


def registrar_controllers(app, servicos) -> None:
    for prefixo, atributo in RECURSOS:
        app.register_blueprint(
            criar_controller_crud(
                nome=f"crud_{atributo}",
                servico=getattr(servicos, atributo),
                prefixo=prefixo,
                servico_auth=servicos.auth,
                # /api/v1/usuarios: criar usuário é /api/auth/registro.
                sem_criacao=(prefixo == "usuarios"),
                # /api/v1/votos-bug: depois do bloqueio de troca de
                # relato_id, a rota só sabe recusar ou não fazer nada.
                sem_atualizacao=(prefixo == "votos-bug"),
            )
        )
