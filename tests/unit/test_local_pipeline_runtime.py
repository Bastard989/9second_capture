from __future__ import annotations

from interview_analytics_agent.services import local_pipeline


class _FakeProvider:
    def __init__(self) -> None:
        self.closed = False
        self.model = self

    def close(self) -> None:
        self.closed = True


def test_shutdown_stt_provider_runtime_clears_provider_and_flags() -> None:
    provider = _FakeProvider()
    snapshot_provider = local_pipeline._stt_provider
    snapshot_started = local_pipeline._stt_warmup_started
    snapshot_ready = local_pipeline._stt_warmup_ready
    snapshot_error = local_pipeline._stt_warmup_error
    snapshot_thread = local_pipeline._stt_warmup_thread
    try:
        local_pipeline._stt_provider = provider
        local_pipeline._stt_warmup_started = True
        local_pipeline._stt_warmup_ready = True
        local_pipeline._stt_warmup_error = "boom"
        local_pipeline._stt_warmup_thread = None

        local_pipeline.shutdown_stt_provider_runtime(join_timeout_sec=0)

        assert provider.closed is True
        assert local_pipeline._stt_provider is None
        assert local_pipeline._stt_warmup_started is False
        assert local_pipeline._stt_warmup_ready is False
        assert local_pipeline._stt_warmup_error == ""
        assert local_pipeline._stt_warmup_thread is None
    finally:
        local_pipeline._stt_provider = snapshot_provider
        local_pipeline._stt_warmup_started = snapshot_started
        local_pipeline._stt_warmup_ready = snapshot_ready
        local_pipeline._stt_warmup_error = snapshot_error
        local_pipeline._stt_warmup_thread = snapshot_thread
