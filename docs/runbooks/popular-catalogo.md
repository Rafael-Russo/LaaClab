# Runbook — Popular o catálogo em massa (Steam)

Procedimento **manual** para carregar 2k–5k jogos reais da Steam no banco. A
ingestão é assíncrona (Celery + Redis) e **resumível**. O CI e os testes NÃO
usam este processo — eles rodam offline com o seed pequeno (`manage.py seed`).

> Requer a implementação do P1 (Celery/tasks/comandos). Antes disso, use
> `manage.py seed` para dados de demonstração.

## Pré-requisitos

- Stack de dev de pé com **Redis** e **worker** Celery.
- Espaço em disco para as capas (~200–500 MB em `media/covers/`).
- Acesso à internet (SteamSpy + Steam store API, ambos sem chave).

## Com Docker (recomendado)

```bash
# 1. Sobe banco, broker, worker e web
docker compose up -d db redis worker web

# 2. Carga inicial: puxa o ranking do SteamSpy e enfileira os detalhes.
#    --pages 5 ≈ 5.000 jogos (cada página do SteamSpy ~1.000, 1 req/min).
docker compose exec web python manage.py ingest --pages 5

# 3. Acompanha o progresso do worker
docker compose logs -f worker

# 4. Confere a contagem por status (pending/fetching/done/failed)
docker compose exec web python manage.py ingest_status

# 5. Se o processo cair no meio, retoma só o que falta (não repuxa o ranking):
docker compose exec web python manage.py ingest --resume
```

A ingestão completa leva ~50–125 min (rate-limit da Steam ~40 req/min). Pode
fechar o terminal — o worker continua. Use `ingest_status` para checar.

## Local (sem Docker)

```bash
# Terminal 1 — Redis (ex.: via docker) e worker
docker run -p 6379:6379 -d redis:7
celery -A config worker -l info

# Terminal 2 — dispara a ingestão
export CELERY_BROKER_URL=redis://localhost:6379/0    # (Windows: set/$env:)
python manage.py ingest --pages 5
python manage.py ingest_status
```

## Flags do comando `ingest`

| Flag | Efeito |
|------|--------|
| `--pages N` | Quantas páginas do SteamSpy puxar (~1.000 jogos/página). |
| `--limit N` | Máximo de candidatos a enfileirar nesta execução. |
| `--resume` | Pula o refresh do ranking; só reenfileira `pending`/`failed`. |
| `--sync` | Roda inline, sem worker (para testar com poucos jogos). |

## Verificação

```bash
docker compose exec web python manage.py ingest_status
# Ex.: pending=0 fetching=0 done=4870 failed=130
```

- `failed` residual é esperado (DLCs, apps sem detalhes, remoções). Detalhes do
  erro ficam em `IngestCandidate.last_error` (visível no admin).
- Capas baixadas ficam em `media/covers/`; jogos sem capa usam o fallback de
  gradiente automaticamente.

## Reset (recomeçar do zero)

```bash
# Remove candidatos e capas; NÃO apaga bibliotecas de usuários.
docker compose exec web python manage.py shell -c "from web.models import IngestCandidate; IngestCandidate.objects.all().delete()"
# (opcional) limpar media/covers/ manualmente
```

## Agendamento (opcional)

Refresh periódico via Celery Beat fica **desligado por padrão**
(`INGEST_SCHEDULE_ENABLED=0`). Para ligar, suba o serviço `beat`
(`docker compose --profile beat up -d beat`) e ajuste a env.
