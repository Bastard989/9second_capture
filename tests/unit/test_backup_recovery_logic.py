from interview_analytics_agent.services.local_pipeline import _extract_missing_tail


def test_extract_missing_tail_when_full_prefix_matches() -> None:
    existing = "Привет команда сегодня короткий статус"
    backup = "Привет команда сегодня короткий статус и блокеры по релизу"
    assert _extract_missing_tail(existing_text=existing, backup_text=backup) == "и блокеры по релизу"


def test_extract_missing_tail_when_overlap_by_tokens() -> None:
    existing = "Сейчас обсуждаем прогресс по задачам команды платформы"
    backup = "задачам команды платформы и перенос сроков по интеграции"
    assert (
        _extract_missing_tail(existing_text=existing, backup_text=backup)
        == "и перенос сроков по интеграции"
    )


def test_extract_missing_tail_when_backup_empty() -> None:
    assert _extract_missing_tail(existing_text="что-то", backup_text="") == ""
