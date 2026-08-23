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


def normalizar_busca(texto: str | None) -> str:
    """Minúscula e sem acento — a forma que a busca compara.

    Feito aqui, e não no banco, porque SQLite não tem `unaccent` e no
    MySQL o resultado dependeria do collation da instalação. Guardar a
    forma normalizada torna a busca igual em qualquer banco.
    """
    import unicodedata

    decomposto = unicodedata.normalize("NFKD", texto or "")
    sem_acento = "".join(c for c in decomposto if not unicodedata.combining(c))
    # Trunca em 200: casefold() EXPANDE alguns caracteres — 'ß' vira
    # 'ss' —, então um `nome` de 200 caracteres pode gerar mais de 200
    # aqui. SQLite aceita em silêncio; MySQL de produção com
    # STRICT_TRANS_TABLES recusa com "Data too long for column
    # 'nome_busca'" — 500 ao cadastrar/renomear e no backfill da
    # migração. `nome_busca` é String(200); o corte acompanha a coluna.
    return sem_acento.casefold().strip()[:200]


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
        dados["nome_busca"] = normalizar_busca(dados["nome"])
        if usuario is not None and self.campo_autor:
            dados[self.campo_autor] = usuario.id
        entidade = self.repositorio.criar(**dados)
        return self.schema_saida.dump(entidade)

    def listar_catalogo(
        self,
        pagina: int = 1,
        por_pagina: int = 20,
        ordenar_por: str | None = None,
        busca: str | None = None,
        genero_slug: str | None = None,
    ):
        """Repassa ao repositório. Existe para que `TelaService` não
        precise conhecer repositório de terceiro — a regra de camadas."""
        return self.repositorio.listar_catalogo(
            pagina=pagina,
            por_pagina=por_pagina,
            ordenar_por=ordenar_por,
            busca=busca,
            genero_slug=genero_slug,
        )

    def atualizar(self, identificador: int, dados_brutos: dict, usuario) -> dict:
        """Renomear um jogo tem que renomear a forma de busca junto.

        Deriva do nome **já persistido**, não do payload cru: assim o
        valor passou pelo schema (um `nome` não textual vira 422 e não
        `TypeError`), e a coluna acaba consistente com o nome qualquer que
        tenha sido o caminho da atualização.
        """
        dados = dict(dados_brutos or {})
        # Retaguarda: o schema já marca `nome_busca` como dump_only, mas
        # depender só disso é o que deixou o campo gravável até aqui.
        dados.pop("nome_busca", None)

        resultado = super().atualizar(identificador, dados, usuario)

        entidade = self.repositorio.obter(identificador)
        esperado = normalizar_busca(entidade.nome)
        if entidade.nome_busca != esperado:
            self.repositorio.atualizar(entidade, nome_busca=esperado)
            resultado = self.schema_saida.dump(entidade)
        return resultado

    @staticmethod
    def montar_card(jogo, favorito: bool, na_biblioteca: bool) -> dict:
        """Shape consumido por seis telas. Um CRUD cru não produz
        iniciais, capa nem status.

        SEM DEFAULT: `favorito`/`na_biblioteca` descrevem o estado do
        usuário logado, não do jogo. Um default `False` transformaria
        esquecer de resolvê-los em resposta errada, em vez de erro —
        foi assim que `/telas/bugometro` mentiu para quem já tinha o
        jogo favoritado (defeito 1 da revisão)."""
        pontuacao = jogo.bugometro.pontuacao if jogo.bugometro else 0
        gradiente = jogo.capa_gradiente or None
        if not gradiente or len(gradiente) < 2:
            gradiente = CAPA_PADRAO

        return {
            # Toda escrita de tela exige `jogo_id`, e a tela só conhece o
            # slug. A listagem do CRUD não filtra por slug — aceita o
            # parâmetro e o ignora — então sem o id aqui não há caminho.
            "id": jogo.id,
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

    SEM_MERCH = "Sem informações de merch para este jogo."
    SEM_DATA = "—"

    def montar_detalhe(
        self,
        jogo,
        comentarios: list[dict],
        bugs: list[dict],
        favorito: bool,
        na_biblioteca: bool,
    ) -> dict:
        """O card canônico mais o que só a tela de detalhe usa.

        `favorito`/`na_biblioteca` chegam resolvidos por quem chama: a
        tela de detalhe é onde o botão de favoritar mais importa, então
        emitir os dois campos corretamente aqui deixou de ser opcional
        (defeito 2 da revisão — antes o valor era descartado com
        `.pop()` por não haver como calculá-lo certo)."""
        detalhe = self.montar_card(jogo, favorito=favorito, na_biblioteca=na_biblioteca)

        detalhe.update(
            {
                # `atualizado_em` é carimbo técnico de escrita da linha,
                # não "quando o jogo foi atualizado" — mostrá-lo aqui
                # diria ao usuário que o jogo recebeu patch toda vez que
                # alguém editou o cadastro. Até existir uma coluna de
                # domínio para isso, usa-se a data de lançamento.
                "ultima_atualizacao": jogo.data_lancamento or self.SEM_DATA,
                "sobre": jogo.sobre or jogo.descricao or "",
                # Inteiro cru: a formatação de milhar é do JS, para
                # unificar com a tela de comunidade, que já formatava lá.
                "curtidas": jogo.curtidas,
                "descurtidas": jogo.descurtidas,
                "conquistas": jogo.conquistas,
                "merch": jogo.merch or self.SEM_MERCH,
                "tempo_para_zerar": {
                    "medio": jogo.tempo_medio or self.SEM_DATA,
                    "speedrun": jogo.tempo_speedrun or self.SEM_DATA,
                    "platina": jogo.tempo_platina or self.SEM_DATA,
                },
                # Lista, igual ao bugômetro. Quem sabe quais relatos
                # contam é o BugometroService — reimplementar a regra
                # aqui faria as duas telas divergirem em silêncio quando
                # um status novo aparecesse.
                "bugs": bugs,
                "comentarios": comentarios,
            }
        )
        return detalhe
