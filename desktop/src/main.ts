import { invoke, convertFileSrc } from "@tauri-apps/api/tauri";
import { open as openDialog } from "@tauri-apps/api/dialog";
import { appWindow } from "@tauri-apps/api/window";

// ═══════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════

interface JobSnapshot {
  job_id: string;
  status: "queued" | "running" | "done" | "error";
  progress: number;
  message: string;
  result?: Record<string, any> | null;
  error?: string | null;
}

type TabKey = "rvc" | "tts" | "models";

// ═══════════════════════════════════════════════════════════════
// DOM Helpers
// ═══════════════════════════════════════════════════════════════

function h<K extends keyof HTMLElementTagNameMap>(tag: K, cls?: string, text?: string): HTMLElementTagNameMap[K] {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}

function btn(label: string, cls = "btn"): HTMLButtonElement {
  const b = document.createElement("button");
  b.className = cls;
  b.textContent = label;
  return b;
}

function fieldWrap(label: string, ...children: HTMLElement[]): HTMLDivElement {
  const w = h("div", "field");
  w.appendChild(h("label", "", label));
  for (const c of children) w.appendChild(c);
  return w;
}

function makeSelect(options: string[], value?: string): HTMLSelectElement {
  const s = document.createElement("select");
  if (!options.length) {
    const o = document.createElement("option");
    o.value = "";
    o.textContent = "(нет)";
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

function makeInput(placeholder = ""): HTMLInputElement {
  const i = document.createElement("input");
  i.type = "text";
  i.placeholder = placeholder;
  return i;
}

function makeSlider(min: number, max: number, step: number, value: number) {
  const wrap = h("div", "slider-row");
  const input = document.createElement("input");
  input.type = "range";
  input.min = String(min);
  input.max = String(max);
  input.step = String(step);
  input.value = String(value);
  const display = h("span", "slider-val", String(value));
  input.oninput = () => { display.textContent = input.value; };
  wrap.appendChild(input);
  wrap.appendChild(display);
  return { wrap, input, display };
}

function makeCheckbox(label: string, checked = false) {
  const wrap = document.createElement("label");
  wrap.className = "checkbox-wrap";
  const input = document.createElement("input");
  input.type = "checkbox";
  input.checked = checked;
  wrap.appendChild(input);
  wrap.appendChild(h("span", "", label));
  return { wrap, input };
}

function makeRow(...children: HTMLElement[]): HTMLDivElement {
  const r = h("div", "row");
  for (const c of children) r.appendChild(c);
  return r;
}

function makeAccordion(title: string, open = false) {
  const details = document.createElement("details");
  details.open = open;
  const summary = document.createElement("summary");
  summary.textContent = title;
  details.appendChild(summary);
  const content = h("div", "accordion-body");
  details.appendChild(content);
  return { details, content };
}

function addSelect(parent: HTMLElement, label: string, obj: Record<string, any>, key: string, options: string[], defaultVal?: string): HTMLSelectElement {
  const sel = makeSelect(options, obj[key] || defaultVal);
  sel.onchange = () => { obj[key] = sel.value; };
  parent.appendChild(fieldWrap(label, sel));
  return sel;
}

function addSlider(parent: HTMLElement, label: string, obj: Record<string, any>, key: string, min: number, max: number, step: number): HTMLInputElement {
  const s = makeSlider(min, max, step, obj[key] ?? min);
  s.input.oninput = () => { obj[key] = parseFloat(s.input.value); s.display.textContent = s.input.value; };
  parent.appendChild(fieldWrap(label, s.wrap));
  return s.input;
}

function addCheckbox(parent: HTMLElement, label: string, obj: Record<string, any>, key: string): HTMLInputElement {
  const c = makeCheckbox(label, !!obj[key]);
  c.input.onchange = () => { obj[key] = c.input.checked; };
  parent.appendChild(c.wrap);
  return c.input;
}

function addInput(parent: HTMLElement, label: string, obj: Record<string, any>, key: string, placeholder = ""): HTMLInputElement {
  const inp = makeInput(placeholder);
  inp.value = obj[key] || "";
  inp.oninput = () => { obj[key] = inp.value; };
  parent.appendChild(fieldWrap(label, inp));
  return inp;
}

// ═══════════════════════════════════════════════════════════════
// Utility
// ═══════════════════════════════════════════════════════════════

function clamp(n: number, a: number, b: number) { return Math.max(a, Math.min(b, n)); }
function fmtPct(v: number) { return `${Math.round(clamp(v, 0, 1) * 100)}%`; }
function basename(p: string) { return p.match(/[^\/\\]+$/)?.[0] || p; }
function truncate(s: string, max = 900) { return s.length <= max ? s : s.slice(0, max - 1) + "…"; }
function formatTime(s: number): string {
  if (!isFinite(s) || s < 0) return "0:00";
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${sec.toString().padStart(2, "0")}`;
}
async function sleep(ms: number) { return new Promise((r) => setTimeout(r, ms)); }
async function tryCopy(text: string) { try { await navigator.clipboard.writeText(text); return true; } catch { return false; } }

// ═══════════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════════

const F0_METHODS = ["rmvpe+", "rmvpe", "fcpe", "crepe", "crepe-tiny"];
const OUTPUT_FORMATS = ["wav", "flac", "mp3", "ogg", "m4a"];
const TONIC_NOTES = ["C", "C#", "Db", "D", "D#", "Eb", "E", "F", "F#", "Gb", "G", "G#", "Ab", "A", "A#", "Bb", "B"];
const SCALES = ["chromatic", "major", "minor", "dorian", "phrygian", "lydian", "mixolydian", "harmonic_minor", "melodic_minor", "pentatonic_major", "pentatonic_minor", "blues"];

// ═══════════════════════════════════════════════════════════════
// State
// ═══════════════════════════════════════════════════════════════

class State {
  tab: TabKey = "models";
  backendUrl: string | null = null;
  backendReady = false;
  models: string[] = [];
  edgeVoices: Record<string, string[]> = {};
  job: JobSnapshot | null = null;
  jobId: string | null = null;
  logFollow = true;
  clearTimer: number | null = null;
  playerPath: string | null = null;

  installUrl = { url: "", model_name: "" };
  installZip = { zip_path: "", model_name: "" };
  installFiles = { pth_path: "", index_path: "", model_name: "" };

  rvc = {
    input_path: "", rvc_model: "",
    f0_method: "rmvpe", f0_min: 50, f0_max: 1100, rvc_pitch: 0,
    protect: 0.5, index_rate: 0, volume_envelope: 1,
    autopitch: false, autopitch_threshold: 155,
    autotune: false, autotune_tonic: "C", autotune_scale: "chromatic", autotune_strength: 1.0,
    stereo_sound: false, audio_upscaling: false, output_format: "mp3",
  };

  tts = {
    rvc_model: "", language: "", tts_voice: "", tts_text: "",
    tts_rate: 0, tts_volume: 0, tts_pitch: 0,
    f0_method: "rmvpe", f0_min: 50, f0_max: 1100, rvc_pitch: 0,
    protect: 0.5, index_rate: 0, volume_envelope: 1,
    autopitch: false, autopitch_threshold: 155,
    autotune: false, autotune_tonic: "C", autotune_scale: "chromatic", autotune_strength: 1.0,
    stereo_sound: false, audio_upscaling: false, output_format: "mp3",
  };
}

const state = new State();
let isSeeking = false;

// ═══════════════════════════════════════════════════════════════
// UI Refs
// ═══════════════════════════════════════════════════════════════

const ui = {
  backendDot: null as HTMLDivElement | null,
  backendText: null as HTMLSpanElement | null,
  navRvc: null as HTMLButtonElement | null,
  navTts: null as HTMLButtonElement | null,
  navModels: null as HTMLButtonElement | null,
  titleText: null as HTMLHeadingElement | null,
  left: null as HTMLDivElement | null,
  kvJobId: null as HTMLElement | null,
  kvStatus: null as HTMLElement | null,
  kvOutput: null as HTMLElement | null,
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
  playerFooter: null as HTMLDivElement | null,
  playerAudio: null as HTMLAudioElement | null,
  playerPlayBtn: null as HTMLButtonElement | null,
  playerSeek: null as HTMLInputElement | null,
  playerTimeCurrent: null as HTMLSpanElement | null,
  playerTimeTotal: null as HTMLSpanElement | null,
  playerFilename: null as HTMLSpanElement | null,
  playerBtnFile: null as HTMLButtonElement | null,
  playerBtnFolder: null as HTMLButtonElement | null,
  es: null as EventSource | null,
};

// ═══════════════════════════════════════════════════════════════
// Player Logic
// ═══════════════════════════════════════════════════════════════

function stopPlayer() {
  const audio = ui.playerAudio;
  if (!audio) return;
  audio.pause();
  audio.currentTime = 0;
  if (ui.playerPlayBtn) ui.playerPlayBtn.textContent = "▶";
}

function loadPlayerAudio(path: string) {
  state.playerPath = path;
  const audio = ui.playerAudio;
  if (!audio) return;
  audio.pause(); audio.currentTime = 0; audio.removeAttribute("src");
  try { audio.src = convertFileSrc(path) + "?t=" + Date.now(); } catch (e) { appendLog(`[UI] convertFileSrc: ${e}`); return; }
  audio.load();
  if (ui.playerFilename) { ui.playerFilename.textContent = basename(path); ui.playerFilename.title = path; }
  if (ui.playerPlayBtn) ui.playerPlayBtn.textContent = "▶";
  if (ui.playerSeek) { ui.playerSeek.value = "0"; ui.playerSeek.style.setProperty("--progress", "0%"); }
  if (ui.playerTimeCurrent) ui.playerTimeCurrent.textContent = "0:00";
  if (ui.playerTimeTotal) ui.playerTimeTotal.textContent = "0:00";
  updatePlayerEnabled();
}

function togglePlayer() {
  const audio = ui.playerAudio;
  if (!audio || !state.playerPath) return;
  if (audio.paused) { audio.play().catch(() => {}); if (ui.playerPlayBtn) ui.playerPlayBtn.textContent = "⏸"; }
  else { audio.pause(); if (ui.playerPlayBtn) ui.playerPlayBtn.textContent = "▶"; }
}

function updatePlayerSeek() {
  if (isSeeking) return;
  const audio = ui.playerAudio;
  if (!audio || !audio.duration) return;
  if (ui.playerSeek) { ui.playerSeek.max = String(audio.duration); ui.playerSeek.value = String(audio.currentTime); ui.playerSeek.style.setProperty("--progress", `${(audio.currentTime / audio.duration) * 100}%`); }
  if (ui.playerTimeCurrent) ui.playerTimeCurrent.textContent = formatTime(audio.currentTime);
}

function updatePlayerEnabled() {
  const enabled = !!state.playerPath;
  if (ui.playerFooter) ui.playerFooter.classList.toggle("player-disabled", !enabled);
  if (ui.playerPlayBtn) ui.playerPlayBtn.disabled = !enabled;
  if (ui.playerSeek) ui.playerSeek.disabled = !enabled;
}

function setupPlayerEvents() {
  const audio = ui.playerAudio;
  if (!audio) return;
  audio.addEventListener("timeupdate", updatePlayerSeek);
  audio.addEventListener("loadedmetadata", () => { if (ui.playerTimeTotal) ui.playerTimeTotal.textContent = formatTime(audio.duration); if (ui.playerSeek) ui.playerSeek.max = String(audio.duration); });
  audio.addEventListener("ended", () => { if (ui.playerPlayBtn) ui.playerPlayBtn.textContent = "▶"; });
  audio.addEventListener("error", () => { if (ui.playerFilename) ui.playerFilename.textContent = "Ошибка воспроизведения"; });
  if (ui.playerSeek) {
    ui.playerSeek.addEventListener("mousedown", () => { isSeeking = true; });
    ui.playerSeek.addEventListener("touchstart", () => { isSeeking = true; });
    ui.playerSeek.addEventListener("mouseup", () => { isSeeking = false; });
    ui.playerSeek.addEventListener("touchend", () => { isSeeking = false; });
    ui.playerSeek.addEventListener("input", () => {
      if (audio) { audio.currentTime = parseFloat(ui.playerSeek!.value); const pct = audio.duration ? (audio.currentTime / audio.duration) * 100 : 0; ui.playerSeek!.style.setProperty("--progress", `${pct}%`); }
      if (ui.playerTimeCurrent) ui.playerTimeCurrent.textContent = formatTime(audio.currentTime);
    });
  }
  if (ui.playerPlayBtn) ui.playerPlayBtn.addEventListener("click", togglePlayer);
  if (ui.playerBtnFile) ui.playerBtnFile.addEventListener("click", () => { if (state.playerPath) invoke("open_file_default", { path: state.playerPath }); });
  if (ui.playerBtnFolder) ui.playerBtnFolder.addEventListener("click", () => { invoke("open_output_dir").catch(() => {}); });
}

// ═══════════════════════════════════════════════════════════════
// UI Updates
// ═══════════════════════════════════════════════════════════════

function setBackendBadge(ok: boolean) {
  if (!ui.backendDot || !ui.backendText) return;
  ui.backendDot.className = `dot ${ok ? "ok" : "warn"}`;
  ui.backendText.textContent = ok ? "Backend: OK" : "Backend: запуск...";
}

function appendLog(line: string) {
  if (!ui.logBox) return;
  ui.logBox.appendChild(document.createTextNode(line + "\n"));
  if (state.logFollow) ui.logBox.scrollTop = ui.logBox.scrollHeight;
}

function showBanner(kind: "warn" | "error", title: string, message: string) {
  if (!ui.banner) return;
  ui.banner.style.display = "";
  ui.banner.classList.toggle("error", kind === "error");
  if (ui.bannerTitle) ui.bannerTitle.textContent = title;
  if (ui.bannerMsg) { ui.bannerMsg.textContent = truncate(message); ui.bannerMsg.title = message; }
}

function hideBanner() { if (ui.banner) ui.banner.style.display = "none"; }

function resetProgressSoon() {
  if (state.clearTimer) window.clearTimeout(state.clearTimer);
  state.clearTimer = window.setTimeout(() => { if (state.job && (state.job.status === "done" || state.job.status === "error")) setJob(null); }, 10000);
}

function beginNewAction() {
  if (state.clearTimer) window.clearTimeout(state.clearTimer);
  hideBanner(); stopPlayer();
  setJob({ job_id: "-", status: "running", progress: 0, message: "Запуск...", result: null, error: null });
}

function setTab(tab: TabKey) {
  state.tab = tab;
  ui.navRvc?.classList.toggle("active", tab === "rvc");
  ui.navTts?.classList.toggle("active", tab === "tts");
  ui.navModels?.classList.toggle("active", tab === "models");
  if (ui.titleText) { ui.titleText.textContent = tab === "rvc" ? "RVC • Конвертация аудио" : tab === "tts" ? "TTS → RVC • Синтез и конвертация" : "Модели • Установка / Удаление"; }
  renderLeft();
}

function setJob(job: JobSnapshot | null) {
  state.job = job;
  if (ui.kvJobId) ui.kvJobId.textContent = state.jobId ?? "-";
  if (ui.kvStatus) ui.kvStatus.textContent = job?.status ?? "idle";
  const outPath = job?.result?.output_path;
  if (ui.kvOutput) { ui.kvOutput.textContent = typeof outPath === "string" ? basename(outPath) : "-"; ui.kvOutput.title = typeof outPath === "string" ? outPath : ""; }
  const isError = job?.status === "error";
  const progress = isError ? 0 : (job?.progress ?? 0);
  const msg = isError ? "Ошибка" : (job?.message ?? "");
  if (ui.progressText) ui.progressText.textContent = job ? `${fmtPct(progress)} • ${msg}` : "Ожидание...";
  if (ui.progressFill) ui.progressFill.style.width = `${Math.round(progress * 100)}%`;
  if (isError && job?.error?.trim()) {
    showBanner("error", "Ошибка", job.error);
    if (ui.bannerBtn1) { ui.bannerBtn1.textContent = "Копировать"; ui.bannerBtn1.onclick = async () => { const ok = await tryCopy(job.error!); appendLog(ok ? "[UI] Скопировано." : "[UI] Не удалось."); }; }
    if (ui.bannerBtn2 && ui.logDetails) { ui.bannerBtn2.textContent = "Логи"; ui.bannerBtn2.onclick = () => { ui.logDetails!.open = true; }; }
    resetProgressSoon();
  }
  if (job?.status === "done") { if (typeof outPath === "string") loadPlayerAudio(outPath); resetProgressSoon(); }
}

// ═══════════════════════════════════════════════════════════════
// Backend API
// ═══════════════════════════════════════════════════════════════

async function loadModels() {
  if (!state.backendUrl) return;
  const r = await fetch(`${state.backendUrl}/models/rvc`);
  const data = await r.json();
  state.models = Array.isArray(data.models) ? data.models : [];
  if (state.models.length) { if (!state.rvc.rvc_model) state.rvc.rvc_model = state.models[0]; if (!state.tts.rvc_model) state.tts.rvc_model = state.models[0]; }
}

async function loadEdgeVoices() {
  if (!state.backendUrl) return;
  const r = await fetch(`${state.backendUrl}/voices/edge`);
  const data = await r.json();
  state.edgeVoices = data.voices ?? {};
  const langs = Object.keys(state.edgeVoices);
  if (!state.tts.language && langs.length) state.tts.language = langs[0];
  const voices = state.edgeVoices[state.tts.language] ?? [];
  if (!state.tts.tts_voice && voices.length) state.tts.tts_voice = voices[0];
}

async function refreshAll() {
  if (!state.backendUrl) return;
  await loadModels(); await loadEdgeVoices(); renderLeft();
  appendLog("[UI] Данные обновлены.");
}

async function connectBackendOrShowBanner() {
  showBanner("warn", "Подключение к backend…", "Ожидаем локальный backend...");
  if (ui.bannerBtn1) { ui.bannerBtn1.textContent = "Restart"; ui.bannerBtn1.onclick = async () => { try { await invoke("backend_restart"); appendLog("[UI] backend_restart."); await sleep(400); await connectBackendOrShowBanner(); } catch (e) { appendLog(`[UI] restart: ${e}`); } }; }
  if (ui.bannerBtn2) { ui.bannerBtn2.textContent = "Retry"; ui.bannerBtn2.onclick = () => connectBackendOrShowBanner(); }

  for (let i = 0; i < 220; i++) {
    const url = await invoke<string | null>("backend_get_url");
    if (typeof url === "string" && url.startsWith("http")) {
      state.backendUrl = url; state.backendReady = true; setBackendBadge(true);
      appendLog(`[UI] Backend: ${url}`);
      try { const hr = await fetch(`${url}/health`); if (!hr.ok) { showBanner("warn", "Backend не отвечает", `status ${hr.status}`); return; } }
      catch (e) { showBanner("warn", "Backend недоступен", String(e)); return; }
      hideBanner(); await loadModels(); await loadEdgeVoices(); renderLeft(); return;
    }
    await sleep(150);
  }
  state.backendReady = false; setBackendBadge(false);
  showBanner("warn", "Backend не найден", "Нажмите Restart.");
}

// ═══════════════════════════════════════════════════════════════
// SSE & Job Tracking
// ═══════════════════════════════════════════════════════════════

function stopSSE() { if (ui.es) { try { ui.es.close(); } catch {} ui.es = null; } }

function attachSSE(jobId: string) {
  stopSSE(); if (!state.backendUrl) return;
  const es = new EventSource(`${state.backendUrl}/jobs/${jobId}/events`);
  ui.es = es;
  es.onmessage = (ev) => {
    try {
      const msg = JSON.parse(ev.data);
      if (!state.job) state.job = { job_id: jobId, status: "running", progress: 0, message: "" };
      if (msg.type === "progress") { state.job.progress = Number(msg.progress ?? state.job.progress); state.job.message = String(msg.message ?? state.job.message); setJob(state.job); }
      if (msg.type === "status") { state.job.status = msg.status; state.job.message = String(msg.message ?? state.job.message); if (msg.result) state.job.result = msg.result; setJob(state.job); if (state.job.status === "done" || state.job.status === "error") stopSSE(); }
      if (msg.type === "error") { state.job.error = String(msg.error ?? ""); state.job.status = "error"; setJob(state.job); appendLog(`[ERROR] ${msg.error ?? ""}`); }
      if (msg.type === "log") appendLog(String(msg.line ?? ""));
    } catch (e) { appendLog(`[UI] SSE: ${e}`); }
  };
  es.onerror = () => { stopSSE(); appendLog("[UI] SSE closed."); };
}

async function pollJobUntilDone(jobId: string) {
  if (!state.backendUrl) return;
  for (let i = 0; i < 3600; i++) {
    const r = await fetch(`${state.backendUrl}/jobs/${jobId}`);
    const data = (await r.json()) as JobSnapshot;
    state.job = data; setJob(data);
    if (data.status === "done" || data.status === "error") { stopSSE(); return; }
    await sleep(ui.es ? 2000 : 400);
  }
}

async function runJob(jobId: string) {
  state.jobId = jobId;
  setJob({ job_id: jobId, status: "queued", progress: 0, message: "Ожидание..." });
  attachSSE(jobId); await pollJobUntilDone(jobId);
}

async function postJob(endpoint: string, body: Record<string, any>): Promise<boolean> {
  if (!state.backendUrl) return false;
  beginNewAction();
  const r = await fetch(`${state.backendUrl}${endpoint}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!r.ok) { const txt = await r.text().catch(() => ""); setJob({ job_id: "-", status: "error", progress: 0, message: "Ошибка", error: txt }); return false; }
  const data = await r.json(); await runJob(data.job_id); return true;
}

// ═══════════════════════════════════════════════════════════════
// Actions
// ═══════════════════════════════════════════════════════════════

async function startRvc() {
  if (!state.rvc.input_path.trim()) { appendLog("[UI] input_path пустой."); return; }
  if (!state.rvc.rvc_model.trim()) { appendLog("[UI] rvc_model пустой."); return; }
  await postJob("/jobs/convert", state.rvc);
}
async function startTts() {
  if (!state.tts.tts_text.trim()) { appendLog("[UI] tts_text пустой."); return; }
  if (!state.tts.tts_voice.trim()) { appendLog("[UI] tts_voice пустой."); return; }
  if (!state.tts.rvc_model.trim()) { appendLog("[UI] rvc_model пустой."); return; }
  await postJob("/jobs/tts_convert", state.tts);
}
async function installModelUrl() {
  if (!state.installUrl.url.trim() || !state.installUrl.model_name.trim()) return;
  const ok = await postJob("/jobs/models/install_url", state.installUrl);
  if (ok) { await loadModels(); renderLeft(); }
}
async function installModelZip() {
  if (!state.installZip.zip_path.trim() || !state.installZip.model_name.trim()) return;
  const ok = await postJob("/jobs/models/install_local_zip", { path: state.installZip.zip_path, model_name: state.installZip.model_name });
  if (ok) { await loadModels(); renderLeft(); }
}
async function installModelFiles() {
  if (!state.installFiles.pth_path.trim() || !state.installFiles.model_name.trim()) return;
  const ok = await postJob("/jobs/models/install_local_files", { path: state.installFiles.pth_path, extra_path: state.installFiles.index_path || null, model_name: state.installFiles.model_name });
  if (ok) { await loadModels(); renderLeft(); }
}
async function deleteModel(name: string) {
  if (!state.backendUrl) return;
  const r = await fetch(`${state.backendUrl}/models/rvc/${encodeURIComponent(name)}`, { method: "DELETE" });
  if (!r.ok) { appendLog(`[UI] delete: ${r.status}`); return; }
  appendLog(`[UI] deleted: ${name}`); await loadModels(); renderLeft();
}
async function openModelFolder(name: string) { try { await invoke("open_rvc_model_dir", { modelName: name }); } catch (e) { appendLog(`[UI] ${e}`); } }

// ═══════════════════════════════════════════════════════════════
// Shared Builders
// ═══════════════════════════════════════════════════════════════

function buildModelSelect(parent: HTMLElement, obj: Record<string, any>, key: string): HTMLSelectElement {
  const wrap = h("div", "field"); wrap.appendChild(h("label", "", "RVC модель"));
  const row = h("div", "model-select-row");
  const sel = makeSelect(state.models, obj[key] || state.models[0]);
  sel.onchange = () => { obj[key] = sel.value; };
  const refreshBtn = h("button", "refresh-btn", "⟳") as HTMLButtonElement;
  refreshBtn.title = "Обновить список моделей";
  refreshBtn.onclick = async () => { await loadModels(); sel.innerHTML = ""; for (const m of state.models) { const o = document.createElement("option"); o.value = m; o.textContent = m; sel.appendChild(o); } if (state.models.length) { if (!state.models.includes(obj[key])) obj[key] = state.models[0]; sel.value = obj[key]; } };
  row.appendChild(sel); row.appendChild(refreshBtn); wrap.appendChild(row); parent.appendChild(wrap);
  return sel;
}

function buildPitchBlock(parent: HTMLElement, s: Record<string, any>) {
  const apChk = addCheckbox(parent, "Авто определение тона", s, "autopitch");
  const thresholdWrap = h("div", "");
  addSelect(thresholdWrap, "Порог", s, "autopitch_threshold", ["155", "255"]);
  const thresholdSel = thresholdWrap.querySelector("select")!; thresholdSel.value = String(s.autopitch_threshold);
  thresholdSel.onchange = () => { s.autopitch_threshold = parseFloat(thresholdSel.value); };
  thresholdWrap.style.display = s.autopitch ? "" : "none";
  const pitchWrap = h("div", ""); addSlider(pitchWrap, "Высота тона (-24 … +24)", s, "rvc_pitch", -24, 24, 1);
  pitchWrap.style.display = s.autopitch ? "none" : "";
  apChk.addEventListener("change", () => { thresholdWrap.style.display = s.autopitch ? "" : "none"; pitchWrap.style.display = s.autopitch ? "none" : ""; });
  parent.appendChild(thresholdWrap); parent.appendChild(pitchWrap);
}

function buildConversionSettings(parent: HTMLElement, s: Record<string, any>) {
  const { details, content } = makeAccordion("Настройки преобразования");
  const a1 = makeAccordion("Стандартные настройки");
  addSelect(a1.content, "Метод F0", s, "f0_method", F0_METHODS);
  addSlider(a1.content, "Влияние индекса", s, "index_rate", 0, 1, 0.01);
  addSlider(a1.content, "Смешивание RMS", s, "volume_envelope", 0, 1, 0.01);
  addSlider(a1.content, "Защита согласных", s, "protect", 0, 0.5, 0.01);
  content.appendChild(a1.details);
  const a2 = makeAccordion("Дополнительные настройки");
  addCheckbox(a2.content, "Стерео", s, "stereo_sound");
  addCheckbox(a2.content, "Аудио-апскейл (FlashSR)", s, "audio_upscaling");
  const atChk = addCheckbox(a2.content, "Автотюн", s, "autotune");
  const atFields = h("div", "autotune-fields");
  addSelect(atFields, "Тоника", s, "autotune_tonic", TONIC_NOTES);
  addSelect(atFields, "Гамма", s, "autotune_scale", SCALES);
  addSlider(atFields, "Сила автотюна", s, "autotune_strength", 0, 1, 0.1);
  atFields.style.display = s.autotune ? "" : "none";
  atChk.addEventListener("change", () => { atFields.style.display = s.autotune ? "" : "none"; });
  a2.content.appendChild(atFields); a2.content.appendChild(h("div", "hr"));
  addSlider(a2.content, "F0 мин", s, "f0_min", 1, 120, 1);
  addSlider(a2.content, "F0 макс", s, "f0_max", 380, 16000, 1);
  content.appendChild(a2.details); parent.appendChild(details);
}

// ═══════════════════════════════════════════════════════════════
// Tab Renderers
// ═══════════════════════════════════════════════════════════════

function renderRvcTab(card: HTMLElement) {
  card.appendChild(h("h2", "", "RVC • Конвертация"));
  const inp = makeInput("Путь к аудио…"); inp.value = state.rvc.input_path; inp.oninput = () => { state.rvc.input_path = inp.value; };
  const pick = btn("Выбрать"); pick.onclick = async () => { const sel = await openDialog({ multiple: false, filters: [{ name: "Audio", extensions: ["mp3", "wav", "flac", "ogg", "m4a"] }] }); if (typeof sel === "string") { state.rvc.input_path = sel; inp.value = sel; } };
  card.appendChild(fieldWrap("Входной файл", makeRow(inp, pick)));
  buildModelSelect(card, state.rvc, "rvc_model"); buildPitchBlock(card, state.rvc);
  addSelect(card, "Формат выхода", state.rvc, "output_format", OUTPUT_FORMATS);
  buildConversionSettings(card, state.rvc);
  const run = btn("Генерировать", "btn primary"); run.onclick = () => startRvc(); card.appendChild(run);
}

function renderTtsTab(card: HTMLElement) {
  card.appendChild(h("h2", "", "TTS → RVC"));
  buildModelSelect(card, state.tts, "rvc_model");
  const langs = Object.keys(state.edgeVoices); const langSel = makeSelect(langs, state.tts.language);
  const voiceSel = makeSelect(state.edgeVoices[state.tts.language] ?? [], state.tts.tts_voice);
  langSel.onchange = () => { state.tts.language = langSel.value; const voices = state.edgeVoices[langSel.value] || []; voiceSel.innerHTML = ""; for (const v of voices) { const o = document.createElement("option"); o.value = v; o.textContent = v; voiceSel.appendChild(o); } state.tts.tts_voice = voices[0] || ""; voiceSel.value = state.tts.tts_voice; };
  voiceSel.onchange = () => { state.tts.tts_voice = voiceSel.value; };
  card.appendChild(fieldWrap("Язык", langSel)); card.appendChild(fieldWrap("Голос TTS", voiceSel));
  const ta = document.createElement("textarea"); ta.placeholder = "Введите текст…"; ta.rows = 5; ta.value = state.tts.tts_text; ta.oninput = () => { state.tts.tts_text = ta.value; };
  card.appendChild(fieldWrap("Текст", ta));
  const ttsAcc = makeAccordion("Настройки TTS");
  addSlider(ttsAcc.content, "Скорость речи", state.tts, "tts_rate", -100, 100, 1);
  addSlider(ttsAcc.content, "Громкость", state.tts, "tts_volume", -100, 100, 1);
  addSlider(ttsAcc.content, "Высота TTS", state.tts, "tts_pitch", -100, 100, 1);
  card.appendChild(ttsAcc.details); buildPitchBlock(card, state.tts);
  addSelect(card, "Формат выхода", state.tts, "output_format", OUTPUT_FORMATS);
  buildConversionSettings(card, state.tts);
  const run = btn("Генерировать", "btn primary"); run.onclick = () => startTts(); card.appendChild(run);
}

function renderModelsTab(card: HTMLElement) {
  card.appendChild(h("h2", "", "RVC модели"));
  const chips = h("div", "chips");
  for (const m of state.models) {
    const chip = h("div", "chip"); const name = h("div", "chipName", m); name.title = m; const actions = h("div", "chipActions");
    const bFolder = h("button", "iconBtn", "📁") as HTMLButtonElement; bFolder.title = "Папка"; bFolder.onclick = () => openModelFolder(m);
    const bDel = h("button", "iconBtn danger", "🗑") as HTMLButtonElement; bDel.title = "Удалить"; bDel.onclick = () => deleteModel(m);
    actions.appendChild(bFolder); actions.appendChild(bDel); chip.appendChild(name); chip.appendChild(actions); chips.appendChild(chip);
  }
  card.appendChild(chips);
  if (!state.models.length) card.appendChild(h("div", "text-muted", "Нет установленных моделей."));
  card.appendChild(h("div", "hr"));
  const d1 = makeAccordion("Установка по ссылке (ZIP)"); addInput(d1.content, "URL", state.installUrl, "url", "https://..."); addInput(d1.content, "Имя модели", state.installUrl, "model_name", "MyModel"); const b1 = btn("Установить", "btn primary"); b1.onclick = () => installModelUrl(); d1.content.appendChild(b1); card.appendChild(d1.details); card.appendChild(h("div", "hr"));
  const d2 = makeAccordion("Распаковка ZIP"); const zipInp = makeInput("Путь к ZIP…"); zipInp.value = state.installZip.zip_path; zipInp.oninput = () => { state.installZip.zip_path = zipInp.value; }; const pickZip = btn("Выбрать"); pickZip.onclick = async () => { const sel = await openDialog({ multiple: false, filters: [{ name: "ZIP", extensions: ["zip"] }] }); if (typeof sel === "string") { state.installZip.zip_path = sel; zipInp.value = sel; } }; d2.content.appendChild(fieldWrap("ZIP файл", makeRow(zipInp, pickZip))); addInput(d2.content, "Имя модели", state.installZip, "model_name", "MyModel"); const b2 = btn("Распаковать", "btn primary"); b2.onclick = () => installModelZip(); d2.content.appendChild(b2); card.appendChild(d2.details); card.appendChild(h("div", "hr"));
  const d3 = makeAccordion("Загрузка .pth / .index"); const pthInp = makeInput(".pth путь…"); pthInp.value = state.installFiles.pth_path; pthInp.oninput = () => { state.installFiles.pth_path = pthInp.value; }; const pickPth = btn("Выбрать"); pickPth.onclick = async () => { const sel = await openDialog({ multiple: false, filters: [{ name: "PTH", extensions: ["pth"] }] }); if (typeof sel === "string") { state.installFiles.pth_path = sel; pthInp.value = sel; } }; d3.content.appendChild(fieldWrap(".pth файл", makeRow(pthInp, pickPth)));
  const idxInp = makeInput(".index путь (необяз.)…"); idxInp.value = state.installFiles.index_path; idxInp.oninput = () => { state.installFiles.index_path = idxInp.value; }; const pickIdx = btn("Выбрать"); pickIdx.onclick = async () => { const sel = await openDialog({ multiple: false, filters: [{ name: "INDEX", extensions: ["index"] }] }); if (typeof sel === "string") { state.installFiles.index_path = sel; idxInp.value = sel; } }; d3.content.appendChild(fieldWrap(".index файл", makeRow(idxInp, pickIdx)));
  addInput(d3.content, "Имя модели", state.installFiles, "model_name", "MyModel"); const b3 = btn("Загрузить", "btn primary"); b3.onclick = () => installModelFiles(); d3.content.appendChild(b3); card.appendChild(d3.details);
}

function renderLeft() {
  if (!ui.left) return; ui.left.innerHTML = "";
  const card = h("div", "card"); ui.left.appendChild(card);
  if (!state.backendReady) { card.appendChild(h("div", "", "Backend не готов.")); return; }
  if (state.tab === "rvc") renderRvcTab(card);
  else if (state.tab === "tts") renderTtsTab(card);
  else renderModelsTab(card);
}

// ═══════════════════════════════════════════════════════════════
// Mount
// ═══════════════════════════════════════════════════════════════

function mount() {
  const root = document.querySelector("#app") as HTMLElement; root.innerHTML = "";
  const app = h("div", "app"); root.appendChild(app);
  const sidebar = h("div", "sidebar"); app.appendChild(sidebar);
  const brand = h("div", "brand"); brand.appendChild(h("div", "logo")); const title = h("div", "title"); title.appendChild(h("b", "", "PolGen Desktop")); brand.appendChild(title); sidebar.appendChild(brand);
  const nav = h("div", "nav"); sidebar.appendChild(nav);
  ui.navRvc = btn("RVC", "btn"); ui.navTts = btn("TTS → RVC", "btn"); ui.navModels = btn("Модели", "btn");
  ui.navRvc.onclick = () => setTab("rvc"); ui.navTts.onclick = () => setTab("tts"); ui.navModels.onclick = () => setTab("models");
  nav.appendChild(ui.navRvc); nav.appendChild(ui.navTts); nav.appendChild(ui.navModels);
  const statusBox = h("div", "status"); const badge = h("div", "badge");
  ui.backendDot = h("div", "dot warn"); ui.backendText = h("span", "", "Backend: запуск...");
  badge.appendChild(ui.backendDot); badge.appendChild(ui.backendText); statusBox.appendChild(badge);
  const sideRefresh = h("button", "sidebar-refresh", "⟳  Обновить данные") as HTMLButtonElement; sideRefresh.onclick = () => refreshAll(); statusBox.appendChild(sideRefresh);
  sidebar.appendChild(statusBox);
  const main = h("div", "main"); app.appendChild(main);
  const titlebar = h("div", "titlebar"); ui.titleText = h("h1", "", "PolGen Desktop"); const spacer = h("div", "spacer");
  const winBtns = h("div", "windowBtns");
  const bMin = h("button", "winBtn", "━"); const bMax = h("button", "winBtn", "🗖"); const bClose = h("button", "winBtn close", "✖");
  bMin.onclick = () => appWindow.minimize(); bMax.onclick = () => appWindow.toggleMaximize(); bClose.onclick = () => appWindow.close();
  winBtns.appendChild(bMin); winBtns.appendChild(bMax); winBtns.appendChild(bClose);
  titlebar.onmousedown = async (ev) => { if (ev.button !== 0 || (ev.target as HTMLElement)?.closest("button, input, select, textarea")) return; try { await appWindow.startDragging(); } catch {} };
  titlebar.appendChild(ui.titleText); titlebar.appendChild(spacer); titlebar.appendChild(winBtns); main.appendChild(titlebar);
  const content = h("div", "content"); main.appendChild(content);
  const left = h("div", ""); const right = h("div", ""); content.appendChild(left); content.appendChild(right); ui.left = left;
  const rc = h("div", "card"); right.appendChild(rc);
  rc.appendChild(h("h2", "", "Задача / Прогресс"));
  ui.banner = h("div", "banner"); ui.banner.style.display = "none";
  const bannerHead = h("div", "bannerHead"); ui.bannerTitle = h("div", "bannerTitle"); const bannerBtns = h("div", "bannerBtns");
  ui.bannerBtn1 = btn("", "btn"); ui.bannerBtn2 = btn("", "btn"); bannerBtns.appendChild(ui.bannerBtn1); bannerBtns.appendChild(ui.bannerBtn2);
  bannerHead.appendChild(ui.bannerTitle); bannerHead.appendChild(bannerBtns); ui.banner.appendChild(bannerHead);
  ui.bannerMsg = h("div", "bannerMsg"); ui.banner.appendChild(ui.bannerMsg); rc.appendChild(ui.banner);
  const kv = h("div", "kv");
  const mkLine = (k: string): HTMLElement => { const line = h("div", ""); line.appendChild(h("span", "", k)); const val = h("b", "", "-"); line.appendChild(val); kv.appendChild(line); return val; };
  ui.kvJobId = mkLine("Job ID"); ui.kvStatus = mkLine("Status"); ui.kvOutput = mkLine("Output");
  rc.appendChild(kv); rc.appendChild(h("div", "hr"));
  ui.progressText = h("div", "small", "Ожидание...");
  const pBar = h("div", "progressBar"); ui.progressFill = h("div", ""); pBar.appendChild(ui.progressFill);
  rc.appendChild(ui.progressText); rc.appendChild(pBar); rc.appendChild(h("div", "hr"));
  ui.logDetails = document.createElement("details"); const logSummary = document.createElement("summary"); logSummary.textContent = "Логи"; ui.logDetails.appendChild(logSummary);
  ui.logBox = h("div", "log");
  ui.logBox.addEventListener("scroll", () => { const near = ui.logBox!.scrollTop + ui.logBox!.clientHeight >= ui.logBox!.scrollHeight - 10; state.logFollow = near; if (ui.followChk) ui.followChk.checked = state.logFollow; });
  ui.logDetails.appendChild(ui.logBox);
  const followRow = h("div", "row"); const fc = makeCheckbox("Авто-прокрутка", state.logFollow); ui.followChk = fc.input;
  fc.input.onchange = () => { state.logFollow = fc.input.checked; if (state.logFollow && ui.logBox) ui.logBox.scrollTop = ui.logBox.scrollHeight; };
  const clearBtn = btn("Очистить"); clearBtn.onclick = () => { if (ui.logBox) ui.logBox.textContent = ""; };
  followRow.appendChild(fc.wrap); followRow.appendChild(clearBtn); ui.logDetails.appendChild(followRow); rc.appendChild(ui.logDetails);

  const playerFooter = h("div", "player-footer player-disabled"); ui.playerFooter = playerFooter;
  ui.playerAudio = document.createElement("audio"); ui.playerAudio.preload = "metadata"; playerFooter.appendChild(ui.playerAudio);
  const playerInner = h("div", "player-inner");
  ui.playerPlayBtn = h("button", "player-play", "▶") as HTMLButtonElement; ui.playerPlayBtn.disabled = true; playerInner.appendChild(ui.playerPlayBtn);
  ui.playerTimeCurrent = h("span", "player-time", "0:00"); playerInner.appendChild(ui.playerTimeCurrent);
  ui.playerSeek = document.createElement("input"); ui.playerSeek.type = "range"; ui.playerSeek.className = "player-seek"; ui.playerSeek.min = "0"; ui.playerSeek.max = "100"; ui.playerSeek.step = "0.1"; ui.playerSeek.value = "0"; ui.playerSeek.disabled = true; ui.playerSeek.style.setProperty("--progress", "0%"); playerInner.appendChild(ui.playerSeek);
  ui.playerTimeTotal = h("span", "player-time", "0:00"); playerInner.appendChild(ui.playerTimeTotal);
  ui.playerFilename = h("span", "player-filename", "Нет аудио"); playerInner.appendChild(ui.playerFilename);
  const playerActions = h("div", "player-actions");
  ui.playerBtnFile = h("button", "player-action", "📄") as HTMLButtonElement; ui.playerBtnFile.title = "Открыть файл";
  ui.playerBtnFolder = h("button", "player-action", "📁") as HTMLButtonElement; ui.playerBtnFolder.title = "Открыть папку";
  playerActions.appendChild(ui.playerBtnFile); playerActions.appendChild(ui.playerBtnFolder); playerInner.appendChild(playerActions);
  playerFooter.appendChild(playerInner); main.appendChild(playerFooter);
  setupPlayerEvents();
  setTab("models"); setJob(null);
}

// ═══════════════════════════════════════════════════════════════
// Bootstrap — ждём видимости окна перед подключением к backend
// ═══════════════════════════════════════════════════════════════

async function waitUntilVisible() {
  for (let i = 0; i < 600; i++) {
    try {
      const visible = await appWindow.isVisible();
      if (visible) return;
    } catch {}
    await sleep(500);
  }
}

async function bootstrap() {
  mount();

  // Если окно скрыто (setup режим) — ждём пока setup покажет нас
  const visible = await appWindow.isVisible();
  if (!visible) {
    appendLog("[UI] Окно скрыто, ожидание установки...");
    await waitUntilVisible();
    appendLog("[UI] Окно видимо, подключение к backend...");
  } else {
    appendLog("[UI] Запуск…");
  }

  await connectBackendOrShowBanner();
  setTab("models");
}

window.addEventListener("DOMContentLoaded", () => {
  bootstrap().catch((e) => {
    appendLog(`[UI] bootstrap error: ${e}`);
    showBanner("error", "UI error", String(e));
  });
});