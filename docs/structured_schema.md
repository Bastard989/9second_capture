# Structured Schema (CSV/JSON)

Экспорт формируется по кнопке LLM. CSV и JSON используют одинаковые поля.

## Columns

- `meeting_id`
- `source` (raw | clean)
- `segment_seq`
- `speaker_name`
- `speaker_role`
- `addressed_to`
- `proxy_for`
- `text`
- `clean_text`
- `topic`
- `intent`
- `sentiment`
- `action_item`
- `action_owner`
- `action_due_date`
- `action_priority`
- `decision`
- `decision_owner`
- `decision_deadline`
- `risk`
- `risk_severity`
- `question`
- `answer_summary`
- `filler_words`
- `keywords`
- `project`
- `metric_name`
- `metric_value`
- `timestamp`

## Notes

- `proxy_for` используется если участник отвечает за отсутствующего.
- `addressed_to` используется для вопросов по имени.
- Если данных нет — поле пустое.
