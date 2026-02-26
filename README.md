# 9second_capture

`9second_capture` — локальный агент для записи интервью, получения канонического MP3, построения транскриптов и последующей LLM/RAG-аналитики.

## Что меняется в векторе проекта (новая базовая модель)
Проект переходит на явную многоуровневую схему:

1. `Audio layer`: запись встречи любым из поддерживаемых способов -> единый `meeting_audio.mp3`
2. `Transcript layer`: `STT` строит транскрипт из MP3
3. `Cleaning layer`: очистка текста (эвристики + опционально LLM)
4. `LLM Artifacts layer`: любые производные форматы (JSON/CSV/таблицы/summary/brief/custom)
5. `RAG layer`: поиск/сравнение по одному или нескольким интервью с цитатами

Ключевое правило: `STT` отвечает только за распознавание речи (транскрипт), а `LLM` работает поверх текста, а не поверх захвата записи.

## Новая терминология (фиксируем)
Чтобы не путаться в слове "отчет", в проекте используется такая терминология:

- `MP3 / Audio artifact` — канонический аудиофайл встречи (`meeting_audio.mp3`)
- `Raw transcript` — сырой STT-транскрипт с мусорными вставками (`ээ`, `мм`, повторы и т.п.)
- `Normalized transcript` — транскрипт после детерминированной очистки (без LLM)
- `Clean transcript` — улучшенный транскрипт (эвристики + опционально LLM)
- `LLM artifact` — любой артефакт, построенный из транскрипта (summary, таблица, JSON, brief, custom output)
- `Analysis` — аналитическая сводка/оценка, построенная LLM или fallback-логикой
- `RAG chat` — чат/запросы по одному или нескольким интервью с retrieval по чанкам транскриптов

### Важное замечание о текущем коде (legacy naming)
В текущем коде еще встречаются legacy-названия (`report`, `structured`, `raw.txt`, `clean.txt`, endpoint `/report`). Это рабочее состояние проекта. В roadmap ниже заложена поэтапная миграция на новую терминологию (`transcript`, `analysis`, `llm artifacts`, `rag`).

## Что уже реализовано сейчас (по состоянию текущей ветки)
### Уже работает
- 4 сценария получения записи (UI режимы): драйверный захват, экран+аудио, API/quick сценарии, импорт/загрузка аудио
- Канонический MP3-артефакт встречи (`meeting_audio.mp3`) как основной результат записи
- `record-first` UX: `Stop` завершает запись/финализирует MP3, а не ждет тяжелую STT/LLM обработку
- Ленивое построение текста/артефактов по запросу (on-demand) вместо тяжелой финализации на `Stop`
- Экспорт MP3 и базовые артефакты через UI/API
- Локальная LLM через OpenAI-compatible endpoint (включая Ollama)
- Quick fallback режим для аварийной записи MP3

### Что еще в переходе (будет переработано)
- Понятие `report` перегружено: сейчас это и транскрипт в понимании пользователя, и аналитический отчет в коде
- Нет отдельного универсального LLM-transform слоя с custom prompt/schema
- Нет полноценного RAG-индекса по всем интервью и multi-interview chat/compare
- Нет единого чата в UI для "сделай любой формат из этого транскрипта"

## Продуктовая логика (целевая)
### 1) Захват -> MP3 (единый аудио-артефакт)
Независимо от способа захвата, итогом всегда должен быть стабильный `meeting_audio.mp3`.

Поддерживаемые источники (текущий UI):
- `Драйвер: системный звук`
- `Браузер: экран + звук`
- `API: подключение/интеграционный сценарий`
- `Quick fallback` (аварийный сценарий записи)

### 2) MP3 -> транскрипт (STT)
`STT` строит транскрипт из MP3. Это не аналитика и не "оценка кандидата". Это текстовая расшифровка речи.

Артефакты слоя транскрипта:
- `raw transcript` — честный STT-output
- `normalized transcript` — детерминированная очистка (эвристики)
- `clean transcript` — улучшенная версия (эвристики + опционально LLM)

### 3) Транскрипт -> LLM артефакты
LLM берет `raw` или `clean` транскрипт и строит пользовательский результат:
- summary
- аналитическая сводка
- scorecard
- таблица для Excel/Google Sheets
- structured JSON
- CSV
- custom format по текстовому запросу пользователя
- доменные шаблоны (например, hiring brief)

### 4) RAG поверх всех интервью
RAG используется для поиска, сравнения и чата:
- по одному интервью
- по выбранному набору интервью
- по всем интервью с фильтрами

RAG-ответы должны возвращаться с цитатами/ссылками на фрагменты транскрипта (реплики/таймкоды).

## Почему рекомендуется гибрид для `clean transcript`
Для качества и стабильности рекомендуется гибридный подход:

1. `STT -> raw transcript`
2. `Deterministic cleaner` (эвристики)
3. `LLM cleaner` (опционально, для повышения качества)

Почему так лучше, чем "сразу LLM":
- `raw` всегда остается воспроизводимым и проверяемым исходником
- базовая очистка работает быстро, дешево и предсказуемо
- LLM можно отключить без потери основного пайплайна
- меньше риск исказить смысл при недоступности/ошибке LLM

## Архитектура (целевая, с учетом текущей базы)
### Слои
- `Capture & Audio`: запись/загрузка/финализация MP3
- `Transcript Service`: STT + нормализация + clean pipeline
- `Artifact Service`: генерация артефактов из транскрипта (LLM/non-LLM)
- `RAG Service`: indexing/retrieval/synthesis
- `UI`: запись, управление артефактами, чат/запросы, compare workspace

### Принцип разделения ответственности
- Захват не делает тяжелую аналитику
- STT не делает продуктовую аналитику
- LLM не трогает аудио напрямую
- RAG не подменяет транскрипт, а помогает находить релевантные фрагменты

## Состояние UI (как мыслить блоками после миграции)
### Блок 1. Запись
Назначение: получить стабильный `meeting_audio.mp3`

### Блок 2. Транскрипты
Назначение: построить/перестроить
- `raw transcript`
- `normalized transcript`
- `clean transcript`

### Блок 3. LLM Артефакты
Назначение: взять выбранный транскрипт (`raw|normalized|clean`) и получить:
- шаблонный вывод
- custom формат
- structured table / JSON / CSV

### Блок 4. RAG Chat / Compare
Назначение:
- чат по одному интервью
- чат по выбранным интервью
- сравнение интервью в ручном наборе
- поиск по всем интервью

## Где хранятся данные (текущая и целевая модель)
Для desktop-сценария launcher хранит рабочие данные в пользовательской папке:
- `~/.9second_capture/records/<meeting_id>/meeting_audio.mp3`
- `~/.9second_capture/records/<meeting_id>/raw.txt` (legacy name, semantically `raw transcript`)
- `~/.9second_capture/records/<meeting_id>/clean.txt` (legacy name, semantically `clean transcript`)
- `~/.9second_capture/records/<meeting_id>/report_*.json|txt` (legacy analytics artifacts)
- `~/.9second_capture/records/<meeting_id>/structured_*.json|csv` (legacy structured artifacts)
- `~/.9second_capture/records/<meeting_id>/meeting_meta.json`

Для dev/server запуска путь задается через `RECORDS_DIR` (по умолчанию `./data/records`).

Quick fallback-рекордер хранит отдельные файлы в `QUICK_RECORD_OUTPUT_DIR` (по умолчанию `./data/records/quick`).

### Целевая эволюция структуры артефактов (roadmap)
Планируемая структура внутри папки встречи:
- `audio/meeting_audio.mp3`
- `transcripts/raw.txt`
- `transcripts/normalized.txt`
- `transcripts/clean.txt`
- `transcripts/chunks/*.jsonl` (реплики/таймкоды/спикеры)
- `artifacts/<artifact_id>/` (`request.json`, `result.json`, `result.csv`, `meta.json`)
- `rag/chunks.jsonl`
- `rag/index_refs.json`
- `meeting_meta.json`

## Установка и запуск (актуально)
## Для конечного пользователя
Рекомендуемый путь — готовые бинарники из релизов:
- [GitHub Releases](https://github.com/Bastard989/9second_capture/releases)

### Первый запуск (launcher)
1. Нажмите `Исправить в 1 клик`
2. Нажмите `Открыть UI агента`
3. Проверьте preflight/аудио-источники
4. Нажмите `Старт`, затем `Стоп`
5. Сохраните MP3 (экспортная копия)
6. Перейдите в блок транскриптов/артефактов и формируйте нужные результаты

## Сборка из исходников
### macOS
```bash
bash tools/packaging/build_mac.sh
open -n dist/9second_capture.app
```

### Windows (PowerShell)
```powershell
powershell -ExecutionPolicy Bypass -File tools/packaging/build_windows.ps1
.\dist\9second_capture\9second_capture.exe
```

### Linux
```bash
bash tools/packaging/build_linux.sh
./dist/9second_capture/9second_capture
```

## Инженерный запуск (без desktop launcher)
```bash
# локально
python3 scripts/run_local_agent.py

# или контейнеры
docker compose up -d --build
```

## Зависимости для аудио и LLM
### ffmpeg (рекомендуется обязательно)
Используется для materialize/транскодирования MP3.

macOS:
```bash
brew install ffmpeg
```

### Ollama / локальная LLM (опционально)
Пример:
```bash
# macOS
brew install --cask ollama
open -a Ollama
ollama pull llama3.1:8b
ollama list
```

Пример конфигурации:
```bash
LLM_ENABLED=true
OPENAI_API_BASE=http://127.0.0.1:11434/v1
OPENAI_API_KEY=ollama
LLM_MODEL_ID=llama3.1:8b
```

## Текущее API (рабочее, legacy naming местами)
### Основное
- `GET /v1/diagnostics/preflight` — готовность окружения/STT/LLM
- `GET /v1/meetings` — список встреч
- `POST /v1/meetings/{id}/rename` — переименование записи
- `POST /v1/meetings/{id}/finish` — финализация записи (закрытие встречи + попытка подготовить MP3)
- `GET /v1/meetings/{id}/artifact?kind=audio&fmt=mp3` — скачать итоговый MP3

### Тексты и артефакты (legacy names, будет миграция)
- `GET /v1/meetings/{id}/artifact?kind=raw&fmt=txt`
- `GET /v1/meetings/{id}/artifact?kind=clean&fmt=txt`
- `POST /v1/meetings/{id}/report`
- `POST /v1/meetings/{id}/structured`

## Целевое API (roadmap, не все реализовано)
### Transcript API
- `POST /v1/meetings/{id}/transcripts/generate`
  - body: `{ source_audio: "meeting_audio", variants: ["raw","normalized","clean"] }`
- `GET /v1/meetings/{id}/transcripts/{variant}`
- `POST /v1/meetings/{id}/transcripts/rebuild`

### LLM Artifact API
- `POST /v1/meetings/{id}/artifacts/generate`
  - body: `{ transcript_variant, mode: "template|custom|table", template_id?, prompt?, schema? }`
- `GET /v1/meetings/{id}/artifacts/{artifact_id}`
- `GET /v1/meetings/{id}/artifacts/{artifact_id}/download?fmt=json|csv|txt|xlsx`

### RAG API
- `POST /v1/rag/index/rebuild` (по одной встрече или батчем)
- `POST /v1/rag/query`
  - body: `{ meeting_ids?: [], filters?: {}, query, response_format, with_citations: true }`
- `POST /v1/rag/chat`
  - body: `{ thread_id?, meeting_ids|filters, message }`

### Compare API
- `POST /v1/compare/jobs`
  - body: `{ meeting_ids: [...], prompt|template, output_format }`
- `GET /v1/compare/jobs/{job_id}`

## RAG: что именно планируется (production-ready подход)
### Базовые требования
- Индексация чанков транскрипта (`chunk_id`, `meeting_id`, `speaker`, `time range`, `text`)
- Metadata filters (`candidate`, `vacancy`, `level`, `interviewer`, `date`, `source mode`)
- Retrieval с цитатами (`citations`) в ответе
- Multi-meeting retrieval (выбранные интервью)
- All-meetings retrieval (по фильтру)

### Рекомендуемый стартовый стек (прагматично)
- Chunking по репликам/таймкодам
- Hybrid retrieval:
  - keyword/BM25
  - embeddings/vector search
- LLM synthesis поверх топ-N чанков
- JSON schema output для таблиц/сравнений

### Почему нужен именно полный RAG для этой задачи
Потому что целевой сценарий — не только "один отчет по одной записи", а:
- сравнить несколько интервью вручную
- найти все интервью, где обсуждали конкретную технологию/кейсы
- построить сводную таблицу по выбранным встречам
- задать произвольный вопрос по всем интервью и получить ответ с доказательствами

## LLM Chat в UI (обязательная часть нового вектора)
В UI планируется отдельный блок `LLM / RAG`, где пользователь сможет:
- выбрать источник (`raw|normalized|clean` transcript)
- выбрать scope (`одно интервью | выбранные интервью | все интервью по фильтру`)
- писать произвольный запрос
- получить ответ с цитатами
- сохранить результат в `TXT / JSON / CSV / XLSX`

### Режимы блока LLM
1. `Templates`
- Summary
- Hiring brief
- Scorecard
- Structured table

2. `Custom format`
- Пользователь пишет, какой формат нужен
- Можно передать JSON-schema (опционально)
- Backend валидирует результат и экспортирует

3. `Chat (RAG)`
- Вопросы по транскриптам
- Сравнение интервью
- Уточняющие вопросы
- Ответы с цитатами и ссылками на фрагменты

## Как стабильно генерировать таблицы и БД-виды
Для таблиц и структурированных данных рекомендуется контракт:
- LLM возвращает **JSON**, а не "красивый текст"
- backend валидирует JSON
- backend экспортирует в CSV/XLSX/Google Sheets-compatible CSV

Рекомендуемый минимальный формат ответа LLM:
- `columns`
- `rows`
- `assumptions`
- `citations`
- `warnings`

Это дает:
- воспроизводимость
- валидацию
- меньше поломок экспорта
- возможность повторно экспортировать в разные форматы без повторного вызова LLM

## Roadmap до production (новый план разработки)
Ниже зафиксирован новый вектор разработки с учетом текущего состояния проекта.

### Phase 0 — Stabilize MP3-first foundation (текущая база)
Цель: запись завершается быстро, MP3 надежно сохраняется, тяжелая обработка не висит на `Stop`.

Задачи:
- закрепить `Stop = finalize recording + MP3 only`
- убрать/пометить legacy UI тексты, где "report" используется вместо "transcript"
- доработать smoke-тесты для 4 способов получения MP3
- проверить кейсы без `ffmpeg` и с fallback-путями

Критерий готовности:
- пользователь стабильно получает MP3 после `Stop`
- первая генерация текста идет отдельным действием и не ломает запись

### Phase 1 — Transcript domain refactor
Цель: выделить транскрипт как отдельную доменную сущность.

Задачи:
- ввести явные сущности `raw/normalized/clean transcript`
- вынести построение транскриптов в отдельный service/API
- переименовать UI блоки (`Транскрипты` вместо legacy `Отчеты`, где это про текст)
- сохранить обратную совместимость с legacy endpoints на переходный период
- добавить кэширование по `meeting_id + audio hash + transcript variant + stt config`

Критерий готовности:
- транскрипт можно сгенерировать/пересобрать независимо от LLM-аналитики
- legacy и новые пути дают эквивалентный результат

### Phase 2 — LLM Artifacts platform (template + custom)
Цель: сделать универсальный слой генерации артефактов из транскрипта.

Задачи:
- `LLM Artifact API` (`generate/get/download`)
- шаблонные режимы (`summary`, `scorecard`, `brief`, `structured table`)
- `custom prompt` режим
- поддержка `schema-guided` JSON output
- валидация и кэш артефактов (`transcript hash + model + prompt/schema`)
- экспорт `JSON/CSV/TXT`, затем `XLSX`

Критерий готовности:
- пользователь может получить любой нужный формат данных без правки кода
- ошибки LLM не ломают запись и базовый транскрипт

### Phase 3 — Full RAG indexing and retrieval
Цель: полноценный RAG по одному/нескольким/всем интервью.

Задачи:
- chunking транскриптов с метаданными (speaker/timecodes/meeting context)
- embeddings pipeline + vector index
- keyword/BM25 индекс (hybrid retrieval)
- retrieval API с filters и citations
- batched reindex / incremental updates
- метрики качества retrieval (hit rate / citation coverage)

Критерий готовности:
- ответы по нескольким интервью содержат цитаты и воспроизводимы
- поиск по выбранным интервью и по фильтрам работает стабильно

### Phase 4 — UI: LLM/RAG Chat + Compare Workspace
Цель: дать пользователю интерфейс для произвольных запросов и сравнений.

Задачи:
- блок `LLM / RAG` в UI
- чат по одному интервью
- чат по выбранным интервью
- compare workspace (ручной выбор встреч)
- сохранение результатов чата/таблиц
- понятные статусы стадий (indexing/retrieval/generation/export)

Критерий готовности:
- пользователь без инженера может получить таблицу/сводку/сравнение по кастомному запросу

### Phase 5 — Production hardening and rollout
Цель: довести систему до управляемого production-сценария.

Задачи:
- observability (метрики, structured logs, tracing ключевых стадий)
- очереди/фоновые задачи для тяжелых операций (STT/LLM/RAG indexing)
- ретраи, таймауты, idempotency
- контроль стоимости/латентности LLM
- RBAC/auth/audit (если multi-user deployment)
- backup/retention policy
- релизный процесс и rollback
- нагрузочные и регрессионные тесты на representative dataset

Критерий готовности:
- predictable SLA на запись/транскрипт/артефакты
- наблюдаемость и воспроизводимость инцидентов
- безопасный rollout обновлений

## Метрики качества (что нужно мерить по новому вектору)
### Capture/Audio
- `% успешной финализации MP3`
- время `Stop -> MP3 ready`
- частота fallback-путей (`backup_audio`, `source_upload`, chunk fallback)

### Transcript
- время `MP3 -> raw transcript`
- время `raw -> normalized -> clean`
- покрытие/длина транскрипта
- доля пустых/низкокачественных транскриптов

### LLM Artifacts
- latency по шаблонам/кастомным запросам
- процент валидных JSON outputs
- доля повторных запросов, обслуженных из кэша

### RAG
- retrieval latency
- citation coverage
- precision@k / recall@k на тестовых сценариях
- качество multi-interview compare (ручная оценка + regression set)

## Ограничения и принципы безопасности
- `raw transcript` должен сохраняться как исходник для верификации
- `clean transcript` и LLM-артефакты не должны тихо подменять смысл без возможности проверить источник
- RAG-ответы должны отдавать цитаты/фрагменты
- отсутствие LLM не должно блокировать запись и базовый транскрипт

## Прод-конфигурация (минимум)
```bash
APP_ENV=prod
AUTH_MODE=api_key
API_KEYS=<user_keys>
SERVICE_API_KEYS=<service_keys>
RECORDS_DIR=/var/lib/9second_capture/records
```

## Техническая структура проекта (текущая)
- `apps/api_gateway` — API + WebSocket + встроенный UI
- `src/interview_analytics_agent` — STT/LLM, постобработка, storage, quick record, сервисы артефактов
- `scripts/launcher.py` — desktop launcher
- `scripts/run_local_agent.py` — инженерный запуск сервиса без упаковки
- `tools/packaging` — сборка desktop-бинарников

## Что считать успехом этого вектора
Пользователь записывает интервью любым способом, получает надежный MP3, отдельно строит нужный вариант транскрипта, а затем через LLM/RAG превращает его в любой полезный формат (таблица, сводка, сравнение, чат с цитатами) без ручной доработки кода под каждый новый запрос.
