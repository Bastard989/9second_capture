# 9second_capture

Локальный агент для записи и анализа интервью.

## Для тех, кто не из IT
`9second_capture` нужен, чтобы записать интервью, получить расшифровку, собрать краткую аналитику и передать результат сеньорам, которые не были на встрече.

Что делает агент простыми словами:
- пишет звук встречи на вашем компьютере;
- сохраняет итоговый MP3 файл встречи;
- делает `raw` (сырой) и `clean` (очищенный) текст;
- формирует отчёт и таблицу для сравнения кандидатов;
- всё хранит локально, без обязательной отправки в облако.

Что важно после последних доработок:
- для каждой встречи создаётся канонический аудиофайл `meeting_audio.mp3`;
- в списке встреч записи имеют имена `Запись 1`, `Запись 2`, ...;
- в меню `...` можно переименовать запись;
- после завершения записи UI предлагает сразу сохранить MP3 в выбранное место;
- в разделе действий есть отдельная кнопка `MP3`.

## Быстрый запуск (macOS)
```bash
cd "/Users/kirill/Documents/New project/9second_capture"
git pull
bash tools/packaging/build_mac.sh
open -n "/Users/kirill/Documents/New project/9second_capture/dist/9second_capture.app"
```

## Первый запуск в UI
1. Откройте лаунчер.
2. Нажмите `Исправить в 1 клик`.
3. Нажмите `Открыть UI агента`.
4. В блоке `Подключение` выберите источник звука и проверьте драйвер.
5. В блоке `Запись` нажмите `Проверить` (диагностика), затем `Старт`.
6. После `Стоп` подтвердите сохранение MP3.

## Где лежат файлы
По умолчанию данные лежат в проекте:
- `./data/records/<meeting_id>/meeting_audio.mp3`
- `./data/records/<meeting_id>/raw.txt`
- `./data/records/<meeting_id>/clean.txt`
- `./data/records/<meeting_id>/report_*.json|txt`
- `./data/records/<meeting_id>/structured_*.json|csv`
- `./data/records/<meeting_id>/meeting_meta.json` (имя записи, индекс)

Quick fallback рекордер пишет отдельные MP3 в:
- `./data/records/quick/`

## MP3 fallback: как это работает
Сервис пытается собрать `meeting_audio.mp3` в таком порядке:
1. `backup_audio.*` (live запись из браузера/драйвера);
2. `source_upload.*` (если встреча была загружена файлом);
3. blob-чанк `chunks/0` или `chunks/1` как запасной путь.

Если формат не MP3, используется `ffmpeg` для перекодирования.

## Ollama / LLM
Если используете локальную LLM:
```bash
brew install --cask ollama
open -a Ollama
ollama pull llama3.1:8b
ollama list
```

В UI:
- `Сканировать` -> выбрать модель -> `Сменить модель`.

Совместимость:
- `llama3:8b` принимается как совместимая с `llama3.1:8b`.

## Windows сборка
Локально на macOS надёжный `.exe` не собирается. Используйте:
- Windows машину + `tools/packaging/build_windows.ps1`, или
- GitHub Actions workflow `Desktop Windows Build` (артефакт `9second_capture-windows`).

---

## Техническая часть

### Основные компоненты
- `apps/api_gateway` — HTTP/WebSocket API и UI.
- `src/interview_analytics_agent` — STT/LLM/обработка/хранилище.
- `scripts/launcher.py` — desktop-лаунчер (`.app/.exe` entrypoint).
- `scripts/run_local_agent.py` — локальный запуск агента для разработки.

### Ключевые сценарии записи
1. **Realtime (браузер, системный звук/экран)**
- `/v1/meetings/start`
- ingest чанков через WS/HTTP
- загрузка `backup_audio.*`
- `/v1/meetings/{id}/finish` -> финализация текста + материализация `meeting_audio.mp3`

2. **Upload audio**
- `/v1/meetings/start` (mode `postmeeting`)
- `/v1/meetings/{id}/upload` (файл сохраняется как `source_upload.*`)
- `/finish` -> генерация `meeting_audio.mp3`

3. **Quick fallback recorder**
- `/v1/quick-record/start`
- локальная запись + MP3
- при `upload_to_agent=true` запись отправляется и как chunk, и как `backup-audio`.

### API по артефактам
- `GET /v1/meetings`
- `POST /v1/meetings/{id}/rename`
- `GET /v1/meetings/{id}/artifact?kind=audio&fmt=mp3`
- `GET /v1/meetings/{id}/artifact?kind=raw|clean|report|structured|senior_brief...`

### Переменные окружения (минимум)
- `APP_ENV=dev`
- `AUTH_MODE=api_key` или `none`
- `API_KEYS=dev-user-key`
- `SERVICE_API_KEYS=dev-service-key`
- `RECORDS_DIR=./data/records`

Для локальной LLM:
- `LLM_ENABLED=true`
- `OPENAI_API_BASE=http://127.0.0.1:11434/v1`
- `OPENAI_API_KEY=ollama`
- `LLM_MODEL_ID=llama3.1:8b`

### Команды для разработчика
```bash
# backend + workers
docker compose up -d --build

# unit tests
python3 -m pytest -q

# локальный запуск без docker
python3 scripts/run_local_agent.py
```

### Карта скриптов
- `scripts/launcher.py` — установка зависимостей в `~/.9second_capture`, запуск агента, открытие UI.
- `scripts/run_local_agent.py` — запуск local API + UI для разработки.
- `scripts/quick_record_meeting.py` — quick fallback запись встречи по URL.
- `tools/packaging/build_mac.sh` / `build_windows.ps1` / `build_linux.sh` — сборка desktop-бинарников.

## Что уже почищено
- удалён локальный build-кэш `.pyinstaller-cache`;
- добавлен игнор `.pyinstaller-cache/` в `.gitignore`.

## Ограничения
- Для не-MP3 источников нужен `ffmpeg` для гарантированной конвертации в `meeting_audio.mp3`.
- Если внешняя интеграция шлёт только произвольные чанки без backup/upload аудио, качество MP3-фоллбека зависит от входного формата.
