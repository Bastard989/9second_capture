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


def test_extract_missing_tail_avoids_full_duplicate_append() -> None:
    existing = "запись запущена транскрипт будет обновляться в реальном времени"
    backup = "Запись запущена, транскрипт будет обновляться в реальном времени."
    assert _extract_missing_tail(existing_text=existing, backup_text=backup) == ""


def test_extract_missing_tail_allows_short_prefix_recovery() -> None:
    existing = "старт записи"
    backup = "старт записи потом пошел основной текст встречи"
    assert (
        _extract_missing_tail(existing_text=existing, backup_text=backup)
        == "потом пошел основной текст встречи"
    )
