# План интеграции RAG в LLM-чат и сравнение интервью

Дата: 2026-03-05
Владелец: команда 9second_capture
Стратегия: сначала MVP+, затем Production+

## 1. Цель

Сделать единый контур, где:
1. Пользователь задает вопрос в LLM-чате.
2. Система ищет релевантные фрагменты по транскриптам через RAG.
3. Ответ формируется с обязательными цитатами.
4. Сразу сохраняются файлы результата, включая top_k фрагменты.
5. Для серии собеседований доступна сравнительная аналитика по интервьюерам.

## 2. Что уже есть в проекте

1. Embeddings и fallback hashing уже реализованы.
2. Индексация и запросы RAG уже есть в API:
- `POST /v1/meetings/{meeting_id}/rag/index`
- `POST /v1/rag/query`
- `GET /v1/meetings/compare`
3. В UI есть LLM-чат по файлам и отдельные состояния для RAG/compare.

Итог: базовый фундамент готов, нужно довести продуктовый сценарий до конца и зафиксировать качество.

## 3. Целевой пользовательский поток

1. Пользователь выбирает интервью (одно или набор).
2. Пользователь задает вопрос в чате.
3. Система:
- проверяет индекс;
- при необходимости индексирует;
- делает retrieval top_k;
- формирует ответ с цитатами `[n]`.
4. В блоке "Файлы результата" автоматически появляются:
- `rag_answer_<timestamp>.txt`
- `rag_hits_topk_<timestamp>.csv`
- `rag_hits_topk_<timestamp>.json`

## 4. MVP+ (первый релиз)

Срок: 2-4 дня

### 4.1 UI задачи

1. В LLM-чате добавить переключатель режима источника ответа:
- `Files only`
- `RAG`
2. Для режима `RAG` добавить контролы:
- выбор набора интервью (meeting_ids);
- `top_k`;
- `auto_index`;
- `force_reindex`;
- `answer_with_citations`.
3. В истории ответа показывать:
- итоговый текст;
- список цитат с метаданными (meeting_id, интервьюер, строки/время, score).
4. После ответа показывать ссылки на 3 файла результата.

### 4.2 Backend задачи

1. Для `RAG` режима в чате использовать `POST /v1/rag/query` вместо прямой генерации по `input_text`.
2. Добавить endpoint сохранения файлов результата RAG-запроса:
- `POST /v1/rag/query/export` (или автоэкспорт внутри текущего rag-query обработчика).
3. Зафиксировать формат `top_k` JSON/CSV/TXT.
4. В `RAGQueryResponse` добавить поля для устойчивого экспорта:
- `request_id`
- `generated_at`
- `index_version`
- `vector_provider`
- `embedding_model`

### 4.3 Форматы файлов MVP+

1. `rag_answer_<ts>.txt`
- вопрос;
- ответ;
- список цитат `[n]`.

2. `rag_hits_topk_<ts>.csv`
- `rank`
- `score`
- `keyword_score`
- `semantic_score`
- `meeting_id`
- `candidate_name`
- `interviewer`
- `line_start`
- `line_end`
- `timestamp_start`
- `timestamp_end`
- `text`

3. `rag_hits_topk_<ts>.json`
- `query`
- `meeting_ids`
- `top_k`
- `retrieval_mode`
- `hits[]`
- `warnings[]`
- `llm_used`

### 4.4 Критерии готовности MVP+

1. RAG-режим доступен из того же LLM-чата.
2. Ответы всегда возвращают citations-блок или явный `no_hits`.
3. После успешного запроса создаются 3 файла результата.
4. На длинных транскриптах нет блокирующих падений.
5. Есть unit/integration тесты на RAG-чат и экспорт файлов.

## 5. Production+ (второй релиз)

Срок: 7-14 дней после MVP+

### 5.1 Качество retrieval

1. Добавить reranker поверх top_k кандидатов.
2. Добавить retrieval-метрики:
- `Recall@K`
- `MRR`
- `nDCG@K`
3. Создать эталонный набор контрольных вопросов и ожидаемых цитат.

### 5.2 Качество генерации

1. Ввести метрики качества ответа:
- `citation_coverage` (доля утверждений со ссылками);
- `unsupported_claim_rate` (утверждения без опоры на цитаты);
- `hallucination_rate`.
2. Добавить post-check ответа:
- если нет ссылок `[n]`, маркировать результат как `low_confidence`.

### 5.3 Сравнение интервьюеров

1. Добавить отдельный compare-режим по интервьюерам:
- агрегирование по полю `interviewer`;
- темы, риски, стиль вопросов, последовательность оценки.
2. Добавить сравнительные выходы:
- `compare_interviewers_<ts>.json`
- `compare_interviewers_<ts>.csv`
- `compare_interviewers_<ts>.txt`.
3. Добавить фильтры:
- vacancy;
- level;
- период дат;
- минимальная полнота данных.

### 5.4 Наблюдаемость и эксплуатация

1. Метрики производительности:
- `rag_index_latency_ms`
- `rag_query_latency_ms`
- `rag_llm_latency_ms`
2. Метрики надежности:
- `rag_query_errors_total`
- `rag_no_hits_total`
- `rag_export_errors_total`
3. Метрики полезности:
- `rag_citation_coverage_avg`
- `rag_answer_quality_score_avg`.

## 6. Детализация по спринтам

## Спринт A (MVP+, 2-4 дня)

1. UI переключатель `Files only | RAG`.
2. UI параметры RAG (`top_k`, `auto_index`, `force_reindex`, набор интервью).
3. Подключение чата к `/v1/rag/query`.
4. Автоформирование и сохранение 3 файлов результата.
5. Unit tests + smoke чек ручного сценария.

Deliverables:
- работающий RAG-чат в текущей вкладке LLM;
- экспорт top_k файлов;
- документация по новому сценарию.

## Спринт B (Production+, 5-10 дней)

1. Reranker и улучшенный ranking pipeline.
2. Метрики retrieval/generation.
3. Compare по интервьюерам с экспортом.
4. Регрессионный набор кейсов качества.

Deliverables:
- стабильное качество цитат;
- измеримое улучшение по метрикам;
- готовый compare-режим для руководителей.

## 7. Изменения по коду (минимальный список)

1. Frontend:
- `apps/api_gateway/ui/index.html`
- `apps/api_gateway/ui/app.js`
- `apps/api_gateway/ui/styles.css` (только при необходимости)

2. Backend:
- `apps/api_gateway/routers/artifacts.py`
- `src/interview_analytics_agent/rag/embeddings.py`
- при необходимости новый модуль ранжирования в `src/interview_analytics_agent/rag/`

3. Tests:
- `tests/unit/test_artifacts_compare_router.py`
- новые тесты для RAG query/export и citation rules.

## 8. Риски и как страхуемся

1. Риск: LLM недоступна или медленная.
- Мера: возвращать retrieval-результат без генерации и сохранять top_k файлы.

2. Риск: плохой транскрипт -> плохой RAG.
- Мера: предупреждение о качестве источника + выбор `clean` по умолчанию.

3. Риск: длинные встречи и долгий ответ.
- Мера: лимиты `top_k`, chunking, асинхронный экспорт файлов.

## 9. Definition of Done

1. Пользователь из LLM-чата получает RAG-ответ с цитатами и файлами top_k.
2. Сравнение между интервьюерами формируется на основе нескольких интервью.
3. Качество контролируется метриками и тестами, а не только ручной оценкой.
4. Поведение предсказуемо при недоступности LLM/embeddings.

