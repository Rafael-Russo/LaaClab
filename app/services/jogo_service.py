"""Regras do catálogo: slug, iniciais, classificação e card canônico."""
import re
import unicodedata

from app.services.base import ServicoBase

#: Gradiente aplicado quando o jogo não tem capa. NUNCA devolver lista
#: vazia: em JS `[] || padrao` resolve para `[]`, e o gradiente quebra.
CAPA_PADRAO = ["#2b2d47", "#14152b"]

TETO_SLUG = 140


def gerar_slug(nome: str) -> str:
    """slugify em ASCII, com teto de 140 — igual ao Django."""
    sem_acento = (
        unicodedata.normalize("NFKD", nome or "")
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    limpo = re.sub(r"[^\w\s-]", "", sem_acento).strip().lower()
    return re.sub(r"[-\s]+", "-", limpo)[:TETO_SLUG].strip("-")


def gerar_iniciais(nome: str) -> str:
    """Primeira letra das DUAS primeiras palavras, em maiúsculas.

    Atenção: é regra diferente das iniciais de PESSOA, que no front são os
    dois primeiros caracteres do nome. São coisas distintas de propósito.
    """
    palavras = [p for p in (nome or "").split() if p]
    if not palavras:
        return ""
    return "".join(p[0] for p in palavras[:2]).upper()


def status_para(pontuacao: int) -> dict:
    """Limiares 65 e 40. O rótulo é pt-BR; o nível vira classe CSS."""
    if pontuacao >= 65:
        return {"rotulo": "Crítico", "nivel": "critical"}
    if pontuacao >= 40:
        return {"rotulo": "Instável", "nivel": "warning"}
    return {"rotulo": "Estável", "nivel": "stable"}


class JogoService(ServicoBase):
    campo_dono = None

    def criar(self, dados_brutos: dict, usuario=None) -> dict:
        """Gera slug e iniciais antes de gravar.

        A autorização continua sendo a do `ServicoBase`: reimplementá-la
        aqui foi exatamente como a checagem de privilégio escapou uma vez
        para o Controller.
        """
        self._autorizar_criacao(usuario)
        dados = self._validar(dados_brutos)
        dados["slug"] = dados.get("slug") or gerar_slug(dados["nome"])
        dados["iniciais"] = dados.get("iniciais") or gerar_iniciais(dados["nome"])
        if usuario is not None and self.campo_autor:
            dados[self.campo_autor] = usuario.id
        entidade = self.repositorio.criar(**dados)
        return self.schema_saida.dump(entidade)

    @staticmethod
    def montar_card(jogo, favorito: bool = False, na_biblioteca: bool = False) -> dict:
        """Shape consumido por seis telas. Um CRUD cru não produz
        iniciais, capa nem status."""
        pontuacao = jogo.bugometro.pontuacao if jogo.bugometro else 0
        gradiente = jogo.capa_gradiente or None
        if not gradiente or len(gradiente) < 2:
            gradiente = CAPA_PADRAO

        return {
            "slug": jogo.slug or "",
            "nome": jogo.nome,
            "pontuacao": pontuacao,
            "iniciais": jogo.iniciais or gerar_iniciais(jogo.nome),
            "capa": list(gradiente),
            "imagem_capa": jogo.capa_url or "",
            "arquivo_capa": jogo.arquivo_capa or "",
            "favorito": favorito,
            "na_biblioteca": na_biblioteca,
            "status": status_para(pontuacao),
        }

    def destaques(self, limite: int = 3) -> list:
        """Jogos de maior metacritic; se nenhum tiver nota, os primeiros
        por nome. Não existe tabela de banners."""
        com_nota = self.repositorio.listar(
            pagina=1, por_pagina=limite, ordenar_por="-metacritic"
        ).itens
        com_nota = [j for j in com_nota if j.metacritic is not None]
        if com_nota:
            return com_nota
        return self.repositorio.listar(
            pagina=1, por_pagina=limite, ordenar_por="nome"
        ).itens

    def buscar_por_slug(self, slug: str):
        from app.errors import NaoEncontrado

        pagina = self.repositorio.listar(
            pagina=1, por_pagina=1, filtros={"slug": slug}
        )
        if not pagina.itens:
            raise NaoEncontrado("Jogo não encontrado.")
        return pagina.itens[0]
