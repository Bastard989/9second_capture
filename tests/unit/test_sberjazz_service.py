from __future__ import annotations

from interview_analytics_agent.services import sberjazz_service


class _FakeRedis:
    def __init__(self) -> None:
        self._store: dict[str, str] = {}
        self._sets: dict[str, set[str]] = {}

    def set(self, key: str, value: str, ex: int | None = None) -> bool:
        _ = ex
        self._store[key] = value
        return True

    def get(self, key: str) -> str | None:
        return self._store.get(key)

    def sadd(self, key: str, value: str) -> int:
        self._sets.setdefault(key, set()).add(value)
        return 1

    def smembers(self, key: str) -> set[str]:
        return self._sets.get(key, set())


class _FakeConnector:
    def __init__(self) -> None:
        self.join_calls = 0
        self.leave_calls = 0

    def join(self, meeting_id: str):
        self.join_calls += 1
        return {"meeting_id": meeting_id}

    def leave(self, meeting_id: str) -> None:
        _ = meeting_id
        self.leave_calls += 1

    def fetch_recording(self, meeting_id: str):
        _ = meeting_id
        return None


def test_join_state_persisted_and_readable_from_redis(monkeypatch) -> None:
    fake_redis = _FakeRedis()
    fake_connector = _FakeConnector()
    monkeypatch.setattr(sberjazz_service, "redis_client", lambda: fake_redis)
    monkeypatch.setattr(
        sberjazz_service,
        "_resolve_connector",
        lambda: ("sberjazz_mock", fake_connector),
    )
    sberjazz_service._SESSIONS.clear()

    joined = sberjazz_service.join_sberjazz_meeting("meeting-1")
    assert joined.connected is True
    assert fake_connector.join_calls == 1

    # Эмулируем новый процесс: удаляем in-memory state, читаем из Redis.
    sberjazz_service._SESSIONS.clear()
    loaded = sberjazz_service.get_sberjazz_meeting_state("meeting-1")
    assert loaded.connected is True
    assert loaded.meeting_id == "meeting-1"


def test_reconnect_calls_leave_then_join_when_connected(monkeypatch) -> None:
    fake_redis = _FakeRedis()
    fake_connector = _FakeConnector()
    monkeypatch.setattr(sberjazz_service, "redis_client", lambda: fake_redis)
    monkeypatch.setattr(
        sberjazz_service,
        "_resolve_connector",
        lambda: ("sberjazz_mock", fake_connector),
    )
    sberjazz_service._SESSIONS.clear()

    sberjazz_service.join_sberjazz_meeting("meeting-2")
    reconnected = sberjazz_service.reconnect_sberjazz_meeting("meeting-2")

    assert reconnected.connected is True
    assert fake_connector.leave_calls == 1
    assert fake_connector.join_calls >= 2


def test_reconcile_reconnects_stale_sessions(monkeypatch) -> None:
    fake_redis = _FakeRedis()
    monkeypatch.setattr(sberjazz_service, "redis_client", lambda: fake_redis)

    sberjazz_service._SESSIONS.clear()
    sberjazz_service._SESSIONS["stale-1"] = sberjazz_service.SberJazzSessionState(
        meeting_id="stale-1",
        provider="sberjazz_mock",
        connected=True,
        attempts=1,
        last_error=None,
        updated_at="2020-01-01T00:00:00+00:00",
    )
    sberjazz_service._SESSIONS["fresh-1"] = sberjazz_service.SberJazzSessionState(
        meeting_id="fresh-1",
        provider="sberjazz_mock",
        connected=True,
        attempts=1,
        last_error=None,
        updated_at="2099-01-01T00:00:00+00:00",
    )

    called: list[str] = []

    def _fake_reconnect(meeting_id: str):
        called.append(meeting_id)
        return sberjazz_service.SberJazzSessionState(
            meeting_id=meeting_id,
            provider="sberjazz_mock",
            connected=True,
            attempts=2,
            last_error=None,
            updated_at="2099-01-01T00:00:01+00:00",
        )

    monkeypatch.setattr(sberjazz_service, "reconnect_sberjazz_meeting", _fake_reconnect)

    result = sberjazz_service.reconcile_sberjazz_sessions(limit=10)
    assert result.scanned >= 2
    assert result.stale >= 1
    assert result.reconnected >= 1
    assert "stale-1" in called
