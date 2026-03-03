# 9second_capture

`9second_capture` — локальный агент записи встреч: захват аудио -> `meeting_audio.mp3` -> транскрипты/артефакты.

## Что важно сейчас

- Основной принцип: **record-first / mp3-first**.
- Кнопка `Стоп` завершает захват и финализирует MP3.
- Тяжелые этапы (`STT`, `LLM`) выполняются позже по запросу в блоке `Результаты`.

## Режимы захвата

1. `Драйвер: системный звук`
- Захват через loopback (BlackHole / VB-CABLE / Monitor).

2. `Браузер: экран + звук`
- Захват через браузерный диалог `Share audio`.

3. `Ссылка: браузер + звук` (`link_fallback`)
- На `Старт` открывается ссылка встречи.
- Захват идет в realtime через браузер (`capture_mode=screen`).
- Системный звук берется из `Share audio`.

4. `API: подключение к встрече`
- Отдельный API-коннекторный поток (без live-текста в UI).

## Логика режима «Ссылка» (актуально)

- `work_mode=link_fallback` теперь валиден только для `mode=realtime`.
- На backend контекст нормализуется в `capture_mode=screen`.
- `mode=postmeeting + link_fallback` отклоняется (`422`).

Ключевой файл:
- `apps/api_gateway/routers/meetings.py`

## Быстрый локальный запуск

```bash
cd "/Users/kirill/Documents/New project/9second_capture"
python3 scripts/run_local_agent.py
```

После старта:
- API обычно на `http://127.0.0.1:8010`
- UI доступен по адресу из логов launcher/agent.

## Smoke-check режима link_fallback

Проверка, что `link_fallback + realtime` стартует без `422`:

```bash
curl -sS -X POST 'http://127.0.0.1:8010/v1/meetings/start' \
  -H 'Content-Type: application/json' \
  -d '{
    "meeting_id": "smoke-link-local",
    "mode": "realtime",
    "consent": "unknown",
    "context": {
      "source": "local_ui",
      "work_mode": "link_fallback"
    }
  }'
```

Ожидаемо: HTTP 200 и `status` типа `PipelineStatus.queued`.

## Транскрипты и артефакты

- `raw` — исходный STT-текст.
- `normalized` — deterministic-нормализация без LLM.
- `clean` — читабельный текст (normalizer + optional LLM).

Дополнительно:
- LLM-артефакты (`template/custom/table`).
- RAG-поиск и сравнение интервью.

## Полезные команды

### Unit tests

```bash
cd "/Users/kirill/Documents/New project/9second_capture"
pytest -q tests/unit
```

### Быстрый quick-record по ссылке (CLI)

```bash
cd "/Users/kirill/Documents/New project/9second_capture"
python3 scripts/quick_record_meeting.py --url "https://your-meeting-link"
```

### Make targets

```bash
cd "/Users/kirill/Documents/New project/9second_capture"
make quick-record URL="https://your-meeting-link"
make test
```

## Сборка macOS app

```bash
cd "/Users/kirill/Documents/New project/9second_capture"
bash tools/packaging/build_mac.sh
open -n "/Users/kirill/Documents/New project/9second_capture/dist/9second_capture.app"
```

## Примечания по бинарникам

- `dist/` исключен из git (`.gitignore`), поэтому собранные `.app`-артефакты не коммитятся в репозиторий.
- Код, конфиги и тесты коммитятся и пушатся в `main`; бинарники собираются локально/в релизном пайплайне.
