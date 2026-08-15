from pathlib import Path

from flask_migrate import upgrade

from app import create_app
from app.config import TestConfig
from app.extensions import db


def test_diretorio_de_migrations_existe():
    raiz = Path(__file__).resolve().parent.parent
    assert (raiz / "migrations" / "env.py").exists()
    assert (raiz / "migrations" / "versions").is_dir()


def test_env_py_importa_o_agregador_de_models():
    """Sem este import, o autogenerate gera migrations vazias silenciosamente."""
    raiz = Path(__file__).resolve().parent.parent
    conteudo = (raiz / "migrations" / "env.py").read_text(encoding="utf-8")
    assert "import app.models" in conteudo


def test_upgrade_roda_em_um_banco_limpo(tmp_path):
    config = TestConfig()
    config.SQLALCHEMY_DATABASE_URI = f"sqlite:///{tmp_path / 'teste.sqlite3'}"
    aplicacao = create_app(config)
    with aplicacao.app_context():
        upgrade()  # nenhuma migration ainda: precisa passar sem erro
        assert db.engine.url.database.endswith("teste.sqlite3")


def test_batch_mode_esta_ligado():
    """SQLite não faz ALTER TABLE; sem batch, migrations de alteração quebram."""
    from app.extensions import migrate

    assert migrate.alembic_ctx_kwargs.get("render_as_batch") is True
