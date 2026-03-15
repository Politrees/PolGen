<script lang="ts">
  import { afterUpdate } from "svelte";
  import { currentJob, currentJobId, logs, toasts } from "$lib/state";
  import { fmtPct, basename, truncate, tryCopy } from "$lib/utils";
  import { openFilePath, openOutputDir } from "$lib/api";

  let logBox: HTMLDivElement;
  let autoScroll = true;

  let showBanner = false;
  let bannerKind: "warn" | "error" = "warn";
  let bannerTitle = "";
  let bannerMsg = "";

  $: job = $currentJob;
  $: isError = job?.status === "error";
  $: isDone = job?.status === "done";
  $: isRunning = job?.status === "running" || job?.status === "queued";
  $: progress = isError ? 0 : (job?.progress ?? 0);
  $: msg = isError ? "Ошибка" : (job?.message ?? "");
  $: progressText = job ? `${fmtPct(progress)} • ${msg}` : "Ожидание...";
  $: progressWidth = `${Math.round(progress * 100)}%`;

  $: jobId = $currentJobId ?? "-";
  $: status = job?.status ?? "idle";
  $: outPath = job?.result?.output_path;
  $: outputDisplay = typeof outPath === "string" ? basename(outPath) : "-";
  $: outputTitle = typeof outPath === "string" ? outPath : "";
  $: hasStems = Array.isArray(job?.result?.stems) && job.result.stems.length > 0;

  const statusIcons: Record<string, string> = {
    idle: "⏳",
    queued: "⏳",
    running: "⚙️",
    done: "✅",
    error: "❌",
  };

  $: statusIcon = statusIcons[status] ?? "⏳";

  $: if (isError && job?.error?.trim()) {
    showBanner = true;
    bannerKind = "error";
    bannerTitle = "Ошибка";
    bannerMsg = job.error;
  } else {
    showBanner = false;
  }

  afterUpdate(() => {
    if (logBox && autoScroll) {
      logBox.scrollTop = logBox.scrollHeight;
    }
  });

  function onLogScroll() {
    if (!logBox) return;
    const atBottom = logBox.scrollTop + logBox.clientHeight >= logBox.scrollHeight - 20;
    autoScroll = atBottom;
  }

  async function copyError() {
    if (job?.error) {
      const ok = await tryCopy(job.error);
      toasts.show(ok ? "Скопировано в буфер обмена" : "Не удалось скопировать");
    }
  }

  function openResult() {
    if (outPath) openFilePath(outPath);
  }
</script>

<div class="card">
  <div class="panel-header">
    <h2>Задача</h2>
    {#if isDone && outPath}
      <button class="btn result-btn" on:click={openResult} title={outPath}>
        📄 Открыть результат
      </button>
    {:else if isDone && hasStems}
      <button class="btn result-btn" on:click={openOutputDir}>
        📁 Открыть папку
      </button>
    {/if}
  </div>

  {#if showBanner}
    <div class="banner" class:error={bannerKind === "error"}>
      <div class="bannerHead">
        <div class="bannerTitle">{bannerTitle}</div>
        <div class="bannerBtns">
          <button class="btn" on:click={copyError}>Копировать</button>
        </div>
      </div>
      <div class="bannerMsg" title={bannerMsg}>{truncate(bannerMsg)}</div>
    </div>
  {/if}

  <div class="kv">
    <div>
      <span>Status</span>
      <b class="status-badge" class:status-running={isRunning} class:status-done={isDone} class:status-error={isError}>
        {statusIcon} {status}
      </b>
    </div>
    <div><span>Job ID</span><b>{jobId}</b></div>
    {#if outPath}
      <div><span>Output</span><b title={outputTitle}>{outputDisplay}</b></div>
    {/if}
    {#if hasStems}
      <div><span>Stems</span><b>{job?.result?.stems?.length ?? 0} файлов</b></div>
    {/if}
  </div>

  <div class="hr" />

  <div class="small">{progressText}</div>
  <div class="progressBar" class:progress-active={isRunning}>
    <div style="width: {progressWidth}" />
  </div>

  <div class="hr" />

  <details>
    <summary>Логи</summary>
    <div
      class="log"
      bind:this={logBox}
      on:scroll={onLogScroll}
    >
      {#each $logs as line}{line + "\n"}{/each}
    </div>
    <button class="btn log-clear-btn" on:click={() => logs.clear()}>Очистить логи</button>
  </details>
</div>

<style>
  .panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  .result-btn {
    height: 30px !important;
    padding: 0 12px !important;
    font-size: 11px !important;
    margin: 0 !important;
    width: auto !important;
    background: rgba(35, 134, 54, 0.1) !important;
    border: 1px solid rgba(35, 134, 54, 0.25) !important;
    color: var(--accent-text) !important;
  }

  .result-btn:hover {
    background: rgba(35, 134, 54, 0.2) !important;
    border-color: rgba(35, 134, 54, 0.4) !important;
  }

  .status-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
  }

  .status-running {
    color: #d29922 !important;
  }

  .status-done {
    color: #3fb950 !important;
  }

  .status-error {
    color: var(--danger) !important;
  }

  .progress-active div {
    animation: progress-shimmer 2s linear infinite, progress-pulse 1.5s ease-in-out infinite;
  }

  @keyframes progress-pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.85; }
  }

  .log-clear-btn {
    width: 100%;
    margin-top: 8px;
    justify-content: center;
  }
</style>