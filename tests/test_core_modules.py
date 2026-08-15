from app.core.models import MODULE_CANDIDATES, Module, module_enabled
from app.extensions import db


def test_modulo_desconhecido_conta_como_ligado(app):
    assert module_enabled("inexistente") is True


def test_modulo_registrado_e_ligado(app):
    db.session.add(Module(key="community", name="Comunidade", enabled=True))
    db.session.commit()
    assert module_enabled("community") is True


def test_modulo_desligado(app):
    db.session.add(Module(key="community", name="Comunidade", enabled=False))
    db.session.commit()
    assert module_enabled("community") is False


def test_key_e_unica(app):
    import pytest
    from sqlalchemy.exc import IntegrityError

    db.session.add(Module(key="catalog", name="Catálogo"))
    db.session.commit()
    db.session.add(Module(key="catalog", name="Outro"))
    with pytest.raises(IntegrityError):
        db.session.commit()


def test_candidatos_sao_os_modulos_com_link_na_nav(app):
    assert MODULE_CANDIDATES == {"catalog", "community", "alerts"}


def test_context_processor_expoe_os_visiveis(app):
    db.session.add(Module(key="alerts", name="Alertas", enabled=False))
    db.session.commit()
    with app.test_request_context("/"):
        contexto = {}
        for processor in app.template_context_processors[None]:
            contexto.update(processor())
    assert contexto["visible_modules"] == {"catalog", "community"}


def test_create_all_cria_todas_as_tabelas(app):
    """Guarda contra a dependência de ordem de import no conftest.

    `db.create_all()` só cria tabela de model já importado. O conftest importa
    `app.models` justamente para registrar todos antes; se esse import sumir,
    rodar um arquivo de teste isolado passa a criar um schema incompleto.
    """
    from sqlalchemy import inspect

    tabelas = set(inspect(db.engine).get_table_names())
    assert {"user", "role", "user_roles", "user_profile", "module"} <= tabelas
