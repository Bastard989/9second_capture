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
  sttModels: [],
  sttStatusKey: "stt_status_loading",
  sttStatusStyle: "muted",
  sttStatusText: "",
  sttStatusParams: {},
  llmModels: [],
  llmStatusKey: "llm_status_loading",
  llmStatusStyle: "muted",
  llmStatusText: "",
  llmStatusParams: {},
  embeddingModels: [],
  embeddingStatusKey: "embedding_status_loading",
  embeddingStatusStyle: "muted",
  embeddingStatusText: "",
  embeddingStatusParams: {},
  quickJobId: null,
  quickStatusKey: "quick_record_state_idle",
  quickStatusStyle: "muted",
  quickHintKey: "quick_record_hint_ready",
  quickHintText: "",
  quickHintStyle: "muted",
  quickPollTimer: null,
  quickCompletedHandledJobId: "",
  quickStopOverlayVisible: false,
  compareItems: [],
  llmArtifact: {
    meetingId: "",
    transcriptSource: "clean",
    mode: "template",
    templateId: "analysis",
    forceRebuild: false,
    chatMessages: [],
    chatAttachments: [],
    chatHintKey: "llm_chat_hint_idle",
    chatHintText: "",
    chatHintStyle: "muted",
    lastResponse: null,
    busy: false,
    hintKey: "llm_artifact_hint_idle",
    hintText: "",
    hintStyle: "muted",
  },
  llmSourceMode: "files",
  rag: {
    selectedMeetingIds: new Set(),
    savedSets: {},
    activeSavedSet: "",
    source: "clean",
    topK: 8,
    autoIndex: true,
    forceReindex: false,
    useLlmAnswer: true,
    lastResponse: null,
    queryBusy: false,
    indexBusy: false,
    indexJobId: "",
    indexJobStatus: null,
    chatMessages: [],
    chatAttachments: [],
    chatHintKey: "rag_chat_hint_idle",
    chatHintText: "",
    chatHintStyle: "muted",
    hintKey: "rag_hint_idle",
    hintText: "",
    hintStyle: "muted",
  },
  recordsMeta: new Map(),
  reportMeetingSelection: {
    raw: "",
    clean: "",
  },
  languageProfile: "mixed",
  diagnosticsLast: null,
  workMode: "link_fallback",
  flowStep: "mode",
  resultsTab: "audio",
  instanceId: `${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 10)}`,
  captureLockTimer: null,
  captureLockConflictMeetingId: "",
  captureClaimInProgress: false,
  uiLogLastByKey: new Map(),
  warnedSystemLowAt: 0,
  busyOverlayCount: 0,
  busyOverlayProgressPct: 0,
  busyOverlayMinimized: false,
  busyOverlayTimer: null,
  busyOverlayStartedAtMs: 0,
  busyOverlayDurationMs: 45000,
  busyOverlayManualProgress: null,
  busyOverlayCancelable: false,
  busyOverlayCancelHintKey: "busy_overlay_cancelled",
  busyOverlayAbortController: null,
  busyOverlayCancelledByUser: false,
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
const QUICK_PROBE_DURATION_SEC = 5;
const QUICK_SIGNAL_MIN_PEAK = 0.001;
const CAPTURE_LOCK_KEY = "9second_capture_active_lock";
const CAPTURE_LOCK_TTL_MS = 20000;
const CAPTURE_LOCK_HEARTBEAT_MS = 4000;
const WORK_MODE_KEY = "9second_capture_work_mode";
const RAG_SAVED_SETS_KEY = "9second_capture_rag_saved_sets_v1";
const UI_EVENT_ENDPOINT = "/v1/diagnostics/ui-event";
const UI_EVENT_THROTTLE_MS = 3000;
const MEETING_TIME_ZONE = "Europe/Moscow";
const TRANSCRIPT_QUALITY_PROFILE = "balanced";
const LLM_FILES_WORKSPACE_ID = "llm_files_workspace";
const BUSY_PROGRESS_DURATION_BY_TITLE = {
  llm_artifact_busy_title: 135000,
  busy_rag_index_title: 180000,
  busy_rag_query_title: 90000,
  busy_report_title: 60000,
  busy_mp3_title: 30000,
  busy_finish_title: 45000,
};
const WORK_MODE_CONFIGS = {
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
    supportsRealtime: true,
    supportsUpload: false,
    supportsQuick: true,
    forceCaptureMode: "screen",
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
const EMBEDDING_MODEL_HINTS = [
  "embed",
  "embedding",
  "text-embedding",
  "nomic-embed",
  "mxbai-embed",
  "bge",
  "e5",
  "gte",
  "minilm",
  "arctic-embed",
  "jina-embeddings",
];

const i18n = {
  ru: {
    subtitle: "Локальный агент записи встреч",
    theme_label: "Тема",
    theme_light: "Светлая",
    theme_dark: "Тёмная",
    flow_mode: "Режим",
    flow_capture: "Запись",
    flow_process: "Обработка",
    flow_results: "Результаты",
    work_mode_title: "Режим работы",
    help_work_mode:
      "Выберите один из 3 способов записи встречи. Активный способ включает только свои настройки.",
    help_mode_driver:
      "Запись системного звука через виртуальный драйвер (BlackHole/VB-CABLE/Monitor).",
    help_mode_browser:
      "Захват вкладки/экрана браузером. Для системного звука включайте Share audio.",
    help_mode_api:
      "Подключение к встрече через API-коннектор. Запись MP3 запускается кнопками Старт/Стоп.",
    help_mode_quick:
      "Вставьте ссылку, нажмите «Старт»: агент откроет встречу и запишет через браузерный Share audio.",
    work_mode_hint:
      "Выберите один режим: его настройки будут активны, остальные секции станут неактивными.",
    work_mode_active_label: "Активный режим:",
    work_mode_driver: "Драйвер: системный звук",
    work_mode_browser: "Браузер: экран + звук",
    work_mode_api: "API: подключение к встрече",
    work_mode_quick: "Ссылка: браузер + звук",
    work_mode_desc_driver:
      "Запись встреч в realtime через виртуальный драйвер (BlackHole/VB-CABLE/Monitor).",
    work_mode_desc_browser:
      "Запись через браузерный захват экрана и звука (Share audio в диалоге обязателен).",
    work_mode_desc_api:
      "Подключение к видеовстрече через API-коннектор и запись MP3 без текстовых апдейтов во время записи.",
    work_mode_desc_quick:
      "Запись по ссылке через браузерный захват: на «Старт» открываем встречу и пишем звук вкладки (Share audio).",
    mode_settings_title: "Настройки выбранного режима",
    mode_settings_browser_hint:
      "Для браузерного захвата выберите вкладку/экран и включите “Share audio”.",
    mode_settings_browser_hint_2:
      "Микрофон настраивается в «Запись», STT-параметры для отчётов — в «Результаты».",
    mode_settings_api_hint:
      "Укажите параметры API-подключения. Запуск и остановка записи MP3 выполняются в блоке «Запись».",
    work_mode_recording_disabled:
      "Режим записи выключен для текущего профиля. Переключитесь на «Браузер» или «Ссылка».",
    work_mode_quick_no_realtime_diag:
      "В текущем режиме realtime-индикатор текста не используется. Для проверки сигнала нажмите «Проверить».",
    work_mode_upload_disabled:
      "Загрузка файла выключена в текущем режиме. Активируйте «API/файл».",
    work_mode_quick_disabled:
      "Режим API-коннектора выключен для текущего профиля. Активируйте «API: подключение к встрече».",
    work_mode_device_disabled:
      "Настройки драйвера доступны только в режиме «Драйвер: системный звук».",
    err_work_mode_switch_locked:
      "Нельзя переключить режим во время активной записи/загрузки. Сначала остановите текущий процесс.",
    err_work_mode_realtime_only:
      "Выбранный режим не поддерживает realtime запись. Переключитесь на «Браузер» или «Ссылка».",
    err_work_mode_upload_only:
      "Прямая загрузка файла отключена в режимах захвата. Используйте «Импорт MP3» в блоке «Результаты».",
    err_work_mode_quick_only:
      "Этот запуск доступен только в режиме «API: подключение к встрече».",
    err_link_mode_url_missing: "Укажите ссылку встречи для режима «Ссылка».",
    link_mode_opening: "Открываем ссылку встречи перед началом записи...",
    link_mode_open_failed_popup:
      "Не удалось автоматически открыть ссылку. Откройте встречу вручную в браузере и продолжите старт.",
    connection_title: "Контекст интервью",
    api_key_label: "API ключ (опционально)",
    help_api_key:
      "Это ключ локального агента (X-API-Key), а не пароль/код от видеовстречи. Нужен только если на локальном API включена авторизация.",
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
    api_record_failed: "Ошибка API-записи. Проверьте ссылку встречи и настройки локального API.",
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
    stt_model_label: "STT модель",
    help_stt_model:
      "Локальная faster-whisper модель для транскрибации. Чем крупнее модель, тем выше качество, но дольше обработка и выше нагрузка.",
    llm_model_label: "LLM модель",
    help_llm:
      "LLM используется в чате для генерации форматов из прикрепленных файлов. Сам TXT транскрипт строится STT без LLM.",
    embedding_model_label: "Embeddings модель",
    help_embeddings_model:
      "Отдельная модель для RAG-поиска по смыслу (эмбеддинги). Используется для поиска/сравнения интервью. Если недоступна, включается локальный hashing fallback.",
    help_llm_schema:
      "Опционально. Если указать JSON-схему, LLM должен вернуть валидный JSON по этой структуре. Оставьте пустым для обычного текста.",
    help_transcript_raw:
      "Raw (грязный): прямой STT-транскрипт как есть, с паузами, междометиями и шумовыми вставками.",
    help_transcript_clean:
      "Clean (чистый): очищенный текст для чтения и отчетов. Обычно строится из raw через нормализацию и (опционально) LLM-очистку.",
    help_transcript_sources:
      "Raw — исходный STT текст. Normalized — служебная нормализация без LLM (убирает мусор/повторы, сохраняет смысл). Clean — пользовательский чистый текст после normalizer + опциональной LLM-очистки.",
    help_llm_chat_any_format:
      "LLM в этом блоке работает только по прикрепленным TXT/CSV/JSON/MD файлам и формирует нужный формат.",
    help_rag_chat_any_format:
      "RAG-чат сравнит выбранные интервью и соберет ответ с цитатами. Можно добавить файлы для дополнительного контекста.",
    stt_scan_btn: "Сканировать",
    stt_apply_btn: "Сменить модель",
    llm_scan_btn: "Сканировать",
    llm_apply_btn: "Сменить модель",
    embedding_scan_btn: "Сканировать",
    embedding_apply_btn: "Сменить модель",
    stt_status_loading: "Загружаем настройки STT...",
    stt_status_ready: "STT готов. Текущая модель: {model}.",
    stt_status_scanning: "Сканируем STT модели...",
    stt_status_scan_done: "Найдено STT моделей: {count}. Текущая: {model}.",
    stt_status_scan_empty: "STT модели не найдены. Текущая: {model}.",
    stt_status_applied: "STT модель переключена: {model}.",
    stt_status_apply_failed: "Не удалось переключить STT модель.",
    stt_status_unavailable: "STT API недоступен. Проверьте локальный backend.",
    stt_model_placeholder: "Выберите STT модель",
    stt_model_missing: "Сначала выберите STT модель.",
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
    embedding_status_loading: "Загружаем настройки embeddings...",
    embedding_status_ready: "Embeddings готовы. Текущая модель: {model}.",
    embedding_status_scanning: "Сканируем embeddings модели...",
    embedding_status_scan_done: "Найдено embeddings моделей: {count}. Текущая: {model}.",
    embedding_status_scan_empty: "Embeddings модели не найдены. Текущая: {model}.",
    embedding_status_applied: "Embeddings модель переключена: {model}.",
    embedding_status_apply_failed: "Не удалось переключить embeddings модель.",
    embedding_status_unavailable:
      "Embeddings API недоступен. RAG будет использовать hashing fallback.",
    embedding_model_placeholder: "Выберите embeddings модель",
    embedding_model_missing: "Сначала выберите embeddings модель.",
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
    chunks_label: "Чанки realtime:",
    transcript_title: "Транскрипт",
    raw_label: "Raw",
    clean_label: "Clean",
    raw_post: "После Стоп",
    clean_delay: "~3–4 сек",
    transcript_mode_record_first:
      "Итоговый текст строится после завершения записи для максимальной точности.",
    transcript_runtime_waiting: "Текст появится после завершения записи.",
    transcript_runtime_recording: "Идёт запись. Текст формируется после остановки записи.",
    transcript_runtime_loading: "Завершаем обработку MP3 и собираем итоговый текст...",
    transcript_runtime_ready: "Итоговый текст готов.",
    transcript_runtime_empty:
      "Запись завершена, но текста пока нет. Проверьте источник аудио и сохраните MP3 для повторной обработки.",
    transcript_empty_title: "Транскрипция после записи",
    transcript_empty_hint:
      "Во время записи показываются только индикаторы захвата. Итоговый текст появится после Стоп.",
    transcript_placeholder_raw_post:
      "Сырой текст появится после завершения записи (final pass по MP3).",
    transcript_placeholder_clean_post:
      "Чистый текст появится после завершения записи и финальной обработки.",
    records_title: "Результаты",
    results_tab_audio: "Аудио",
    results_tab_transcript: "Транскрипция",
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
    results_stt_title: "Настройки STT для транскриптов",
    results_report_name_label: "Имя файла отчёта (обязательно)",
    results_report_name_placeholder: "report_clean",
    results_generate_report_btn: "Сформировать TXT",
    results_download_report_btn: "Сохранить TXT",
    results_current_report_file: "Текущий файл отчёта",
    results_convert_title: "2) TXT транскрипты и LLM-чат",
    results_convert_settings_toggle: "Настройки STT и моделей",
    results_convert_hint:
      "Сначала сохраняем TXT транскрипт (Raw/Clean). Другие форматы создаются через LLM-чат ниже.",
    results_raw_lane_title: "Грязный транскрипт (Raw)",
    results_clean_lane_title: "Чистый транскрипт (Clean)",
    results_raw_report_name_placeholder: "raw_transcript",
    results_clean_report_name_placeholder: "clean_transcript",
    results_transcript_name_label: "Имя TXT файла",
    results_transcript_name_hint: "Введите имя файла (без .txt)",
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
    llm_artifact_title: "LLM-экспорт / кастомные форматы",
    llm_artifact_generate_btn: "Сформировать",
    llm_artifact_hint_idle:
      "Прикрепите файлы и отправьте запрос: LLM сформирует нужный формат только по вложениям.",
    llm_artifact_hint_running: "LLM-артефакт формируется...",
    llm_artifact_hint_done: "LLM-артефакт сформирован.",
    llm_artifact_hint_failed: "Не удалось сформировать LLM-артефакт.",
    llm_artifact_hint_no_meeting: "Выберите запись для генерации LLM-артефакта.",
    llm_artifact_hint_prompt_required: "Для режимов Custom/Table укажите prompt.",
    llm_artifact_hint_schema_invalid: "Schema JSON некорректен. Проверьте формат JSON.",
    llm_artifact_hint_no_result: "Сначала сформируйте LLM-артефакт.",
    llm_artifact_hint_needs_text_or_transcript:
      "Добавьте текст через вложения. Этот LLM-блок работает только по прикрепленным файлам.",
    llm_artifact_source_panel_title: "Источник и режим",
    llm_artifact_meeting_label: "Запись",
    llm_artifact_transcript_source_label: "Источник транскрипта",
    llm_artifact_mode_label: "Режим",
    llm_artifact_mode_template: "Шаблон",
    llm_artifact_mode_custom: "Custom prompt",
    llm_artifact_mode_table: "Таблица (JSON+CSV)",
    llm_artifact_template_label: "Шаблон",
    llm_artifact_template_analysis: "Analysis",
    llm_artifact_template_summary: "Summary",
    llm_artifact_template_structured: "Structured table",
    llm_artifact_template_senior: "Senior brief",
    llm_artifact_force_rebuild: "Принудительно пересобрать (игнорировать cache)",
    llm_artifact_prompt_panel_title: "Prompt / Schema",
    llm_artifact_prompt_label: "Prompt (для custom/table)",
    llm_artifact_prompt_placeholder:
      "Сделай протокол встречи: темы, решения, action items (owner, due_date, status), риски, блокеры.",
    llm_artifact_schema_label: "Schema JSON (опционально)",
    llm_artifact_schema_placeholder: '{"type":"object","properties":{"rows":{"type":"array"}}}',
    llm_artifact_result_title: "Результат LLM-артефакта",
    llm_artifact_result_none: "Результата пока нет",
    llm_artifact_meta_template:
      "artifact_id={artifact_id}\nmode={mode}\ntemplate={template}\nsource={source}\nkind={kind}\nstatus={status}\ncreated_at={created_at}\ntranscript_chars={chars}\ncached={cached}",
    llm_artifact_file_download: "Скачать {fmt}",
    llm_artifact_busy_title: "LLM-артефакт",
    llm_artifact_busy_text:
      "Генерируем артефакт из прикрепленных файлов. Для custom/table и LLM может потребоваться больше времени.",
    llm_chat_title: "LLM чат по файлам",
    llm_mode_files_only: "Files only",
    llm_mode_rag: "RAG",
    llm_mode_hint_files: "Режим Files only: LLM обрабатывает только прикрепленные файлы.",
    llm_mode_hint_rag: "Режим RAG: поиск по интервью через векторы/цитаты + ответ LLM по найденным фрагментам.",
    llm_chat_clear_btn: "Очистить",
    llm_chat_send_btn: "Отправить",
    llm_chat_hint_idle: "Прикрепите TXT/CSV/JSON/MD файлы и опишите нужный формат. LLM обработает только вложения.",
    llm_chat_hint_cleared: "Предыдущие результаты очищены.",
    llm_chat_hint_files_required: "Прикрепите хотя бы один текстовый файл (TXT/CSV/JSON/MD).",
    llm_chat_hint_prompt_required: "Введите запрос в чат LLM.",
    llm_chat_hint_running: "LLM обрабатывает запрос...",
    llm_chat_hint_done: "Ответ LLM получен.",
    llm_chat_hint_failed: "Не удалось получить ответ LLM.",
    llm_chat_hint_needs_text_or_transcript:
      "Добавьте текст через вложения. Этот LLM-блок работает только по прикрепленным файлам.",
    llm_chat_input_label: "Запрос в LLM",
    llm_chat_input_placeholder:
      "Сделай протокол встречи по прикрепленным файлам: summary, topics, decisions, action_items, risks, blockers.",
    llm_chat_preset_summary: "Summary (интервьюеры)",
    llm_chat_preset_table: "Таблица",
    llm_chat_preset_json: "JSON",
    llm_chat_preset_csv: "CSV",
    llm_chat_preset_summary_prompt:
      "Сделай summary по прикрепленным файлам: ключевые темы, решения, риски, договоренности, next steps.",
    llm_chat_preset_table_prompt:
      "Сделай таблицу для Google Sheets по прикрепленным файлам встречи: columns=[Тема, Решение, Действие, Ответственный, Срок, Риск, Статус], rows по смыслу. Не выдумывай факты: если Ответственный/Срок не названы явно, ставь «Не указан». Не подставляй имена по догадке.",
    llm_chat_preset_json_prompt:
      "Верни адаптивный JSON по прикрепленным файлам. Сначала определи meeting_type (interview|standup|status|planning|sync|other). Затем верни keys: meeting_type, summary, topics, decisions, action_items[{owner,task,due_date,status}], risks, blockers, open_questions, next_steps. Если meeting_type=interview, дополнительно верни skills, evidence, recommendations, итоговый_вердикт.",
    llm_chat_preset_csv_prompt:
      "Собери табличный CSV по прикрепленным файлам обычной встречи: topic, decision, action_item, owner, due_date, risk, status.",
    llm_chat_history_empty: "Здесь появится диалог с LLM.",
    llm_chat_files_title: "Файлы результата",
    chat_attach_btn: "📎 Прикрепить файлы",
    chat_attach_none: "Файлы не выбраны",
    chat_attach_selected: "Файлов: {count}",
    llm_chat_role_user: "Вы",
    llm_chat_role_assistant: "LLM",
    llm_chat_preview_error: "Не удалось загрузить предпросмотр артефакта.",
    rag_title: "RAG чат / сравнение интервью",
    rag_refresh_meetings: "Обновить список",
    rag_index_selected: "Индексировать выбранные",
    rag_run_btn: "Выполнить запрос",
    rag_hint_idle: "Выберите интервью, задайте запрос и получите ответ с цитатами из транскриптов.",
    rag_hint_indexing: "Строим RAG индекс для выбранных интервью...",
    rag_hint_querying: "Ищем релевантные фрагменты и собираем ответ...",
    rag_hint_done: "RAG запрос выполнен.",
    rag_hint_query_empty: "Введите вопрос или задачу для RAG.",
    rag_hint_index_no_selection: "Выберите хотя бы одну запись для индексации.",
    rag_hint_failed: "RAG запрос завершился с ошибкой.",
    rag_hint_no_results: "По запросу не найдено релевантных фрагментов.",
    rag_hint_export_empty: "Сначала выполните RAG запрос.",
    rag_meeting_picker_title: "Интервью для сравнения",
    rag_meeting_picker_hint: "Если ничего не выбрано, поиск пойдет по последним записям.",
    rag_picker_empty: "Список записей пуст. Сначала создайте или импортируйте запись.",
    rag_select_current: "Текущая запись",
    rag_select_all: "Выбрать все",
    rag_clear_selection: "Очистить",
    rag_saved_set_none: "Сохраненные наборы",
    rag_saved_set_save: "Сохранить набор",
    rag_saved_set_load: "Загрузить",
    rag_saved_set_delete: "Удалить",
    rag_saved_set_prompt_name: "Введите название набора интервью для RAG compare:",
    rag_saved_set_hint_saved: "Набор сохранен.",
    rag_saved_set_hint_loaded: "Набор загружен.",
    rag_saved_set_hint_deleted: "Набор удален.",
    rag_saved_set_hint_empty_selection: "Сначала выберите хотя бы одну запись.",
    rag_saved_set_hint_choose: "Выберите сохраненный набор.",
    rag_source_label: "Источник транскрипта",
    rag_source_raw: "Raw",
    rag_source_normalized: "Normalized",
    rag_source_clean: "Clean",
    rag_index_status_prefix: "RAG индекс",
    rag_index_status_indexed: "готов",
    rag_index_status_outdated: "устарел",
    rag_index_status_missing: "нет",
    rag_index_status_invalid: "битый",
    rag_index_status_orphaned: "без транскрипта",
    rag_index_status_unknown: "неизвестно",
    rag_topk_label: "Top-K цитат",
    rag_query_title: "Запрос по выбранным интервью (compare)",
    rag_chat_send_btn: "Отправить",
    rag_chat_hint_idle: "RAG-чат сравнивает выбранные интервью и отвечает с цитатами.",
    rag_chat_hint_running: "RAG обрабатывает запрос...",
    rag_chat_hint_done: "Ответ RAG получен.",
    rag_chat_hint_failed: "Не удалось получить ответ RAG.",
    rag_chat_history_empty: "Здесь появится диалог RAG-чата.",
    rag_chat_role_user: "Вы",
    rag_chat_role_assistant: "RAG",
    rag_use_llm_answer: "Сгенерировать ответ LLM по найденным цитатам",
    rag_auto_index: "Автоиндексация выбранных интервью перед запросом",
    rag_force_reindex: "Принудительно пересобрать индекс",
    rag_query_input_label: "Вопрос / задача",
    rag_query_input_placeholder:
      "Сравни кандидатов по backend/system design и собери таблицу с сильными и слабыми сторонами.",
    rag_answer_prompt_label: "Доп. инструкция для ответа (опционально)",
    rag_answer_prompt_placeholder: "Ответь кратко, затем перечисли доказательства с ссылками [n].",
    rag_export_json: "Экспорт JSON",
    rag_export_csv: "Экспорт CSV цитат",
    rag_export_txt: "Экспорт TXT ответа",
    rag_answer_title: "Ответ (LLM/RAG)",
    rag_hits_title: "Цитаты / найденные фрагменты",
    rag_result_meta_none: "Нет результатов",
    rag_result_meta_template:
      "Встреч: {meetings}, индексов: {indexed}, чанков: {chunks}, top hits: {hits}, режим: {mode}",
    rag_hit_meta_score: "Score",
    rag_hit_meta_meeting: "Запись",
    rag_hit_meta_candidate: "Кандидат",
    rag_hit_meta_vacancy: "Вакансия",
    rag_hit_meta_level: "Уровень",
    rag_hit_meta_lines: "Строки",
    rag_hit_meta_time: "Время",
    rag_hit_meta_speakers: "Спикеры",
    rag_hits_empty: "Здесь появятся найденные фрагменты с цитатами.",
    rag_result_files_title: "Файлы результата RAG",
    rag_result_file_download: "Скачать {fmt}",
    busy_rag_query_title: "RAG запрос",
    busy_rag_query_text: "Ищем фрагменты по выбранным интервью и готовим ответ с цитатами.",
    busy_rag_index_title: "Индексация RAG",
    busy_rag_index_text: "Собираем чанки и citations по выбранным транскриптам.",
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
    prompt_report_name: "Укажите имя TXT файла:",
    hint_record_renamed: "Название записи обновлено.",
    hint_record_rename_failed: "Не удалось переименовать запись. Проверьте лог локального API.",
    hint_mp3_saved: "MP3 сохранен.",
    hint_mp3_not_found: "MP3 пока недоступен для этой записи.",
    hint_mp3_not_found_ffmpeg:
      "MP3 недоступен. Скорее всего не установлен ffmpeg (нужен для конвертации backup_audio.webm в MP3).",
    hint_mp3_import_started: "Импортируем MP3 в агент (без транскрибации)...",
    hint_mp3_import_done: "MP3 импортирован. Транскрипт будет построен только по запросу.",
    hint_mp3_import_failed: "Не удалось импортировать MP3 файл.",
    hint_report_generated: "TXT транскрипт сохранён.",
    hint_report_source_missing: "Сначала выберите запись для транскрипта.",
    hint_report_name_missing: "Укажите имя TXT файла.",
    hint_report_missing: "TXT транскрипт пока не найден для этой записи.",
    hint_transcript_not_ready:
      "Транскрипт ещё не сформирован. Нажмите «TXT» в блоке нужного источника (Raw/Clean).",
    hint_transcript_generate_failed: "Не удалось сформировать транскрипт. Проверьте логи STT.",
    busy_overlay_title: "Подождите...",
    busy_overlay_cancel_btn: "Прервать",
    busy_overlay_minimize_btn: "Свернуть",
    busy_overlay_restore_btn: "Развернуть",
    busy_overlay_progress_label: "Прогресс",
    busy_overlay_cancelled: "Операция прервана пользователем.",
    busy_finish_title: "Формируем MP3",
    busy_finish_text:
      "Сохраняем аудио и готовим MP3. Текст и отчёты формируются позже по запросу в блоке «Результаты».",
    busy_mp3_title: "Готовим MP3",
    busy_mp3_text: "Конвертируем запись в MP3 и открываем сохранение файла.",
    busy_report_title: "Формируем транскрипт",
    busy_report_text:
      "Строим TXT транскрипт из MP3 через STT (без LLM). На длинных записях это может занять время.",
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
    quick_record_title: "Запись по ссылке (браузерный захват)",
    quick_record_url_label: "Ссылка встречи",
    help_quick_url:
      "Ссылка встречи. На старте агент откроет её и запустит браузерный захват вкладки со звуком.",
    quick_record_url_placeholder: "https://...",
    quick_record_duration_label: "Длительность (сек)",
    help_quick_duration:
      "Ограничение времени quick-записи. По достижении лимита запись остановится.",
    quick_record_start_btn: "Quick старт",
    quick_record_stop_btn: "Quick стоп",
    quick_record_state_idle: "Не запущено",
    quick_record_state_running: "Идет запись",
    quick_record_state_stopping: "Останавливаем",
    quick_record_state_completed: "Завершено",
    quick_record_state_failed: "Ошибка",
    quick_record_hint_ready:
      "Нажмите «Старт»: откроется встреча, затем в окне браузера выберите вкладку встречи и включите Share audio.",
    quick_record_hint_started: "Fallback запись запущена.",
    quick_record_hint_stopped: "Fallback запись остановлена.",
    quick_record_hint_missing_url: "Укажите ссылку встречи (http/https).",
    quick_record_hint_missing_duration: "Укажите корректную длительность (>= 5 сек).",
    quick_record_hint_already_running: "Quick запись уже выполняется.",
    quick_record_hint_start_failed: "Не удалось запустить quick запись.",
    quick_record_hint_stop_failed: "Не удалось остановить quick запись.",
    quick_record_hint_running_probe_wait: "Идёт запись. Первичная проверка сигнала через {seconds} сек.",
    quick_record_hint_running_probe_ok: "Идёт запись: сигнал обнаружен ({peak}%). Устройство: {device}.",
    quick_record_hint_running_probe_fail:
      "Идёт запись, но за первые 5 сек сигнал не обнаружен. Проверьте, что звук встречи реально воспроизводится на системный выход.",
    quick_record_hint_failed: "Quick запись завершилась с ошибкой: {error}",
    quick_record_hint_completed: "Quick запись завершена: {path}",
    quick_probe_failed: "Проверка quick-захвата не удалась: {detail}",
    quick_probe_no_signal: "Проверка quick-захвата: сигнал не обнаружен. Устройство: {device}.",
    quick_probe_signal_ok: "Проверка quick-захвата: сигнал есть ({peak}%). Устройство: {device}.",
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
      "Обнаружена активная запись в другом окне/вкладке или зависшая сессия. Нажмите «Забрать управление в этом окне» и повторите.",
    capture_claim_btn: "Забрать управление в этом окне",
    capture_claim_running: "Освобождаем захват и завершаем зависшую сессию...",
    capture_claim_success: "Управление захватом передано этому окну. Можно запускать запись.",
    capture_claim_no_active: "Активных сессий не найдено. Можно запускать запись.",
    capture_claim_failed: "Не удалось передать управление. Проверьте локальный API и повторите.",
    warn_system_level_low:
      "Системный звук очень тихий. Проверьте маршрутизацию: вывод встречи должен идти в BlackHole/VB-CABLE/Monitor.",
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
    flow_mode: "Mode",
    flow_capture: "Capture",
    flow_process: "Process",
    flow_results: "Results",
    work_mode_title: "Work mode",
    help_work_mode:
      "Pick one of three interview capture modes. Only the active mode settings are applied.",
    help_mode_driver:
      "Capture system audio through virtual loopback driver (BlackHole/VB-CABLE/Monitor).",
    help_mode_browser:
      "Capture screen/tab via browser. Enable Share audio to include system sound.",
    help_mode_api:
      "Connect to meeting through API connector. MP3 recording starts with Start/Stop controls.",
    help_mode_quick:
      "Paste a meeting URL and press Start: app opens the meeting and records via browser Share audio.",
    work_mode_hint:
      "Choose one mode: only its settings stay active, other sections are dimmed and blocked.",
    work_mode_active_label: "Active mode:",
    work_mode_driver: "Driver: system audio",
    work_mode_browser: "Browser: screen + audio",
    work_mode_api: "API: meeting connector",
    work_mode_quick: "Link: browser + audio",
    work_mode_desc_driver:
      "Realtime interview capture via virtual loopback driver (BlackHole/VB-CABLE/Monitor).",
    work_mode_desc_browser:
      "Browser capture of screen + audio (Share audio must be enabled).",
    work_mode_desc_api:
      "Meeting API connector flow: record MP3 from meeting source without transcript updates during recording.",
    work_mode_desc_quick:
      "Meeting-by-link browser capture: on Start we open the meeting and record tab audio via Share audio.",
    mode_settings_title: "Selected mode settings",
    mode_settings_browser_hint:
      "For browser capture, choose tab/screen and enable “Share audio”.",
    mode_settings_browser_hint_2:
      "Microphone is configured in Recording. STT settings for reports are in Results.",
    mode_settings_api_hint:
      "Set API connector parameters. Start/Stop in Recording controls MP3 session.",
    work_mode_recording_disabled:
      "Recording controls are disabled for this profile. Switch to Browser or Link mode.",
    work_mode_quick_no_realtime_diag:
      "Realtime text monitor is not used in this mode. Use Check to run signal probe.",
    work_mode_upload_disabled:
      "File upload is disabled for this profile. Switch to API/file mode.",
    work_mode_quick_disabled:
      "API connector mode is disabled for this profile. Switch to API meeting connector mode.",
    work_mode_device_disabled:
      "Driver controls are available only in Driver system-audio mode.",
    err_work_mode_switch_locked:
      "Cannot switch mode during active recording/upload. Stop current flow first.",
    err_work_mode_realtime_only:
      "Selected mode does not support realtime recording. Switch to Browser or Link.",
    err_work_mode_upload_only:
      "Direct upload mode is removed from capture panels. Use MP3 import in Results.",
    err_work_mode_quick_only:
      "This flow is available only in API meeting connector mode.",
    err_link_mode_url_missing: "Provide meeting URL for Link mode.",
    link_mode_opening: "Opening meeting URL before capture...",
    link_mode_open_failed_popup:
      "Could not open meeting URL automatically. Open it manually in browser and continue.",
    connection_title: "Interview context",
    api_key_label: "API key (optional)",
    help_api_key:
      "This is the local agent key (X-API-Key), not a meeting password/code. It is required only when local API authentication is enabled.",
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
    api_record_failed: "API recording failed. Check meeting URL and local API settings.",
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
    stt_model_label: "STT model",
    help_stt_model:
      "Local faster-whisper model for transcription. Larger models improve quality but increase latency and CPU load.",
    llm_model_label: "LLM model",
    help_llm:
      "LLM is used in chat to generate formats from attached files. TXT transcript itself is built by STT without LLM.",
    embedding_model_label: "Embeddings model",
    help_embeddings_model:
      "Separate model for semantic RAG retrieval (embeddings). Used for search/compare across interviews. If unavailable, local hashing fallback is used.",
    help_llm_schema:
      "Optional. If provided, LLM should return valid JSON that follows this schema guide. Leave empty for plain text output.",
    help_transcript_raw:
      "Raw: direct STT transcript as-is, including fillers, pauses, and noisy fragments.",
    help_transcript_clean:
      "Clean: user-facing cleaned transcript for reading and reports. Usually built from raw via normalization and optional LLM cleanup.",
    help_transcript_sources:
      "Raw = original STT text. Normalized = internal deterministic cleanup without LLM (removes noise/repeats, preserves meaning). Clean = user-facing text after normalizer + optional LLM cleanup.",
    help_llm_chat_any_format:
      "LLM in this block works only with attached TXT/CSV/JSON/MD files and generates requested output format.",
    help_rag_chat_any_format:
      "RAG chat compares selected interviews and returns citation-backed answers. You can attach files for extra context.",
    stt_scan_btn: "Scan",
    stt_apply_btn: "Switch model",
    llm_scan_btn: "Scan",
    llm_apply_btn: "Switch model",
    embedding_scan_btn: "Scan",
    embedding_apply_btn: "Switch model",
    stt_status_loading: "Loading STT settings...",
    stt_status_ready: "STT ready. Current model: {model}.",
    stt_status_scanning: "Scanning STT models...",
    stt_status_scan_done: "STT models found: {count}. Current: {model}.",
    stt_status_scan_empty: "No STT models found. Current: {model}.",
    stt_status_applied: "STT model switched: {model}.",
    stt_status_apply_failed: "Failed to switch STT model.",
    stt_status_unavailable: "STT API is unavailable. Check local backend.",
    stt_model_placeholder: "Select STT model",
    stt_model_missing: "Select an STT model first.",
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
    embedding_status_loading: "Loading embeddings settings...",
    embedding_status_ready: "Embeddings ready. Current model: {model}.",
    embedding_status_scanning: "Scanning embeddings models...",
    embedding_status_scan_done: "Embedding models found: {count}. Current: {model}.",
    embedding_status_scan_empty: "No embedding models found. Current: {model}.",
    embedding_status_applied: "Embedding model switched: {model}.",
    embedding_status_apply_failed: "Failed to switch embedding model.",
    embedding_status_unavailable:
      "Embeddings API unavailable. RAG will use hashing fallback.",
    embedding_model_placeholder: "Select embedding model",
    embedding_model_missing: "Select an embedding model first.",
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
    chunks_label: "Realtime chunks:",
    transcript_title: "Transcript",
    raw_label: "Raw",
    clean_label: "Clean",
    raw_post: "Post-stop",
    clean_delay: "~3–4s",
    transcript_mode_record_first:
      "Final transcript is built after recording ends for maximum accuracy.",
    transcript_runtime_waiting: "Transcript will appear after recording stops.",
    transcript_runtime_recording: "Recording in progress. Transcript is generated after stop.",
    transcript_runtime_loading: "Finalizing MP3 and building final transcript...",
    transcript_runtime_ready: "Final transcript is ready.",
    transcript_runtime_empty:
      "Recording is finished, but transcript is still empty. Check audio source and save MP3 for reprocessing.",
    transcript_empty_title: "Post-record transcription",
    transcript_empty_hint:
      "During recording, only capture health indicators are shown. Final transcript appears after Stop.",
    transcript_placeholder_raw_post:
      "Raw text appears after recording stops (final pass from MP3).",
    transcript_placeholder_clean_post:
      "Clean text appears after recording stops and final processing is complete.",
    records_title: "Results",
    results_tab_audio: "Audio",
    results_tab_transcript: "Transcript",
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
    results_stt_title: "STT settings for transcripts",
    results_report_name_label: "Report filename (required)",
    results_report_name_placeholder: "report_clean",
    results_generate_report_btn: "Build TXT",
    results_download_report_btn: "Save TXT",
    results_current_report_file: "Current report file",
    results_convert_title: "2) TXT transcripts and LLM chat",
    results_convert_settings_toggle: "STT and model settings",
    results_convert_hint:
      "First save TXT transcript (raw/clean). Generate other formats in the LLM chat below.",
    results_raw_lane_title: "Raw transcript",
    results_clean_lane_title: "Clean transcript",
    results_raw_report_name_placeholder: "raw_transcript",
    results_clean_report_name_placeholder: "clean_transcript",
    results_transcript_name_label: "TXT filename",
    results_transcript_name_hint: "Enter filename (without .txt)",
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
    llm_artifact_title: "LLM export / custom formats",
    llm_artifact_generate_btn: "Generate",
    llm_artifact_hint_idle: "Attach files and send request. LLM will generate output format from attachments only.",
    llm_artifact_hint_running: "Generating LLM artifact...",
    llm_artifact_hint_done: "LLM artifact generated.",
    llm_artifact_hint_failed: "Failed to generate LLM artifact.",
    llm_artifact_hint_no_meeting: "Select a recording for LLM artifact generation.",
    llm_artifact_hint_prompt_required: "Prompt is required for Custom/Table modes.",
    llm_artifact_hint_schema_invalid: "Schema JSON is invalid. Check JSON syntax.",
    llm_artifact_hint_no_result: "Generate an LLM artifact first.",
    llm_artifact_hint_needs_text_or_transcript:
      "Add text via attachments. This LLM block works with attached files only.",
    llm_artifact_source_panel_title: "Source and mode",
    llm_artifact_meeting_label: "Recording",
    llm_artifact_transcript_source_label: "Transcript source",
    llm_artifact_mode_label: "Mode",
    llm_artifact_mode_template: "Template",
    llm_artifact_mode_custom: "Custom prompt",
    llm_artifact_mode_table: "Table (JSON+CSV)",
    llm_artifact_template_label: "Template",
    llm_artifact_template_analysis: "Analysis",
    llm_artifact_template_summary: "Summary",
    llm_artifact_template_structured: "Structured table",
    llm_artifact_template_senior: "Senior brief",
    llm_artifact_force_rebuild: "Force rebuild (ignore cache)",
    llm_artifact_prompt_panel_title: "Prompt / Schema",
    llm_artifact_prompt_label: "Prompt (for custom/table)",
    llm_artifact_prompt_placeholder:
      "Build meeting minutes: topics, decisions, action items (owner, due_date, status), risks, blockers.",
    llm_artifact_schema_label: "Schema JSON (optional)",
    llm_artifact_schema_placeholder: '{"type":"object","properties":{"rows":{"type":"array"}}}',
    llm_artifact_result_title: "LLM artifact result",
    llm_artifact_result_none: "No artifact yet",
    llm_artifact_meta_template:
      "artifact_id={artifact_id}\nmode={mode}\ntemplate={template}\nsource={source}\nkind={kind}\nstatus={status}\ncreated_at={created_at}\ntranscript_chars={chars}\ncached={cached}",
    llm_artifact_file_download: "Download {fmt}",
    llm_artifact_busy_title: "LLM artifact",
    llm_artifact_busy_text:
      "Generating artifact from attached files. Custom/table modes may take longer with LLM.",
    llm_chat_title: "LLM chat over files",
    llm_mode_files_only: "Files only",
    llm_mode_rag: "RAG",
    llm_mode_hint_files: "Files only mode: LLM uses only attached files.",
    llm_mode_hint_rag: "RAG mode: semantic retrieval over interviews + optional LLM answer with citations.",
    llm_chat_clear_btn: "Clear",
    llm_chat_send_btn: "Send",
    llm_chat_hint_idle: "Attach TXT/CSV/JSON/MD files and describe target format. LLM will use attachments only.",
    llm_chat_hint_cleared: "Previous results were cleared.",
    llm_chat_hint_files_required: "Attach at least one text file (TXT/CSV/JSON/MD).",
    llm_chat_hint_prompt_required: "Enter a prompt for LLM chat.",
    llm_chat_hint_running: "LLM is processing the request...",
    llm_chat_hint_done: "LLM response received.",
    llm_chat_hint_failed: "Failed to get an LLM response.",
    llm_chat_hint_needs_text_or_transcript:
      "Add text via attachments. This LLM block works with attached files only.",
    llm_chat_input_label: "LLM prompt",
    llm_chat_input_placeholder:
      "Build meeting minutes from attached files: summary, topics, decisions, action_items, risks, blockers.",
    llm_chat_preset_summary: "Summary (interviewer compare)",
    llm_chat_preset_table: "Table",
    llm_chat_preset_json: "JSON",
    llm_chat_preset_csv: "CSV",
    llm_chat_preset_summary_prompt:
      "Create a summary from attached files: key topics, decisions, risks, agreements, next steps.",
    llm_chat_preset_table_prompt:
      "Build a Google Sheets table for a regular meeting from attached files with columns [Topic, Decision, Action, Owner, DueDate, Risk, Status]. Do not invent facts: if Owner/DueDate are not explicitly stated, use \"Not specified\". Do not assign people by guess.",
    llm_chat_preset_json_prompt:
      "Return adaptive JSON from attached files. Detect meeting_type first (interview|standup|status|planning|sync|other). Return keys: meeting_type, summary, topics, decisions, action_items[{owner,task,due_date,status}], risks, blockers, open_questions, next_steps. If meeting_type=interview, also include skills, evidence, recommendations, final_decision.",
    llm_chat_preset_csv_prompt:
      "Build a CSV from attached files of a regular meeting with fields: topic, decision, action_item, owner, due_date, risk, status.",
    llm_chat_history_empty: "LLM chat history will appear here.",
    llm_chat_files_title: "Result files",
    chat_attach_btn: "📎 Attach files",
    chat_attach_none: "No files selected",
    chat_attach_selected: "Files: {count}",
    llm_chat_role_user: "You",
    llm_chat_role_assistant: "LLM",
    llm_chat_preview_error: "Failed to load artifact preview.",
    rag_title: "RAG chat / interview comparison",
    rag_refresh_meetings: "Refresh list",
    rag_index_selected: "Index selected",
    rag_run_btn: "Run query",
    rag_hint_idle: "Select interviews, enter a query, and get an answer with transcript citations.",
    rag_hint_indexing: "Building RAG index for selected interviews...",
    rag_hint_querying: "Searching relevant chunks and composing the answer...",
    rag_hint_done: "RAG query completed.",
    rag_hint_query_empty: "Enter a RAG question or task.",
    rag_hint_index_no_selection: "Select at least one recording to build an index.",
    rag_hint_failed: "RAG query failed.",
    rag_hint_no_results: "No relevant transcript chunks were found.",
    rag_hint_export_empty: "Run a RAG query first.",
    rag_meeting_picker_title: "Interviews for comparison",
    rag_meeting_picker_hint: "If nothing is selected, search runs on recent recordings.",
    rag_picker_empty: "No recordings yet. Create or import a recording first.",
    rag_select_current: "Current record",
    rag_select_all: "Select all",
    rag_clear_selection: "Clear",
    rag_saved_set_none: "Saved sets",
    rag_saved_set_save: "Save set",
    rag_saved_set_load: "Load",
    rag_saved_set_delete: "Delete",
    rag_saved_set_prompt_name: "Enter a name for this RAG compare set:",
    rag_saved_set_hint_saved: "Set saved.",
    rag_saved_set_hint_loaded: "Set loaded.",
    rag_saved_set_hint_deleted: "Set deleted.",
    rag_saved_set_hint_empty_selection: "Select at least one recording first.",
    rag_saved_set_hint_choose: "Select a saved set.",
    rag_source_label: "Transcript source",
    rag_source_raw: "Raw",
    rag_source_normalized: "Normalized",
    rag_source_clean: "Clean",
    rag_index_status_prefix: "RAG index",
    rag_index_status_indexed: "ready",
    rag_index_status_outdated: "outdated",
    rag_index_status_missing: "missing",
    rag_index_status_invalid: "invalid",
    rag_index_status_orphaned: "orphaned",
    rag_index_status_unknown: "unknown",
    rag_topk_label: "Top-K citations",
    rag_query_title: "Query across selected interviews (compare)",
    rag_chat_send_btn: "Send",
    rag_chat_hint_idle: "RAG chat compares selected interviews and answers with citations.",
    rag_chat_hint_running: "RAG is processing your request...",
    rag_chat_hint_done: "RAG response received.",
    rag_chat_hint_failed: "Failed to get a RAG response.",
    rag_chat_history_empty: "RAG chat history will appear here.",
    rag_chat_role_user: "You",
    rag_chat_role_assistant: "RAG",
    rag_use_llm_answer: "Generate an LLM answer from retrieved citations",
    rag_auto_index: "Auto-index selected interviews before query",
    rag_force_reindex: "Force rebuild index",
    rag_query_input_label: "Question / task",
    rag_query_input_placeholder:
      "Compare candidates on backend/system design and build a table of strengths and weaknesses.",
    rag_answer_prompt_label: "Extra answer instruction (optional)",
    rag_answer_prompt_placeholder: "Answer briefly, then list evidence with [n] citations.",
    rag_export_json: "Export JSON",
    rag_export_csv: "Export citations CSV",
    rag_export_txt: "Export answer TXT",
    rag_answer_title: "Answer (LLM/RAG)",
    rag_hits_title: "Citations / retrieved chunks",
    rag_result_meta_none: "No results",
    rag_result_meta_template:
      "Meetings: {meetings}, indexed: {indexed}, chunks: {chunks}, top hits: {hits}, mode: {mode}",
    rag_hit_meta_score: "Score",
    rag_hit_meta_meeting: "Record",
    rag_hit_meta_candidate: "Candidate",
    rag_hit_meta_vacancy: "Vacancy",
    rag_hit_meta_level: "Level",
    rag_hit_meta_lines: "Lines",
    rag_hit_meta_time: "Time",
    rag_hit_meta_speakers: "Speakers",
    rag_hits_empty: "Retrieved chunks with citations will appear here.",
    rag_result_files_title: "RAG result files",
    rag_result_file_download: "Download {fmt}",
    busy_rag_query_title: "RAG query",
    busy_rag_query_text: "Searching selected interviews and preparing an answer with citations.",
    busy_rag_index_title: "RAG indexing",
    busy_rag_index_text: "Building chunks and citations for selected transcripts.",
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
    prompt_report_name: "Enter TXT filename:",
    hint_record_renamed: "Recording name updated.",
    hint_record_rename_failed: "Failed to rename recording. Check local API logs.",
    hint_mp3_saved: "MP3 saved.",
    hint_mp3_not_found: "MP3 is not available for this recording yet.",
    hint_mp3_not_found_ffmpeg:
      "MP3 is unavailable. ffmpeg is likely missing (required to convert backup_audio.webm to MP3).",
    hint_mp3_import_started: "Importing MP3 into agent (no auto transcription)...",
    hint_mp3_import_done: "MP3 imported. Transcript will be generated only on demand.",
    hint_mp3_import_failed: "Failed to import MP3 file.",
    hint_report_generated: "TXT transcript saved.",
    hint_report_source_missing: "Select a record for transcript export.",
    hint_report_name_missing: "Set TXT filename.",
    hint_report_missing: "TXT transcript is not available for this recording yet.",
    hint_transcript_not_ready:
      "Transcript is not generated yet. Click \"TXT\" in the needed lane (Raw/Clean) to generate it.",
    hint_transcript_generate_failed: "Failed to generate transcript. Check STT logs.",
    busy_overlay_title: "Please wait...",
    busy_overlay_cancel_btn: "Abort",
    busy_overlay_minimize_btn: "Minimize",
    busy_overlay_restore_btn: "Restore",
    busy_overlay_progress_label: "Progress",
    busy_overlay_cancelled: "Operation canceled by user.",
    busy_finish_title: "Building MP3",
    busy_finish_text:
      "Saving audio and preparing MP3. Text and reports are generated later on demand in Results.",
    busy_mp3_title: "Preparing MP3",
    busy_mp3_text: "Converting recording to MP3 and opening the save dialog.",
    busy_report_title: "Building transcript",
    busy_report_text:
      "Building TXT transcript from MP3 via STT (without LLM). Long recordings can take time.",
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
    quick_record_title: "Meeting link (browser capture)",
    quick_record_url_label: "Meeting URL",
    help_quick_url:
      "Meeting URL. On Start, app opens this URL and records selected tab with Share audio.",
    quick_record_url_placeholder: "https://...",
    quick_record_duration_label: "Duration (sec)",
    help_quick_duration:
      "Maximum quick-record duration. Recording auto-stops when limit is reached.",
    quick_record_start_btn: "Quick start",
    quick_record_stop_btn: "Quick stop",
    quick_record_state_idle: "Idle",
    quick_record_state_running: "Recording",
    quick_record_state_stopping: "Stopping",
    quick_record_state_completed: "Completed",
    quick_record_state_failed: "Failed",
    quick_record_hint_ready:
      "Press Start: meeting URL will open, then select meeting tab in browser capture and enable Share audio.",
    quick_record_hint_started: "Fallback recording started.",
    quick_record_hint_stopped: "Fallback recording stop requested.",
    quick_record_hint_missing_url: "Provide meeting URL (http/https).",
    quick_record_hint_missing_duration: "Provide valid duration (>= 5 sec).",
    quick_record_hint_already_running: "Quick recorder is already running.",
    quick_record_hint_start_failed: "Failed to start quick recorder.",
    quick_record_hint_stop_failed: "Failed to stop quick recorder.",
    quick_record_hint_running_probe_wait:
      "Recording is in progress. First signal check will be available in {seconds}s.",
    quick_record_hint_running_probe_ok: "Recording is in progress: signal detected ({peak}%). Device: {device}.",
    quick_record_hint_running_probe_fail:
      "Recording is running, but no signal was detected in the first 5s. Verify that meeting audio is actually playing on system output.",
    quick_record_hint_failed: "Quick recorder failed: {error}",
    quick_record_hint_completed: "Quick recording completed: {path}",
    quick_probe_failed: "Quick capture probe failed: {detail}",
    quick_probe_no_signal: "Quick capture probe: no signal detected. Device: {device}.",
    quick_probe_signal_ok: "Quick capture probe: signal detected ({peak}%). Device: {device}.",
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
      "Active recording is detected in another tab/window or stale session. Click “Claim capture in this window” and retry.",
    capture_claim_btn: "Claim capture in this window",
    capture_claim_running: "Releasing capture and finishing stale session...",
    capture_claim_success: "Capture control is moved to this window. You can start recording.",
    capture_claim_no_active: "No active sessions found. You can start recording.",
    capture_claim_failed: "Failed to claim capture control. Check local API and retry.",
    warn_system_level_low:
      "System audio level is very low. Check routing: meeting output must go to BlackHole/VB-CABLE/Monitor.",
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
  sttModelSelect: document.getElementById("sttModelSelect"),
  scanSttModels: document.getElementById("scanSttModels"),
  applySttModel: document.getElementById("applySttModel"),
  sttModelStatusText: document.getElementById("sttModelStatusText"),
  llmModelSelect: document.getElementById("llmModelSelect"),
  scanLlmModels: document.getElementById("scanLlmModels"),
  applyLlmModel: document.getElementById("applyLlmModel"),
  llmStatusText: document.getElementById("llmStatusText"),
  embeddingModelSelect: document.getElementById("embeddingModelSelect"),
  scanEmbeddingModels: document.getElementById("scanEmbeddingModels"),
  applyEmbeddingModel: document.getElementById("applyEmbeddingModel"),
  embeddingStatusText: document.getElementById("embeddingStatusText"),
  deviceSelect: document.getElementById("deviceSelect"),
  deviceStatusText: document.getElementById("deviceStatusText"),
  refreshDevices: document.getElementById("refreshDevices"),
  checkDriver: document.getElementById("checkDriver"),
  includeMic: document.getElementById("includeMic"),
  micSelect: document.getElementById("micSelect"),
  realtimeOnlySettings: document.getElementById("realtimeOnlySettings"),
  languageProfileSelect: document.getElementById("languageProfileSelect"),
  captureMethodChip: document.getElementById("captureMethodChip"),
  recordingModeHint: document.getElementById("recordingModeHint"),
  uploadModeHint: document.getElementById("uploadModeHint"),
  deviceModeBlock: document.getElementById("deviceModeBlock"),
  apiConnectBlock: document.getElementById("apiConnectBlock"),
  apiRecordUrl: document.getElementById("apiRecordUrl"),
  apiRecordDuration: document.getElementById("apiRecordDuration"),
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
  claimCaptureBtn: document.getElementById("claimCaptureBtn"),
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
  llmArtifactGenerateBtn: document.getElementById("llmArtifactGenerateBtn"),
  llmArtifactHint: document.getElementById("llmArtifactHint"),
  llmArtifactMeetingSelect: document.getElementById("llmArtifactMeetingSelect"),
  llmArtifactSourceSelect: document.getElementById("llmArtifactSourceSelect"),
  llmArtifactModeSelect: document.getElementById("llmArtifactModeSelect"),
  llmArtifactTemplateField: document.getElementById("llmArtifactTemplateField"),
  llmArtifactTemplateSelect: document.getElementById("llmArtifactTemplateSelect"),
  llmArtifactPromptInput: document.getElementById("llmArtifactPromptInput"),
  llmArtifactSchemaInput: document.getElementById("llmArtifactSchemaInput"),
  llmArtifactForceRebuild: document.getElementById("llmArtifactForceRebuild"),
  llmChatClearBtn: document.getElementById("llmChatClearBtn"),
  llmChatSendBtn: document.getElementById("llmChatSendBtn"),
  llmSourceModeFiles: document.getElementById("llmSourceModeFiles"),
  llmSourceModeRag: document.getElementById("llmSourceModeRag"),
  llmModeHint: document.getElementById("llmModeHint"),
  llmFilesModePanel: document.getElementById("llmFilesModePanel"),
  llmRagModePanel: document.getElementById("llmRagModePanel"),
  llmChatHint: document.getElementById("llmChatHint"),
  llmChatHistory: document.getElementById("llmChatHistory"),
  llmChatInput: document.getElementById("llmChatInput"),
  llmChatAttachBtn: document.getElementById("llmChatAttachBtn"),
  llmChatAttachInput: document.getElementById("llmChatAttachInput"),
  llmChatAttachments: document.getElementById("llmChatAttachments"),
  llmChatPresetSummary: document.getElementById("llmChatPresetSummary"),
  llmChatPresetTable: document.getElementById("llmChatPresetTable"),
  llmChatPresetJson: document.getElementById("llmChatPresetJson"),
  llmChatPresetCsv: document.getElementById("llmChatPresetCsv"),
  llmArtifactMetaBadge: document.getElementById("llmArtifactMetaBadge"),
  llmArtifactMetaText: document.getElementById("llmArtifactMetaText"),
  llmArtifactFiles: document.getElementById("llmArtifactFiles"),
  ragRefreshMeetingsBtn: document.getElementById("ragRefreshMeetingsBtn"),
  ragIndexSelectedBtn: document.getElementById("ragIndexSelectedBtn"),
  ragRunBtn: document.getElementById("ragRunBtn"),
  ragHint: document.getElementById("ragHint"),
  ragMeetingPicker: document.getElementById("ragMeetingPicker"),
  ragSelectCurrentBtn: document.getElementById("ragSelectCurrentBtn"),
  ragSelectAllBtn: document.getElementById("ragSelectAllBtn"),
  ragClearSelectionBtn: document.getElementById("ragClearSelectionBtn"),
  ragSavedSetSelect: document.getElementById("ragSavedSetSelect"),
  ragSaveSetBtn: document.getElementById("ragSaveSetBtn"),
  ragLoadSetBtn: document.getElementById("ragLoadSetBtn"),
  ragDeleteSetBtn: document.getElementById("ragDeleteSetBtn"),
  ragSourceSelect: document.getElementById("ragSourceSelect"),
  ragTopKInput: document.getElementById("ragTopKInput"),
  ragUseLlmAnswer: document.getElementById("ragUseLlmAnswer"),
  ragAutoIndex: document.getElementById("ragAutoIndex"),
  ragForceReindex: document.getElementById("ragForceReindex"),
  ragChatSendBtn: document.getElementById("ragChatSendBtn"),
  ragChatHint: document.getElementById("ragChatHint"),
  ragChatHistory: document.getElementById("ragChatHistory"),
  ragQueryInput: document.getElementById("ragQueryInput"),
  ragChatAttachBtn: document.getElementById("ragChatAttachBtn"),
  ragChatAttachInput: document.getElementById("ragChatAttachInput"),
  ragChatAttachments: document.getElementById("ragChatAttachments"),
  ragAnswerPromptInput: document.getElementById("ragAnswerPromptInput"),
  ragExportJsonBtn: document.getElementById("ragExportJsonBtn"),
  ragExportCsvBtn: document.getElementById("ragExportCsvBtn"),
  ragExportTxtBtn: document.getElementById("ragExportTxtBtn"),
  ragResultMeta: document.getElementById("ragResultMeta"),
  ragAnswerText: document.getElementById("ragAnswerText"),
  ragHitsList: document.getElementById("ragHitsList"),
  ragResultFiles: document.getElementById("ragResultFiles"),
  chooseFolder: document.getElementById("chooseFolder"),
  folderStatus: document.getElementById("folderStatus"),
  busyOverlay: document.getElementById("busyOverlay"),
  busyOverlayTitle: document.getElementById("busyOverlayTitle"),
  busyOverlayText: document.getElementById("busyOverlayText"),
  busyOverlayCancel: document.getElementById("busyOverlayCancel"),
  busyOverlayToggle: document.getElementById("busyOverlayToggle"),
  busyOverlayProgressFill: document.getElementById("busyOverlayProgressFill"),
  busyOverlayPercent: document.getElementById("busyOverlayPercent"),
  quickRecordUrl: document.getElementById("quickRecordUrl"),
  quickRecordDuration: document.getElementById("quickRecordDuration"),
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
  flowSteps: Array.from(document.querySelectorAll("[data-flow-step]")),
  resultTabButtons: Array.from(document.querySelectorAll("[data-results-tab]")),
  resultTabPanes: Array.from(document.querySelectorAll("[data-results-pane]")),
  modeSettingsPanels: Array.from(document.querySelectorAll("[data-mode-panel]")),
  workModeButtons: Array.from(document.querySelectorAll("[data-work-mode]")),
  captureModeInputs: Array.from(document.querySelectorAll('input[name="captureMode"]')),
  llmSourceModeButtons: Array.from(document.querySelectorAll("[data-llm-source-mode]")),
};

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
  return CHUNK_TIMESLICE_MS;
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
  renderSttStatus();
  renderLlmStatus();
  renderEmbeddingStatus();
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
  document.querySelectorAll(".lang-btn").forEach((btn) => {
    btn.classList.toggle("active", String(btn.dataset.lang || "") === state.lang);
  });
  _renderBusyOverlayToggle();
  _renderBusyOverlayCancel();
  _setBusyOverlayProgress(state.busyOverlayProgressPct || 0);
  syncLanguageProfileSelect();
  renderMeterDetailLabels();
  renderDiagnosticsLabels();
  if (els.sttModelSelect && !state.sttModels.length) {
    setSttModelOptions([], "");
  }
  if (els.llmModelSelect && !state.llmModels.length) {
    setLlmModelOptions([], "");
  }
  if (els.embeddingModelSelect && !state.embeddingModels.length) {
    setEmbeddingModelOptions([], "");
  }
  setQuickStatus(state.quickStatusKey || "quick_record_state_idle", state.quickStatusStyle || "muted");
  if (state.quickHintKey) {
    setQuickHint(state.quickHintKey, state.quickHintStyle || "muted", false);
  } else if (state.quickHintText) {
    setQuickHint(state.quickHintText, state.quickHintStyle || "muted", true);
  }
  applyWorkModeUi();
  setLlmSourceMode(state.llmSourceMode || "files");
  renderComparisonTable();
  if (Array.isArray(state.compareItems) && state.compareItems.length) {
    setCompareHint("compare_hint_idle", "good");
  } else {
    setCompareHint("compare_hint_empty", "muted");
  }
  renderLlmArtifactWorkspace();
  renderRagWorkspace();
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
  if (style === "bad") {
    logUiEvent(
      "status_hint_bad",
      {
        hint_key: state.statusHintKey || "",
        hint_text: state.statusHintText || "",
        capture_mode: getCaptureMode(),
        chunk_count: Number(state.chunkCount || 0),
        levels: {
          mixed: Number(state.meterLevels.mixed || 0),
          system: Number(state.meterLevels.system || 0),
          mic: Number(state.meterLevels.mic || 0),
        },
      },
      "warning",
      { throttleKey: `status_bad:${state.statusHintKey || state.statusHintText}`, throttleMs: 1800 }
    );
  }
  refreshRecognitionDiagnosis();
};

const resolveUiText = (keyOrText = "", isRaw = false) => {
  if (!keyOrText) return "";
  const dict = i18n[state.lang] || {};
  if (!isRaw && dict[keyOrText]) return String(dict[keyOrText]);
  return String(keyOrText || "");
};

const _busyOverlayProgressLabel = () =>
  resolveUiText("busy_overlay_progress_label") || "Progress";

const _busyOverlayDurationMs = (titleKeyOrText = "", overrideMs = null) => {
  if (Number.isFinite(Number(overrideMs)) && Number(overrideMs) > 0) {
    return Math.max(5000, Number(overrideMs));
  }
  const key = String(titleKeyOrText || "").trim();
  const mapped = Number(BUSY_PROGRESS_DURATION_BY_TITLE[key] || 0);
  if (mapped > 0) return mapped;
  return 45000;
};

const _setBusyOverlayProgress = (progressPct) => {
  const normalized = Math.max(0, Math.min(100, Math.round(Number(progressPct) || 0)));
  state.busyOverlayProgressPct = normalized;
  if (els.busyOverlayProgressFill) {
    els.busyOverlayProgressFill.style.width = `${normalized}%`;
  }
  if (els.busyOverlayPercent) {
    els.busyOverlayPercent.textContent = `${_busyOverlayProgressLabel()}: ${normalized}%`;
  }
};

const _renderBusyOverlayToggle = () => {
  if (!els.busyOverlayToggle) return;
  const key = state.busyOverlayMinimized ? "busy_overlay_restore_btn" : "busy_overlay_minimize_btn";
  const fallback = state.busyOverlayMinimized ? "Restore" : "Minimize";
  els.busyOverlayToggle.textContent = resolveUiText(key) || fallback;
};

const _renderBusyOverlayCancel = () => {
  if (!els.busyOverlayCancel) return;
  const visible = Boolean(state.busyOverlayCancelable && state.busyOverlayCount > 0);
  els.busyOverlayCancel.classList.toggle("hidden", !visible);
  els.busyOverlayCancel.disabled = !visible;
  if (visible) {
    els.busyOverlayCancel.textContent = resolveUiText("busy_overlay_cancel_btn") || "Abort";
  }
};

const _applyBusyOverlayMinimized = () => {
  if (!els.busyOverlay) return;
  els.busyOverlay.classList.toggle("minimized", Boolean(state.busyOverlayMinimized));
  _renderBusyOverlayToggle();
  _renderBusyOverlayCancel();
};

const _stopBusyOverlayTimer = () => {
  if (state.busyOverlayTimer) {
    clearInterval(state.busyOverlayTimer);
    state.busyOverlayTimer = null;
  }
};

const _tickBusyOverlayProgress = () => {
  if (!els.busyOverlay || state.busyOverlayCount <= 0) return;
  if (typeof state.busyOverlayManualProgress === "number") {
    _setBusyOverlayProgress(Math.max(state.busyOverlayProgressPct, state.busyOverlayManualProgress));
    return;
  }
  const elapsed = Math.max(0, Date.now() - Number(state.busyOverlayStartedAtMs || Date.now()));
  const duration = Math.max(5000, Number(state.busyOverlayDurationMs || 45000));
  const ratio = Math.min(1, elapsed / duration);
  const eased = 1 - Math.pow(1 - ratio, 2.2);
  const target = Math.min(97, Math.round(4 + eased * 93));
  _setBusyOverlayProgress(Math.max(state.busyOverlayProgressPct, target));
};

const updateBusyOverlayProgress = (progressPct, textKeyOrText = "", options = {}) => {
  if (!els.busyOverlay || state.busyOverlayCount <= 0) return;
  const { rawText = false } = options || {};
  if (textKeyOrText && els.busyOverlayText) {
    const text = resolveUiText(textKeyOrText, rawText);
    if (text) {
      els.busyOverlayText.textContent = text;
    }
  }
  if (Number.isFinite(Number(progressPct))) {
    const normalized = Math.max(0, Math.min(100, Number(progressPct)));
    state.busyOverlayManualProgress = normalized;
    _setBusyOverlayProgress(Math.max(state.busyOverlayProgressPct, normalized));
  }
};

const toggleBusyOverlayMinimized = () => {
  if (!els.busyOverlay || state.busyOverlayCount <= 0) return;
  state.busyOverlayMinimized = !state.busyOverlayMinimized;
  _applyBusyOverlayMinimized();
};

const getBusyOverlayAbortSignal = () => {
  const ctrl = state.busyOverlayAbortController;
  if (!ctrl || !ctrl.signal) return null;
  return ctrl.signal;
};

const cancelBusyOverlayOperation = () => {
  if (!state.busyOverlayCancelable) return;
  state.busyOverlayCancelledByUser = true;
  const ctrl = state.busyOverlayAbortController;
  if (ctrl && ctrl.signal && !ctrl.signal.aborted) {
    ctrl.abort();
  }
  setStatusHint(state.busyOverlayCancelHintKey || "busy_overlay_cancelled", "muted");
  hideBusyOverlay();
};

const showBusyOverlay = (titleKeyOrText = "busy_overlay_title", textKeyOrText = "", options = {}) => {
  if (!els.busyOverlay) return;
  const {
    rawTitle = false,
    rawText = false,
    durationMs = null,
    cancelable = false,
    cancelHintKey = "busy_overlay_cancelled",
    abortController = null,
  } = options || {};
  const isFirstOpen = Number(state.busyOverlayCount || 0) <= 0;
  state.busyOverlayCount = Number(state.busyOverlayCount || 0) + 1;
  const title = resolveUiText(titleKeyOrText, rawTitle) || resolveUiText("busy_overlay_title");
  const text = resolveUiText(textKeyOrText, rawText);
  if (els.busyOverlayTitle) {
    els.busyOverlayTitle.textContent = title;
  }
  if (els.busyOverlayText) {
    els.busyOverlayText.textContent = text || title;
  }
  if (isFirstOpen) {
    state.busyOverlayProgressPct = 0;
    state.busyOverlayManualProgress = null;
    state.busyOverlayStartedAtMs = Date.now();
    state.busyOverlayDurationMs = _busyOverlayDurationMs(titleKeyOrText, durationMs);
    state.busyOverlayMinimized = false;
    state.busyOverlayCancelHintKey = String(cancelHintKey || "busy_overlay_cancelled");
    state.busyOverlayCancelledByUser = false;
    state.busyOverlayCancelable = Boolean(cancelable);
    const hasCustomAbortController = abortController && typeof abortController.abort === "function" && abortController.signal;
    const hasNativeAbortController = typeof AbortController === "function";
    state.busyOverlayAbortController = state.busyOverlayCancelable
      ? (hasCustomAbortController ? abortController : hasNativeAbortController ? new AbortController() : null)
      : null;
    if (state.busyOverlayCancelable && !state.busyOverlayAbortController) {
      state.busyOverlayCancelable = false;
    }
    _setBusyOverlayProgress(3);
    _stopBusyOverlayTimer();
    state.busyOverlayTimer = setInterval(_tickBusyOverlayProgress, 420);
  }
  _applyBusyOverlayMinimized();
  els.busyOverlay.classList.remove("hidden");
  els.busyOverlay.setAttribute("aria-hidden", "false");
  _renderBusyOverlayCancel();
  return getBusyOverlayAbortSignal();
};

const hideBusyOverlay = () => {
  if (!els.busyOverlay) return;
  state.busyOverlayCount = Math.max(0, Number(state.busyOverlayCount || 0) - 1);
  if (state.busyOverlayCount > 0) return;
  _stopBusyOverlayTimer();
  state.busyOverlayProgressPct = 0;
  state.busyOverlayManualProgress = null;
  state.busyOverlayStartedAtMs = 0;
  state.busyOverlayDurationMs = 45000;
  state.busyOverlayMinimized = false;
  state.busyOverlayCancelable = false;
  state.busyOverlayCancelHintKey = "busy_overlay_cancelled";
  state.busyOverlayAbortController = null;
  state.busyOverlayCancelledByUser = false;
  _setBusyOverlayProgress(0);
  _applyBusyOverlayMinimized();
  _renderBusyOverlayCancel();
  els.busyOverlay.classList.add("hidden");
  els.busyOverlay.setAttribute("aria-hidden", "true");
};

const showQuickStopOverlay = () => {
  if (state.quickStopOverlayVisible) return;
  state.quickStopOverlayVisible = true;
  showBusyOverlay("busy_finish_title", "busy_finish_text");
};

const hideQuickStopOverlay = () => {
  if (!state.quickStopOverlayVisible) return;
  state.quickStopOverlayVisible = false;
  hideBusyOverlay();
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
  const modeCfg = getWorkModeConfig();
  if (!modeCfg.supportsRealtime) {
    if (modeCfg.supportsQuick) {
      return { key: "work_mode_quick_no_realtime_diag", style: "muted" };
    }
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
  if (els.driverStatus) {
    els.driverStatus.textContent = dict[statusKey] || statusKey;
    els.driverStatus.className = `pill ${style || "muted"}`;
  }
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
  if (!els.compareHint && !els.compareTableBody) {
    return;
  }
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

const setLlmArtifactHint = (hintKeyOrText = "", style = "muted", isRaw = false, params = {}) => {
  if (!els.llmArtifactHint) return;
  const dict = i18n[state.lang] || {};
  let text = "";
  if (!hintKeyOrText) {
    text = "";
    state.llmArtifact.hintKey = "";
    state.llmArtifact.hintText = "";
    state.llmArtifact.hintStyle = "muted";
  } else if (!isRaw && dict[hintKeyOrText]) {
    text = formatText(dict[hintKeyOrText], params || {});
    state.llmArtifact.hintKey = hintKeyOrText;
    state.llmArtifact.hintText = "";
    state.llmArtifact.hintStyle = style || "muted";
  } else {
    text = String(hintKeyOrText || "");
    state.llmArtifact.hintKey = "";
    state.llmArtifact.hintText = text;
    state.llmArtifact.hintStyle = style || "muted";
  }
  els.llmArtifactHint.textContent = text;
  els.llmArtifactHint.className = `hint ${style || "muted"}`;
};

const setLlmChatHint = (hintKeyOrText = "", style = "muted", isRaw = false, params = {}) => {
  if (!els.llmChatHint) return;
  const dict = i18n[state.lang] || {};
  let text = "";
  if (!hintKeyOrText) {
    text = "";
    state.llmArtifact.chatHintKey = "";
    state.llmArtifact.chatHintText = "";
    state.llmArtifact.chatHintStyle = "muted";
  } else if (!isRaw && dict[hintKeyOrText]) {
    text = formatText(dict[hintKeyOrText], params || {});
    state.llmArtifact.chatHintKey = hintKeyOrText;
    state.llmArtifact.chatHintText = "";
    state.llmArtifact.chatHintStyle = style || "muted";
  } else {
    text = String(hintKeyOrText || "");
    state.llmArtifact.chatHintKey = "";
    state.llmArtifact.chatHintText = text;
    state.llmArtifact.chatHintStyle = style || "muted";
  }
  els.llmChatHint.textContent = text;
  els.llmChatHint.className = `hint ${style || "muted"}`;
};

const setRagChatHint = (hintKeyOrText = "", style = "muted", isRaw = false, params = {}) => {
  if (!els.ragChatHint) return;
  const dict = i18n[state.lang] || {};
  let text = "";
  if (!hintKeyOrText) {
    text = "";
    state.rag.chatHintKey = "";
    state.rag.chatHintText = "";
    state.rag.chatHintStyle = "muted";
  } else if (!isRaw && dict[hintKeyOrText]) {
    text = formatText(dict[hintKeyOrText], params || {});
    state.rag.chatHintKey = hintKeyOrText;
    state.rag.chatHintText = "";
    state.rag.chatHintStyle = style || "muted";
  } else {
    text = String(hintKeyOrText || "");
    state.rag.chatHintKey = "";
    state.rag.chatHintText = text;
    state.rag.chatHintStyle = style || "muted";
  }
  els.ragChatHint.textContent = text;
  els.ragChatHint.className = `hint ${style || "muted"}`;
};

const _normalizeLlmSourceMode = (mode) => {
  const raw = String(mode || "").trim().toLowerCase();
  return raw === "rag" ? "rag" : "files";
};

const setLlmSourceMode = (mode) => {
  const dict = i18n[state.lang] || {};
  const normalized = _normalizeLlmSourceMode(mode || state.llmSourceMode || "files");
  state.llmSourceMode = normalized;
  (els.llmSourceModeButtons || []).forEach((btn) => {
    if (!btn || !btn.dataset) return;
    const btnMode = _normalizeLlmSourceMode(btn.dataset.llmSourceMode || "");
    btn.classList.toggle("active", btnMode === normalized);
  });
  if (els.llmFilesModePanel) {
    const isActive = normalized === "files";
    els.llmFilesModePanel.classList.toggle("active", isActive);
    els.llmFilesModePanel.classList.toggle("hidden", !isActive);
  }
  if (els.llmRagModePanel) {
    const isActive = normalized === "rag";
    els.llmRagModePanel.classList.toggle("active", isActive);
    els.llmRagModePanel.classList.toggle("hidden", !isActive);
  }
  if (els.llmModeHint) {
    const key = normalized === "rag" ? "llm_mode_hint_rag" : "llm_mode_hint_files";
    const text = String(dict[key] || "");
    els.llmModeHint.textContent = text;
    els.llmModeHint.className = "hint muted";
  }
};

const _attachmentFilesFromInput = (inputEl) =>
  Array.from((inputEl && inputEl.files) || [])
    .filter(Boolean)
    .slice(0, 8);

const _attachmentIsTextLike = (file) => {
  const name = String((file && file.name) || "").toLowerCase();
  const type = String((file && file.type) || "").toLowerCase();
  if (type.startsWith("text/")) return true;
  if (type.includes("json") || type.includes("xml") || type.includes("yaml") || type.includes("csv")) return true;
  return /\.(txt|md|markdown|json|csv|tsv|log|xml|yaml|yml|html|htm|js|ts|jsx|tsx|py|java|go|sql|ini|cfg|conf)$/i.test(
    name
  );
};

const _attachmentContextBlock = async (files = []) => {
  const list = Array.isArray(files) ? files.filter(Boolean).slice(0, 8) : [];
  if (!list.length) return "";
  const ru = state.lang === "ru";
  const lines = [];
  lines.push(ru ? "Дополнительные вложения пользователя:" : "Additional user attachments:");

  const maxPerFileChars = 3500;
  const maxTotalChars = 12000;
  let consumed = 0;

  for (const file of list) {
    const name = String(file && file.name ? file.name : "file");
    const size = Number(file && file.size ? file.size : 0);
    const type = String(file && file.type ? file.type : "");
    lines.push(`- ${name} (${_formatBytes(size)}${type ? `, ${type}` : ""})`);
    if (!_attachmentIsTextLike(file)) continue;
    if (consumed >= maxTotalChars) continue;
    try {
      const rawText = await file.text();
      const remained = Math.max(0, maxTotalChars - consumed);
      const localLimit = Math.max(0, Math.min(maxPerFileChars, remained));
      const text = String(rawText || "").trim();
      if (!text || !localLimit) continue;
      const clipped = text.length > localLimit ? `${text.slice(0, localLimit)}\n…` : text;
      lines.push(`\n[${name}]`);
      lines.push(clipped);
      consumed += clipped.length;
    } catch (err) {
      // ignore unreadable files
    }
  }
  return lines.join("\n");
};

const renderLlmChatAttachments = () => {
  if (!els.llmChatAttachments) return;
  const dict = i18n[state.lang] || {};
  const files = Array.isArray(state.llmArtifact.chatAttachments) ? state.llmArtifact.chatAttachments : [];
  els.llmChatAttachments.innerHTML = "";
  if (!files.length) {
    const pill = document.createElement("span");
    pill.className = "chat-attachment-pill";
    pill.textContent = dict.chat_attach_none || "No files selected";
    els.llmChatAttachments.appendChild(pill);
    return;
  }
  const count = document.createElement("span");
  count.className = "chat-attachment-pill";
  count.textContent = formatText(dict.chat_attach_selected || "Files: {count}", { count: files.length });
  els.llmChatAttachments.appendChild(count);
  files.forEach((file) => {
    const pill = document.createElement("span");
    pill.className = "chat-attachment-pill";
    const name = String((file && file.name) || "file");
    pill.textContent = `${name} (${_formatBytes(file && file.size ? file.size : 0)})`;
    els.llmChatAttachments.appendChild(pill);
  });
};

const renderRagChatAttachments = () => {
  if (!els.ragChatAttachments) return;
  const dict = i18n[state.lang] || {};
  const files = Array.isArray(state.rag.chatAttachments) ? state.rag.chatAttachments : [];
  els.ragChatAttachments.innerHTML = "";
  if (!files.length) {
    const pill = document.createElement("span");
    pill.className = "chat-attachment-pill";
    pill.textContent = dict.chat_attach_none || "No files selected";
    els.ragChatAttachments.appendChild(pill);
    return;
  }
  const count = document.createElement("span");
  count.className = "chat-attachment-pill";
  count.textContent = formatText(dict.chat_attach_selected || "Files: {count}", { count: files.length });
  els.ragChatAttachments.appendChild(count);
  files.forEach((file) => {
    const pill = document.createElement("span");
    pill.className = "chat-attachment-pill";
    const name = String((file && file.name) || "file");
    pill.textContent = `${name} (${_formatBytes(file && file.size ? file.size : 0)})`;
    els.ragChatAttachments.appendChild(pill);
  });
};

const _llmArtifactMeetingId = () => {
  return LLM_FILES_WORKSPACE_ID;
};

const _llmArtifactSource = () => {
  const raw = String(
    (els.llmArtifactSourceSelect && els.llmArtifactSourceSelect.value) || state.llmArtifact.transcriptSource || "clean"
  )
    .trim()
    .toLowerCase();
  if (raw === "raw" || raw === "normalized") return raw;
  return "clean";
};

const _llmArtifactMode = () => {
  const raw = String((els.llmArtifactModeSelect && els.llmArtifactModeSelect.value) || state.llmArtifact.mode || "template")
    .trim()
    .toLowerCase();
  if (raw === "custom" || raw === "table") return raw;
  return "template";
};

const _syncLlmArtifactControlsToState = () => {
  state.llmArtifact.meetingId = _llmArtifactMeetingId();
  state.llmArtifact.transcriptSource = _llmArtifactSource();
  state.llmArtifact.mode = _llmArtifactMode();
  state.llmArtifact.templateId = String(
    (els.llmArtifactTemplateSelect && els.llmArtifactTemplateSelect.value) || state.llmArtifact.templateId || "analysis"
  ).trim() || "analysis";
  state.llmArtifact.forceRebuild = Boolean(els.llmArtifactForceRebuild && els.llmArtifactForceRebuild.checked);
};

const _parseLlmArtifactSchema = () => {
  const raw = String((els.llmArtifactSchemaInput && els.llmArtifactSchemaInput.value) || "").trim();
  if (!raw) return { ok: true, value: null };
  try {
    return { ok: true, value: JSON.parse(raw) };
  } catch (err) {
    return { ok: false, value: null, error: err };
  }
};

const _formatBytes = (value) => {
  const n = Number(value || 0);
  if (!Number.isFinite(n) || n <= 0) return "0 B";
  if (n < 1024) return `${Math.round(n)} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
};

const _llmArtifactSuggestedFilename = ({ meetingId, fmt, response, fileRef }) => {
  const meta = state.recordsMeta.get(String(meetingId || "").trim()) || {};
  const isFilesWorkspace = String(meetingId || "").trim() === LLM_FILES_WORKSPACE_ID;
  const label = sanitizeFilenamePart(isFilesWorkspace ? "llm_files" : meta.display_name || meetingId || "record");
  const ext = String(fmt || "").trim().toLowerCase() || "txt";
  const source = String((response && response.transcript_variant) || state.llmArtifact.transcriptSource || "clean");
  const mode = String((response && response.mode) || state.llmArtifact.mode || "template");
  const template = String((response && response.template_id) || "").trim() || String((response && response.result_kind) || mode);
  const artifactId = String((response && response.artifact_id) || "").trim().slice(0, 10);
  const base = `${label}__${template || mode}_${source}${artifactId ? `_${artifactId}` : ""}`;
  if (fileRef && String(fileRef.filename || "").trim()) {
    const original = String(fileRef.filename).trim();
    if (original.includes(".")) {
      return normalizeFilenameWithExt(base, base, original.split(".").pop() || ext);
    }
  }
  return normalizeFilenameWithExt(base, base, ext);
};

const _llmChatPushMessage = ({ role = "assistant", text = "", meta = "" } = {}) => {
  const normalizedRole = String(role || "").trim().toLowerCase() === "user" ? "user" : "assistant";
  const normalizedText = String(text || "").trim();
  if (!normalizedText) return;
  if (!Array.isArray(state.llmArtifact.chatMessages)) {
    state.llmArtifact.chatMessages = [];
  }
  state.llmArtifact.chatMessages.push({
    role: normalizedRole,
    text: normalizedText,
    meta: String(meta || "").trim(),
    ts: Date.now(),
  });
  if (state.llmArtifact.chatMessages.length > 30) {
    state.llmArtifact.chatMessages = state.llmArtifact.chatMessages.slice(-30);
  }
};

const _llmChatInferMode = (prompt) => {
  const raw = String(prompt || "").toLowerCase();
  if (
    /(таблиц|table|csv|sheet|sheets|excel|column|columns|rows|строк|колонк|google)/.test(raw)
  ) {
    return "table";
  }
  return "custom";
};

const _llmChatPresetPrompt = (presetId) => {
  const dict = i18n[state.lang] || {};
  const keyByPreset = {
    summary: "llm_chat_preset_summary_prompt",
    table: "llm_chat_preset_table_prompt",
    json: "llm_chat_preset_json_prompt",
    csv: "llm_chat_preset_csv_prompt",
  };
  const key = keyByPreset[String(presetId || "").trim().toLowerCase()];
  if (!key) return "";
  return String(dict[key] || "").trim();
};

const _llmArtifactFindFileByFmt = (artifactResponse, fmt) => {
  const targetFmt = String(fmt || "").trim().toLowerCase();
  if (!targetFmt) return null;
  const files = artifactResponse && Array.isArray(artifactResponse.files) ? artifactResponse.files : [];
  return (
    files.find((item) => String(item && item.fmt ? item.fmt : "").trim().toLowerCase() === targetFmt) || null
  );
};

const _llmArtifactFetchPreviewText = async ({ meetingId, artifactResponse }) => {
  const artifactId = String((artifactResponse && artifactResponse.artifact_id) || "").trim();
  if (!meetingId || !artifactId) return "";
  const preferredFmts = ["txt", "json", "csv"];
  const fallback = artifactResponse && Array.isArray(artifactResponse.files) ? artifactResponse.files[0] : null;
  const picked =
    preferredFmts
      .map((fmt) => _llmArtifactFindFileByFmt(artifactResponse, fmt))
      .find((item) => Boolean(item)) || fallback;
  const fmt = String((picked && picked.fmt) || "").trim().toLowerCase();
  if (!fmt) return "";
  const res = await fetch(
    `/v1/meetings/${encodeURIComponent(meetingId)}/artifacts/${encodeURIComponent(artifactId)}/download?fmt=${encodeURIComponent(fmt)}`,
    {
      headers: buildHeaders(),
    }
  );
  if (!res.ok) {
    throw new Error(`llm_artifact_preview_failed_${res.status}`);
  }
  const raw = await res.text();
  let preview = String(raw || "").trim();
  if (!preview) return "";
  if (fmt === "json") {
    try {
      preview = JSON.stringify(JSON.parse(preview), null, 2);
    } catch (err) {
      // keep raw if not valid JSON text
    }
  }
  const limit = 8000;
  if (preview.length > limit) {
    preview = `${preview.slice(0, limit)}\n\n…`;
  }
  return preview;
};

const renderLlmChatHistory = () => {
  if (!els.llmChatHistory) return;
  const dict = i18n[state.lang] || {};
  const messages = Array.isArray(state.llmArtifact.chatMessages) ? state.llmArtifact.chatMessages : [];
  els.llmChatHistory.innerHTML = "";
  if (!messages.length) {
    const empty = document.createElement("div");
    empty.className = "llm-chat-empty";
    empty.textContent = dict.llm_chat_history_empty || "LLM chat history will appear here.";
    els.llmChatHistory.appendChild(empty);
  } else {
    messages.forEach((msg) => {
      const card = document.createElement("div");
      card.className = `llm-chat-msg ${msg.role === "user" ? "user" : "assistant"}`;

      const head = document.createElement("div");
      head.className = "llm-chat-msg-head";
      const role = document.createElement("span");
      role.className = "llm-chat-msg-role";
      role.textContent =
        msg.role === "user"
          ? dict.llm_chat_role_user || "You"
          : dict.llm_chat_role_assistant || "LLM";
      head.appendChild(role);

      const right = document.createElement("span");
      const parts = [];
      if (Number.isFinite(Number(msg.ts))) {
        try {
          parts.push(new Date(Number(msg.ts)).toLocaleTimeString());
        } catch (err) {
          // ignore time formatting issues
        }
      }
      if (msg.meta) parts.push(String(msg.meta));
      right.textContent = parts.join(" • ");
      head.appendChild(right);
      card.appendChild(head);

      const body = document.createElement("pre");
      body.className = "llm-chat-msg-body";
      body.textContent = String(msg.text || "");
      card.appendChild(body);
      els.llmChatHistory.appendChild(card);
    });
  }
  els.llmChatHistory.scrollTop = els.llmChatHistory.scrollHeight;

  if (els.llmChatSendBtn) {
    els.llmChatSendBtn.disabled = Boolean(state.llmArtifact.busy);
  }
  if (els.llmChatClearBtn) {
    els.llmChatClearBtn.disabled = Boolean(state.llmArtifact.busy);
  }
  if (state.llmArtifact.chatHintKey) {
    setLlmChatHint(state.llmArtifact.chatHintKey, state.llmArtifact.chatHintStyle || "muted", false);
  } else if (state.llmArtifact.chatHintText) {
    setLlmChatHint(state.llmArtifact.chatHintText, state.llmArtifact.chatHintStyle || "muted", true);
  } else {
    setLlmChatHint("llm_chat_hint_idle", "muted");
  }
  renderLlmChatAttachments();
};

const _ragChatPushMessage = ({ role = "assistant", text = "", meta = "" } = {}) => {
  const normalizedRole = String(role || "").trim().toLowerCase() === "user" ? "user" : "assistant";
  const normalizedText = String(text || "").trim();
  if (!normalizedText) return;
  if (!Array.isArray(state.rag.chatMessages)) {
    state.rag.chatMessages = [];
  }
  state.rag.chatMessages.push({
    role: normalizedRole,
    text: normalizedText,
    meta: String(meta || "").trim(),
    ts: Date.now(),
  });
  if (state.rag.chatMessages.length > 30) {
    state.rag.chatMessages = state.rag.chatMessages.slice(-30);
  }
};

const renderRagChatHistory = () => {
  if (!els.ragChatHistory) return;
  const dict = i18n[state.lang] || {};
  const messages = Array.isArray(state.rag.chatMessages) ? state.rag.chatMessages : [];
  els.ragChatHistory.innerHTML = "";
  if (!messages.length) {
    const empty = document.createElement("div");
    empty.className = "llm-chat-empty";
    empty.textContent = dict.rag_chat_history_empty || "RAG chat history will appear here.";
    els.ragChatHistory.appendChild(empty);
  } else {
    messages.forEach((msg) => {
      const card = document.createElement("div");
      card.className = `llm-chat-msg ${msg.role === "user" ? "user" : "assistant"}`;

      const head = document.createElement("div");
      head.className = "llm-chat-msg-head";
      const role = document.createElement("span");
      role.className = "llm-chat-msg-role";
      role.textContent =
        msg.role === "user"
          ? dict.rag_chat_role_user || dict.llm_chat_role_user || "You"
          : dict.rag_chat_role_assistant || "RAG";
      head.appendChild(role);

      const right = document.createElement("span");
      const parts = [];
      if (Number.isFinite(Number(msg.ts))) {
        try {
          parts.push(new Date(Number(msg.ts)).toLocaleTimeString());
        } catch (err) {
          // ignore time formatting issues
        }
      }
      if (msg.meta) parts.push(String(msg.meta));
      right.textContent = parts.join(" • ");
      head.appendChild(right);
      card.appendChild(head);

      const body = document.createElement("pre");
      body.className = "llm-chat-msg-body";
      body.textContent = String(msg.text || "");
      card.appendChild(body);
      els.ragChatHistory.appendChild(card);
    });
  }
  els.ragChatHistory.scrollTop = els.ragChatHistory.scrollHeight;
  if (els.ragChatSendBtn) {
    els.ragChatSendBtn.disabled = Boolean(state.rag.queryBusy || state.rag.indexBusy);
  }
  if (state.rag.chatHintKey) {
    setRagChatHint(state.rag.chatHintKey, state.rag.chatHintStyle || "muted", false);
  } else if (state.rag.chatHintText) {
    setRagChatHint(state.rag.chatHintText, state.rag.chatHintStyle || "muted", true);
  } else {
    setRagChatHint("rag_chat_hint_idle", "muted");
  }
  renderRagChatAttachments();
};

const _applyLlmChatPreset = (presetId) => {
  setResultsTab("llm", { setFlow: true });
  setLlmSourceMode("files");
  const prompt = _llmChatPresetPrompt(presetId);
  if (!prompt || !els.llmChatInput) return;
  els.llmChatInput.value = prompt;
  if (els.llmArtifactSourceSelect) {
    els.llmArtifactSourceSelect.value = "clean";
  }
  state.llmArtifact.transcriptSource = "clean";
  _syncLlmArtifactControlsToState();
  renderLlmArtifactWorkspace();
  els.llmChatInput.focus();
};

const renderLlmArtifactWorkspace = () => {
  _syncLlmArtifactControlsToState();
  const dict = i18n[state.lang] || {};
  const items = Array.from(state.recordsMeta.values());
  const current = String(getSelectedMeeting() || "").trim();

  if (els.llmArtifactMeetingSelect) {
    const prevMeeting = String(state.llmArtifact.meetingId || "").trim();
    els.llmArtifactMeetingSelect.innerHTML = "";
    if (!items.length) {
      const opt = document.createElement("option");
      opt.value = "";
      opt.textContent = dict.report_picker_empty || "No records";
      els.llmArtifactMeetingSelect.appendChild(opt);
      state.llmArtifact.meetingId = "";
    } else {
      items.forEach((meta) => {
        const meetingId = String(meta.meeting_id || "").trim();
        const opt = document.createElement("option");
        opt.value = meetingId;
        opt.textContent = formatMeetingOptionLabel(meta);
        els.llmArtifactMeetingSelect.appendChild(opt);
      });
      const preferred = [prevMeeting, current, String(items[0].meeting_id || "").trim()].find(
        (id) => id && items.some((item) => String(item.meeting_id || "") === id)
      );
      els.llmArtifactMeetingSelect.value = String(preferred || "");
      state.llmArtifact.meetingId = String(els.llmArtifactMeetingSelect.value || "");
    }
  } else {
    state.llmArtifact.meetingId = _llmArtifactMeetingId();
  }

  if (els.llmArtifactSourceSelect) {
    els.llmArtifactSourceSelect.value = state.llmArtifact.transcriptSource || "clean";
  }
  if (els.llmArtifactModeSelect) {
    els.llmArtifactModeSelect.value = state.llmArtifact.mode || "template";
  }
  if (els.llmArtifactTemplateSelect) {
    const tpl = String(state.llmArtifact.templateId || "analysis");
    if (Array.from(els.llmArtifactTemplateSelect.options || []).some((o) => String(o.value || "") === tpl)) {
      els.llmArtifactTemplateSelect.value = tpl;
    }
  }
  if (els.llmArtifactForceRebuild) {
    els.llmArtifactForceRebuild.checked = Boolean(state.llmArtifact.forceRebuild);
  }
  const mode = _llmArtifactMode();
  if (els.llmArtifactTemplateField) {
    els.llmArtifactTemplateField.classList.toggle("hidden", mode !== "template");
  }

  const resp = state.llmArtifact.lastResponse && typeof state.llmArtifact.lastResponse === "object"
    ? state.llmArtifact.lastResponse
    : null;

  if (els.llmArtifactMetaBadge) {
    if (!resp) {
      els.llmArtifactMetaBadge.textContent = dict.llm_artifact_result_none || "No artifact";
      els.llmArtifactMetaBadge.className = "pill muted";
    } else {
      const rid = String(resp.artifact_id || "").trim();
      const shortId = rid ? rid.slice(0, 10) : "artifact";
      const filesCount = Array.isArray(resp.files) ? resp.files.length : 0;
      els.llmArtifactMetaBadge.textContent = `${shortId} • files=${filesCount}`;
      els.llmArtifactMetaBadge.className = `pill ${resp.cached ? "muted" : "good"}`;
    }
  }

  if (els.llmArtifactMetaText) {
    if (!resp) {
      els.llmArtifactMetaText.textContent = "";
    } else {
      const template = formatText(dict.llm_artifact_meta_template || "", {
        artifact_id: String(resp.artifact_id || ""),
        mode: String(resp.mode || ""),
        template: String(resp.template_id || "—"),
        source: String(resp.transcript_variant || ""),
        kind: String(resp.result_kind || ""),
        status: String(resp.status || ""),
        created_at: String(resp.created_at || ""),
        chars: Number(resp.transcript_chars || 0),
        cached: Boolean(resp.cached),
      });
      els.llmArtifactMetaText.textContent = template || JSON.stringify(resp, null, 2);
    }
  }

  if (els.llmArtifactFiles) {
    els.llmArtifactFiles.innerHTML = "";
    const files = resp && Array.isArray(resp.files) ? resp.files : [];
    if (!files.length) {
      const empty = document.createElement("div");
      empty.className = "rag-hit-empty";
      empty.textContent = dict.llm_artifact_result_none || "No artifact yet";
      els.llmArtifactFiles.appendChild(empty);
    } else {
      files.forEach((fileRef) => {
        const fmt = String(fileRef && fileRef.fmt ? fileRef.fmt : "").trim().toLowerCase();
        if (!fmt) return;
        const btn = document.createElement("button");
        btn.className = "ghost llm-artifact-file-btn";
        const label = formatText(dict.llm_artifact_file_download || "Download {fmt}", { fmt: fmt.toUpperCase() });
        btn.textContent = `${label} (${_formatBytes(fileRef.bytes)})`;
        btn.addEventListener("click", () => {
          void downloadLlmArtifactFile(fmt, fileRef);
        });
        els.llmArtifactFiles.appendChild(btn);
      });
    }
  }

  const busy = Boolean(state.llmArtifact.busy);
  if (els.llmArtifactGenerateBtn) {
    els.llmArtifactGenerateBtn.disabled = busy;
  }
  renderLlmChatHistory();
  if (state.llmArtifact.hintKey) {
    setLlmArtifactHint(state.llmArtifact.hintKey, state.llmArtifact.hintStyle || "muted", false);
  } else if (state.llmArtifact.hintText) {
    setLlmArtifactHint(state.llmArtifact.hintText, state.llmArtifact.hintStyle || "muted", true);
  } else {
    setLlmArtifactHint("llm_artifact_hint_idle", "muted");
  }
};

const generateLlmArtifact = async () => {
  _syncLlmArtifactControlsToState();
  const meetingId = String(state.llmArtifact.meetingId || "").trim();
  if (!meetingId) {
    setLlmArtifactHint("llm_artifact_hint_no_meeting", "bad");
    return;
  }
  const mode = _llmArtifactMode();
  const prompt = String((els.llmArtifactPromptInput && els.llmArtifactPromptInput.value) || "").trim();
  if ((mode === "custom" || mode === "table") && !prompt) {
    setLlmArtifactHint("llm_artifact_hint_prompt_required", "bad");
    return;
  }
  const schemaParsed = _parseLlmArtifactSchema();
  if (!schemaParsed.ok) {
    setLlmArtifactHint("llm_artifact_hint_schema_invalid", "bad");
    return;
  }

  const body = {
    transcript_variant: _llmArtifactSource(),
    mode,
    template_id: String((els.llmArtifactTemplateSelect && els.llmArtifactTemplateSelect.value) || "analysis").trim(),
    prompt: prompt || null,
    schema: schemaParsed.value,
    force_rebuild: Boolean(els.llmArtifactForceRebuild && els.llmArtifactForceRebuild.checked),
  };
  if (mode !== "template") {
    delete body.template_id;
  }

  state.llmArtifact.busy = true;
  renderLlmArtifactWorkspace();
  setLlmArtifactHint("llm_artifact_hint_running", "muted");
  const busySignal = showBusyOverlay("llm_artifact_busy_title", "llm_artifact_busy_text", { cancelable: true });
  updateBusyOverlayProgress(8);
  try {
    const res = await fetch(`/v1/meetings/${meetingId}/artifacts/generate`, {
      method: "POST",
      headers: buildHeaders(),
      body: JSON.stringify(body),
      signal: busySignal || undefined,
    });
    if (!res.ok) {
      const detail = await readApiErrorMessage(res, `llm_artifact_generate_failed_${res.status}`);
      if (isTranscriptNotReadyError(detail) || detail === "llm_input_text_required") {
        throw new Error("llm_requires_input_or_transcript");
      }
      throw new Error(detail);
    }
    updateBusyOverlayProgress(72);
    const payload = await res.json();
    updateBusyOverlayProgress(92);
    state.llmArtifact.lastResponse = payload;
    setLlmArtifactHint("llm_artifact_hint_done", "good");
    updateBusyOverlayProgress(100);
  } catch (err) {
    if (isAbortRequestError(err)) {
      setLlmArtifactHint("busy_overlay_cancelled", "muted");
      return;
    }
    console.warn("llm artifact generate failed", err);
    state.llmArtifact.lastResponse = null;
    const detail = String((err && err.message) || err || "").trim();
    if (detail === "llm_requires_input_or_transcript") {
      setLlmArtifactHint("llm_artifact_hint_needs_text_or_transcript", "bad");
    } else {
      setLlmArtifactHint("llm_artifact_hint_failed", "bad");
    }
  } finally {
    hideBusyOverlay();
    state.llmArtifact.busy = false;
    renderLlmArtifactWorkspace();
  }
};

const clearLlmChatResults = () => {
  if (Boolean(state.llmArtifact.busy)) return;
  state.llmArtifact.chatMessages = [];
  state.llmArtifact.lastResponse = null;
  state.llmArtifact.chatAttachments = [];
  if (els.llmChatAttachInput) {
    els.llmChatAttachInput.value = "";
  }
  setLlmChatHint("llm_chat_hint_cleared", "good");
  setLlmArtifactHint("llm_chat_hint_cleared", "good");
  renderLlmArtifactWorkspace();
};

const sendLlmChatPrompt = async () => {
  setResultsTab("llm", { setFlow: true });
  setLlmSourceMode("files");
  _syncLlmArtifactControlsToState();
  const dict = i18n[state.lang] || {};
  const meetingId = LLM_FILES_WORKSPACE_ID;
  state.llmArtifact.meetingId = meetingId;
  const prompt = String((els.llmChatInput && els.llmChatInput.value) || "").trim();
  if (!prompt) {
    setLlmChatHint("llm_chat_hint_prompt_required", "bad");
    return;
  }

  if (els.llmArtifactSourceSelect) {
    els.llmArtifactSourceSelect.value = "clean";
  }
  state.llmArtifact.transcriptSource = "clean";
  const mode = _llmChatInferMode(prompt);
  const attachments = Array.isArray(state.llmArtifact.chatAttachments) ? state.llmArtifact.chatAttachments : [];
  const textLikeAttachments = attachments.filter((file) => _attachmentIsTextLike(file));
  if (!textLikeAttachments.length) {
    setLlmChatHint("llm_chat_hint_files_required", "bad");
    setLlmArtifactHint("llm_chat_hint_files_required", "bad");
    return;
  }
  const attachmentContext = await _attachmentContextBlock(textLikeAttachments);
  if (!attachmentContext || !String(attachmentContext).trim()) {
    setLlmChatHint("llm_chat_hint_files_required", "bad");
    setLlmArtifactHint("llm_chat_hint_files_required", "bad");
    return;
  }
  const body = {
    transcript_variant: "clean",
    mode,
    prompt,
    input_text: attachmentContext || null,
    schema: null,
    // Для chat-запросов всегда пересобираем, чтобы не возвращать старый cache-артефакт.
    force_rebuild: true,
  };

  if (els.llmArtifactModeSelect) {
    els.llmArtifactModeSelect.value = mode;
  }
  state.llmArtifact.mode = mode;
  const userMetaParts = [attachmentContext ? "source=files" : "source=clean"];
  if (textLikeAttachments.length) userMetaParts.push(`files=${textLikeAttachments.length}`);
  _llmChatPushMessage({ role: "user", text: prompt, meta: userMetaParts.join(" • ") });
  if (els.llmChatInput) {
    els.llmChatInput.value = "";
  }

  state.llmArtifact.busy = true;
  setLlmChatHint("llm_chat_hint_running", "muted");
  setLlmArtifactHint("llm_artifact_hint_running", "muted");
  renderLlmArtifactWorkspace();
  const busySignal = showBusyOverlay("llm_artifact_busy_title", "llm_artifact_busy_text", { cancelable: true });
  updateBusyOverlayProgress(8);
  try {
    const res = await fetch(`/v1/meetings/${meetingId}/artifacts/generate`, {
      method: "POST",
      headers: buildHeaders(),
      body: JSON.stringify(body),
      signal: busySignal || undefined,
    });
    if (!res.ok) {
      let detail = "";
      try {
        const payload = await res.json();
        detail = String((payload && payload.detail) || "").trim();
      } catch (err) {
        // ignore non-json errors
      }
      if (isTranscriptNotReadyError(detail) || detail === "llm_input_text_required") {
        detail = "llm_requires_input_or_transcript";
      }
      throw new Error(detail ? `llm_chat_failed_${res.status}_${detail}` : `llm_chat_failed_${res.status}`);
    }
    updateBusyOverlayProgress(70);
    const payload = await res.json();
    updateBusyOverlayProgress(86);
    state.llmArtifact.lastResponse = payload;

    let previewText = "";
    try {
      previewText = await _llmArtifactFetchPreviewText({ meetingId, artifactResponse: payload });
    } catch (err) {
      previewText = "";
    }
    if (!previewText) {
      previewText = dict.llm_chat_preview_error || "Failed to load artifact preview.";
    }
    const rid = String(payload.artifact_id || "").trim();
    const shortId = rid ? rid.slice(0, 10) : "";
    const modeLabel = String(payload.mode || mode);
    _llmChatPushMessage({
      role: "assistant",
      text: previewText,
      meta: shortId ? `${modeLabel} • ${shortId}` : modeLabel,
    });
    setLlmChatHint("llm_chat_hint_done", "good");
    setLlmArtifactHint("llm_artifact_hint_done", "good");
    setFlowStep("results");
    updateBusyOverlayProgress(100);
  } catch (err) {
    if (isAbortRequestError(err)) {
      _llmChatPushMessage({
        role: "assistant",
        text: dict.busy_overlay_cancelled || "Operation canceled by user.",
      });
      setLlmChatHint("busy_overlay_cancelled", "muted");
      setLlmArtifactHint("busy_overlay_cancelled", "muted");
      setFlowStep("results");
      return;
    }
    console.warn("llm chat failed", err);
    const rawErr = String(err && err.message ? err.message : err || "").trim();
    const isNeedsText = rawErr.includes("llm_requires_input_or_transcript");
    const friendlyErr = isNeedsText
      ? (dict.llm_chat_hint_needs_text_or_transcript ||
          "Нет готового транскрипта. Сначала сформируйте TXT в блоке «Транскрипция» или прикрепите TXT файл.")
      : rawErr;
    _llmChatPushMessage({
      role: "assistant",
      text: `${dict.llm_chat_hint_failed || "Failed to get an LLM response."}\n${friendlyErr}`,
    });
    if (isNeedsText) {
      setLlmChatHint("llm_chat_hint_needs_text_or_transcript", "bad");
      setLlmArtifactHint("llm_artifact_hint_needs_text_or_transcript", "bad");
    } else {
      setLlmChatHint("llm_chat_hint_failed", "bad");
      setLlmArtifactHint("llm_artifact_hint_failed", "bad");
    }
    setFlowStep("process");
  } finally {
    hideBusyOverlay();
    state.llmArtifact.busy = false;
    state.llmArtifact.chatAttachments = [];
    if (els.llmChatAttachInput) {
      els.llmChatAttachInput.value = "";
    }
    renderLlmArtifactWorkspace();
  }
};

const downloadLlmArtifactFile = async (fmt, fileRef = null) => {
  const resp = state.llmArtifact.lastResponse;
  const meetingId = String((state.llmArtifact.meetingId || _llmArtifactMeetingId() || "")).trim();
  if (!resp || typeof resp !== "object" || !meetingId) {
    setLlmArtifactHint("llm_artifact_hint_no_result", "bad");
    return;
  }
  const artifactId = String(resp.artifact_id || "").trim();
  if (!artifactId) {
    setLlmArtifactHint("llm_artifact_hint_no_result", "bad");
    return;
  }
  const fmtSafe = ["json", "txt", "csv"].includes(String(fmt || "").toLowerCase()) ? String(fmt).toLowerCase() : "json";
  const url = `/v1/meetings/${meetingId}/artifacts/${artifactId}/download?fmt=${fmtSafe}`;
  const filename = _llmArtifactSuggestedFilename({
    meetingId,
    fmt: fmtSafe,
    response: resp,
    fileRef,
  });
  const result = await downloadArtifact(url, filename, { preferPicker: true });
  if (!result || !result.ok) {
    setLlmArtifactHint("llm_artifact_hint_failed", "bad");
  }
};

const setRagHint = (hintKeyOrText = "", style = "muted", isRaw = false, params = {}) => {
  if (!els.ragHint) return;
  const dict = i18n[state.lang] || {};
  let text = "";
  if (!hintKeyOrText) {
    text = "";
    state.rag.hintKey = "";
    state.rag.hintText = "";
    state.rag.hintStyle = "muted";
  } else if (!isRaw && dict[hintKeyOrText]) {
    text = formatText(dict[hintKeyOrText], params || {});
    state.rag.hintKey = hintKeyOrText;
    state.rag.hintText = "";
    state.rag.hintStyle = style || "muted";
  } else {
    text = String(hintKeyOrText || "");
    state.rag.hintKey = "";
    state.rag.hintText = text;
    state.rag.hintStyle = style || "muted";
  }
  els.ragHint.textContent = text;
  els.ragHint.className = `hint ${style || "muted"}`;
};

const _ragSelectedMeetingIds = () => {
  const set = state.rag && state.rag.selectedMeetingIds instanceof Set ? state.rag.selectedMeetingIds : new Set();
  const existing = new Set(Array.from(state.recordsMeta.keys()));
  return Array.from(set)
    .map((v) => String(v || "").trim())
    .filter((v) => v && existing.has(v));
};

const _setRagSelectedMeetingIds = (values = []) => {
  if (!(state.rag.selectedMeetingIds instanceof Set)) {
    state.rag.selectedMeetingIds = new Set();
  }
  state.rag.selectedMeetingIds.clear();
  (Array.isArray(values) ? values : []).forEach((value) => {
    const meetingId = String(value || "").trim();
    if (meetingId && state.recordsMeta.has(meetingId)) {
      state.rag.selectedMeetingIds.add(meetingId);
    }
  });
};

const _ragSourceValue = () => {
  const raw = String((els.ragSourceSelect && els.ragSourceSelect.value) || state.rag.source || "clean").trim();
  if (raw === "raw" || raw === "normalized") return raw;
  return "clean";
};

const _ragTopKValue = () => {
  const raw = Number((els.ragTopKInput && els.ragTopKInput.value) || state.rag.topK || 8);
  const bounded = Math.min(50, Math.max(1, Number.isFinite(raw) ? Math.round(raw) : 8));
  return bounded;
};

const _ragIndexStatusValue = (meta, source = "clean") => {
  const src = String(source || "clean").trim().toLowerCase();
  const map = meta && typeof meta.rag_index_status === "object" ? meta.rag_index_status : null;
  const value = map ? String(map[src] || "") : "";
  return value || "missing";
};

const _ragIndexStatusLabel = (statusValue) => {
  const dict = i18n[state.lang] || {};
  const key = `rag_index_status_${String(statusValue || "").trim().toLowerCase() || "missing"}`;
  return String(dict[key] || dict.rag_index_status_unknown || statusValue || "unknown");
};

const _normalizeRagSavedSets = (raw) => {
  const out = {};
  if (!raw || typeof raw !== "object") return out;
  Object.entries(raw).forEach(([nameRaw, idsRaw]) => {
    const name = String(nameRaw || "").trim().slice(0, 80);
    if (!name) return;
    const seen = new Set();
    const ids = [];
    (Array.isArray(idsRaw) ? idsRaw : []).forEach((value) => {
      const meetingId = String(value || "").trim();
      if (!meetingId || seen.has(meetingId)) return;
      seen.add(meetingId);
      ids.push(meetingId);
    });
    if (ids.length) {
      out[name] = ids;
    }
  });
  return out;
};

const _loadRagSavedSetsFromStorage = () => {
  try {
    const raw = localStorage.getItem(RAG_SAVED_SETS_KEY);
    if (!raw) {
      state.rag.savedSets = {};
      state.rag.activeSavedSet = "";
      return;
    }
    const parsed = JSON.parse(raw);
    state.rag.savedSets = _normalizeRagSavedSets(parsed);
    if (!state.rag.savedSets[String(state.rag.activeSavedSet || "")]) {
      state.rag.activeSavedSet = "";
    }
  } catch (err) {
    state.rag.savedSets = {};
    state.rag.activeSavedSet = "";
  }
};

const _persistRagSavedSetsToStorage = () => {
  try {
    const normalized = _normalizeRagSavedSets(state.rag.savedSets || {});
    state.rag.savedSets = normalized;
    localStorage.setItem(RAG_SAVED_SETS_KEY, JSON.stringify(normalized));
  } catch (err) {
    console.warn("rag saved sets persist failed", err);
  }
};

const _renderRagSavedSetSelect = () => {
  if (!els.ragSavedSetSelect) return;
  const dict = i18n[state.lang] || {};
  const savedSets = _normalizeRagSavedSets(state.rag.savedSets || {});
  state.rag.savedSets = savedSets;
  const names = Object.keys(savedSets).sort((a, b) => a.localeCompare(b, state.lang === "ru" ? "ru" : "en"));
  if (!savedSets[String(state.rag.activeSavedSet || "")]) {
    state.rag.activeSavedSet = "";
  }
  els.ragSavedSetSelect.innerHTML = "";
  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = dict.rag_saved_set_none || "Saved sets";
  els.ragSavedSetSelect.appendChild(placeholder);
  names.forEach((name) => {
    const opt = document.createElement("option");
    opt.value = name;
    const ids = Array.isArray(savedSets[name]) ? savedSets[name] : [];
    opt.textContent = `${name} (${ids.length})`;
    if (name === state.rag.activeSavedSet) opt.selected = true;
    els.ragSavedSetSelect.appendChild(opt);
  });
  if (els.ragLoadSetBtn) els.ragLoadSetBtn.disabled = !state.rag.activeSavedSet;
  if (els.ragDeleteSetBtn) els.ragDeleteSetBtn.disabled = !state.rag.activeSavedSet;
};

const _syncRagControlsToState = () => {
  state.rag.source = _ragSourceValue();
  state.rag.topK = _ragTopKValue();
  state.rag.useLlmAnswer = Boolean(els.ragUseLlmAnswer && els.ragUseLlmAnswer.checked);
  state.rag.autoIndex = !(els.ragAutoIndex && !els.ragAutoIndex.checked);
  state.rag.forceReindex = Boolean(els.ragForceReindex && els.ragForceReindex.checked);
};

const renderRagMeetingPicker = () => {
  if (!els.ragMeetingPicker) return;
  const dict = i18n[state.lang] || {};
  const items = Array.from(state.recordsMeta.values());
  const currentSelected = String(getSelectedMeeting() || "").trim();
  const existingIds = new Set(items.map((item) => String(item && item.meeting_id ? item.meeting_id : "")));

  if (!(state.rag.selectedMeetingIds instanceof Set)) {
    state.rag.selectedMeetingIds = new Set();
  }
  {
    const nextSaved = {};
    const currentSaved = _normalizeRagSavedSets(state.rag.savedSets || {});
    let changed = false;
    Object.entries(currentSaved).forEach(([name, ids]) => {
      const filtered = ids.filter((meetingId) => existingIds.has(String(meetingId || "")));
      if (!filtered.length) {
        changed = true;
        if (state.rag.activeSavedSet === name) state.rag.activeSavedSet = "";
        return;
      }
      nextSaved[name] = filtered;
      if (filtered.length !== ids.length) changed = true;
    });
    if (changed) {
      state.rag.savedSets = nextSaved;
      _persistRagSavedSetsToStorage();
    } else {
      state.rag.savedSets = currentSaved;
    }
  }
  Array.from(state.rag.selectedMeetingIds).forEach((meetingId) => {
    if (!existingIds.has(String(meetingId || ""))) {
      state.rag.selectedMeetingIds.delete(meetingId);
    }
  });
  if (!state.rag.selectedMeetingIds.size && currentSelected && existingIds.has(currentSelected)) {
    state.rag.selectedMeetingIds.add(currentSelected);
  }

  if (els.ragSourceSelect) {
    els.ragSourceSelect.value = state.rag.source || "clean";
  }
  if (els.ragTopKInput) {
    els.ragTopKInput.value = String(_ragTopKValue());
  }
  if (els.ragUseLlmAnswer) {
    els.ragUseLlmAnswer.checked = Boolean(state.rag.useLlmAnswer);
  }
  if (els.ragAutoIndex) {
    els.ragAutoIndex.checked = Boolean(state.rag.autoIndex);
  }
  if (els.ragForceReindex) {
    els.ragForceReindex.checked = Boolean(state.rag.forceReindex);
  }
  if (els.ragSavedSetSelect) {
    els.ragSavedSetSelect.value = String(state.rag.activeSavedSet || "");
  }
  _renderRagSavedSetSelect();

  els.ragMeetingPicker.innerHTML = "";
  if (!items.length) {
    const empty = document.createElement("div");
    empty.className = "rag-meeting-picker-empty";
    empty.textContent = dict.rag_picker_empty || "No recordings yet.";
    els.ragMeetingPicker.appendChild(empty);
    return;
  }

  items.forEach((meta) => {
    const meetingId = String(meta.meeting_id || "").trim();
    if (!meetingId) return;
    const row = document.createElement("label");
    row.className = "rag-meeting-option";

    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.checked = state.rag.selectedMeetingIds.has(meetingId);
    cb.addEventListener("change", () => {
      if (cb.checked) state.rag.selectedMeetingIds.add(meetingId);
      else state.rag.selectedMeetingIds.delete(meetingId);
      renderRagWorkspace();
    });

    const body = document.createElement("div");
    const title = document.createElement("div");
    title.className = "rag-meeting-title";
    title.textContent = formatMeetingOptionLabel(meta);

    const sub = document.createElement("div");
    sub.className = "rag-meeting-sub";
    const parts = [];
    if (meta && meta.artifacts && meta.artifacts.audio_mp3) parts.push("MP3");
    if (meta && meta.artifacts && meta.artifacts.clean) parts.push("clean");
    if (meta && meta.artifacts && meta.artifacts.normalized) parts.push("normalized");
    if (meta && meta.artifacts && meta.artifacts.raw) parts.push("raw");
    sub.textContent = parts.length ? parts.join(" • ") : "—";

    const ragSub = document.createElement("div");
    ragSub.className = "rag-meeting-sub";
    const ragSource = _ragSourceValue();
    const ragStatus = _ragIndexStatusValue(meta, ragSource);
    const srcLabel = String(((i18n[state.lang] || {})[`rag_source_${ragSource}`] || ragSource) || ragSource);
    const statusLabel = _ragIndexStatusLabel(ragStatus);
    ragSub.textContent = `${(i18n[state.lang] || {}).rag_index_status_prefix || "RAG index"} (${srcLabel}): ${statusLabel}`;
    if (ragStatus === "indexed") ragSub.classList.add("good");
    else if (ragStatus === "outdated" || ragStatus === "invalid" || ragStatus === "orphaned") ragSub.classList.add("bad");
    else ragSub.classList.add("muted");

    body.appendChild(title);
    body.appendChild(sub);
    body.appendChild(ragSub);
    row.appendChild(cb);
    row.appendChild(body);
    els.ragMeetingPicker.appendChild(row);
  });
};

const saveRagCompareSet = () => {
  const selectedIds = _ragSelectedMeetingIds();
  if (!selectedIds.length) {
    setRagHint("rag_saved_set_hint_empty_selection", "bad");
    return;
  }
  const dict = i18n[state.lang] || {};
  const suggested =
    String(state.rag.activeSavedSet || "").trim() ||
    String(getSelectedRecordDisplayName ? getSelectedRecordDisplayName() : "").trim() ||
    "";
  const rawName = window.prompt(dict.rag_saved_set_prompt_name || "Set name", suggested);
  if (rawName == null) return;
  const name = String(rawName || "").trim().slice(0, 80);
  if (!name) return;
  state.rag.savedSets = _normalizeRagSavedSets({
    ...(state.rag.savedSets && typeof state.rag.savedSets === "object" ? state.rag.savedSets : {}),
    [name]: selectedIds,
  });
  state.rag.activeSavedSet = name;
  _persistRagSavedSetsToStorage();
  renderRagWorkspace();
  setRagHint("rag_saved_set_hint_saved", "good");
};

const loadRagCompareSet = () => {
  const name = String(
    (els.ragSavedSetSelect && els.ragSavedSetSelect.value) || state.rag.activeSavedSet || ""
  ).trim();
  if (!name) {
    setRagHint("rag_saved_set_hint_choose", "bad");
    return;
  }
  const savedSets = _normalizeRagSavedSets(state.rag.savedSets || {});
  const ids = Array.isArray(savedSets[name]) ? savedSets[name] : [];
  if (!ids.length) {
    setRagHint("rag_saved_set_hint_choose", "bad");
    return;
  }
  state.rag.activeSavedSet = name;
  _setRagSelectedMeetingIds(ids);
  renderRagWorkspace();
  setRagHint("rag_saved_set_hint_loaded", "good");
};

const deleteRagCompareSet = () => {
  const name = String(
    (els.ragSavedSetSelect && els.ragSavedSetSelect.value) || state.rag.activeSavedSet || ""
  ).trim();
  if (!name) {
    setRagHint("rag_saved_set_hint_choose", "bad");
    return;
  }
  const next = { ...(state.rag.savedSets && typeof state.rag.savedSets === "object" ? state.rag.savedSets : {}) };
  delete next[name];
  state.rag.savedSets = _normalizeRagSavedSets(next);
  if (state.rag.activeSavedSet === name) {
    state.rag.activeSavedSet = "";
  }
  _persistRagSavedSetsToStorage();
  renderRagWorkspace();
  setRagHint("rag_saved_set_hint_deleted", "good");
};

const _ragHitPill = (text, style = "muted") => {
  const span = document.createElement("span");
  span.className = `pill ${style}`;
  span.textContent = String(text || "");
  return span;
};

const renderRagResults = () => {
  const dict = i18n[state.lang] || {};
  const resp = state.rag.lastResponse && typeof state.rag.lastResponse === "object" ? state.rag.lastResponse : null;
  const hits = resp && Array.isArray(resp.hits) ? resp.hits : [];
  const answerText = resp ? String(resp.answer || "").trim() : "";

  if (els.ragResultMeta) {
    if (!resp) {
      els.ragResultMeta.textContent = dict.rag_result_meta_none || "No results";
      els.ragResultMeta.className = "pill muted";
    } else {
      const mode = String(resp.llm_used ? "llm" : "retrieval_only");
      const txt = formatText(dict.rag_result_meta_template || "", {
        meetings: Number(resp.searched_meetings || 0),
        indexed: Number(resp.indexed_meetings || 0),
        chunks: Number(resp.total_chunks_scanned || 0),
        hits: hits.length,
        mode,
      });
      els.ragResultMeta.textContent = txt || mode;
      els.ragResultMeta.className = `pill ${hits.length ? "good" : "muted"}`;
    }
  }

  if (els.ragAnswerText) {
    if (!resp) {
      els.ragAnswerText.textContent = "";
    } else if (answerText) {
      const warnings = Array.isArray(resp.warnings) ? resp.warnings.filter(Boolean) : [];
      const warnLine = warnings.length ? `Warnings: ${warnings.join(", ")}\n\n` : "";
      els.ragAnswerText.textContent = `${warnLine}${answerText}`;
    } else {
      const warnings = Array.isArray(resp.warnings) ? resp.warnings.filter(Boolean) : [];
      els.ragAnswerText.textContent = warnings.length ? `Warnings: ${warnings.join(", ")}` : "";
    }
  }

  if (els.ragHitsList) {
    els.ragHitsList.innerHTML = "";
    if (!hits.length) {
      const empty = document.createElement("div");
      empty.className = "rag-hit-empty";
      empty.textContent = dict.rag_hits_empty || "Retrieved chunks will appear here.";
      els.ragHitsList.appendChild(empty);
    } else {
      hits.forEach((hit) => {
        const card = document.createElement("div");
        card.className = "rag-hit-card";

        const head = document.createElement("div");
        head.className = "rag-hit-head";

        const title = document.createElement("div");
        title.className = "rag-hit-title";
        title.textContent = `${dict.rag_hit_meta_meeting || "Record"}: ${String(hit.meeting_id || "")}`;

        const meta = document.createElement("div");
        meta.className = "rag-hit-meta";
        const score = Number.isFinite(Number(hit.score)) ? Number(hit.score).toFixed(3) : "0";
        const chunkId = String(hit.chunk_id || "");
        meta.textContent = `${dict.rag_hit_meta_score || "Score"}=${score} • chunk=${chunkId}`;

        head.appendChild(title);
        head.appendChild(meta);
        card.appendChild(head);

        const cite = document.createElement("div");
        cite.className = "rag-hit-cite";
        if (hit.line_start != null || hit.line_end != null) {
          const ls = hit.line_start != null ? hit.line_start : "?";
          const le = hit.line_end != null ? hit.line_end : "?";
          cite.appendChild(_ragHitPill(`${dict.rag_hit_meta_lines || "Lines"}: ${ls}-${le}`, "muted"));
        }
        if (String(hit.timestamp_start || "").trim() || String(hit.timestamp_end || "").trim()) {
          cite.appendChild(
            _ragHitPill(
              `${dict.rag_hit_meta_time || "Time"}: ${String(hit.timestamp_start || "?")}..${String(hit.timestamp_end || "?")}`,
              "muted"
            )
          );
        }
        const speakers = Array.isArray(hit.speakers) ? hit.speakers.filter(Boolean) : [];
        if (speakers.length) {
          cite.appendChild(
            _ragHitPill(`${dict.rag_hit_meta_speakers || "Speakers"}: ${speakers.join(", ")}`, "muted")
          );
        }
        if (String(hit.candidate_name || "").trim()) {
          cite.appendChild(
            _ragHitPill(
              `${dict.rag_hit_meta_candidate || "Candidate"}: ${String(hit.candidate_name)}`,
              "good"
            )
          );
        }
        if (String(hit.vacancy || "").trim()) {
          cite.appendChild(
            _ragHitPill(`${dict.rag_hit_meta_vacancy || "Vacancy"}: ${String(hit.vacancy)}`, "muted")
          );
        }
        if (String(hit.level || "").trim()) {
          cite.appendChild(_ragHitPill(`${dict.rag_hit_meta_level || "Level"}: ${String(hit.level)}`, "muted"));
        }
        if (cite.childNodes.length) {
          card.appendChild(cite);
        }

        const text = document.createElement("pre");
        text.className = "rag-hit-text";
        text.textContent = String(hit.text || "");
        card.appendChild(text);

        els.ragHitsList.appendChild(card);
      });
    }
  }

  const hasResponse = Boolean(resp);
  [els.ragExportJsonBtn, els.ragExportCsvBtn, els.ragExportTxtBtn].forEach((btn) => {
    if (!btn) return;
    btn.disabled = !hasResponse;
  });

  if (els.ragResultFiles) {
    els.ragResultFiles.innerHTML = "";
    const files = resp && Array.isArray(resp.files) ? resp.files : [];
    if (!files.length) {
      const empty = document.createElement("div");
      empty.className = "rag-hit-empty";
      empty.textContent = dict.llm_artifact_result_none || dict.rag_result_meta_none || "No results";
      els.ragResultFiles.appendChild(empty);
    } else {
      files.forEach((fileRef) => {
        const fmt = String((fileRef && fileRef.fmt) || "").trim().toLowerCase();
        if (!["json", "csv", "txt"].includes(fmt)) return;
        const btn = document.createElement("button");
        btn.className = "ghost llm-artifact-file-btn";
        const fallbackName = `rag_${fmt}_result.${fmt}`;
        const filename = String((fileRef && fileRef.filename) || "").trim() || fallbackName;
        const bytes = Number((fileRef && fileRef.bytes) || 0);
        const label = formatText(dict.rag_result_file_download || dict.llm_artifact_file_download || "Download {fmt}", {
          fmt: fmt.toUpperCase(),
        });
        btn.textContent = `${label} (${_formatBytes(bytes)})`;
        btn.addEventListener("click", () => {
          const directUrl = String((fileRef && fileRef.download_url) || "").trim();
          const requestId = String((resp && resp.request_id) || "").trim();
          const url = directUrl || (requestId ? `/v1/rag/query/export?request_id=${encodeURIComponent(requestId)}&fmt=${encodeURIComponent(fmt)}` : "");
          if (!url) {
            setRagHint("rag_hint_export_empty", "bad");
            return;
          }
          void downloadArtifact(url, filename, { preferPicker: true });
        });
        els.ragResultFiles.appendChild(btn);
      });
    }
  }
};

const renderRagWorkspace = () => {
  _syncRagControlsToState();
  renderRagMeetingPicker();
  renderRagResults();
  renderRagChatHistory();
  if (state.rag.hintKey) {
    setRagHint(state.rag.hintKey, state.rag.hintStyle || "muted", false);
  } else if (state.rag.hintText) {
    setRagHint(state.rag.hintText, state.rag.hintStyle || "muted", true);
  } else {
    setRagHint("rag_hint_idle", "muted");
  }
  const busyAny = Boolean(state.rag.queryBusy || state.rag.indexBusy);
  if (els.ragRunBtn) els.ragRunBtn.disabled = busyAny;
  if (els.ragIndexSelectedBtn) els.ragIndexSelectedBtn.disabled = busyAny;
};

const _ragJsonHeaders = () => ({
  ...buildHeaders(),
});

const _ragIndexJobTerminal = (status) => {
  const value = String(status || "").trim().toLowerCase();
  return value === "completed" || value === "failed";
};

const _formatRagIndexJobHint = (job) => {
  const status = String((job && job.status) || "").trim().toLowerCase();
  const total = Number((job && job.total_meetings) || 0);
  const done = Number((job && job.completed_meetings) || 0);
  const ok = Number((job && job.ok_meetings) || 0);
  const failed = Number((job && job.failed_meetings) || 0);
  const current = String((job && job.current_meeting_id) || "").trim();
  const ru = state.lang === "ru";
  if (status === "completed") {
    return ru
      ? `RAG индексация завершена: ${ok}/${total || ok + failed} успешно, ошибок: ${failed}.`
      : `RAG indexing completed: ${ok}/${total || ok + failed} succeeded, failed: ${failed}.`;
  }
  if (status === "failed") {
    const err = String((job && job.error) || "").trim();
    return ru
      ? `RAG индексация завершилась с ошибкой${err ? `: ${err}` : ""}.`
      : `RAG indexing failed${err ? `: ${err}` : ""}.`;
  }
  const progressPct = Math.round(Math.max(0, Math.min(100, Number((job && job.progress) || 0) * 100)));
  if (ru) {
    return `Индексация RAG: ${done}/${total || "?"} (${progressPct}%)${current ? ` · сейчас: ${current}` : ""}`;
  }
  return `RAG indexing: ${done}/${total || "?"} (${progressPct}%)${current ? ` · current: ${current}` : ""}`;
};

const _applyRagIndexJobStatusToRecords = (job) => {
  if (!job || typeof job !== "object") return;
  const source = String(job.transcript_variant || state.rag.source || "clean").trim().toLowerCase();
  if (!["raw", "normalized", "clean"].includes(source)) return;
  const items = Array.isArray(job.items) ? job.items : [];
  items.forEach((row) => {
    const meetingId = String((row && row.meeting_id) || "").trim();
    if (!meetingId || !state.recordsMeta.has(meetingId)) return;
    const meta = state.recordsMeta.get(meetingId) || { meeting_id: meetingId };
    const currentMap = meta && typeof meta.rag_index_status === "object" ? meta.rag_index_status : {};
    const nextMap = { ...currentMap };
    const rowStatus = String((row && row.status) || "").trim().toLowerCase();
    if (rowStatus === "completed") nextMap[source] = "indexed";
    else if (rowStatus === "failed") nextMap[source] = "outdated";
    state.recordsMeta.set(meetingId, { ...meta, rag_index_status: nextMap });
  });
};

const _pollRagIndexJobUntilDone = async (jobId, signal = null) => {
  const id = String(jobId || "").trim();
  if (!id) throw new Error("rag_index_job_id_required");
  let lastBody = null;
  const startedAt = Date.now();
  const timeoutMs = 15 * 60 * 1000;
  while (Date.now() - startedAt < timeoutMs) {
    if (signal && signal.aborted) {
      throw new DOMException("Operation canceled by user", "AbortError");
    }
    const res = await fetch(`/v1/rag/index-jobs/${encodeURIComponent(id)}`, {
      headers: _ragJsonHeaders(),
      signal: signal || undefined,
    });
    if (!res.ok) {
      throw new Error(`rag_index_job_status_failed_${res.status}`);
    }
    const body = await res.json();
    lastBody = body;
    state.rag.indexJobId = id;
    state.rag.indexJobStatus = body;
    _applyRagIndexJobStatusToRecords(body);
    const hintText = _formatRagIndexJobHint(body);
    const progressPct = Math.round(Math.max(0, Math.min(100, Number((body && body.progress) || 0) * 100)));
    updateBusyOverlayProgress(Math.max(6, progressPct), hintText, { rawText: true });
    setRagHint(hintText, _ragIndexJobTerminal(body.status) ? (body.status === "completed" ? "good" : "bad") : "muted", true);
    renderRagWorkspace();
    if (_ragIndexJobTerminal(body.status)) {
      updateBusyOverlayProgress(100, hintText, { rawText: true });
      return body;
    }
    await sleepMs(700);
  }
  throw new Error("rag_index_job_timeout");
};

const _startRagIndexJobForMeetings = async (meetingIds, signal = null) => {
  const ids = Array.isArray(meetingIds) ? meetingIds.map((v) => String(v || "").trim()).filter(Boolean) : [];
  if (!ids.length) {
    throw new Error("rag_index_job_meeting_ids_required");
  }
  const startRes = await fetch("/v1/rag/index-jobs", {
    method: "POST",
    headers: _ragJsonHeaders(),
    body: JSON.stringify({
      meeting_ids: ids,
      transcript_variant: state.rag.source || "clean",
      force_rebuild: Boolean(state.rag.forceReindex),
    }),
    signal: signal || undefined,
  });
  if (!startRes.ok) {
    throw new Error(`rag_index_job_start_failed_${startRes.status}`);
  }
  const startBody = await startRes.json();
  const jobId = String((startBody && startBody.job_id) || "").trim();
  if (!jobId) {
    throw new Error("rag_index_job_id_missing");
  }
  state.rag.indexJobId = jobId;
  state.rag.indexJobStatus = startBody;
  renderRagWorkspace();
  return { jobId, startBody };
};

const _runRagIndexJobForMeetings = async (meetingIds, signal = null) => {
  const started = await _startRagIndexJobForMeetings(meetingIds, signal);
  return _pollRagIndexJobUntilDone(started.jobId, signal);
};

const indexSelectedRagMeetings = async () => {
  const selectedIds = _ragSelectedMeetingIds();
  if (!selectedIds.length) {
    setRagHint("rag_hint_index_no_selection", "bad");
    return;
  }
  _syncRagControlsToState();
  state.rag.indexBusy = true;
  state.rag.indexJobStatus = null;
  renderRagWorkspace();
  setRagHint("rag_hint_indexing", "muted");
  const busySignal = showBusyOverlay("busy_rag_index_title", "busy_rag_index_text", { cancelable: true });
  updateBusyOverlayProgress(8);
  try {
    await _runRagIndexJobForMeetings(selectedIds, busySignal || null);
  } catch (err) {
    if (isAbortRequestError(err)) {
      setRagHint("busy_overlay_cancelled", "muted");
      return;
    }
    console.warn("rag index failed", err);
    setRagHint("rag_hint_failed", "bad");
  } finally {
    hideBusyOverlay();
    state.rag.indexBusy = false;
    renderRagWorkspace();
  }
};

const runRagQuery = async () => {
  setResultsTab("llm", { setFlow: true });
  setLlmSourceMode("rag");
  const dict = i18n[state.lang] || {};
  const query = String((els.ragQueryInput && els.ragQueryInput.value) || "").trim();
  if (!query) {
    setRagHint("rag_hint_query_empty", "bad");
    setRagChatHint("rag_hint_query_empty", "bad");
    return;
  }
  _syncRagControlsToState();
  const selectedIds = _ragSelectedMeetingIds();
  const attachments = Array.isArray(state.rag.chatAttachments) ? state.rag.chatAttachments : [];
  const attachmentContext = await _attachmentContextBlock(attachments);
  const answerPromptBase = String((els.ragAnswerPromptInput && els.ragAnswerPromptInput.value) || "").trim();
  const mergedAnswerPrompt = [answerPromptBase, attachmentContext].filter(Boolean).join("\n\n");
  const payload = {
    query,
    transcript_variant: state.rag.source || "clean",
    meeting_ids: selectedIds,
    top_k: _ragTopKValue(),
    auto_index: Boolean(state.rag.autoIndex),
    force_reindex: Boolean(state.rag.forceReindex),
    answer_mode: state.rag.useLlmAnswer ? "llm" : "none",
    answer_prompt: mergedAnswerPrompt,
  };
  const userMetaParts = [];
  if (selectedIds.length) userMetaParts.push(`meetings=${selectedIds.length}`);
  if (attachments.length) userMetaParts.push(`files=${attachments.length}`);
  _ragChatPushMessage({ role: "user", text: query, meta: userMetaParts.join(" • ") });

  state.rag.queryBusy = true;
  renderRagWorkspace();
  if (selectedIds.length && state.rag.autoIndex) {
    state.rag.indexBusy = true;
  }
  renderRagWorkspace();
  setRagHint(selectedIds.length && state.rag.autoIndex ? "rag_hint_indexing" : "rag_hint_querying", "muted");
  setRagChatHint("rag_chat_hint_running", "muted");
  const busySignal = showBusyOverlay("busy_rag_query_title", "busy_rag_query_text", { cancelable: true });
  updateBusyOverlayProgress(8);
  try {
    if (selectedIds.length && state.rag.autoIndex) {
      const indexJob = await _runRagIndexJobForMeetings(selectedIds, busySignal || null);
      const okMeetings = Number((indexJob && indexJob.ok_meetings) || 0);
      const totalMeetings = Number((indexJob && indexJob.total_meetings) || selectedIds.length || 0);
      if (okMeetings <= 0 && totalMeetings > 0) {
        throw new Error("rag_query_preindex_failed_all");
      }
      // Avoid duplicate synchronous indexing on query request when selection was pre-indexed asynchronously.
      payload.auto_index = false;
      setRagHint("rag_hint_querying", "muted");
      updateBusyOverlayProgress(62);
    }
    updateBusyOverlayProgress(70);
    const res = await fetch("/v1/rag/query", {
      method: "POST",
      headers: _ragJsonHeaders(),
      body: JSON.stringify(payload),
      signal: busySignal || undefined,
    });
    if (!res.ok) {
      throw new Error(`rag_query_failed_${res.status}`);
    }
    const body = await res.json();
    updateBusyOverlayProgress(88);
    state.rag.lastResponse = body;
    renderRagResults();
    const hits = Array.isArray(body && body.hits) ? body.hits : [];
    const answerText = String((body && body.answer) || "").trim();
    const fallback = hits.length
      ? hits
          .slice(0, 3)
          .map((hit, idx) => `[${idx + 1}] ${String(hit && hit.text ? hit.text : "").trim()}`)
          .filter(Boolean)
          .join("\n\n")
      : "";
    _ragChatPushMessage({
      role: "assistant",
      text: answerText || fallback || (dict.rag_hint_no_results || "No relevant transcript chunks were found."),
      meta: `hits=${hits.length}`,
    });
    if (!hits.length) {
      setRagHint("rag_hint_no_results", "muted");
      setRagChatHint("rag_hint_no_results", "muted");
    } else {
      setRagHint("rag_hint_done", "good");
      setRagChatHint("rag_chat_hint_done", "good");
    }
    updateBusyOverlayProgress(100);
  } catch (err) {
    if (isAbortRequestError(err)) {
      setRagHint("busy_overlay_cancelled", "muted");
      setRagChatHint("busy_overlay_cancelled", "muted");
      return;
    }
    console.warn("rag query failed", err);
    state.rag.lastResponse = null;
    renderRagResults();
    setRagHint("rag_hint_failed", "bad");
    _ragChatPushMessage({
      role: "assistant",
      text: `${dict.rag_chat_hint_failed || "Failed to get a RAG response."}\n${String(err && err.message ? err.message : err)}`,
    });
    setRagChatHint("rag_chat_hint_failed", "bad");
  } finally {
    hideBusyOverlay();
    state.rag.indexBusy = false;
    state.rag.queryBusy = false;
    state.rag.chatAttachments = [];
    if (els.ragChatAttachInput) {
      els.ragChatAttachInput.value = "";
    }
    renderRagWorkspace();
  }
};

const _ragCsvEscape = (value) => {
  const text = String(value == null ? "" : value);
  if (/[",\n\r]/.test(text)) {
    return `"${text.replace(/"/g, '""')}"`;
  }
  return text;
};

const _ragResponseToCsv = (resp) => {
  const hits = Array.isArray(resp && resp.hits) ? resp.hits : [];
  const headers = [
    "meeting_id",
    "chunk_id",
    "score",
    "line_start",
    "line_end",
    "start_ms",
    "end_ms",
    "timestamp_start",
    "timestamp_end",
    "speakers",
    "candidate_name",
    "candidate_id",
    "vacancy",
    "level",
    "interviewer",
    "text",
  ];
  const rows = [headers.join(",")];
  hits.forEach((hit) => {
    rows.push(
      [
        hit.meeting_id,
        hit.chunk_id,
        hit.score,
        hit.line_start,
        hit.line_end,
        hit.start_ms,
        hit.end_ms,
        hit.timestamp_start,
        hit.timestamp_end,
        Array.isArray(hit.speakers) ? hit.speakers.join("|") : "",
        hit.candidate_name,
        hit.candidate_id,
        hit.vacancy,
        hit.level,
        hit.interviewer,
        hit.text,
      ]
        .map(_ragCsvEscape)
        .join(",")
    );
  });
  return `\ufeff${rows.join("\n")}`;
};

const _ragResponseToTxt = (resp) => {
  const body = resp && typeof resp === "object" ? resp : {};
  const hits = Array.isArray(body.hits) ? body.hits : [];
  const lines = [];
  lines.push(`Query: ${String(body.query || "")}`);
  lines.push(`Transcript source: ${String(body.transcript_variant || "")}`);
  lines.push(
    `Meetings: searched=${Number(body.searched_meetings || 0)}, indexed=${Number(body.indexed_meetings || 0)}`
  );
  lines.push(`Chunks scanned: ${Number(body.total_chunks_scanned || 0)}`);
  lines.push(`LLM used: ${Boolean(body.llm_used)}`);
  if (Array.isArray(body.warnings) && body.warnings.length) {
    lines.push(`Warnings: ${body.warnings.join(", ")}`);
  }
  lines.push("");
  lines.push("Answer:");
  lines.push(String(body.answer || "").trim() || "—");
  lines.push("");
  lines.push("Hits:");
  hits.forEach((hit, idx) => {
    lines.push(
      `[${idx + 1}] meeting=${String(hit.meeting_id || "")} chunk=${String(hit.chunk_id || "")} score=${String(hit.score || "")}`
    );
    lines.push(
      `lines=${String(hit.line_start ?? "?")}-${String(hit.line_end ?? "?")} time=${String(hit.timestamp_start || "?")}..${String(hit.timestamp_end || "?")}`
    );
    if (Array.isArray(hit.speakers) && hit.speakers.length) {
      lines.push(`speakers=${hit.speakers.join(", ")}`);
    }
    lines.push(String(hit.text || ""));
    lines.push("");
  });
  return lines.join("\n");
};

const exportRagResults = async (fmt = "json") => {
  const resp = state.rag.lastResponse;
  if (!resp || typeof resp !== "object") {
    setRagHint("rag_hint_export_empty", "bad");
    return;
  }
  const query = String(resp.query || "rag_query")
    .slice(0, 40)
    .replace(/[\\/:*?"<>|]/g, "_")
    .replace(/\s+/g, "_");
  const stamp = new Date().toISOString().replace(/[-:TZ.]/g, "").slice(0, 14);
  let filename = `rag_${query || "query"}_${stamp}.${fmt}`;
  let blob = null;
  if (fmt === "json") {
    blob = new Blob([JSON.stringify(resp, null, 2)], { type: "application/json" });
  } else if (fmt === "csv") {
    blob = new Blob([_ragResponseToCsv(resp)], { type: "text/csv;charset=utf-8" });
  } else {
    blob = new Blob([_ragResponseToTxt(resp)], { type: "text/plain;charset=utf-8" });
    filename = `rag_${query || "query"}_${stamp}.txt`;
  }
  const saved = await saveLocalBlob(filename, blob, { preferPicker: true });
  if (!saved.ok) {
    setRagHint("rag_hint_failed", "bad");
  }
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

const renderSttStatus = () => {
  if (!els.sttModelStatusText) return;
  const dict = i18n[state.lang] || {};
  let text = state.sttStatusText;
  if (!text) {
    const template = dict[state.sttStatusKey] || state.sttStatusKey;
    text = formatText(template, state.sttStatusParams || {});
  }
  els.sttModelStatusText.textContent = text;
  els.sttModelStatusText.className = `hint llm-status ${state.sttStatusStyle || "muted"}`;
};

const setSttStatus = (
  statusKeyOrText = "stt_status_loading",
  style = "muted",
  params = {},
  isRaw = false
) => {
  state.sttStatusStyle = style || "muted";
  state.sttStatusParams = params || {};
  if (isRaw) {
    state.sttStatusText = String(statusKeyOrText || "");
    state.sttStatusKey = "";
  } else {
    state.sttStatusKey = String(statusKeyOrText || "");
    state.sttStatusText = "";
  }
  renderSttStatus();
};

const setSttModelOptions = (models = [], preferredModel = "") => {
  if (!els.sttModelSelect) return;
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

  const currentValue = String(preferredModel || els.sttModelSelect.value || "").trim();
  state.sttModels = unique;

  els.sttModelSelect.innerHTML = "";
  if (!unique.length) {
    const emptyOpt = document.createElement("option");
    emptyOpt.value = "";
    emptyOpt.textContent = i18n[state.lang].stt_model_placeholder || "Select STT model";
    els.sttModelSelect.appendChild(emptyOpt);
    els.sttModelSelect.value = "";
    return;
  }

  unique.forEach((model) => {
    const opt = document.createElement("option");
    opt.value = model;
    opt.textContent = model;
    els.sttModelSelect.appendChild(opt);
  });

  if (currentValue && unique.includes(currentValue)) {
    els.sttModelSelect.value = currentValue;
  } else {
    els.sttModelSelect.value = unique[0];
  }
};

const fetchSttStatus = async (options = {}) => {
  const { scanAfter = false } = options;
  if (!els.sttModelSelect) return;
  setSttStatus("stt_status_loading", "muted");
  try {
    const res = await fetch("/v1/stt/status", { headers: buildHeaders() });
    if (!res.ok) {
      throw new Error(`stt_status_failed_${res.status}`);
    }
    const data = await res.json();
    const currentModel = String(data.model_id || "").trim();
    if (currentModel) {
      setSttModelOptions([currentModel], currentModel);
    } else {
      setSttModelOptions([], "");
    }
    const warmupError = String(data.warmup_error || "").trim();
    if (warmupError) {
      setSttStatus(warmupError, "bad", {}, true);
      return;
    }
    setSttStatus("stt_status_ready", "good", { model: currentModel || "—" });
    if (scanAfter) {
      await scanSttModels({ silentErrors: true });
    }
  } catch (err) {
    console.warn("stt status fetch failed", err);
    setSttStatus("stt_status_unavailable", "bad");
  }
};

const scanSttModels = async (options = {}) => {
  const { silentErrors = false } = options;
  if (!els.sttModelSelect) return;
  setSttStatus("stt_status_scanning", "muted");
  if (els.scanSttModels) els.scanSttModels.disabled = true;
  if (els.applySttModel) els.applySttModel.disabled = true;
  try {
    const res = await fetch("/v1/stt/models", { headers: buildHeaders() });
    if (!res.ok) {
      throw new Error(`stt_models_failed_${res.status}`);
    }
    const data = await res.json();
    const models = Array.isArray(data.models) ? data.models : [];
    const currentModel = String(data.current_model || els.sttModelSelect.value || "").trim();
    setSttModelOptions(models, currentModel);
    const selectedModel = String(els.sttModelSelect.value || currentModel || "—");
    if (models.length) {
      setSttStatus("stt_status_scan_done", "good", {
        count: models.length,
        model: selectedModel,
      });
    } else {
      setSttStatus("stt_status_scan_empty", "bad", { model: selectedModel });
    }
  } catch (err) {
    console.warn("stt model scan failed", err);
    if (!silentErrors) {
      setSttStatus("stt_status_unavailable", "bad");
    }
  } finally {
    if (els.scanSttModels) els.scanSttModels.disabled = false;
    if (els.applySttModel) els.applySttModel.disabled = false;
  }
};

const applySttModel = async () => {
  if (!els.sttModelSelect) return;
  const modelId = String(els.sttModelSelect.value || "").trim();
  if (!modelId) {
    setSttStatus("stt_model_missing", "bad");
    return;
  }
  if (els.applySttModel) els.applySttModel.disabled = true;
  try {
    const res = await fetch("/v1/stt/model", {
      method: "POST",
      headers: buildHeaders(),
      body: JSON.stringify({ model_id: modelId }),
    });
    if (!res.ok) {
      const detail = await readApiErrorMessage(res, `stt_model_update_failed_${res.status}`);
      throw new Error(detail);
    }
    const data = await res.json();
    const appliedModel = String(data.model_id || modelId).trim();
    setSttModelOptions(state.sttModels.length ? state.sttModels : [appliedModel], appliedModel);
    setSttStatus("stt_status_applied", "good", { model: appliedModel || "—" });
  } catch (err) {
    console.warn("stt model switch failed", err);
    const detail = String((err && err.message) || "").trim();
    if (detail) {
      setSttStatus(detail, "bad", {}, true);
    } else {
      setSttStatus("stt_status_apply_failed", "bad");
    }
  } finally {
    if (els.applySttModel) els.applySttModel.disabled = false;
  }
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

const normalizeModelStem = (modelId) =>
  String(modelId || "")
    .trim()
    .toLowerCase()
    .split(":")[0]
    .replace(/_/g, "-");

const isEmbeddingModelId = (modelId) => {
  const normalized = normalizeModelStem(modelId);
  if (!normalized) return false;
  return EMBEDDING_MODEL_HINTS.some((hint) => normalized.includes(hint));
};

const filterChatModelIds = (models = []) =>
  (Array.isArray(models) ? models : []).filter((modelId) => !isEmbeddingModelId(modelId));

const filterEmbeddingModelIds = (models = []) =>
  (Array.isArray(models) ? models : []).filter((modelId) => isEmbeddingModelId(modelId));

const setLlmModelOptions = (models = [], preferredModel = "") => {
  if (!els.llmModelSelect) return;
  const incoming = filterChatModelIds(models);
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
  const modeCfg = getWorkModeConfig();
  const modeAllows = Boolean(modeCfg.supportsRealtime || modeCfg.supportsQuick);
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

const _nowMs = () => Date.now();

const _uiLogShouldSend = (throttleKey = "", throttleMs = UI_EVENT_THROTTLE_MS) => {
  const key = String(throttleKey || "").trim();
  if (!key) return true;
  const now = _nowMs();
  const lastTs = Number(state.uiLogLastByKey.get(key) || 0);
  if (now - lastTs < Math.max(0, Number(throttleMs) || 0)) {
    return false;
  }
  state.uiLogLastByKey.set(key, now);
  return true;
};

const logUiEvent = (eventName, payload = {}, level = "info", options = {}) => {
  const event = String(eventName || "").trim();
  if (!event) return;
  const throttleKey = String((options && options.throttleKey) || event).trim();
  const throttleMs = Number((options && options.throttleMs) || UI_EVENT_THROTTLE_MS);
  if (!_uiLogShouldSend(throttleKey, throttleMs)) return;
  const workCfg = getWorkModeConfig();
  const headers = { "Content-Type": "application/json", ...buildAuthHeaders() };
  const body = {
    event,
    level: String(level || "info").trim().toLowerCase(),
    work_mode: String((workCfg && workCfg.id) || state.workMode || "").trim(),
    meeting_id: String(state.meetingId || "").trim(),
    payload,
  };
  fetch(UI_EVENT_ENDPOINT, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
    keepalive: true,
  }).catch(() => {});
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

const forceClearCaptureLock = () => {
  try {
    localStorage.removeItem(CAPTURE_LOCK_KEY);
  } catch (_err) {
    // ignore storage failures
  }
};

const clearCaptureLockConflict = () => {
  state.captureLockConflictMeetingId = "";
  if (els.claimCaptureBtn) {
    els.claimCaptureBtn.classList.add("hidden");
    els.claimCaptureBtn.disabled = false;
  }
};

const showCaptureLockConflict = (meetingId = "") => {
  const nextMeetingId = String(meetingId || "").trim();
  if (nextMeetingId) {
    state.captureLockConflictMeetingId = nextMeetingId;
  }
  if (els.claimCaptureBtn) {
    els.claimCaptureBtn.classList.remove("hidden");
    els.claimCaptureBtn.disabled = false;
  }
};

const extractCaptureLockMeetingId = (err) => {
  const message = err && typeof err === "object" ? err.message || "" : String(err || "");
  const marker = "capture_locked_other_tab:";
  const idx = message.indexOf(marker);
  if (idx < 0) return "";
  return String(message.slice(idx + marker.length) || "").trim();
};

const isActiveMeetingStatus = (value) => {
  const normalized = String(value || "").trim().toLowerCase();
  if (!normalized) return false;
  if (normalized.includes("done")) return false;
  if (normalized.includes("failed")) return false;
  if (normalized.includes("error")) return false;
  return true;
};

const findActiveMeetingCandidate = async () => {
  const res = await fetch("/v1/meetings?limit=80", { headers: buildAuthHeaders() });
  if (!res.ok) return "";
  const body = await res.json();
  const items = Array.isArray(body.items) ? body.items : [];
  const active = items.find((item) => {
    if (!item || typeof item !== "object") return false;
    const finishedAt = String(item.finished_at || "").trim();
    if (finishedAt) return false;
    return isActiveMeetingStatus(item.status);
  });
  return String((active && active.meeting_id) || "").trim();
};

const claimCaptureInThisWindow = async () => {
  if (state.captureClaimInProgress) return;
  state.captureClaimInProgress = true;
  logUiEvent("capture_claim_start", { conflict_meeting_id: state.captureLockConflictMeetingId || "" }, "warning");
  if (els.claimCaptureBtn) {
    els.claimCaptureBtn.disabled = true;
    els.claimCaptureBtn.classList.remove("hidden");
  }
  setStatus("status_idle", "idle");
  setStatusHint("capture_claim_running", "muted");
  try {
    let meetingId = String(state.captureLockConflictMeetingId || "").trim();
    if (!meetingId) {
      const lock = readCaptureLock();
      meetingId = String((lock && lock.meetingId) || "").trim();
    }
    forceClearCaptureLock();
    if (!meetingId) {
      meetingId = await findActiveMeetingCandidate();
    }
    if (meetingId) {
      const finishRes = await fetch(`/v1/meetings/${meetingId}/finish`, {
        method: "POST",
        headers: buildHeaders(),
      });
      if (!finishRes.ok && finishRes.status !== 404) {
        throw new Error(`capture_claim_finish_failed_${finishRes.status}`);
      }
    }
    await fetchQuickRecordStatus({ silentErrors: true });
    await fetchRecords();
    clearCaptureLockConflict();
    setRecordingButtons(false);
    setStatus("status_idle", "idle");
    if (meetingId) {
      setStatusHint("capture_claim_success", "good");
      logUiEvent("capture_claim_success", { finished_meeting_id: meetingId }, "info");
    } else {
      setStatusHint("capture_claim_no_active", "muted");
      logUiEvent("capture_claim_no_active", {}, "info");
    }
  } catch (err) {
    console.warn("claim capture failed", err);
    setStatus("status_error", "error");
    setStatusHint("capture_claim_failed", "bad");
    logUiEvent(
      "capture_claim_failed",
      { error_name: String((err && err.name) || ""), error_message: String((err && err.message) || err || "") },
      "error"
    );
    if (els.claimCaptureBtn) {
      els.claimCaptureBtn.classList.remove("hidden");
      els.claimCaptureBtn.disabled = false;
    }
  } finally {
    state.captureClaimInProgress = false;
    if (els.claimCaptureBtn && !els.claimCaptureBtn.classList.contains("hidden")) {
      els.claimCaptureBtn.disabled = false;
    }
  }
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
    const hasSystemPicker = Boolean(els.deviceSelect);
    if (!hasSystemPicker && !els.micSelect) {
      return;
    }
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
    const prevValue = hasSystemPicker ? els.deviceSelect.value : "";
    const prevMicValue = els.micSelect ? els.micSelect.value : "";
    if (hasSystemPicker) {
      els.deviceSelect.innerHTML = "";
      inputs.forEach((device, index) => {
        const opt = document.createElement("option");
        opt.value = device.deviceId;
        opt.textContent = device.label || `Audio device ${index + 1}`;
        els.deviceSelect.appendChild(opt);
      });
    }
    if (!inputs.length) {
      if (hasSystemPicker) {
        const opt = document.createElement("option");
        opt.value = "";
        opt.textContent = "—";
        els.deviceSelect.appendChild(opt);
      }
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
    if (hasSystemPicker) {
      const hasPrev = inputs.some((d) => d.deviceId === prevValue);
      if (hasPrev) {
        els.deviceSelect.value = prevValue;
      } else {
        const firstVirtual = inputs.find((device) => isVirtualAudioDevice(device.label));
        if (firstVirtual && firstVirtual.deviceId) {
          els.deviceSelect.value = firstVirtual.deviceId;
        }
      }
    }

    if (els.micSelect) {
      const selectedSystemDeviceId = hasSystemPicker ? (els.deviceSelect.value || "") : "";
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
    const selectedSystem = hasSystemPicker
      ? inputs.find((device) => device.deviceId === String(els.deviceSelect.value || ""))
      : null;
    logUiEvent(
      "device_list_refreshed",
      {
        request_access: Boolean(requestAccess),
        audio_inputs_count: inputs.length,
        selected_system_device_id: hasSystemPicker ? String(els.deviceSelect.value || "") : "",
        selected_system_device_label: String((selectedSystem && selectedSystem.label) || ""),
        selected_system_is_virtual: Boolean(selectedSystem && isVirtualAudioDevice(selectedSystem.label)),
        selected_mic_device_id: String((els.micSelect && els.micSelect.value) || ""),
      },
      "debug",
      { throttleKey: "device_list_refreshed", throttleMs: 2000 }
    );
  } catch (err) {
    console.warn("device list failed", err);
    const denied = err && typeof err === "object" && err.name === "NotAllowedError";
    logUiEvent(
      "device_list_failed",
      { error_name: String((err && err.name) || ""), error_message: String((err && err.message) || err || "") },
      "error"
    );
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

const readApiErrorMessage = async (res, fallback) => {
  const fallbackText = String(fallback || "").trim() || `request_failed_${res && res.status}`;
  if (!res) return fallbackText;
  try {
    const payload = await res.json();
    if (payload && typeof payload === "object") {
      const detail = String(payload.detail || payload.error || "").trim();
      if (detail) return detail;
    }
  } catch (err) {
    // ignore json parse errors
  }
  try {
    const text = String((await res.text()) || "").trim();
    if (text) return text.slice(0, 240);
  } catch (err) {
    // ignore body read errors
  }
  return fallbackText;
};

const isTranscriptNotReadyError = (detail) =>
  /^transcript_(raw|normalized|clean)_not_ready$/i.test(String(detail || "").trim());

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
      const detail = await readApiErrorMessage(res, `llm_model_update_failed_${res.status}`);
      throw new Error(detail);
    }
    const data = await res.json();
    const appliedModel = String(data.model_id || modelId).trim();
    setLlmModelOptions(state.llmModels.length ? state.llmModels : [appliedModel], appliedModel);
    setLlmStatus("llm_status_applied", "good", { model: appliedModel || "—" });
  } catch (err) {
    console.warn("llm model switch failed", err);
    const detail = String((err && err.message) || "").trim();
    if (detail) {
      setLlmStatus(detail, "bad", {}, true);
    } else {
      setLlmStatus("llm_status_apply_failed", "bad");
    }
  } finally {
    if (els.applyLlmModel) els.applyLlmModel.disabled = false;
  }
};

const renderEmbeddingStatus = () => {
  if (!els.embeddingStatusText) return;
  const dict = i18n[state.lang] || {};
  let text = state.embeddingStatusText;
  if (!text) {
    const template = dict[state.embeddingStatusKey] || state.embeddingStatusKey;
    text = formatText(template, state.embeddingStatusParams || {});
  }
  els.embeddingStatusText.textContent = text;
  els.embeddingStatusText.className = `hint llm-status ${state.embeddingStatusStyle || "muted"}`;
};

const setEmbeddingStatus = (
  statusKeyOrText = "embedding_status_loading",
  style = "muted",
  params = {},
  isRaw = false
) => {
  state.embeddingStatusStyle = style || "muted";
  state.embeddingStatusParams = params || {};
  if (isRaw) {
    state.embeddingStatusText = String(statusKeyOrText || "");
    state.embeddingStatusKey = "";
  } else {
    state.embeddingStatusKey = String(statusKeyOrText || "");
    state.embeddingStatusText = "";
  }
  renderEmbeddingStatus();
};

const setEmbeddingModelOptions = (models = [], preferredModel = "") => {
  if (!els.embeddingModelSelect) return;
  const incoming = filterEmbeddingModelIds(models);
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

  const currentValue = String(preferredModel || els.embeddingModelSelect.value || "").trim();
  state.embeddingModels = unique;

  els.embeddingModelSelect.innerHTML = "";
  if (!unique.length) {
    const emptyOpt = document.createElement("option");
    emptyOpt.value = "";
    emptyOpt.textContent = i18n[state.lang].embedding_model_placeholder || "Select embedding model";
    els.embeddingModelSelect.appendChild(emptyOpt);
    els.embeddingModelSelect.value = "";
    return;
  }

  unique.forEach((model) => {
    const opt = document.createElement("option");
    opt.value = model;
    opt.textContent = model;
    els.embeddingModelSelect.appendChild(opt);
  });

  if (currentValue && unique.includes(currentValue)) {
    els.embeddingModelSelect.value = currentValue;
  } else {
    els.embeddingModelSelect.value = unique[0];
  }
};

const fetchEmbeddingStatus = async (options = {}) => {
  const { scanAfter = false } = options;
  if (!els.embeddingModelSelect) return;
  setEmbeddingStatus("embedding_status_loading", "muted");
  try {
    const res = await fetch("/v1/llm/embeddings/status", { headers: buildHeaders() });
    if (!res.ok) {
      throw new Error(`embedding_status_failed_${res.status}`);
    }
    const data = await res.json();
    const currentModel = String(data.model_id || "").trim();
    if (currentModel) {
      setEmbeddingModelOptions([currentModel], currentModel);
    } else {
      setEmbeddingModelOptions([], "");
    }
    const available = Boolean(data.available);
    const message = String(data.message || "").trim();
    if (available) {
      if (message) {
        setEmbeddingStatus(message, "good", {}, true);
      } else {
        setEmbeddingStatus("embedding_status_ready", "good", { model: currentModel || "—" });
      }
    } else {
      setEmbeddingStatus(message || "embedding_status_unavailable", "bad", {}, Boolean(message));
    }
    if (scanAfter) {
      await scanEmbeddingModels({ silentErrors: true });
    }
  } catch (err) {
    console.warn("embedding status fetch failed", err);
    setEmbeddingStatus("embedding_status_unavailable", "bad");
  }
};

const scanEmbeddingModels = async (options = {}) => {
  const { silentErrors = false } = options;
  if (!els.embeddingModelSelect) return;
  setEmbeddingStatus("embedding_status_scanning", "muted");
  if (els.scanEmbeddingModels) els.scanEmbeddingModels.disabled = true;
  if (els.applyEmbeddingModel) els.applyEmbeddingModel.disabled = true;
  try {
    const res = await fetch("/v1/llm/embeddings/models", { headers: buildHeaders() });
    if (!res.ok) {
      throw new Error(`embedding_models_failed_${res.status}`);
    }
    const data = await res.json();
    const models = Array.isArray(data.models) ? data.models : [];
    const currentModel = String(data.current_model || els.embeddingModelSelect.value || "").trim();
    setEmbeddingModelOptions(models, currentModel);
    const selectedModel = String(els.embeddingModelSelect.value || currentModel || "—");
    if (models.length) {
      setEmbeddingStatus("embedding_status_scan_done", "good", {
        count: models.length,
        model: selectedModel,
      });
    } else {
      setEmbeddingStatus("embedding_status_scan_empty", "bad", { model: selectedModel });
    }
  } catch (err) {
    console.warn("embedding model scan failed", err);
    if (!silentErrors) {
      setEmbeddingStatus("embedding_status_unavailable", "bad");
    }
  } finally {
    if (els.scanEmbeddingModels) els.scanEmbeddingModels.disabled = false;
    if (els.applyEmbeddingModel) els.applyEmbeddingModel.disabled = false;
  }
};

const applyEmbeddingModel = async () => {
  if (!els.embeddingModelSelect) return;
  const modelId = String(els.embeddingModelSelect.value || "").trim();
  if (!modelId) {
    setEmbeddingStatus("embedding_model_missing", "bad");
    return;
  }
  if (els.applyEmbeddingModel) els.applyEmbeddingModel.disabled = true;
  try {
    const res = await fetch("/v1/llm/embeddings/model", {
      method: "POST",
      headers: buildHeaders(),
      body: JSON.stringify({ model_id: modelId }),
    });
    if (!res.ok) {
      const detail = await readApiErrorMessage(res, `embedding_model_update_failed_${res.status}`);
      throw new Error(detail);
    }
    const data = await res.json();
    const appliedModel = String(data.model_id || modelId).trim();
    setEmbeddingModelOptions(
      state.embeddingModels.length ? state.embeddingModels : [appliedModel],
      appliedModel
    );
    setEmbeddingStatus("embedding_status_applied", "good", { model: appliedModel || "—" });
  } catch (err) {
    console.warn("embedding model switch failed", err);
    const detail = String((err && err.message) || "").trim();
    if (detail) {
      setEmbeddingStatus(detail, "bad", {}, true);
    } else {
      setEmbeddingStatus("embedding_status_apply_failed", "bad");
    }
  } finally {
    if (els.applyEmbeddingModel) els.applyEmbeddingModel.disabled = false;
  }
};

const normalizeWorkMode = (value) => {
  const raw = String(value || "").trim();
  return WORK_MODE_CONFIGS[raw] ? raw : "link_fallback";
};

const getWorkModeConfig = (value = state.workMode) => {
  const mode = normalizeWorkMode(value);
  return WORK_MODE_CONFIGS[mode] || WORK_MODE_CONFIGS.link_fallback;
};

const _normalizeFlowStep = (step) => {
  const raw = String(step || "").trim().toLowerCase();
  if (raw === "capture" || raw === "process" || raw === "results") return raw;
  return "mode";
};

const setFlowStep = (step) => {
  const normalized = _normalizeFlowStep(step);
  state.flowStep = normalized;
  (els.flowSteps || []).forEach((el) => {
    if (!el || !el.dataset) return;
    const target = _normalizeFlowStep(el.dataset.flowStep || "");
    el.classList.toggle("active", target === normalized);
  });
};

const setResultsTab = (tab, options = {}) => {
  const { setFlow = false } = options;
  const target = String(tab || "").trim().toLowerCase() === "llm"
    ? "llm"
    : String(tab || "").trim().toLowerCase() === "transcript"
    ? "transcript"
    : "audio";
  state.resultsTab = target;
  (els.resultTabButtons || []).forEach((btn) => {
    if (!btn || !btn.dataset) return;
    const key = String(btn.dataset.resultsTab || "").trim().toLowerCase();
    btn.classList.toggle("active", key === target);
  });
  (els.resultTabPanes || []).forEach((pane) => {
    if (!pane || !pane.dataset) return;
    const key = String(pane.dataset.resultsPane || "").trim().toLowerCase();
    const active = key === target;
    pane.classList.toggle("active", active);
    pane.classList.toggle("hidden", !active);
  });
  if (setFlow) {
    setFlowStep(target === "audio" ? "results" : "process");
  }
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
    };
  }
  return {
    url: els.quickRecordUrl,
    duration: els.quickRecordDuration,
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
  [quickControls.url, quickControls.duration].forEach((el) => {
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

  if (!state.captureStopper && !state.isCountingDown && !isQuickFlowActive() && !state.isUploading) {
    setFlowStep("mode");
  }
  syncCheckSignalButton();
  updateCaptureUi();
  setQuickButtonsByStatus(state.quickStatusKey || "quick_record_state_idle");
  if (!recordingEnabled) {
    setRecordingButtons(false);
  }
  if (els.runDiagnostics && !state.signalCheckInProgress) {
    els.runDiagnostics.disabled = !(realtimeEnabled || quickEnabled);
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

const isAbortRequestError = (err) => {
  if (!err) return false;
  const name = String((err && err.name) || "").trim().toLowerCase();
  if (name === "aborterror") return true;
  const message = String((err && err.message) || err || "").trim().toLowerCase();
  return message.includes("abort");
};

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
  const selectedDeviceId =
    mode === "system" && els.deviceSelect ? els.deviceSelect.value || "" : "";
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
      setSignal("signal_no_audio");
      console.warn("screen capture started without audio track");
    }
  } else {
    const deviceId = els.deviceSelect ? els.deviceSelect.value : "";
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
  if (message.includes("link_mode_url_missing")) return "err_link_mode_url_missing";
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
  if (state.captureStopper && getCaptureMode() === "system") {
    const now = Date.now();
    const elapsedMs = state.monitor.startedAt ? now - Number(state.monitor.startedAt || 0) : 0;
    const levelsVeryLow = mixedLevel < 0.02 && systemLevel < 0.02;
    if (elapsedMs > 9000 && levelsVeryLow && now - Number(state.warnedSystemLowAt || 0) > 18000) {
      state.warnedSystemLowAt = now;
      const currentHint = String(state.statusHintKey || "");
      if (!currentHint || currentHint === "hint_recording_record_first") {
        setStatusHint("warn_system_level_low", "muted");
      }
      logUiEvent(
        "capture_system_level_low",
        {
          mixed: Number(mixedLevel.toFixed(4)),
          system: Number(systemLevel.toFixed(4)),
          mic: Number(micLevel.toFixed(4)),
          elapsed_ms: elapsedMs,
          selected_device: String((els.deviceSelect && els.deviceSelect.value) || ""),
        },
        "warning",
        { throttleKey: "capture_system_level_low", throttleMs: 12000 }
      );
    }
  }
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
    quality_profile: TRANSCRIPT_QUALITY_PROFILE,
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
  if (state.chunkCount <= 3 || state.chunkCount % 20 === 0) {
    logUiEvent(
      "capture_chunk_sent",
      {
        seq: Number(payload.seq),
        source_track: track,
        mixed_level: Number(payload.mixed_level || 0),
        system_level: Number(payload.system_level || 0),
        mic_level: Number(payload.mic_level || 0),
        codec: String(payload.codec || ""),
      },
      "debug",
      { throttleKey: `chunk:${payload.seq}`, throttleMs: 1 }
    );
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
  state.warnedSystemLowAt = 0;
  state.lastAckSeq = -1;
  state.wsHasServerActivity = false;
  state.wsBootstrapDeadlineMs = 0;
  state.wsLastServerActivityMs = 0;
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
};

const getLinkModeMeetingUrl = () => String((els.quickRecordUrl && els.quickRecordUrl.value) || "").trim();

const isHttpMeetingUrl = (url) =>
  typeof url === "string" && (url.startsWith("http://") || url.startsWith("https://"));

const openMeetingUrlInBrowser = (url) => {
  if (!isHttpMeetingUrl(url)) return false;
  try {
    const ref = window.open(url, "_blank", "noopener,noreferrer");
    return Boolean(ref);
  } catch (_err) {
    return false;
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
  setFlowStep("process");
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
    setTranscriptUiState("waiting");
    if (hasTranscriptContent()) {
      setFlowStep("results");
    }
  } catch (err) {
    setTranscriptUiState("empty");
    console.warn("load final transcripts failed", err);
    setFlowStep("mode");
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
          quality_profile: payload.quality_profile || TRANSCRIPT_QUALITY_PROFILE,
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
  clearCaptureLockConflict();
  setFlowStep("capture");
  const workCfg = getWorkModeConfig();
  logUiEvent(
    "recording_start_click",
    {
      work_mode: workCfg.id,
      capture_mode: getCaptureMode(),
      selected_device: String((els.deviceSelect && els.deviceSelect.value) || ""),
      include_mic: Boolean(els.includeMic && els.includeMic.checked),
      selected_mic: String((els.micSelect && els.micSelect.value) || ""),
    },
    "info"
  );
  if (!workCfg.supportsRealtime) {
    setStatus("status_error", "error");
    setStatusHint("err_work_mode_realtime_only", "bad");
    setRecordingButtons(false);
    setFlowStep("mode");
    return;
  }
  const captureLock = isCaptureLockedByOtherTab();
  if (captureLock.locked) {
    logUiEvent(
      "recording_blocked_capture_lock",
      { lock_meeting_id: String(captureLock.meetingId || "") },
      "warning"
    );
    showCaptureLockConflict(captureLock.meetingId || "");
    setStatus("status_error", "error");
    setStatusHint("err_capture_locked_other_tab", "bad");
    setRecordingButtons(false);
    setFlowStep("mode");
    return;
  }
  setRecordingButtons(true);
  writeCaptureLock("");
  startCaptureLockHeartbeat();
  resetSessionState();
  els.countdownValue.textContent = "9s";
  const captureMode = getCaptureMode();
  const linkModeActive = workCfg.id === "link_fallback";
  const linkMeetingUrl = linkModeActive ? getLinkModeMeetingUrl() : "";
  let interviewMeta = null;

  try {
    if (linkModeActive) {
      if (!isHttpMeetingUrl(linkMeetingUrl)) {
        throw new Error("link_mode_url_missing");
      }
      setStatusHint("link_mode_opening", "muted");
      const opened = openMeetingUrlInBrowser(linkMeetingUrl);
      if (!opened) {
        setStatusHint("link_mode_open_failed_popup", "muted");
      }
      await sleepMs(220);
    }
    interviewMeta = validateInterviewMetadata();
    if (captureMode === "system" && !(els.deviceSelect && els.deviceSelect.value)) {
      throw new Error("no_device_selected");
    }
    await runCapturePreflight(captureMode);
    await ensureStream(captureMode, { force: true });
    if (!state.stream || !state.stream.getAudioTracks().length) {
      throw new Error("preflight_no_audio_track");
    }
    await buildAudioMeter(captureMode, { force: false });
    startMeter();

    await startCountdown(9);
  } catch (err) {
    releasePreparedCapture();
    stopCaptureLockHeartbeat();
    setStatus("status_idle", "idle");
    setStatusHint("");
    setRecordingButtons(false);
    if (String(err || "").includes("countdown_cancelled")) {
      logUiEvent("recording_start_cancelled", {}, "info");
      setFlowStep("mode");
      return;
    }
    clearCaptureLockConflict();
    setStatus("status_error", "error");
    setStatusHint(mapStartError(err, captureMode), "bad");
    logUiEvent(
      "recording_start_prepare_failed",
      {
        error_name: String((err && err.name) || ""),
        error_message: String((err && err.message) || err || ""),
        capture_mode: captureMode,
      },
      "error"
    );
    setFlowStep("mode");
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
    } else if (captureMode === "screen" && state.screenAudioMissing) {
      setSignal(state.micAdded ? "signal_low" : "signal_no_audio");
      setStatusHint(state.micAdded ? "warn_screen_audio_mic_only" : "err_screen_audio_missing", "bad");
    } else if (els.includeMic && els.includeMic.checked && !state.micAdded) {
      setStatusHint("warn_mic_not_added", "bad");
    } else {
      setStatusHint("hint_recording_record_first", "good");
    }
  } catch (err) {
    console.error("start recording failed", err);
    const hintKey = mapStartError(err, captureMode);
    if (hintKey === "err_capture_locked_other_tab") {
      showCaptureLockConflict(extractCaptureLockMeetingId(err));
    } else {
      clearCaptureLockConflict();
    }
    setStatus("status_error", "error");
    setStatusHint(hintKey, "bad");
    logUiEvent(
      "recording_start_failed",
      {
        hint_key: hintKey,
        error_name: String((err && err.name) || ""),
        error_message: String((err && err.message) || err || ""),
        capture_mode: captureMode,
      },
      "error"
    );
    await stopRecording({ preserveStatus: true, preserveHint: true, forceFinish: true });
    throw err;
  }
};

const stopRecording = async (options = {}) => {
  const { preserveStatus = false, preserveHint = false, forceFinish = false } = options;
  const wasRecording = Boolean(state.captureStopper);
  const wasCountingDown = Boolean(state.isCountingDown);
  const activeMeetingId = state.meetingId;
  if (activeMeetingId) {
    setFlowStep("process");
  }
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
  // Stop local media/meter immediately on user Stop; backend may still finalize/save MP3.
  if (state.stream) {
    releasePreparedCapture();
  } else {
    closeAudioMeter();
  }
  setRecordingButtons(false);
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
    setTranscriptUiState("waiting");
    showBusyOverlay("busy_finish_title", "busy_finish_text");
    updateBusyOverlayProgress(10);
    try {
      await fetch(`/v1/meetings/${activeMeetingId}/finish`, {
        method: "POST",
        headers: buildHeaders(),
      });
      updateBusyOverlayProgress(72);
      await fetchRecords({ refreshCompare: false });
      updateBusyOverlayProgress(92);
      setTranscriptUiState("waiting");
      setResultsTab("audio");
      setFlowStep("results");
      finishedOk = true;
      updateBusyOverlayProgress(100);
    } catch (err) {
      setTranscriptUiState("waiting");
      setFlowStep("mode");
      // ignore and keep local UI responsive
    } finally {
      hideBusyOverlay();
    }
  }
  if (shouldOfferMp3 && finishedOk) {
    await saveMeetingMp3(activeMeetingId, { askUser: true, syncRecordName: true });
  }
  if (!preserveStatus) {
    setStatus("status_idle", "idle");
  }
  if (!preserveHint) {
    setStatusHint("");
  }
  els.countdownValue.textContent = preserveStatus ? "0s" : "—";
  logUiEvent(
    "recording_stopped",
    {
      meeting_id: String(activeMeetingId || ""),
      finished_ok: finishedOk,
      force_finish: Boolean(forceFinish),
      chunks: Number(state.chunkCount || 0),
      levels_last: {
        mixed: Number(state.meterLevels.mixed || 0),
        system: Number(state.meterLevels.system || 0),
        mic: Number(state.meterLevels.mic || 0),
      },
    },
    finishedOk ? "info" : "warning",
    { throttleKey: `recording_stopped:${activeMeetingId || "none"}`, throttleMs: 1 }
  );
  state.meetingId = null;
  els.meetingIdText.textContent = "—";
  state.stopRequested = false;
  if (!finishedOk && !state.captureStopper && !state.isCountingDown) {
    setFlowStep("mode");
  }
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

const runQuickAudioProbe = async (options = {}) => {
  const { forStart = false } = options;
  const dict = i18n[state.lang] || {};
  if (els.runDiagnostics) {
    els.runDiagnostics.disabled = true;
  }
  setCheckSignalBusy(true);
  _diagMarkAllMuted();
  setDiagItemStatus(els.diagAudio, "running");
  setDiagItemStatus(els.diagSystem, "running");
  setDiagItemStatus(els.diagMic, "muted", dict.diag_skip_not_required || "not required");
  setDiagItemStatus(els.diagStt, "running");
  setDiagItemStatus(els.diagLlm, "muted", dict.diag_skip_not_required || "not required");
  setDiagHint("diag_hint_running", "muted");
  try {
    const res = await fetch(`/v1/quick-record/probe?duration_sec=${QUICK_PROBE_DURATION_SEC}`, {
      headers: buildHeaders(),
    });
    if (!res.ok) {
      throw new Error(`quick_probe_failed_${res.status}`);
    }
    const body = await res.json();
    const probe = body && body.probe ? body.probe : {};
    const signalOk = Boolean(probe.signal_ok);
    const detail = String(probe.detail || "").trim();
    const accessOk = !detail;
    const peak = Number(probe.peak || 0);
    const peakPercent = Number.isFinite(Number(probe.peak_percent))
      ? Number(probe.peak_percent)
      : Math.round(Math.max(0, Math.min(1, peak)) * 100);
    const device = String(probe.device || "—");
    setDiagItemStatus(els.diagAudio, accessOk ? "good" : "bad");
    setDiagItemStatus(els.diagStt, accessOk ? "good" : "bad");
    if (signalOk && accessOk) {
      setDiagItemStatus(els.diagSystem, "good");
      setDiagHint("diag_hint_ok", "good");
      setSignal(peak >= 0.02 ? "signal_ok" : "signal_low");
      setStatusHint(
        formatText(dict.quick_probe_signal_ok || "Signal detected ({peak}%). Device: {device}.", {
          peak: String(Math.round(peakPercent)),
          device,
        }),
        "good",
        true
      );
    } else {
      setDiagItemStatus(els.diagSystem, "bad");
      setDiagHint(accessOk ? "diag_hint_levels_low" : "diag_hint_fail", accessOk ? "muted" : "bad");
      setSignal("signal_no_audio");
      if (detail) {
        setStatusHint(
          formatText(dict.quick_probe_failed || "Quick capture probe failed: {detail}", { detail }),
          "bad",
          true
        );
      } else {
        setStatusHint(
          formatText(dict.quick_probe_no_signal || "No signal detected. Device: {device}.", { device }),
          "bad",
          true
        );
      }
    }
    const criticalPassed = Boolean(signalOk);
    state.diagnosticsLast = {
      criticalPassed,
      systemOk: signalOk,
      micOk: false,
      micSkipped: true,
      mp3Ready: signalOk,
      ts: Date.now(),
    };
    if (forStart && !criticalPassed) {
      throw new Error("diagnostics_failed");
    }
    return { criticalPassed, mp3Ready: signalOk, peak };
  } finally {
    if (els.runDiagnostics) {
      els.runDiagnostics.disabled = false;
    }
    setCheckSignalBusy(false);
  }
};

const checkSignal = async () => {
  if (state.signalCheckInProgress) return;
  const workCfg = getWorkModeConfig();
  if (!workCfg.supportsRealtime) {
    if (workCfg.supportsQuick) {
      try {
        await runQuickAudioProbe({ forStart: false });
      } catch (err) {
        console.warn("quick signal check failed", err);
      }
      return;
    }
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
    if (mode === "system" && !(els.deviceSelect && els.deviceSelect.value)) {
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
  const workCfg = getWorkModeConfig();
  if (!workCfg.supportsRealtime) {
    if (workCfg.supportsQuick) {
      return await runQuickAudioProbe({ forStart });
    }
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
  logUiEvent(
    forStart ? "capture_diagnostics_for_start" : "capture_diagnostics_manual",
    {
      critical_passed: criticalPassed,
      system_ok: systemOk,
      mic_ok: micOk,
      mic_skipped: micSkipped,
      mp3_ready: mp3Ready,
      capture_mode: mode,
      levels: {
        mixed: Number(state.meterLevels.mixed || 0),
        system: Number(state.meterLevels.system || 0),
        mic: Number(state.meterLevels.mic || 0),
      },
    },
    criticalPassed ? "info" : "warning",
    { throttleKey: `diag:${forStart ? "start" : "manual"}`, throttleMs: 1200 }
  );

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
  [quickControls.url, quickControls.duration].forEach((el) => {
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
  const dict = i18n[state.lang] || {};
  if (!job) {
    hideQuickStopOverlay();
    state.quickJobId = null;
    setQuickStatus("quick_record_state_idle", "muted");
    setQuickButtonsByStatus("idle");
    setTranscriptUiState(hasTranscriptContent() ? "ready" : "waiting");
    if (quickPrimaryMode) {
      setStatus("status_idle", "idle");
      clearCaptureLockConflict();
      if (
        state.statusHintKey === "err_media_not_readable" ||
        state.statusHintKey === "err_capture_locked_other_tab" ||
        state.statusHintKey === "err_diagnostics_failed"
      ) {
        setStatusHint("");
      }
    }
    clearQuickPollTimer();
    return;
  }

  state.quickJobId = String(job.job_id || "");
  const jobId = String(job.job_id || "").trim();
  const status = String(job.status || "").trim().toLowerCase();
  if (status === "queued" || status === "running") {
    hideQuickStopOverlay();
    setQuickStatus("quick_record_state_running", "good");
    setQuickButtonsByStatus(status);
    setTranscriptUiState("recording");
    const elapsed = Number(job.elapsed_sec || 0);
    const peak = Number(job.audio_peak || 0);
    const device = String(job.input_device || "").trim() || "—";
    const peakPercent = Math.round(Math.max(0, Math.min(1, peak)) * 100);
    if (elapsed < QUICK_PROBE_DURATION_SEC) {
      const left = Math.max(0, QUICK_PROBE_DURATION_SEC - elapsed);
      setQuickHint("quick_record_hint_running_probe_wait", "muted", false, {
        seconds: String(left),
      });
      if (quickPrimaryMode && !apiMode) {
        setStatusHint(
          formatText(
            dict.quick_record_hint_running_probe_wait ||
              "Recording is in progress. Initial signal probe in {seconds} sec.",
            { seconds: String(left) }
          ),
          "muted",
          true
        );
      }
    } else if (peak >= QUICK_SIGNAL_MIN_PEAK) {
      setQuickHint("quick_record_hint_running_probe_ok", "good", false, {
        peak: String(peakPercent),
        device,
      });
      if (quickPrimaryMode && !apiMode) {
        setStatusHint(
          formatText(
            dict.quick_record_hint_running_probe_ok ||
              "Recording is in progress: signal detected ({peak}%). Device: {device}.",
            { peak: String(peakPercent), device }
          ),
          "good",
          true
        );
      }
    } else {
      setQuickHint("quick_record_hint_running_probe_fail", "bad");
      if (quickPrimaryMode && !apiMode) {
        setStatusHint(
          dict.quick_record_hint_running_probe_fail ||
            "Recording is in progress, but signal is still low. Check audio routing/meeting output.",
          "bad",
          true
        );
      }
    }
    if (quickPrimaryMode) {
      clearCaptureLockConflict();
      setStatus("status_recording", "recording");
      if (apiMode) {
        setStatusHint("api_record_started", "good");
      } else if (state.statusHintKey === "api_record_failed") {
        setStatusHint("");
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
    showQuickStopOverlay();
    setQuickStatus("quick_record_state_stopping", "muted");
    setQuickButtonsByStatus(status);
    setTranscriptUiState("recording");
    if (quickPrimaryMode) {
      setStatus("status_recording", "recording");
      if (apiMode) {
        setStatusHint("api_record_stopped", "muted");
      } else {
        setStatusHint("quick_record_state_stopping", "muted");
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
    hideQuickStopOverlay();
    setQuickStatus("quick_record_state_completed", "good");
    setQuickButtonsByStatus(status);
    setTranscriptUiState(hasTranscriptContent() ? "ready" : "empty");
    if (quickPrimaryMode) {
      setStatus("status_idle", "idle");
      if (apiMode) {
        setStatusHint("api_record_completed", "good");
      } else {
        setStatusHint(
          formatText(dict.quick_record_hint_completed || "Quick recording completed. MP3: {path}", {
            path: String(job.mp3_path || "—"),
          }),
          "good",
          true
        );
      }
    }
    setQuickHint("quick_record_hint_completed", "good", false, {
      path: String(job.mp3_path || "—"),
    });
    const firstCompletedEvent = Boolean(jobId) && state.quickCompletedHandledJobId !== jobId;
    if (firstCompletedEvent) {
      state.quickCompletedHandledJobId = jobId;
      const completionMeetingId = String(
        (job && (job.local_meeting_id || job.agent_meeting_id)) || ""
      ).trim();
      void (async () => {
        await fetchRecords();
        if (!completionMeetingId || !els.recordsSelect) return;
        const hasOption = Array.from(els.recordsSelect.options || []).some(
          (opt) => String((opt && opt.value) || "").trim() === completionMeetingId
        );
        if (!hasOption) return;
        els.recordsSelect.value = completionMeetingId;
        state.meetingId = completionMeetingId;
        state.reportMeetingSelection.raw = completionMeetingId;
        state.reportMeetingSelection.clean = completionMeetingId;
        syncResultsState();
        await saveMeetingMp3(completionMeetingId, { askUser: true, syncRecordName: true });
      })();
    }
    return;
  }

  if (status === "failed") {
    hideQuickStopOverlay();
    setQuickStatus("quick_record_state_failed", "bad");
    setQuickButtonsByStatus(status);
    setTranscriptUiState("empty");
    if (quickPrimaryMode) {
      setStatus("status_error", "error");
      if (apiMode) {
        setStatusHint("api_record_failed", "bad");
      } else {
        setStatusHint(
          formatText(dict.quick_record_hint_failed || "Quick recording failed: {error}", {
            error: String(job.error || "unknown"),
          }),
          "bad",
          true
        );
      }
    }
    setQuickHint("quick_record_hint_failed", "bad", false, {
      error: String(job.error || "unknown"),
    });
    return;
  }

  hideQuickStopOverlay();
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
    hideQuickStopOverlay();
    clearQuickPollTimer();
    if (!silentErrors) {
      setQuickHint("quick_record_hint_start_failed", "bad");
    }
  }
};

const startQuickRecord = async () => {
  const workCfg = getWorkModeConfig();
  setFlowStep("capture");
  hideQuickStopOverlay();
  clearCaptureLockConflict();
  logUiEvent(
    "quick_record_start_click",
    {
      work_mode: workCfg.id,
      is_api_mode: workCfg.id === "api_upload",
    },
    "info"
  );
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

  const transcribe = false;
  const uploadToAgent = apiMode ? true : false;
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
      let detail = "";
      try {
        const payload = await res.json();
        detail = String((payload && payload.detail) || "").trim();
      } catch (_err) {
        detail = "";
      }
      throw new Error(detail ? `quick_start_failed_${res.status}_${detail}` : `quick_start_failed_${res.status}`);
    }
    const body = await res.json();
    setQuickHint("quick_record_hint_started", "good");
    logUiEvent(
      "quick_record_started",
      {
        job_id: String((body && body.job && body.job.job_id) || ""),
        work_mode: workCfg.id,
      },
      "info"
    );
    if (apiMode) {
      setStatusHint("api_record_started", "good");
    }
    applyQuickJobStatus(body.job || null);
  } catch (err) {
    console.warn("quick record start failed", err);
    setQuickHint("quick_record_hint_start_failed", "bad");
    const raw = String((err && err.message) || "").trim();
    if (raw) {
      setQuickHint(`${(i18n[state.lang] || {}).quick_record_hint_start_failed || "Failed to start quick recorder."} (${raw})`, "bad", true);
    }
    logUiEvent(
      "quick_record_start_failed",
      { error_name: String((err && err.name) || ""), error_message: String((err && err.message) || err || "") },
      "error"
    );
    if (apiMode) {
      setStatusHint("api_record_failed", "bad");
    }
    setFlowStep("mode");
    await fetchQuickRecordStatus({ silentErrors: true });
  } finally {
    if (els.quickRecordStart && (!els.quickRecordStop || els.quickRecordStop.disabled)) {
      els.quickRecordStart.disabled = false;
    }
  }
};

const stopQuickRecord = async () => {
  const currentMode = getWorkModeConfig();
  setFlowStep("process");
  const apiMode = currentMode.id === "api_upload";
  if (!currentMode.supportsQuick) {
    setQuickHint("err_work_mode_quick_only", "bad");
    return;
  }
  try {
    showQuickStopOverlay();
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
    setFlowStep("results");
    applyQuickJobStatus(body.job || null);
  } catch (err) {
    hideQuickStopOverlay();
    console.warn("quick record stop failed", err);
    setQuickHint("quick_record_hint_stop_failed", "bad");
    if (apiMode) {
      setStatusHint("api_record_failed", "bad");
    }
    setFlowStep("mode");
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
  if (els.sttModelSelect) {
    els.sttModelSelect.disabled = sttControlsLocked;
  }
  if (els.scanSttModels) {
    els.scanSttModels.disabled = sttControlsLocked;
  }
  if (els.applySttModel) {
    els.applySttModel.disabled = sttControlsLocked;
  }
  if (els.runDiagnostics && !state.signalCheckInProgress) {
    els.runDiagnostics.disabled = !(realtimeEnabled || Boolean(cfg.supportsQuick));
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

const formatMeetingCreatedAtMsk = (isoValue) => {
  const raw = String(isoValue || "").trim();
  if (!raw) return "";
  const dt = new Date(raw);
  if (!Number.isFinite(dt.valueOf())) return "";
  const locale = state.lang === "ru" ? "ru-RU" : "en-GB";
  const formatter = new Intl.DateTimeFormat(locale, {
    timeZone: MEETING_TIME_ZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
  const base = formatter.format(dt);
  return state.lang === "ru" ? `${base} МСК` : `${base} MSK`;
};

const formatMeetingOptionLabel = (meta) => {
  if (!meta || typeof meta !== "object") return "—";
  const display = String(meta.display_name || meta.meeting_id || "").trim() || "record";
  const createdRaw = String(meta.created_at || "").trim();
  const createdLabel = formatMeetingCreatedAtMsk(createdRaw);
  if (!createdLabel) return display;
  return `${display} (${createdLabel})`;
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
  const source = state.resultsSource === "raw" ? "raw" : "clean";
  if (els.resultsRaw) {
    els.resultsRaw.classList.toggle("active", source === "raw");
  }
  if (els.resultsClean) {
    els.resultsClean.classList.toggle("active", source === "clean");
  }
  const filename = buildFilename({ kind: "report", source, fmt: "txt" });
  if (els.resultFileName) {
    els.resultFileName.textContent = filename;
  }
  if (els.reportNameInput) {
    const currentName = String(els.reportNameInput.value || "").trim();
    if (!currentName) {
      els.reportNameInput.value = source === "clean" ? "report_clean" : "report_raw";
    }
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
  renderLlmArtifactWorkspace();
  renderRagWorkspace();
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

const fetchRecords = async (options = {}) => {
  const { refreshCompare = false } = options || {};
  try {
    const res = await fetch("/v1/meetings?limit=200", { headers: buildHeaders() });
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
      if (refreshCompare) {
        void fetchComparison();
      }
      if (!state.captureStopper && !state.isCountingDown && !isQuickFlowActive() && !state.isUploading) {
        setFlowStep("mode");
      }
      return;
    }
    items.forEach((item) => {
      const meetingId = String(item.meeting_id || "").trim();
      const displayName = String(item.display_name || "").trim() || meetingId;
      const artifacts = item && typeof item.artifacts === "object" ? item.artifacts : {};
      const ragIndexStatus = item && typeof item.rag_index_status === "object" ? item.rag_index_status : {};
      state.recordsMeta.set(meetingId, {
        meeting_id: meetingId,
        display_name: displayName,
        record_index: Number(item.record_index || 0),
        created_at: String(item.created_at || ""),
        audio_mp3: Boolean(item.audio_mp3),
        artifacts,
        rag_index_status: ragIndexStatus,
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
    if (refreshCompare) {
      void fetchComparison();
    }
    if (!state.captureStopper && !state.isCountingDown && !isQuickFlowActive() && !state.isUploading) {
      setFlowStep("results");
    }
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

const _stripFileExt = (value, ext = "") => {
  const suffix = String(ext || "").trim().toLowerCase();
  const text = String(value || "").trim();
  if (!suffix) return text.replace(/\.[a-z0-9]{1,8}$/i, "");
  return text.replace(new RegExp(`\\.${suffix}$`, "i"), "");
};

const ensureNamedReportInput = (inputEl, source = "raw") => {
  const fallbackBase = source === "clean" ? "clean_transcript" : "raw_transcript";
  const current = String((inputEl && inputEl.value) || "").trim();
  if (current) return current;
  const dict = i18n[state.lang] || {};
  const question = dict.prompt_report_name || "Enter report filename:";
  const suggested = fallbackBase;
  const entered = window.prompt(question, suggested);
  if (entered == null) return "";
  const normalized = normalizeFilenameWithExt(entered, fallbackBase, "txt");
  const baseOnly = _stripFileExt(normalized, "txt");
  if (inputEl) {
    inputEl.value = baseOnly;
  }
  return baseOnly;
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

const saveLocalBlob = async (filename, blob, options = {}) => {
  const { preferPicker = false } = options || {};
  try {
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
    console.warn("save local blob failed", err);
    return { ok: false, status: 0 };
  }
};

const downloadArtifact = async (url, filename, options = {}) => {
  const { preferPicker = false, onProgress = null, signal = null } = options;
  try {
    const res = await fetch(url, { headers: buildAuthHeaders(), signal: signal || undefined });
    if (!res.ok) {
      return { ok: false, status: res.status };
    }
    let blob = null;
    const totalBytes = Number(res.headers.get("content-length") || 0);
    if (
      res.body &&
      Number.isFinite(totalBytes) &&
      totalBytes > 0 &&
      typeof onProgress === "function"
    ) {
      const reader = res.body.getReader();
      const chunks = [];
      let loaded = 0;
      onProgress(6);
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        if (value && value.byteLength) {
          chunks.push(value);
          loaded += value.byteLength;
          const pct = Math.max(6, Math.min(99, Math.round((loaded / totalBytes) * 100)));
          onProgress(pct);
        }
      }
      blob = new Blob(chunks, {
        type: res.headers.get("content-type") || "application/octet-stream",
      });
    } else {
      blob = await res.blob();
      if (typeof onProgress === "function") {
        onProgress(95);
      }
    }
    return await saveLocalBlob(filename, blob, { preferPicker });
  } catch (err) {
    if (isAbortRequestError(err)) {
      return { ok: false, status: 0, aborted: true };
    }
    console.warn("download failed", err);
    return { ok: false, status: 0 };
  }
};

const saveMeetingMp3 = async (meetingId, options = {}) => {
  const { askUser = false, syncRecordName = false } = options;
  if (!meetingId) return false;
  const dict = i18n[state.lang] || {};
  let filename = buildFilename({ kind: "audio", fmt: "mp3", meetingId });
  let recordNameFromMp3 = "";
  if (askUser) {
    const question = dict.prompt_save_mp3_after_stop || "Recording is finished. Enter MP3 file name:";
    const suggested = normalizeMp3Filename(filename, "record");
    const entered = window.prompt(question, suggested);
    if (entered == null) {
      return false;
    }
    filename = normalizeMp3Filename(entered, suggested.replace(/\.mp3$/i, ""));
    recordNameFromMp3 = _stripFileExt(filename, "mp3");
  }
  if (syncRecordName && recordNameFromMp3) {
    try {
      const renameRes = await fetch(`/v1/meetings/${meetingId}/rename`, {
        method: "POST",
        headers: buildHeaders(),
        body: JSON.stringify({ display_name: recordNameFromMp3 }),
      });
      if (renameRes.ok) {
        const body = await renameRes.json();
        const confirmedName = String((body && body.display_name) || recordNameFromMp3).trim() || recordNameFromMp3;
        const existing = state.recordsMeta.get(meetingId) || { meeting_id: meetingId };
        state.recordsMeta.set(meetingId, { ...existing, display_name: confirmedName });
        if (els.recordsSelect && els.recordsSelect.options) {
          const option = Array.from(els.recordsSelect.options).find((opt) => String(opt.value || "") === meetingId);
          if (option) {
            option.textContent = formatMeetingOptionLabel(state.recordsMeta.get(meetingId));
          }
        }
        syncReportSelectors();
      }
    } catch (err) {
      console.warn("sync record name from mp3 failed", err);
    }
  }
  const url = `/v1/meetings/${meetingId}/artifact?kind=audio&fmt=mp3`;
  let result = null;
  const busySignal = showBusyOverlay("busy_mp3_title", "busy_mp3_text", { cancelable: true });
  try {
    updateBusyOverlayProgress(8);
    result = await downloadArtifact(url, filename, {
      preferPicker: true,
      onProgress: (pct) => updateBusyOverlayProgress(pct),
      signal: busySignal,
    });
    updateBusyOverlayProgress(100);
  } finally {
    hideBusyOverlay();
  }
  if (result && result.aborted) {
    return false;
  }
  if (result && result.ok) {
    if (syncRecordName && recordNameFromMp3) {
      const ru = state.lang === "ru";
      setStatusHint(
        ru ? "MP3 сохранён. Название записи обновлено." : "MP3 saved. Recording name updated.",
        "good",
        true
      );
    } else {
      setStatusHint("hint_mp3_saved", "good");
    }
    void fetchRecords();
    return true;
  }
  if (result && result.status === 404) {
    setStatusHint("hint_mp3_not_found_ffmpeg", "bad");
    logUiEvent(
      "mp3_artifact_missing_after_finish",
      { meeting_id: meetingId, filename, status: 404 },
      "error"
    );
  } else if (result && !result.ok) {
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
    logUiEvent(
      "record_rename_submit",
      {
        meeting_id: meetingId,
        old_name: currentName,
        new_name: value,
      },
      "info"
    );
    const res = await fetch(`/v1/meetings/${meetingId}/rename`, {
      method: "POST",
      headers: buildHeaders(),
      body: JSON.stringify({ display_name: value }),
    });
    if (!res.ok) {
      setStatusHint("hint_record_rename_failed", "bad");
      logUiEvent(
        "record_rename_failed_http",
        { meeting_id: meetingId, status: res.status, attempted_name: value },
        "error"
      );
      return;
    }
    const body = await res.json();
    const confirmedName = String((body && body.display_name) || value).trim() || value;
    const existing = state.recordsMeta.get(meetingId) || { meeting_id: meetingId };
    state.recordsMeta.set(meetingId, {
      ...existing,
      display_name: confirmedName,
    });
    if (els.recordsSelect && els.recordsSelect.options) {
      const option = Array.from(els.recordsSelect.options).find((opt) => String(opt.value || "") === meetingId);
      if (option) {
        option.textContent = formatMeetingOptionLabel(state.recordsMeta.get(meetingId));
      }
    }
    closeRecordMenu();
    setStatusHint("hint_record_renamed", "good");
    logUiEvent(
      "record_rename_success",
      { meeting_id: meetingId, display_name: confirmedName },
      "info"
    );
    await fetchRecords();
  } catch (err) {
    console.warn("rename record failed", err);
    setStatusHint("hint_record_rename_failed", "bad");
    logUiEvent(
      "record_rename_failed_exception",
      { meeting_id: meetingId, error_name: String((err && err.name) || ""), error_message: String((err && err.message) || err || "") },
      "error"
    );
  }
};

const generateTranscriptForMeeting = async (meetingId, source = "raw", options = {}) => {
  if (!meetingId) return false;
  const src = source === "clean" ? "clean" : "raw";
  const forceRebuild = Boolean(options && options.forceRebuild);
  const generated = await fetch(`/v1/meetings/${meetingId}/transcripts/generate`, {
    method: "POST",
    headers: buildHeaders(),
    body: JSON.stringify({
      variants: [src],
      force_rebuild: forceRebuild,
    }),
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
  let inputValue = String((els.reportNameInput && els.reportNameInput.value) || "").trim();
  if (!inputValue) {
    inputValue = ensureNamedReportInput(els.reportNameInput, source);
    if (!inputValue) {
      setStatusHint("hint_report_name_missing", "bad");
      return;
    }
  }
  const fallback = source === "raw" ? "raw_transcript" : "clean_transcript";
  const filename = normalizeFilenameWithExt(inputValue, fallback, "txt");
  const url = `/v1/meetings/${meetingId}/artifact?kind=${source}&fmt=txt`;
  const busySignal = showBusyOverlay("busy_report_title", "busy_report_text", { cancelable: true });
  let result = null;
  try {
    updateBusyOverlayProgress(8);
    result = await downloadArtifact(url, filename, {
      preferPicker: true,
      onProgress: (pct) => updateBusyOverlayProgress(pct),
      signal: busySignal,
    });
    updateBusyOverlayProgress(100);
  } finally {
    hideBusyOverlay();
  }
  if (result && result.aborted) {
    return;
  }
  if (!result || !result.ok) {
    if (result && Number(result.status) === 409) {
      setStatusHint("hint_transcript_not_ready", "bad");
    } else {
      setStatusHint("hint_report_missing", "bad");
    }
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
  let inputValue = String((els.reportNameInput && els.reportNameInput.value) || "").trim();
  if (!inputValue) {
    inputValue = ensureNamedReportInput(els.reportNameInput, source);
  }
  if (!inputValue) {
    setStatusHint("hint_report_name_missing", "bad");
    return;
  }
  let result = null;
  const busySignal = showBusyOverlay("busy_report_title", "busy_report_text", { cancelable: true });
  try {
    updateBusyOverlayProgress(12);
    const built = await generateTranscriptForMeeting(meetingId, source, {
      forceRebuild: false,
    });
    if (!built) {
      setStatusHint("hint_transcript_generate_failed", "bad");
      return;
    }
    const filename = normalizeFilenameWithExt(
      inputValue,
      source === "raw" ? "raw_transcript" : "clean_transcript",
      "txt"
    );
    const url = `/v1/meetings/${meetingId}/artifact?kind=${source}&fmt=txt`;
    updateBusyOverlayProgress(42);
    result = await downloadArtifact(url, filename, {
      preferPicker: true,
      onProgress: (pct) => updateBusyOverlayProgress(Math.max(42, pct)),
      signal: busySignal,
    });
    updateBusyOverlayProgress(100);
  } finally {
    hideBusyOverlay();
  }
  if (result && result.aborted) {
    return;
  }
  if (!result || !result.ok) {
    setStatusHint("hint_report_missing", "bad");
    return;
  }
  await fetchRecords();
  await fetchComparison();
  setStatusHint("hint_report_generated", "good");
};

const exportReportLane = async (source = "raw", exportKind = "report_txt") => {
  setResultsTab("transcript", { setFlow: true });
  const src = source === "clean" ? "clean" : "raw";
  const meetingId = getReportMeetingId(src);
  if (!meetingId) {
    setStatusHint("hint_report_source_missing", "bad");
    return;
  }
  const inputEl = getReportNameInputEl(src);
  let rawName = String((inputEl && inputEl.value) || "").trim();
  if (!rawName) {
    rawName = ensureNamedReportInput(inputEl, src);
    if (!rawName) {
      setStatusHint("hint_report_name_missing", "bad");
      return;
    }
  }

  if (exportKind !== "report_txt") {
    setStatusHint("hint_report_missing", "bad");
    return;
  }

  let result = null;
  setFlowStep("process");
  const busySignal = showBusyOverlay("busy_report_title", "busy_report_text", { cancelable: true });
  try {
    updateBusyOverlayProgress(12);
    const built = await generateTranscriptForMeeting(meetingId, src, {
      forceRebuild: false,
    });
    if (!built) {
      setStatusHint("hint_transcript_generate_failed", "bad");
      return;
    }
    const url = `/v1/meetings/${meetingId}/artifact?kind=${src}&fmt=txt`;
    const filename = normalizeFilenameWithExt(rawName, `${src}_transcript`, "txt");
    updateBusyOverlayProgress(42);
    result = await downloadArtifact(url, filename, {
      preferPicker: true,
      onProgress: (pct) => updateBusyOverlayProgress(Math.max(42, pct)),
      signal: busySignal,
    });
    updateBusyOverlayProgress(100);
  } finally {
    hideBusyOverlay();
  }
  if (result && result.aborted) {
    setFlowStep("results");
    return;
  }
  if (!result || !result.ok) {
    setStatusHint("hint_report_missing", "bad");
    return;
  }
  await fetchRecords();
  await fetchComparison();
  setFlowStep("results");
};

const uploadAudioToMeetingPipeline = async (file, options = {}) => {
  const { source = "upload_audio", enforceUploadMode = false, importOnly = false } = options;
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
  setFlowStep("process");
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
    const uploadEndpoint = importOnly ? "backup-audio" : "upload";
    const uploadRes = await fetch(`/v1/meetings/${meetingId}/${uploadEndpoint}`, {
      method: "POST",
      headers: buildAuthHeaders(),
      body: form,
    });
    if (!uploadRes.ok) {
      throw new Error(`meeting_upload_failed_${uploadRes.status}`);
    }
    if (!importOnly) {
      state.chunkCount = 1;
      if (els.chunkCount) {
        els.chunkCount.textContent = "1";
      }
    }
    setTranscriptUiState("waiting");
    const finishRes = await fetch(`/v1/meetings/${meetingId}/finish`, {
      method: "POST",
      headers: buildHeaders(),
    });
    if (!finishRes.ok) {
      throw new Error(`meeting_finish_failed_${finishRes.status}`);
    }
    await fetchRecords({ refreshCompare: false });
    setTranscriptUiState("waiting");
    setResultsTab("audio");
    setFlowStep("results");
    if (els.recordsSelect) {
      els.recordsSelect.value = meetingId;
    }
    syncResultsState();
    return meetingId;
  } catch (err) {
    console.warn("postmeeting upload failed", err);
    setStatus("status_error", "error");
    setFlowStep("mode");
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

(els.resultTabButtons || []).forEach((btn) => {
  btn.addEventListener("click", () => {
    const tab = btn && btn.dataset ? btn.dataset.resultsTab : "audio";
    setResultsTab(tab, { setFlow: true });
  });
});

if (els.scanLlmModels) {
  els.scanLlmModels.addEventListener("click", () => {
    void scanLlmModels();
  });
}
if (els.scanSttModels) {
  els.scanSttModels.addEventListener("click", () => {
    void scanSttModels();
  });
}
if (els.applySttModel) {
  els.applySttModel.addEventListener("click", () => {
    void applySttModel();
  });
}
if (els.applyLlmModel) {
  els.applyLlmModel.addEventListener("click", () => {
    void applyLlmModel();
  });
}
if (els.scanEmbeddingModels) {
  els.scanEmbeddingModels.addEventListener("click", () => {
    void scanEmbeddingModels();
  });
}
if (els.applyEmbeddingModel) {
  els.applyEmbeddingModel.addEventListener("click", () => {
    void applyEmbeddingModel();
  });
}
if (els.busyOverlayToggle) {
  els.busyOverlayToggle.addEventListener("click", () => {
    toggleBusyOverlayMinimized();
  });
}
if (els.busyOverlayCancel) {
  els.busyOverlayCancel.addEventListener("click", () => {
    cancelBusyOverlayOperation();
  });
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
if (els.claimCaptureBtn) {
  els.claimCaptureBtn.addEventListener("click", () => {
    void claimCaptureInThisWindow();
  });
}

if (els.refreshDevices) {
  els.refreshDevices.addEventListener("click", () => {
    void listDevices({ requestAccess: true });
  });
}
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
    showCaptureLockConflict(lock.meetingId || "");
    setStatus("status_error", "error");
    setStatusHint("err_capture_locked_other_tab", "bad");
  }
});
if (els.checkDriver) {
  els.checkDriver.addEventListener("click", checkDriver);
}
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
    const meetingId = await uploadAudioToMeetingPipeline(file, {
      source: "results_mp3_import",
      importOnly: true,
    });
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
if (els.llmArtifactGenerateBtn) {
  els.llmArtifactGenerateBtn.addEventListener("click", () => {
    void generateLlmArtifact();
  });
}
[els.llmArtifactMeetingSelect, els.llmArtifactSourceSelect, els.llmArtifactModeSelect, els.llmArtifactTemplateSelect].forEach(
  (el) => {
    if (!el) return;
    el.addEventListener("change", () => {
      _syncLlmArtifactControlsToState();
      renderLlmArtifactWorkspace();
    });
  }
);
if (els.llmArtifactForceRebuild) {
  els.llmArtifactForceRebuild.addEventListener("change", () => {
    _syncLlmArtifactControlsToState();
    renderLlmArtifactWorkspace();
  });
}
if (els.llmArtifactPromptInput) {
  els.llmArtifactPromptInput.addEventListener("keydown", (event) => {
    if (!(event.metaKey || event.ctrlKey)) return;
    if (event.key !== "Enter") return;
    event.preventDefault();
    void generateLlmArtifact();
  });
}
if (els.llmArtifactSchemaInput) {
  els.llmArtifactSchemaInput.addEventListener("blur", () => {
    const raw = String(els.llmArtifactSchemaInput.value || "").trim();
    if (!raw) return;
    const parsed = _parseLlmArtifactSchema();
    if (!parsed.ok) {
      setLlmArtifactHint("llm_artifact_hint_schema_invalid", "bad");
    }
  });
}
if (els.llmChatSendBtn) {
  els.llmChatSendBtn.addEventListener("click", () => {
    void sendLlmChatPrompt();
  });
}
if (els.llmSourceModeFiles) {
  els.llmSourceModeFiles.addEventListener("click", () => {
    setResultsTab("llm", { setFlow: true });
    setLlmSourceMode("files");
  });
}
if (els.llmSourceModeRag) {
  els.llmSourceModeRag.addEventListener("click", () => {
    setResultsTab("llm", { setFlow: true });
    setLlmSourceMode("rag");
  });
}
if (els.llmChatClearBtn) {
  els.llmChatClearBtn.addEventListener("click", () => {
    clearLlmChatResults();
  });
}
if (els.llmChatInput) {
  els.llmChatInput.addEventListener("keydown", (event) => {
    if (!(event.metaKey || event.ctrlKey)) return;
    if (event.key !== "Enter") return;
    event.preventDefault();
    void sendLlmChatPrompt();
  });
}
if (els.llmChatAttachBtn && els.llmChatAttachInput) {
  els.llmChatAttachBtn.addEventListener("click", () => {
    els.llmChatAttachInput.value = "";
    els.llmChatAttachInput.click();
  });
}
if (els.llmChatAttachInput) {
  els.llmChatAttachInput.addEventListener("change", () => {
    state.llmArtifact.chatAttachments = _attachmentFilesFromInput(els.llmChatAttachInput);
    renderLlmChatAttachments();
  });
}
[
  [els.llmChatPresetSummary, "summary"],
  [els.llmChatPresetTable, "table"],
  [els.llmChatPresetJson, "json"],
  [els.llmChatPresetCsv, "csv"],
].forEach(([el, preset]) => {
  if (!el) return;
  el.addEventListener("click", () => {
    _applyLlmChatPreset(preset);
  });
});
if (els.ragRefreshMeetingsBtn) {
  els.ragRefreshMeetingsBtn.addEventListener("click", () => {
    void fetchRecords();
  });
}
if (els.ragSelectCurrentBtn) {
  els.ragSelectCurrentBtn.addEventListener("click", () => {
    const current = String(getSelectedMeeting() || "").trim();
    if (!current) return;
    _setRagSelectedMeetingIds([current]);
    renderRagWorkspace();
  });
}
if (els.ragSelectAllBtn) {
  els.ragSelectAllBtn.addEventListener("click", () => {
    _setRagSelectedMeetingIds(Array.from(state.recordsMeta.keys()));
    renderRagWorkspace();
  });
}
if (els.ragClearSelectionBtn) {
  els.ragClearSelectionBtn.addEventListener("click", () => {
    _setRagSelectedMeetingIds([]);
    renderRagWorkspace();
  });
}
if (els.ragSavedSetSelect) {
  els.ragSavedSetSelect.addEventListener("change", () => {
    state.rag.activeSavedSet = String(els.ragSavedSetSelect.value || "").trim();
    renderRagWorkspace();
  });
}
if (els.ragSaveSetBtn) {
  els.ragSaveSetBtn.addEventListener("click", () => {
    saveRagCompareSet();
  });
}
if (els.ragLoadSetBtn) {
  els.ragLoadSetBtn.addEventListener("click", () => {
    loadRagCompareSet();
  });
}
if (els.ragDeleteSetBtn) {
  els.ragDeleteSetBtn.addEventListener("click", () => {
    deleteRagCompareSet();
  });
}
if (els.ragSourceSelect) {
  els.ragSourceSelect.addEventListener("change", () => {
    state.rag.source = _ragSourceValue();
    renderRagWorkspace();
  });
}
if (els.ragTopKInput) {
  els.ragTopKInput.addEventListener("change", () => {
    state.rag.topK = _ragTopKValue();
    renderRagWorkspace();
  });
}
[els.ragUseLlmAnswer, els.ragAutoIndex, els.ragForceReindex].forEach((el) => {
  if (!el) return;
  el.addEventListener("change", () => {
    _syncRagControlsToState();
    renderRagWorkspace();
  });
});
if (els.ragRunBtn) {
  els.ragRunBtn.addEventListener("click", () => {
    void runRagQuery();
  });
}
if (els.ragChatSendBtn) {
  els.ragChatSendBtn.addEventListener("click", () => {
    void runRagQuery();
  });
}
if (els.ragIndexSelectedBtn) {
  els.ragIndexSelectedBtn.addEventListener("click", () => {
    void indexSelectedRagMeetings();
  });
}
if (els.ragQueryInput) {
  els.ragQueryInput.addEventListener("keydown", (event) => {
    if (!(event.metaKey || event.ctrlKey)) return;
    if (event.key !== "Enter") return;
    event.preventDefault();
    void runRagQuery();
  });
}
if (els.ragChatAttachBtn && els.ragChatAttachInput) {
  els.ragChatAttachBtn.addEventListener("click", () => {
    els.ragChatAttachInput.value = "";
    els.ragChatAttachInput.click();
  });
}
if (els.ragChatAttachInput) {
  els.ragChatAttachInput.addEventListener("change", () => {
    state.rag.chatAttachments = _attachmentFilesFromInput(els.ragChatAttachInput);
    renderRagChatAttachments();
  });
}
if (els.ragExportJsonBtn) {
  els.ragExportJsonBtn.addEventListener("click", () => {
    void exportRagResults("json");
  });
}
if (els.ragExportCsvBtn) {
  els.ragExportCsvBtn.addEventListener("click", () => {
    void exportRagResults("csv");
  });
}
if (els.ragExportTxtBtn) {
  els.ragExportTxtBtn.addEventListener("click", () => {
    void exportRagResults("txt");
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
updateI18n();
setResultsTab(state.resultsTab || "audio");
setLlmSourceMode(state.llmSourceMode || "files");
setFlowStep("mode");
_loadRagSavedSetsFromStorage();
_diagMarkAllMuted();
setDiagHint("diag_hint_idle", "muted");
pruneStaleCaptureLock();
clearCaptureLock();
listDevices();
fetchSttStatus({ scanAfter: true });
fetchLlmStatus({ scanAfter: true });
fetchEmbeddingStatus({ scanAfter: true });
updateCaptureUi();
fetchRecords();
setRecordingButtons(false);
setDriverHelpTab("mac");
syncResultsState();
setCompareHint("compare_hint_idle", "muted");
renderComparisonTable();
setLlmArtifactHint("llm_artifact_hint_idle", "muted");
renderLlmArtifactWorkspace();
setRagHint("rag_hint_idle", "muted");
renderRagWorkspace();
setQuickStatus("quick_record_state_idle", "muted");
setQuickHint("quick_record_hint_ready", "muted");
setQuickButtonsByStatus("idle");
fetchQuickRecordStatus({ silentErrors: true });
if (!window.showDirectoryPicker) {
  setFolderStatus("folder_not_supported", "bad");
}
