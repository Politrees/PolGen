import { invoke } from "@tauri-apps/api/tauri";
import { open as openDialog } from "@tauri-apps/api/dialog";
import { appWindow } from "@tauri-apps/api/window";
import { readBinaryFile } from "@tauri-apps/api/fs";

type BackendModelsResponse = { models: string[] };
type BackendJobStarted = { job_id: string };
type BackendJobStatus = {
  job_id: string;
  status: "queued" | "running" | "done" | "error";
  progress: number;
  message: string;
  result?: any;
  error?: string | null;
};

type EdgeVoicesResponse = { voices: Record<string, string[]> };
type TabKey = "rvc" | "tts" | "models";

function clamp(n: number, a: number, b: number) { return Math.max(a, Math.min(b, n)); }
function fmtPct(v: number) { return `${Math.round(clamp(v, 0, 1) * 100)}%`; }
function dirname(p: string) { return p.replace(/[\/\\][^\/\\]+$/, ""); }
function basename(p: string) { const m = p.match(/[^\/\\]+$/); return m ? m[0] : p; }
function truncate(s: string, max = 900) { return s.length <= max ? s : s.slice(0, max - 1) + "…"; }

function el<K extends keyof HTMLElementTagNameMap>(tag: K, className?: string, text?: string) {
  const e = document.createElement(tag);
  if (className) e.className = className;
  if (text !== undefined) e.textContent = text;
  return e;
}
function btn(label: string, className = "btn") {
  const b = document.createElement("button");
  b.className = className;
  b.textContent = label;
  return b;
}
function field(labelText: string, inputEl: HTMLElement) {
  const w = el("div", "field");
  w.appendChild(el("label", "", labelText));
  w.appendChild(inputEl);
  return w;
}
function row(left: HTMLElement, right: HTMLElement) {
  const w = el("div", "row");
  w.appendChild(left);
  w.appendChild(right);
  return w;
}
function inputText(placeholder = "") {
  const i = document.createElement("input");
  i.type = "text";
  i.placeholder = placeholder;
  return i;
}
function textarea(placeholder = "") {
  const t = document.createElement("textarea");
  t.placeholder = placeholder;
  return t;
}
function checkbox(label: string, initial = false) {
  const wrap = document.createElement("label");
  wrap.style.display = "flex";
  wrap.style.alignItems = "center";
  wrap.style.gap = "10px";
  wrap.style.cursor = "pointer";

  const c = document.createElement("input");
  c.type = "checkbox";
  c.checked = initial;

  const t = document.createElement("span");
  t.textContent = label;
  t.style.fontSize = "13px";

  wrap.appendChild(c);
  wrap.appendChild(t);
  return { wrap, input: c };
}
function selectEl(options: string[], value?: string) {
  const s = document.createElement("select");
  s.innerHTML = "";
  if (!options.length) {
    const o = document.createElement("option");
    o.value = "";
    o.textContent = "(нет данных)";
    s.appendChild(o);
    s.disabled = true;
    return s;
  }
  for (const opt of options) {
    const o = document.createElement("option");
    o.value = opt;
    o.textContent = opt;
    s.appendChild(o);
  }
  s.disabled = false;
  if (value && options.includes(value)) s.value = value;
  else s.value = options[0];
  return s;
}
async function sleep(ms: number) { return new Promise((r) => setTimeout(r, ms)); }

async function tryCopy(text: string): Promise<boolean> {
  try { await navigator.clipboard.writeText(text); return true; } catch { return false; }
}

class State {
  tab: TabKey = "rvc";
  backendUrl: string | null = null;
  backendReady = false;

  models: string[] = [];
  edgeVoices: Record<string, string[]> = {};

  job: BackendJobStatus | null = null;
  jobId: string | null = null;

  logFollow = true;
  clearTimer: number | null = null;

  installUrl = { url: "", model_name: "" };
  installZip = { zip_path: "", model_name: "" };
  installFiles = { pth_path: "", index_path: "", model_name: "" };

  rvc = {
    input_path: "",
    rvc_model: "",
    f0_method: "rmvpe",
    f0_min: 50,
    f0_max: 1100,
    rvc_pitch: -6,
    protect: 0.5,
    index_rate: 0,
    volume_envelope: 1,
    autopitch: false,
    autopitch_threshold: 155,
    autotune: false,
    autotune_tonic: "C",
    autotune_scale: "chromatic",
    autotune_strength: 1.0,
    stereo_sound: false,
    audio_upscaling: false,
    output_format: "mp3"
  };

  tts = {
    rvc_model: "",
    language: "",
    tts_voice: "",
    tts_text: "",
    tts_rate: 0,
    tts_volume: 0,
    tts_pitch: 0,

    f0_method: "rmvpe",
    f0_min: 50,
    f0_max: 1100,
    rvc_pitch: -6,
    protect: 0.5,
    index_rate: 0,
    volume_envelope: 1,
    autopitch: false,
    autopitch_threshold: 155,
    autotune: false,
    autotune_tonic: "C",
    autotune_scale: "chromatic",
    autotune_strength: 1.0,
    stereo_sound: false,
    audio_upscaling: false,
    output_format: "mp3"
  };
}
const state = new State();

const ui = {
  backendDot: null as HTMLDivElement | null,
  backendText: null as HTMLSpanElement | null,

  navRvc: null as HTMLButtonElement | null,
  navTts: null as HTMLButtonElement | null,
  navModels: null as HTMLButtonElement | null,
  titleText: null as HTMLHeadingElement | null,

  left: null as HTMLDivElement | null,

  kvBackend: null as HTMLSpanElement | null,
  kvJobId: null as HTMLSpanElement | null,
  kvStatus: null as HTMLSpanElement | null,
  kvOutput: null as HTMLSpanElement | null,

  progressText: null as HTMLDivElement | null,
  progressFill: null as HTMLDivElement | null,

  banner: null as HTMLDivElement | null,
  bannerTitle: null as HTMLDivElement | null,
  bannerMsg: null as HTMLDivElement | null,
  bannerBtn1: null as HTMLButtonElement | null,
  bannerBtn2: null as HTMLButtonElement | null,

  logDetails: null as HTMLDetailsElement | null,
  logBox: null as HTMLDivElement | null,
  followChk: null as HTMLInputElement | null,

  es: null as EventSource | null
};

function setBackendBadge(ok: boolean, url: string | null) {
  if (!ui.backendDot || !ui.backendText) return;
  ui.backendDot.classList.remove("ok", "warn", "err");
  ui.backendDot.classList.add(ok ? "ok" : "warn");
  ui.backendText.textContent = ok ? `Backend: OK (${url})` : "Backend: запуск...";
}

function appendLog(line: string) {
  if (!ui.logBox) return;
  ui.logBox.appendChild(document.createTextNode(line + "\n"));
  if (state.logFollow) ui.logBox.scrollTop = ui.logBox.scrollHeight;
}

function showBanner(kind: "warn" | "error", title: string, message: string) {
  if (!ui.banner || !ui.bannerTitle || !ui.bannerMsg) return;
  ui.banner.classList.add("show");
  ui.banner.classList.toggle("error", kind === "error");
  ui.bannerTitle.textContent = title;
  ui.bannerMsg.textContent = truncate(message, 900);
  ui.bannerMsg.title = message;
}

function hideBanner() {
  if (!ui.banner || !ui.bannerTitle || !ui.bannerMsg) return;
  ui.banner.classList.remove("show", "error");
  ui.bannerTitle.textContent = "";
  ui.bannerMsg.textContent = "";
  ui.bannerMsg.title = "";
}

function resetProgressSoon() {
  if (state.clearTimer) window.clearTimeout(state.clearTimer);
  state.clearTimer = window.setTimeout(() => {
    if (!state.job) return;
    if (state.job.status === "done" || state.job.status === "error") {
      setJob(null);
    }
  }, 8000);
}

function beginNewAction() {
  if (state.clearTimer) window.clearTimeout(state.clearTimer);
  hideBanner();
  setJob({ job_id: "-", status: "running", progress: 0, message: "Запуск...", result: null, error: null });
}

function setTab(tab: TabKey) {
  state.tab = tab;
  ui.navRvc?.classList.toggle("active", tab === "rvc");
  ui.navTts?.classList.toggle("active", tab === "tts");
  ui.navModels?.classList.toggle("active", tab === "models");

  if (ui.titleText) {
    ui.titleText.textContent =
      tab === "rvc" ? "RVC • Конвертация аудио" :
      tab === "tts" ? "TTS → RVC • Синтез и конвертация" :
      "Модели • Установка/Удаление";
  }
  renderLeft();
}

function setJob(job: BackendJobStatus | null) {
  state.job = job;

  if (ui.kvBackend) ui.kvBackend.textContent = state.backendUrl ?? "";
  if (ui.kvJobId) ui.kvJobId.textContent = state.jobId ?? "-";
  if (ui.kvStatus) ui.kvStatus.textContent = job?.status ?? "-";

  const outFull = job?.result?.output_path;
  const outShown = typeof outFull === "string" ? basename(outFull) : "-";
  if (ui.kvOutput) {
    ui.kvOutput.textContent = outShown;
    ui.kvOutput.title = typeof outFull === "string" ? outFull : "";
  }

  const isError = job?.status === "error";
  const progress = isError ? 0 : (job?.progress ?? 0);
  const msg = isError ? "Ошибка. См. баннер и логи." : (job?.message ?? "");

  if (ui.progressText) ui.progressText.textContent = job ? `${fmtPct(progress)} • ${msg}` : "Пока задач нет.";
  if (ui.progressFill) ui.progressFill.style.width = `${Math.round(progress * 100)}%`;

  if (isError && typeof job?.error === "string" && job.error.trim()) {
    showBanner("error", "Ошибка", job.error);
    if (ui.bannerBtn1) {
      ui.bannerBtn1.textContent = "Копировать";
      ui.bannerBtn1.onclick = async () => {
        const ok = await tryCopy(job.error!);
        appendLog(ok ? "[UI] Ошибка скопирована." : "[UI] Не удалось скопировать.");
      };
    }
    if (ui.bannerBtn2 && ui.logDetails) {
      ui.bannerBtn2.textContent = "Логи";
      ui.bannerBtn2.onclick = () => { ui.logDetails!.open = true; };
    }
    resetProgressSoon();
  }

  if (job && (job.status === "done")) {
    resetProgressSoon();
  }
}

function stopSSE() {
  if (ui.es) {
    try { ui.es.close(); } catch {}
    ui.es = null;
  }
}

async function connectBackendOrShowBanner() {
  showBanner("warn", "Подключение к backend…", "Ожидаем локальный backend. Если не подключится — нажми Restart backend.");

  if (ui.bannerBtn1) {
    ui.bannerBtn1.textContent = "Restart backend";
    ui.bannerBtn1.onclick = async () => {
      try {
        await invoke("backend_restart");
        appendLog("[UI] backend_restart вызван.");
        await sleep(400);
        await connectBackendOrShowBanner();
      } catch (e) {
        appendLog(`[UI] backend_restart error: ${String(e)}`);
      }
    };
  }
  if (ui.bannerBtn2) {
    ui.bannerBtn2.textContent = "Retry";
    ui.bannerBtn2.onclick = async () => {
      await connectBackendOrShowBanner();
    };
  }

  for (let i = 0; i < 220; i++) {
    const url = await invoke<string | null>("backend_get_url");
    if (typeof url === "string" && url.startsWith("http")) {
      state.backendUrl = url;
      state.backendReady = true;
      setBackendBadge(true, url);
      appendLog(`[UI] Backend URL: ${url}`);

      const h = await fetch(`${url}/health`);
      if (!h.ok) {
        state.backendReady = false;
        setBackendBadge(false, null);
        showBanner("warn", "Backend не отвечает", `health status ${h.status}`);
        return;
      }

      hideBanner();
      await loadModels();
      await loadEdgeVoices();
      renderLeft();
      return;
    }
    await sleep(150);
  }

  state.backendReady = false;
  setBackendBadge(false, null);
  showBanner("warn", "Backend не найден", "Не удалось получить backend URL. Нажми Restart backend.");
}

function attachSSE(jobId: string) {
  stopSSE();
  if (!state.backendUrl) return;

  const es = new EventSource(`${state.backendUrl}/jobs/${jobId}/events`);
  ui.es = es;

  es.onmessage = (ev) => {
    try {
      const msg = JSON.parse(ev.data);

      if (msg.type === "progress") {
        if (!state.job) state.job = { job_id: jobId, status: "running", progress: 0, message: "" };
        state.job.progress = Number(msg.progress ?? state.job.progress);
        state.job.message = String(msg.message ?? state.job.message);
        setJob(state.job);
        appendLog(`[${fmtPct(state.job.progress)}] ${state.job.message}`);
      }

      if (msg.type === "status") {
        if (!state.job) state.job = { job_id: jobId, status: "running", progress: 0, message: "" };
        state.job.status = msg.status;
        state.job.message = String(msg.message ?? state.job.message);
        setJob(state.job);
        appendLog(`[STATUS] ${state.job.status} • ${state.job.message}`);
        if (state.job.status === "done" || state.job.status === "error") stopSSE();
      }

      if (msg.type === "error") {
        appendLog(`[ERROR] ${String(msg.error ?? "")}`);
      }
      if (msg.type === "log") {
        appendLog(String(msg.line ?? ""));
      }
    } catch (e) {
      appendLog(`[UI] SSE parse error: ${String(e)}`);
    }
  };

  es.onerror = () => {
    stopSSE();
    appendLog("[UI] SSE closed/errored.");
  };
}

async function pollJobUntilDone(jobId: string) {
  if (!state.backendUrl) return;
  for (let i = 0; i < 2000; i++) {
    const r = await fetch(`${state.backendUrl}/jobs/${jobId}`);
    const data = (await r.json()) as BackendJobStatus;
    state.job = data;
    setJob(data);
    if (data.status === "done" || data.status === "error") {
      stopSSE();
      return;
    }
    await sleep(250);
  }
}

async function startRvc() {
  if (!state.backendUrl) return;
  if (!state.rvc.input_path.trim()) { appendLog("[UI] input_path пустой."); return; }
  if (!state.rvc.rvc_model.trim()) { appendLog("[UI] rvc_model пустой."); return; }

  beginNewAction();
  appendLog("[UI] Создаём RVC job…");
  const r = await fetch(`${state.backendUrl}/jobs/convert`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(state.rvc)
  });

  if (!r.ok) {
    const txt = await r.text().catch(() => "");
    appendLog(`[UI] Ошибка POST /jobs/convert: ${r.status} ${txt}`);
    state.jobId = "-";
    setJob({ job_id: "-", status: "error", progress: 0, message: "Ошибка", error: txt });
    return;
  }

  const data = (await r.json()) as BackendJobStarted;
  state.jobId = data.job_id;
  setJob({ job_id: data.job_id, status: "queued", progress: 0, message: "queued" });
  attachSSE(data.job_id);
  await pollJobUntilDone(data.job_id);
}

async function startTts() {
  if (!state.backendUrl) return;
  if (!state.tts.tts_text.trim()) { appendLog("[UI] tts_text пустой."); return; }
  if (!state.tts.tts_voice.trim()) { appendLog("[UI] tts_voice пустой."); return; }
  if (!state.tts.rvc_model.trim()) { appendLog("[UI] rvc_model пустой."); return; }

  beginNewAction();
  appendLog("[UI] Создаём TTS → RVC job…");
  const r = await fetch(`${state.backendUrl}/jobs/tts_convert`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(state.tts)
  });

  if (!r.ok) {
    const txt = await r.text().catch(() => "");
    appendLog(`[UI] Ошибка POST /jobs/tts_convert: ${r.status} ${txt}`);
    state.jobId = "-";
    setJob({ job_id: "-", status: "error", progress: 0, message: "Ошибка", error: txt });
    return;
  }

  const data = (await r.json()) as BackendJobStarted;
  state.jobId = data.job_id;
  setJob({ job_id: data.job_id, status: "queued", progress: 0, message: "queued" });
  attachSSE(data.job_id);
  await pollJobUntilDone(data.job_id);
}

async function installModelUrl() {
  if (!state.backendUrl) return;
  if (!state.installUrl.url.trim()) { appendLog("[UI] URL пустой."); return; }
  if (!state.installUrl.model_name.trim()) { appendLog("[UI] model_name пустой."); return; }

  beginNewAction();
  appendLog("[UI] Создаём job установки модели по URL…");
  const r = await fetch(`${state.backendUrl}/jobs/models/install_url`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(state.installUrl)
  });

  if (!r.ok) {
    const txt = await r.text().catch(() => "");
    appendLog(`[UI] install_url error: ${r.status} ${txt}`);
    setJob({ job_id: "-", status: "error", progress: 0, message: "Ошибка", error: txt });
    return;
  }

  const data = (await r.json()) as BackendJobStarted;
  state.jobId = data.job_id;
  setJob({ job_id: data.job_id, status: "queued", progress: 0, message: "queued" });
  attachSSE(data.job_id);
  await pollJobUntilDone(data.job_id);
  await loadModels();
  renderLeft();
}

async function _pathToBlob(path: string): Promise<{ blob: Blob; filename: string }> {
  const bytes = await readBinaryFile(path);
  const blob = new Blob([bytes]);
  return { blob, filename: basename(path) };
}

async function installModelZip() {
  if (!state.backendUrl) return;
  if (!state.installZip.zip_path.trim()) return;
  
  beginNewAction();
  appendLog("[UI] Передача пути ZIP в бэкенд...");

  const r = await fetch(`${state.backendUrl}/jobs/models/install_local_zip`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      path: state.installZip.zip_path,
      model_name: state.installZip.model_name
    })
  });
  
  processInstallResponse(r);
}

async function installModelFiles() {
  if (!state.backendUrl) return;
  if (!state.installFiles.pth_path.trim()) return;

  beginNewAction();
  appendLog("[UI] Передача путей файлов в бэкенд...");

  const r = await fetch(`${state.backendUrl}/jobs/models/install_local_files`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      path: state.installFiles.pth_path,
      extra_path: state.installFiles.index_path,
      model_name: state.installFiles.model_name
    })
  });

  processInstallResponse(r);
}

async function processInstallResponse(r: Response) {
  if (!r.ok) {
    const txt = await r.text();
    setJob({ job_id: "-", status: "error", progress: 0, message: "Ошибка", error: txt });
    return;
  }
  const data = await r.json();
  state.jobId = data.job_id;
  setJob({ job_id: data.job_id, status: "queued", progress: 0, message: "Ожидание..." });
  attachSSE(data.job_id);
  await pollJobUntilDone(data.job_id);
  await loadModels();
  renderLeft();
}

async function deleteModel(modelName: string) {
  if (!state.backendUrl) return;
  const r = await fetch(`${state.backendUrl}/models/rvc/${encodeURIComponent(modelName)}`, { method: "DELETE" });
  if (!r.ok) {
    const txt = await r.text().catch(() => "");
    appendLog(`[UI] delete error: ${r.status} ${txt}`);
    return;
  }
  appendLog(`[UI] deleted: ${modelName}`);
  await loadModels();
  renderLeft();
}

async function openModelFolder(modelName: string) {
  try {
    await invoke("open_rvc_model_dir", { modelName });
  } catch (e) {
    appendLog(`[UI] open model dir error: ${String(e)}`);
  }
}

async function loadModels() {
  if (!state.backendUrl) return;
  const r = await fetch(`${state.backendUrl}/models/rvc`);
  const data = (await r.json()) as BackendModelsResponse;
  state.models = Array.isArray(data.models) ? data.models : [];
  appendLog(`[UI] models: ${state.models.join(", ") || "(empty)"}`);

  if (state.models.length) {
    if (!state.rvc.rvc_model) state.rvc.rvc_model = state.models[0];
    if (!state.tts.rvc_model) state.tts.rvc_model = state.models[0];
  }
}

async function loadEdgeVoices() {
  if (!state.backendUrl) return;
  const r = await fetch(`${state.backendUrl}/voices/edge`);
  const data = (await r.json()) as EdgeVoicesResponse;
  state.edgeVoices = data.voices ?? {};
  appendLog(`[UI] edge voices loaded: ${Object.keys(state.edgeVoices).length} languages`);

  const langs = Object.keys(state.edgeVoices);
  if (!state.tts.language && langs.length) state.tts.language = langs[0];
  const voices = state.edgeVoices[state.tts.language] ?? [];
  if (!state.tts.tts_voice && voices.length) state.tts.tts_voice = voices[0];
}

function mount() {
  const root = document.querySelector("#app") as HTMLElement;
  root.innerHTML = "";

  const app = el("div", "app");
  root.appendChild(app);

  // sidebar
  const sidebar = el("div", "sidebar");
  app.appendChild(sidebar);

  const brand = el("div", "brand");
  brand.appendChild(el("div", "logo"));
  const title = el("div", "title");
  title.appendChild(el("b", "", "PolGen Desktop"));
  // title.appendChild(el("span", "", "Model Manager + RVC"));
  brand.appendChild(title);
  sidebar.appendChild(brand);

  const nav = el("div", "nav");
  sidebar.appendChild(nav);

  ui.navRvc = btn("RVC", "btn");
  ui.navTts = btn("TTS → RVC", "btn");
  ui.navModels = btn("Модели", "btn");
  ui.navRvc.onclick = () => setTab("rvc");
  ui.navTts.onclick = () => setTab("tts");
  ui.navModels.onclick = () => setTab("models");
  nav.appendChild(ui.navRvc);
  nav.appendChild(ui.navTts);
  nav.appendChild(ui.navModels);

  const statusBox = el("div", "status");
  const badge = el("div", "badge");
  ui.backendDot = el("div", "dot warn");
  ui.backendText = el("span", "", "Backend: запуск...");
  badge.appendChild(ui.backendDot);
  badge.appendChild(ui.backendText);
  statusBox.appendChild(badge);
  sidebar.appendChild(statusBox);

  // main
  const main = el("div", "main");
  app.appendChild(main);

  const titlebar = el("div", "titlebar");
  ui.titleText = el("h1", "", "PolGen Desktop");
  const spacer = el("div", "spacer");
  const refresh = btn("Обновить");
  refresh.onclick = async () => {
    if (!state.backendUrl) return;
    await loadModels();
    await loadEdgeVoices();
    renderLeft();
  };

  const winBtns = el("div", "windowBtns");
  const bMin = el("button", "winBtn", "—");
  const bMax = el("button", "winBtn", "□");
  const bClose = el("button", "winBtn close", "×");
  bMin.onclick = () => appWindow.minimize();
  bMax.onclick = () => appWindow.toggleMaximize();
  bClose.onclick = () => appWindow.close();
  winBtns.appendChild(bMin);
  winBtns.appendChild(bMax);
  winBtns.appendChild(bClose);

  titlebar.onmousedown = async (ev) => {
    if (ev.button !== 0) return;
    const target = ev.target as HTMLElement | null;
    if (!target) return;
    if (target.closest("button, input, select, textarea")) return;
    try { await appWindow.startDragging(); } catch {}
  };

  titlebar.appendChild(ui.titleText);
  titlebar.appendChild(spacer);
  titlebar.appendChild(refresh);
  titlebar.appendChild(winBtns);
  main.appendChild(titlebar);

  const content = el("div", "content");
  main.appendChild(content);

  const left = el("div", "");
  const right = el("div", "");
  content.appendChild(left);
  content.appendChild(right);
  ui.left = left;

  // right card
  const rightCard = el("div", "card");
  right.appendChild(rightCard);

  rightCard.appendChild(el("h2", "", "Задача / Прогресс"));

  ui.banner = el("div", "banner");
  const bannerHead = el("div", "bannerHead");
  ui.bannerTitle = el("div", "bannerTitle", "");
  const bannerBtns = el("div", "bannerBtns");
  ui.bannerBtn1 = btn("", "btn");
  ui.bannerBtn2 = btn("", "btn");
  bannerBtns.appendChild(ui.bannerBtn1);
  bannerBtns.appendChild(ui.bannerBtn2);
  bannerHead.appendChild(ui.bannerTitle);
  bannerHead.appendChild(bannerBtns);
  ui.banner.appendChild(bannerHead);
  ui.bannerMsg = el("div", "bannerMsg", "");
  ui.banner.appendChild(ui.bannerMsg);
  rightCard.appendChild(ui.banner);

  const kv = el("div", "kv");
  const mkLine = (k: string) => {
    const line = el("div", "");
    line.innerHTML = `<div>${k}</div><b>-</b>`;
    return line;
  };

  const backendLine = mkLine("Backend");
  const jobLine = mkLine("Job ID");
  const stLine = mkLine("Status");
  const outLine = mkLine("Output");

  ui.kvBackend = backendLine.querySelector("b")!;
  ui.kvJobId = jobLine.querySelector("b")!;
  ui.kvStatus = stLine.querySelector("b")!;
  ui.kvOutput = outLine.querySelector("b")!;

  kv.appendChild(backendLine);
  kv.appendChild(jobLine);
  kv.appendChild(stLine);
  kv.appendChild(outLine);
  rightCard.appendChild(kv);

  rightCard.appendChild(el("div", "hr"));

  ui.progressText = el("div", "small", "Пока задач нет.");
  const pBar = el("div", "progressBar");
  ui.progressFill = el("div", "");
  pBar.appendChild(ui.progressFill);
  rightCard.appendChild(ui.progressText);
  rightCard.appendChild(pBar);

  rightCard.appendChild(el("div", "hr"));

  ui.logDetails = document.createElement("details");
  const summary = document.createElement("summary");
  summary.textContent = "Логи";
  ui.logDetails.appendChild(summary);

  ui.logBox = el("div", "log") as HTMLDivElement;
  ui.logBox.addEventListener("scroll", () => {
    const nearBottom = ui.logBox!.scrollTop + ui.logBox!.clientHeight >= ui.logBox!.scrollHeight - 10;
    state.logFollow = nearBottom;
    if (ui.followChk) ui.followChk.checked = state.logFollow;
  });

  ui.logDetails.appendChild(ui.logBox);

  const followRow = el("div", "row");
  const f = checkbox("Авто-прокрутка вниз", state.logFollow);
  ui.followChk = f.input;
  f.input.onchange = () => {
    state.logFollow = f.input.checked;
    if (state.logFollow && ui.logBox) ui.logBox.scrollTop = ui.logBox.scrollHeight;
  };
  const clear = btn("Очистить");
  clear.onclick = () => { if (ui.logBox) ui.logBox.textContent = ""; };
  followRow.appendChild(f.wrap);
  followRow.appendChild(clear);
  ui.logDetails.appendChild(followRow);

  rightCard.appendChild(ui.logDetails);

  hideBanner();
  setBackendBadge(false, null);
  setTab("models");
  setJob(null);
}

function renderLeft() {
  if (!ui.left) return;
  ui.left.innerHTML = "";

  const card = el("div", "card");
  ui.left.appendChild(card);

  if (!state.backendReady) {
    card.appendChild(el("div", "", "Backend не готов."));
    return;
  }

  if (state.tab === "models") {
    card.appendChild(el("h2", "", "RVC модели"));

    // compact chips
    const chips = el("div", "chips");
    for (const m of state.models) {
      const chip = el("div", "chip");
      const name = el("div", "chipName", m);
      name.title = m;
      const actions = el("div", "chipActions");

      const bFolder = el("button", "iconBtn", "📁") as HTMLButtonElement;
      bFolder.title = "Открыть папку модели";
      bFolder.onclick = () => openModelFolder(m);

      const bDel = el("button", "iconBtn danger", "🗑") as HTMLButtonElement;
      bDel.title = "Удалить модель";
      bDel.onclick = () => deleteModel(m);

      actions.appendChild(bFolder);
      actions.appendChild(bDel);

      chip.appendChild(name);
      chip.appendChild(actions);
      chips.appendChild(chip);
    }

    card.appendChild(chips);
    card.appendChild(el("div", "hr"));

    // URL accordion
    const d1 = document.createElement("details");
    d1.open = false;
    const s1 = document.createElement("summary");
    s1.textContent = "Установка по ссылке (URL на ZIP)";
    d1.appendChild(s1);

    const urlInp = inputText("URL на ZIP...");
    urlInp.value = state.installUrl.url;
    urlInp.oninput = () => (state.installUrl.url = urlInp.value);

    const nameInp = inputText("Имя модели...");
    nameInp.value = state.installUrl.model_name;
    nameInp.oninput = () => (state.installUrl.model_name = nameInp.value);

    d1.appendChild(field("URL", urlInp));
    d1.appendChild(field("Имя модели", nameInp));
    const run = btn("Установить", "btn primary");
    run.onclick = () => installModelUrl();
    d1.appendChild(run);
    card.appendChild(d1);

    card.appendChild(el("div", "hr"));

    // ZIP accordion
    const d2 = document.createElement("details");
    d2.open = false;
    const s2 = document.createElement("summary");
    s2.textContent = "Распаковка из ZIP";
    d2.appendChild(s2);

    const zipPath = inputText("Путь к ZIP...");
    zipPath.value = state.installZip.zip_path;
    zipPath.oninput = () => (state.installZip.zip_path = zipPath.value);

    const pickZip = btn("Выбрать ZIP");
    pickZip.onclick = async () => {
      const selected = await openDialog({ multiple: false, directory: false, filters: [{ name: "ZIP", extensions: ["zip"] }] });
      if (typeof selected === "string") {
        state.installZip.zip_path = selected;
        zipPath.value = selected;
      }
    };

    const zipName = inputText("Имя модели...");
    zipName.value = state.installZip.model_name;
    zipName.oninput = () => (state.installZip.model_name = zipName.value);

    d2.appendChild(field("ZIP", row(zipPath, pickZip)));
    d2.appendChild(field("Имя модели", zipName));
    const runZip = btn("Распаковать ZIP", "btn primary");
    runZip.onclick = () => installModelZip();
    d2.appendChild(runZip);
    card.appendChild(d2);

    card.appendChild(el("div", "hr"));

    // Files accordion
    const d3 = document.createElement("details");
    d3.open = false;
    const s3 = document.createElement("summary");
    s3.textContent = "Загрузка .pth/.index";
    d3.appendChild(s3);

    const pthPath = inputText("Путь к .pth...");
    pthPath.value = state.installFiles.pth_path;
    pthPath.oninput = () => (state.installFiles.pth_path = pthPath.value);

    const pickPth = btn("Выбрать .pth");
    pickPth.onclick = async () => {
      const selected = await openDialog({ multiple: false, directory: false, filters: [{ name: "PTH", extensions: ["pth"] }] });
      if (typeof selected === "string") {
        state.installFiles.pth_path = selected;
        pthPath.value = selected;
      }
    };

    const idxPath = inputText("Путь к .index (необязательно)...");
    idxPath.value = state.installFiles.index_path;
    idxPath.oninput = () => (state.installFiles.index_path = idxPath.value);

    const pickIdx = btn("Выбрать .index");
    pickIdx.onclick = async () => {
      const selected = await openDialog({ multiple: false, directory: false, filters: [{ name: "INDEX", extensions: ["index"] }] });
      if (typeof selected === "string") {
        state.installFiles.index_path = selected;
        idxPath.value = selected;
      }
    };

    const filesName = inputText("Имя модели...");
    filesName.value = state.installFiles.model_name;
    filesName.oninput = () => (state.installFiles.model_name = filesName.value);

    d3.appendChild(field(".pth", row(pthPath, pickPth)));
    d3.appendChild(field(".index", row(idxPath, pickIdx)));
    d3.appendChild(field("Имя модели", filesName));
    const runFiles = btn("Загрузить файлы", "btn primary");
    runFiles.onclick = () => installModelFiles();
    d3.appendChild(runFiles);
    card.appendChild(d3);

    return;
  }

  // RVC / TTS UI тут можно оставить минимальным, как раньше; сейчас фокус — models manager
  if (state.tab === "rvc") {
    card.appendChild(el("h2", "", "RVC"));
    const inp = inputText("Путь к аудио…");
    inp.value = state.rvc.input_path;
    inp.oninput = () => (state.rvc.input_path = inp.value);

    const pick = btn("Выбрать файл");
    pick.onclick = async () => {
      const selected = await openDialog({ multiple: false, directory: false, filters: [{ name: "Audio", extensions: ["mp3", "wav", "flac", "ogg", "m4a"] }] });
      if (typeof selected === "string") {
        state.rvc.input_path = selected;
        inp.value = selected;
      }
    };
    card.appendChild(field("Входной файл", row(inp, pick)));

    const model = selectEl(state.models, state.rvc.rvc_model || state.models[0]);
    model.onchange = () => (state.rvc.rvc_model = model.value);
    card.appendChild(field("RVC модель", model));

    const run = btn("Запустить", "btn primary");
    run.onclick = () => startRvc();
    card.appendChild(run);
    return;
  }

  card.appendChild(el("h2", "", "TTS → RVC"));
  const run = btn("Запустить TTS", "btn primary");
  run.onclick = () => startTts();
  card.appendChild(run);
}

async function bootstrap() {
  mount();
  appendLog("[UI] запуск…");
  await connectBackendOrShowBanner();
  setTab("models");
}

window.addEventListener("DOMContentLoaded", () => {
  bootstrap().catch((e) => {
    appendLog(`[UI] bootstrap error: ${String(e)}`);
    showBanner("error", "UI error", String(e));
  });
});