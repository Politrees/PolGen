import { invoke } from "@tauri-apps/api/tauri";
import { get } from "svelte/store";
import { sleep } from "./utils";
import type { JobSnapshot } from "./types";
import {
  backendUrl,
  backendReady,
  models,
  edgeVoices,
  currentJob,
  currentJobId,
  jobRunning,
  playerPath,
  logs,
  toasts,
  rvcForm,
  ttsForm,
} from "./state";

let eventSource: EventSource | null = null;

function stopSSE() {
  if (eventSource) {
    try { eventSource.close(); } catch {}
    eventSource = null;
  }
}

// ═══════════════════════════════════════════════════════════════
// Data loading
// ═══════════════════════════════════════════════════════════════

export async function loadModels(): Promise<void> {
  const url = get(backendUrl);
  if (!url) return;
  try {
    const r = await fetch(`${url}/models/rvc`);
    const data = await r.json();
    const list: string[] = Array.isArray(data.models) ? data.models : [];
    models.set(list);
    if (list.length) {
      rvcForm.update((f) => {
        if (!f.rvc_model || !list.includes(f.rvc_model)) f.rvc_model = list[0];
        return f;
      });
      ttsForm.update((f) => {
        if (!f.rvc_model || !list.includes(f.rvc_model)) f.rvc_model = list[0];
        return f;
      });
    }
  } catch (e) {
    logs.append(`[API] loadModels: ${e}`);
  }
}

export async function loadEdgeVoices(): Promise<void> {
  const url = get(backendUrl);
  if (!url) return;
  try {
    const r = await fetch(`${url}/voices/edge`);
    const data = await r.json();
    const voices: Record<string, string[]> = data.voices ?? {};
    edgeVoices.set(voices);
    const langs = Object.keys(voices);
    ttsForm.update((f) => {
      if (!f.language && langs.length) f.language = langs[0];
      const voiceList = voices[f.language] ?? [];
      if (!f.tts_voice && voiceList.length) f.tts_voice = voiceList[0];
      return f;
    });
  } catch (e) {
    logs.append(`[API] loadEdgeVoices: ${e}`);
  }
}

// ═══════════════════════════════════════════════════════════════
// Health check
// ═══════════════════════════════════════════════════════════════

async function checkHealth(url: string): Promise<boolean> {
  try {
    const r = await fetch(`${url}/health`, { signal: AbortSignal.timeout(3000) });
    return r.ok;
  } catch {
    return false;
  }
}

// ═══════════════════════════════════════════════════════════════
// Backend connection
// ═══════════════════════════════════════════════════════════════

/**
 * Главная функция — вызывается при старте main окна.
 *
 * 1. Просит Rust гарантировать что backend запущен (ensure_backend_running)
 * 2. Ждёт пока backend ответит на /health
 */
export async function connectBackend(): Promise<boolean> {
  // Шаг 1: Просим Rust запустить backend если он не запущен
  logs.append("[UI] Запуск backend...");
  try {
    await invoke("ensure_backend_running");
  } catch (e) {
    logs.append(`[UI] ensure_backend_running: ${e}`);
    // Не fatal — может python ещё не установлен, попробуем подождать
  }

  // Шаг 2: Ждём пока backend ответит (до 60 сек)
  for (let i = 0; i < 120; i++) {
    const url = await invoke<string | null>("backend_get_url");
    if (typeof url === "string" && url.startsWith("http")) {
      if (await checkHealth(url)) {
        backendUrl.set(url);
        backendReady.set(true);
        logs.append(`[UI] Backend готов: ${url}`);
        await loadModels();
        await loadEdgeVoices();
        return true;
      }
    }
    await sleep(500);
  }

  logs.append("[UI] Backend не ответил за 60 сек.");
  backendReady.set(false);
  return false;
}

/**
 * Обновление данных / переподключение.
 * Если backend жив — обновляет списки.
 * Если мёртв — перезапускает.
 */
export async function refreshAll(): Promise<void> {
  const url = get(backendUrl);

  if (url && await checkHealth(url)) {
    await loadModels();
    await loadEdgeVoices();
    logs.append("[UI] Данные обновлены.");
    toasts.show("Данные обновлены");
    return;
  }

  logs.append("[UI] Backend не отвечает, перезапуск...");
  backendReady.set(false);
  backendUrl.set(null);

  try {
    await invoke("ensure_backend_running");
  } catch (e) {
    logs.append(`[UI] ensure: ${e}`);
  }

  const ok = await connectBackend();
  if (ok) {
    toasts.show("Backend перезапущен");
  } else {
    toasts.show("Не удалось перезапустить backend");
  }
}

export async function restartBackend(): Promise<void> {
  backendReady.set(false);
  backendUrl.set(null);
  await connectBackend();
}

// ═══════════════════════════════════════════════════════════════
// SSE & Job tracking
// ═══════════════════════════════════════════════════════════════

function attachSSE(jobId: string): void {
  stopSSE();
  const url = get(backendUrl);
  if (!url) return;

  const es = new EventSource(`${url}/jobs/${jobId}/events`);
  eventSource = es;

  es.onmessage = (ev) => {
    try {
      const msg = JSON.parse(ev.data);
      currentJob.update((job) => {
        if (!job) job = { job_id: jobId, status: "running", progress: 0, message: "" };

        switch (msg.type) {
          case "progress":
            job.progress = Number(msg.progress ?? job.progress);
            job.message = String(msg.message ?? job.message);
            if (msg.message) logs.append(String(msg.message));
            break;
          case "result":
            job.result = msg.result;
            break;
          case "status":
            job.status = msg.status;
            job.message = String(msg.message ?? job.message);
            if (msg.result) job.result = msg.result;
            if (job.status === "done" || job.status === "error") stopSSE();
            break;
          case "error":
            job.error = String(msg.error ?? "");
            job.status = "error";
            logs.append(`[ERROR] ${msg.error ?? ""}`);
            break;
          case "log":
            logs.append(String(msg.line ?? ""));
            break;
          case "snapshot":
            if (msg.result) job.result = msg.result;
            if (msg.status) job.status = msg.status;
            if (msg.progress !== undefined) job.progress = Number(msg.progress);
            if (msg.message) job.message = String(msg.message);
            break;
        }
        return { ...job };
      });
    } catch (e) {
      logs.append(`[UI] SSE parse: ${e}`);
    }
  };

  es.onerror = () => {
    stopSSE();
    logs.append("[UI] SSE отключён, polling...");
  };
}

async function waitForJobCompletion(jobId: string): Promise<void> {
  for (let i = 0; i < 7200; i++) {
    const job = get(currentJob);
    if (job && (job.status === "done" || job.status === "error")) break;

    const sseActive = eventSource !== null && eventSource.readyState === EventSource.OPEN;
    if (!sseActive) {
      const url = get(backendUrl);
      if (url) {
        try {
          const r = await fetch(`${url}/jobs/${jobId}`);
          const data = (await r.json()) as JobSnapshot;
          currentJob.set(data);
          if (data.status === "done" || data.status === "error") break;
        } catch {}
      }
    }
    await sleep(sseActive ? 2000 : 500);
  }

  stopSSE();

  const url = get(backendUrl);
  if (url) {
    try {
      const r = await fetch(`${url}/jobs/${jobId}`);
      const data = (await r.json()) as JobSnapshot;
      currentJob.set(data);
      if (data.status === "done" && data.result?.output_path) {
        playerPath.set(data.result.output_path);
      }
    } catch {}
  }
  jobRunning.set(false);
}

// ═══════════════════════════════════════════════════════════════
// Job submission
// ═══════════════════════════════════════════════════════════════

export async function postJob(endpoint: string, body: Record<string, any>): Promise<boolean> {
  const url = get(backendUrl);
  if (!url) { toasts.show("Backend не подключён"); return false; }
  if (get(jobRunning)) { toasts.show("Задача уже выполняется"); return false; }

  jobRunning.set(true);
  playerPath.set(null);
  currentJob.set({ job_id: "-", status: "running", progress: 0, message: "Запуск...", result: null, error: null });

  try {
    const r = await fetch(`${url}${endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!r.ok) {
      const txt = await r.text().catch(() => "");
      currentJob.set({ job_id: "-", status: "error", progress: 0, message: "Ошибка", error: txt });
      jobRunning.set(false);
      return false;
    }
    const data = await r.json();
    currentJobId.set(data.job_id);
    currentJob.set({ job_id: data.job_id, status: "queued", progress: 0, message: "Ожидание..." });
    attachSSE(data.job_id);
    await waitForJobCompletion(data.job_id);
    return true;
  } catch (e) {
    currentJob.set({ job_id: "-", status: "error", progress: 0, message: "Ошибка", error: String(e) });
    jobRunning.set(false);
    return false;
  }
}

// ═══════════════════════════════════════════════════════════════
// Model management
// ═══════════════════════════════════════════════════════════════

export async function deleteModel(name: string): Promise<void> {
  const url = get(backendUrl);
  if (!url) return;
  try {
    const r = await fetch(`${url}/models/rvc/${encodeURIComponent(name)}`, { method: "DELETE" });
    if (!r.ok) { logs.append(`[UI] delete: ${r.status}`); return; }
    logs.append(`[UI] Удалено: ${name}`);
    await loadModels();
  } catch (e) {
    logs.append(`[UI] delete: ${e}`);
  }
}

export async function openModelFolder(name: string): Promise<void> {
  try { await invoke("open_rvc_model_dir", { modelName: name }); }
  catch (e) { logs.append(`[UI] ${e}`); }
}

export async function openOutputDir(): Promise<void> {
  try { await invoke("open_output_dir"); }
  catch (e) { logs.append(`[UI] ${e}`); }
}

export async function openFilePath(path: string): Promise<void> {
  try { await invoke("open_file_default", { path }); }
  catch (e) { logs.append(`[UI] ${e}`); }
}