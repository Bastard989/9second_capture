# Performance Runbook

## Load guardrail (локально)

1. Поднять стек в быстром режиме:
   `APP_ENV=dev AUTH_MODE=api_key API_KEYS=dev-user-key SERVICE_API_KEYS=dev-service-key STT_PROVIDER=mock LLM_ENABLED=false docker compose up -d --build`
2. Запустить guardrail:
   `python3 tools/realtime_load_guardrail.py --base-url http://127.0.0.1:8010 --user-key dev-user-key --service-key dev-service-key`
   - если нужно падать при недоступности admin-checks: добавь `--strict-admin-checks`.
3. Проверить результат:
   - stdout: `load guardrail OK|FAILED`
   - отчет: `reports/realtime_load_guardrail.json`

## Что проверяется

- `failure_rate` — доля встреч, где pipeline не дошел до `report`.
- `p95_ingest_ms` — p95 latency HTTP ingest (`POST /v1/meetings/{id}/chunks`).
- `p95_e2e_ms` — p95 от первого chunk до готового `report`.
- `throughput_meetings_per_min` — успешные встречи в минуту.
- `total_dlq_depth` — суммарная глубина DLQ (если передан `--service-key`).

## Действия, если guardrail упал

1. Проверить `failed_meetings` и `checks` в JSON-отчете.
2. Проверить admin endpoint: `GET /v1/admin/queues/health`.
3. Проверить метрики и backlog:
   - `/metrics`
   - Prometheus/Grafana (если поднят observability profile)
4. Проверить логи `api-gateway` и worker'ов:
   `docker compose logs --no-color --tail=300 api-gateway worker-stt worker-enhancer worker-analytics worker-delivery`
