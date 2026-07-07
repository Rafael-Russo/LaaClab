# P3 — Identificação de bugs funcionais (design)

- **Data:** 2026-07-07
- **Status:** direção aprovada; **R&D com itens em aberto** — a Fase 3b merece um *spike* antes de implementar.
- **Ordem:** implementar após P2. Ver [P1](2026-07-07-p1-catalogo-biblioteca-design.md), [P2](2026-07-07-p2-modularizacao-moderacao-design.md).

## Objetivo

Substituir o `bug_score` **falso** (derivado do appid) por um score **real**
baseado em bugs funcionais identificados por múltiplas fontes de sinal, com o
melhor equilíbrio entre eficiência de identificação e experiência do usuário.

## Decisão: abordagem faseada com fontes de sinal plugáveis

Recomendada por eficiência + UX. O modelo `Bug` nasce agnóstico à origem; cada
fase adiciona uma **fonte** sem retrabalho:

- **Fase 3a — Reports da comunidade (MVP real):** usuários reportam bugs
  estruturados por jogo e votam/confirmam. Dado funcional real e imediato, zero
  risco de ML, engaja a comunidade existente. Já passa a alimentar o `bug_score`.
- **Fase 3b — Scraping + embeddings:** tasks Celery raspam comunidades
  (discussões da Steam, Reddit) → classificam textos com **embeddings** (é bug
  funcional? categoria?) → deduplicam/agrupam → criam/atualizam `Bug`
  (`source=scraped`). Escala cobertura sem instalar nada no cliente.
- **Fase 3c — Agente no PC (opcional/futuro):** coletor local opt-in envia
  telemetria de crash/FPS → agregada por jogo (`source=agent`). Sinal técnico
  mais rico, porém maior esforço e sensível a privacidade. **Só design aqui.**

## Modelo de dados (app `bugs`, criado aqui)

- **`Bug`**: `game` (FK), `title`, `description`, `category`
  (`crash`|`graphics`|`performance`|`progression`|`online`|`other`), `severity`
  (`low`|`medium`|`high`|`critical`), `status`
  (`open`|`confirmed`|`resolved`|`rejected`), `source`
  (`community`|`scraped`|`agent`), `confirmations` (int), `created_at`,
  `updated_at`, moderação (P2: `moderated_by`/`status`).
- **`BugReport`**: report bruto de um usuário (`bug` FK opcional, `game`,
  `author`, `text`, `category`, `created_at`) — vira/anexa a um `Bug`.
- **`BugVote`**: confirmação/voto de usuário em um `Bug` (unique user+bug).
- **`BugSignal`** (3b/3c): evidência bruta de fonte automática (`bug` FK,
  `source`, `payload`/`url`, `score`/similaridade, `created_at`) — rastreia de
  onde veio o sinal.
- **`GameScoreSnapshot`** (compartilhado com P4 Históricos): `game`, `bug_score`,
  `captured_at` — série temporal para o gráfico real.

## Cálculo do `bug_score` (real)

Função de agregação por jogo a partir dos `Bug` ativos: pondera **quantidade**,
**severidade**, **recência** e **confirmações** → 0–100. Substitui
`services.bugometro_metrics`/gráfico sintéticos por dados reais; snapshots
periódicos (Celery Beat) alimentam Históricos (P4). O `_bug_score` falso do
`ingest` (P1) some.

## Pipeline de scraping + embeddings (Fase 3b)

- Tasks Celery: `scrape_source(game, source)` coleta textos recentes;
  `classify_texts` gera embeddings e classifica (bug funcional? categoria?);
  `upsert_scraped_bugs` deduplica por similaridade e cria/atualiza `Bug`+`BugSignal`.
- **Provedor de classificação (decisão de implementação, em aberto):**
  1. **LLM classificador via API (recomendado p/ qualidade):** usar os modelos
     **Claude (Anthropic API)** para classificar/extrair bug + categoria + severidade
     de cada texto (few-shot). Melhor precisão, custo por chamada; abstrair atrás
     de uma interface `Classifier` para trocar provedor.
  2. **Embeddings locais + similaridade:** `sentence-transformers` local +
     classificação por similaridade a exemplos rotulados/protótipos de categoria.
     Sem custo de API, roda no worker; qualidade menor.
  - Abstração `Classifier`/`Embedder` para permitir trocar (1)↔(2) e testar com
    um *fake* determinístico.
- **Conformidade:** respeitar robots/ToS e rate-limits das fontes; guardar
  proveniência (`BugSignal.url`). Itens de compliance ficam listados como
  requisito no plano.

## Agente no PC (Fase 3c — só design)

Coletor opt-in (fora do repo web) que envia eventos anonimizáveis (crash/FPS/
travamento) a um endpoint autenticado; agregação por jogo vira `Bug`/`BugSignal`
`source=agent`. Requer: consentimento explícito, minimização/anonimização de
dados, autenticação por token. **Não implementar em P3**; registrar como fase
futura com um mini-RFC de privacidade.

## Integrações

- **P2:** `Bug`/`BugReport` são moderados pelo grupo *Moderador de Jogos/Bugs*
  (aprovar/confirmar/rejeitar). App `bugs` é um módulo ligável pelo `core`.
- **P1:** reusa Celery/Redis; scraping é mais tasks no mesmo worker.
- **P4:** detalhe do jogo mostra bugs reais; Históricos usa `GameScoreSnapshot`.

## Testes

- Reports/votos: criar report, virar Bug, votar (unique), recomputar score.
- `bug_score`: casos determinísticos da função de agregação.
- Scraping/classificação: `requests` mockado + `Classifier` *fake* determinístico
  (sem rede/sem LLM real nos testes); dedupe por similaridade testado com vetores fixos.
- CI offline (sem chamadas a APIs externas).

## Itens em aberto (resolver antes/na implementação da 3b)

1. Provedor de classificação: Claude API vs embeddings locais (recomendo começar
   com Claude atrás da interface, com fallback local).
2. Fontes de scraping iniciais e compliance (Steam discussions, Reddit API/ToS).
3. Pesos exatos da função de `bug_score`.
4. Escopo/privacidade do agente (3c) — mini-RFC futuro.

> Recomenda-se um **spike** curto na 3b (raspar 1 fonte + classificar N textos)
> para validar qualidade antes do build completo.
