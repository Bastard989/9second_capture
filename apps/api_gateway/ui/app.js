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
  micAdded: false,
  inputStreams: [],
  audioContext: null,
  analyser: null,
  meterMode: "",
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
  nonEmptyRawUpdates: 0,
  pendingChunks: [],
  wsReconnectTimer: null,
  wsReconnectAttempts: 0,
  httpDrainTimer: null,
  httpDrainInProgress: false,
  backupRecorder: null,
};

const PREFER_PCM_CAPTURE = true;
const CHUNK_TIMESLICE_MS = 3000;
const HTTP_DRAIN_INTERVAL_MS = 1400;
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
    connection_title: "Подключение",
    api_key_label: "API ключ (опционально)",
    api_key_placeholder: "X-API-Key",
    device_label: "Источник аудио",
    refresh_devices: "Обновить",
    device_hint: "Выберите виртуальный драйвер захвата системного звука.",
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
    capture_mode_system: "Системный звук",
    capture_mode_screen: "Экран + звук",
    capture_mode_hint: "Для экрана со звуком включите “Share audio” в окне браузера.",
    capture_mode_system_note:
      "Важно: в режиме «Системный звук» микрофон добавляется автоматически, чтобы записывать и голос, и системный трек.",
    include_mic_label: "Добавлять микрофон в запись",
    mic_input_label: "Микрофон",
    mic_input_auto: "Авто (рекомендуется)",
    countdown_label: "Отсчёт:",
    signal_waiting: "Сигнал: ожидание",
    signal_ok: "Сигнал: есть",
    signal_low: "Сигнал: слабый",
    signal_no_audio: "Сигнал: нет аудио",
    signal_check: "Проверить захват",
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
    raw_live: "Live",
    clean_delay: "~3–4 сек",
    transcript_placeholder_raw: "Сырой текст будет появляться в реальном времени...",
    transcript_placeholder_clean: "Чистый текст появится с небольшой задержкой...",
    records_title: "Результаты",
    records_refresh: "Обновить",
    choose_folder: "Выбрать папку",
    folder_not_selected: "Папка не выбрана",
    folder_selected: "Папка выбрана",
    folder_not_supported: "Выбор папки недоступен",
    results_source_label: "Источник",
    file_transcript: "Файл транскрипта",
    file_action_download: "Скачать",
    file_action_report: "Экспорт TXT",
    file_action_table: "Таблица",
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
    upload_audio_btn: "Загрузить аудио",
    upload_video_label: "Видео файл",
    upload_video_btn: "Видео (в разработке)",
    upload_hint: "Видео‑анализ появится после интеграции мультимодальной LLM.",
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
    err_no_device_selected:
      "Не выбран источник аудио. Выберите устройство и повторите.",
    err_screen_audio_missing:
      "В режиме «Экран + звук» включите «Share audio» в окне выбора экрана.",
    err_server_start: "Не удалось создать встречу на локальном API.",
    err_network: "Сбой сети/локального API. Попробуйте ещё раз.",
    err_recorder_init:
      "MediaRecorder не поддерживается для текущего источника. Попробуйте другой режим.",
    err_mic_same_as_system:
      "Микрофон совпадает с системным источником. Выберите другой микрофон или режим «Авто».",
    warn_mic_not_added:
      "Микрофон не удалось добавить. Разрешите доступ к микрофону и проверьте выбранный вход.",
    warn_screen_audio_mic_only:
      "Системный звук экрана не передаётся (Share audio выключен). Записывается только микрофон.",
    warn_media_fallback_pcm:
      "MediaRecorder недоступен, переключились на PCM-захват. Нагрузка на CPU может быть выше.",
    warn_capture_stream_interrupted:
      "Один из потоков захвата остановился. Продолжаем запись доступных дорожек.",
    warn_backup_upload_failed:
      "Резервный аудиофайл не удалось отправить. Часть хвоста записи может не попасть в финальный текст.",
    err_generic: "Не удалось начать запись. Проверьте права браузера и источник аудио.",
    hint_recording_ok: "Запись запущена. Транскрипт будет обновляться в реальном времени.",
    hint_no_speech_yet:
      "Пока нет распознанной речи. Проверьте источник: в «Системном звуке» звук встречи должен идти в BlackHole/VB-CABLE; в «Экран + звук» включите Share audio; для голоса убедитесь, что микрофон добавлен.",
  },
  en: {
    subtitle: "Local meeting capture agent",
    theme_label: "Theme",
    theme_light: "Light",
    theme_dark: "Dark",
    connection_title: "Connection",
    api_key_label: "API key (optional)",
    api_key_placeholder: "X-API-Key",
    device_label: "Audio source",
    refresh_devices: "Refresh",
    device_hint: "Select the virtual driver that captures system audio.",
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
    capture_mode_system: "System audio",
    capture_mode_screen: "Screen + audio",
    capture_mode_hint: "For screen + audio enable “Share audio” in the browser dialog.",
    capture_mode_system_note:
      "Important: in “System audio” mode microphone is added automatically to capture both voice and system track.",
    include_mic_label: "Include microphone in recording",
    mic_input_label: "Microphone",
    mic_input_auto: "Auto (recommended)",
    countdown_label: "Countdown:",
    signal_waiting: "Signal: waiting",
    signal_ok: "Signal: ok",
    signal_low: "Signal: low",
    signal_no_audio: "Signal: no audio",
    signal_check: "Check capture",
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
    raw_live: "Live",
    clean_delay: "~3–4s",
    transcript_placeholder_raw: "Raw text will appear in real time...",
    transcript_placeholder_clean: "Clean text appears with a small delay...",
    records_title: "Results",
    records_refresh: "Refresh",
    choose_folder: "Choose folder",
    folder_not_selected: "Folder not selected",
    folder_selected: "Folder selected",
    folder_not_supported: "Folder chooser not supported",
    results_source_label: "Source",
    file_transcript: "Transcript file",
    file_action_download: "Download",
    file_action_report: "Export TXT",
    file_action_table: "Table",
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
    upload_audio_btn: "Upload audio",
    upload_video_label: "Video file",
    upload_video_btn: "Video (in development)",
    upload_hint: "Video analysis will arrive with multimodal LLM support.",
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
    err_no_device_selected:
      "Audio source is not selected. Choose a device and retry.",
    err_screen_audio_missing:
      "In “Screen + audio” mode, enable “Share audio” in browser capture dialog.",
    err_server_start: "Unable to create meeting on local API.",
    err_network: "Network/local API error. Please retry.",
    err_recorder_init:
      "MediaRecorder is not supported for this source. Try another mode.",
    err_mic_same_as_system:
      "Microphone matches system source. Choose another microphone or keep Auto mode.",
    warn_mic_not_added:
      "Microphone could not be added. Allow microphone access and verify selected input.",
    warn_screen_audio_mic_only:
      "Screen system audio is not shared (Share audio is off). Recording microphone only.",
    warn_media_fallback_pcm:
      "MediaRecorder is unavailable, switched to PCM capture. CPU usage may be higher.",
    warn_capture_stream_interrupted:
      "One capture stream stopped unexpectedly. Continuing with remaining tracks.",
    warn_backup_upload_failed:
      "Backup audio upload failed. A tail part of recording may be missing in final transcript.",
    err_generic: "Unable to start recording. Check browser permissions and source.",
    hint_recording_ok: "Recording started. Transcript updates in real time.",
    hint_no_speech_yet:
      "No recognized speech yet. Verify source routing: in “System audio” route meeting output to BlackHole/VB-CABLE; in “Screen + audio” enable Share audio; for voice capture ensure microphone is added.",
  },
};

const els = {
  apiKey: document.getElementById("apiKey"),
  deviceSelect: document.getElementById("deviceSelect"),
  refreshDevices: document.getElementById("refreshDevices"),
  checkDriver: document.getElementById("checkDriver"),
  includeMic: document.getElementById("includeMic"),
  micSelect: document.getElementById("micSelect"),
  driverHelpBtn: document.getElementById("driverHelpBtn"),
  driverHelp: document.getElementById("driverHelp"),
  driverStatus: document.getElementById("driverStatus"),
  startBtn: document.getElementById("startBtn"),
  stopBtn: document.getElementById("stopBtn"),
  statusText: document.getElementById("statusText"),
  statusHint: document.getElementById("statusHint"),
  countdownValue: document.getElementById("countdownValue"),
  levelBar: document.getElementById("levelBar"),
  signalText: document.getElementById("signalText"),
  checkSignal: document.getElementById("checkSignal"),
  meetingIdText: document.getElementById("meetingIdText"),
  chunkCount: document.getElementById("chunkCount"),
  transcriptRaw: document.getElementById("transcriptRaw"),
  transcriptClean: document.getElementById("transcriptClean"),
  recordsSelect: document.getElementById("recordsSelect"),
  refreshRecords: document.getElementById("refreshRecords"),
  resultsRaw: document.getElementById("resultsRaw"),
  resultsClean: document.getElementById("resultsClean"),
  resultFileName: document.getElementById("resultFileName"),
  downloadArtifactBtn: document.getElementById("downloadArtifactBtn"),
  reportArtifactBtn: document.getElementById("reportArtifactBtn"),
  structuredArtifactBtn: document.getElementById("structuredArtifactBtn"),
  chooseFolder: document.getElementById("chooseFolder"),
  folderStatus: document.getElementById("folderStatus"),
  uploadAudio: document.getElementById("uploadAudio"),
  uploadAudioBtn: document.getElementById("uploadAudioBtn"),
  uploadVideo: document.getElementById("uploadVideo"),
  uploadVideoBtn: document.getElementById("uploadVideoBtn"),
  themeLight: document.getElementById("themeLight"),
  themeDark: document.getElementById("themeDark"),
};

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
  setDriverStatus(state.driverStatusKey, state.driverStatusStyle);
  setFolderStatus(state.folderStatusKey, state.folderStatusStyle);
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
};

const setSignal = (statusKey) => {
  const dict = i18n[state.lang];
  els.signalText.textContent = dict[statusKey] || statusKey;
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
  els.checkSignal.disabled = busy || recordingBlocked;
  els.checkSignal.textContent = busy
    ? dict.signal_check_running || "Checking capture..."
    : dict.signal_check || "Check capture";
};

const setRecordingButtons = (isRecording) => {
  if (isRecording) {
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

const listDevices = async () => {
  try {
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
      return;
    }
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
  }
};

const getCaptureMode = () => {
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

const buildMixedAudioStream = async (baseStream, includeMic, selectedMicId = "") => {
  const Ctx = window.AudioContext || window.webkitAudioContext;
  if (!Ctx) return { stream: baseStream, micAdded: false, micError: "" };

  const context = new Ctx();
  const destination = context.createMediaStreamDestination();
  const nodes = [destination];
  let micAdded = false;
  let micStream = null;
  let micError = "";

  const connectStream = (stream, gainValue = 1) => {
    const source = context.createMediaStreamSource(stream);
    const gain = context.createGain();
    gain.gain.value = gainValue;
    source.connect(gain);
    gain.connect(destination);
    nodes.push(source, gain);
  };

  connectStream(baseStream, 1);

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
      micStream = await navigator.mediaDevices.getUserMedia({
        audio: preferredMicId ? { deviceId: { exact: preferredMicId } } : true,
      });
      connectStream(micStream, 1);
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
  state.micAdded = false;
  closeMixGraph();
  stopInputStreams();

  let baseStream;
  if (mode === "screen") {
    baseStream = await navigator.mediaDevices.getDisplayMedia({
      video: true,
      audio: true,
    });
    state.screenAudioMissing = !baseStream.getAudioTracks().length;
    if (state.screenAudioMissing) {
      setSignal("signal_no_audio");
      console.warn("screen capture started without audio track");
    }
  } else {
    const deviceId = els.deviceSelect.value;
    const constraints = {
      audio: deviceId ? { deviceId: { exact: deviceId } } : true,
    };
    baseStream = await navigator.mediaDevices.getUserMedia(constraints);
    state.streamDeviceId = deviceId || "";
  }

  if (includeMic) {
    const mixed = await buildMixedAudioStream(baseStream, true, selectedMicId);
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
  if (state.audioContext) {
    state.audioContext.close().catch(() => {});
  }
  state.audioContext = null;
  state.analyser = null;
  state.meterMode = "";
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
  if (message.includes("no_device_selected")) return "err_no_device_selected";
  if (message.includes("start meeting failed")) return "err_server_start";
  if (message.includes("ws_open_failed")) return "err_network";
  if (message.includes("stream_missing_after_countdown")) return "err_media_not_readable";
  if (message.includes("Failed to fetch") || message.includes("NetworkError")) return "err_network";
  if (message.includes("pcm_capture_unsupported")) return "err_recorder_init";
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
  const source = state.audioContext.createMediaStreamSource(stream);
  state.analyser = state.audioContext.createAnalyser();
  state.analyser.fftSize = 1024;
  source.connect(state.analyser);
  state.meterMode = mode;
  state.signalPeak = 0;
};

const updateMeter = () => {
  if (!state.analyser) return;
  const buffer = new Uint8Array(state.analyser.fftSize);
  state.analyser.getByteTimeDomainData(buffer);
  let sum = 0;
  for (let i = 0; i < buffer.length; i += 1) {
    const v = (buffer[i] - 128) / 128;
    sum += v * v;
  }
  const rms = Math.sqrt(sum / buffer.length);
  const level = Math.min(1, rms * 2.5);
  state.signalPeak = Math.max(state.signalPeak, level);
  els.levelBar.style.transform = `scaleX(${level})`;
  if (level > 0.08) {
    setSignal("signal_ok");
  } else if (level > 0.02) {
    setSignal("signal_low");
  } else {
    setSignal("signal_waiting");
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
        setStatusHint("hint_recording_ok", "good");
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
    quality_profile: "live",
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
      "warn_screen_audio_mic_only",
      "err_media_denied",
      "err_media_not_found",
      "err_media_not_readable",
      "err_screen_audio_missing",
      "err_recorder_init",
      "err_network",
      "err_server_start",
      "err_no_device_selected",
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
    flushPendingChunks();
  };
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      handleTranscriptUpdate(data);
    } catch (err) {
      console.warn("ws message parse failed", err);
    }
  };
  ws.onclose = (event) => {
    const normalCloseCode = 1000;
    if (state.captureStopper && !state.stopRequested && (!event || event.code !== normalCloseCode)) {
      setStatusHint("err_network", "bad");
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
  }, CHUNK_TIMESLICE_MS);

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
  recorder.start(CHUNK_TIMESLICE_MS);
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
};

const handleTranscriptUpdate = (data) => {
  if (!data || data.event_type !== "transcript.update") return;
  if (typeof data.seq !== "number") return;

  if (typeof data.raw_text === "string") {
    state.transcript.raw.set(data.seq, data.raw_text);
    if (data.raw_text.trim()) {
      state.nonEmptyRawUpdates += 1;
      setSignal("signal_ok");
      if (state.statusHintKey === "hint_no_speech_yet" || state.statusHintKey === "signal_check_fail") {
        setStatusHint("hint_recording_ok", "good");
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
  state.backupRecorder = null;
  state.seq = 0;
  state.chunkCount = 0;
  state.pendingChunks = [];
  state.httpDrainInProgress = false;
  clearHttpDrainTimer();
  state.signalPeak = 0;
  state.nonEmptyRawUpdates = 0;
  els.chunkCount.textContent = "0";
  state.transcript.raw.clear();
  state.transcript.enhanced.clear();
  state.enhancedTimers.forEach((timer) => clearTimeout(timer));
  state.enhancedTimers.clear();
  if (els.transcriptRaw) els.transcriptRaw.value = "";
  if (els.transcriptClean) els.transcriptClean.value = "";
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
          quality_profile: "live",
          idempotency_key: payload.idempotency_key,
        }),
      });
      if (!res.ok) {
        state.pendingChunks.push(payload);
      } else {
        try {
          const body = await res.json();
          const updates = Array.isArray(body.inline_updates) ? body.inline_updates : [];
          updates.forEach((u) => handleTranscriptUpdate(u));
        } catch (_err) {
          // ignore parse errors: chunk can be accepted without inline_updates
        }
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
  setRecordingButtons(true);
  resetSessionState();
  els.countdownValue.textContent = "9s";
  const captureMode = getCaptureMode();

  try {
    if (captureMode === "system" && !els.deviceSelect.value) {
      throw new Error("no_device_selected");
    }
    await ensureStream(captureMode, { force: true });
    if (captureMode === "screen" && state.screenAudioMissing && !state.micAdded) {
      throw new Error("screen capture no audio track");
    }
    await buildAudioMeter(captureMode, { force: true });
    startMeter();

    await startCountdown(9);
  } catch (err) {
    releasePreparedCapture();
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
  state.stopRequested = false;

  try {
    const res = await fetch("/v1/meetings/start", {
      method: "POST",
      headers: buildHeaders(),
      body: JSON.stringify({
        mode: "realtime",
        context: { source: "local_ui", locale: state.lang, capture_mode: captureMode },
      }),
    });
    if (!res.ok) {
      throw new Error(`start meeting failed: ${res.status}`);
    }
    const data = await res.json();
    state.meetingId = data.meeting_id;
    els.meetingIdText.textContent = state.meetingId;

    await waitForWsOpen();
    const stream = state.stream;
    if (!stream) {
      throw new Error("stream_missing_after_countdown");
    }
    const captureTargets = buildCaptureTargets(captureMode);
    if (!captureTargets.length) {
      throw new Error("stream_missing_after_countdown");
    }
    const captureEngines = captureTargets.map((target) =>
      createCaptureEngine(target.stream, { sourceTrack: target.sourceTrack })
    );
    state.captureEngine = captureEngines.map((item) => `${item.engine}:${item.sourceTrack}`).join(",");
    state.captureStopper = async () => {
      for (const item of captureEngines) {
        try {
          await item.stop();
        } catch (err) {
          console.warn("capture engine stop failed", err);
        }
      }
    };
    startBackupRecorder();
    const hasFallbackPcm = captureEngines.some((item) => item.fallbackToPcm);
    if (hasFallbackPcm) {
      setStatusHint("warn_media_fallback_pcm", "bad");
    } else if (captureMode === "screen" && state.screenAudioMissing && state.micAdded) {
      setSignal("signal_low");
      setStatusHint("warn_screen_audio_mic_only", "bad");
    } else if (els.includeMic && els.includeMic.checked && !state.micAdded) {
      setStatusHint("warn_mic_not_added", "bad");
    } else {
      setStatusHint("hint_recording_ok", "good");
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
  state.stopRequested = true;
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
  await drainPendingChunksHttp(activeMeetingId, { force: true, reschedule: false });
  if (activeMeetingId && backupBlob) {
    const uploaded = await uploadBackupAudio(activeMeetingId, backupBlob);
    if (!uploaded) {
      setStatusHint("warn_backup_upload_failed", "bad");
    }
  }
  if (activeMeetingId && (forceFinish || wasRecording || wasCountingDown)) {
    try {
      await fetch(`/v1/meetings/${activeMeetingId}/finish`, {
        method: "POST",
        headers: buildHeaders(),
      });
      await fetchRecords();
    } catch (err) {
      // ignore and keep local UI responsive
    }
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

const checkSignal = async () => {
  if (state.signalCheckInProgress) return;
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

const uploadAudioFile = async () => {
  if (state.isUploading) return;
  const file = els.uploadAudio.files && els.uploadAudio.files[0];
  if (!file) return;
  state.isUploading = true;
  els.startBtn.disabled = true;
  els.stopBtn.disabled = true;
  setStatus("status_uploading", "recording");
  resetSessionState();

  const res = await fetch("/v1/meetings/start", {
    method: "POST",
    headers: buildHeaders(),
    body: JSON.stringify({
      mode: "postmeeting",
      context: { source: "upload_audio", locale: state.lang, filename: file.name },
    }),
  });
  if (!res.ok) {
    setStatus("status_error", "error");
    state.isUploading = false;
    setRecordingButtons(false);
    return;
  }
  const data = await res.json();
  state.meetingId = data.meeting_id;
  els.meetingIdText.textContent = state.meetingId;
  openWebSocket();

  const form = new FormData();
  form.append("file", file, file.name);
  const uploadRes = await fetch(`/v1/meetings/${state.meetingId}/upload`, {
    method: "POST",
    headers: buildAuthHeaders(),
    body: form,
  });
  if (!uploadRes.ok) {
    setStatus("status_error", "error");
    state.isUploading = false;
    setRecordingButtons(false);
    return;
  }
  state.chunkCount = 1;
  els.chunkCount.textContent = "1";

  await fetch(`/v1/meetings/${state.meetingId}/finish`, {
    method: "POST",
    headers: buildHeaders(),
  });
  await fetchRecords();

  state.isUploading = false;
  setStatus("status_idle", "idle");
  setRecordingButtons(false);
};

const updateCaptureUi = () => {
  const mode = getCaptureMode();
  els.deviceSelect.disabled = mode === "screen";
  if (els.includeMic) {
    if (mode === "system") {
      els.includeMic.checked = true;
      els.includeMic.disabled = true;
    } else {
      els.includeMic.disabled = false;
    }
  }
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

const syncResultsState = () => {
  if (!els.resultsRaw || !els.resultsClean) return;
  const source = state.resultsSource;
  els.resultsRaw.classList.toggle("active", source === "raw");
  els.resultsClean.classList.toggle("active", source === "clean");
  const filename = buildFilename({ kind: source, fmt: "txt" });
  if (els.resultFileName) els.resultFileName.textContent = filename;
  if (els.downloadArtifactBtn) els.downloadArtifactBtn.dataset.kind = source;
  if (els.reportArtifactBtn) els.reportArtifactBtn.dataset.source = source;
  if (els.structuredArtifactBtn) els.structuredArtifactBtn.dataset.source = source;
  const hasMeeting = Boolean(getSelectedMeeting());
  [els.downloadArtifactBtn, els.reportArtifactBtn, els.structuredArtifactBtn].forEach(
    (btn) => {
      if (btn) btn.disabled = !hasMeeting;
    }
  );
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
    els.recordsSelect.innerHTML = "";
    if (!items.length) {
      const opt = document.createElement("option");
      opt.value = "";
      opt.textContent = "—";
      els.recordsSelect.appendChild(opt);
      syncResultsState();
      return;
    }
    items.forEach((item) => {
      const opt = document.createElement("option");
      opt.value = item.meeting_id;
      const created = item.created_at ? new Date(item.created_at).toLocaleString() : "";
      opt.textContent = `${item.meeting_id}${created ? ` (${created})` : ""}`;
      if (current && item.meeting_id === current) {
        opt.selected = true;
      }
      els.recordsSelect.appendChild(opt);
    });
    syncResultsState();
  } catch (err) {
    console.warn("fetch records failed", err);
  }
};

const getSelectedMeeting = () => {
  return els.recordsSelect.value || state.meetingId;
};

const buildFilename = ({ kind, source, fmt }) => {
  if (kind === "raw") return "raw.txt";
  if (kind === "clean") return "clean.txt";
  if (kind === "report") {
    return source === "raw" ? "report_raw.txt" : "report_clean.txt";
  }
  if (kind === "structured") {
    return `structured_${source}.${fmt}`;
  }
  return "artifact.bin";
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

const downloadArtifact = async (url, filename) => {
  try {
    const res = await fetch(url, { headers: buildAuthHeaders() });
    if (!res.ok) return;
    const blob = await res.blob();
    const saved = await saveToFolder(filename, blob);
    if (saved) return;
    const link = document.createElement("a");
    const objectUrl = URL.createObjectURL(blob);
    link.href = objectUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(objectUrl), 500);
  } catch (err) {
    console.warn("download failed", err);
  }
};

const handleRecordAction = async (event) => {
  const button = event.currentTarget;
  const action = button.dataset.action;
  const meetingId = getSelectedMeeting();
  if (!meetingId) return;

  if (action === "view") {
    const kind = button.dataset.kind;
    const res = await fetch(
      `/v1/meetings/${meetingId}/artifact?kind=${kind}&fmt=txt`,
      { headers: buildHeaders() }
    );
    if (!res.ok) return;
    const text = await res.text();
    if (els.transcriptClean) els.transcriptClean.value = text;
    return;
  }

  if (action === "download") {
    const kind = button.dataset.kind;
    const url = `/v1/meetings/${meetingId}/artifact?kind=${kind}&fmt=txt`;
    const filename = buildFilename({ kind, fmt: "txt" });
    await downloadArtifact(url, filename);
    return;
  }

  if (action === "report") {
    const source = button.dataset.source || state.resultsSource;
    const view = await fetch(
      `/v1/meetings/${meetingId}/artifact?kind=${source}&fmt=txt`,
      { headers: buildHeaders() }
    );
    if (view.ok) {
      const text = await view.text();
      if (source === "raw" && els.transcriptRaw) {
        els.transcriptRaw.value = text;
      } else if (source === "clean" && els.transcriptClean) {
        els.transcriptClean.value = text;
      }
    }
    const url = `/v1/meetings/${meetingId}/artifact?kind=${source}&fmt=txt`;
    const filename = source === "raw" ? "raw_export.txt" : "clean_export.txt";
    await downloadArtifact(url, filename);
    await fetchRecords();
    return;
  }

  if (action === "structured") {
    const source = button.dataset.source || state.resultsSource;
    await fetch(`/v1/meetings/${meetingId}/structured`, {
      method: "POST",
      headers: buildHeaders(),
      body: JSON.stringify({ source }),
    });
    const url = `/v1/meetings/${meetingId}/artifact?kind=structured&source=${source}&fmt=csv`;
    const filename = buildFilename({ kind: "structured", source, fmt: "csv" });
    await downloadArtifact(url, filename);
    await fetchRecords();
    return;
  }
};

document.querySelectorAll(".lang-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    state.lang = btn.dataset.lang;
    updateI18n();
    renderTranscript();
    syncResultsState();
  });
});

document.querySelectorAll('input[name="captureMode"]').forEach((el) => {
  el.addEventListener("change", updateCaptureUi);
});

els.refreshDevices.addEventListener("click", listDevices);
if (els.deviceSelect) {
  els.deviceSelect.addEventListener("change", () => {
    void listDevices();
  });
}
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
  }
  syncResultsState();
});
if (els.resultsRaw) {
  els.resultsRaw.addEventListener("click", () => {
    state.resultsSource = "raw";
    syncResultsState();
  });
}
if (els.resultsClean) {
  els.resultsClean.addEventListener("click", () => {
    state.resultsSource = "clean";
    syncResultsState();
  });
}
els.chooseFolder.addEventListener("click", chooseFolder);
document.querySelectorAll("[data-action]").forEach((btn) => {
  btn.addEventListener("click", handleRecordAction);
});
els.startBtn.addEventListener("click", async () => {
  try {
    await startRecording();
  } catch (err) {
    console.error(err);
    setStatus("status_error", "error");
    setRecordingButtons(false);
  }
});
els.stopBtn.addEventListener("click", () => {
  void stopRecording();
});
els.checkSignal.addEventListener("click", checkSignal);
els.uploadAudioBtn.addEventListener("click", uploadAudioFile);

const savedTheme = (() => {
  try {
    return localStorage.getItem("ui_theme");
  } catch (err) {
    return null;
  }
})();
applyTheme(savedTheme || "light");
updateI18n();
listDevices();
updateCaptureUi();
fetchRecords();
setRecordingButtons(false);
setDriverHelpTab("mac");
syncResultsState();
if (!window.showDirectoryPicker) {
  setFolderStatus("folder_not_supported", "bad");
}
