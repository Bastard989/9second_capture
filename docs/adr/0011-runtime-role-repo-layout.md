# ADR 0011: Runtime-Role Repository Layout

## Status

Accepted

## Context

The repository already contains clear runtime roles:

- API gateway
- workers
- alert services
- local launcher

But the entrypoints were split between `apps/` and `scripts/`, which made the
runtime topology harder to understand:

- `apps/` contained long-running services
- `scripts/` also contained long-running runtime entrypoints (`launcher.py`, `run_local_agent.py`)

This created a hybrid layout that was convenient for development, but less clear
for onboarding and production architecture reviews.

## Decision

Use the following structure rule:

- `apps/` = runtime services and process roles
- `src/interview_analytics_agent/` = shared application/core code
- `scripts/` = wrappers and developer tooling
- `deploy/`, `ops/`, `configs/` = infrastructure layer
- `docs/`, `diagrams/` = architecture and operational knowledge
- `tools/` = guardrails, benchmarks, packaging and support tooling

As part of this decision:

- move the local installation launcher runtime into `apps/launcher/main.py`
- move the local agent runtime into `apps/local_agent/main.py`
- keep `scripts/launcher.py` and `scripts/run_local_agent.py` as compatibility wrappers

## Consequences

### Positive

- runtime roles are visible in one place
- local desktop runtime is treated as a first-class service
- developers can still use existing commands and scripts
- packaging and test flows keep backward compatibility

### Negative

- the repository remains a hybrid monorepo for now
- infrastructure is still split across `deploy/`, `ops/` and `configs/`
- the shared core is still under `src/`, not under a dedicated `packages/` root

## Follow-up

Recommended next phase:

1. keep `apps/` as the runtime root
2. add explicit architecture docs for service boundaries
3. only if needed later, introduce a `packages/` root for shared libraries
4. avoid a destructive top-level rewrite unless deployment tooling requires it
