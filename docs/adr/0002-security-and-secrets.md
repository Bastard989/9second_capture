# ADR 0002: Security and Secrets Strategy

- Status: Accepted
- Date: 2026-02-04

## Context

Для production нужны централизованная аутентификация, ротация секретов и контроль доступа.

## Decision

1. Auth model:
   - AUTH_MODE=jwt для внешних клиентов.
   - В jwt-режиме разрешен service API key fallback для внутреннего трафика.
2. OIDC:
   - Проверка JWT через OIDC issuer/JWKS.
   - Для локальной разработки разрешен JWT_SHARED_SECRET.
3. Secret management:
   - В репозитории храним только `.env.example`.
   - Production секреты: Vault / cloud secret manager + Kubernetes secret sync.
4. Ingress/TLS:
   - Для production принимается NGINX Ingress + cert-manager.

## Consequences

- Плюсы:
  - SSO/корпоративные токены, аудит и ротация.
  - Нет секретов в git и образах.
- Минусы:
  - Более сложный начальный bootstrap окружений.
