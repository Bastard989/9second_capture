# 9second_capture

`9second_capture` — локальный агент для записи интервью в `MP3`, построения транскриптов (`raw / normalized / clean`), генерации LLM-артефактов и RAG-поиска/сравнения по интервью.

Проект переведен на `transcript-first` архитектуру:

1. Захват (4 режима) -> `meeting_audio.mp3`
2. `STT` -> `raw transcript`
3. Deterministic cleaner -> `normalized transcript`
4. Опциональный `LLM cleaner` -> `clean transcript`
5. `LLM` строит артефакты из текста (таблицы/JSON/summary/custom)
6. `RAG` ищет и сравнивает интервью по чанкам транскриптов

Ключевой принцип: `Stop` должен завершать запись и финализацию `MP3`, а тяжелые `STT/LLM` выполняются по запросу в блоке `Результаты`.

## Что делает агент сейчас (актуально)

### 1) Захват и MP3-first
- Поддерживает 4 сценария получения записи (в UI):
  - `Драйвер: системный звук`
  - `Браузер: экран + звук`
  - `API: подключение к встрече`
  - `Quick fallback (по ссылке)`
- Во всех сценариях целевой артефакт записи: `meeting_audio.mp3`
- `Stop` не ждет финальный `STT/LLM` (тяжелая обработка вынесена в on-demand генерацию)

### 2) Транскрипты (новая логика)
- `raw transcript` — прямой STT-результат (грязный текст)
- `normalized transcript` — служебная deterministic-нормализация без LLM
- `clean transcript` — пользовательский чистый текст (normalizer + опциональная LLM-очистка)

Важно:
- Пользовательский сценарий обычно опирается на 2 вида текста: `raw` и `clean`
- `normalized` нужен как внутренний стабильный слой и fallback

### 3) LLM-артефакты (из транскрипта)
- Универсальный backend API для генерации артефактов из `raw|normalized|clean`
- Режимы:
  - `template`
  - `custom`
  - `table`
- Поддержка `schema-guided JSON`
- Скачивание результата в `json/txt/csv`

### 4) RAG (поиск/сравнение интервью)
- Индексация транскрипта чанками с цитатами и таймкодами
- Multi-meeting query (по выбранным интервью или по recent)
- RAG chat / compare workspace в UI
- Hybrid retrieval:
  - keyword/BM25-lite
  - vector score
- Сейчас vector layer поддерживает:
  - `Ollama/OpenAI-compatible embeddings` (предпочтительно)
  - `hashing fallback` (локально, офлайн, бесплатно)

## Терминология (фиксируем)

Чтобы не путаться в слове «отчет», используем такие термины:

- `Audio artifact` — итоговый `meeting_audio.mp3`
- `Raw transcript` — грязный STT-текст
- `Normalized transcript` — служебная deterministic-очистка без LLM
- `Clean transcript` — читабельный текст (normalizer + optional LLM)
- `LLM artifact` — любой результат из транскрипта (summary / JSON / CSV / table / custom)
- `Analysis` — аналитический артефакт (legacy alias `/report` сохранен)
- `RAG chat` — запросы/диалог по одному или нескольким интервью с цитатами

## Почему `normalized` нужен, если пользователю важны только `raw` и `clean`

`normalized` — это не “третий пользовательский отчет”. Это технический слой, который:
- удаляет `эээ / ммм / ну` и часть шумовых вставок по правилам
- схлопывает повторы
- нормализует пробелы/пунктуацию
- не зависит от LLM
- не меняет смысл

Зачем это нужно:
- стабильная база для `clean`
- fallback, если LLM недоступна
- часто улучшает RAG-поиск (меньше шумовых слов)

## Ollama в проекте (новая роль)

Проект теперь умеет работать с **двумя разными моделями Ollama**:

1. `LLM модель` (текстовая)
- используется для:
  - `clean transcript` (опциональная LLM-очистка)
  - `analysis`
  - `LLM artifacts` (`template/custom/table`)
  - `RAG answer` (ответ по найденным цитатам)

2. `Embeddings модель`
- используется для:
  - векторизации чанков транскриптов в `RAG`
  - семантического поиска и сравнения интервью

### Почему лучше 2 модели, а не одна
- embeddings-модель обычно легче и быстрее
- поиск не грузит большую LLM на каждый запрос
- качество retrieval по смыслу выше и стабильнее

### Что происходит, если embeddings-модель не установлена
Ничего не ломается:
- `RAG` продолжает работать через `hashing fallback` (локально)
- качество semantic retrieval может быть ниже
- keyword/BM25-lite retrieval остается рабочим

## Установка для пользователя (desktop app)

### Что нужно поставить
- `ffmpeg` (рекомендуется обязательно)
- `Ollama` (если хотите LLM и качественный vector RAG локально)

### Рекомендуемый быстрый путь (launcher)
1. Откройте `9second_capture.app`
2. На стартовом экране (мастер установки) заполните модели:
   - `LLM модель` (например `llama3.1:8b`)
   - `Embeddings модель` (например `nomic-embed-text`)
3. Нажмите `Исправить в 1 клик`
4. Дождитесь, пока мастер:
   - установит STT зависимости
   - проверит `Ollama CLI`
   - запустит `Ollama`
   - скачает обе модели (если их нет)
   - сохранит runtime-настройки агента
5. Нажмите `Открыть UI агента`

### Что проверяет стартовый экран (launcher preflight)
- `Python venv`
- `STT зависимости`
- `Ollama CLI`
- `Ollama сервис`
- `LLM модель` (наличие)
- `Embeddings модель` (наличие)
- браузерные разрешения (микрофон / экран)

## Подробная установка Ollama и моделей (вручную)

### macOS
```bash
brew install ffmpeg
brew install --cask ollama
open -a Ollama
```

### Проверка Ollama
```bash
ollama list
```

### Скачать 2 модели (обязательно для полной локальной схемы)
```bash
# LLM (пример)
ollama pull llama3.1:8b

# Embeddings (пример, рекомендуется)
ollama pull nomic-embed-text
```

### Альтернативные embeddings-модели (если хотите попробовать)
```bash
ollama pull mxbai-embed-large
# или
ollama pull all-minilm
```

### Что выбрать по умолчанию
- `LLM`: `llama3.1:8b` (комфортный старт локально)
- `Embeddings`: `nomic-embed-text`

## Главный UI (что теперь есть)

### Блок «Результаты»
1. `Raw / Clean` экспорт (и legacy совместимые кнопки)
2. `LLM-экспорт / кастомные форматы`
   - выбор записи
   - выбор источника транскрипта (`raw / normalized / clean`)
   - режимы `template / custom / table`
   - `prompt`
   - optional `schema JSON`
3. `RAG chat / compare workspace`
   - выбор интервью вручную
   - query по одному/нескольким интервью
   - citations с линиями/таймкодами/спикерами
   - экспорт RAG результата (`JSON / CSV citations / TXT answer`)

### Выбор моделей в главном UI
В главном UI теперь есть **два селектора**:
- `LLM модель`
- `Embeddings модель`

Оба умеют:
- `Сканировать` модели из Ollama/OpenAI-compatible `/models`
- `Сменить модель` (с сохранением runtime override)

## Архитектура данных (текущая логика)

### Capture layer
- задача: получить надежный `meeting_audio.mp3`
- `Stop` завершает запись и финализирует аудио, без ожидания STT/LLM

### Transcript layer
- `STT` строит `raw`
- deterministic cleaner строит `normalized`
- optional LLM cleaner строит `clean`

### LLM Artifact layer
- вход: `raw | normalized | clean`
- выход: `analysis / table / json / csv / custom`
- поддержка кэширования по fingerprint запроса

### RAG layer
- индексирует чанки транскрипта
- хранит metadata чанков:
  - `meeting_id`
  - `speaker(s)`
  - `line_start/line_end`
  - `start_ms/end_ms`
  - `timestamp_start/timestamp_end`
  - `meeting_meta` (candidate/vacancy/level/interviewer)
- retrieval:
  - keyword/BM25-lite
  - vector (Ollama embeddings) или `hashing fallback`
- synthesis (опционально): LLM отвечает по найденным цитатам

## API (актуально)

Все маршруты ниже идут под префиксом `/v1`.

### LLM / embeddings model control
- `GET /llm/status`
- `GET /llm/models`
- `POST /llm/model`
- `GET /llm/embeddings/status`
- `GET /llm/embeddings/models`
- `POST /llm/embeddings/model`

### Diagnostics
- `GET /diagnostics/preflight`
  - включает `stt`, `llm`, `embeddings`
- `POST /diagnostics/ui-event`

### Meetings / MP3 / transcripts
- `GET /meetings`
- `POST /meetings/{meeting_id}/finish` (`MP3-first` finalize)
- `POST /meetings/{meeting_id}/transcripts/generate`
- `POST /meetings/{meeting_id}/transcripts/rebuild`
- `GET /meetings/{meeting_id}/transcripts/{variant}` (`raw|normalized|clean`, `fmt=txt|json`)

### RAG
- `POST /meetings/{meeting_id}/rag/index`
- `GET /meetings/{meeting_id}/rag/index`
- `POST /rag/query`

### LLM artifacts / analysis / compare
- `POST /meetings/{meeting_id}/artifacts/generate`
- `GET /meetings/{meeting_id}/artifacts/{artifact_id}`
- `GET /meetings/{meeting_id}/artifacts/{artifact_id}/download?fmt=json|txt|csv`
- `POST /meetings/{meeting_id}/analysis` (новый термин)
- `POST /meetings/{meeting_id}/report` (legacy alias)
- `POST /meetings/{meeting_id}/structured` (legacy endpoint)
- `POST /meetings/{meeting_id}/senior-brief`
- `GET /meetings/compare`
- `GET /meetings/compare/export`
- `GET /meetings/{meeting_id}/artifact` (legacy download multiplexer)

## Конфигурация (важные env)

### Базовое LLM / Ollama
```bash
OPENAI_API_BASE=http://127.0.0.1:11434/v1
OPENAI_API_KEY=ollama
LLM_ENABLED=true
LLM_MODEL_ID=llama3.1:8b
```

### Embeddings / RAG vector
```bash
RAG_VECTOR_ENABLED=true
RAG_EMBEDDING_PROVIDER=auto
EMBEDDING_MODEL_ID=nomic-embed-text
# optional (если хотите отдельный endpoint для embeddings)
# EMBEDDING_API_BASE=http://127.0.0.1:11434/v1
# EMBEDDING_API_KEY=ollama
```

`RAG_EMBEDDING_PROVIDER`:
- `auto` (рекомендуется): пытается OpenAI-compatible embeddings, иначе fallback на hashing
- `openai_compat` / `ollama`: использовать embeddings API (с fallback на hashing в части сценариев)
- `hashing`: принудительно локальный hashing (офлайн)

## Разработка и запуск из исходников

### Локально
```bash
cd /Users/kirill/Documents/New\ project/9second_capture
python3 scripts/run_local_agent.py
```

### Сборка macOS app
```bash
cd /Users/kirill/Documents/New\ project/9second_capture
bash tools/packaging/build_mac.sh
open -n dist/9second_capture.app
```

## Тесты и быстрые проверки

### Python unit tests (пример)
```bash
pytest -q tests/unit/test_llm_router.py
pytest -q tests/unit/test_artifacts_compare_router.py
pytest -q tests/unit/test_enhancer.py
```

### Синтаксические проверки
```bash
python3 -m py_compile apps/api_gateway/routers/artifacts.py apps/api_gateway/routers/llm.py
node --check apps/api_gateway/ui/app.js
```

## Как мыслить новой логикой (коротко)

### Что делает `STT`
Только переводит `MP3 -> текст` (`raw transcript`).

### Что делает `normalizer`
Чистит мусор детерминированно (`raw -> normalized`) без LLM.

### Что делает `LLM`
Работает **только с транскриптом**, а не с аудио:
- `normalized -> clean` (опционально)
- `raw|normalized|clean -> artifacts / analysis / custom formats`
- `RAG citations -> answer`

## Что еще в roadmap до продакшна

1. Улучшить embeddings provider layer (батчинг, кэширование эмбеддингов, внешний provider по конфигу)
2. Полный hybrid retrieval (`BM25 + embeddings`) с более точной нормализацией/ранжированием
3. Расширить UI `compare workspace` (сохраненные наборы интервью, фильтры)
4. Production hardening (очереди, retries, observability, SLA)

## Troubleshooting

### `Stop` долго выполняется
В новой логике `Stop` должен завершать запись и финализацию `MP3` без тяжелого `STT/LLM`.
Если долго:
- проверьте `ffmpeg`
- проверьте, что зависание не в сохранении/экспорте артефактов после `Stop`
- посмотрите `agent.log` / `launcher.log`

### RAG работает, но ответы «слабые»
- вероятно используется `hashing fallback`
- проверьте `Embeddings модель` в launcher/main UI
- установите `nomic-embed-text` и пересоберите индекс (`force reindex`)

### LLM-артефакты не генерируются
- проверьте `Ollama` и `OPENAI_API_BASE`
- проверьте выбранную `LLM модель`
- посмотрите `LLM status` в главном UI

## Где хранятся локальные данные (desktop launcher)

Обычно в папке пользователя:
- `~/.9second_capture/records/` — записи и артефакты
- `~/.9second_capture/state/runtime_overrides.json` — сохраненные runtime-настройки (модели, LLM/embeddings)
- `~/.9second_capture/agent.log`
- `~/.9second_capture/launcher.log`

## Релизы
- [GitHub Releases](https://github.com/Bastard989/9second_capture/releases)
