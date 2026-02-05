# Runbook: OTEL Tracing

## Цель

Проверить, что сервисы экспортируют trace-спаны и можно коррелировать события по `meeting_id`.

## Быстрый smoke (local/dev)

1. В `.env` включить:
   - `OTEL_ENABLED=true`
   - `OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318/v1/traces`
2. Поднять стек с observability:
   - `docker compose --profile observability up -d --build`
3. Прогнать e2e:
   - `python3 tools/e2e_local.py`
4. Проверить логи collector:
   - `docker compose logs otel-collector --tail=200`
5. Проверить корреляцию в логах сервиса:
   - `docker compose logs api-gateway --tail=200 | rg trace_id`

## Что считать успехом

- В `otel-collector` есть входящие spans без export error.
- В логах API/воркеров есть `trace_id` и `meeting_id`.
- Для одного `meeting_id` видно связанный trace по этапам:
  ingest -> stt -> enhancer -> analytics -> delivery.

## Диагностика

- `otel_dependencies_missing`:
  - в образе нет OTEL пакетов; пересобрать контейнер.
- `otel_setup_failed`:
  - проверить `OTEL_EXPORTER_OTLP_ENDPOINT` и доступность collector.
- Нет `trace_id` в логах:
  - убедиться, что запросы реально идут через `/v1/meetings/...` или WS ingest,
  - проверить, что обновлённый образ запущен (`docker compose up -d --build`).
