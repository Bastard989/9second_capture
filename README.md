# 9second_capture

`9second_capture` — локальный агент для записи встреч, формирования транскриптов и генерации LLM-форматов из файлов.

## Актуальная модель работы

- Запись и импорт MP3: отдельно.
- STT (транскрипт): только по явной команде пользователя.
- LLM (таблицы/JSON/CSV/summary): только по явной команде пользователя.
- Live-транскрипт во время записи не используется.

## Режимы записи

1. `Браузер: экран + звук`
- Захват через браузерный `Share audio`.

2. `API/файл: загрузка аудио`
- Работа с уже готовыми аудиофайлами и API-подключением.

3. `Ссылка: quick fallback`
- Быстрый старт записи встречи по ссылке.

## Базовый сценарий

1. Выбрать режим и записать встречу (или импортировать MP3).
2. Сохранить MP3 в разделе `Результаты -> Аудио`.
3. В разделе `Результаты -> Транскрипция` запустить генерацию `Raw/Clean` вручную.
4. В разделе `Результаты -> LLM` прикрепить TXT/CSV/JSON/MD и отправить запрос на нужный формат.

## Локальный запуск

```bash
cd "/Users/kirill/Documents/New project/9second_capture"
python3 scripts/run_local_agent.py
```

## Сборка macOS приложения

```bash
cd "/Users/kirill/Documents/New project/9second_capture"
bash tools/packaging/build_mac.sh
open -n "/Users/kirill/Documents/New project/9second_capture/dist/9second_capture.app"
```

## Проверки

```bash
cd "/Users/kirill/Documents/New project/9second_capture"
pytest -q tests/unit
```

## Документация

- Пользовательский гайд: `docs/user_guide.md`
- Короткий гайд: `docs/user_guide_simple_ru.md`
- Чеклист проверки: `docs/qa_checklist.md`
- Troubleshooting: `docs/troubleshooting_capture_ru.md`

## Важно про артефакты сборки

- `dist/`, `build/`, `.pyinstaller-cache/`, `*.spec` не хранятся в Git.
- В репозиторий коммитится только исходный код и документация.
