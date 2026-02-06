# Structured Schema (CSV/JSON)

Экспорт формируется по кнопке LLM. CSV и JSON используют одинаковые поля.

## Columns

- `meeting_id`
- `source` (raw | clean)
- `meeting_title`
- `meeting_type`
- `meeting_date`
- `language`
- `source_mode`
- `segment_seq`
- `segment_start_ms`
- `segment_end_ms`
- `segment_duration_ms`
- `speaker_id`
- `speaker_name`
- `speaker_role`
- `speaker_team`
- `speaker_email`
- `addressed_to`
- `proxy_for`
- `text`
- `clean_text`
- `filler_words`
- `keywords`
- `topic`
- `topic_tags`
- `intent`
- `sentiment`
- `sentiment_score`
- `emotion`
- `question`
- `answer_summary`
- `decision`
- `decision_owner`
- `decision_deadline`
- `decision_reason`
- `action_item`
- `action_owner`
- `action_due_date`
- `action_priority`
- `action_status`
- `risk`
- `risk_severity`
- `risk_owner`
- `blocker`
- `next_step`
- `project`
- `project_code`
- `ticket_id`
- `metric_name`
- `metric_value`
- `metric_delta`
- `status`
- `confidence`
- `timestamp`

## Notes

- `proxy_for` используется если участник отвечает за отсутствующего.
- `addressed_to` используется для вопросов по имени.
- Если данных нет — поле пустое.
