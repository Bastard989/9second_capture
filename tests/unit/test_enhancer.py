from interview_analytics_agent.processing.enhancer import (
    enhance_text,
    normalize_text_deterministic,
    normalize_transcript_deterministic,
)


def test_enhancer_adds_punct():
    text, meta = enhance_text("привет")
    assert text.endswith(".")
    assert "final_punct" in meta["applied"]


def test_normalize_text_deterministic_removes_fillers():
    text, meta = normalize_text_deterministic("ну привет мм")
    assert text == "привет."
    assert "filler_cleanup" in meta["applied"]


def test_normalize_transcript_deterministic_preserves_speaker_prefix():
    text, meta = normalize_transcript_deterministic("CANDIDATE: ну привет\nINTERVIEWER: мм ок")
    assert text.splitlines()[0] == "CANDIDATE: привет."
    assert text.splitlines()[1] == "INTERVIEWER: ок."
    assert meta["lines"] == 2
