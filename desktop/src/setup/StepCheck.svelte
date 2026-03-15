<script lang="ts">
  import { envStatus, platform, currentStep, selectedUrl, installMode } from "./state";

  $: env = $envStatus;
  $: plat = $platform;
  $: allReady = env?.ready ?? false;
  $: canProceed = !!env?.project_root;

  function goNext() {
    if (allReady) {
      $currentStep = "done";
      return;
    }
    if (plat) {
      $selectedUrl = plat.recommended_url;
      $installMode = "download";
    }
    $currentStep = "configure";
  }

  function formatVram(mb: number): string {
    if (mb <= 0) return "";
    if (mb >= 1024) return `, ${(mb / 1024).toFixed(0)} ГБ VRAM`;
    return `, ${mb} МБ VRAM`;
  }

  // Режим который будет предложен
  $: recommendedMode = plat?.gpu_cuda_capable ? "CUDA" : "CPU";

  $: checks = (() => {
    const list: Array<{ ok: boolean; text: string }> = [];

    // Проект
    list.push({
      ok: !!env?.project_root,
      text: env?.project_root
        ? `Проект найден`
        : "Корень проекта не найден",
    });

    // Окружение
    list.push({
      ok: env?.env_exists ?? false,
      text: env?.env_exists
        ? "Окружение установлено"
        : "Окружение не установлено",
    });

    // GPU
    if (plat) {
      if (!plat.has_nvidia) {
        list.push({
          ok: false,
          text: "NVIDIA GPU не обнаружена → режим CPU",
        });
      } else if (plat.gpu_cuda_capable) {
        list.push({
          ok: true,
          text: `${plat.gpu_name}${formatVram(plat.gpu_vram_mb)} → режим CUDA`,
        });
      } else {
        list.push({
          ok: false,
          text: `${plat.gpu_name}${formatVram(plat.gpu_vram_mb)} → режим CPU`,
        });
      }
    }

    return list;
  })();

  // Показываем причину отказа от CUDA только если NVIDIA есть, но не подходит
  $: showCudaWarning = plat && plat.has_nvidia && !plat.gpu_cuda_capable;
</script>

<div class="setup-step">
  <div class="setup-header">
    <div class="setup-logo" />
    <div class="setup-header-text">
      <h1>PolGen Desktop</h1>
      <p>Проверка системы</p>
    </div>
  </div>

  <div class="checks">
    {#each checks as check}
      <div class="check" class:ok={check.ok} class:warn={!check.ok}>
        <span class="check-icon">{check.ok ? "✓" : "○"}</span>
        {check.text}
      </div>
    {/each}
  </div>

  {#if showCudaWarning && plat}
    <div class="setup-warn">{plat.cuda_reason}</div>
  {/if}

  {#if !canProceed}
    <div class="setup-warn">
      Убедитесь что исполняемый файл находится в папке с app.py и rvc/.
    </div>
  {/if}

  {#if allReady}
    <div class="ready-box">
      <span>✅</span> Всё готово, можно запускать.
    </div>
  {:else if canProceed}
    <div class="info-box">
      Будет предложен режим <b>{recommendedMode}</b>. Требуется ~15 ГБ на диске.
    </div>
  {/if}

  <button class="setup-btn" disabled={!canProceed} on:click={goNext}>
    {allReady ? "🚀 Запустить" : "Далее →"}
  </button>
</div>

<style>
  .info-box {
    font-size: 12px;
    color: var(--text-muted);
    padding: 8px 12px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid var(--border);
    border-radius: 8px;
    line-height: 1.5;
  }

  .info-box b {
    color: var(--accent-text);
  }

  .ready-box {
    font-size: 12px;
    color: #3fb950;
    padding: 8px 12px;
    background: rgba(63, 185, 80, 0.08);
    border: 1px solid rgba(63, 185, 80, 0.2);
    border-radius: 8px;
    display: flex;
    align-items: center;
    gap: 6px;
  }
</style>