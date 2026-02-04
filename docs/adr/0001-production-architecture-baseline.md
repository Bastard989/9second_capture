# ADR 0001: Production Architecture Baseline

- Status: Accepted
- Date: 2026-02-04

## Context

Нужно зафиксировать базовую production-архитектуру для interview-analytics-agent с двумя режимами работы:
1) post-meeting (загрузка записи),
2) realtime (подключение к встрече и потоковая транскрипция).

## Decision

1. Runtime:
   - Production: Kubernetes.
   - Development: Docker Compose.
2. Security:
   - Внешний трафик: JWT/OIDC.
   - Межсервисный доступ: service API keys.
3. Queueing:
   - Redis Streams + consumer groups + DLQ.
4. STT:
   - faster-whisper.
   - Модель прогревается заранее, runtime в offline режиме.
5. Storage:
   - Shared POSIX storage (NFS/managed NFS) для chunks и артефактов.
   - S3-compatible storage не используется.
6. Observability:
   - Prometheus + Alertmanager + Grafana + Loki + OTEL/Tempo.
7. Realtime transport:
   - WebSocket.
8. LLM layer:
   - OpenAI-compatible API (сейчас Ollama), с возможностью замены на корпоративную модель без изменения контракта.

## Consequences

- Плюсы:
  - Хорошая отказоустойчивость и масштабирование воркеров.
  - Предсказуемая эксплуатация через стандартный production стек.
  - Возможность поэтапно усиливать SLA/SLO.
- Минусы:
  - Выше сложность инфраструктуры (K8s, OIDC, Observability stack).
  - Требуется дисциплина по миграциям, мониторингу и runbook.

## Follow-up

- Внедрить JWT/OIDC и service key fallback.
- Перевести воркеры с Redis Lists на Redis Streams.
- Добавить DB-idempotency constraints для transcript segments.
- Довести e2e smoke до полного бизнес-сценария.
