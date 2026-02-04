"""
Retry/DLQ утилиты для очередей.

Назначение:
- аккуратно перекидывать задачи обратно в очередь с ограниченным числом попыток
- делать простой backoff (sleep) между повторными постановками
- DLQ как отдельный stream <queue>:dlq

Важно:
- это синхронная реализация (подходит для наших воркеров)
"""

from __future__ import annotations

import time
from typing import Any

from interview_analytics_agent.common.logging import get_project_logger
from interview_analytics_agent.queue.streams import enqueue, stream_dlq_name

log = get_project_logger()


def requeue_with_backoff(
    *,
    queue_name: str,
    task_payload: dict[str, Any],
    max_attempts: int = 3,
    backoff_sec: int = 1,
) -> bool:
    """
    Повторно поставить задачу в очередь, увеличивая attempts.

    Возвращает:
    - True: задача поставлена обратно в очередь
    - False: задача отправлена в DLQ
    """
    attempts = int(task_payload.get("attempts", 0)) + 1
    task_payload["attempts"] = attempts

    if attempts > max_attempts:
        # В DLQ — чтобы не зациклиться
        dlq = stream_dlq_name(queue_name)
        enqueue(dlq, task_payload)
        log.warning(
            "task_moved_to_dlq",
            extra={
                "payload": {
                    "queue": queue_name,
                    "dlq": dlq,
                    "attempts": attempts,
                    "max_attempts": max_attempts,
                }
            },
        )
        return False

    # Backoff
    if backoff_sec and backoff_sec > 0:
        time.sleep(backoff_sec)

    enqueue(queue_name, task_payload)
    log.warning(
        "task_requeued",
        extra={
            "payload": {
                "queue": queue_name,
                "attempts": attempts,
                "max_attempts": max_attempts,
                "backoff_sec": backoff_sec,
            }
        },
    )
    return True
