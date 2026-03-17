# 9second_capture

`9second_capture` — локальный агент для записи встреч, получения транскриптов и генерации результатов через LLM.

## Для пользователей без IT-бэкграунда

Это приложение помогает пройти путь от встречи до готового результата в несколько шагов:

- записать встречу и сохранить MP3;
- по кнопке превратить аудио в текст;
- по кнопке попросить LLM сделать таблицу, JSON, CSV, summary или другой формат;
- при необходимости искать и сравнивать уже готовые TXT-транскрипты через RAG.

Простыми словами: агент не делает всё сам без спроса. Сначала он сохраняет аудио. Потом вы сами решаете, когда строить транскрипт. Потом вы сами решаете, когда строить отчет или запускать RAG.

## Что умеет агент сейчас

- захват встречи из браузера с аудио;
- импорт MP3-файлов;
- ручная транскрибация через STT;
- ручная генерация таблиц, JSON, CSV и других форматов через LLM;
- RAG-поиск по готовым TXT-файлам;
- локальная работа без обязательной привязки к одному провайдеру.

## Универсальная модель провайдеров

Агент больше не привязан к одному стеку. У него три независимых слоя:

1. `LLM`
2. `Embeddings`
3. `STT`

Их можно настраивать отдельно.

### LLM-провайдеры

- `OpenAI-compatible`
- `OpenAI`
- `Anthropic`
- `Gemini`
- `Mock`

### Embeddings-провайдеры

- `OpenAI-compatible`
- `OpenAI`
- `Gemini`
- `Hashing local`
- `Auto`

### STT-провайдеры

- `Whisper local`
- `Google STT`
- `SaluteSpeech`
- `Mock`

## Как это устроено по логике

- Во время записи строится только аудио.
- Транскрипт строится только по ручной команде пользователя.
- LLM-результаты строятся только по ручной команде пользователя.
- RAG работает только по готовым текстовым файлам, а не по аудио.

## STT, LLM и RAG — это разные вещи

### STT

STT берет аудио и превращает его в текст.

Примеры:

- `Whisper local`
- `Google STT`
- `SaluteSpeech`

### LLM

LLM берет уже готовые файлы и по запросу пользователя строит:

- summary;
- таблицу;
- JSON;
- CSV;
- произвольный текстовый результат.

### RAG

RAG работает по готовым TXT-файлам:

- берет TXT-транскрипты;
- режет их на куски;
- ищет самые подходящие фрагменты по смыслу;
- передает найденные фрагменты в LLM;
- показывает ответ и цитаты, на которых ответ основан.

## Режимы работы

1. `Браузер: экран + звук`  
   Захват вкладки или экрана через браузерное `Share audio`.

2. `API/файл: загрузка аудио`  
   Импорт готового аудиофайла или работа через API.

3. `Ссылка: quick fallback`  
   Быстрый запуск записи по ссылке встречи.

## Установка из GitHub

### Базовые зависимости

Нужно установить:

- `git`
- `python3` (рекомендуется 3.10+)
- `ffmpeg`

Дополнительно:

- `ollama` нужен только если вы хотите локальную LLM или локальные embeddings через Ollama;
- для `Google STT` и `SaluteSpeech` отдельный локальный STT-движок не нужен.

### Шаги

1. Клонируйте репозиторий:

```bash
git clone git@github.com:Bastard989/9second_capture.git
```

2. Перейдите в папку проекта:

```bash
cd "/Users/kirill/Documents/New project/9second_capture"
```

3. Создайте и активируйте виртуальное окружение:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

4. Установите зависимости:

```bash
pip install -r requirements.txt
```

5. Запустите мастер установки:

```bash
python3 scripts/launcher.py
```

6. В мастере выберите:

- провайдер LLM;
- провайдер embeddings;
- провайдер STT;
- адреса API, ключи и модели, если это требуется вашим провайдером.

7. После сохранения настроек откройте UI агента.

## Быстрый запуск без мастера

```bash
cd "/Users/kirill/Documents/New project/9second_capture"
python3 scripts/run_local_agent.py
```

## Настройка провайдеров

### 1. Локальный сценарий

Если вы хотите полностью локальный стек:

- `LLM provider = OpenAI-compatible`
- `LLM API base = http://127.0.0.1:11434/v1`
- `LLM model = llama3.1:8b` или другая локальная chat-модель
- `Embeddings provider = OpenAI-compatible` или `Auto`
- `Embeddings model = nomic-embed-text` или другая embeddings-модель
- `STT provider = Whisper local`

### 2. Внешний LLM/Embeddings провайдер

Если ваш провайдер совместим с OpenAI API:

- укажите `API URL`
- укажите `API key`
- выберите модель

Если это нативный провайдер `OpenAI`, `Anthropic` или `Gemini`, выберите его в UI и заполните его адрес/ключ/модель.

### 3. Google STT

Для `Google STT` нужно:

- выбрать `STT provider = Google STT`;
- вставить `service account JSON`;
- при необходимости оставить стандартный `recognize URL`;
- выбрать профиль модели, например `latest_long`.

Через env это выглядит так:

```bash
GOOGLE_STT_SERVICE_ACCOUNT_JSON='<SERVICE_ACCOUNT_JSON>'
GOOGLE_STT_RECOGNIZE_URL='https://speech.googleapis.com/v1/speech:recognize'
STT_PROVIDER='google'
STT_MODEL_ID='latest_long'
```

### 4. SaluteSpeech

Для `SaluteSpeech` нужно:

- выбрать `STT provider = SaluteSpeech`;
- указать `Client ID`;
- указать `Client Secret`;
- оставить или настроить `auth URL`;
- оставить или настроить `recognize URL`;
- указать `scope`, если он отличается от стандартного.

Через env это выглядит так:

```bash
SALUTESPEECH_CLIENT_ID='<CLIENT_ID>'
SALUTESPEECH_CLIENT_SECRET='<CLIENT_SECRET>'
SALUTESPEECH_AUTH_URL='https://ngw.devices.sberbank.ru:9443/api/v2/oauth'
SALUTESPEECH_RECOGNIZE_URL='https://smartspeech.sber.ru/rest/v1/speech:recognize'
SALUTESPEECH_SCOPE='SALUTE_SPEECH_PERS'
STT_PROVIDER='salutespeech'
STT_MODEL_ID='general'
```

## Базовый сценарий использования

1. Выберите режим и получите MP3.
2. Во вкладке `Аудио` сохраните MP3.
3. Во вкладке `Транскрипция` вручную запустите нужный транскрипт.
4. Во вкладке `LLM` прикрепите файлы и запросите нужный формат результата.
5. Во вкладке `RAG` прикрепите готовые TXT-файлы и задайте вопрос по ним.

## RAG и сравнение интервью

Во вкладке `LLM` есть два режима:

- `Files only`
- `RAG`

### Files only

Вы прикрепляете файлы, а LLM делает результат напрямую по ним.

### RAG

Вы прикрепляете готовые TXT-файлы, задаете вопрос, агент:

- строит смысловой поиск;
- берет `Top-K` лучших фрагментов;
- строит ответ по найденным местам текста;
- показывает цитаты и сохраняет файлы результата.

После RAG-запроса сохраняются:

- `rag_answer_<ts>.txt`
- `rag_hits_topk_<ts>.csv`
- `rag_hits_topk_<ts>.json`

## Сборка macOS приложения

```bash
cd "/Users/kirill/Documents/New project/9second_capture"
bash tools/packaging/build_mac.sh
open -n "/Users/kirill/Documents/New project/9second_capture/dist/9second_capture.app"
```

## Тесты

```bash
cd "/Users/kirill/Documents/New project/9second_capture"
pytest -q tests/unit
```

RAG benchmark:

```bash
cd "/Users/kirill/Documents/New project/9second_capture"
python3 tools/rag_benchmark.py \
  --api-base http://127.0.0.1:8010 \
  --dataset "интеграция rag/benchmark_dataset.sample.json" \
  --source clean \
  --top-k 8
```

## Документация

- `docs/user_guide.md`
- `docs/user_guide_simple_ru.md`
- `docs/qa_checklist.md`
- `docs/troubleshooting_capture_ru.md`

## Что хранится в Git

- исходный код;
- тесты;
- документация;
- конфиги-примеры.

В Git не коммитятся локальные сборки и локальные артефакты работы агента.
