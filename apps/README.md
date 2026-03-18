# Runtime Services

`apps/` is the runtime layer of the agent. Every directory here represents a process
role, not just a code category.

## Services

- `api_gateway/`
  FastAPI application, WebSocket endpoints, UI static files, main HTTP API.

- `launcher/`
  Local installation wizard and desktop bootstrap service.

- `local_agent/`
  Local runtime entrypoint that starts the API gateway on `127.0.0.1`.

- `worker_stt/`
  Speech-to-text background worker.

- `worker_enhancer/`
  Transcript cleanup and enhancement worker.

- `worker_analytics/`
  Report/analytics worker.

- `worker_delivery/`
  Export and delivery worker.

- `worker_retention/`
  Retention and cleanup worker.

- `worker_reconciliation/`
  Consistency and reconciliation worker.

- `alert_relay/`
  Alert forwarding service.

- `alert_sink/`
  Alert receiving/test sink.

## Design rule

Runtime entrypoints belong to `apps/`.

- `scripts/` contains wrappers, developer commands and convenience launchers.
- `src/interview_analytics_agent/` contains shared domain logic and reusable code.
