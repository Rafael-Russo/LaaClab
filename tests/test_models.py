import pytest
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import BibliotecaUsuario, Jogo, RelatoBug, Usuario, VotoBug


def _usuario(nome="gamer", email="gamer@laaclab.dev"):
    u = Usuario(nome_usuario=nome, email=email)
    u.definir_senha("senha123")
    return u


def test_senha_e_hasheada_e_verificavel(sessao):
    u = _usuario()
    assert u.senha_hash != "senha123"
    assert u.checar_senha("senha123") is True
    assert u.checar_senha("errada") is False


def test_usuario_tem_defaults_de_progressao(sessao):
    u = _usuario()
    sessao.add(u)
    sessao.commit()
    assert u.nivel == 1
    assert u.xp == 0
    assert u.xp_max == 2000
    assert u.cor_avatar == "#6b7cff"
    assert u.is_admin is False


def test_nome_usuario_e_unico(sessao):
    sessao.add(_usuario())
    sessao.commit()
    sessao.add(_usuario(email="outro@laaclab.dev"))
    with pytest.raises(IntegrityError):
        sessao.commit()


def test_biblioteca_e_unica_por_usuario_e_jogo(sessao):
    u = _usuario()
    j = Jogo(nome="Hollow Knight", slug="hollow-knight")
    sessao.add_all([u, j])
    sessao.commit()

    sessao.add(BibliotecaUsuario(usuario_id=u.id, jogo_id=j.id))
    sessao.commit()

    sessao.add(BibliotecaUsuario(usuario_id=u.id, jogo_id=j.id))
    with pytest.raises(IntegrityError):
        sessao.commit()


def test_biblioteca_tem_progresso_e_minutos_jogados(sessao):
    u = _usuario()
    j = Jogo(nome="Celeste", slug="celeste")
    sessao.add_all([u, j])
    sessao.commit()
    entrada = BibliotecaUsuario(usuario_id=u.id, jogo_id=j.id)
    sessao.add(entrada)
    sessao.commit()
    assert entrada.minutos_jogados == 0
    assert entrada.progresso == 0
    assert entrada.favorito is False


def test_voto_e_unico_por_relato_e_usuario(sessao):
    u = _usuario()
    j = Jogo(nome="Cuphead", slug="cuphead")
    sessao.add_all([u, j])
    sessao.commit()
    relato = RelatoBug(jogo_id=j.id, titulo="Crash no boss", usuario_id=u.id)
    sessao.add(relato)
    sessao.commit()

    sessao.add(VotoBug(relato_id=relato.id, usuario_id=u.id))
    sessao.commit()

    sessao.add(VotoBug(relato_id=relato.id, usuario_id=u.id))
    with pytest.raises(IntegrityError):
        sessao.commit()


def test_apagar_jogo_cascateia_pelo_orm(sessao):
    j = Jogo(nome="Hades", slug="hades")
    sessao.add(j)
    sessao.commit()
    sessao.add(RelatoBug(jogo_id=j.id, titulo="Bug de áudio"))
    sessao.commit()

    sessao.delete(j)
    sessao.commit()
    assert sessao.execute(db.select(RelatoBug)).scalars().all() == []


def test_relato_nasce_aberto_sem_confirmacoes(sessao):
    j = Jogo(nome="Dead Cells", slug="dead-cells")
    sessao.add(j)
    sessao.commit()
    r = RelatoBug(jogo_id=j.id, titulo="Textura sumindo")
    sessao.add(r)
    sessao.commit()
    assert r.status == "aberto"
    assert r.confirmacoes == 0
    assert r.oculto is False
