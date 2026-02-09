const state = {
  lang: "ru",
  theme: "light",
  ws: null,
  recorder: null,
  stream: null,
  streamMode: "system",
  streamDeviceId: "",
  audioContext: null,
  analyser: null,
  meterMode: "",
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
};

const PREFER_PCM_CAPTURE = true;
const CHUNK_TIMESLICE_MS = 2000;

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
    countdown_label: "Отсчёт:",
    signal_waiting: "Сигнал: ожидание",
    signal_ok: "Сигнал: есть",
    signal_low: "Сигнал: слабый",
    signal_no_audio: "Сигнал: нет аудио",
    signal_check: "Проверить захват",
    signal_check_running: "Проверка захвата...",
    signal_check_ok: "Захват работает: уровень сигнала обнаружен.",
    signal_check_fail: "Захват не обнаружил аудио. Проверьте источник/Share audio.",
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
    err_generic: "Не удалось начать запись. Проверьте права браузера и источник аудио.",
    hint_recording_ok: "Запись запущена. Транскрипт будет обновляться в реальном времени.",
    hint_no_speech_yet:
      "Пока нет распознанной речи. Проверьте источник звука или включите Share audio.",
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
    countdown_label: "Countdown:",
    signal_waiting: "Signal: waiting",
    signal_ok: "Signal: ok",
    signal_low: "Signal: low",
    signal_no_audio: "Signal: no audio",
    signal_check: "Check capture",
    signal_check_running: "Checking capture...",
    signal_check_ok: "Capture is working: audio level detected.",
    signal_check_fail: "No audio detected. Check source/Share audio.",
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
    gen_structured_raw: "Tables raw",
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
    err_generic: "Unable to start recording. Check browser permissions and source.",
    hint_recording_ok: "Recording started. Transcript updates in real time.",
    hint_no_speech_yet:
      "No recognized speech yet. Check audio source or enable Share audio.",
  },
};

const els = {
  apiKey: document.getElementById("apiKey"),
  deviceSelect: document.getElementById("deviceSelect"),
  refreshDevices: document.getElementById("refreshDevices"),
  checkDriver: document.getElementById("checkDriver"),
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
  if (els.checkSignal && state.signalCheckInProgress) {
    els.checkSignal.textContent = dict.signal_check_running || "Checking capture...";
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

const listDevices = async () => {
  try {
    const devices = await navigator.mediaDevices.enumerateDevices();
    const inputs = devices.filter((d) => d.kind === "audioinput");
    const prevValue = els.deviceSelect.value;
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
      return;
    }
    const hasPrev = inputs.some((d) => d.deviceId === prevValue);
    if (hasPrev) {
      els.deviceSelect.value = prevValue;
    }
  } catch (err) {
    console.warn("device list failed", err);
  }
};

const getCaptureMode = () => {
  const el = document.querySelector('input[name="captureMode"]:checked');
  return el ? el.value : "system";
};

const ensureStream = async (mode, options = {}) => {
  const { force = false } = options;
  const selectedDeviceId = mode === "system" ? els.deviceSelect.value || "" : "";
  const canReuse =
    !force &&
    state.stream &&
    state.streamMode === mode &&
    (mode !== "system" || state.streamDeviceId === selectedDeviceId);
  if (canReuse) return state.stream;
  if (state.stream) {
    state.stream.getTracks().forEach((t) => t.stop());
    state.stream = null;
    state.streamDeviceId = "";
  }
  if (mode === "screen") {
    state.stream = await navigator.mediaDevices.getDisplayMedia({
      video: true,
      audio: true,
    });
    if (!state.stream.getAudioTracks().length) {
      setSignal("signal_no_audio");
      console.warn("screen capture started without audio track");
    }
    state.streamDeviceId = "";
  } else {
    const deviceId = els.deviceSelect.value;
    const constraints = {
      audio: deviceId ? { deviceId: { exact: deviceId } } : true,
    };
    state.stream = await navigator.mediaDevices.getUserMedia(constraints);
    state.streamDeviceId = deviceId || "";
  }
  state.streamMode = mode;
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

const mapStartError = (err, mode) => {
  const name = err && typeof err === "object" ? err.name || "" : "";
  const message = err && typeof err === "object" ? err.message || "" : String(err || "");
  if (name === "NotAllowedError" || name === "SecurityError") return "err_media_denied";
  if (name === "NotFoundError" || name === "OverconstrainedError") return "err_media_not_found";
  if (name === "NotReadableError" || name === "AbortError") return "err_media_not_readable";
  if (message.includes("no_device_selected")) return "err_no_device_selected";
  if (message.includes("start meeting failed")) return "err_server_start";
  if (message.includes("ws_open_failed")) return "err_network";
  if (message.includes("Failed to fetch") || message.includes("NetworkError")) return "err_network";
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
    state.ws.send(JSON.stringify(payload));
  }
};

const queueOrSendChunk = (payload) => {
  if (state.ws && state.ws.readyState === WebSocket.OPEN) {
    state.ws.send(JSON.stringify(payload));
    return;
  }
  state.pendingChunks.push(payload);
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

const sendChunk = async (blob, mimeType) => {
  if (!state.meetingId) return;
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
    content_b64,
  };
  queueOrSendChunk(payload);
  state.seq += 1;
  state.chunkCount += 1;
  els.chunkCount.textContent = String(state.chunkCount);
  if (state.chunkCount >= 4 && state.nonEmptyRawUpdates === 0) {
    setSignal("signal_no_audio");
    setStatusHint("hint_no_speech_yet", "bad");
  }
};

const openWebSocket = () => {
  if (state.ws) return state.ws;
  const base = window.location.origin.replace("http", "ws");
  const ws = new WebSocket(`${base}/v1/ws`);
  state.ws = ws;
  ws.onopen = () => {
    flushPendingChunks();
  };
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.event_type === "transcript.update") {
        if (typeof data.seq === "number") {
          if (typeof data.raw_text === "string") {
            state.transcript.raw.set(data.seq, data.raw_text);
            if (data.raw_text.trim()) {
              state.nonEmptyRawUpdates += 1;
            }
          }
          if (data.enhanced_text != null) {
            if (!state.enhancedTimers.has(data.seq)) {
              const timer = setTimeout(() => {
                state.transcript.enhanced.set(data.seq, data.enhanced_text);
                state.enhancedTimers.delete(data.seq);
                renderTranscript();
              }, 3500);
              state.enhancedTimers.set(data.seq, timer);
            }
          }
          renderTranscript();
        }
      }
    } catch (err) {
      console.warn("ws message parse failed", err);
    }
  };
  ws.onclose = () => {
    if (state.captureStopper) {
      setStatus("status_error", "error");
      setStatusHint("err_network", "bad");
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

const createPcmCapture = (stream) => {
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
      await sendChunk(wavBlob, "audio/wav");
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

const createMediaRecorderCapture = (stream) => {
  const { recorder, mimeType } = createRecorderWithFallback(stream);
  recorder.onerror = () => {
    if (!state.stopRequested) {
      setStatus("status_error", "error");
      setStatusHint("err_recorder_init", "bad");
    }
  };
  recorder.onstop = () => {
    if (!state.stopRequested) {
      setStatus("status_error", "error");
      setStatusHint("err_recorder_init", "bad");
    }
  };
  recorder.ondataavailable = async (e) => {
    if (e.data && e.data.size > 0) {
      await sendChunk(e.data, mimeType || e.data.type);
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

const createCaptureEngine = (stream) => {
  if (PREFER_PCM_CAPTURE) {
    try {
      return createPcmCapture(stream);
    } catch (err) {
      console.warn("pcm capture fallback to MediaRecorder", err);
    }
  }
  return createMediaRecorderCapture(stream);
};

const setCheckSignalBusy = (busy) => {
  state.signalCheckInProgress = busy;
  if (!els.checkSignal) return;
  els.checkSignal.disabled = busy;
  const dict = i18n[state.lang];
  els.checkSignal.textContent = busy
    ? dict.signal_check_running || "Checking capture..."
    : dict.signal_check || "Check capture";
};

const renderTranscript = () => {
  const orderedRaw = Array.from(state.transcript.raw.entries())
    .sort((a, b) => a[0] - b[0])
    .map(([, text]) => text)
    .filter(Boolean)
    .join(" ");
  const orderedClean = Array.from(state.transcript.enhanced.entries())
    .sort((a, b) => a[0] - b[0])
    .map(([, text]) => text)
    .filter(Boolean)
    .join(" ");
  if (els.transcriptRaw) els.transcriptRaw.value = orderedRaw;
  if (els.transcriptClean) els.transcriptClean.value = orderedClean;
};

const resetSessionState = () => {
  state.seq = 0;
  state.chunkCount = 0;
  state.pendingChunks = [];
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

  try {
    await startCountdown(9);
  } catch (err) {
    setStatus("status_idle", "idle");
    setStatusHint("");
    setRecordingButtons(false);
    return;
  }

  setStatus("status_recording", "recording");
  setStatusHint("");
  state.stopRequested = false;

  const captureMode = getCaptureMode();
  try {
    if (captureMode === "system" && !els.deviceSelect.value) {
      throw new Error("no_device_selected");
    }

    const stream = await ensureStream(captureMode, { force: true });
    if (captureMode === "screen" && !stream.getAudioTracks().length) {
      throw new Error("screen capture no audio track");
    }
    await buildAudioMeter(captureMode, { force: true });
    startMeter();

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
    const capture = createCaptureEngine(stream);
    state.captureEngine = capture.engine;
    state.captureStopper = capture.stop;
    setStatusHint("hint_recording_ok", "good");
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
  if (state.ws) {
    flushPendingChunks();
    state.ws.close();
  }
  state.ws = null;
  state.pendingChunks = [];
  if (activeMeetingId && (forceFinish || wasRecording || wasCountingDown)) {
    fetch(`/v1/meetings/${activeMeetingId}/finish`, {
      method: "POST",
      headers: buildHeaders(),
    })
      .then(() => fetchRecords())
      .catch(() => {});
  }
  if (state.stream) {
    state.stream.getTracks().forEach((t) => t.stop());
  }
  state.stream = null;
  state.streamDeviceId = "";
  closeAudioMeter();
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
    if (peak > 0.08) {
      setSignal("signal_ok");
      setStatusHint("signal_check_ok", "good");
    } else if (peak > 0.02) {
      setSignal("signal_low");
      setStatusHint("signal_check_ok", "good");
    } else {
      setSignal("signal_no_audio");
      setStatusHint("signal_check_fail", "bad");
    }

    if (!keepStream) {
      closeAudioMeter();
      if (state.stream) {
        state.stream.getTracks().forEach((t) => t.stop());
      }
      state.stream = null;
      state.streamDeviceId = "";
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
      if (els.transcriptClean) els.transcriptClean.value = await view.text();
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
