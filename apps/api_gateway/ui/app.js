const state = {
  lang: "ru",
  theme: "light",
  ws: null,
  recorder: null,
  stream: null,
  streamMode: "system",
  streamDeviceId: "",
  streamKey: "",
  screenAudioMissing: false,
  screenAudioDriverFallback: false,
  micAdded: false,
  inputStreams: [],
  audioContext: null,
  analyser: null,
  analyserSystem: null,
  analyserMic: null,
  meterNodes: [],
  meterLevels: {
    mixed: 0,
    system: 0,
    mic: 0,
  },
  meterMode: "",
  monitor: {
    systemHeard: false,
    micHeard: false,
    speechNow: false,
    lastPhraseAt: 0,
    segmentCount: 0,
    startedAt: 0,
  },
  signalSmooth: 0,
  signalState: "signal_waiting",
  mixContext: null,
  mixNodes: [],
  levelTimer: null,
  signalPeak: 0,
  seq: 0,
  meetingId: null,
  chunkCount: 0,
  countdownTimer: null,
  countdownValue: null,
  isCountingDown: false,
  stopRequested: false,
  signalCheckInProgress: false,
  isUploading: false,
  captureEngine: null,
  captureStopper: null,
  enhancedTimers: new Map(),
  resultsSource: "raw",
  driverStatusKey: "driver_unknown",
  driverStatusStyle: "muted",
  folderStatusKey: "folder_not_selected",
  folderStatusStyle: "muted",
  statusHintKey: "",
  statusHintText: "",
  statusHintStyle: "muted",
  downloadDirHandle: null,
  transcript: {
    raw: new Map(),
    enhanced: new Map(),
  },
  transcriptUiState: "waiting",
  nonEmptyRawUpdates: 0,
  pendingChunks: [],
  wsReconnectTimer: null,
  wsReconnectAttempts: 0,
  httpDrainTimer: null,
  httpDrainInProgress: false,
  backupRecorder: null,
  wsHeartbeatTimer: null,
  wsPongTimer: null,
  wsAwaitingPong: false,
  wsHasServerActivity: false,
  wsBootstrapDeadlineMs: 0,
  wsLastServerActivityMs: 0,
  lastAckSeq: -1,
  deviceStatusKey: "device_status_unknown",
  deviceStatusStyle: "muted",
  deviceStatusCount: 0,
  llmModels: [],
  llmStatusKey: "llm_status_loading",
  llmStatusStyle: "muted",
  llmStatusText: "",
  llmStatusParams: {},
  quickJobId: null,
  quickStatusKey: "quick_record_state_idle",
  quickStatusStyle: "muted",
  quickHintKey: "quick_record_hint_ready",
  quickHintText: "",
  quickHintStyle: "muted",
  quickPollTimer: null,
  compareItems: [],
  recordsMeta: new Map(),
  reportMeetingSelection: {
    raw: "",
    clean: "",
  },
  captureQuality: "balanced",
  languageProfile: "mixed",
  diagnosticsLast: null,
  workMode: "driver_audio",
  instanceId: `${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 10)}`,
  captureLockTimer: null,
};

const PREFER_PCM_CAPTURE = true;
const CHUNK_TIMESLICE_MS = 3800;
const HTTP_DRAIN_INTERVAL_MS = 1400;
const WS_HEARTBEAT_INTERVAL_MS = 12000;
const WS_PONG_TIMEOUT_MS = 25000;
const WS_BOOTSTRAP_GRACE_MS = 90000;
const MEDIA_BUSY_RETRY_DELAYS_MS = [220, 480, 900, 1600];
const SCREEN_AUDIO_RETRY_DELAYS_MS = [280, 640, 1200, 1900];
const DIAG_AUDIO_RETRY_DELAYS_MS = [220, 520, 1100];
const SIGNAL_SMOOTHING_ALPHA = 0.24;
const SIGNAL_OK_ENTER = 0.08;
const SIGNAL_OK_EXIT = 0.06;
const SIGNAL_LOW_ENTER = 0.025;
const SIGNAL_LOW_EXIT = 0.015;
const SYSTEM_STREAM_GAIN = 1.9;
const SYSTEM_STREAM_GAIN_SCREEN = 2.15;
const MIC_STREAM_GAIN = 1.12;
const DIAG_SYSTEM_MIN_LEVEL = 0.01;
const DIAG_SYSTEM_CRITICAL_MIN = 0.006;
const DIAG_MIC_MIN_LEVEL = 0.008;
const CAPTURE_LOCK_KEY = "9second_capture_active_lock";
const CAPTURE_LOCK_TTL_MS = 20000;
const CAPTURE_LOCK_HEARTBEAT_MS = 4000;
const WORK_MODE_KEY = "9second_capture_work_mode";
const QUALITY_PROFILES = {
  fast: {
    id: "fast",
    wsQualityProfile: "live_fast",
    timesliceMs: 3200,
    hintKey: "quality_fast_desc",
  },
  balanced: {
    id: "balanced",
    wsQualityProfile: "live_balanced",
    timesliceMs: 3800,
    hintKey: "quality_balanced_desc",
  },
  accurate: {
    id: "accurate",
    wsQualityProfile: "live_accurate",
    timesliceMs: 4600,
    hintKey: "quality_accurate_desc",
  },
};
const WORK_MODE_CONFIGS = {
  driver_audio: {
    id: "driver_audio",
    labelKey: "work_mode_driver",
    descriptionKey: "work_mode_desc_driver",
    supportsRealtime: true,
    supportsUpload: false,
    supportsQuick: false,
    forceCaptureMode: "system",
    useDeviceDriver: true,
    contextMode: "driver_audio",
  },
  browser_screen_audio: {
    id: "browser_screen_audio",
    labelKey: "work_mode_browser",
    descriptionKey: "work_mode_desc_browser",
    supportsRealtime: true,
    supportsUpload: false,
    supportsQuick: false,
    forceCaptureMode: "screen",
    useDeviceDriver: false,
    contextMode: "browser_screen_audio",
  },
  api_upload: {
    id: "api_upload",
    labelKey: "work_mode_api",
    descriptionKey: "work_mode_desc_api",
    supportsRealtime: false,
    supportsUpload: false,
    supportsQuick: true,
    forceCaptureMode: null,
    useDeviceDriver: false,
    contextMode: "api_upload",
  },
  link_fallback: {
    id: "link_fallback",
    labelKey: "work_mode_quick",
    descriptionKey: "work_mode_desc_quick",
    supportsRealtime: false,
    supportsUpload: false,
    supportsQuick: true,
    forceCaptureMode: null,
    useDeviceDriver: false,
    contextMode: "link_fallback",
  },
};
const VIRTUAL_DEVICE_PATTERNS = [
  "blackhole",
  "vb-cable",
  "cable input",
  "pulse",
  "monitor of",
  "loopback",
  "virtual",
];

const i18n = {
  ru: {
    subtitle: "Локальный агент записи встреч",
    theme_label: "Тема",
    theme_light: "Светлая",
    theme_dark: "Тёмная",
    work_mode_title: "Режим работы",
    help_work_mode:
      "Выберите один из 4 способов записи встречи. Активный способ включает только свои настройки.",
    help_mode_driver:
      "Запись системного звука через виртуальный драйвер (BlackHole/VB-CABLE/Monitor).",
    help_mode_browser:
      "Захват вкладки/экрана браузером. Для системного звука включайте Share audio.",
    help_mode_api:
      "Подключение к встрече через API-коннектор. Запись MP3 запускается кнопками Старт/Стоп.",
    help_mode_quick:
      "Fallback-запись по ссылке встречи, когда основной захват недоступен.",
    work_mode_hint:
      "Выберите один режим: его настройки будут активны, остальные секции станут неактивными.",
    work_mode_active_label: "Активный режим:",
    work_mode_driver: "Драйвер: системный звук",
    work_mode_browser: "Браузер: экран + звук",
    work_mode_api: "API: подключение к встрече",
    work_mode_quick: "Ссылка: quick fallback",
    work_mode_desc_driver:
      "Запись встреч в realtime через виртуальный драйвер (BlackHole/VB-CABLE/Monitor).",
    work_mode_desc_browser:
      "Запись через браузерный захват экрана и звука (Share audio в диалоге обязателен).",
    work_mode_desc_api:
      "Подключение к видеовстрече через API-коннектор и запись MP3 без локального live-транскрипта.",
    work_mode_desc_quick:
      "Fallback-режим: запись встречи по ссылке через quick recorder и опциональная отправка в агент.",
    mode_settings_title: "Настройки выбранного режима",
    mode_settings_browser_hint:
      "Для браузерного захвата выберите вкладку/экран и включите “Share audio”.",
    mode_settings_browser_hint_2:
      "Микрофон настраивается в «Запись», STT-параметры для отчётов — в «Результаты».",
    mode_settings_api_hint:
      "Укажите параметры API-подключения. Запуск и остановка записи MP3 выполняются в блоке «Запись».",
    work_mode_recording_disabled:
      "Режим записи выключен для текущего профиля. Переключитесь на «Драйвер» или «Браузер».",
    work_mode_upload_disabled:
      "Загрузка файла выключена в текущем режиме. Активируйте «API/файл».",
    work_mode_quick_disabled:
      "Quick fallback выключен в текущем режиме. Активируйте «Ссылка: quick fallback».",
    work_mode_device_disabled:
      "Настройки драйвера доступны только в режиме «Драйвер: системный звук».",
    err_work_mode_switch_locked:
      "Нельзя переключить режим во время активной записи/загрузки. Сначала остановите текущий процесс.",
    err_work_mode_realtime_only:
      "Выбранный режим не поддерживает realtime запись. Переключитесь на «Драйвер» или «Браузер».",
    err_work_mode_upload_only:
      "Прямая загрузка файла отключена в режимах захвата. Используйте «Импорт MP3» в блоке «Результаты».",
    err_work_mode_quick_only:
      "Quick fallback доступен только в режиме «Ссылка: quick fallback».",
    connection_title: "Контекст интервью",
    api_key_label: "API ключ (опционально)",
    help_api_key: "Нужен только если на локальном API включена авторизация.",
    api_key_placeholder: "X-API-Key",
    api_record_url_label: "Ссылка встречи",
    help_api_meeting_url:
      "URL встречи для API-коннектора. После старта агент пишет MP3 и отправляет данные в пайплайн.",
    api_record_url_placeholder: "https://...",
    api_record_duration_label: "Длительность (сек)",
    help_api_duration:
      "Ограничение времени API-захвата. По достижении лимита запись остановится автоматически.",
    api_record_upload_label: "Отправить запись в пайплайн агента",
    api_record_hint:
      "Нажмите «Старт» в блоке «Запись»: агент подключится к встрече и начнет запись MP3.",
    api_record_started: "API-захват запущен. Идёт запись MP3.",
    api_record_stopped: "Останавливаем API-захват...",
    api_record_completed: "API-запись завершена. MP3 доступен в блоке «Результаты».",
    api_record_failed: "Ошибка API-записи. Проверьте ссылку встречи и ключ API.",
    interview_meta_title: "Контекст интервью (опционально)",
    help_interview_meta:
      "Рекомендуется заполнить для сравнимой аналитики между интервью. Поля не обязательны.",
    meta_candidate_name: "Имя кандидата",
    meta_candidate_id: "Candidate ID",
    meta_vacancy: "Вакансия",
    meta_level: "Уровень (Junior/Middle/Senior)",
    meta_interviewer: "Интервьюер",
    interview_meta_hint:
      "Поля не обязательны, но помогают делать сравнимую аналитику между интервью.",
    llm_model_label: "LLM модель",
    help_llm:
      "LLM участвует после записи: улучшает clean-текст и формирует итоговые отчеты/таблицы.",
    llm_scan_btn: "Сканировать",
    llm_apply_btn: "Сменить модель",
    llm_status_loading: "Загружаем настройки LLM...",
    llm_status_ready: "LLM включен. Текущая модель: {model}.",
    llm_status_disabled: "LLM выключен (LLM_ENABLED=false).",
    llm_status_scanning: "Сканируем модели...",
    llm_status_scan_done: "Найдено моделей: {count}. Текущая: {model}.",
    llm_status_scan_empty: "Модели не найдены. Текущая: {model}.",
    llm_status_applied: "Модель переключена: {model}.",
    llm_status_apply_failed: "Не удалось переключить модель.",
    llm_status_unavailable:
      "LLM API недоступен. Проверьте Ollama/OPENAI_API_BASE.",
    llm_model_placeholder: "Выберите модель",
    llm_model_missing: "Сначала выберите модель.",
    device_label: "Источник аудио",
    help_device:
      "Главный источник речи собеседника. Обычно это виртуальный драйвер системного звука.",
    refresh_devices: "Обновить",
    device_hint: "Выберите виртуальный драйвер захвата системного звука.",
    device_status_unknown: "Устройства не проверены.",
    device_status_count: "Найдено аудиоисточников: {count}.",
    device_status_empty: "Аудиоисточники не найдены.",
    device_status_access_denied:
      "Нет доступа к аудиоустройствам. Разрешите доступ в браузере и обновите список.",
    driver_check: "Проверить драйвер",
    driver_help_btn: "Инструкция",
    os_mac: "macOS",
    os_windows: "Windows",
    os_linux: "Linux",
    driver_mac_1: "Установите BlackHole (2ch) и создайте Multi‑Output Device.",
    driver_mac_2: "Выход системы → Multi‑Output, вход агента → BlackHole.",
    driver_win_1: "Установите VB‑CABLE.",
    driver_win_2: "Выход системы → CABLE Input, вход агента → CABLE Output.",
    driver_linux_1: "Выберите “Monitor of …” для нужного sink в списке устройств.",
    driver_linux_2: "Если нет monitor — включите loopback в PulseAudio/PipeWire.",
    driver_unknown: "Драйвер не проверен",
    driver_checking: "Проверяем...",
    driver_ok: "Драйвер найден",
    driver_missing: "Драйвер не найден",
    recording_title: "Запись",
    status_label: "Статус:",
    status_idle: "Ожидание",
    status_countdown: "Отсчёт",
    status_recording: "Запись",
    status_uploading: "Загрузка",
    status_error: "Ошибка",
    start_btn: "Старт",
    stop_btn: "Стоп",
    capture_mode_label: "Режим захвата",
    help_capture_method:
      "Показывает текущий способ захвата. Переключается в блоке «Режим работы».",
    capture_mode_system: "Системный звук",
    capture_mode_screen: "Экран + звук",
    capture_mode_hint: "Для экрана со звуком включите “Share audio” в окне браузера.",
    capture_mode_system_note:
      "Важно: в режиме «Системный звук» микрофон добавляется автоматически, чтобы записывать и голос, и системный трек.",
    include_mic_label: "Добавлять микрофон в запись",
    help_mic:
      "Добавляет ваш микрофон, чтобы в записи были слышны вопросы интервьюера.",
    recording_stt_moved_hint:
      "STT-настройки вынесены в «Результаты»: они используются при формировании отчётов из MP3.",
    mic_input_label: "Микрофон",
    mic_input_auto: "Авто (рекомендуется)",
    language_profile_label: "Язык интервью",
    help_language_profile:
      "Подсказка для STT по языку интервью. Улучшает точность терминов и имен.",
    language_profile_mixed: "Mixed (RU + EN)",
    language_profile_ru: "Русский",
    language_profile_en: "English",
    language_profile_hint:
      "Подсказка для STT: выберите язык интервью для лучшей точности терминов.",
    quality_profile_label: "Профиль качества",
    help_quality_profile:
      "Fast — быстрее, Accurate — точнее, Balanced — оптимальный профиль по умолчанию.",
    quality_fast: "Fast",
    quality_balanced: "Balanced",
    quality_accurate: "Accurate",
    quality_fast_desc: "Минимальная задержка, ниже точность, меньше нагрузка на CPU.",
    quality_balanced_desc: "Баланс точности и задержки. Рекомендуется по умолчанию.",
    quality_accurate_desc: "Максимальная точность, выше задержка и нагрузка на CPU.",
    diag_title: "Проверка MP3-захвата перед стартом",
    help_diagnostics:
      "Опциональная проверка перед записью: доступ к аудио, уровни system/mic и готовность MP3-потока.",
    diag_run_btn: "Проверить",
    diag_hint_idle: "Запустите проверку, если есть проблемы с захватом.",
    diag_hint_running: "Диагностика выполняется...",
    diag_hint_ok: "Диагностика пройдена. Можно запускать запись.",
    diag_hint_fail: "Диагностика не пройдена. Исправьте источник/микрофон/MP3-поток.",
    diag_audio_access: "Доступ к аудио",
    diag_system_level: "Уровень system",
    diag_mic_level: "Уровень mic",
    diag_mp3_ready: "MP3 поток готов",
    diag_llm_ready: "LLM доступен",
    diag_skip_not_required: "не обязательно",
    diag_stt_warming: "прогрев модели...",
    diag_hint_levels_low:
      "Доступ есть, но уровни сейчас низкие. Можно запускать запись и проверить сигнал во время разговора.",
    meter_system_label: "System: {level}",
    meter_mic_label: "Mic: {level}",
    structured_insufficient_data: "Недостаточно данных для структурирования.",
    countdown_label: "Отсчёт:",
    recording_advanced_title: "Расширенная диагностика (опционально)",
    signal_waiting: "Сигнал: ожидание",
    signal_ok: "Сигнал: есть",
    signal_low: "Сигнал: слабый",
    signal_no_audio: "Сигнал: нет аудио",
    signal_check: "Проверить захват",
    monitor_title: "Индикатор работы записи",
    monitor_hint:
      "Показывает, слышит ли агент системный звук/микрофон и фиксирует ли аудио-сегменты в MP3.",
    monitor_system_label: "Системный звук",
    monitor_mic_label: "Микрофон",
    monitor_speech_now_label: "Речь сейчас",
    monitor_last_phrase_label: "Последний аудио-пик",
    monitor_segments_label: "Сегментов MP3",
    monitor_not_started: "не запущено",
    monitor_state_heard: "слышно",
    monitor_state_silent: "тишина",
    monitor_state_speaking: "идет речь",
    monitor_state_pause: "пауза",
    monitor_last_never: "еще не зафиксировано",
    help_live_monitor:
      "Этот блок не распознаёт текст. Он показывает именно корректность захвата аудио в MP3.",
    signal_check_running: "Проверка захвата...",
    signal_check_blocked_recording: "Проверка захвата доступна только до старта записи.",
    signal_check_ok: "Захват работает: уровень сигнала обнаружен.",
    signal_check_fail: "Захват не обнаружил аудио. Проверьте источник/Share audio.",
    signal_check_mic_only:
      "Системный источник молчит. Слышен только микрофон. Проверьте loopback/драйвер.",
    signal_check_system_only:
      "Системный источник слышен, но микрофон не добавлен. Проверьте доступ к микрофону.",
    meeting_id_label: "Meeting ID:",
    chunks_label: "Чанки:",
    transcript_title: "Транскрипт",
    raw_label: "Raw",
    clean_label: "Clean",
    raw_post: "После Стоп",
    clean_delay: "~3–4 сек",
    transcript_mode_record_first:
      "Итоговый текст строится после завершения записи для максимальной точности.",
    transcript_runtime_waiting: "Текст появится после завершения записи.",
    transcript_runtime_recording: "Идёт запись. Live-транскрипт отключён для снижения нагрузки.",
    transcript_runtime_loading: "Завершаем обработку MP3 и собираем итоговый текст...",
    transcript_runtime_ready: "Итоговый текст готов.",
    transcript_runtime_empty:
      "Запись завершена, но текста пока нет. Проверьте источник аудио и сохраните MP3 для повторной обработки.",
    transcript_empty_title: "Live-транскрипт отключен",
    transcript_empty_hint:
      "Во время записи показываются только индикаторы захвата. Итоговый текст появится после Стоп.",
    transcript_placeholder_raw_post:
      "Сырой текст появится после завершения записи (final pass по MP3).",
    transcript_placeholder_clean_post:
      "Чистый текст появится после завершения записи и финальной обработки.",
    records_title: "Результаты",
    records_refresh: "Обновить",
    records_menu_btn: "...",
    record_menu_rename: "Переименовать запись",
    record_menu_save_mp3: "Сохранить MP3",
    results_mp3_title: "1) MP3 после встречи",
    results_mp3_hint: "Выберите запись, задайте имя MP3 и сохраните файл в нужную папку.",
    results_save_mp3_btn: "Сохранить MP3",
    results_import_mp3_btn: "Импорт MP3",
    results_report_title: "2) TXT отчёт из MP3",
    results_report_hint: "Выберите тип отчёта (грязный/чистый), задайте имя и сохраните TXT.",
    results_stt_title: "Настройки STT для отчётов",
    results_report_name_placeholder: "report_clean",
    results_generate_report_btn: "Сформировать TXT",
    results_download_report_btn: "Сохранить TXT",
    results_current_report_file: "Текущий файл отчёта",
    results_convert_title: "3) Конвертация готовых отчётов",
    results_convert_hint: "Для каждого типа отчёта выберите запись и формат выгрузки.",
    results_raw_lane_title: "Грязный отчёт (Raw)",
    results_clean_lane_title: "Чистый отчёт (Clean)",
    results_raw_report_name_placeholder: "raw_report_export",
    results_clean_report_name_placeholder: "clean_report_export",
    results_export_txt: "TXT",
    results_export_json: "JSON",
    results_export_csv: "CSV",
    results_export_table_json: "Таблица JSON",
    results_export_senior: "Для сеньоров",
    compare_title: "Сравнение интервью (опционально)",
    compare_refresh: "Обновить",
    compare_hint_idle: "Этот блок нужен только для сравнения нескольких интервью между собой.",
    compare_hint_loading: "Обновляем сравнительную сводку...",
    compare_hint_empty: "Нет данных для сравнения. Проведите интервью и сгенерируйте отчёты.",
    compare_hint_failed: "Не удалось загрузить сравнение интервью.",
    compare_export_csv: "Экспорт CSV",
    compare_export_json: "Экспорт JSON",
    compare_col_candidate: "Кандидат",
    compare_col_vacancy: "Вакансия",
    compare_col_level: "Уровень",
    compare_col_score: "Score",
    compare_col_decision: "Решение",
    compare_col_quality: "Качество",
    compare_row_candidate_fallback: "Кандидат не указан",
    choose_folder: "Выбрать папку",
    folder_not_selected: "Папка не выбрана",
    folder_selected: "Папка выбрана",
    folder_not_supported: "Выбор папки недоступен",
    results_source_label: "Источник",
    file_transcript: "Файл отчёта",
    file_action_download: "Скачать",
    file_action_report: "Экспорт TXT",
    file_action_table: "Таблица",
    file_action_mp3: "MP3",
    prompt_rename_record: "Введите новое название записи:",
    prompt_save_mp3_after_stop: "Запись завершена. Укажите имя MP3 файла:",
    hint_record_renamed: "Название записи обновлено.",
    hint_mp3_saved: "MP3 сохранен.",
    hint_mp3_not_found: "MP3 пока недоступен для этой записи.",
    hint_mp3_import_started: "Загружаем MP3 в агент и строим запись...",
    hint_mp3_import_done: "MP3 импортирован. Можно формировать отчёты.",
    hint_mp3_import_failed: "Не удалось импортировать MP3 файл.",
    hint_report_generated: "TXT отчёт сформирован.",
    hint_report_source_missing: "Сначала выберите запись для отчёта.",
    hint_report_name_missing: "Укажите имя файла отчёта.",
    hint_report_missing: "Отчёт пока не найден. Сначала нажмите «Сформировать TXT».",
    report_picker_empty: "Нет записей",
    download_raw: "Скачать raw",
    download_clean: "Скачать clean",
    gen_report_raw: "Отчёт raw",
    gen_report_clean: "Отчёт clean",
    download_report_raw: "Скачать отчёт raw",
    download_report_clean: "Скачать отчёт clean",
    gen_structured_raw: "Таблицы raw",
    gen_structured_clean: "Таблицы clean",
    download_structured_raw_json: "JSON raw",
    download_structured_raw_csv: "CSV raw",
    download_structured_clean_json: "JSON clean",
    download_structured_clean_csv: "CSV clean",
    upload_title: "Загрузка конференции",
    upload_audio_label: "Аудио файл",
    help_upload_audio:
      "Загрузите готовый файл встречи. Агент построит MP3, транскрипт, отчеты и таблицы.",
    upload_audio_btn: "Загрузить аудио",
    upload_video_label: "Видео файл",
    upload_video_btn: "Видео (в разработке)",
    upload_hint: "Импортируйте MP3 в блоке «Результаты», чтобы собрать raw/clean и отчёты.",
    quick_record_title: "Quick fallback запись",
    quick_record_url_label: "Ссылка встречи",
    help_quick_url:
      "Ссылка на встречу для quick fallback-рекордера, когда обычный захват недоступен.",
    quick_record_url_placeholder: "https://...",
    quick_record_duration_label: "Длительность (сек)",
    help_quick_duration:
      "Ограничение времени quick-записи. По достижении лимита запись остановится.",
    quick_record_transcribe_label: "Сделать локальную транскрибацию",
    quick_record_upload_label: "Отправить запись в пайплайн агента",
    quick_record_start_btn: "Quick старт",
    quick_record_stop_btn: "Quick стоп",
    quick_record_state_idle: "Не запущено",
    quick_record_state_running: "Идет запись",
    quick_record_state_stopping: "Останавливаем",
    quick_record_state_completed: "Завершено",
    quick_record_state_failed: "Ошибка",
    quick_record_hint_ready: "Fallback запись готова к запуску.",
    quick_record_hint_started: "Fallback запись запущена.",
    quick_record_hint_stopped: "Fallback запись остановлена.",
    quick_record_hint_missing_url: "Укажите ссылку встречи (http/https).",
    quick_record_hint_missing_duration: "Укажите корректную длительность (>= 5 сек).",
    quick_record_hint_already_running: "Quick запись уже выполняется.",
    quick_record_hint_start_failed: "Не удалось запустить quick запись.",
    quick_record_hint_stop_failed: "Не удалось остановить quick запись.",
    quick_record_hint_failed: "Quick запись завершилась с ошибкой: {error}",
    quick_record_hint_completed: "Quick запись завершена: {path}",
    help_title: "Как настроить звук",
    help_item_1: "Установите драйвер loopback (BlackHole / VB-Cable / PulseAudio).",
    help_item_2: "macOS: BlackHole + Multi‑Output Device (колонки + BlackHole).",
    help_item_3:
      "Windows: VB‑CABLE, вывод системы → CABLE Input, вход агента → CABLE Output.",
    help_item_4: "Linux: выберите “Monitor of …” для нужного sink.",
    help_item_5: "Нажмите «Проверить захват» и убедитесь, что уровень не нулевой.",
    footer_note:
      "Данные остаются локально. Для записи требуется разрешение браузера.",
    err_media_denied:
      "Браузер не дал доступ к аудио. Разрешите микрофон/захват экрана и повторите.",
    err_media_not_found:
      "Аудиоустройство не найдено. Проверьте выбранный источник и драйвер.",
    err_media_not_readable:
      "Источник аудио занят другим приложением или недоступен.",
    warn_system_source_fallback:
      "Выбранный источник недоступен. Автоматически переключились на другой аудиовход.",
    err_capture_locked_other_tab:
      "Запись уже запущена в другом окне/вкладке. Остановите её там и повторите.",
    err_no_device_selected:
      "Не выбран источник аудио. Выберите устройство и повторите.",
    err_interview_meta_missing:
      "Поля интервью опциональны. Можно запускать запись без заполнения.",
    err_system_source_not_virtual:
      "Выбран не виртуальный системный источник. Для встреч выберите BlackHole/VB-CABLE/Monitor.",
    err_screen_audio_missing:
      "В режиме «Экран + звук» включите «Share audio» в окне выбора экрана.",
    err_server_start: "Не удалось создать встречу на локальном API.",
    err_network: "Сбой сети/локального API. Попробуйте ещё раз.",
    err_recorder_init:
      "MediaRecorder не поддерживается для текущего источника. Попробуйте другой режим.",
    err_diagnostics_failed:
      "Диагностика не пройдена. Исправьте ошибки источника/микрофона/STT и повторите.",
    err_mic_same_as_system:
      "Микрофон совпадает с системным источником. Выберите другой микрофон или режим «Авто».",
    warn_mic_not_added:
      "Микрофон не удалось добавить. Разрешите доступ к микрофону и проверьте выбранный вход.",
    warn_screen_audio_mic_only:
      "Системный звук экрана не передаётся (Share audio выключен). Записывается только микрофон.",
    warn_screen_audio_driver_fallback:
      "Share audio не передал системный звук. Используем системный трек через виртуальный драйвер.",
    warn_media_fallback_pcm:
      "MediaRecorder недоступен, переключились на PCM-захват. Нагрузка на CPU может быть выше.",
    warn_capture_stream_interrupted:
      "Один из потоков захвата остановился. Продолжаем запись доступных дорожек.",
    warn_backup_upload_failed:
      "Резервный аудиофайл не удалось отправить. Часть хвоста записи может не попасть в финальный текст.",
    err_generic: "Не удалось начать запись. Проверьте права браузера и источник аудио.",
    hint_recording_ok: "Запись запущена. Идёт захват аудио.",
    hint_recording_record_first:
      "Record-first режим: во время записи показывается только диагностика захвата. Итоговый текст появится после Стоп.",
    hint_stt_warmup:
      "Инициализация распознавания... первые фразы могут появиться с задержкой 5-20 секунд.",
    hint_no_speech_yet:
      "Пока нет распознанной речи. Проверьте источник: в «Системном звуке» звук встречи должен идти в BlackHole/VB-CABLE; в «Экран + звук» включите Share audio; для голоса убедитесь, что микрофон добавлен.",
    diag_reason_none: "Диагноз: пока данных недостаточно.",
    diag_reason_system_track_missing:
      "Диагноз: не виден системный аудио-трек. Включите loopback/виртуальный драйвер или Share audio.",
    diag_reason_mic_only:
      "Диагноз: идёт только микрофон (mic-only). Для интервью включите системный трек.",
    diag_reason_low_snr:
      "Диагноз: низкий SNR (тихо/шумно). Поднимите уровень источника и снизьте фон.",
    diag_reason_stt_warmup: "Диагноз: STT ещё прогревается, первые фразы могут запаздывать.",
    diag_reason_audio_busy:
      "Диагноз: устройство занято другим приложением. Освободите источник и запустите снова.",
  },
  en: {
    subtitle: "Local meeting capture agent",
    theme_label: "Theme",
    theme_light: "Light",
    theme_dark: "Dark",
    work_mode_title: "Work mode",
    help_work_mode:
      "Pick one of four interview capture modes. Only the active mode settings are applied.",
    help_mode_driver:
      "Capture system audio through virtual loopback driver (BlackHole/VB-CABLE/Monitor).",
    help_mode_browser:
      "Capture screen/tab via browser. Enable Share audio to include system sound.",
    help_mode_api:
      "Connect to meeting through API connector. MP3 recording starts with Start/Stop controls.",
    help_mode_quick:
      "Fallback capture by meeting URL when normal capture is not available.",
    work_mode_hint:
      "Choose one mode: only its settings stay active, other sections are dimmed and blocked.",
    work_mode_active_label: "Active mode:",
    work_mode_driver: "Driver: system audio",
    work_mode_browser: "Browser: screen + audio",
    work_mode_api: "API: meeting connector",
    work_mode_quick: "Link: quick fallback",
    work_mode_desc_driver:
      "Realtime interview capture via virtual loopback driver (BlackHole/VB-CABLE/Monitor).",
    work_mode_desc_browser:
      "Browser capture of screen + audio (Share audio must be enabled).",
    work_mode_desc_api:
      "Meeting API connector flow: record MP3 from meeting source without live transcript.",
    work_mode_desc_quick:
      "Fallback mode: capture meeting by URL via quick recorder and optionally upload to agent.",
    mode_settings_title: "Selected mode settings",
    mode_settings_browser_hint:
      "For browser capture, choose tab/screen and enable “Share audio”.",
    mode_settings_browser_hint_2:
      "Microphone is configured in Recording. STT settings for reports are in Results.",
    mode_settings_api_hint:
      "Set API connector parameters. Start/Stop in Recording controls MP3 session.",
    work_mode_recording_disabled:
      "Recording controls are disabled for this profile. Switch to Driver or Browser mode.",
    work_mode_upload_disabled:
      "File upload is disabled for this profile. Switch to API/file mode.",
    work_mode_quick_disabled:
      "Quick fallback is disabled for this profile. Switch to Link quick fallback mode.",
    work_mode_device_disabled:
      "Driver controls are available only in Driver system-audio mode.",
    err_work_mode_switch_locked:
      "Cannot switch mode during active recording/upload. Stop current flow first.",
    err_work_mode_realtime_only:
      "Selected mode does not support realtime recording. Switch to Driver or Browser.",
    err_work_mode_upload_only:
      "Direct upload mode is removed from capture panels. Use MP3 import in Results.",
    err_work_mode_quick_only:
      "Quick fallback is available only in Link quick fallback mode.",
    connection_title: "Interview context",
    api_key_label: "API key (optional)",
    help_api_key: "Needed only when authentication is enabled on local API.",
    api_key_placeholder: "X-API-Key",
    api_record_url_label: "Meeting URL",
    help_api_meeting_url:
      "Meeting link used by API connector. After start, agent records MP3 and sends it to pipeline.",
    api_record_url_placeholder: "https://...",
    api_record_duration_label: "Duration (sec)",
    help_api_duration:
      "Maximum API capture duration. Recording auto-stops when limit is reached.",
    api_record_upload_label: "Upload recording to agent pipeline",
    api_record_hint:
      "Press Start in Recording: agent connects by API and starts MP3 recording.",
    api_record_started: "API capture started. MP3 recording is in progress.",
    api_record_stopped: "Stopping API capture...",
    api_record_completed: "API recording completed. MP3 is available in Results.",
    api_record_failed: "API recording failed. Check meeting URL and API key.",
    interview_meta_title: "Interview context (optional)",
    help_interview_meta:
      "Recommended for comparable analytics across interviews, but not required to start.",
    meta_candidate_name: "Candidate name",
    meta_candidate_id: "Candidate ID",
    meta_vacancy: "Vacancy",
    meta_level: "Level (Junior/Middle/Senior)",
    meta_interviewer: "Interviewer",
    interview_meta_hint:
      "Fields are optional, but they improve comparability between interviews.",
    llm_model_label: "LLM model",
    help_llm:
      "LLM is used after recording to improve clean transcript and generate reports/tables.",
    llm_scan_btn: "Scan",
    llm_apply_btn: "Switch model",
    llm_status_loading: "Loading LLM settings...",
    llm_status_ready: "LLM enabled. Current model: {model}.",
    llm_status_disabled: "LLM is disabled (LLM_ENABLED=false).",
    llm_status_scanning: "Scanning models...",
    llm_status_scan_done: "Models found: {count}. Current: {model}.",
    llm_status_scan_empty: "No models found. Current: {model}.",
    llm_status_applied: "Model switched: {model}.",
    llm_status_apply_failed: "Failed to switch model.",
    llm_status_unavailable:
      "LLM API is unavailable. Check Ollama/OPENAI_API_BASE.",
    llm_model_placeholder: "Select model",
    llm_model_missing: "Select a model first.",
    device_label: "Audio source",
    help_device:
      "Primary interviewee speech source. Typically this is a virtual system loopback input.",
    refresh_devices: "Refresh",
    device_hint: "Select the virtual driver that captures system audio.",
    device_status_unknown: "Audio devices are not checked yet.",
    device_status_count: "Audio sources found: {count}.",
    device_status_empty: "No audio sources found.",
    device_status_access_denied:
      "Audio device access is denied. Allow browser permissions and refresh the list.",
    driver_check: "Check driver",
    driver_help_btn: "Instructions",
    os_mac: "macOS",
    os_windows: "Windows",
    os_linux: "Linux",
    driver_mac_1: "Install BlackHole (2ch) and create a Multi‑Output Device.",
    driver_mac_2: "System output → Multi‑Output, agent input → BlackHole.",
    driver_win_1: "Install VB‑CABLE.",
    driver_win_2: "System output → CABLE Input, agent input → CABLE Output.",
    driver_linux_1: "Choose “Monitor of …” for the target sink in devices list.",
    driver_linux_2: "If no monitor exists, enable loopback in PulseAudio/PipeWire.",
    driver_unknown: "Driver not checked",
    driver_checking: "Checking...",
    driver_ok: "Driver found",
    driver_missing: "Driver not found",
    recording_title: "Recording",
    status_label: "Status:",
    status_idle: "Idle",
    status_countdown: "Countdown",
    status_recording: "Recording",
    status_uploading: "Uploading",
    status_error: "Error",
    start_btn: "Start",
    stop_btn: "Stop",
    capture_mode_label: "Capture mode",
    help_capture_method:
      "Shows currently active capture method. Switch mode in the Work mode section.",
    capture_mode_system: "System audio",
    capture_mode_screen: "Screen + audio",
    capture_mode_hint: "For screen + audio enable “Share audio” in the browser dialog.",
    capture_mode_system_note:
      "Important: in “System audio” mode microphone is added automatically to capture both voice and system track.",
    include_mic_label: "Include microphone in recording",
    help_mic:
      "Adds interviewer microphone so questions/comments are also present in recording.",
    recording_stt_moved_hint:
      "STT settings were moved to Results and are used for report generation from MP3.",
    mic_input_label: "Microphone",
    mic_input_auto: "Auto (recommended)",
    language_profile_label: "Interview language",
    help_language_profile:
      "STT language hint. Correct choice improves recognition of terms and names.",
    language_profile_mixed: "Mixed (RU + EN)",
    language_profile_ru: "Russian",
    language_profile_en: "English",
    language_profile_hint: "STT hint: choose interview language for better term accuracy.",
    quality_profile_label: "Quality profile",
    help_quality_profile:
      "Fast = lighter/faster, Accurate = better quality/higher load, Balanced = default.",
    quality_fast: "Fast",
    quality_balanced: "Balanced",
    quality_accurate: "Accurate",
    quality_fast_desc: "Lowest latency, lower accuracy, minimal CPU usage.",
    quality_balanced_desc: "Balanced accuracy and latency (recommended).",
    quality_accurate_desc: "Highest accuracy with higher latency and CPU load.",
    diag_title: "MP3 capture preflight checks",
    help_diagnostics:
      "Optional preflight: audio access, system/mic levels, and MP3 stream readiness.",
    diag_run_btn: "Run checks",
    diag_hint_idle: "Run this check only if you suspect capture issues.",
    diag_hint_running: "Running diagnostics...",
    diag_hint_ok: "Diagnostics passed. Recording can be started.",
    diag_hint_fail: "Diagnostics failed. Fix source/microphone/MP3 stream before recording.",
    diag_audio_access: "Audio access",
    diag_system_level: "System level",
    diag_mic_level: "Mic level",
    diag_mp3_ready: "MP3 stream ready",
    diag_llm_ready: "LLM ready",
    diag_skip_not_required: "not required",
    diag_stt_warming: "model warmup...",
    diag_hint_levels_low:
      "Access is fine, but levels are currently low. You can still start and verify levels while speaking.",
    meter_system_label: "System: {level}",
    meter_mic_label: "Mic: {level}",
    structured_insufficient_data: "Insufficient data for structured export.",
    countdown_label: "Countdown:",
    recording_advanced_title: "Advanced diagnostics (optional)",
    signal_waiting: "Signal: waiting",
    signal_ok: "Signal: ok",
    signal_low: "Signal: low",
    signal_no_audio: "Signal: no audio",
    signal_check: "Check capture",
    monitor_title: "Recording health monitor",
    monitor_hint:
      "Simple status for MP3 recording health: system/mic audibility and audio segment activity.",
    monitor_system_label: "System audio",
    monitor_mic_label: "Microphone",
    monitor_speech_now_label: "Speech now",
    monitor_last_phrase_label: "Last audio peak",
    monitor_segments_label: "MP3 segments",
    monitor_not_started: "not started",
    monitor_state_heard: "heard",
    monitor_state_silent: "silent",
    monitor_state_speaking: "speaking",
    monitor_state_pause: "pause",
    monitor_last_never: "not detected yet",
    help_live_monitor:
      "This block does not transcribe text. It confirms MP3 capture health only.",
    signal_check_running: "Checking capture...",
    signal_check_blocked_recording: "Capture check is available only before recording starts.",
    signal_check_ok: "Capture is working: audio level detected.",
    signal_check_fail: "No audio detected. Check source/Share audio.",
    signal_check_mic_only:
      "System source is silent. Only microphone is audible. Check loopback/driver.",
    signal_check_system_only:
      "System source is audible, but microphone is missing. Check microphone permission.",
    meeting_id_label: "Meeting ID:",
    chunks_label: "Chunks:",
    transcript_title: "Transcript",
    raw_label: "Raw",
    clean_label: "Clean",
    raw_post: "Post-stop",
    clean_delay: "~3–4s",
    transcript_mode_record_first:
      "Final transcript is built after recording ends for maximum accuracy.",
    transcript_runtime_waiting: "Transcript will appear after recording stops.",
    transcript_runtime_recording: "Recording in progress. Live transcript is disabled to reduce load.",
    transcript_runtime_loading: "Finalizing MP3 and building final transcript...",
    transcript_runtime_ready: "Final transcript is ready.",
    transcript_runtime_empty:
      "Recording is finished, but transcript is still empty. Check audio source and save MP3 for reprocessing.",
    transcript_empty_title: "Live transcript is disabled",
    transcript_empty_hint:
      "During recording, only capture health indicators are shown. Final transcript appears after Stop.",
    transcript_placeholder_raw_post:
      "Raw text appears after recording stops (final pass from MP3).",
    transcript_placeholder_clean_post:
      "Clean text appears after recording stops and final processing is complete.",
    records_title: "Results",
    records_refresh: "Refresh",
    records_menu_btn: "...",
    record_menu_rename: "Rename recording",
    record_menu_save_mp3: "Save MP3",
    results_mp3_title: "1) MP3 after meeting",
    results_mp3_hint: "Pick a record, set MP3 name, and save it to your folder.",
    results_save_mp3_btn: "Save MP3",
    results_import_mp3_btn: "Import MP3",
    results_report_title: "2) TXT report from MP3",
    results_report_hint: "Choose report type (raw/clean), set file name, and save TXT.",
    results_stt_title: "STT settings for reports",
    results_report_name_placeholder: "report_clean",
    results_generate_report_btn: "Build TXT",
    results_download_report_btn: "Save TXT",
    results_current_report_file: "Current report file",
    results_convert_title: "3) Convert ready reports",
    results_convert_hint: "For each report type choose a record and export format.",
    results_raw_lane_title: "Raw report lane",
    results_clean_lane_title: "Clean report lane",
    results_raw_report_name_placeholder: "raw_report_export",
    results_clean_report_name_placeholder: "clean_report_export",
    results_export_txt: "TXT",
    results_export_json: "JSON",
    results_export_csv: "CSV",
    results_export_table_json: "Table JSON",
    results_export_senior: "Senior brief",
    compare_title: "Interview comparison (optional)",
    compare_refresh: "Refresh",
    compare_hint_idle: "Use this block only when comparing multiple interviews.",
    compare_hint_loading: "Loading comparison summary...",
    compare_hint_empty: "No comparable data yet. Run interviews and generate reports.",
    compare_hint_failed: "Failed to load interview comparison.",
    compare_export_csv: "Export CSV",
    compare_export_json: "Export JSON",
    compare_col_candidate: "Candidate",
    compare_col_vacancy: "Vacancy",
    compare_col_level: "Level",
    compare_col_score: "Score",
    compare_col_decision: "Decision",
    compare_col_quality: "Quality",
    compare_row_candidate_fallback: "Candidate not set",
    choose_folder: "Choose folder",
    folder_not_selected: "Folder not selected",
    folder_selected: "Folder selected",
    folder_not_supported: "Folder chooser not supported",
    results_source_label: "Source",
    file_transcript: "Report file",
    file_action_download: "Download",
    file_action_report: "Export TXT",
    file_action_table: "Table",
    file_action_mp3: "MP3",
    prompt_rename_record: "Enter new recording name:",
    prompt_save_mp3_after_stop: "Recording is finished. Enter MP3 file name:",
    hint_record_renamed: "Recording name updated.",
    hint_mp3_saved: "MP3 saved.",
    hint_mp3_not_found: "MP3 is not available for this recording yet.",
    hint_mp3_import_started: "Importing MP3 and creating record...",
    hint_mp3_import_done: "MP3 imported. You can build reports now.",
    hint_mp3_import_failed: "Failed to import MP3 file.",
    hint_report_generated: "TXT report generated.",
    hint_report_source_missing: "Select a record for report generation.",
    hint_report_name_missing: "Set report filename.",
    hint_report_missing: "Report not found yet. Generate TXT first.",
    report_picker_empty: "No records",
    download_raw: "Download raw",
    download_clean: "Download clean",
    gen_report_raw: "Report raw",
    gen_report_clean: "Report clean",
    download_report_raw: "Download report raw",
    download_report_clean: "Download report clean",
    gen_structured_clean: "Tables clean",
    download_structured_raw_json: "JSON raw",
    download_structured_raw_csv: "CSV raw",
    download_structured_clean_json: "JSON clean",
    download_structured_clean_csv: "CSV clean",
    upload_title: "Conference upload",
    upload_audio_label: "Audio file",
    help_upload_audio:
      "Upload a ready interview file. Agent will build MP3, transcript, reports, and tables.",
    upload_audio_btn: "Upload audio",
    upload_video_label: "Video file",
    upload_video_btn: "Video (in development)",
    upload_hint: "Use MP3 import in Results to generate raw/clean and reports.",
    quick_record_title: "Quick fallback capture",
    quick_record_url_label: "Meeting URL",
    help_quick_url:
      "Meeting URL for quick fallback recorder when regular capture path is unavailable.",
    quick_record_url_placeholder: "https://...",
    quick_record_duration_label: "Duration (sec)",
    help_quick_duration:
      "Maximum quick-record duration. Recording auto-stops when limit is reached.",
    quick_record_transcribe_label: "Run local transcription",
    quick_record_upload_label: "Upload recording to agent pipeline",
    quick_record_start_btn: "Quick start",
    quick_record_stop_btn: "Quick stop",
    quick_record_state_idle: "Idle",
    quick_record_state_running: "Recording",
    quick_record_state_stopping: "Stopping",
    quick_record_state_completed: "Completed",
    quick_record_state_failed: "Failed",
    quick_record_hint_ready: "Fallback recorder is ready.",
    quick_record_hint_started: "Fallback recording started.",
    quick_record_hint_stopped: "Fallback recording stop requested.",
    quick_record_hint_missing_url: "Provide meeting URL (http/https).",
    quick_record_hint_missing_duration: "Provide valid duration (>= 5 sec).",
    quick_record_hint_already_running: "Quick recorder is already running.",
    quick_record_hint_start_failed: "Failed to start quick recorder.",
    quick_record_hint_stop_failed: "Failed to stop quick recorder.",
    quick_record_hint_failed: "Quick recorder failed: {error}",
    quick_record_hint_completed: "Quick recording completed: {path}",
    help_title: "Audio setup",
    help_item_1: "Install a loopback driver (BlackHole / VB-Cable / PulseAudio).",
    help_item_2: "macOS: BlackHole + Multi‑Output Device (speakers + BlackHole).",
    help_item_3:
      "Windows: VB‑CABLE, system output → CABLE Input, agent input → CABLE Output.",
    help_item_4: "Linux: choose “Monitor of …” for the sink.",
    help_item_5: "Click “Check capture” and confirm the level is not zero.",
    footer_note: "Data stays local. Browser permission is required to record.",
    err_media_denied:
      "Browser denied audio access. Allow microphone/screen capture and retry.",
    err_media_not_found: "Audio device not found. Check selected source and driver.",
    err_media_not_readable: "Audio source is busy or unavailable.",
    warn_system_source_fallback:
      "Selected source is unavailable. Switched automatically to another audio input.",
    err_capture_locked_other_tab:
      "Recording is already running in another tab/window. Stop it there and retry.",
    err_no_device_selected:
      "Audio source is not selected. Choose a device and retry.",
    err_interview_meta_missing:
      "Interview fields are optional. Recording can start with empty fields.",
    err_system_source_not_virtual:
      "Selected source is not a virtual system input. Choose BlackHole/VB-CABLE/Monitor for meetings.",
    err_screen_audio_missing:
      "In “Screen + audio” mode, enable “Share audio” in browser capture dialog.",
    err_server_start: "Unable to create meeting on local API.",
    err_network: "Network/local API error. Please retry.",
    err_recorder_init:
      "MediaRecorder is not supported for this source. Try another mode.",
    err_diagnostics_failed:
      "Diagnostics failed. Fix source/microphone/STT issues and retry.",
    err_mic_same_as_system:
      "Microphone matches system source. Choose another microphone or keep Auto mode.",
    warn_mic_not_added:
      "Microphone could not be added. Allow microphone access and verify selected input.",
    warn_screen_audio_mic_only:
      "Screen system audio is not shared (Share audio is off). Recording microphone only.",
    warn_screen_audio_driver_fallback:
      "Share audio did not provide system audio. Using virtual driver system-track fallback.",
    warn_media_fallback_pcm:
      "MediaRecorder is unavailable, switched to PCM capture. CPU usage may be higher.",
    warn_capture_stream_interrupted:
      "One capture stream stopped unexpectedly. Continuing with remaining tracks.",
    warn_backup_upload_failed:
      "Backup audio upload failed. A tail part of recording may be missing in final transcript.",
    err_generic: "Unable to start recording. Check browser permissions and source.",
    hint_recording_ok: "Recording started. Audio capture is active.",
    hint_recording_record_first:
      "Record-first mode: only capture diagnostics are shown during recording. Final transcript appears after Stop.",
    hint_stt_warmup:
      "Speech recognition is initializing... first phrases may appear with a 5-20 second delay.",
    hint_no_speech_yet:
      "No recognized speech yet. Verify source routing: in “System audio” route meeting output to BlackHole/VB-CABLE; in “Screen + audio” enable Share audio; for voice capture ensure microphone is added.",
    diag_reason_none: "Diagnosis: not enough data yet.",
    diag_reason_system_track_missing:
      "Diagnosis: system audio track is missing. Enable loopback/virtual driver or Share audio.",
    diag_reason_mic_only:
      "Diagnosis: mic-only capture detected. Enable system track for interview recording.",
    diag_reason_low_snr:
      "Diagnosis: low SNR (quiet/noisy source). Increase source level and reduce background noise.",
    diag_reason_stt_warmup: "Diagnosis: STT warmup is still in progress, first phrases may be delayed.",
    diag_reason_audio_busy:
      "Diagnosis: audio device is busy in another app. Release the source and retry.",
  },
};

const els = {
  workModeDriver: document.getElementById("workModeDriver"),
  workModeBrowser: document.getElementById("workModeBrowser"),
  workModeApi: document.getElementById("workModeApi"),
  workModeQuick: document.getElementById("workModeQuick"),
  workModeName: document.getElementById("workModeName"),
  workModeHint: document.getElementById("workModeHint"),
  apiKey: document.getElementById("apiKey"),
  metaCandidateName: document.getElementById("metaCandidateName"),
  metaCandidateId: document.getElementById("metaCandidateId"),
  metaVacancy: document.getElementById("metaVacancy"),
  metaLevel: document.getElementById("metaLevel"),
  metaInterviewer: document.getElementById("metaInterviewer"),
  llmModelSelect: document.getElementById("llmModelSelect"),
  scanLlmModels: document.getElementById("scanLlmModels"),
  applyLlmModel: document.getElementById("applyLlmModel"),
  llmStatusText: document.getElementById("llmStatusText"),
  deviceSelect: document.getElementById("deviceSelect"),
  deviceStatusText: document.getElementById("deviceStatusText"),
  refreshDevices: document.getElementById("refreshDevices"),
  checkDriver: document.getElementById("checkDriver"),
  includeMic: document.getElementById("includeMic"),
  micSelect: document.getElementById("micSelect"),
  realtimeOnlySettings: document.getElementById("realtimeOnlySettings"),
  languageProfileSelect: document.getElementById("languageProfileSelect"),
  qualityFast: document.getElementById("qualityFast"),
  qualityBalanced: document.getElementById("qualityBalanced"),
  qualityAccurate: document.getElementById("qualityAccurate"),
  qualityHint: document.getElementById("qualityHint"),
  captureMethodChip: document.getElementById("captureMethodChip"),
  recordingModeHint: document.getElementById("recordingModeHint"),
  uploadModeHint: document.getElementById("uploadModeHint"),
  deviceModeBlock: document.getElementById("deviceModeBlock"),
  apiConnectBlock: document.getElementById("apiConnectBlock"),
  apiRecordUrl: document.getElementById("apiRecordUrl"),
  apiRecordDuration: document.getElementById("apiRecordDuration"),
  apiRecordUpload: document.getElementById("apiRecordUpload"),
  apiRecordHint: document.getElementById("apiRecordHint"),
  quickRecordBlock: document.getElementById("quickRecordBlock"),
  runDiagnostics: document.getElementById("runDiagnostics"),
  diagHint: document.getElementById("diagHint"),
  diagAudio: document.getElementById("diagAudio"),
  diagSystem: document.getElementById("diagSystem"),
  diagMic: document.getElementById("diagMic"),
  diagStt: document.getElementById("diagStt"),
  diagLlm: document.getElementById("diagLlm"),
  driverHelpBtn: document.getElementById("driverHelpBtn"),
  driverHelp: document.getElementById("driverHelp"),
  driverStatus: document.getElementById("driverStatus"),
  startBtn: document.getElementById("startBtn"),
  stopBtn: document.getElementById("stopBtn"),
  statusText: document.getElementById("statusText"),
  statusHint: document.getElementById("statusHint"),
  recognitionDiagnosis: document.getElementById("recognitionDiagnosis"),
  countdownValue: document.getElementById("countdownValue"),
  levelBar: document.getElementById("levelBar"),
  systemLevelBar: document.getElementById("systemLevelBar"),
  micLevelBar: document.getElementById("micLevelBar"),
  systemLevelText: document.getElementById("systemLevelText"),
  micLevelText: document.getElementById("micLevelText"),
  signalText: document.getElementById("signalText"),
  checkSignal: document.getElementById("checkSignal"),
  monitorHint: document.getElementById("monitorHint"),
  monitorSystemState: document.getElementById("monitorSystemState"),
  monitorMicState: document.getElementById("monitorMicState"),
  monitorSpeechNow: document.getElementById("monitorSpeechNow"),
  monitorLastPhrase: document.getElementById("monitorLastPhrase"),
  monitorSegmentsCount: document.getElementById("monitorSegmentsCount"),
  meetingIdText: document.getElementById("meetingIdText"),
  chunkCount: document.getElementById("chunkCount"),
  transcriptRaw: document.getElementById("transcriptRaw"),
  transcriptClean: document.getElementById("transcriptClean"),
  transcriptModeNote: document.getElementById("transcriptModeNote"),
  transcriptRuntimeState: document.getElementById("transcriptRuntimeState"),
  transcriptCard: document.getElementById("transcriptCard"),
  transcriptGrid: document.getElementById("transcriptGrid"),
  transcriptEmptyState: document.getElementById("transcriptEmptyState"),
  rawLiveBadge: document.getElementById("rawLiveBadge"),
  recordsSelect: document.getElementById("recordsSelect"),
  refreshRecords: document.getElementById("refreshRecords"),
  mp3SourceHint: document.getElementById("mp3SourceHint"),
  saveCurrentMp3Btn: document.getElementById("saveCurrentMp3Btn"),
  importMp3Btn: document.getElementById("importMp3Btn"),
  importMp3Input: document.getElementById("importMp3Input"),
  recordMenuBtn: document.getElementById("recordMenuBtn"),
  recordMenu: document.getElementById("recordMenu"),
  renameRecordBtn: document.getElementById("renameRecordBtn"),
  saveRecordMp3Btn: document.getElementById("saveRecordMp3Btn"),
  resultsRaw: document.getElementById("resultsRaw"),
  resultsClean: document.getElementById("resultsClean"),
  reportNameInput: document.getElementById("reportNameInput"),
  generateReportBtn: document.getElementById("generateReportBtn"),
  downloadReportBtn: document.getElementById("downloadReportBtn"),
  resultFileName: document.getElementById("resultFileName"),
  rawReportSelect: document.getElementById("rawReportSelect"),
  cleanReportSelect: document.getElementById("cleanReportSelect"),
  rawReportNameInput: document.getElementById("rawReportNameInput"),
  cleanReportNameInput: document.getElementById("cleanReportNameInput"),
  reportActionButtons: Array.from(document.querySelectorAll(".report-action-btn")),
  refreshCompare: document.getElementById("refreshCompare"),
  compareHint: document.getElementById("compareHint"),
  compareTableBody: document.getElementById("compareTableBody"),
  downloadCompareCsv: document.getElementById("downloadCompareCsv"),
  downloadCompareJson: document.getElementById("downloadCompareJson"),
  chooseFolder: document.getElementById("chooseFolder"),
  folderStatus: document.getElementById("folderStatus"),
  quickRecordUrl: document.getElementById("quickRecordUrl"),
  quickRecordDuration: document.getElementById("quickRecordDuration"),
  quickRecordTranscribe: document.getElementById("quickRecordTranscribe"),
  quickRecordUpload: document.getElementById("quickRecordUpload"),
  quickRecordStart: document.getElementById("quickRecordStart"),
  quickRecordStop: document.getElementById("quickRecordStop"),
  quickRecordState: document.getElementById("quickRecordState"),
  quickRecordHint: document.getElementById("quickRecordHint"),
  themeLight: document.getElementById("themeLight"),
  themeDark: document.getElementById("themeDark"),
  cardMode: document.querySelector(".card-mode"),
  cardConnection: document.querySelector(".card-connection"),
  cardRecording: document.querySelector(".card-recording"),
  cardUpload: document.querySelector(".card-upload"),
  modeSettingsPanels: Array.from(document.querySelectorAll("[data-mode-panel]")),
  workModeButtons: Array.from(document.querySelectorAll("[data-work-mode]")),
  captureModeInputs: Array.from(document.querySelectorAll('input[name="captureMode"]')),
};

function getQualityConfig() {
  return QUALITY_PROFILES[state.captureQuality] || QUALITY_PROFILES.balanced;
}

function renderTranscriptModeUi() {
  const dict = i18n[state.lang] || {};
  if (els.transcriptModeNote) {
    els.transcriptModeNote.textContent = dict.transcript_mode_record_first || "";
  }
  if (els.rawLiveBadge) {
    els.rawLiveBadge.textContent = dict.raw_post || "Post-stop";
  }
  if (els.transcriptRaw) {
    els.transcriptRaw.setAttribute(
      "placeholder",
      dict.transcript_placeholder_raw_post || ""
    );
  }
  if (els.transcriptClean) {
    els.transcriptClean.setAttribute(
      "placeholder",
      dict.transcript_placeholder_clean_post || ""
    );
  }
}

function hasTranscriptContent() {
  const hasRaw = Array.from(state.transcript.raw.values()).some((text) => String(text || "").trim());
  const hasClean = Array.from(state.transcript.enhanced.values()).some((text) =>
    String(text || "").trim()
  );
  const rawArea = String((els.transcriptRaw && els.transcriptRaw.value) || "").trim();
  const cleanArea = String((els.transcriptClean && els.transcriptClean.value) || "").trim();
  return Boolean(hasRaw || hasClean || rawArea || cleanArea);
}

function renderTranscriptVisibility() {
  const dict = i18n[state.lang] || {};
  const uiState = String(state.transcriptUiState || "waiting");
  const hasData = hasTranscriptContent();
  const showGrid = hasData && uiState !== "recording" && uiState !== "loading";

  if (els.transcriptGrid) {
    els.transcriptGrid.classList.toggle("hidden", !showGrid);
  }
  if (els.transcriptEmptyState) {
    els.transcriptEmptyState.classList.toggle("hidden", showGrid);
  }
  if (els.transcriptCard) {
    els.transcriptCard.classList.toggle("is-compact", !showGrid);
  }
  if (els.transcriptRuntimeState) {
    let key = "transcript_runtime_waiting";
    if (uiState === "recording") key = "transcript_runtime_recording";
    else if (uiState === "loading") key = "transcript_runtime_loading";
    else if (showGrid) key = "transcript_runtime_ready";
    else if (uiState === "empty") key = "transcript_runtime_empty";
    els.transcriptRuntimeState.textContent = dict[key] || key;
  }
}

function setTranscriptUiState(nextState = "waiting") {
  state.transcriptUiState = String(nextState || "waiting");
  renderTranscriptVisibility();
}

function renderHelpTips() {
  const dict = i18n[state.lang] || {};
  document.querySelectorAll("[data-help-i18n]").forEach((el) => {
    const key = String(el.getAttribute("data-help-i18n") || "").trim();
    if (!key) return;
    const text = String(dict[key] || key).trim();
    el.setAttribute("title", text);
    el.setAttribute("aria-label", text);
  });
}

function getCaptureTimesliceMs() {
  return Math.max(1200, Number(getQualityConfig().timesliceMs || CHUNK_TIMESLICE_MS));
}

function renderQualityProfile() {
  const cfg = getQualityConfig();
  if (els.qualityFast) {
    els.qualityFast.classList.toggle("active", cfg.id === "fast");
  }
  if (els.qualityBalanced) {
    els.qualityBalanced.classList.toggle("active", cfg.id === "balanced");
  }
  if (els.qualityAccurate) {
    els.qualityAccurate.classList.toggle("active", cfg.id === "accurate");
  }
  if (els.qualityHint) {
    const dict = i18n[state.lang] || {};
    els.qualityHint.textContent = dict[cfg.hintKey] || cfg.hintKey;
  }
}

function setCaptureQuality(nextQuality) {
  const next = String(nextQuality || "").trim().toLowerCase();
  if (!QUALITY_PROFILES[next]) {
    state.captureQuality = "balanced";
  } else {
    state.captureQuality = next;
  }
  renderQualityProfile();
}

function getLanguageProfile() {
  const raw = String(
    (els.languageProfileSelect && els.languageProfileSelect.value) || state.languageProfile || "mixed"
  )
    .trim()
    .toLowerCase();
  if (raw === "ru" || raw === "en" || raw === "mixed") return raw;
  return "mixed";
}

function syncLanguageProfileSelect() {
  if (!els.languageProfileSelect) return;
  const next = getLanguageProfile();
  state.languageProfile = next;
  els.languageProfileSelect.value = next;
}

function _diagItemLabel(el) {
  if (!el) return "";
  const dict = i18n[state.lang] || {};
  const key = String(el.getAttribute("data-i18n") || "").trim();
  return (key && dict[key]) || key || "";
}

function _renderDiagItem(el) {
  if (!el) return;
  const base = _diagItemLabel(el);
  const note = String(el.dataset.note || "").trim();
  const suffix = note ? `: ${note}` : "";
  el.textContent = `${base}${suffix}`;
}

function setDiagItemStatus(el, status = "muted", note = "") {
  if (!el) return;
  el.classList.remove("muted", "good", "bad", "running");
  el.classList.add(status || "muted");
  if (note) {
    el.dataset.note = String(note);
  } else {
    delete el.dataset.note;
  }
  _renderDiagItem(el);
}

function setDiagHint(messageKeyOrText = "", style = "muted", isRaw = false) {
  if (!els.diagHint) return;
  const dict = i18n[state.lang] || {};
  if (!messageKeyOrText) {
    els.diagHint.textContent = "";
    els.diagHint.className = "hint";
    return;
  }
  if (!isRaw && dict[messageKeyOrText]) {
    els.diagHint.textContent = dict[messageKeyOrText];
  } else {
    els.diagHint.textContent = String(messageKeyOrText || "");
  }
  els.diagHint.className = `hint ${style || "muted"}`;
}

function renderMeterDetailLabels() {
  const dict = i18n[state.lang] || {};
  const systemLevel = Math.max(0, Number(state.meterLevels.system || 0));
  const micLevel = Math.max(0, Number(state.meterLevels.mic || 0));
  const systemLabel = systemLevel > 0.001 ? `${Math.round(systemLevel * 100)}%` : "—";
  const micLabel = micLevel > 0.001 ? `${Math.round(micLevel * 100)}%` : "—";
  if (els.systemLevelText) {
    els.systemLevelText.textContent = formatText(
      dict.meter_system_label || "System: {level}",
      { level: systemLabel }
    );
  }
  if (els.micLevelText) {
    els.micLevelText.textContent = formatText(dict.meter_mic_label || "Mic: {level}", {
      level: micLabel,
    });
  }
}

function renderDiagnosticsLabels() {
  _renderDiagItem(els.diagAudio);
  _renderDiagItem(els.diagSystem);
  _renderDiagItem(els.diagMic);
  _renderDiagItem(els.diagStt);
  _renderDiagItem(els.diagLlm);
}

function formatElapsed(secondsRaw) {
  const seconds = Math.max(0, Number(secondsRaw) || 0);
  const mm = Math.floor(seconds / 60)
    .toString()
    .padStart(2, "0");
  const ss = Math.floor(seconds % 60)
    .toString()
    .padStart(2, "0");
  return `${mm}:${ss}`;
}

function setMonitorPill(el, isGood, goodKey, badKey) {
  if (!el) return;
  const dict = i18n[state.lang] || {};
  const key = isGood ? goodKey : badKey;
  el.textContent = dict[key] || key;
  el.className = `pill ${isGood ? "good" : "muted"}`;
}

function renderLiveMonitor() {
  const dict = i18n[state.lang] || {};
  const m = state.monitor;
  if (els.monitorHint) {
    els.monitorHint.textContent = dict.monitor_hint || "";
  }
  if (!state.captureStopper && !state.isCountingDown) {
    const idle = dict.monitor_not_started || "not started";
    [els.monitorSystemState, els.monitorMicState, els.monitorSpeechNow].forEach((el) => {
      if (!el) return;
      el.textContent = idle;
      el.className = "pill muted";
    });
    if (els.monitorLastPhrase) {
      els.monitorLastPhrase.textContent = dict.monitor_last_never || "not detected yet";
    }
    if (els.monitorSegmentsCount) {
      els.monitorSegmentsCount.textContent = String(m.segmentCount || 0);
    }
    return;
  }
  setMonitorPill(els.monitorSystemState, m.systemHeard, "monitor_state_heard", "monitor_state_silent");
  setMonitorPill(els.monitorMicState, m.micHeard, "monitor_state_heard", "monitor_state_silent");
  setMonitorPill(els.monitorSpeechNow, m.speechNow, "monitor_state_speaking", "monitor_state_pause");
  if (els.monitorLastPhrase) {
    if (!m.lastPhraseAt || !m.startedAt) {
      els.monitorLastPhrase.textContent = dict.monitor_last_never || "not detected yet";
    } else {
      const elapsed = (m.lastPhraseAt - m.startedAt) / 1000;
      els.monitorLastPhrase.textContent = formatElapsed(elapsed);
    }
  }
  if (els.monitorSegmentsCount) {
    els.monitorSegmentsCount.textContent = String(m.segmentCount || 0);
  }
}

function resetLiveMonitor() {
  state.monitor = {
    systemHeard: false,
    micHeard: false,
    speechNow: false,
    lastPhraseAt: 0,
    segmentCount: 0,
    startedAt: 0,
  };
  renderLiveMonitor();
}

function updateLiveMonitorFromLevels(levels) {
  const now = Date.now();
  const systemLevel = Number(levels.system || 0);
  const micLevel = Number(levels.mic || 0);
  const mixedLevel = Number(levels.mixed || 0);
  const systemHeard = systemLevel >= 0.01;
  const micHeard = micLevel >= 0.01;
  const speechEnter = 0.03;
  const speechExit = 0.018;
  const maxLevel = Math.max(systemLevel, micLevel, mixedLevel);
  const speechNow = state.monitor.speechNow ? maxLevel >= speechExit : maxLevel >= speechEnter;
  const phraseStarted = speechNow && !state.monitor.speechNow;
  state.monitor.systemHeard = systemHeard;
  state.monitor.micHeard = micHeard;
  state.monitor.speechNow = speechNow;
  if (phraseStarted) {
    state.monitor.segmentCount = Number(state.monitor.segmentCount || 0) + 1;
    state.monitor.lastPhraseAt = now;
  }
  if (!state.monitor.startedAt && (state.captureStopper || state.isCountingDown)) {
    state.monitor.startedAt = now;
  }
  renderLiveMonitor();
}

const updateI18n = () => {
  const dict = i18n[state.lang];
  document.documentElement.lang = state.lang;
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.getAttribute("data-i18n");
    if (dict[key]) el.textContent = dict[key];
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    const key = el.getAttribute("data-i18n-placeholder");
    if (dict[key]) el.setAttribute("placeholder", dict[key]);
  });
  renderHelpTips();
  setDriverStatus(state.driverStatusKey, state.driverStatusStyle);
  setFolderStatus(state.folderStatusKey, state.folderStatusStyle);
  renderDeviceStatus();
  renderLlmStatus();
  if (state.statusHintKey) {
    setStatusHint(state.statusHintKey, state.statusHintStyle);
  } else if (state.statusHintText) {
    setStatusHint(state.statusHintText, state.statusHintStyle, true);
  }
  syncCheckSignalButton();
  if (els.micSelect) {
    const first = els.micSelect.querySelector('option[value=""]');
    if (first) {
      first.textContent = dict.mic_input_auto || "Auto (recommended)";
    }
  }
  if (els.themeLight) els.themeLight.textContent = dict.theme_light || "Light";
  if (els.themeDark) els.themeDark.textContent = dict.theme_dark || "Dark";
  renderQualityProfile();
  syncLanguageProfileSelect();
  renderMeterDetailLabels();
  renderDiagnosticsLabels();
  if (els.llmModelSelect && !state.llmModels.length) {
    setLlmModelOptions([], "");
  }
  setQuickStatus(state.quickStatusKey || "quick_record_state_idle", state.quickStatusStyle || "muted");
  if (state.quickHintKey) {
    setQuickHint(state.quickHintKey, state.quickHintStyle || "muted", false);
  } else if (state.quickHintText) {
    setQuickHint(state.quickHintText, state.quickHintStyle || "muted", true);
  }
  applyWorkModeUi();
  renderComparisonTable();
  if (Array.isArray(state.compareItems) && state.compareItems.length) {
    setCompareHint("compare_hint_idle", "good");
  } else {
    setCompareHint("compare_hint_empty", "muted");
  }
  renderTranscriptModeUi();
  renderTranscriptVisibility();
  renderLiveMonitor();
  refreshRecognitionDiagnosis();
};

const setStatus = (statusKey, style) => {
  const dict = i18n[state.lang];
  els.statusText.textContent = dict[statusKey] || statusKey;
  els.statusText.className = `status-pill ${style}`;
};

const setStatusHint = (messageKeyOrText = "", style = "muted", isRaw = false) => {
  if (!els.statusHint) return;
  const dict = i18n[state.lang];
  if (!messageKeyOrText) {
    els.statusHint.textContent = "";
    els.statusHint.className = "status-hint";
    state.statusHintKey = "";
    state.statusHintText = "";
    state.statusHintStyle = "muted";
    return;
  }
  if (!isRaw && dict[messageKeyOrText]) {
    els.statusHint.textContent = dict[messageKeyOrText];
    state.statusHintKey = messageKeyOrText;
    state.statusHintText = "";
  } else {
    els.statusHint.textContent = messageKeyOrText;
    state.statusHintKey = "";
    state.statusHintText = messageKeyOrText;
  }
  state.statusHintStyle = style;
  els.statusHint.className = `status-hint ${style}`;
  refreshRecognitionDiagnosis();
};

const setRecognitionDiagnosis = (messageKeyOrText = "", style = "muted", isRaw = false) => {
  if (!els.recognitionDiagnosis) return;
  const dict = i18n[state.lang] || {};
  let text = "";
  if (!messageKeyOrText) {
    text = dict.diag_reason_none || "";
  } else if (!isRaw && dict[messageKeyOrText]) {
    text = dict[messageKeyOrText];
  } else {
    text = String(messageKeyOrText || "");
  }
  els.recognitionDiagnosis.textContent = text;
  els.recognitionDiagnosis.className = `status-hint ${style || "muted"}`;
};

const deriveRecognitionDiagnosis = () => {
  if (!getWorkModeConfig().supportsRealtime) {
    return { key: "work_mode_recording_disabled", style: "muted" };
  }
  const hint = String(state.statusHintKey || "").trim();
  if (
    hint === "err_media_not_readable" ||
    hint === "err_no_device_selected" ||
    hint === "err_media_not_found"
  ) {
    return { key: "diag_reason_audio_busy", style: "bad" };
  }

  const diag = state.diagnosticsLast || {};
  const systemOk = Boolean(diag.systemOk);
  const micOk = Boolean(diag.micOk);
  const micSkipped = Boolean(diag.micSkipped);

  const systemLevel = Number(state.meterLevels.system || 0);
  const micLevel = Number(state.meterLevels.mic || 0);
  const peak = Math.max(systemLevel, micLevel, Number(state.signalPeak || 0));

  if ((!systemOk && micOk) || (systemLevel < DIAG_SYSTEM_CRITICAL_MIN && micLevel >= 0.03)) {
    return { key: "diag_reason_mic_only", style: "bad" };
  }
  if ((!systemOk && micSkipped) || state.signalState === "signal_no_audio") {
    return { key: "diag_reason_system_track_missing", style: "bad" };
  }
  if (state.signalState === "signal_low" || (peak > 0.002 && peak < 0.03)) {
    return { key: "diag_reason_low_snr", style: "muted" };
  }
  return { key: "diag_reason_none", style: "muted" };
};

const refreshRecognitionDiagnosis = () => {
  const diagnosis = deriveRecognitionDiagnosis();
  setRecognitionDiagnosis(diagnosis.key, diagnosis.style);
};

const setSignal = (statusKey) => {
  const dict = i18n[state.lang];
  els.signalText.textContent = dict[statusKey] || statusKey;
  state.signalState = statusKey;
  refreshRecognitionDiagnosis();
};

const setDriverStatus = (statusKey, style) => {
  const dict = i18n[state.lang];
  els.driverStatus.textContent = dict[statusKey] || statusKey;
  els.driverStatus.className = `pill ${style || "muted"}`;
  state.driverStatusKey = statusKey;
  state.driverStatusStyle = style || "muted";
};

const setFolderStatus = (statusKey, style) => {
  const dict = i18n[state.lang];
  els.folderStatus.textContent = dict[statusKey] || statusKey;
  els.folderStatus.className = `pill ${style || "muted"}`;
  state.folderStatusKey = statusKey;
  state.folderStatusStyle = style || "muted";
};

const setQuickStatus = (statusKey, style = "muted") => {
  if (!els.quickRecordState) return;
  const dict = i18n[state.lang] || {};
  els.quickRecordState.textContent = dict[statusKey] || statusKey;
  els.quickRecordState.className = `pill ${style || "muted"}`;
  state.quickStatusKey = statusKey;
  state.quickStatusStyle = style || "muted";
};

const setQuickHint = (hintKeyOrText = "", style = "muted", isRaw = false, params = {}) => {
  if (!els.quickRecordHint) return;
  const dict = i18n[state.lang] || {};
  let text = "";
  if (!hintKeyOrText) {
    text = "";
    state.quickHintKey = "";
    state.quickHintText = "";
    state.quickHintStyle = "muted";
  } else if (!isRaw && dict[hintKeyOrText]) {
    text = formatText(dict[hintKeyOrText], params);
    state.quickHintKey = hintKeyOrText;
    state.quickHintText = "";
    state.quickHintStyle = style || "muted";
  } else {
    text = String(hintKeyOrText);
    state.quickHintKey = "";
    state.quickHintText = text;
    state.quickHintStyle = style || "muted";
  }
  els.quickRecordHint.textContent = text;
  els.quickRecordHint.className = `hint ${style || "muted"}`;
};

const setCompareHint = (hintKeyOrText = "", style = "muted", isRaw = false) => {
  if (!els.compareHint) return;
  const dict = i18n[state.lang] || {};
  let text = "";
  if (!hintKeyOrText) {
    text = "";
  } else if (!isRaw && dict[hintKeyOrText]) {
    text = dict[hintKeyOrText];
  } else {
    text = String(hintKeyOrText || "");
  }
  els.compareHint.textContent = text;
  els.compareHint.className = `hint ${style || "muted"}`;
};

const _metaText = (value) => String(value || "").trim();

const getInterviewMetadata = () => {
  const candidateName = _metaText(els.metaCandidateName && els.metaCandidateName.value);
  const candidateId = _metaText(els.metaCandidateId && els.metaCandidateId.value);
  const vacancy = _metaText(els.metaVacancy && els.metaVacancy.value);
  const level = _metaText(els.metaLevel && els.metaLevel.value);
  const interviewer = _metaText(els.metaInterviewer && els.metaInterviewer.value);
  return {
    candidate_name: candidateName,
    candidate_id: candidateId,
    vacancy,
    level,
    interviewer,
  };
};

const validateInterviewMetadata = () => {
  return getInterviewMetadata();
};

const renderComparisonTable = () => {
  if (!els.compareTableBody) return;
  els.compareTableBody.innerHTML = "";
  const dict = i18n[state.lang] || {};
  const rows = Array.isArray(state.compareItems) ? state.compareItems : [];
  rows.forEach((item) => {
    const tr = document.createElement("tr");
    const candidate = _metaText(item.candidate_name) || dict.compare_row_candidate_fallback || "Candidate";
    const vacancy = _metaText(item.vacancy) || "—";
    const level = _metaText(item.level) || "—";
    const score = Number.isFinite(Number(item.overall_score))
      ? `${Number(item.overall_score).toFixed(2)}`
      : "—";
    const decision = _metaText(item.decision_status) || "insufficient_data";
    const quality = _metaText(item.transcript_quality) || "low";
    [candidate, vacancy, level, score, decision, quality].forEach((value, idx) => {
      const td = document.createElement("td");
      td.textContent = value;
      if (idx === 4 && (decision === "no" || decision === "lean_no" || decision === "insufficient_data")) {
        td.classList.add("bad");
      }
      if (idx === 4 && (decision === "yes" || decision === "strong_yes" || decision === "lean_yes")) {
        td.classList.add("good");
      }
      if (idx === 5 && (quality === "low" || quality === "unknown")) {
        td.classList.add("bad");
      }
      if (idx === 5 && (quality === "high" || quality === "medium")) {
        td.classList.add("good");
      }
      tr.appendChild(td);
    });
    els.compareTableBody.appendChild(tr);
  });
};

const fetchComparison = async () => {
  if (els.refreshCompare) els.refreshCompare.disabled = true;
  setCompareHint("compare_hint_loading", "muted");
  try {
    const source = state.resultsSource === "raw" ? "raw" : "clean";
    const res = await fetch(`/v1/meetings/compare?source=${source}&limit=50`, {
      headers: buildHeaders(),
    });
    if (!res.ok) {
      throw new Error(`compare_failed_${res.status}`);
    }
    const body = await res.json();
    const items = Array.isArray(body.items) ? body.items : [];
    state.compareItems = items;
    renderComparisonTable();
    if (!items.length) {
      setCompareHint("compare_hint_empty", "muted");
    } else {
      setCompareHint("compare_hint_idle", "good");
    }
  } catch (err) {
    console.warn("compare fetch failed", err);
    state.compareItems = [];
    renderComparisonTable();
    setCompareHint("compare_hint_failed", "bad");
  } finally {
    if (els.refreshCompare) els.refreshCompare.disabled = false;
  }
};

const downloadComparison = async (fmt) => {
  const source = state.resultsSource === "raw" ? "raw" : "clean";
  const url = `/v1/meetings/compare/export?source=${source}&limit=50&fmt=${fmt}`;
  const filename = `compare_${source}.${fmt}`;
  await downloadArtifact(url, filename);
};

const formatText = (template, params = {}) => {
  let text = String(template || "");
  Object.entries(params).forEach(([key, value]) => {
    text = text.replaceAll(`{${key}}`, String(value));
  });
  return text;
};

const renderDeviceStatus = () => {
  if (!els.deviceStatusText) return;
  const dict = i18n[state.lang] || {};
  const template = dict[state.deviceStatusKey] || state.deviceStatusKey;
  const text = formatText(template, { count: state.deviceStatusCount || 0 });
  els.deviceStatusText.textContent = text;
  els.deviceStatusText.className = `hint device-status ${state.deviceStatusStyle || "muted"}`;
};

const setDeviceStatus = (statusKey, style = "muted", count = 0) => {
  state.deviceStatusKey = statusKey;
  state.deviceStatusStyle = style;
  state.deviceStatusCount = Number.isFinite(count) ? Number(count) : 0;
  renderDeviceStatus();
};

const renderLlmStatus = () => {
  if (!els.llmStatusText) return;
  const dict = i18n[state.lang] || {};
  let text = state.llmStatusText;
  if (!text) {
    const template = dict[state.llmStatusKey] || state.llmStatusKey;
    text = formatText(template, state.llmStatusParams || {});
  }
  els.llmStatusText.textContent = text;
  els.llmStatusText.className = `hint llm-status ${state.llmStatusStyle || "muted"}`;
};

const setLlmStatus = (
  statusKeyOrText = "llm_status_loading",
  style = "muted",
  params = {},
  isRaw = false
) => {
  state.llmStatusStyle = style || "muted";
  state.llmStatusParams = params || {};
  if (isRaw) {
    state.llmStatusText = String(statusKeyOrText || "");
    state.llmStatusKey = "";
  } else {
    state.llmStatusKey = String(statusKeyOrText || "");
    state.llmStatusText = "";
  }
  renderLlmStatus();
};

const setLlmModelOptions = (models = [], preferredModel = "") => {
  if (!els.llmModelSelect) return;
  const incoming = Array.isArray(models) ? models : [];
  const normalized = incoming
    .map((value) => String(value || "").trim())
    .filter(Boolean);
  const seen = new Set();
  const unique = [];
  normalized.forEach((model) => {
    if (seen.has(model)) return;
    seen.add(model);
    unique.push(model);
  });

  const currentValue = String(preferredModel || els.llmModelSelect.value || "").trim();
  if (currentValue && !seen.has(currentValue)) {
    unique.push(currentValue);
  }
  state.llmModels = unique;

  els.llmModelSelect.innerHTML = "";
  if (!unique.length) {
    const emptyOpt = document.createElement("option");
    emptyOpt.value = "";
    emptyOpt.textContent = i18n[state.lang].llm_model_placeholder || "Select model";
    els.llmModelSelect.appendChild(emptyOpt);
    els.llmModelSelect.value = "";
    return;
  }

  unique.forEach((model) => {
    const opt = document.createElement("option");
    opt.value = model;
    opt.textContent = model;
    els.llmModelSelect.appendChild(opt);
  });

  if (currentValue && unique.includes(currentValue)) {
    els.llmModelSelect.value = currentValue;
  } else {
    els.llmModelSelect.value = unique[0];
  }
};

const applyTheme = (theme) => {
  const next = theme === "dark" ? "dark" : "light";
  state.theme = next;
  document.body.dataset.theme = next;
  if (els.themeLight) {
    els.themeLight.classList.toggle("active", next === "light");
  }
  if (els.themeDark) {
    els.themeDark.classList.toggle("active", next === "dark");
  }
  try {
    localStorage.setItem("ui_theme", next);
  } catch (err) {
    // ignore storage errors
  }
};

const isRecordingFlowActive = () =>
  state.isCountingDown ||
  Boolean(state.captureStopper) ||
  Boolean(state.meetingId) ||
  !els.stopBtn.disabled;

const syncCheckSignalButton = () => {
  if (!els.checkSignal) return;
  const dict = i18n[state.lang];
  const busy = state.signalCheckInProgress;
  const recordingBlocked = isRecordingFlowActive();
  const modeAllows = Boolean(getWorkModeConfig().supportsRealtime);
  els.checkSignal.disabled = busy || recordingBlocked || !modeAllows;
  els.checkSignal.textContent = busy
    ? dict.signal_check_running || "Checking capture..."
    : dict.signal_check || "Check capture";
};

const setRecordingButtons = (isRecording) => {
  const modeAllowsRealtime = Boolean(getWorkModeConfig().supportsRealtime);
  const modeAllowsQuick = Boolean(getWorkModeConfig().supportsQuick);
  if (modeAllowsQuick && !modeAllowsRealtime) {
    const quickBusy = isQuickFlowActive();
    if (isRecording || quickBusy) {
      els.startBtn.disabled = true;
      els.stopBtn.disabled = false;
      els.startBtn.classList.add("is-inactive");
      els.startBtn.classList.remove("is-active");
      els.stopBtn.classList.add("is-active");
      els.stopBtn.classList.remove("is-inactive");
    } else {
      els.startBtn.disabled = false;
      els.stopBtn.disabled = true;
      els.startBtn.classList.add("is-active");
      els.startBtn.classList.remove("is-inactive");
      els.stopBtn.classList.add("is-inactive");
      els.stopBtn.classList.remove("is-active");
    }
    syncCheckSignalButton();
    return;
  }
  if (isRecording) {
    els.startBtn.disabled = true;
    els.stopBtn.disabled = false;
    els.startBtn.classList.add("is-inactive");
    els.startBtn.classList.remove("is-active");
    els.stopBtn.classList.add("is-active");
    els.stopBtn.classList.remove("is-inactive");
  } else {
    els.startBtn.disabled = !modeAllowsRealtime;
    els.stopBtn.disabled = true;
    els.startBtn.classList.toggle("is-active", modeAllowsRealtime);
    els.startBtn.classList.toggle("is-inactive", !modeAllowsRealtime);
    els.stopBtn.classList.add("is-inactive");
    els.stopBtn.classList.remove("is-active");
  }
  syncCheckSignalButton();
};

const buildHeaders = () => {
  const headers = { "Content-Type": "application/json" };
  const key = (els.apiKey.value || "").trim();
  if (key) headers["X-API-Key"] = key;
  return headers;
};

const buildAuthHeaders = () => {
  const headers = {};
  const key = (els.apiKey.value || "").trim();
  if (key) headers["X-API-Key"] = key;
  return headers;
};

const nowMs = () => Date.now();

const readCaptureLock = () => {
  try {
    const raw = localStorage.getItem(CAPTURE_LOCK_KEY);
    if (!raw) return null;
    const data = JSON.parse(raw);
    if (!data || typeof data !== "object") return null;
    const owner = String(data.owner || "").trim();
    const ts = Number(data.ts || 0);
    const meetingId = String(data.meetingId || "").trim();
    if (!owner || !Number.isFinite(ts) || ts <= 0) return null;
    return { owner, ts, meetingId };
  } catch (_err) {
    return null;
  }
};

const writeCaptureLock = (meetingId = "") => {
  try {
    localStorage.setItem(
      CAPTURE_LOCK_KEY,
      JSON.stringify({
        owner: state.instanceId,
        ts: nowMs(),
        meetingId: String(meetingId || ""),
      })
    );
  } catch (_err) {
    // ignore storage failures
  }
};

const clearCaptureLock = () => {
  try {
    const current = readCaptureLock();
    if (!current) return;
    if (current.owner !== state.instanceId) return;
    localStorage.removeItem(CAPTURE_LOCK_KEY);
  } catch (_err) {
    // ignore storage failures
  }
};

const pruneStaleCaptureLock = () => {
  try {
    const lock = readCaptureLock();
    if (!lock) return;
    if (nowMs() - lock.ts <= CAPTURE_LOCK_TTL_MS) return;
    localStorage.removeItem(CAPTURE_LOCK_KEY);
  } catch (_err) {
    // ignore storage failures
  }
};

const isCaptureLockedByOtherTab = () => {
  const lock = readCaptureLock();
  if (!lock) return { locked: false, meetingId: "" };
  if (lock.owner === state.instanceId) return { locked: false, meetingId: lock.meetingId };
  if (nowMs() - lock.ts > CAPTURE_LOCK_TTL_MS) return { locked: false, meetingId: lock.meetingId };
  return { locked: true, meetingId: lock.meetingId };
};

const startCaptureLockHeartbeat = () => {
  if (state.captureLockTimer) return;
  state.captureLockTimer = setInterval(() => {
    writeCaptureLock(state.meetingId || "");
  }, CAPTURE_LOCK_HEARTBEAT_MS);
};

const stopCaptureLockHeartbeat = () => {
  if (state.captureLockTimer) {
    clearInterval(state.captureLockTimer);
  }
  state.captureLockTimer = null;
  clearCaptureLock();
};

const isVirtualAudioDevice = (label = "") => {
  const normalized = String(label || "").toLowerCase();
  if (!normalized) return false;
  return VIRTUAL_DEVICE_PATTERNS.some((pattern) => normalized.includes(pattern));
};

const pickPreferredMicDeviceId = async (excludeDeviceId = "") => {
  const devices = await navigator.mediaDevices.enumerateDevices();
  const inputs = devices.filter((device) => device.kind === "audioinput");
  const exactExclude = String(excludeDeviceId || "");
  const nonVirtual = inputs.find((device) => {
    if (!device.deviceId || device.deviceId === exactExclude) return false;
    return !isVirtualAudioDevice(device.label);
  });
  if (nonVirtual && nonVirtual.deviceId) return nonVirtual.deviceId;
  const fallback = inputs.find((device) => device.deviceId && device.deviceId !== exactExclude);
  return fallback ? fallback.deviceId : "";
};

const pickMicDeviceId = async (excludeDeviceId = "", selectedMicId = "") => {
  const normalizedSelected = String(selectedMicId || "").trim();
  const normalizedExclude = String(excludeDeviceId || "").trim();
  if (normalizedSelected && normalizedSelected !== normalizedExclude) {
    return normalizedSelected;
  }
  const preferred = await pickPreferredMicDeviceId(normalizedExclude);
  return preferred || "";
};

const listDevices = async (options = {}) => {
  const { requestAccess = false } = options;
  try {
    if (
      requestAccess &&
      navigator.mediaDevices &&
      typeof navigator.mediaDevices.getUserMedia === "function" &&
      !isRecordingFlowActive()
    ) {
      try {
        const tmpStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        tmpStream.getTracks().forEach((track) => track.stop());
      } catch (err) {
        console.warn("audio permission for device refresh failed", err);
      }
    }

    const devices = await navigator.mediaDevices.enumerateDevices();
    const inputs = devices
      .filter((d) => d.kind === "audioinput")
      .sort((left, right) => {
        const lv = isVirtualAudioDevice(left.label) ? 1 : 0;
        const rv = isVirtualAudioDevice(right.label) ? 1 : 0;
        return rv - lv;
      });
    const prevValue = els.deviceSelect.value;
    const prevMicValue = els.micSelect ? els.micSelect.value : "";
    els.deviceSelect.innerHTML = "";
    inputs.forEach((device) => {
      const opt = document.createElement("option");
      opt.value = device.deviceId;
      opt.textContent = device.label || `Audio device ${els.deviceSelect.length + 1}`;
      els.deviceSelect.appendChild(opt);
    });
    if (!inputs.length) {
      const opt = document.createElement("option");
      opt.value = "";
      opt.textContent = "—";
      els.deviceSelect.appendChild(opt);
      if (els.micSelect) {
        els.micSelect.innerHTML = "";
        const autoOpt = document.createElement("option");
        autoOpt.value = "";
        autoOpt.textContent = i18n[state.lang].mic_input_auto || "Auto (recommended)";
        els.micSelect.appendChild(autoOpt);
      }
      setDeviceStatus("device_status_empty", "bad", 0);
      return;
    }
    setDeviceStatus("device_status_count", "muted", inputs.length);
    const hasPrev = inputs.some((d) => d.deviceId === prevValue);
    if (hasPrev) {
      els.deviceSelect.value = prevValue;
    } else {
      const firstVirtual = inputs.find((device) => isVirtualAudioDevice(device.label));
      if (firstVirtual && firstVirtual.deviceId) {
        els.deviceSelect.value = firstVirtual.deviceId;
      }
    }

    if (els.micSelect) {
      const selectedSystemDeviceId = els.deviceSelect.value || "";
      const micCandidates = inputs
        .filter((device) => device.deviceId && device.deviceId !== selectedSystemDeviceId)
        .sort((left, right) => {
          const lv = isVirtualAudioDevice(left.label) ? 1 : 0;
          const rv = isVirtualAudioDevice(right.label) ? 1 : 0;
          return lv - rv;
        });
      els.micSelect.innerHTML = "";
      const autoOpt = document.createElement("option");
      autoOpt.value = "";
      autoOpt.textContent = i18n[state.lang].mic_input_auto || "Auto (recommended)";
      els.micSelect.appendChild(autoOpt);
      micCandidates.forEach((device, index) => {
        const opt = document.createElement("option");
        opt.value = device.deviceId;
        opt.textContent = device.label || `Mic ${index + 1}`;
        els.micSelect.appendChild(opt);
      });
      if (
        prevMicValue &&
        micCandidates.some((device) => device.deviceId === prevMicValue)
      ) {
        els.micSelect.value = prevMicValue;
      } else {
        els.micSelect.value = "";
      }
    }
  } catch (err) {
    console.warn("device list failed", err);
    const denied = err && typeof err === "object" && err.name === "NotAllowedError";
    if (denied) {
      setDeviceStatus("device_status_access_denied", "bad", 0);
    } else {
      setDeviceStatus("device_status_unknown", "bad", 0);
    }
  }
};

const fetchLlmStatus = async (options = {}) => {
  const { scanAfter = false } = options;
  if (!els.llmModelSelect) return;
  setLlmStatus("llm_status_loading", "muted");
  try {
    const res = await fetch("/v1/llm/status", { headers: buildHeaders() });
    if (!res.ok) {
      throw new Error(`llm_status_failed_${res.status}`);
    }
    const data = await res.json();
    const currentModel = String(data.model_id || "").trim();
    if (currentModel) {
      setLlmModelOptions([currentModel], currentModel);
    } else {
      setLlmModelOptions([], "");
    }
    if (!data.llm_enabled) {
      setLlmStatus("llm_status_disabled", "bad");
      return;
    }
    setLlmStatus("llm_status_ready", "good", { model: currentModel || "—" });
    if (scanAfter) {
      await scanLlmModels({ silentErrors: true });
    }
  } catch (err) {
    console.warn("llm status fetch failed", err);
    setLlmStatus("llm_status_unavailable", "bad");
  }
};

const scanLlmModels = async (options = {}) => {
  const { silentErrors = false } = options;
  if (!els.llmModelSelect) return;
  setLlmStatus("llm_status_scanning", "muted");
  if (els.scanLlmModels) els.scanLlmModels.disabled = true;
  if (els.applyLlmModel) els.applyLlmModel.disabled = true;
  try {
    const res = await fetch("/v1/llm/models", { headers: buildHeaders() });
    if (!res.ok) {
      throw new Error(`llm_models_failed_${res.status}`);
    }
    const data = await res.json();
    const models = Array.isArray(data.models) ? data.models : [];
    const currentModel = String(
      data.current_model || els.llmModelSelect.value || ""
    ).trim();
    setLlmModelOptions(models, currentModel);
    const selectedModel = String(els.llmModelSelect.value || currentModel || "—");
    if (models.length) {
      setLlmStatus("llm_status_scan_done", "good", {
        count: models.length,
        model: selectedModel,
      });
    } else {
      setLlmStatus("llm_status_scan_empty", "bad", { model: selectedModel });
    }
  } catch (err) {
    console.warn("llm model scan failed", err);
    if (!silentErrors) {
      setLlmStatus("llm_status_unavailable", "bad");
    }
  } finally {
    if (els.scanLlmModels) els.scanLlmModels.disabled = false;
    if (els.applyLlmModel) els.applyLlmModel.disabled = false;
  }
};

const applyLlmModel = async () => {
  if (!els.llmModelSelect) return;
  const modelId = String(els.llmModelSelect.value || "").trim();
  if (!modelId) {
    setLlmStatus("llm_model_missing", "bad");
    return;
  }
  if (els.applyLlmModel) els.applyLlmModel.disabled = true;
  try {
    const res = await fetch("/v1/llm/model", {
      method: "POST",
      headers: buildHeaders(),
      body: JSON.stringify({ model_id: modelId }),
    });
    if (!res.ok) {
      throw new Error(`llm_model_update_failed_${res.status}`);
    }
    const data = await res.json();
    const appliedModel = String(data.model_id || modelId).trim();
    setLlmModelOptions(state.llmModels.length ? state.llmModels : [appliedModel], appliedModel);
    setLlmStatus("llm_status_applied", "good", { model: appliedModel || "—" });
  } catch (err) {
    console.warn("llm model switch failed", err);
    setLlmStatus("llm_status_apply_failed", "bad");
  } finally {
    if (els.applyLlmModel) els.applyLlmModel.disabled = false;
  }
};

const normalizeWorkMode = (value) => {
  const raw = String(value || "").trim();
  return WORK_MODE_CONFIGS[raw] ? raw : "driver_audio";
};

const getWorkModeConfig = (value = state.workMode) => {
  const mode = normalizeWorkMode(value);
  return WORK_MODE_CONFIGS[mode] || WORK_MODE_CONFIGS.driver_audio;
};

const isQuickFlowActive = () => {
  const key = String(state.quickStatusKey || "").trim();
  return key === "quick_record_state_running" || key === "quick_record_state_stopping";
};

const isWorkModeSwitchLocked = () => {
  return Boolean(state.isUploading || isRecordingFlowActive() || isQuickFlowActive());
};

const _setModeHintText = (el, messageKeyOrText = "", style = "muted", isRaw = false) => {
  if (!el) return;
  const dict = i18n[state.lang] || {};
  if (!messageKeyOrText) {
    el.textContent = "";
    el.className = "hint mode-hint";
    return;
  }
  el.textContent = !isRaw && dict[messageKeyOrText] ? dict[messageKeyOrText] : String(messageKeyOrText || "");
  el.className = `hint mode-hint ${style || "muted"}`;
};

const syncModeSettingsPanels = (activeMode = state.workMode) => {
  const normalized = normalizeWorkMode(activeMode);
  (els.modeSettingsPanels || []).forEach((panel) => {
    if (!panel || !panel.dataset) return;
    const panelMode = normalizeWorkMode(panel.dataset.modePanel || "");
    panel.classList.toggle("active", panelMode === normalized);
  });
};

const getQuickControlSet = (cfg = getWorkModeConfig()) => {
  if (cfg && cfg.id === "api_upload") {
    return {
      url: els.apiRecordUrl,
      duration: els.apiRecordDuration,
      transcribe: null,
      upload: els.apiRecordUpload,
    };
  }
  return {
    url: els.quickRecordUrl,
    duration: els.quickRecordDuration,
    transcribe: els.quickRecordTranscribe,
    upload: els.quickRecordUpload,
  };
};

const applyWorkModeUi = () => {
  const cfg = getWorkModeConfig();
  state.workMode = cfg.id;
  const dict = i18n[state.lang] || {};

  (els.workModeButtons || []).forEach((btn) => {
    const mode = normalizeWorkMode(btn && btn.dataset ? btn.dataset.workMode : "");
    btn.classList.toggle("active", mode === cfg.id);
  });
  syncModeSettingsPanels(cfg.id);

  if (els.workModeName) {
    const label = dict[cfg.labelKey] || cfg.id;
    els.workModeName.textContent = label;
  }
  _setModeHintText(els.workModeHint, cfg.descriptionKey, "muted");

  const recordingEnabled = Boolean(cfg.supportsRealtime || cfg.supportsQuick);
  const realtimeEnabled = Boolean(cfg.supportsRealtime);
  const uploadEnabled = Boolean(cfg.supportsUpload);
  const quickEnabled = Boolean(cfg.supportsQuick);
  const driverEnabled = Boolean(cfg.useDeviceDriver);

  if (cfg.forceCaptureMode) {
    (els.captureModeInputs || []).forEach((input) => {
      if (!input) return;
      input.checked = input.value === cfg.forceCaptureMode;
    });
  }

  (els.captureModeInputs || []).forEach((input) => {
    if (!input) return;
    input.disabled = !realtimeEnabled || Boolean(cfg.forceCaptureMode);
  });

  if (els.cardRecording) {
    els.cardRecording.classList.toggle("mode-active", recordingEnabled);
    els.cardRecording.classList.toggle("mode-disabled", !recordingEnabled);
  }
  if (els.cardUpload) {
    const uploadCardActive = uploadEnabled || quickEnabled;
    els.cardUpload.classList.toggle("mode-active", uploadCardActive);
    els.cardUpload.classList.toggle("mode-disabled", !uploadCardActive);
  }
  if (els.cardConnection) {
    els.cardConnection.classList.add("mode-active");
    els.cardConnection.classList.remove("mode-disabled");
  }

  if (els.deviceModeBlock) {
    els.deviceModeBlock.classList.toggle("mode-disabled", !driverEnabled);
  }
  [els.deviceSelect, els.refreshDevices, els.checkDriver, els.driverHelpBtn].forEach((el) => {
    if (!el) return;
    el.disabled = !driverEnabled;
  });
  if (!driverEnabled && els.driverHelp) {
    els.driverHelp.classList.add("hidden");
  }

  _setModeHintText(
    els.recordingModeHint,
    recordingEnabled ? cfg.descriptionKey : "work_mode_recording_disabled",
    recordingEnabled ? "muted" : "bad"
  );

  if (els.apiConnectBlock) {
    els.apiConnectBlock.classList.toggle("mode-disabled", cfg.id !== "api_upload");
  }

  if (els.quickRecordBlock) {
    els.quickRecordBlock.classList.toggle("mode-disabled", !quickEnabled);
  }
  const quickBusy = isQuickFlowActive();
  const quickControls = getQuickControlSet(cfg);
  [quickControls.url, quickControls.duration, quickControls.transcribe, quickControls.upload].forEach((el) => {
    if (!el) return;
    el.disabled = !quickEnabled || quickBusy;
  });
  if (els.apiKey) {
    els.apiKey.disabled = cfg.id === "api_upload" ? quickBusy : false;
  }
  _setModeHintText(
    els.uploadModeHint,
    cfg.id === "api_upload"
      ? "work_mode_desc_api"
      : quickEnabled
      ? "work_mode_desc_quick"
      : "work_mode_upload_disabled",
    uploadEnabled || quickEnabled ? "muted" : "bad"
  );

  syncCheckSignalButton();
  updateCaptureUi();
  setQuickButtonsByStatus(state.quickStatusKey || "quick_record_state_idle");
  if (!recordingEnabled) {
    setRecordingButtons(false);
  }
  if (els.runDiagnostics && !state.signalCheckInProgress) {
    els.runDiagnostics.disabled = !realtimeEnabled;
  }
};

const setWorkMode = (nextMode, options = {}) => {
  const { persist = true, force = false } = options;
  const normalized = normalizeWorkMode(nextMode);
  if (!force && isWorkModeSwitchLocked()) {
    setStatusHint("err_work_mode_switch_locked", "bad");
    return false;
  }
  state.workMode = normalized;
  if (persist) {
    try {
      localStorage.setItem(WORK_MODE_KEY, normalized);
    } catch (_err) {
      // ignore storage failures
    }
  }
  applyWorkModeUi();
  refreshRecognitionDiagnosis();
  return true;
};

const getCaptureMode = () => {
  const cfg = getWorkModeConfig();
  if (cfg.forceCaptureMode) return cfg.forceCaptureMode;
  const el = document.querySelector('input[name="captureMode"]:checked');
  return el ? el.value : "system";
};

const closeMixGraph = () => {
  if (state.mixNodes && state.mixNodes.length) {
    state.mixNodes.forEach((node) => {
      try {
        node.disconnect();
      } catch (err) {
        void err;
      }
    });
  }
  state.mixNodes = [];
  if (state.mixContext) {
    state.mixContext.close().catch(() => {});
  }
  state.mixContext = null;
};

const stopInputStreams = () => {
  state.inputStreams.forEach((input) => {
    try {
      input.getTracks().forEach((track) => track.stop());
    } catch (err) {
      void err;
    }
  });
  state.inputStreams = [];
};

const ensureAudioContextActive = async (ctx) => {
  if (!ctx || typeof ctx.resume !== "function") return;
  if (ctx.state !== "suspended") return;
  try {
    await ctx.resume();
  } catch (err) {
    console.warn("audio context resume failed", err);
  }
};

const sleepMs = (ms) =>
  new Promise((resolve) => {
    setTimeout(resolve, Math.max(0, Number(ms) || 0));
  });

const isDeviceBusyError = (err) => {
  const name = err && typeof err === "object" ? String(err.name || "") : "";
  return name === "NotReadableError" || name === "AbortError";
};

const withBusyRetry = async (openFn, delays = MEDIA_BUSY_RETRY_DELAYS_MS) => {
  let lastErr = null;
  for (let attempt = 0; attempt <= delays.length; attempt += 1) {
    try {
      return await openFn();
    } catch (err) {
      lastErr = err;
      if (!isDeviceBusyError(err) || attempt >= delays.length) {
        throw err;
      }
      await sleepMs(delays[attempt]);
    }
  }
  throw lastErr || new Error("media_open_failed");
};

const stopStreamTracksSafe = (stream) => {
  if (!stream) return;
  try {
    stream.getTracks().forEach((track) => track.stop());
  } catch (err) {
    void err;
  }
};

const openScreenCaptureStream = async () => {
  let lastErr = null;
  try {
    const stream = await withBusyRetry(
      () =>
        navigator.mediaDevices.getDisplayMedia({
          video: true,
          audio: true,
        }),
      SCREEN_AUDIO_RETRY_DELAYS_MS
    );
    if (stream.getAudioTracks().length) {
      return { stream, audioMissing: false };
    }
    stopStreamTracksSafe(stream);
  } catch (err) {
    lastErr = err;
    if (!isDeviceBusyError(err)) {
      throw err;
    }
  }

  // Fallback: если браузер не отдал системный трек, продолжаем с mic-only.
  await sleepMs(260);
  try {
    const fallback = await withBusyRetry(
      () =>
        navigator.mediaDevices.getDisplayMedia({
          video: true,
          audio: false,
        }),
      [260, 520, 1000]
    );
    return { stream: fallback, audioMissing: true };
  } catch (err) {
    if (lastErr && isDeviceBusyError(lastErr)) {
      throw lastErr;
    }
    throw err;
  }
};

const openSystemDriverFallbackStream = async () => {
  if (!navigator.mediaDevices || typeof navigator.mediaDevices.getUserMedia !== "function") {
    return null;
  }
  let devices = [];
  try {
    devices = await navigator.mediaDevices.enumerateDevices();
  } catch (_err) {
    devices = [];
  }

  const selectedDeviceId = String((els.deviceSelect && els.deviceSelect.value) || "").trim();
  const inputs = (Array.isArray(devices) ? devices : [])
    .filter((d) => d && d.kind === "audioinput" && d.deviceId)
    .sort((left, right) => {
      const lv = isVirtualAudioDevice(left.label) ? 1 : 0;
      const rv = isVirtualAudioDevice(right.label) ? 1 : 0;
      return rv - lv;
    });

  if (!inputs.length && selectedDeviceId) {
    try {
      const stream = await withBusyRetry(
        () =>
          navigator.mediaDevices.getUserMedia({
            audio: { deviceId: { exact: selectedDeviceId } },
          }),
        [200, 460, 900]
      );
      if (stream.getAudioTracks().length) {
        return { stream, deviceId: selectedDeviceId, label: "" };
      }
      stopStreamTracksSafe(stream);
    } catch (_err) {
      return null;
    }
    return null;
  }

  const ordered = [];
  if (selectedDeviceId) {
    const preferred = inputs.find((d) => d.deviceId === selectedDeviceId);
    if (preferred) ordered.push(preferred);
  }
  inputs.forEach((d) => {
    if (!ordered.some((item) => item.deviceId === d.deviceId)) {
      ordered.push(d);
    }
  });

  for (const candidate of ordered) {
    try {
      const stream = await withBusyRetry(
        () =>
          navigator.mediaDevices.getUserMedia({
            audio: { deviceId: { exact: candidate.deviceId } },
          }),
        [200, 460, 900]
      );
      if (!stream.getAudioTracks().length) {
        stopStreamTracksSafe(stream);
        continue;
      }
      return {
        stream,
        deviceId: String(candidate.deviceId || ""),
        label: String(candidate.label || ""),
      };
    } catch (_err) {
      // try next candidate
    }
  }
  return null;
};

const buildMixedAudioStream = async (baseStream, includeMic, selectedMicId = "", options = {}) => {
  const { mode = "system" } = options;
  const Ctx = window.AudioContext || window.webkitAudioContext;
  if (!Ctx) return { stream: baseStream, micAdded: false, micError: "" };

  const context = new Ctx();
  const destination = context.createMediaStreamDestination();
  const nodes = [destination];
  let micAdded = false;
  let micStream = null;
  let micError = "";

  const connectStream = (stream, options = {}) => {
    const { gainValue = 1, useCompressor = false } = options;
    const source = context.createMediaStreamSource(stream);
    const gain = context.createGain();
    gain.gain.value = gainValue;
    source.connect(gain);
    if (useCompressor) {
      const compressor = context.createDynamicsCompressor();
      compressor.threshold.value = -28;
      compressor.knee.value = 24;
      compressor.ratio.value = 3.2;
      compressor.attack.value = 0.004;
      compressor.release.value = 0.22;
      gain.connect(compressor);
      compressor.connect(destination);
      nodes.push(source, gain, compressor);
      return;
    }
    gain.connect(destination);
    nodes.push(source, gain);
  };

  connectStream(baseStream, {
    gainValue: mode === "screen" ? SYSTEM_STREAM_GAIN_SCREEN : SYSTEM_STREAM_GAIN,
    useCompressor: true,
  });

  if (includeMic) {
    const selectedSystemDeviceId = state.streamDeviceId || (els.deviceSelect && els.deviceSelect.value) || "";
    try {
      let preferredMicId = await pickMicDeviceId(selectedSystemDeviceId, selectedMicId);
      if (
        preferredMicId &&
        selectedSystemDeviceId &&
        preferredMicId === selectedSystemDeviceId
      ) {
        preferredMicId = await pickPreferredMicDeviceId(selectedSystemDeviceId);
      }
      if (
        preferredMicId &&
        selectedSystemDeviceId &&
        preferredMicId === selectedSystemDeviceId
      ) {
        throw new Error("mic_same_as_system");
      }
      if (!preferredMicId && selectedSystemDeviceId) {
        throw new Error("mic_not_found");
      }
      micStream = await withBusyRetry(() =>
        navigator.mediaDevices.getUserMedia({
          audio: preferredMicId ? { deviceId: { exact: preferredMicId } } : true,
        })
      );
      connectStream(micStream, { gainValue: MIC_STREAM_GAIN });
      micAdded = true;
    } catch (err) {
      micError = err && err.message ? String(err.message) : "mic_add_failed";
      console.warn("unable to add microphone to mixed stream", err);
    }
  }

  await ensureAudioContextActive(context);
  state.mixContext = context;
  state.mixNodes = nodes;
  state.inputStreams = micStream ? [baseStream, micStream] : [baseStream];

  const mixed = destination.stream;
  if (!mixed.getAudioTracks().length) {
    closeMixGraph();
    stopInputStreams();
    return { stream: baseStream, micAdded: false, micError };
  }
  return { stream: mixed, micAdded, micError };
};

const ensureStream = async (mode, options = {}) => {
  const { force = false } = options;
  const selectedDeviceId = mode === "system" ? els.deviceSelect.value || "" : "";
  const includeMic =
    mode === "system"
      ? true
      : Boolean(els.includeMic ? els.includeMic.checked : true);
  const selectedMicId =
    includeMic && els.micSelect ? String(els.micSelect.value || "").trim() : "";
  const nextStreamKey = `${mode}:${selectedDeviceId}:${includeMic ? "mic" : "nomic"}:${selectedMicId || "auto"}`;
  const canReuse =
    !force &&
    state.stream &&
    state.streamKey === nextStreamKey;
  if (canReuse) return state.stream;

  if (state.stream) {
    try {
      state.stream.getTracks().forEach((track) => track.stop());
    } catch (err) {
      void err;
    }
  }
  state.stream = null;
  state.streamDeviceId = "";
  state.streamKey = "";
  state.screenAudioMissing = false;
  state.screenAudioDriverFallback = false;
  state.micAdded = false;
  closeMixGraph();
  stopInputStreams();
  // Короткая пауза снижает шанс NotReadable/AbortError при быстром reopen того же устройства.
  await sleepMs(120);

  let baseStream;
  if (mode === "screen") {
    const result = await openScreenCaptureStream();
    baseStream = result.stream;
    state.screenAudioMissing = Boolean(result.audioMissing) || !baseStream.getAudioTracks().length;
    state.screenAudioDriverFallback = false;
    if (state.screenAudioMissing) {
      const driverFallback = await openSystemDriverFallbackStream();
      if (driverFallback && driverFallback.stream && driverFallback.stream.getAudioTracks().length) {
        stopStreamTracksSafe(baseStream);
        baseStream = driverFallback.stream;
        state.streamDeviceId = driverFallback.deviceId || "";
        state.screenAudioMissing = false;
        state.screenAudioDriverFallback = true;
      } else {
        setSignal("signal_no_audio");
        console.warn("screen capture started without audio track");
      }
    }
  } else {
    const deviceId = els.deviceSelect.value;
    const openStreamForDevice = async (targetDeviceId) => {
      const constraints = {
        audio: targetDeviceId ? { deviceId: { exact: targetDeviceId } } : true,
      };
      return withBusyRetry(() => navigator.mediaDevices.getUserMedia(constraints));
    };

    try {
      baseStream = await openStreamForDevice(deviceId);
      state.streamDeviceId = deviceId || "";
    } catch (err) {
      if (!isDeviceBusyError(err) || !deviceId) {
        throw err;
      }
      const devices = await navigator.mediaDevices.enumerateDevices();
      const fallbacks = devices
        .filter((d) => d.kind === "audioinput" && d.deviceId && d.deviceId !== deviceId)
        .sort((left, right) => {
          const lv = isVirtualAudioDevice(left.label) ? 1 : 0;
          const rv = isVirtualAudioDevice(right.label) ? 1 : 0;
          return rv - lv;
        });
      let fallbackError = err;
      let opened = false;
      for (const candidate of fallbacks) {
        try {
          baseStream = await openStreamForDevice(candidate.deviceId);
          state.streamDeviceId = candidate.deviceId;
          if (els.deviceSelect) {
            els.deviceSelect.value = candidate.deviceId;
          }
          setStatusHint("warn_system_source_fallback", "bad");
          opened = true;
          break;
        } catch (candidateErr) {
          fallbackError = candidateErr;
        }
      }
      if (!opened) {
        throw fallbackError;
      }
    }
  }

  if (includeMic) {
    const mixed = await buildMixedAudioStream(baseStream, true, selectedMicId, { mode });
    state.stream = mixed.stream;
    state.micAdded = mixed.micAdded;
    if (!mixed.micAdded && mixed.micError === "mic_same_as_system") {
      setStatusHint("err_mic_same_as_system", "bad");
    } else if (!mixed.micAdded) {
      setStatusHint("warn_mic_not_added", "bad");
    }
  } else {
    state.stream = baseStream;
    state.inputStreams = [baseStream];
    state.micAdded = false;
  }
  state.streamMode = mode;
  state.streamKey = nextStreamKey;
  return state.stream;
};

const closeAudioMeter = () => {
  stopMeter();
  if (state.meterNodes && state.meterNodes.length) {
    state.meterNodes.forEach((node) => {
      try {
        if (node && typeof node.disconnect === "function") {
          node.disconnect();
        }
      } catch (err) {
        void err;
      }
    });
  }
  state.meterNodes = [];
  if (state.audioContext) {
    state.audioContext.close().catch(() => {});
  }
  state.audioContext = null;
  state.analyser = null;
  state.analyserSystem = null;
  state.analyserMic = null;
  state.meterLevels = { mixed: 0, system: 0, mic: 0 };
  state.meterMode = "";
  renderMeterDetailLabels();
};

const releasePreparedCapture = () => {
  if (state.stream) {
    try {
      state.stream.getTracks().forEach((track) => track.stop());
    } catch (err) {
      void err;
    }
  }
  state.stream = null;
  state.streamDeviceId = "";
  state.streamKey = "";
  state.screenAudioMissing = false;
  state.screenAudioDriverFallback = false;
  state.micAdded = false;
  closeMixGraph();
  stopInputStreams();
  closeAudioMeter();
};

const mapStartError = (err, mode) => {
  const name = err && typeof err === "object" ? err.name || "" : "";
  const message = err && typeof err === "object" ? err.message || "" : String(err || "");
  if (name === "NotAllowedError" || name === "SecurityError") return "err_media_denied";
  if (name === "NotFoundError" || name === "OverconstrainedError") return "err_media_not_found";
  if (name === "NotReadableError" || name === "AbortError") return "err_media_not_readable";
  if (message.includes("preflight_no_audio_track")) return "err_media_not_readable";
  if (message.includes("no_device_selected")) return "err_no_device_selected";
  if (message.includes("interview_meta_missing")) return "err_interview_meta_missing";
  if (message.includes("system_source_not_virtual")) return "err_system_source_not_virtual";
  if (message.includes("capture_locked_other_tab")) return "err_capture_locked_other_tab";
  if (message.includes("start_meeting_failed")) return "err_server_start";
  if (message.includes("start meeting failed")) return "err_server_start";
  if (message.includes("ws_open_failed")) return "err_network";
  if (message.includes("stream_missing_after_countdown")) return "err_media_not_readable";
  if (message.includes("Failed to fetch") || message.includes("NetworkError")) return "err_network";
  if (message.includes("pcm_capture_unsupported")) return "err_recorder_init";
  if (message.includes("diagnostics_failed")) return "err_diagnostics_failed";
  if (message.includes("work_mode_realtime_only")) return "err_work_mode_realtime_only";
  if (message.includes("mic_same_as_system")) return "err_mic_same_as_system";
  if (name === "NotSupportedError" || name === "TypeError") return "err_recorder_init";
  if (message.includes("MediaRecorder")) return "err_recorder_init";
  if (mode === "screen" && message.includes("no audio track")) return "err_screen_audio_missing";
  return "err_generic";
};

const buildAudioMeter = async (mode, options = {}) => {
  const { force = false } = options;
  if (state.audioContext && !force && state.meterMode === mode) return;
  closeAudioMeter();
  const stream = await ensureStream(mode, { force });
  const Ctx = window.AudioContext || window.webkitAudioContext;
  if (!Ctx) return;
  state.audioContext = new Ctx();
  await ensureAudioContextActive(state.audioContext);
  state.meterNodes = [];
  const attachAnalyser = (targetStream) => {
    if (!targetStream || !targetStream.getAudioTracks().length) return null;
    const source = state.audioContext.createMediaStreamSource(targetStream);
    const analyser = state.audioContext.createAnalyser();
    analyser.fftSize = 1024;
    source.connect(analyser);
    state.meterNodes.push(source, analyser);
    return analyser;
  };
  state.analyser = attachAnalyser(stream);
  const systemStream = state.inputStreams.length ? state.inputStreams[0] : null;
  const micStream =
    state.inputStreams.length > 1 ? state.inputStreams[state.inputStreams.length - 1] : null;
  state.analyserSystem = attachAnalyser(systemStream);
  state.analyserMic = attachAnalyser(micStream);
  state.meterMode = mode;
  state.signalPeak = 0;
  state.signalSmooth = 0;
  state.meterLevels = { mixed: 0, system: 0, mic: 0 };
  renderMeterDetailLabels();
};

const updateMeter = () => {
  const calcLevel = (analyser) => {
    if (!analyser) return 0;
    const buffer = new Uint8Array(analyser.fftSize);
    analyser.getByteTimeDomainData(buffer);
    let sum = 0;
    for (let i = 0; i < buffer.length; i += 1) {
      const v = (buffer[i] - 128) / 128;
      sum += v * v;
    }
    const rms = Math.sqrt(sum / buffer.length);
    return Math.min(1, rms * 2.5);
  };

  const mixedLevel = calcLevel(state.analyser);
  if (mixedLevel <= 0 && !state.analyserSystem && !state.analyserMic) {
    updateLiveMonitorFromLevels({ mixed: 0, system: 0, mic: 0 });
    return;
  }
  const systemLevel = calcLevel(state.analyserSystem);
  const micLevel = calcLevel(state.analyserMic);
  state.meterLevels = {
    mixed: mixedLevel,
    system: systemLevel,
    mic: micLevel,
  };
  updateLiveMonitorFromLevels(state.meterLevels);
  renderMeterDetailLabels();
  if (els.systemLevelBar) {
    els.systemLevelBar.style.transform = `scaleX(${systemLevel})`;
  }
  if (els.micLevelBar) {
    els.micLevelBar.style.transform = `scaleX(${micLevel})`;
  }

  const level = mixedLevel;
  state.signalSmooth =
    state.signalSmooth <= 0
      ? level
      : state.signalSmooth * (1 - SIGNAL_SMOOTHING_ALPHA) + level * SIGNAL_SMOOTHING_ALPHA;
  const smoothed = state.signalSmooth;
  state.signalPeak = Math.max(state.signalPeak, level);
  els.levelBar.style.transform = `scaleX(${level})`;
  let nextSignal = state.signalState || "signal_waiting";
  if (nextSignal === "signal_ok") {
    if (smoothed < SIGNAL_OK_EXIT) {
      nextSignal = smoothed >= SIGNAL_LOW_ENTER ? "signal_low" : "signal_waiting";
    }
  } else if (nextSignal === "signal_low") {
    if (smoothed >= SIGNAL_OK_ENTER) {
      nextSignal = "signal_ok";
    } else if (smoothed < SIGNAL_LOW_EXIT) {
      nextSignal = "signal_waiting";
    }
  } else if (smoothed >= SIGNAL_OK_ENTER) {
    nextSignal = "signal_ok";
  } else if (smoothed >= SIGNAL_LOW_ENTER) {
    nextSignal = "signal_low";
  } else {
    nextSignal = "signal_waiting";
  }
  if (nextSignal !== state.signalState) {
    setSignal(nextSignal);
  }
};

const startMeter = () => {
  if (state.levelTimer) return;
  state.levelTimer = setInterval(updateMeter, 120);
};

const stopMeter = () => {
  if (state.levelTimer) clearInterval(state.levelTimer);
  state.levelTimer = null;
  els.levelBar.style.transform = "scaleX(0)";
  if (els.systemLevelBar) els.systemLevelBar.style.transform = "scaleX(0)";
  if (els.micLevelBar) els.micLevelBar.style.transform = "scaleX(0)";
  state.meterLevels = { mixed: 0, system: 0, mic: 0 };
  renderMeterDetailLabels();
  state.signalSmooth = 0;
  updateLiveMonitorFromLevels(state.meterLevels);
};

const flushPendingChunks = () => {
  if (!state.ws || state.ws.readyState !== WebSocket.OPEN) return;
  while (state.pendingChunks.length > 0) {
    const payload = state.pendingChunks.shift();
    try {
      state.ws.send(JSON.stringify(payload));
    } catch (err) {
      state.pendingChunks.unshift(payload);
      break;
    }
  }
};

const clearHttpDrainTimer = () => {
  if (state.httpDrainTimer) {
    clearTimeout(state.httpDrainTimer);
  }
  state.httpDrainTimer = null;
};

const clearWsReconnectTimer = () => {
  if (state.wsReconnectTimer) {
    clearTimeout(state.wsReconnectTimer);
  }
  state.wsReconnectTimer = null;
};

const clearWsHeartbeat = () => {
  if (state.wsHeartbeatTimer) {
    clearInterval(state.wsHeartbeatTimer);
  }
  state.wsHeartbeatTimer = null;
  if (state.wsPongTimer) {
    clearTimeout(state.wsPongTimer);
  }
  state.wsPongTimer = null;
  state.wsAwaitingPong = false;
};

const markWsServerActivity = () => {
  state.wsHasServerActivity = true;
  state.wsLastServerActivityMs = Date.now();
  if (state.statusHintKey === "err_network") {
    setStatusHint("hint_recording_record_first", "good");
  }
};

const markWsNetworkIssue = () => {
  // Не показываем фатальный network-hint, если очередь пустая:
  // иногда это краткий ws-reconnect без потери чанков.
  if (state.pendingChunks.length > 0) {
    setStatusHint("err_network", "bad");
  }
};

const handleWsPong = (payload = {}) => {
  markWsServerActivity();
  if (state.wsPongTimer) {
    clearTimeout(state.wsPongTimer);
  }
  state.wsPongTimer = null;
  state.wsAwaitingPong = false;
  if (typeof payload.last_acked_seq === "number") {
    state.lastAckSeq = Math.max(state.lastAckSeq, payload.last_acked_seq);
  }
};

const sendWsResume = () => {
  if (!state.ws || state.ws.readyState !== WebSocket.OPEN) return;
  if (!state.meetingId) return;
  try {
    state.ws.send(
      JSON.stringify({
        event_type: "session.resume",
        meeting_id: state.meetingId,
        last_seq: state.lastAckSeq,
        pending_chunks: state.pendingChunks.length,
      })
    );
  } catch (err) {
    console.warn("ws resume failed", err);
  }
};

const sendWsHeartbeat = () => {
  if (!state.ws || state.ws.readyState !== WebSocket.OPEN) return;
  if (!state.meetingId) return;

  const now = Date.now();
  const inBootstrapGrace =
    !state.wsHasServerActivity &&
    state.wsBootstrapDeadlineMs > 0 &&
    now < state.wsBootstrapDeadlineMs;

  if (inBootstrapGrace) {
    try {
      state.ws.send(
        JSON.stringify({
          event_type: "ping",
          meeting_id: state.meetingId,
          ts_ms: now,
          last_seq: state.lastAckSeq,
          bootstrap: true,
        })
      );
    } catch (err) {
      console.warn("ws ping failed (bootstrap)", err);
      scheduleWsReconnect();
      scheduleHttpDrain();
    }
    return;
  }

  if (state.wsAwaitingPong) {
    markWsNetworkIssue();
    try {
      state.ws.close();
    } catch (err) {
      void err;
    }
    scheduleWsReconnect();
    scheduleHttpDrain();
    return;
  }

  state.wsAwaitingPong = true;
  if (state.wsPongTimer) {
    clearTimeout(state.wsPongTimer);
  }
  state.wsPongTimer = setTimeout(() => {
    state.wsPongTimer = null;
    state.wsAwaitingPong = false;
    markWsNetworkIssue();
    try {
      if (state.ws) state.ws.close();
    } catch (err) {
      void err;
    }
    scheduleWsReconnect();
    scheduleHttpDrain();
  }, WS_PONG_TIMEOUT_MS);

  try {
    state.ws.send(
      JSON.stringify({
        event_type: "ping",
        meeting_id: state.meetingId,
        ts_ms: now,
        last_seq: state.lastAckSeq,
      })
    );
  } catch (err) {
    console.warn("ws ping failed", err);
    if (state.wsPongTimer) {
      clearTimeout(state.wsPongTimer);
    }
    state.wsPongTimer = null;
    state.wsAwaitingPong = false;
    scheduleWsReconnect();
    scheduleHttpDrain();
  }
};

const startWsHeartbeat = () => {
  clearWsHeartbeat();
  if (!state.ws || state.ws.readyState !== WebSocket.OPEN) return;
  if (!state.meetingId) return;
  state.wsHeartbeatTimer = setInterval(sendWsHeartbeat, WS_HEARTBEAT_INTERVAL_MS);
};

const scheduleWsReconnect = () => {
  if (state.stopRequested || !state.captureStopper) return;
  if (state.wsReconnectTimer) return;
  const attempt = Math.min(state.wsReconnectAttempts + 1, 8);
  state.wsReconnectAttempts = attempt;
  const delayMs = Math.min(3800, 350 * 2 ** (attempt - 1));

  state.wsReconnectTimer = setTimeout(async () => {
    state.wsReconnectTimer = null;
    if (state.stopRequested || !state.captureStopper) return;
    try {
      await waitForWsOpen(5200);
      state.wsReconnectAttempts = 0;
      flushPendingChunks();
      if (state.statusHintKey === "err_network") {
        setStatusHint("hint_recording_record_first", "good");
      }
    } catch (err) {
      scheduleWsReconnect();
    }
  }, delayMs);
};

const scheduleHttpDrain = () => {
  if (state.stopRequested || !state.captureStopper) return;
  if (!state.pendingChunks.length) return;
  if (state.httpDrainTimer || state.httpDrainInProgress) return;
  if (state.ws && state.ws.readyState === WebSocket.OPEN) return;
  state.httpDrainTimer = setTimeout(async () => {
    state.httpDrainTimer = null;
    await drainPendingChunksHttp(state.meetingId, { force: false, reschedule: true });
  }, HTTP_DRAIN_INTERVAL_MS);
};

const queueOrSendChunk = (payload) => {
  if (state.ws && state.ws.readyState === WebSocket.OPEN) {
    try {
      state.ws.send(JSON.stringify(payload));
      return;
    } catch (err) {
      state.pendingChunks.push(payload);
      scheduleWsReconnect();
      return;
    }
  }
  state.pendingChunks.push(payload);
  scheduleWsReconnect();
  scheduleHttpDrain();
};

const toBase64 = async (blob) => {
  const buffer = await blob.arrayBuffer();
  const bytes = new Uint8Array(buffer);
  let binary = "";
  for (let i = 0; i < bytes.length; i += 1) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
};

const sendChunk = async (blob, mimeType, sourceTrack = "mixed") => {
  if (!state.meetingId) return;
  if (state.stopRequested && (!state.ws || state.ws.readyState !== WebSocket.OPEN)) {
    return;
  }
  const track = String(sourceTrack || "mixed").trim().toLowerCase();
  const content_b64 = await toBase64(blob);
  const payload = {
    schema_version: "v1",
    event_type: "audio.chunk",
    meeting_id: state.meetingId,
    seq: state.seq,
    timestamp_ms: Date.now(),
    codec: mimeType || "audio/webm",
    sample_rate: state.audioContext ? state.audioContext.sampleRate : 48000,
    channels: 1,
    source_track: track,
    quality_profile: String(getQualityConfig().wsQualityProfile || "live_balanced"),
    mixed_level: Number((state.meterLevels.mixed || 0).toFixed(4)),
    system_level: Number((state.meterLevels.system || 0).toFixed(4)),
    mic_level: Number((state.meterLevels.mic || 0).toFixed(4)),
    idempotency_key: `${state.meetingId}:${state.seq}:${Date.now()}`,
    content_b64,
  };
  queueOrSendChunk(payload);
  state.seq += 1;
  state.chunkCount += 1;
  els.chunkCount.textContent = String(state.chunkCount);
  if (state.chunkCount >= 4 && state.nonEmptyRawUpdates === 0) {
    setSignal("signal_no_audio");
    const protectedHints = new Set([
      "warn_mic_not_added",
      "warn_system_source_fallback",
      "warn_screen_audio_mic_only",
      "err_media_denied",
      "err_media_not_found",
      "err_media_not_readable",
      "err_screen_audio_missing",
      "err_recorder_init",
      "err_network",
      "err_server_start",
      "err_no_device_selected",
      "err_system_source_not_virtual",
    ]);
    if (!protectedHints.has(state.statusHintKey)) {
      setStatusHint("hint_no_speech_yet", "bad");
    }
  }
};

const openWebSocket = () => {
  if (state.ws) return state.ws;
  const base = window.location.origin.replace("http", "ws");
  const ws = new WebSocket(`${base}/v1/ws`);
  state.ws = ws;
  ws.onopen = () => {
    clearWsReconnectTimer();
    clearHttpDrainTimer();
    state.wsReconnectAttempts = 0;
    handleWsPong();
    sendWsResume();
    flushPendingChunks();
    startWsHeartbeat();
  };
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data && data.event_type === "ws.pong") {
        handleWsPong(data);
        return;
      }
      if (data && data.event_type === "ws.resumed") {
        markWsServerActivity();
        if (typeof data.last_acked_seq === "number") {
          state.lastAckSeq = Math.max(state.lastAckSeq, data.last_acked_seq);
        }
        flushPendingChunks();
        return;
      }
      if (data && data.event_type === "ws.ack") {
        markWsServerActivity();
        if (typeof data.last_acked_seq === "number") {
          state.lastAckSeq = Math.max(state.lastAckSeq, data.last_acked_seq);
        } else if (typeof data.seq === "number") {
          state.lastAckSeq = Math.max(state.lastAckSeq, data.seq);
        }
        return;
      }
      markWsServerActivity();
      if (data && data.event_type === "transcript.update") {
        // Record-first mode: live transcript is disabled in UI/runtime.
        return;
      }
    } catch (err) {
      console.warn("ws message parse failed", err);
    }
  };
  ws.onclose = (event) => {
    clearWsHeartbeat();
    const normalCloseCode = 1000;
    if (state.captureStopper && !state.stopRequested && (!event || event.code !== normalCloseCode)) {
      scheduleWsReconnect();
      scheduleHttpDrain();
    }
    state.ws = null;
  };
  return ws;
};

const waitForWsOpen = (timeoutMs = 4000) =>
  new Promise((resolve, reject) => {
    const ws = openWebSocket();
    if (ws.readyState === WebSocket.OPEN) {
      resolve();
      return;
    }
    if (ws.readyState === WebSocket.CLOSING || ws.readyState === WebSocket.CLOSED) {
      reject(new Error("ws_open_failed"));
      return;
    }
    const timer = setTimeout(() => {
      cleanup();
      reject(new Error("ws_open_failed"));
    }, timeoutMs);
    const cleanup = () => {
      clearTimeout(timer);
      ws.removeEventListener("open", onOpen);
      ws.removeEventListener("error", onError);
      ws.removeEventListener("close", onClose);
    };
    const onOpen = () => {
      cleanup();
      resolve();
    };
    const onError = () => {
      cleanup();
      reject(new Error("ws_open_failed"));
    };
    const onClose = () => {
      cleanup();
      reject(new Error("ws_open_failed"));
    };
    ws.addEventListener("open", onOpen);
    ws.addEventListener("error", onError);
    ws.addEventListener("close", onClose);
  });

const createRecorderWithFallback = (stream) => {
  const candidates = [
    "video/webm;codecs=vp8,opus",
    "video/webm",
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/ogg;codecs=opus",
    "audio/mp4;codecs=mp4a.40.2",
    "audio/mp4",
    "video/mp4",
  ];

  const tryCreate = (targetStream) => {
    let lastError = null;
    for (const mimeType of candidates) {
      if (typeof MediaRecorder.isTypeSupported === "function" && !MediaRecorder.isTypeSupported(mimeType)) {
        continue;
      }
      try {
        const recorder = new MediaRecorder(targetStream, { mimeType });
        return { recorder, mimeType };
      } catch (err) {
        lastError = err;
      }
    }
    try {
      return { recorder: new MediaRecorder(targetStream), mimeType: "" };
    } catch (err) {
      if (lastError) throw lastError;
      throw err;
    }
  };

  try {
    return tryCreate(stream);
  } catch (err) {
    const audioTracks = stream.getAudioTracks();
    if (!audioTracks.length) throw err;
    const audioOnlyStream = new MediaStream(audioTracks);
    return tryCreate(audioOnlyStream);
  }
};

const encodeWav = (samples, sampleRate) => {
  const dataSize = samples.length * 2;
  const buffer = new ArrayBuffer(44 + dataSize);
  const view = new DataView(buffer);
  const writeString = (offset, value) => {
    for (let i = 0; i < value.length; i += 1) {
      view.setUint8(offset + i, value.charCodeAt(i));
    }
  };

  writeString(0, "RIFF");
  view.setUint32(4, 36 + dataSize, true);
  writeString(8, "WAVE");
  writeString(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true); // PCM
  view.setUint16(22, 1, true); // mono
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeString(36, "data");
  view.setUint32(40, dataSize, true);

  let offset = 44;
  for (let i = 0; i < samples.length; i += 1) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    offset += 2;
  }

  return new Blob([buffer], { type: "audio/wav" });
};

const createPcmCapture = (stream, sourceTrack = "mixed") => {
  const Ctx = window.AudioContext || window.webkitAudioContext;
  if (!Ctx) throw new Error("pcm_capture_unsupported");

  const ctx = new Ctx();
  const source = ctx.createMediaStreamSource(stream);
  if (!ctx.createScriptProcessor) throw new Error("pcm_capture_unsupported");
  const processor = ctx.createScriptProcessor(4096, 1, 1);
  const sink = ctx.createGain();
  sink.gain.value = 0;

  const chunks = [];
  let flushing = false;

  const flush = async () => {
    if (flushing || !chunks.length) return;
    flushing = true;
    try {
      const totalLength = chunks.reduce((sum, part) => sum + part.length, 0);
      const merged = new Float32Array(totalLength);
      let cursor = 0;
      chunks.splice(0).forEach((part) => {
        merged.set(part, cursor);
        cursor += part.length;
      });
      const wavBlob = encodeWav(merged, ctx.sampleRate || 48000);
      await sendChunk(wavBlob, "audio/wav", sourceTrack);
    } finally {
      flushing = false;
    }
  };

  processor.onaudioprocess = (event) => {
    const input = event.inputBuffer.getChannelData(0);
    chunks.push(new Float32Array(input));
  };

  source.connect(processor);
  processor.connect(sink);
  sink.connect(ctx.destination);
  void ensureAudioContextActive(ctx);

  const timer = setInterval(() => {
    void flush();
  }, getCaptureTimesliceMs());

  return {
    engine: "pcm",
    stop: async () => {
      clearInterval(timer);
      processor.onaudioprocess = null;
      try {
        await flush();
      } catch (err) {
        console.warn("pcm flush failed", err);
      }
      try {
        source.disconnect();
      } catch (err) {
        void err;
      }
      try {
        processor.disconnect();
      } catch (err) {
        void err;
      }
      try {
        sink.disconnect();
      } catch (err) {
        void err;
      }
      try {
        await ctx.close();
      } catch (err) {
        void err;
      }
    },
  };
};

const createMediaRecorderCapture = (stream, sourceTrack = "mixed") => {
  const { recorder, mimeType } = createRecorderWithFallback(stream);
  recorder.onerror = () => {
    if (!state.stopRequested) {
      setStatusHint("warn_capture_stream_interrupted", "bad");
    }
  };
  recorder.onstop = () => {
    if (!state.stopRequested) {
      setStatusHint("warn_capture_stream_interrupted", "bad");
    }
  };
  recorder.ondataavailable = async (e) => {
    if (e.data && e.data.size > 0) {
      await sendChunk(e.data, mimeType || e.data.type, sourceTrack);
    }
  };
  recorder.start(getCaptureTimesliceMs());
  return {
    engine: "media",
    stop: async () => {
      if (recorder.state === "inactive") return;
      await new Promise((resolve) => {
        let done = false;
        const finish = () => {
          if (done) return;
          done = true;
          resolve();
        };
        recorder.addEventListener("stop", finish, { once: true });
        recorder.addEventListener("error", finish, { once: true });
        setTimeout(finish, 1200);
        try {
          recorder.stop();
        } catch (err) {
          finish();
        }
      });
      await new Promise((resolve) => setTimeout(resolve, 220));
    },
  };
};

const createCaptureEngine = (stream, options = {}) => {
  const { sourceTrack = "mixed" } = options;
  if (PREFER_PCM_CAPTURE) {
    try {
      return { ...createPcmCapture(stream, sourceTrack), fallbackToPcm: false, sourceTrack };
    } catch (err) {
      console.warn("pcm capture fallback to MediaRecorder", err);
    }
  }
  try {
    return {
      ...createMediaRecorderCapture(stream, sourceTrack),
      fallbackToPcm: false,
      sourceTrack,
    };
  } catch (mediaErr) {
    console.warn("media capture fallback to pcm", mediaErr);
    return { ...createPcmCapture(stream, sourceTrack), fallbackToPcm: true, sourceTrack };
  }
};

const startBackupRecorder = () => {
  if (!state.stream) return;
  try {
    const { recorder, mimeType } = createRecorderWithFallback(state.stream);
    const chunks = [];
    recorder.ondataavailable = (event) => {
      if (event.data && event.data.size > 0) {
        chunks.push(event.data);
      }
    };
    recorder.start(1000);
    state.backupRecorder = {
      recorder,
      chunks,
      mimeType: mimeType || "audio/webm",
    };
  } catch (err) {
    console.warn("backup recorder init failed", err);
    state.backupRecorder = null;
  }
};

const stopBackupRecorder = async () => {
  const current = state.backupRecorder;
  state.backupRecorder = null;
  if (!current) return null;
  const { recorder, chunks, mimeType } = current;

  if (recorder && recorder.state !== "inactive") {
    await new Promise((resolve) => {
      let settled = false;
      const done = () => {
        if (settled) return;
        settled = true;
        resolve();
      };
      recorder.addEventListener("stop", done, { once: true });
      recorder.addEventListener("error", done, { once: true });
      setTimeout(done, 1600);
      try {
        recorder.stop();
      } catch (err) {
        done();
      }
    });
  }

  if (!chunks || !chunks.length) return null;
  const mediaType = mimeType || chunks[0]?.type || "audio/webm";
  return new Blob(chunks, { type: mediaType });
};

const uploadBackupAudio = async (meetingId, blob) => {
  if (!meetingId || !blob || blob.size <= 8192) return true;
  const extFromType = (() => {
    if (!blob.type) return "webm";
    if (blob.type.includes("ogg")) return "ogg";
    if (blob.type.includes("wav")) return "wav";
    if (blob.type.includes("mp4")) return "mp4";
    if (blob.type.includes("mpeg")) return "mp3";
    return "webm";
  })();
  const filename = `backup_audio.${extFromType}`;
  const form = new FormData();
  form.append("file", blob, filename);
  try {
    const res = await fetch(`/v1/meetings/${meetingId}/backup-audio`, {
      method: "POST",
      headers: buildAuthHeaders(),
      body: form,
    });
    return res.ok;
  } catch (err) {
    return false;
  }
};

const setCheckSignalBusy = (busy) => {
  state.signalCheckInProgress = busy;
  syncCheckSignalButton();
};

const renderTranscript = () => {
  const orderedRaw = Array.from(state.transcript.raw.entries())
    .sort((a, b) => a[0] - b[0])
    .map(([, text]) => text)
    .filter(Boolean)
    .join("\n");
  const orderedClean = Array.from(state.transcript.enhanced.entries())
    .sort((a, b) => a[0] - b[0])
    .map(([, text]) => text)
    .filter(Boolean)
    .join("\n");
  const setAreaValue = (area, nextValue) => {
    if (!area) return;
    const pinnedToBottom = area.scrollTop + area.clientHeight >= area.scrollHeight - 80;
    area.value = nextValue;
    if (pinnedToBottom) {
      area.scrollTop = area.scrollHeight;
    }
  };
  setAreaValue(els.transcriptRaw, orderedRaw);
  setAreaValue(els.transcriptClean, orderedClean);
  renderTranscriptVisibility();
};

const handleTranscriptUpdate = (data) => {
  if (!data || data.event_type !== "transcript.update") return;
  if (state.captureStopper && !state.stopRequested) return;
  if (typeof data.seq !== "number") return;

  if (typeof data.raw_text === "string") {
      state.transcript.raw.set(data.seq, data.raw_text);
      if (data.raw_text.trim()) {
        state.nonEmptyRawUpdates += 1;
        setSignal("signal_ok");
      if (
        state.statusHintKey === "hint_no_speech_yet" ||
        state.statusHintKey === "signal_check_fail"
      ) {
        setStatusHint("hint_recording_record_first", "good");
      }
    }
  }

  if (data.enhanced_text != null) {
    if (state.enhancedTimers.has(data.seq)) {
      clearTimeout(state.enhancedTimers.get(data.seq));
      state.enhancedTimers.delete(data.seq);
    }
    const timer = setTimeout(() => {
      state.transcript.enhanced.set(data.seq, data.enhanced_text);
      state.enhancedTimers.delete(data.seq);
      renderTranscript();
    }, 3500);
    state.enhancedTimers.set(data.seq, timer);
  }

  renderTranscript();
};

const resetSessionState = () => {
  clearWsHeartbeat();
  state.backupRecorder = null;
  state.seq = 0;
  state.chunkCount = 0;
  state.pendingChunks = [];
  state.httpDrainInProgress = false;
  clearHttpDrainTimer();
  state.signalPeak = 0;
  state.signalSmooth = 0;
  state.signalState = "signal_waiting";
  state.lastAckSeq = -1;
  state.wsHasServerActivity = false;
  state.wsBootstrapDeadlineMs = 0;
  state.wsLastServerActivityMs = 0;
  state.nonEmptyRawUpdates = 0;
  setSignal("signal_waiting");
  els.chunkCount.textContent = "0";
  state.transcript.raw.clear();
  state.transcript.enhanced.clear();
  state.enhancedTimers.forEach((timer) => clearTimeout(timer));
  state.enhancedTimers.clear();
  if (els.transcriptRaw) els.transcriptRaw.value = "";
  if (els.transcriptClean) els.transcriptClean.value = "";
  setTranscriptUiState("waiting");
  resetLiveMonitor();
  state.diagnosticsLast = null;
  refreshRecognitionDiagnosis();
};

const getSelectedSystemDeviceLabel = () => {
  if (!els.deviceSelect || !els.deviceSelect.options.length) return "";
  const index = Math.max(0, els.deviceSelect.selectedIndex);
  const option = els.deviceSelect.options[index];
  return String(option && option.textContent ? option.textContent : "").trim();
};

const validateSystemSourceSelection = () => {
  const label = getSelectedSystemDeviceLabel();
  if (!label) return;
  if (!isVirtualAudioDevice(label)) {
    throw new Error("system_source_not_virtual");
  }
};

const runCapturePreflight = async (mode) => {
  if (mode !== "system") return;
  const deviceId = (els.deviceSelect && els.deviceSelect.value) || "";
  if (!deviceId) {
    throw new Error("no_device_selected");
  }
  validateSystemSourceSelection();

  let probeStream = null;
  try {
    probeStream = await withBusyRetry(() =>
      navigator.mediaDevices.getUserMedia({
        audio: { deviceId: { exact: deviceId } },
      })
    );
    const tracks = probeStream.getAudioTracks();
    if (!tracks.length) {
      throw new Error("preflight_no_audio_track");
    }
  } finally {
    if (probeStream) {
      try {
        probeStream.getTracks().forEach((track) => track.stop());
      } catch (err) {
        void err;
      }
    }
    // Safari/Chrome иногда освобождают аудио-девайс не мгновенно после stop().
    await sleepMs(140);
  }
};

const buildCaptureTargets = (captureMode) => {
  const targets = [];
  const hasInputStreams = Array.isArray(state.inputStreams) && state.inputStreams.length > 0;
  if (hasInputStreams) {
    const systemStream = state.inputStreams[0] || null;
    const micStream =
      state.inputStreams.length > 1 ? state.inputStreams[state.inputStreams.length - 1] : null;
    if (systemStream && systemStream.getAudioTracks().length) {
      targets.push({ stream: systemStream, sourceTrack: "system" });
    }
    if (micStream && micStream.getAudioTracks().length) {
      targets.push({ stream: micStream, sourceTrack: "mic" });
    }
  }

  if (!targets.length && state.stream) {
    let fallbackTrack = "mixed";
    if (captureMode === "screen" && state.screenAudioMissing && state.micAdded) {
      fallbackTrack = "mic";
    } else if (!state.micAdded) {
      fallbackTrack = "system";
    }
    targets.push({ stream: state.stream, sourceTrack: fallbackTrack });
  }

  const unique = [];
  targets.forEach((item) => {
    if (!item.stream) return;
    const exists = unique.some(
      (prev) => prev.stream === item.stream && prev.sourceTrack === item.sourceTrack
    );
    if (!exists) unique.push(item);
  });
  return unique;
};

const loadFinalTranscripts = async (meetingId) => {
  if (!meetingId) return;
  setTranscriptUiState("loading");
  try {
    const [rawRes, cleanRes] = await Promise.all([
      fetch(`/v1/meetings/${meetingId}/artifact?kind=raw&fmt=txt`, { headers: buildAuthHeaders() }),
      fetch(`/v1/meetings/${meetingId}/artifact?kind=clean&fmt=txt`, { headers: buildAuthHeaders() }),
    ]);
    const rawText = rawRes.ok ? await rawRes.text() : "";
    const cleanText = cleanRes.ok ? await cleanRes.text() : "";
    state.transcript.raw.clear();
    state.transcript.enhanced.clear();
    if (rawText.trim()) state.transcript.raw.set(0, rawText);
    if (cleanText.trim()) state.transcript.enhanced.set(0, cleanText);
    renderTranscript();
    setTranscriptUiState(hasTranscriptContent() ? "ready" : "empty");
  } catch (err) {
    setTranscriptUiState("empty");
    console.warn("load final transcripts failed", err);
  }
};

const drainPendingChunksHttp = async (meetingId, options = {}) => {
  const { force = false, reschedule = false } = options;
  if (!meetingId || !state.pendingChunks.length) return;
  if (state.httpDrainInProgress) return;
  if (!force && state.ws && state.ws.readyState === WebSocket.OPEN) return;

  state.httpDrainInProgress = true;
  const pending = [...state.pendingChunks];
  state.pendingChunks = [];
  for (const payload of pending) {
    try {
      const res = await fetch(`/v1/meetings/${meetingId}/chunks`, {
        method: "POST",
        headers: buildHeaders(),
        body: JSON.stringify({
          seq: payload.seq,
          content_b64: payload.content_b64,
          codec: payload.codec,
          sample_rate: payload.sample_rate,
          channels: payload.channels,
          source_track: payload.source_track || "mixed",
          quality_profile: payload.quality_profile || String(getQualityConfig().wsQualityProfile || "live_balanced"),
          mixed_level:
            typeof payload.mixed_level === "number" ? payload.mixed_level : undefined,
          system_level:
            typeof payload.system_level === "number" ? payload.system_level : undefined,
          mic_level: typeof payload.mic_level === "number" ? payload.mic_level : undefined,
          idempotency_key: payload.idempotency_key,
        }),
      });
      if (!res.ok) {
        state.pendingChunks.push(payload);
      }
    } catch (err) {
      state.pendingChunks.push(payload);
    }
  }
  state.httpDrainInProgress = false;
  if (reschedule && state.pendingChunks.length && state.captureStopper && !state.stopRequested) {
    scheduleHttpDrain();
  }
};

const startCountdown = (seconds) =>
  new Promise((resolve, reject) => {
    state.isCountingDown = true;
    state.countdownValue = seconds;
    els.countdownValue.textContent = `${seconds}s`;
    setStatus("status_countdown", "idle");
    state.countdownTimer = setInterval(() => {
      if (!state.isCountingDown) {
        clearInterval(state.countdownTimer);
        state.countdownTimer = null;
        reject(new Error("countdown_cancelled"));
        return;
      }
      state.countdownValue -= 1;
      if (state.countdownValue <= 0) {
        clearInterval(state.countdownTimer);
        state.countdownTimer = null;
        state.isCountingDown = false;
        els.countdownValue.textContent = "0s";
        resolve();
      } else {
        els.countdownValue.textContent = `${state.countdownValue}s`;
      }
    }, 1000);
  });

const startRecording = async () => {
  if (state.isUploading) return;
  const workCfg = getWorkModeConfig();
  if (!workCfg.supportsRealtime) {
    setStatus("status_error", "error");
    setStatusHint("err_work_mode_realtime_only", "bad");
    setRecordingButtons(false);
    return;
  }
  const captureLock = isCaptureLockedByOtherTab();
  if (captureLock.locked) {
    setStatus("status_error", "error");
    setStatusHint("err_capture_locked_other_tab", "bad");
    setRecordingButtons(false);
    return;
  }
  setRecordingButtons(true);
  writeCaptureLock("");
  startCaptureLockHeartbeat();
  resetSessionState();
  els.countdownValue.textContent = "9s";
  const captureMode = getCaptureMode();
  let interviewMeta = null;

  try {
    interviewMeta = validateInterviewMetadata();
    if (captureMode === "system" && !els.deviceSelect.value) {
      throw new Error("no_device_selected");
    }
    await runDiagnostics({ forStart: true });
    await runCapturePreflight(captureMode);
    await ensureStream(captureMode, { force: true });
    if (captureMode === "screen" && state.screenAudioMissing && !state.micAdded) {
      throw new Error("screen capture no audio track");
    }
    await buildAudioMeter(captureMode, { force: true });
    startMeter();

    await startCountdown(9);
  } catch (err) {
    releasePreparedCapture();
    stopCaptureLockHeartbeat();
    setStatus("status_idle", "idle");
    setStatusHint("");
    setRecordingButtons(false);
    if (String(err || "").includes("countdown_cancelled")) {
      return;
    }
    setStatus("status_error", "error");
    setStatusHint(mapStartError(err, captureMode), "bad");
    return;
  }

  setStatus("status_recording", "recording");
  setStatusHint("");
  setTranscriptUiState("recording");
  state.monitor.startedAt = Date.now();
  renderLiveMonitor();
  state.stopRequested = false;
  state.wsHasServerActivity = false;
  state.wsLastServerActivityMs = 0;
  state.wsBootstrapDeadlineMs = Date.now() + WS_BOOTSTRAP_GRACE_MS;

  try {
    const res = await fetch("/v1/meetings/start", {
      method: "POST",
      headers: buildHeaders(),
      body: JSON.stringify({
        mode: "realtime",
        context: {
          source: "local_ui",
          work_mode: workCfg.contextMode,
          source_mode: workCfg.contextMode,
          locale: state.lang,
          language_profile: getLanguageProfile(),
          capture_mode: captureMode,
          ...(interviewMeta || {}),
          source_track_roles: {
            system: "candidate",
            mic: "interviewer",
          },
        },
      }),
    });
    if (!res.ok) {
      let errorCode = "";
      let errorMessage = "";
      try {
        const body = await res.json();
        const detail = body && body.detail ? body.detail : {};
        if (detail && typeof detail === "object") {
          errorCode = String(detail.code || "").trim();
          errorMessage = String(detail.message || "").trim();
        }
      } catch (_err) {
        // ignore parse errors and fallback to status-only error
      }
      if (errorCode === "active_recording_exists") {
        throw new Error(`capture_locked_other_tab:${errorMessage}`);
      }
      throw new Error(`start_meeting_failed:${res.status}:${errorCode || "unknown"}`);
    }
    const data = await res.json();
    state.meetingId = data.meeting_id;
    writeCaptureLock(state.meetingId);
    els.meetingIdText.textContent = state.meetingId;

    const stream = state.stream;
    if (!stream) {
      throw new Error("stream_missing_after_countdown");
    }
    void stream;
    state.captureEngine = "record-first";
    state.captureStopper = async () => {};
    startBackupRecorder();
    if (captureMode === "screen" && state.screenAudioDriverFallback) {
      setSignal("signal_low");
      setStatusHint("warn_screen_audio_driver_fallback", "muted");
    } else if (captureMode === "screen" && state.screenAudioMissing && state.micAdded) {
      setSignal("signal_low");
      setStatusHint("warn_screen_audio_mic_only", "bad");
    } else if (els.includeMic && els.includeMic.checked && !state.micAdded) {
      setStatusHint("warn_mic_not_added", "bad");
    } else {
      setStatusHint("hint_recording_record_first", "good");
    }
  } catch (err) {
    console.error("start recording failed", err);
    setStatus("status_error", "error");
    setStatusHint(mapStartError(err, captureMode), "bad");
    await stopRecording({ preserveStatus: true, preserveHint: true, forceFinish: true });
    throw err;
  }
};

const stopRecording = async (options = {}) => {
  const { preserveStatus = false, preserveHint = false, forceFinish = false } = options;
  const wasRecording = Boolean(state.captureStopper);
  const wasCountingDown = Boolean(state.isCountingDown);
  const activeMeetingId = state.meetingId;
  const shouldOfferMp3 = Boolean(activeMeetingId && wasRecording && !forceFinish);
  let finishedOk = false;
  state.stopRequested = true;
  stopCaptureLockHeartbeat();
  if (state.isCountingDown) {
    state.isCountingDown = false;
  }

  if (state.captureStopper) {
    try {
      await state.captureStopper();
    } catch (err) {
      console.warn("capture stop failed", err);
    }
  }
  state.captureStopper = null;
  state.captureEngine = null;
  const backupBlob = await stopBackupRecorder();
  clearWsReconnectTimer();
  clearHttpDrainTimer();
  state.wsReconnectAttempts = 0;
  if (state.ws) {
    flushPendingChunks();
    state.ws.close();
  }
  state.ws = null;
  clearWsHeartbeat();
  await drainPendingChunksHttp(activeMeetingId, { force: true, reschedule: false });
  if (activeMeetingId && backupBlob) {
    const uploaded = await uploadBackupAudio(activeMeetingId, backupBlob);
    if (!uploaded) {
      setStatusHint("warn_backup_upload_failed", "bad");
    }
  }
  if (activeMeetingId && (forceFinish || wasRecording || wasCountingDown)) {
    setTranscriptUiState("loading");
    try {
      await fetch(`/v1/meetings/${activeMeetingId}/finish`, {
        method: "POST",
        headers: buildHeaders(),
      });
      await loadFinalTranscripts(activeMeetingId);
      await fetchRecords();
      finishedOk = true;
    } catch (err) {
      setTranscriptUiState("empty");
      // ignore and keep local UI responsive
    }
  }
  if (shouldOfferMp3 && finishedOk) {
    await saveMeetingMp3(activeMeetingId, { askUser: true });
  }
  if (state.stream) {
    releasePreparedCapture();
  } else {
    closeAudioMeter();
  }
  if (!preserveStatus) {
    setStatus("status_idle", "idle");
  }
  if (!preserveHint) {
    setStatusHint("");
  }
  els.countdownValue.textContent = preserveStatus ? "0s" : "—";
  state.meetingId = null;
  els.meetingIdText.textContent = "—";
  setRecordingButtons(false);
  state.stopRequested = false;
};

const emergencyReleaseOnUnload = () => {
  try {
    state.stopRequested = true;
    stopCaptureLockHeartbeat();
    clearWsReconnectTimer();
    clearHttpDrainTimer();
    clearWsHeartbeat();
    clearQuickPollTimer();
    if (state.ws) {
      try {
        state.ws.close();
      } catch (_err) {
        // ignore close errors
      }
      state.ws = null;
    }
    if (state.stream) {
      releasePreparedCapture();
    } else {
      closeAudioMeter();
    }
  } catch (_err) {
    // ignore unload cleanup errors
  }
};

const checkSignal = async () => {
  if (state.signalCheckInProgress) return;
  if (!getWorkModeConfig().supportsRealtime) {
    setStatusHint("err_work_mode_realtime_only", "bad");
    return;
  }
  if (isRecordingFlowActive()) {
    setStatusHint("signal_check_blocked_recording", "muted");
    return;
  }
  setCheckSignalBusy(true);
  const mode = getCaptureMode();
  setStatusHint("signal_check_running", "muted");
  try {
    if (mode === "system" && !els.deviceSelect.value) {
      throw new Error("no_device_selected");
    }
    const keepStream = Boolean(state.captureStopper);
    await buildAudioMeter(mode, { force: !keepStream });
    state.signalPeak = 0;
    startMeter();
    await new Promise((resolve) => setTimeout(resolve, 2400));

    const peak = state.signalPeak;
    const systemStream = state.inputStreams.length ? state.inputStreams[0] : null;
    const micStream =
      state.inputStreams.length > 1 ? state.inputStreams[state.inputStreams.length - 1] : null;
    let systemPeak = 0;
    let micPeak = 0;

    const measurePeak = async (stream) => {
      if (!stream) return 0;
      const Ctx = window.AudioContext || window.webkitAudioContext;
      if (!Ctx) return 0;
      const meterCtx = new Ctx();
      await ensureAudioContextActive(meterCtx);
      const source = meterCtx.createMediaStreamSource(stream);
      const analyser = meterCtx.createAnalyser();
      analyser.fftSize = 1024;
      source.connect(analyser);
      const endAt = Date.now() + 700;
      let maxLevel = 0;
      const buffer = new Uint8Array(analyser.fftSize);
      while (Date.now() < endAt) {
        analyser.getByteTimeDomainData(buffer);
        let sum = 0;
        for (let i = 0; i < buffer.length; i += 1) {
          const value = (buffer[i] - 128) / 128;
          sum += value * value;
        }
        const rms = Math.sqrt(sum / buffer.length);
        const level = Math.min(1, rms * 2.5);
        if (level > maxLevel) maxLevel = level;
        await new Promise((resolve) => setTimeout(resolve, 45));
      }
      try {
        source.disconnect();
      } catch (err) {
        void err;
      }
      try {
        analyser.disconnect();
      } catch (err) {
        void err;
      }
      try {
        await meterCtx.close();
      } catch (err) {
        void err;
      }
      return maxLevel;
    };

    if (mode === "system" && els.includeMic && els.includeMic.checked) {
      [systemPeak, micPeak] = await Promise.all([measurePeak(systemStream), measurePeak(micStream)]);
    }

    if (peak > 0.08) {
      setSignal("signal_ok");
      if (systemPeak < 0.015 && micPeak > 0.04) {
        setStatusHint("signal_check_mic_only", "bad");
      } else if (systemPeak > 0.04 && micPeak < 0.015) {
        setStatusHint("signal_check_system_only", "bad");
      } else {
        setStatusHint("signal_check_ok", "good");
      }
    } else if (peak > 0.02) {
      setSignal("signal_low");
      if (systemPeak < 0.015 && micPeak > 0.03) {
        setStatusHint("signal_check_mic_only", "bad");
      } else if (systemPeak > 0.03 && micPeak < 0.015) {
        setStatusHint("signal_check_system_only", "bad");
      } else {
        setStatusHint("signal_check_ok", "good");
      }
    } else {
      setSignal("signal_no_audio");
      setStatusHint("signal_check_fail", "bad");
    }

    if (!keepStream) {
      closeAudioMeter();
      if (state.stream) {
        try {
          state.stream.getTracks().forEach((track) => track.stop());
        } catch (err) {
          void err;
        }
      }
      state.stream = null;
      state.streamDeviceId = "";
      state.streamKey = "";
      state.screenAudioMissing = false;
      state.screenAudioDriverFallback = false;
      state.micAdded = false;
      closeMixGraph();
      stopInputStreams();
    }
  } catch (err) {
    console.warn("signal check failed", err);
    setStatusHint(mapStartError(err, mode), "bad");
  } finally {
    setCheckSignalBusy(false);
  }
};

const checkDriver = async () => {
  setDriverStatus("driver_checking", "muted");
  try {
    const tmpStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    tmpStream.getTracks().forEach((t) => t.stop());
    const devices = await navigator.mediaDevices.enumerateDevices();
    const labels = devices
      .filter((d) => d.kind === "audioinput")
      .map((d) => (d.label || "").toLowerCase());
    const patterns = ["blackhole", "vb-cable", "cable", "pulse", "monitor"];
    const found = labels.some((label) => patterns.some((p) => label.includes(p)));
    if (found) {
      setDriverStatus("driver_ok", "good");
    } else {
      setDriverStatus("driver_missing", "bad");
    }
    await listDevices();
  } catch (err) {
    console.warn("driver check failed", err);
    setDriverStatus("driver_missing", "bad");
  }
};

const _diagMarkAllMuted = () => {
  setDiagItemStatus(els.diagAudio, "muted");
  setDiagItemStatus(els.diagSystem, "muted");
  setDiagItemStatus(els.diagMic, "muted");
  setDiagItemStatus(els.diagStt, "muted");
  setDiagItemStatus(els.diagLlm, "muted");
};

const runDiagnostics = async (options = {}) => {
  const { forStart = false } = options;
  if (!getWorkModeConfig().supportsRealtime) {
    if (forStart) {
      throw new Error("work_mode_realtime_only");
    }
    _diagMarkAllMuted();
    setDiagHint("work_mode_recording_disabled", "bad");
    return { criticalPassed: false, mp3Ready: false };
  }
  if (els.runDiagnostics) {
    els.runDiagnostics.disabled = true;
  }
  _diagMarkAllMuted();
  setDiagItemStatus(els.diagAudio, "running");
  setDiagItemStatus(els.diagSystem, "running");
  setDiagItemStatus(els.diagMic, "running");
  setDiagItemStatus(els.diagStt, "running");
  setDiagHint("diag_hint_running", "muted");

  let audioOk = false;
  let systemOk = false;
  let micOk = false;
  let micSkipped = false;
  let mp3Ready = false;
  const notRequiredText =
    (i18n[state.lang] && i18n[state.lang].diag_skip_not_required) || "not required";
  setDiagItemStatus(els.diagLlm, "muted", notRequiredText);

  const mode = getCaptureMode();
  const includeMic =
    mode === "system" ? true : Boolean(els.includeMic ? els.includeMic.checked : true);

  try {
    const testAccess = await withBusyRetry(
      () => navigator.mediaDevices.getUserMedia({ audio: true }),
      DIAG_AUDIO_RETRY_DELAYS_MS
    );
    testAccess.getTracks().forEach((track) => track.stop());
    audioOk = true;
    setDiagItemStatus(els.diagAudio, "good");
  } catch (err) {
    setDiagItemStatus(els.diagAudio, "bad");
  }

  if (audioOk) {
    try {
      await buildAudioMeter(mode, { force: true });
      startMeter();
      await sleepMs(1400);
      const systemLevel = Number(state.meterLevels.system || state.meterLevels.mixed || 0);
      const micLevel = Number(state.meterLevels.mic || 0);

      systemOk = systemLevel >= DIAG_SYSTEM_MIN_LEVEL;
      setDiagItemStatus(els.diagSystem, systemOk ? "good" : "bad");

      if (!includeMic) {
        micSkipped = true;
        setDiagItemStatus(els.diagMic, "muted", notRequiredText);
      } else {
        micOk = micLevel >= DIAG_MIC_MIN_LEVEL;
        setDiagItemStatus(els.diagMic, micOk ? "good" : "bad");
      }
    } catch (err) {
      setDiagItemStatus(els.diagSystem, "bad");
      if (includeMic) {
        setDiagItemStatus(els.diagMic, "bad");
      } else {
        micSkipped = true;
        setDiagItemStatus(els.diagMic, "muted", notRequiredText);
      }
    } finally {
      releasePreparedCapture();
    }
  } else {
    setDiagItemStatus(els.diagSystem, "bad");
    if (includeMic) {
      setDiagItemStatus(els.diagMic, "bad");
    } else {
      micSkipped = true;
      setDiagItemStatus(els.diagMic, "muted", notRequiredText);
    }
  }

  try {
    mp3Ready = typeof MediaRecorder !== "undefined";
    if (!mp3Ready && PREFER_PCM_CAPTURE) {
      const Ctx = window.AudioContext || window.webkitAudioContext;
      mp3Ready = Boolean(Ctx);
    }
    setDiagItemStatus(els.diagStt, mp3Ready ? "good" : "bad");
    setDiagItemStatus(els.diagLlm, "muted", notRequiredText);
  } finally {
    if (els.runDiagnostics) {
      els.runDiagnostics.disabled = false;
    }
  }

  const systemLooksMissingWhileMicPresent = Boolean(
    mode === "system" &&
      includeMic &&
      Number(state.meterLevels.system || 0) < DIAG_SYSTEM_CRITICAL_MIN &&
      Number(state.meterLevels.mic || 0) >= 0.03
  );
  const criticalPassed = Boolean(audioOk && mp3Ready && !systemLooksMissingWhileMicPresent);
  state.diagnosticsLast = {
    criticalPassed,
    systemOk,
    micOk,
    micSkipped,
    mp3Ready,
    ts: Date.now(),
  };
  if (!criticalPassed) {
    if (systemLooksMissingWhileMicPresent) {
      setDiagHint("signal_check_mic_only", "bad");
    } else {
      setDiagHint("diag_hint_fail", "bad");
    }
  } else if (systemOk && (micSkipped || micOk) && mp3Ready) {
    setDiagHint("diag_hint_ok", "good");
  } else {
    setDiagHint("diag_hint_levels_low", "muted");
  }

  if (forStart && !criticalPassed) {
    throw new Error("diagnostics_failed");
  }
  refreshRecognitionDiagnosis();
  return { criticalPassed, mp3Ready };
};

const clearQuickPollTimer = () => {
  if (!state.quickPollTimer) return;
  clearInterval(state.quickPollTimer);
  state.quickPollTimer = null;
};

const setQuickButtonsByStatus = (status) => {
  const workCfg = getWorkModeConfig();
  const quickEnabled = Boolean(workCfg.supportsQuick);
  const quickPrimaryMode = quickEnabled && !Boolean(workCfg.supportsRealtime);
  const running = status === "queued" || status === "running";
  const stopping = status === "stopping";
  const busy = running || stopping;
  if (els.quickRecordStart) {
    els.quickRecordStart.disabled = !quickEnabled || busy;
  }
  if (els.quickRecordStop) {
    els.quickRecordStop.disabled = !quickEnabled || !busy;
  }
  const quickControls = getQuickControlSet(workCfg);
  [quickControls.url, quickControls.duration, quickControls.transcribe, quickControls.upload].forEach((el) => {
    if (!el) return;
    el.disabled = !quickEnabled || busy;
  });
  if (els.apiKey) {
    els.apiKey.disabled = workCfg.id === "api_upload" ? busy : false;
  }
  if (quickPrimaryMode) {
    if (els.startBtn) {
      els.startBtn.disabled = busy;
      els.startBtn.classList.toggle("is-active", !busy);
      els.startBtn.classList.toggle("is-inactive", busy);
    }
    if (els.stopBtn) {
      els.stopBtn.disabled = !busy;
      els.stopBtn.classList.toggle("is-active", busy);
      els.stopBtn.classList.toggle("is-inactive", !busy);
    }
  }
};

const applyQuickJobStatus = (job) => {
  const currentMode = getWorkModeConfig();
  const quickPrimaryMode = Boolean(currentMode.supportsQuick) && !Boolean(currentMode.supportsRealtime);
  const apiMode = currentMode.id === "api_upload";
  if (!job) {
    state.quickJobId = null;
    setQuickStatus("quick_record_state_idle", "muted");
    setQuickButtonsByStatus("idle");
    setTranscriptUiState(hasTranscriptContent() ? "ready" : "waiting");
    if (quickPrimaryMode) {
      setStatus("status_idle", "idle");
    }
    clearQuickPollTimer();
    return;
  }

  state.quickJobId = String(job.job_id || "");
  const status = String(job.status || "").trim().toLowerCase();
  if (status === "queued" || status === "running") {
    setQuickStatus("quick_record_state_running", "good");
    setQuickButtonsByStatus(status);
    setTranscriptUiState("recording");
    if (quickPrimaryMode) {
      setStatus("status_recording", "recording");
      if (apiMode) {
        setStatusHint("api_record_started", "good");
      }
    }
    if (!state.quickPollTimer) {
      state.quickPollTimer = setInterval(() => {
        void fetchQuickRecordStatus({ silentErrors: true });
      }, 2500);
    }
    return;
  }

  if (status === "stopping") {
    setQuickStatus("quick_record_state_stopping", "muted");
    setQuickButtonsByStatus(status);
    setTranscriptUiState("recording");
    if (quickPrimaryMode) {
      setStatus("status_recording", "recording");
      if (apiMode) {
        setStatusHint("api_record_stopped", "muted");
      }
    }
    if (!state.quickPollTimer) {
      state.quickPollTimer = setInterval(() => {
        void fetchQuickRecordStatus({ silentErrors: true });
      }, 1500);
    }
    return;
  }

  clearQuickPollTimer();
  if (status === "completed") {
    setQuickStatus("quick_record_state_completed", "good");
    setQuickButtonsByStatus(status);
    setTranscriptUiState(hasTranscriptContent() ? "ready" : "empty");
    if (quickPrimaryMode) {
      setStatus("status_idle", "idle");
      if (apiMode) {
        setStatusHint("api_record_completed", "good");
      }
    }
    setQuickHint("quick_record_hint_completed", "good", false, {
      path: String(job.mp3_path || "—"),
    });
    return;
  }

  if (status === "failed") {
    setQuickStatus("quick_record_state_failed", "bad");
    setQuickButtonsByStatus(status);
    setTranscriptUiState("empty");
    if (quickPrimaryMode) {
      setStatus("status_error", "error");
      if (apiMode) {
        setStatusHint("api_record_failed", "bad");
      }
    }
    setQuickHint("quick_record_hint_failed", "bad", false, {
      error: String(job.error || "unknown"),
    });
    return;
  }

  setQuickStatus("quick_record_state_idle", "muted");
  setQuickButtonsByStatus(status);
  setTranscriptUiState(hasTranscriptContent() ? "ready" : "waiting");
  if (quickPrimaryMode) {
    setStatus("status_idle", "idle");
  }
};

const fetchQuickRecordStatus = async (options = {}) => {
  const { silentErrors = false } = options;
  try {
    const res = await fetch("/v1/quick-record/status", { headers: buildHeaders() });
    if (!res.ok) {
      throw new Error(`quick_status_failed_${res.status}`);
    }
    const body = await res.json();
    applyQuickJobStatus(body.job || null);
  } catch (err) {
    console.warn("quick record status failed", err);
    clearQuickPollTimer();
    if (!silentErrors) {
      setQuickHint("quick_record_hint_start_failed", "bad");
    }
  }
};

const startQuickRecord = async () => {
  const workCfg = getWorkModeConfig();
  if (!workCfg.supportsQuick) {
    setQuickHint("err_work_mode_quick_only", "bad");
    return;
  }
  const quickControls = getQuickControlSet(workCfg);
  const apiMode = workCfg.id === "api_upload";
  const meetingUrl = String((quickControls.url && quickControls.url.value) || "").trim();
  if (!meetingUrl || (!meetingUrl.startsWith("http://") && !meetingUrl.startsWith("https://"))) {
    setQuickHint("quick_record_hint_missing_url", "bad");
    return;
  }
  const duration = Number.parseInt(
    String((quickControls.duration && quickControls.duration.value) || "0"),
    10
  );
  if (!Number.isFinite(duration) || duration < 5) {
    setQuickHint("quick_record_hint_missing_duration", "bad");
    return;
  }

  const transcribe = apiMode
    ? false
    : Boolean(quickControls.transcribe && quickControls.transcribe.checked);
  const uploadToAgent = apiMode
    ? true
    : Boolean(quickControls.upload && quickControls.upload.checked);
  const agentApiKey = String((els.apiKey && els.apiKey.value) || "").trim();

  if (els.quickRecordStart) {
    els.quickRecordStart.disabled = true;
  }
  try {
    const res = await fetch("/v1/quick-record/start", {
      method: "POST",
      headers: buildHeaders(),
      body: JSON.stringify({
        meeting_url: meetingUrl,
        duration_sec: duration,
        work_mode: workCfg.contextMode,
        transcribe,
        upload_to_agent: uploadToAgent,
        agent_api_key: agentApiKey || null,
      }),
    });
    if (res.status === 409) {
      setQuickHint("quick_record_hint_already_running", "bad");
      await fetchQuickRecordStatus({ silentErrors: true });
      return;
    }
    if (!res.ok) {
      throw new Error(`quick_start_failed_${res.status}`);
    }
    const body = await res.json();
    setQuickHint("quick_record_hint_started", "good");
    if (apiMode) {
      setStatusHint("api_record_started", "good");
    }
    applyQuickJobStatus(body.job || null);
  } catch (err) {
    console.warn("quick record start failed", err);
    setQuickHint("quick_record_hint_start_failed", "bad");
    if (apiMode) {
      setStatusHint("api_record_failed", "bad");
    }
    await fetchQuickRecordStatus({ silentErrors: true });
  } finally {
    if (els.quickRecordStart && (!els.quickRecordStop || els.quickRecordStop.disabled)) {
      els.quickRecordStart.disabled = false;
    }
  }
};

const stopQuickRecord = async () => {
  const currentMode = getWorkModeConfig();
  const apiMode = currentMode.id === "api_upload";
  if (!currentMode.supportsQuick) {
    setQuickHint("err_work_mode_quick_only", "bad");
    return;
  }
  try {
    const res = await fetch("/v1/quick-record/stop", {
      method: "POST",
      headers: buildHeaders(),
    });
    if (!res.ok) {
      throw new Error(`quick_stop_failed_${res.status}`);
    }
    const body = await res.json();
    setQuickHint("quick_record_hint_stopped", "muted");
    if (apiMode) {
      setStatusHint("api_record_stopped", "muted");
    }
    applyQuickJobStatus(body.job || null);
  } catch (err) {
    console.warn("quick record stop failed", err);
    setQuickHint("quick_record_hint_stop_failed", "bad");
    if (apiMode) {
      setStatusHint("api_record_failed", "bad");
    }
  }
};

const updateCaptureUi = () => {
  const cfg = getWorkModeConfig();
  const realtimeEnabled = Boolean(cfg.supportsRealtime);
  const mode = getCaptureMode();
  if (els.realtimeOnlySettings) {
    els.realtimeOnlySettings.classList.toggle("hidden", !realtimeEnabled);
  }
  if (els.deviceSelect) {
    els.deviceSelect.disabled = !cfg.useDeviceDriver || mode === "screen";
  }
  if (els.includeMic) {
    if (!realtimeEnabled) {
      els.includeMic.disabled = true;
    } else if (mode === "system") {
      els.includeMic.checked = true;
      els.includeMic.disabled = true;
    } else {
      els.includeMic.disabled = false;
    }
  }
  if (els.micSelect) {
    els.micSelect.disabled = !realtimeEnabled || !els.includeMic || !els.includeMic.checked;
  }
  const sttControlsLocked = Boolean(state.captureStopper || state.isUploading || isQuickFlowActive());
  if (els.languageProfileSelect) {
    els.languageProfileSelect.disabled = sttControlsLocked;
  }
  [els.qualityFast, els.qualityBalanced, els.qualityAccurate].forEach((btn) => {
    if (!btn) return;
    btn.disabled = sttControlsLocked;
  });
  if (els.runDiagnostics && !state.signalCheckInProgress) {
    els.runDiagnostics.disabled = !realtimeEnabled;
  }
  if (els.captureMethodChip) {
    const dict = i18n[state.lang] || {};
    if (!realtimeEnabled) {
      const workCfg = getWorkModeConfig();
      els.captureMethodChip.textContent = dict[workCfg.labelKey] || workCfg.id;
    } else {
      const modeLabelKey = mode === "screen" ? "capture_mode_screen" : "capture_mode_system";
      els.captureMethodChip.textContent = dict[modeLabelKey] || modeLabelKey;
    }
  }
  setRecordingButtons(Boolean(realtimeEnabled && state.captureStopper));
  renderTranscriptModeUi();
};

const toggleDriverHelp = () => {
  if (!els.driverHelp) return;
  els.driverHelp.classList.toggle("hidden");
};

const setDriverHelpTab = (os) => {
  document.querySelectorAll(".driver-tab").forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.os === os);
  });
  document.querySelectorAll(".driver-panel").forEach((panel) => {
    panel.classList.toggle("hidden", panel.dataset.os !== os);
  });
};

const formatMeetingOptionLabel = (meta) => {
  if (!meta || typeof meta !== "object") return "—";
  const display = String(meta.display_name || meta.meeting_id || "").trim() || "record";
  const createdRaw = String(meta.created_at || "").trim();
  if (!createdRaw) return display;
  const dt = new Date(createdRaw);
  if (!Number.isFinite(dt.valueOf())) return display;
  return `${display} (${dt.toLocaleString()})`;
};

const getReportSelectEl = (source = "raw") => {
  return source === "clean" ? els.cleanReportSelect : els.rawReportSelect;
};

const getReportNameInputEl = (source = "raw") => {
  return source === "clean" ? els.cleanReportNameInput : els.rawReportNameInput;
};

const syncReportSelectors = () => {
  const dict = i18n[state.lang] || {};
  const meetingList = Array.from(state.recordsMeta.values());
  ["raw", "clean"].forEach((source) => {
    const select = getReportSelectEl(source);
    if (!select) return;
    const selectedMain = getSelectedMeeting();
    const preferred = String(state.reportMeetingSelection[source] || selectedMain || "").trim();
    select.innerHTML = "";
    if (!meetingList.length) {
      const opt = document.createElement("option");
      opt.value = "";
      opt.textContent = dict.report_picker_empty || "No records";
      select.appendChild(opt);
      state.reportMeetingSelection[source] = "";
      return;
    }
    meetingList.forEach((meta) => {
      const opt = document.createElement("option");
      opt.value = String(meta.meeting_id || "");
      opt.textContent = formatMeetingOptionLabel(meta);
      select.appendChild(opt);
    });
    const fallback = String(meetingList[0].meeting_id || "");
    const selected = meetingList.some((item) => String(item.meeting_id || "") === preferred)
      ? preferred
      : fallback;
    select.value = selected;
    state.reportMeetingSelection[source] = selected;
  });
};

const syncResultsState = () => {
  if (!els.resultsRaw || !els.resultsClean) return;
  const source = state.resultsSource === "raw" ? "raw" : "clean";
  els.resultsRaw.classList.toggle("active", source === "raw");
  els.resultsClean.classList.toggle("active", source === "clean");
  const filename = buildFilename({ kind: "report", source, fmt: "txt" });
  if (els.resultFileName) {
    els.resultFileName.textContent = filename;
  }
  const hasMeeting = Boolean(getSelectedMeeting());
  [
    els.recordMenuBtn,
    els.saveCurrentMp3Btn,
    els.generateReportBtn,
    els.downloadReportBtn,
    els.resultsRaw,
    els.resultsClean,
  ].forEach((btn) => {
    if (!btn) return;
    btn.disabled = !hasMeeting;
  });
  if (!hasMeeting) {
    setTranscriptUiState("waiting");
    closeRecordMenu();
  }
  syncReportSelectors();
};

const chooseFolder = async () => {
  if (!window.showDirectoryPicker) {
    setFolderStatus("folder_not_supported", "bad");
    return;
  }
  try {
    state.downloadDirHandle = await window.showDirectoryPicker();
    setFolderStatus("folder_selected", "good");
  } catch (err) {
    console.warn("folder pick cancelled", err);
  }
};

const fetchRecords = async () => {
  try {
    const res = await fetch("/v1/meetings?limit=50", { headers: buildHeaders() });
    if (!res.ok) return;
    const data = await res.json();
    const items = data.items || [];
    const current = getSelectedMeeting();
    state.recordsMeta = new Map();
    els.recordsSelect.innerHTML = "";
    if (!items.length) {
      const opt = document.createElement("option");
      opt.value = "";
      opt.textContent = "—";
      els.recordsSelect.appendChild(opt);
      syncResultsState();
      void fetchComparison();
      return;
    }
    items.forEach((item) => {
      const meetingId = String(item.meeting_id || "").trim();
      const displayName = String(item.display_name || "").trim() || meetingId;
      const artifacts = item && typeof item.artifacts === "object" ? item.artifacts : {};
      state.recordsMeta.set(meetingId, {
        meeting_id: meetingId,
        display_name: displayName,
        record_index: Number(item.record_index || 0),
        created_at: String(item.created_at || ""),
        audio_mp3: Boolean(item.audio_mp3),
        artifacts,
      });
      const opt = document.createElement("option");
      opt.value = meetingId;
      opt.textContent = formatMeetingOptionLabel(state.recordsMeta.get(meetingId));
      if (current && meetingId === current) {
        opt.selected = true;
      }
      els.recordsSelect.appendChild(opt);
    });
    syncResultsState();
    void fetchComparison();
  } catch (err) {
    console.warn("fetch records failed", err);
  }
};

const getSelectedMeeting = () => {
  return els.recordsSelect.value || state.meetingId;
};

const getSelectedRecordMeta = () => {
  const meetingId = getSelectedMeeting();
  if (!meetingId) return null;
  return state.recordsMeta.get(meetingId) || null;
};

const getReportMeetingId = (source = "raw") => {
  const select = getReportSelectEl(source);
  const selected = String((select && select.value) || state.reportMeetingSelection[source] || "").trim();
  if (selected) return selected;
  return String(getSelectedMeeting() || "").trim();
};

const getSelectedRecordDisplayName = () => {
  const meta = getSelectedRecordMeta();
  if (meta && meta.display_name) return String(meta.display_name);
  const meetingId = getSelectedMeeting();
  return meetingId ? String(meetingId) : "record";
};

const sanitizeFilenamePart = (value) => {
  const base = String(value || "")
    .replace(/[\\\\/:*?\"<>|]/g, "_")
    .replace(/\\s+/g, " ")
    .trim();
  return (base || "record").slice(0, 80);
};

const normalizeMp3Filename = (value, fallbackBase = "record") => {
  const normalized = String(value || "").trim().replace(/\.mp3$/i, "");
  const safeBase = sanitizeFilenamePart(normalized || fallbackBase);
  return `${safeBase}.mp3`;
};

const normalizeFilenameWithExt = (value, fallbackBase = "record", ext = "txt") => {
  const normalized = String(value || "")
    .trim()
    .replace(/\.[a-z0-9]{1,8}$/i, "");
  const safeBase = sanitizeFilenamePart(normalized || fallbackBase);
  return `${safeBase}.${String(ext || "txt").trim().toLowerCase()}`;
};

const closeRecordMenu = () => {
  if (els.recordMenu) {
    els.recordMenu.classList.add("hidden");
  }
};

const toggleRecordMenu = () => {
  if (!els.recordMenu) return;
  const hasMeeting = Boolean(getSelectedMeeting());
  if (!hasMeeting) return;
  els.recordMenu.classList.toggle("hidden");
};

const buildFilename = ({ kind, source, fmt, meetingId }) => {
  const sourceSafe = source === "raw" ? "raw" : "clean";
  const ext = String(fmt || "").trim().toLowerCase();
  if (kind === "raw") return "raw.txt";
  if (kind === "clean") return "clean.txt";
  if (kind === "audio") {
    const targetMeeting = String(meetingId || "").trim() || getSelectedMeeting();
    const meta = targetMeeting ? state.recordsMeta.get(targetMeeting) : null;
    const label = meta && meta.display_name ? meta.display_name : getSelectedRecordDisplayName();
    return `${sanitizeFilenamePart(label)}.mp3`;
  }
  if (kind === "report") {
    if (ext === "json") return sourceSafe === "raw" ? "report_raw.json" : "report_clean.json";
    return sourceSafe === "raw" ? "report_raw.txt" : "report_clean.txt";
  }
  if (kind === "structured") {
    return `structured_${sourceSafe}.${ext || "csv"}`;
  }
  if (kind === "senior_brief") {
    return sourceSafe === "raw" ? "senior_brief_raw.txt" : "senior_brief_clean.txt";
  }
  return "artifact.bin";
};

const saveBlobViaPicker = async (filename, blob) => {
  if (!window.showSaveFilePicker) return false;
  const ext = String(filename || "")
    .split(".")
    .pop()
    .trim()
    .toLowerCase();
  let description = "File";
  let mime = "application/octet-stream";
  if (ext === "mp3") {
    description = "MP3 audio";
    mime = "audio/mpeg";
  } else if (ext === "txt") {
    description = "Text";
    mime = "text/plain";
  } else if (ext === "json") {
    description = "JSON";
    mime = "application/json";
  } else if (ext === "csv") {
    description = "CSV";
    mime = "text/csv";
  }
  try {
    const handle = await window.showSaveFilePicker({
      suggestedName: filename,
      types: [
        {
          description,
          accept: { [mime]: [`.${ext || "txt"}`] },
        },
      ],
    });
    const writable = await handle.createWritable();
    await writable.write(blob);
    await writable.close();
    return true;
  } catch (err) {
    return false;
  }
};

const saveToFolder = async (filename, blob) => {
  if (!state.downloadDirHandle) return false;
  try {
    const handle = await state.downloadDirHandle.getFileHandle(filename, { create: true });
    const writable = await handle.createWritable();
    await writable.write(blob);
    await writable.close();
    return true;
  } catch (err) {
    console.warn("save to folder failed", err);
    return false;
  }
};

const downloadArtifact = async (url, filename, options = {}) => {
  const { preferPicker = false } = options;
  try {
    const res = await fetch(url, { headers: buildAuthHeaders() });
    if (!res.ok) {
      return { ok: false, status: res.status };
    }
    const blob = await res.blob();
    if (preferPicker) {
      const savedPicker = await saveBlobViaPicker(filename, blob);
      if (savedPicker) return { ok: true, status: 200 };
    }
    const saved = await saveToFolder(filename, blob);
    if (saved) return { ok: true, status: 200 };
    const link = document.createElement("a");
    const objectUrl = URL.createObjectURL(blob);
    link.href = objectUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(objectUrl), 500);
    return { ok: true, status: 200 };
  } catch (err) {
    console.warn("download failed", err);
    return { ok: false, status: 0 };
  }
};

const saveMeetingMp3 = async (meetingId, options = {}) => {
  const { askUser = false } = options;
  if (!meetingId) return false;
  const dict = i18n[state.lang] || {};
  let filename = buildFilename({ kind: "audio", fmt: "mp3", meetingId });
  if (askUser) {
    const question = dict.prompt_save_mp3_after_stop || "Recording is finished. Enter MP3 file name:";
    const suggested = normalizeMp3Filename(filename, "record");
    const entered = window.prompt(question, suggested);
    if (entered == null) {
      return false;
    }
    filename = normalizeMp3Filename(entered, suggested.replace(/\.mp3$/i, ""));
  }
  const url = `/v1/meetings/${meetingId}/artifact?kind=audio&fmt=mp3`;
  const result = await downloadArtifact(url, filename, { preferPicker: true });
  if (result && result.ok) {
    setStatusHint("hint_mp3_saved", "good");
    return true;
  }
  if (result && result.status === 404) {
    setStatusHint("hint_mp3_not_found", "bad");
  }
  return false;
};

const renameSelectedRecord = async () => {
  const meetingId = getSelectedMeeting();
  if (!meetingId) return;
  const dict = i18n[state.lang] || {};
  const currentName = getSelectedRecordDisplayName();
  const promptText = dict.prompt_rename_record || "Enter new recording name:";
  const nextName = window.prompt(promptText, currentName);
  if (nextName == null) return;
  const value = String(nextName).trim();
  if (!value) return;
  try {
    const res = await fetch(`/v1/meetings/${meetingId}/rename`, {
      method: "POST",
      headers: buildHeaders(),
      body: JSON.stringify({ display_name: value }),
    });
    if (!res.ok) return;
    closeRecordMenu();
    setStatusHint("hint_record_renamed", "good");
    await fetchRecords();
  } catch (err) {
    console.warn("rename record failed", err);
  }
};

const generateReportForMeeting = async (meetingId, source = "raw") => {
  if (!meetingId) return false;
  const src = source === "clean" ? "clean" : "raw";
  const generated = await fetch(`/v1/meetings/${meetingId}/report`, {
    method: "POST",
    headers: buildHeaders(),
    body: JSON.stringify({ source: src }),
  });
  if (!generated.ok) return false;
  return true;
};

const generateStructuredForMeeting = async (meetingId, source = "raw") => {
  if (!meetingId) return false;
  const src = source === "clean" ? "clean" : "raw";
  const generated = await fetch(`/v1/meetings/${meetingId}/structured`, {
    method: "POST",
    headers: buildHeaders(),
    body: JSON.stringify({ source: src }),
  });
  if (!generated.ok) return false;
  try {
    const payload = await generated.json();
    if (String(payload.status || "") === "insufficient_data") {
      setStatusHint(
        payload.message ||
          (i18n[state.lang] && i18n[state.lang].structured_insufficient_data) ||
          "Insufficient data",
        "bad",
        true
      );
    }
  } catch (_err) {
    // ignore parse failures and continue with download
  }
  return true;
};

const generateSeniorBriefForMeeting = async (meetingId, source = "raw") => {
  if (!meetingId) return false;
  const src = source === "clean" ? "clean" : "raw";
  const generated = await fetch(`/v1/meetings/${meetingId}/senior-brief`, {
    method: "POST",
    headers: buildHeaders(),
    body: JSON.stringify({ source: src }),
  });
  return Boolean(generated.ok);
};

const downloadCurrentReportTxt = async () => {
  const meetingId = getSelectedMeeting();
  if (!meetingId) {
    setStatusHint("hint_report_source_missing", "bad");
    return;
  }
  const source = state.resultsSource === "clean" ? "clean" : "raw";
  const inputValue = String((els.reportNameInput && els.reportNameInput.value) || "").trim();
  const fallback = source === "raw" ? "report_raw" : "report_clean";
  const filename = normalizeFilenameWithExt(inputValue, fallback, "txt");
  const url = `/v1/meetings/${meetingId}/artifact?kind=report&source=${source}&fmt=txt`;
  let result = await downloadArtifact(url, filename, { preferPicker: true });
  if (result && result.status === 404) {
    const generated = await generateReportForMeeting(meetingId, source);
    if (!generated) {
      setStatusHint("hint_report_missing", "bad");
      return;
    }
    result = await downloadArtifact(url, filename, { preferPicker: true });
  }
  if (!result || !result.ok) {
    setStatusHint("hint_report_missing", "bad");
    return;
  }
  await fetchRecords();
  await fetchComparison();
  setStatusHint("hint_report_generated", "good");
};

const generateAndSaveCurrentReport = async () => {
  const meetingId = getSelectedMeeting();
  if (!meetingId) {
    setStatusHint("hint_report_source_missing", "bad");
    return;
  }
  const source = state.resultsSource === "clean" ? "clean" : "raw";
  const inputValue = String((els.reportNameInput && els.reportNameInput.value) || "").trim();
  if (!inputValue) {
    setStatusHint("hint_report_name_missing", "bad");
    return;
  }
  const generated = await generateReportForMeeting(meetingId, source);
  if (!generated) return;
  const filename = normalizeFilenameWithExt(
    inputValue,
    source === "raw" ? "report_raw" : "report_clean",
    "txt"
  );
  const url = `/v1/meetings/${meetingId}/artifact?kind=report&source=${source}&fmt=txt`;
  const result = await downloadArtifact(url, filename, { preferPicker: true });
  if (!result || !result.ok) {
    setStatusHint("hint_report_missing", "bad");
    return;
  }
  await fetchRecords();
  await fetchComparison();
  setStatusHint("hint_report_generated", "good");
};

const exportReportLane = async (source = "raw", exportKind = "report_txt") => {
  const src = source === "clean" ? "clean" : "raw";
  const meetingId = getReportMeetingId(src);
  if (!meetingId) {
    setStatusHint("hint_report_source_missing", "bad");
    return;
  }
  const inputEl = getReportNameInputEl(src);
  const rawName = String((inputEl && inputEl.value) || "").trim();

  if (exportKind === "report_txt") {
    const ok = await generateReportForMeeting(meetingId, src);
    if (!ok) return;
    const url = `/v1/meetings/${meetingId}/artifact?kind=report&source=${src}&fmt=txt`;
    const filename = normalizeFilenameWithExt(rawName, `report_${src}`, "txt");
    const result = await downloadArtifact(url, filename, { preferPicker: true });
    if (!result || !result.ok) {
      setStatusHint("hint_report_missing", "bad");
      return;
    }
  } else if (exportKind === "report_json") {
    const ok = await generateReportForMeeting(meetingId, src);
    if (!ok) return;
    const url = `/v1/meetings/${meetingId}/artifact?kind=report&source=${src}&fmt=json`;
    const filename = normalizeFilenameWithExt(rawName, `report_${src}`, "json");
    const result = await downloadArtifact(url, filename, { preferPicker: true });
    if (!result || !result.ok) {
      setStatusHint("hint_report_missing", "bad");
      return;
    }
  } else if (exportKind === "structured_csv") {
    const ok = await generateStructuredForMeeting(meetingId, src);
    if (!ok) return;
    const url = `/v1/meetings/${meetingId}/artifact?kind=structured&source=${src}&fmt=csv`;
    const filename = normalizeFilenameWithExt(rawName, `structured_${src}`, "csv");
    await downloadArtifact(url, filename, { preferPicker: true });
  } else if (exportKind === "structured_json") {
    const ok = await generateStructuredForMeeting(meetingId, src);
    if (!ok) return;
    const url = `/v1/meetings/${meetingId}/artifact?kind=structured&source=${src}&fmt=json`;
    const filename = normalizeFilenameWithExt(rawName, `structured_${src}`, "json");
    await downloadArtifact(url, filename, { preferPicker: true });
  } else if (exportKind === "senior_brief") {
    const ok = await generateSeniorBriefForMeeting(meetingId, src);
    if (!ok) return;
    const url = `/v1/meetings/${meetingId}/artifact?kind=senior_brief&source=${src}&fmt=txt`;
    const filename = normalizeFilenameWithExt(rawName, `senior_brief_${src}`, "txt");
    await downloadArtifact(url, filename, { preferPicker: true });
  }
  await fetchRecords();
  await fetchComparison();
};

const uploadAudioToMeetingPipeline = async (file, options = {}) => {
  const { source = "upload_audio", enforceUploadMode = false } = options;
  if (!file) return null;
  if (state.isUploading) return null;
  const workCfg = getWorkModeConfig();
  if (enforceUploadMode && !workCfg.supportsUpload) {
    setStatusHint("err_work_mode_upload_only", "bad");
    return null;
  }
  let interviewMeta = null;
  try {
    interviewMeta = validateInterviewMetadata();
  } catch (err) {
    setStatusHint(mapStartError(err, "system"), "bad");
    return null;
  }
  state.isUploading = true;
  els.startBtn.disabled = true;
  els.stopBtn.disabled = true;
  setStatus("status_uploading", "recording");
  resetSessionState();
  try {
    const res = await fetch("/v1/meetings/start", {
      method: "POST",
      headers: buildHeaders(),
      body: JSON.stringify({
        mode: "postmeeting",
        context: {
          source,
          work_mode: "api_upload",
          source_mode: "api_upload",
          locale: state.lang,
          language_profile: getLanguageProfile(),
          filename: file.name,
          ...(interviewMeta || {}),
          source_track_roles: {
            system: "candidate",
            mic: "interviewer",
          },
        },
      }),
    });
    if (!res.ok) {
      throw new Error(`meeting_start_failed_${res.status}`);
    }
    const data = await res.json();
    const meetingId = String(data.meeting_id || "").trim();
    state.meetingId = meetingId;
    if (els.meetingIdText) {
      els.meetingIdText.textContent = meetingId || "—";
    }

    const form = new FormData();
    form.append("file", file, file.name);
    const uploadRes = await fetch(`/v1/meetings/${meetingId}/upload`, {
      method: "POST",
      headers: buildAuthHeaders(),
      body: form,
    });
    if (!uploadRes.ok) {
      throw new Error(`meeting_upload_failed_${uploadRes.status}`);
    }
    state.chunkCount = 1;
    if (els.chunkCount) {
      els.chunkCount.textContent = "1";
    }
    setTranscriptUiState("loading");
    const finishRes = await fetch(`/v1/meetings/${meetingId}/finish`, {
      method: "POST",
      headers: buildHeaders(),
    });
    if (!finishRes.ok) {
      throw new Error(`meeting_finish_failed_${finishRes.status}`);
    }
    await loadFinalTranscripts(meetingId);
    await fetchRecords();
    if (els.recordsSelect) {
      els.recordsSelect.value = meetingId;
    }
    syncResultsState();
    return meetingId;
  } catch (err) {
    console.warn("postmeeting upload failed", err);
    setStatus("status_error", "error");
    return null;
  } finally {
    state.isUploading = false;
    setStatus("status_idle", "idle");
    setRecordingButtons(false);
  }
};

const importMp3FromPicker = async () => {
  if (!els.importMp3Input) return;
  els.importMp3Input.value = "";
  els.importMp3Input.click();
};

document.querySelectorAll(".lang-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    state.lang = btn.dataset.lang;
    updateI18n();
    renderTranscript();
    syncResultsState();
  });
});

els.captureModeInputs.forEach((el) => {
  el.addEventListener("change", updateCaptureUi);
});

(els.workModeButtons || []).forEach((btn) => {
  btn.addEventListener("click", () => {
    const mode = btn && btn.dataset ? btn.dataset.workMode : "";
    setWorkMode(mode);
  });
});

if (els.scanLlmModels) {
  els.scanLlmModels.addEventListener("click", () => {
    void scanLlmModels();
  });
}
if (els.applyLlmModel) {
  els.applyLlmModel.addEventListener("click", () => {
    void applyLlmModel();
  });
}
if (els.qualityFast) {
  els.qualityFast.addEventListener("click", () => setCaptureQuality("fast"));
}
if (els.qualityBalanced) {
  els.qualityBalanced.addEventListener("click", () => setCaptureQuality("balanced"));
}
if (els.qualityAccurate) {
  els.qualityAccurate.addEventListener("click", () => setCaptureQuality("accurate"));
}
if (els.languageProfileSelect) {
  els.languageProfileSelect.addEventListener("change", () => {
    state.languageProfile = getLanguageProfile();
    refreshRecognitionDiagnosis();
  });
}
if (els.runDiagnostics) {
  els.runDiagnostics.addEventListener("click", () => {
    void runDiagnostics({ forStart: false });
  });
}

els.refreshDevices.addEventListener("click", () => {
  void listDevices({ requestAccess: true });
});
if (els.deviceSelect) {
  els.deviceSelect.addEventListener("change", () => {
    void listDevices();
  });
}
if (navigator.mediaDevices && typeof navigator.mediaDevices.addEventListener === "function") {
  navigator.mediaDevices.addEventListener("devicechange", () => {
    void listDevices();
  });
}
window.addEventListener("beforeunload", emergencyReleaseOnUnload);
window.addEventListener("pagehide", emergencyReleaseOnUnload);
window.addEventListener("storage", (event) => {
  if (!event || event.key !== CAPTURE_LOCK_KEY) return;
  const lock = isCaptureLockedByOtherTab();
  if (!lock.locked) return;
  if (isRecordingFlowActive()) {
    setStatusHint("err_capture_locked_other_tab", "bad");
  }
});
els.checkDriver.addEventListener("click", checkDriver);
if (els.themeLight) {
  els.themeLight.addEventListener("click", () => applyTheme("light"));
}
if (els.themeDark) {
  els.themeDark.addEventListener("click", () => applyTheme("dark"));
}
if (els.driverHelpBtn) {
  els.driverHelpBtn.addEventListener("click", toggleDriverHelp);
}
document.querySelectorAll(".driver-tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    setDriverHelpTab(tab.dataset.os);
  });
});
els.refreshRecords.addEventListener("click", fetchRecords);
els.recordsSelect.addEventListener("change", () => {
  const meetingId = getSelectedMeeting();
  if (meetingId) {
    els.meetingIdText.textContent = meetingId;
    state.reportMeetingSelection.raw = meetingId;
    state.reportMeetingSelection.clean = meetingId;
  }
  state.transcript.raw.clear();
  state.transcript.enhanced.clear();
  if (els.transcriptRaw) els.transcriptRaw.value = "";
  if (els.transcriptClean) els.transcriptClean.value = "";
  setTranscriptUiState("waiting");
  closeRecordMenu();
  syncResultsState();
});
if (els.recordMenuBtn) {
  els.recordMenuBtn.addEventListener("click", (event) => {
    event.stopPropagation();
    toggleRecordMenu();
  });
}
if (els.renameRecordBtn) {
  els.renameRecordBtn.addEventListener("click", () => {
    void renameSelectedRecord();
  });
}
if (els.saveRecordMp3Btn) {
  els.saveRecordMp3Btn.addEventListener("click", () => {
    const meetingId = getSelectedMeeting();
    if (!meetingId) return;
    closeRecordMenu();
    void saveMeetingMp3(meetingId, { askUser: false });
  });
}
if (els.saveCurrentMp3Btn) {
  els.saveCurrentMp3Btn.addEventListener("click", () => {
    const meetingId = getSelectedMeeting();
    if (!meetingId) return;
    void saveMeetingMp3(meetingId, { askUser: true });
  });
}
if (els.importMp3Btn) {
  els.importMp3Btn.addEventListener("click", () => {
    void importMp3FromPicker();
  });
}
if (els.importMp3Input) {
  els.importMp3Input.addEventListener("change", async () => {
    const file = els.importMp3Input && els.importMp3Input.files ? els.importMp3Input.files[0] : null;
    if (!file) return;
    setStatusHint("hint_mp3_import_started", "muted");
    const meetingId = await uploadAudioToMeetingPipeline(file, { source: "results_mp3_import" });
    if (!meetingId) {
      setStatusHint("hint_mp3_import_failed", "bad");
      return;
    }
    setStatusHint("hint_mp3_import_done", "good");
  });
}
if (els.resultsRaw) {
  els.resultsRaw.addEventListener("click", () => {
    state.resultsSource = "raw";
    syncResultsState();
    void fetchComparison();
  });
}
if (els.resultsClean) {
  els.resultsClean.addEventListener("click", () => {
    state.resultsSource = "clean";
    syncResultsState();
    void fetchComparison();
  });
}
if (els.generateReportBtn) {
  els.generateReportBtn.addEventListener("click", () => {
    void generateAndSaveCurrentReport();
  });
}
if (els.downloadReportBtn) {
  els.downloadReportBtn.addEventListener("click", () => {
    void downloadCurrentReportTxt();
  });
}
if (els.rawReportSelect) {
  els.rawReportSelect.addEventListener("change", () => {
    state.reportMeetingSelection.raw = String(els.rawReportSelect.value || "").trim();
  });
}
if (els.cleanReportSelect) {
  els.cleanReportSelect.addEventListener("change", () => {
    state.reportMeetingSelection.clean = String(els.cleanReportSelect.value || "").trim();
  });
}
(els.reportActionButtons || []).forEach((btn) => {
  btn.addEventListener("click", () => {
    const source = String((btn.dataset && btn.dataset.exportSource) || "raw").trim();
    const kind = String((btn.dataset && btn.dataset.exportKind) || "report_txt").trim();
    void exportReportLane(source, kind);
  });
});
if (els.chooseFolder) {
  els.chooseFolder.addEventListener("click", chooseFolder);
}
document.addEventListener("click", (event) => {
  if (!els.recordMenu || !els.recordMenuBtn) return;
  const target = event && event.target ? event.target : null;
  if (!target) return;
  if (els.recordMenu.contains(target)) return;
  if (els.recordMenuBtn.contains(target)) return;
  closeRecordMenu();
});
els.startBtn.addEventListener("click", async () => {
  const modeCfg = getWorkModeConfig();
  if (modeCfg.supportsQuick && !modeCfg.supportsRealtime) {
    await startQuickRecord();
    return;
  }
  try {
    await startRecording();
  } catch (err) {
    console.error(err);
    setStatus("status_error", "error");
    setRecordingButtons(false);
  }
});
els.stopBtn.addEventListener("click", () => {
  const modeCfg = getWorkModeConfig();
  if (modeCfg.supportsQuick && !modeCfg.supportsRealtime) {
    void stopQuickRecord();
    return;
  }
  void stopRecording();
});
els.checkSignal.addEventListener("click", checkSignal);
if (els.quickRecordStart) {
  els.quickRecordStart.addEventListener("click", () => {
    void startQuickRecord();
  });
}
if (els.quickRecordStop) {
  els.quickRecordStop.addEventListener("click", () => {
    void stopQuickRecord();
  });
}
if (els.refreshCompare) {
  els.refreshCompare.addEventListener("click", () => {
    void fetchComparison();
  });
}
if (els.downloadCompareCsv) {
  els.downloadCompareCsv.addEventListener("click", () => {
    void downloadComparison("csv");
  });
}
if (els.downloadCompareJson) {
  els.downloadCompareJson.addEventListener("click", () => {
    void downloadComparison("json");
  });
}

const savedTheme = (() => {
  try {
    return localStorage.getItem("ui_theme");
  } catch (err) {
    return null;
  }
})();
const savedWorkMode = (() => {
  try {
    return localStorage.getItem(WORK_MODE_KEY);
  } catch (err) {
    return null;
  }
})();
applyTheme(savedTheme || "light");
setWorkMode(savedWorkMode || state.workMode, { persist: false, force: true });
setCaptureQuality(state.captureQuality || "balanced");
updateI18n();
_diagMarkAllMuted();
setDiagHint("diag_hint_idle", "muted");
pruneStaleCaptureLock();
clearCaptureLock();
listDevices();
fetchLlmStatus({ scanAfter: true });
updateCaptureUi();
fetchRecords();
setRecordingButtons(false);
setDriverHelpTab("mac");
syncResultsState();
setCompareHint("compare_hint_idle", "muted");
renderComparisonTable();
setQuickStatus("quick_record_state_idle", "muted");
setQuickHint("quick_record_hint_ready", "muted");
setQuickButtonsByStatus("idle");
fetchQuickRecordStatus({ silentErrors: true });
if (!window.showDirectoryPicker) {
  setFolderStatus("folder_not_supported", "bad");
}
