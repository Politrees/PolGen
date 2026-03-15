<script lang="ts">
  import { onMount, afterUpdate } from "svelte";
  import { invoke } from "@tauri-apps/api/tauri";
  import { listen, type UnlistenFn } from "@tauri-apps/api/event";
  import {
    installMode,
    selectedUrl,
    isRunning,
    installProgress,
    installMessage,
    installLogs,
    installSuccess,
    currentStep,
    appendLog,
    clearLogs,
  } from "./state";
  import type { DownloadProgressEvent } from "./types";

  let logBox: HTMLDivElement;
  let autoScroll = true;
  let listeners: UnlistenFn[] = [];
  let cancelled = false;

  afterUpdate(() => {
    if (logBox && autoScroll) {
      logBox.scrollTop = logBox.scrollHeight;
    }
  });

  function onLogScroll() {
    if (!logBox) return;
    autoScroll = logBox.scrollTop + logBox.clientHeight >= logBox.scrollHeight - 20;
  }

  function cleanup() {
    for (const un of listeners) un();
    listeners = [];
  }

  onMount(() => {
    startInstall();
    return cleanup;
  });

  async function startInstall() {
    if ($isRunning) return;
    $isRunning = true;
    $installSuccess = null;
    $installProgress = 0;
    $installMessage = "Подготовка...";
    cancelled = false;
    clearLogs();

    if ($installMode === "download") {
      await startDownload();
    } else {
      await startConda();
    }
  }

  async function startDownload() {
    if (!$selectedUrl) {
      appendLog("URL не выбран.");
      $isRunning = false;
      $installSuccess = false;
      return;
    }

    listeners.push(
      await listen<{ line: string }>("setup-log", (ev) => {
        appendLog(ev.payload.line);
      })
    );

    listeners.push(
      await listen<DownloadProgressEvent>("download-progress", (ev) => {
        $installProgress = ev.payload.percent;
        $installMessage = ev.payload.message;
      })
    );

    listeners.push(
      await listen<{ success: boolean; message: string }>("download-done", (ev) => {
        cleanup();
        if (cancelled) {
          appendLog("Установка отменена.");
          $isRunning = false;
          $installSuccess = false;
          return;
        }
        appendLog(ev.payload.message);
        $isRunning = false;
        $installSuccess = ev.payload.success;
        if (ev.payload.success) {
          $installProgress = 100;
          $installMessage = "Установка завершена!";
        }
      })
    );

    try {
      await invoke("download_env", { url: $selectedUrl });
    } catch (e) {
      cleanup();
      if (!cancelled) {
        appendLog(`Ошибка: ${e}`);
        $isRunning = false;
        $installSuccess = false;
      }
    }
  }

  async function startConda() {
    listeners.push(
      await listen<{ line: string }>("setup-log", (ev) => {
        appendLog(ev.payload.line);
      })
    );

    listeners.push(
      await listen<{ success: boolean; message: string }>("setup-done", (ev) => {
        cleanup();
        if (cancelled) {
          appendLog("Установка отменена.");
          $isRunning = false;
          $installSuccess = false;
          return;
        }
        appendLog(ev.payload.message);
        $isRunning = false;
        $installSuccess = ev.payload.success;
        if (ev.payload.success) {
          $installProgress = 100;
          $installMessage = "Установка завершена!";
        }
      })
    );

    try {
      await invoke("run_setup");
    } catch (e) {
      cleanup();
      if (!cancelled) {
        appendLog(`Ошибка: ${e}`);
        $isRunning = false;
        $installSuccess = false;
      }
    }
  }

  async function cancelInstall() {
    cancelled = true;
    cleanup();
    appendLog("Отмена установки...");
    $installMessage = "Отмена...";

    // Пытаемся остановить backend/скачивание через Tauri
    try {
      await invoke("cancel_setup");
    } catch {
      // команда может не существовать — ничего страшного
    }

    $isRunning = false;
    $installSuccess = false;
    $installProgress = 0;
    $installMessage = "Установка отменена.";
    appendLog("Установка отменена пользователем.");
  }

  function goBack() {
    cleanup();
    $isRunning = false;
    $installSuccess = null;
    $installProgress = 0;
    $installMessage = "";
    $currentStep = "configure";
  }
</script>

<div class="setup-step">
  <h2>
    {#if cancelled}
      ⚠ Установка отменена
    {:else if $isRunning}
      ⏳ Идёт установка...
    {:else if $installSuccess === true}
      ✅ Установка завершена
    {:else if $installSuccess === false}
      ❌ Ошибка установки
    {/if}
  </h2>

  <!-- Progress bar -->
  <div class="dl-progress-bar">
    <div class="dl-progress-fill" style="width: {Math.round($installProgress)}%" />
  </div>
  <div class="dl-progress-text">{$installMessage}</div>

  <!-- Лог -->
  <div class="setup-log" bind:this={logBox} on:scroll={onLogScroll}>
    {#each $installLogs as line}{line + "\n"}{/each}
  </div>

  <!-- Кнопки -->
  {#if $isRunning}
    <button class="setup-btn-cancel" on:click={cancelInstall}>
      ✖ Отменить
    </button>
  {:else if $installSuccess === true}
    <button class="setup-btn" on:click={() => ($currentStep = "done")}>
      Далее →
    </button>
  {:else}
    <div class="setup-buttons">
      <button class="setup-btn-secondary" on:click={goBack}>
        ← Назад
      </button>
      <button class="setup-btn" on:click={startInstall}>
        Повторить
      </button>
    </div>
  {/if}
</div>