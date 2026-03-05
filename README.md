# 9second_capture

`9second_capture` — локальный агент для записи встреч, получения транскриптов и генерации отчетов через LLM.

## Для пользователей без IT-бэкграунда

Это приложение помогает после встречи быстро получить:

- аудиозапись встречи в MP3;
- текст встречи (черновой и очищенный);
- итоговые форматы для работы: таблицы, JSON, CSV, summary.

Простыми словами: вы записываете встречу, сохраняете MP3, потом по кнопке делаете текст, потом по кнопке просите LLM собрать нужный отчет.

## Как работает агент сейчас

- Во время записи строится только аудио.
- Транскрипт строится только когда вы нажимаете это вручную во вкладке `Транскрипция`.
- LLM строит форматы только когда вы нажимаете это вручную во вкладке `LLM`.

## RAG и сравнение интервью

- Во вкладке `LLM` есть два режима: `Files only` и `RAG`.
- В режиме `RAG` можно выбрать набор интервью, `top_k`, `auto_index`, `force_reindex`, и получить ответ с цитатами.
- После каждого RAG-запроса автоматически сохраняются 3 файла результата:
  - `rag_answer_<ts>.txt`
  - `rag_hits_topk_<ts>.csv`
  - `rag_hits_topk_<ts>.json`
- Для аналитики по серии интервью доступны API:
  - `GET /v1/meetings/compare/interviewers`
  - `GET /v1/meetings/compare/interviewers/export?fmt=csv|json|txt`

## Режимы работы

1. `Браузер: экран + звук`  
   Захват вкладки/экрана через `Share audio`.
2. `API/файл: загрузка аудио`  
   Работа с готовыми аудиофайлами или API-подключением.
3. `Ссылка: quick fallback`  
   Быстрый запуск записи по ссылке встречи.

## Установка из GitHub (пошагово)

1. Установите базовые инструменты:
- `git`
- `python3` (рекомендуется 3.10+)
- `ffmpeg`
- `ollama` (если планируете локальную LLM)

2. Клонируйте репозиторий:

```bash
git clone git@github.com:Bastard989/9second_capture.git
```

3. Перейдите в папку проекта:

```bash
cd "/Users/kirill/Documents/New project/9second_capture"
```

4. Создайте и активируйте виртуальное окружение:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

5. Установите зависимости:

```bash
pip install -r requirements.txt
```

6. Запустите мастер установки (рекомендуется):

```bash
python3 scripts/launcher.py
```

7. Пройдите шаги мастера и дождитесь запуска локального UI.

8. Если нужен запуск без мастера:

```bash
python3 scripts/run_local_agent.py
```

## Базовый сценарий использования

1. Выберите режим и запишите встречу (или импортируйте MP3).
2. Во вкладке `Аудио` сохраните MP3 в нужную папку.
3. Во вкладке `Транскрипция` вручную получите `Raw` и/или `Clean` TXT.
4. Во вкладке `LLM` прикрепите файлы и запросите нужный формат отчета.

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

## Что хранится в Git

- В репозиторий коммитится исходный код, тесты и документация.
- Папки сборки и локальные артефакты (`dist/`, `build/`, `*.spec`) не хранятся в Git.
