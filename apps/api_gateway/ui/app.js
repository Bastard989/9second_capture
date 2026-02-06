const state = {
  lang: "ru",
  ws: null,
  recorder: null,
  stream: null,
  streamMode: "system",
  audioContext: null,
  analyser: null,
  levelTimer: null,
  seq: 0,
  meetingId: null,
  chunkCount: 0,
  countdownTimer: null,
  countdownValue: null,
  isCountingDown: false,
  isUploading: false,
  transcriptMode: "enhanced",
  driverStatusKey: "driver_unknown",
  driverStatusStyle: "muted",
  transcript: {
    raw: new Map(),
    enhanced: new Map(),
  },
};

const i18n = {
  ru: {
    subtitle: "Локальный агент записи встреч",
    connection_title: "Подключение",
    api_key_label: "API ключ (опционально)",
    api_key_placeholder: "X-API-Key",
    device_label: "Источник аудио",
    refresh_devices: "Обновить",
    device_hint: "Выберите виртуальный драйвер захвата системного звука.",
    driver_check: "Проверить драйвер",
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
    countdown_label: "Отсчёт:",
    signal_waiting: "Сигнал: ожидание",
    signal_ok: "Сигнал: есть",
    signal_low: "Сигнал: слабый",
    signal_check: "Проверить захват",
    meeting_id_label: "Meeting ID:",
    chunks_label: "Чанки:",
    transcript_title: "Транскрипт",
    view_raw: "Raw",
    view_enhanced: "Clean",
    records_title: "Результаты",
    records_refresh: "Обновить",
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
    transcript_placeholder: "Здесь появится текст по мере распознавания...",
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
  },
  en: {
    subtitle: "Local meeting capture agent",
    connection_title: "Connection",
    api_key_label: "API key (optional)",
    api_key_placeholder: "X-API-Key",
    device_label: "Audio source",
    refresh_devices: "Refresh",
    device_hint: "Select the virtual driver that captures system audio.",
    driver_check: "Check driver",
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
    countdown_label: "Countdown:",
    signal_waiting: "Signal: waiting",
    signal_ok: "Signal: ok",
    signal_low: "Signal: low",
    signal_check: "Check capture",
    meeting_id_label: "Meeting ID:",
    chunks_label: "Chunks:",
    transcript_title: "Transcript",
    view_raw: "Raw",
    view_enhanced: "Clean",
    records_title: "Results",
    records_refresh: "Refresh",
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
    transcript_placeholder: "Text will appear here as recognition runs...",
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
  },
};

const els = {
  apiKey: document.getElementById("apiKey"),
  deviceSelect: document.getElementById("deviceSelect"),
  refreshDevices: document.getElementById("refreshDevices"),
  checkDriver: document.getElementById("checkDriver"),
  driverStatus: document.getElementById("driverStatus"),
  startBtn: document.getElementById("startBtn"),
  stopBtn: document.getElementById("stopBtn"),
  statusText: document.getElementById("statusText"),
  countdownValue: document.getElementById("countdownValue"),
  levelBar: document.getElementById("levelBar"),
  signalText: document.getElementById("signalText"),
  checkSignal: document.getElementById("checkSignal"),
  meetingIdText: document.getElementById("meetingIdText"),
  chunkCount: document.getElementById("chunkCount"),
  transcriptArea: document.getElementById("transcriptArea"),
  viewRaw: document.getElementById("viewRaw"),
  viewEnhanced: document.getElementById("viewEnhanced"),
  recordsSelect: document.getElementById("recordsSelect"),
  refreshRecords: document.getElementById("refreshRecords"),
  uploadAudio: document.getElementById("uploadAudio"),
  uploadAudioBtn: document.getElementById("uploadAudioBtn"),
  uploadVideo: document.getElementById("uploadVideo"),
  uploadVideoBtn: document.getElementById("uploadVideoBtn"),
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
};

const setStatus = (statusKey, style) => {
  const dict = i18n[state.lang];
  els.statusText.textContent = dict[statusKey] || statusKey;
  els.statusText.className = `status-pill ${style}`;
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

const buildHeaders = () => {
  const headers = { "Content-Type": "application/json" };
  const key = (els.apiKey.value || "").trim();
  if (key) headers["X-API-Key"] = key;
  return headers;
};

const listDevices = async () => {
  try {
    const devices = await navigator.mediaDevices.enumerateDevices();
    const inputs = devices.filter((d) => d.kind === "audioinput");
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
    }
  } catch (err) {
    console.warn("device list failed", err);
  }
};

const getCaptureMode = () => {
  const el = document.querySelector('input[name="captureMode"]:checked');
  return el ? el.value : "system";
};

const ensureStream = async (mode) => {
  if (state.stream && state.streamMode === mode) return state.stream;
  if (state.stream) {
    state.stream.getTracks().forEach((t) => t.stop());
    state.stream = null;
  }
  if (mode === "screen") {
    state.stream = await navigator.mediaDevices.getDisplayMedia({
      video: true,
      audio: true,
    });
  } else {
    const deviceId = els.deviceSelect.value;
    const constraints = {
      audio: deviceId ? { deviceId: { exact: deviceId } } : true,
    };
    state.stream = await navigator.mediaDevices.getUserMedia(constraints);
  }
  state.streamMode = mode;
  return state.stream;
};

const buildAudioMeter = async (mode) => {
  if (state.audioContext) return;
  const stream = await ensureStream(mode);
  state.audioContext = new AudioContext();
  const source = state.audioContext.createMediaStreamSource(stream);
  state.analyser = state.audioContext.createAnalyser();
  state.analyser.fftSize = 1024;
  source.connect(state.analyser);
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
  if (!state.ws || state.ws.readyState !== WebSocket.OPEN) return;
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
  state.ws.send(JSON.stringify(payload));
  state.seq += 1;
  state.chunkCount += 1;
  els.chunkCount.textContent = String(state.chunkCount);
};

const openWebSocket = () => {
  if (state.ws) return;
  const base = window.location.origin.replace("http", "ws");
  const ws = new WebSocket(`${base}/v1/ws`);
  state.ws = ws;
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.event_type === "transcript.update") {
        if (typeof data.seq === "number") {
          if (data.raw_text != null) state.transcript.raw.set(data.seq, data.raw_text);
          if (data.enhanced_text != null) {
            state.transcript.enhanced.set(data.seq, data.enhanced_text);
          }
          renderTranscript();
        }
      }
    } catch (err) {
      console.warn("ws message parse failed", err);
    }
  };
  ws.onclose = () => {
    state.ws = null;
  };
};

const renderTranscript = () => {
  const source =
    state.transcriptMode === "raw" ? state.transcript.raw : state.transcript.enhanced;
  const ordered = Array.from(source.entries())
    .sort((a, b) => a[0] - b[0])
    .map(([, text]) => text)
    .filter(Boolean)
    .join(" ");
  els.transcriptArea.value = ordered;
};

const resetSessionState = () => {
  state.seq = 0;
  state.chunkCount = 0;
  els.chunkCount.textContent = "0";
  state.transcript.raw.clear();
  state.transcript.enhanced.clear();
  els.transcriptArea.value = "";
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
  els.startBtn.disabled = true;
  els.stopBtn.disabled = false;
  resetSessionState();
  els.countdownValue.textContent = "9s";

  try {
    await startCountdown(9);
  } catch (err) {
    setStatus("status_idle", "idle");
    els.startBtn.disabled = false;
    els.stopBtn.disabled = true;
    return;
  }

  setStatus("status_recording", "recording");

  const captureMode = getCaptureMode();
  const res = await fetch("/v1/meetings/start", {
    method: "POST",
    headers: buildHeaders(),
    body: JSON.stringify({
      mode: "realtime",
      context: { source: "local_ui", locale: state.lang, capture_mode: captureMode },
    }),
  });
  if (!res.ok) {
    setStatus("status_error", "error");
    els.startBtn.disabled = false;
    els.stopBtn.disabled = true;
    throw new Error(`start meeting failed: ${res.status}`);
  }
  const data = await res.json();
  state.meetingId = data.meeting_id;
  els.meetingIdText.textContent = state.meetingId;

  await buildAudioMeter(captureMode);
  startMeter();
  openWebSocket();

  const stream = await ensureStream(captureMode);
  const preferred = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/ogg;codecs=opus",
  ];
  let mimeType = "";
  for (const option of preferred) {
    if (MediaRecorder.isTypeSupported(option)) {
      mimeType = option;
      break;
    }
  }
  const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
  state.recorder = recorder;
  recorder.ondataavailable = async (e) => {
    if (e.data && e.data.size > 0) {
      await sendChunk(e.data, mimeType || e.data.type);
    }
  };
  recorder.start(1000);
};

const stopRecording = () => {
  if (state.isCountingDown) {
    state.isCountingDown = false;
  }
  if (state.recorder && state.recorder.state !== "inactive") {
    state.recorder.stop();
  }
  state.recorder = null;
  if (state.ws) {
    state.ws.close();
  }
  state.ws = null;
  if (state.meetingId) {
    fetch(`/v1/meetings/${state.meetingId}/finish`, {
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
  if (state.audioContext) {
    state.audioContext.close();
  }
  state.audioContext = null;
  state.analyser = null;
  stopMeter();
  setStatus("status_idle", "idle");
  els.countdownValue.textContent = "—";
  els.startBtn.disabled = false;
  els.stopBtn.disabled = true;
};

const checkSignal = async () => {
  const mode = getCaptureMode();
  await buildAudioMeter(mode);
  startMeter();
  setTimeout(() => {
    if (!state.recorder) {
      stopMeter();
    }
  }, 2500);
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
    els.startBtn.disabled = false;
    return;
  }
  const data = await res.json();
  state.meetingId = data.meeting_id;
  els.meetingIdText.textContent = state.meetingId;
  openWebSocket();

  const content_b64 = await toBase64(file);
  await fetch(`/v1/meetings/${state.meetingId}/chunks`, {
    method: "POST",
    headers: buildHeaders(),
    body: JSON.stringify({
      seq: 0,
      content_b64,
      codec: file.type || "audio",
      sample_rate: 16000,
      channels: 1,
    }),
  });
  state.chunkCount = 1;
  els.chunkCount.textContent = "1";

  await fetch(`/v1/meetings/${state.meetingId}/finish`, {
    method: "POST",
    headers: buildHeaders(),
  });
  await fetchRecords();

  state.isUploading = false;
  setStatus("status_idle", "idle");
  els.startBtn.disabled = false;
};

const updateCaptureUi = () => {
  const mode = getCaptureMode();
  els.deviceSelect.disabled = mode === "screen";
};

const fetchRecords = async () => {
  try {
    const res = await fetch("/v1/meetings?limit=50", { headers: buildHeaders() });
    if (!res.ok) return;
    const data = await res.json();
    const items = data.items || [];
    els.recordsSelect.innerHTML = "";
    if (!items.length) {
      const opt = document.createElement("option");
      opt.value = "";
      opt.textContent = "—";
      els.recordsSelect.appendChild(opt);
      return;
    }
    items.forEach((item) => {
      const opt = document.createElement("option");
      opt.value = item.meeting_id;
      const created = item.created_at ? new Date(item.created_at).toLocaleString() : "";
      opt.textContent = `${item.meeting_id}${created ? ` (${created})` : ""}`;
      els.recordsSelect.appendChild(opt);
    });
  } catch (err) {
    console.warn("fetch records failed", err);
  }
};

const getSelectedMeeting = () => {
  return els.recordsSelect.value || state.meetingId;
};

const openDownload = (url) => {
  window.open(url, "_blank");
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
    els.transcriptArea.value = text;
    return;
  }

  if (action === "download") {
    const kind = button.dataset.kind;
    openDownload(`/v1/meetings/${meetingId}/artifact?kind=${kind}&fmt=txt`);
    return;
  }

  if (action === "report") {
    const source = button.dataset.source;
    await fetch(`/v1/meetings/${meetingId}/report`, {
      method: "POST",
      headers: buildHeaders(),
      body: JSON.stringify({ source }),
    });
    const view = await fetch(
      `/v1/meetings/${meetingId}/artifact?kind=report&source=${source}&fmt=json`,
      { headers: buildHeaders() }
    );
    if (view.ok) {
      els.transcriptArea.value = await view.text();
    }
    await fetchRecords();
    return;
  }

  if (action === "download-report") {
    const source = button.dataset.source;
    openDownload(`/v1/meetings/${meetingId}/artifact?kind=report&source=${source}&fmt=json`);
    return;
  }

  if (action === "structured") {
    const source = button.dataset.source;
    await fetch(`/v1/meetings/${meetingId}/structured`, {
      method: "POST",
      headers: buildHeaders(),
      body: JSON.stringify({ source }),
    });
    const view = await fetch(
      `/v1/meetings/${meetingId}/artifact?kind=structured&source=${source}&fmt=json`,
      { headers: buildHeaders() }
    );
    if (view.ok) {
      els.transcriptArea.value = await view.text();
    }
    await fetchRecords();
    return;
  }

  if (action === "download-structured-json") {
    const source = button.dataset.source;
    openDownload(
      `/v1/meetings/${meetingId}/artifact?kind=structured&source=${source}&fmt=json`
    );
    return;
  }

  if (action === "download-structured-csv") {
    const source = button.dataset.source;
    openDownload(
      `/v1/meetings/${meetingId}/artifact?kind=structured&source=${source}&fmt=csv`
    );
  }
};

document.querySelectorAll(".lang-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    state.lang = btn.dataset.lang;
    updateI18n();
    renderTranscript();
  });
});

document.querySelectorAll('input[name="captureMode"]').forEach((el) => {
  el.addEventListener("change", updateCaptureUi);
});

els.refreshDevices.addEventListener("click", listDevices);
els.checkDriver.addEventListener("click", checkDriver);
els.refreshRecords.addEventListener("click", fetchRecords);
document.querySelectorAll("[data-action]").forEach((btn) => {
  btn.addEventListener("click", handleRecordAction);
});
els.startBtn.addEventListener("click", async () => {
  try {
    await startRecording();
  } catch (err) {
    console.error(err);
    setStatus("status_error", "error");
  }
});
els.stopBtn.addEventListener("click", stopRecording);
els.checkSignal.addEventListener("click", checkSignal);
els.uploadAudioBtn.addEventListener("click", uploadAudioFile);
els.viewRaw.addEventListener("click", () => {
  state.transcriptMode = "raw";
  els.viewRaw.classList.add("active");
  els.viewEnhanced.classList.remove("active");
  renderTranscript();
});
els.viewEnhanced.addEventListener("click", () => {
  state.transcriptMode = "enhanced";
  els.viewEnhanced.classList.add("active");
  els.viewRaw.classList.remove("active");
  renderTranscript();
});

updateI18n();
listDevices();
updateCaptureUi();
fetchRecords();
