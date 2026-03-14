import { invoke } from "@tauri-apps/api/tauri";
import { listen, UnlistenFn } from "@tauri-apps/api/event";
import { appWindow, WebviewWindow } from "@tauri-apps/api/window";

// ═══════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════

interface EnvStatus {
  ready: boolean;
  python_found: boolean;
  env_exists: boolean;
  project_root: string | null;
}

interface EnvVariant {
  label: string;
  url: string;
  description: string;
}

interface PlatformInfo {
  os: string;
  has_nvidia: boolean;
  recommended_url: string;
  all_variants: EnvVariant[];
}

interface DownloadProgressEvent {
  downloaded_mb: number;
  total_mb: number;
  percent: number;
  speed_mbps: number;
  eta_seconds: number;
  message: string;
}

type InstallMode = "download" | "conda";

// ═══════════════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════════════

function h<K extends keyof HTMLElementTagNameMap>(tag: K, cls?: string, text?: string): HTMLElementTagNameMap[K] {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}

async function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

// ═══════════════════════════════════════════════════════════════
// State
// ═══════════════════════════════════════════════════════════════

let setupLog: HTMLDivElement | null = null;
let setupBtn: HTMLButtonElement | null = null;
let checksContainer: HTMLDivElement | null = null;
let progressBar: HTMLDivElement | null = null;
let progressFill: HTMLDivElement | null = null;
let progressText: HTMLDivElement | null = null;
let modeContainer: HTMLDivElement | null = null;
let variantSelect: HTMLSelectElement | null = null;

let envStatus: EnvStatus | null = null;
let platform: PlatformInfo | null = null;
let isRunning = false;
let currentMode: InstallMode = "download";
let selectedUrl = "";

// ═══════════════════════════════════════════════════════════════
// Log & UI updates
// ═══════════════════════════════════════════════════════════════

function appendLog(line: string) {
  if (!setupLog) return;
  setupLog.appendChild(document.createTextNode(line + "\n"));
  setupLog.scrollTop = setupLog.scrollHeight;
}

function updateChecks() {
  if (!checksContainer || !envStatus) return;
  checksContainer.innerHTML = "";

  const add = (ok: boolean | null, text: string) => {
    const cls = ok === true ? "ok" : ok === false ? "warn" : "wait";
    const icon = ok === true ? "✓" : ok === false ? "○" : "⏳";
    checksContainer!.appendChild(h("div", `check ${cls}`, `${icon}  ${text}`));
  };

  add(
    !!envStatus.project_root,
    envStatus.project_root ? `Проект: ${envStatus.project_root}` : "Корень проекта не найден"
  );
  add(envStatus.env_exists, envStatus.env_exists ? "Окружение (env/) найдено" : "Окружение (env/) не найдено");
  add(envStatus.python_found, envStatus.python_found ? "Python найден" : "Python не найден");

  if (platform) {
    add(platform.has_nvidia, platform.has_nvidia ? "NVIDIA GPU обнаружена" : "NVIDIA GPU не обнаружена");
  }
}

function setProgress(percent: number, text: string) {
  if (progressFill) progressFill.style.width = `${Math.min(100, Math.max(0, Math.round(percent)))}%`;
  if (progressText) progressText.textContent = text;
  if (progressBar) progressBar.style.display = "";
}

function hideProgress() {
  if (progressBar) progressBar.style.display = "none";
  if (progressText) progressText.textContent = "";
}

function setButtonState(disabled: boolean, text: string) {
  if (setupBtn) {
    setupBtn.disabled = disabled;
    setupBtn.textContent = text;
  }
}

// ═══════════════════════════════════════════════════════════════
// Mode switch
// ═══════════════════════════════════════════════════════════════

function renderModeSwitch() {
  if (!modeContainer) return;
  modeContainer.innerHTML = "";

  const tabs = h("div", "mode-tabs");

  const tabDownload = h("button", `mode-tab ${currentMode === "download" ? "active" : ""}`, "📦 Скачать готовое");
  tabDownload.onclick = () => {
    if (isRunning) return;
    currentMode = "download";
    renderModeSwitch();
  };

  const tabConda = h("button", `mode-tab ${currentMode === "conda" ? "active" : ""}`, "🔧 Conda (скрипт)");
  tabConda.onclick = () => {
    if (isRunning) return;
    currentMode = "conda";
    renderModeSwitch();
  };

  tabs.appendChild(tabDownload);
  tabs.appendChild(tabConda);
  modeContainer.appendChild(tabs);

  if (currentMode === "download") {
    renderDownloadMode();
  } else {
    renderCondaMode();
  }
}

function renderDownloadMode() {
  if (!modeContainer || !platform) return;

  const info = h("div", "mode-info");
  info.appendChild(h("p", "mode-desc", "Скачивает готовое Python-окружение с HuggingFace. Быстро, не требует Conda."));

  const fieldWrap = h("div", "setup-field");
  fieldWrap.appendChild(h("label", "", "Версия:"));

  variantSelect = document.createElement("select");
  variantSelect.className = "setup-select";

  for (const v of platform.all_variants) {
    const opt = document.createElement("option");
    opt.value = v.url;
    opt.textContent = v.label;
    opt.title = v.description;
    variantSelect.appendChild(opt);
  }

  variantSelect.value = selectedUrl || platform.recommended_url;
  selectedUrl = variantSelect.value;
  variantSelect.onchange = () => {
    selectedUrl = variantSelect!.value;
    updateVariantDesc();
  };

  fieldWrap.appendChild(variantSelect);
  info.appendChild(fieldWrap);

  const descEl = h("div", "variant-desc");
  descEl.id = "variant-desc";
  info.appendChild(descEl);

  modeContainer.appendChild(info);
  updateVariantDesc();
}

function updateVariantDesc() {
  if (!platform) return;
  const descEl = document.getElementById("variant-desc");
  if (!descEl) return;

  const variant = platform.all_variants.find((v) => v.url === selectedUrl);
  if (variant) {
    let text = variant.description;
    if (platform.has_nvidia && variant.url.includes("CUDA")) {
      text += " ⭐ Рекомендуется.";
    } else if (!platform.has_nvidia && (variant.url.includes("CPU") || variant.url.includes("MacOS"))) {
      text += " ⭐ Рекомендуется.";
    }
    descEl.textContent = text;
  }
}

function renderCondaMode() {
  if (!modeContainer) return;
  const info = h("div", "mode-info");
  info.appendChild(h("p", "mode-desc", "Запускает скрипт run-PolGen-installer. Требует доступ к Conda/pip."));
  info.appendChild(h("p", "mode-warn", "⚠ Conda может быть недоступна в некоторых регионах (напр. РФ)."));
  modeContainer.appendChild(info);
}

// ═══════════════════════════════════════════════════════════════
// Install actions
// ═══════════════════════════════════════════════════════════════

async function startInstall() {
  if (isRunning) return;
  if (currentMode === "download") {
    await startDownloadInstall();
  } else {
    await startCondaInstall();
  }
}

async function startDownloadInstall() {
  if (!selectedUrl) {
    appendLog("URL не выбран.");
    return;
  }

  isRunning = true;
  setButtonState(true, "⏳ Скачивание...");
  if (setupLog) setupLog.textContent = "";
  setProgress(0, "Подготовка...");

  const listeners: UnlistenFn[] = [];

  listeners.push(
    await listen<{ line: string }>("setup-log", (ev) => {
      appendLog(ev.payload.line);
    })
  );

  listeners.push(
    await listen<DownloadProgressEvent>("download-progress", (ev) => {
      setProgress(ev.payload.percent, ev.payload.message);
    })
  );

  listeners.push(
    await listen<{ success: boolean; message: string }>("download-done", async (ev) => {
      for (const un of listeners) un();

      appendLog(`\n${ev.payload.message}\n`);

      if (ev.payload.success) {
        setProgress(100, "Запуск backend...");
        await waitForBackendAndLaunch();
      } else {
        hideProgress();
        isRunning = false;
        setButtonState(false, "Повторить");
      }
    })
  );

  try {
    await invoke("download_env", { url: selectedUrl });
  } catch (e) {
    for (const un of listeners) un();
    appendLog(`Ошибка: ${e}\n`);
    hideProgress();
    isRunning = false;
    setButtonState(false, "Повторить");
  }
}

async function startCondaInstall() {
  isRunning = true;
  setButtonState(true, "⏳ Установка...");
  if (setupLog) setupLog.textContent = "";
  hideProgress();
  appendLog("Запуск установщика...\n");

  const listeners: UnlistenFn[] = [];

  listeners.push(
    await listen<{ line: string }>("setup-log", (ev) => {
      appendLog(ev.payload.line);
    })
  );

  listeners.push(
    await listen<{ success: boolean; message: string }>("setup-done", async (ev) => {
      for (const un of listeners) un();

      appendLog(`\n${ev.payload.message}\n`);

      if (ev.payload.success) {
        setProgress(100, "Запуск backend...");
        await waitForBackendAndLaunch();
      } else {
        isRunning = false;
        setButtonState(false, "Повторить");
      }
    })
  );

  try {
    await invoke("run_setup");
  } catch (e) {
    for (const un of listeners) un();
    appendLog(`Ошибка: ${e}\n`);
    isRunning = false;
    setButtonState(false, "Повторить");
  }
}

// ═══════════════════════════════════════════════════════════════
// Post-install: verify env → start backend → show main
// ═══════════════════════════════════════════════════════════════

async function waitForBackendAndLaunch() {
  appendLog("Проверка окружения...");
  envStatus = await invoke<EnvStatus>("check_env_ready");
  updateChecks();

  if (!envStatus.ready) {
    appendLog("⚠ Окружение не готово после установки.");
    hideProgress();
    isRunning = false;
    setButtonState(false, "Повторить");
    return;
  }

  appendLog("Запуск backend...");
  setProgress(100, "Запуск backend...");
  setButtonState(true, "✓ Запуск приложения...");

  try {
    await invoke("backend_restart");
  } catch (e) {
    appendLog(`backend_restart: ${e}`);
  }

  appendLog("Ожидание backend...");
  let backendOk = false;

  for (let attempt = 0; attempt < 60; attempt++) {
    try {
      const url = await invoke<string | null>("backend_get_url");
      if (typeof url === "string" && url.startsWith("http")) {
        const resp = await fetch(`${url}/health`);
        if (resp.ok) {
          appendLog(`Backend запущен: ${url}`);
          backendOk = true;
          break;
        }
      }
    } catch {
      // ещё не готов
    }
    await sleep(500);
  }

  if (!backendOk) {
    appendLog("⚠ Backend не ответил за 30 сек. Попробуйте перезапустить.");
    hideProgress();
    isRunning = false;
    setButtonState(false, "Повторить");
    return;
  }

  setProgress(100, "Готово!");
  appendLog("✓ Открытие приложения...");

  await sleep(300);

  try {
    const mainWin = WebviewWindow.getByLabel("main");
    if (mainWin) {
      await mainWin.show();
      await mainWin.setFocus();
    }
  } catch (e) {
    appendLog(`show main: ${e}`);
  }

  await sleep(500);
  await appWindow.close();
}

// ═══════════════════════════════════════════════════════════════
// Close
// ═══════════════════════════════════════════════════════════════

async function closeApp() {
  try {
    await invoke("exit_app");
  } catch {
    await appWindow.close();
  }
}

// ═══════════════════════════════════════════════════════════════
// Mount
// ═══════════════════════════════════════════════════════════════

async function mount() {
  const root = document.getElementById("setup-root")!;
  root.innerHTML = "";

  // Titlebar
  const titlebar = h("div", "setup-titlebar");
  titlebar.appendChild(h("span", "", "PolGen — Установка"));
  const closeBtn = h("button", "setup-close", "✖");
  closeBtn.onclick = () => closeApp();
  titlebar.appendChild(closeBtn);
  titlebar.onmousedown = async (ev) => {
    if (ev.button !== 0 || (ev.target as HTMLElement).closest("button")) return;
    try {
      await appWindow.startDragging();
    } catch {}
  };
  root.appendChild(titlebar);

  // Card
  const card = h("div", "setup-card");

  // Header
  const header = h("div", "setup-header");
  header.appendChild(h("div", "setup-logo"));
  const headerText = h("div", "setup-header-text");
  headerText.appendChild(h("h1", "", "PolGen Desktop"));
  headerText.appendChild(h("p", "", "Установка окружения"));
  header.appendChild(headerText);
  card.appendChild(header);
  card.appendChild(h("div", "hr"));

  // Checks
  checksContainer = h("div", "checks");
  card.appendChild(checksContainer);
  card.appendChild(h("div", "hr"));

  // Mode switch
  modeContainer = h("div", "mode-container");
  card.appendChild(modeContainer);
  card.appendChild(h("div", "hr"));

  // Progress
  progressBar = h("div", "dl-progress-bar");
  progressBar.style.display = "none";
  progressFill = h("div", "dl-progress-fill");
  progressBar.appendChild(progressFill);
  card.appendChild(progressBar);

  progressText = h("div", "dl-progress-text");
  card.appendChild(progressText);

  // Button
  setupBtn = h("button", "setup-btn", "Установить") as HTMLButtonElement;
  setupBtn.onclick = () => startInstall();
  card.appendChild(setupBtn);

  // Log
  setupLog = h("div", "setup-log");
  card.appendChild(setupLog);

  root.appendChild(card);

  // Load data
  try {
    envStatus = await invoke<EnvStatus>("check_env_ready");
  } catch {
    envStatus = { ready: false, python_found: false, env_exists: false, project_root: null };
  }

  try {
    platform = await invoke<PlatformInfo>("detect_platform");
  } catch {
    platform = null;
  }

  if (platform && platform.recommended_url) {
    selectedUrl = platform.recommended_url;
  }

  updateChecks();
  renderModeSwitch();

  // Если уже готово
  if (envStatus.ready) {
    appendLog("Окружение уже установлено.");
    setButtonState(true, "✓ Запуск...");
    await waitForBackendAndLaunch();
  }
}

window.addEventListener("DOMContentLoaded", () => {
  mount();
});