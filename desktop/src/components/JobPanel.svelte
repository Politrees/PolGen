<script lang="ts">
  import { afterUpdate } from "svelte";
  import { currentJob, currentJobId, logs } from "$lib/state";
  import { fmtPct, basename, truncate, tryCopy } from "$lib/utils";

  let logBox: HTMLDivElement;
  let autoScroll = true;

  let showBanner = false;
  let bannerKind: "warn" | "error" = "warn";
  let bannerTitle = "";
  let bannerMsg = "";

  $: job = $currentJob;
  $: isError = job?.status === "error";
  $: progress = isError ? 0 : (job?.progress ?? 0);
  $: msg = isError ? "Ошибка" : (job?.message ?? "");
  $: progressText = job ? `${fmtPct(progress)} • ${msg}` : "Ожидание...";
  $: progressWidth = `${Math.round(progress * 100)}%`;

  $: jobId = $currentJobId ?? "-";
  $: status = job?.status ?? "idle";
  $: outPath = job?.result?.output_path;
  $: outputDisplay = typeof outPath === "string" ? basename(outPath) : "-";
  $: outputTitle = typeof outPath === "string" ? outPath : "";

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
      logs.append(ok ? "[UI] Скопировано." : "[UI] Не удалось.");
    }
  }
</script>

<div class="card">
  <h2>Задача / Прогресс</h2>

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
    <div><span>Job ID</span><b>{jobId}</b></div>
    <div><span>Status</span><b>{status}</b></div>
    <div><span>Output</span><b title={outputTitle}>{outputDisplay}</b></div>
  </div>

  <div class="hr" />

  <div class="small">{progressText}</div>
  <div class="progressBar">
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
  .log-clear-btn {
    width: 100%;
    margin-top: 8px;
    justify-content: center;
  }
</style>