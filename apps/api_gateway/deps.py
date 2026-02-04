"""
FastAPI Depends.

Сюда выносим:
- проверку авторизации (Bearer JWT / X-API-Key)
- (в будущем) correlation_id, request_id и т.д.
"""

from __future__ import annotations

from fastapi import Header, HTTPException, status

from interview_analytics_agent.common.errors import UnauthorizedError
from interview_analytics_agent.common.security import require_auth


def auth_dep(
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    """
    Проверка авторизации для HTTP.
    """
    try:
        require_auth(authorization=authorization, x_api_key=x_api_key)
    except UnauthorizedError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": e.code, "message": e.message},
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
